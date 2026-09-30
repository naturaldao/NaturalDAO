"""客户端：重试/退避、429/5xx、不可重试错误、两种协议、成本日志、密钥不泄露（离线）。"""
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from clients import (CallFailure, CallLog, ChatClient, SOURCES, build_client,
                     run_ordered, validate_endpoint)
from common import load_secret


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status = status
        self._body = body
        self.headers = headers or {}

    def read(self, size=-1):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    def __init__(self, script):
        self.script = list(script)
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, Exception):
            raise item
        return FakeResponse(*item)


def body(text="ok", **usage):
    payload = {"choices": [{"message": {"content": text}}]}
    if usage:
        payload["usage"] = usage
    return json.dumps(payload).encode("utf-8")


def responses_body(text="ok", **usage):
    payload = {"output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}
    if usage:
        payload["usage"] = usage
    return json.dumps(payload).encode("utf-8")


def make_client(script, **kwargs):
    log = kwargs.pop("log", CallLog())
    slept = []
    client = ChatClient(provider="test", base_url="https://example.invalid/v1", model="m",
                        key="secret-key-value", key_source="test", lineage="test",
                        log=log, opener=FakeOpener(script), sleeper=slept.append,
                        backoff_jitter=0.0, **kwargs)
    return client, log, slept


class RetryTests(unittest.TestCase):
    def test_429_then_success_retries_with_retry_after(self):
        client, log, slept = make_client([(429, b"{}", {"Retry-After": "1"}),
                                          (200, body("done", prompt_tokens=10,
                                                     completion_tokens=5, total_tokens=15), {})])
        result = client.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(result["text"], "done")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(slept, [1.0])
        self.assertEqual([row["ok"] for row in log.rows], [False, True])
        self.assertEqual(log.summary()["total_tokens"], 15)

    def test_5xx_retries_then_gives_up(self):
        client, log, slept = make_client([(503, b"busy", {})], max_attempts=2, backoff=0.5)
        with self.assertRaises(CallFailure) as caught:
            client.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(caught.exception.attempts, 2)
        self.assertEqual(len(log.rows), 2)
        self.assertEqual(len(slept), 1)

    def test_401_is_not_retried(self):
        client, log, slept = make_client([(401, b'{"error":"bad key"}', {})], max_attempts=3)
        with self.assertRaises(CallFailure) as caught:
            client.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(caught.exception.kind, "error")
        self.assertEqual(len(log.rows), 1)
        self.assertEqual(slept, [])

    def test_timeout_is_retried(self):
        client, log, _ = make_client([urllib.error.URLError(TimeoutError("slow")),
                                      (200, body("late"), {})], max_attempts=2)
        self.assertEqual(client.chat([{"role": "user", "content": "hi"}])["text"], "late")

    def test_empty_content_is_invalid_not_ok(self):
        empty = json.dumps({"choices": [{"message": {"content": "", "reasoning_content": ""}}]})
        client, log, _ = make_client([(200, empty.encode("utf-8"), {})])
        with self.assertRaises(CallFailure) as caught:
            client.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(caught.exception.kind, "invalid")
        self.assertFalse(log.rows[-1]["ok"])

    def test_reasoning_content_is_accepted(self):
        payload = json.dumps({"choices": [{"message": {"content": "",
                                                       "reasoning_content": "推理结果"}}]})
        client, _, _ = make_client([(200, payload.encode("utf-8"), {})])
        self.assertEqual(client.chat([{"role": "user", "content": "hi"}])["text"], "推理结果")

    def test_invalid_can_be_retried_when_asked(self):
        empty = json.dumps({"choices": [{"message": {"content": "", "reasoning_content": ""}}]})
        client, log, slept = make_client([(200, empty.encode("utf-8"), {}),
                                          (200, body("recovered"), {})], retry_invalid=True)
        self.assertEqual(client.chat([{"role": "user", "content": "hi"}])["text"], "recovered")
        self.assertEqual([row["ok"] for row in log.rows], [False, True])
        self.assertEqual(log.rows[0]["failure_kind"], "invalid")
        self.assertEqual(log.rows[1]["retries"], 1)
        self.assertEqual(log.summary()["failed_by_kind"], {"invalid": 1})
        self.assertEqual(log.summary()["invalid_attempt_rate"], 0.5)

    def test_key_never_appears_in_log_or_summary(self):
        client, log, _ = make_client([(200, body("done"), {})])
        client.chat([{"role": "user", "content": "hi"}])
        rendered = json.dumps(log.rows, ensure_ascii=False) + json.dumps(log.summary())
        self.assertNotIn("secret-key-value", rendered)
        self.assertIn("key_fingerprint", log.rows[0])

    def test_cost_is_computed_when_prices_given(self):
        client, log, _ = make_client([(200, body("done", prompt_tokens=1000,
                                                 completion_tokens=500, total_tokens=1500), {})],
                                     price_in=1.0, price_out=2.0)
        client.chat([{"role": "user", "content": "hi"}])
        self.assertAlmostEqual(log.rows[0]["cost_usd"], (1000 * 1.0 + 500 * 2.0) / 1e6)
        self.assertAlmostEqual(log.summary()["cost_usd"], 0.002)
        unpriced, unpriced_log, _ = make_client([(200, body("done"), {})])
        unpriced.chat([{"role": "user", "content": "hi"}])
        self.assertIsNone(unpriced_log.summary()["cost_usd"])  # 价格未知写 null，不编造 0


class ProtocolTests(unittest.TestCase):
    def test_responses_protocol_payload_and_parsing(self):
        client, log, _ = make_client([(200, responses_body("判定结果", input_tokens=7,
                                                           output_tokens=3), {})],
                                     protocol="responses")
        result = client.chat([{"role": "user", "content": "问题"}])
        self.assertEqual(result["text"], "判定结果")
        self.assertTrue(client.url.endswith("/responses"))
        sent = json.loads(client._opener.requests[0].data.decode("utf-8"))
        self.assertEqual(set(sent), {"model", "input", "max_output_tokens"})
        self.assertEqual(sent["input"], "问题")
        self.assertEqual(log.rows[0]["total_tokens"], 10)

    def test_responses_empty_output_is_invalid(self):
        empty = json.dumps({"output": [{"content": []}]}).encode("utf-8")
        client, _, _ = make_client([(200, empty, {})], protocol="responses")
        with self.assertRaises(CallFailure) as caught:
            client.chat([{"role": "user", "content": "问题"}])
        self.assertEqual(caught.exception.kind, "invalid")

    def test_chat_protocol_path(self):
        client, _, _ = make_client([(200, body("x"), {})])
        self.assertTrue(client.url.endswith("/chat/completions"))


class EndpointAndConfigTests(unittest.TestCase):
    def test_plain_http_only_for_loopback(self):
        validate_endpoint("http://127.0.0.1:8009/answers")
        for bad in ("http://example.com/v1", "ftp://example.com",
                    "https://user:pass@example.com/v1", "https://example.com/v1?x=1"):
            with self.assertRaises(ValueError):
                validate_endpoint(bad)

    def test_source_matrix_matches_the_approved_models(self):
        self.assertEqual(SOURCES["luna"]["model"], "gpt-6-luna")
        self.assertEqual(SOURCES["luna"]["lineage"], "openai-luna")
        self.assertEqual(SOURCES["luna"]["key_env"], "SUB_API_KEY")
        self.assertEqual(SOURCES["gpt-6.1-sol"]["protocol"], "responses")
        self.assertEqual(SOURCES["gpt-6.1-sol"]["lineage"], "openai-sol")
        self.assertEqual(SOURCES["grok-4.7"]["key_env"], "SUB_GROK_API_KEY")
        self.assertEqual(SOURCES["grok-4.7"]["lineage"], "xai-grok")
        self.assertEqual(SOURCES["mimo-v2.6-pro"]["lineage"], "xiaomi-mimo")
        self.assertEqual(SOURCES["deepseek-v4.1-flash"]["model"], "deepseek-v4.1-flash")
        for name in SOURCES:
            self.assertIn("protocol", SOURCES[name])
        self.assertEqual(SOURCES["glm-5.3"]["lineage"], SOURCES["glm-5.3-flash"]["lineage"])

    def test_user_agent_is_a_product_name_not_urllib(self):
        client = build_client("luna", api_key="k")
        agent = client._headers()["User-Agent"]
        self.assertIn("PoL2-pipeline", agent)
        self.assertNotIn("urllib", agent.lower())

    def test_session_header_and_max_token_floor(self):
        mimo = build_client("mimo-v2.6-pro", api_key="k", max_tokens=64)
        self.assertEqual(mimo.payload([{"role": "user", "content": "hi"}])["max_tokens"], 1024)
        self.assertTrue(mimo._headers()["x-opencode-session"])
        self.assertEqual(mimo.base_url, "https://opencode.ai/zen/go/v1")
        sol = build_client("gpt-6.1-sol", api_key="k", max_tokens=16)
        self.assertEqual(sol.payload([{"role": "user", "content": "hi"}])["max_output_tokens"], 1024)
        self.assertNotIn("x-opencode-session", sol._headers())
        luna = build_client("luna", api_key="k", max_tokens=8192)
        self.assertEqual(luna.payload([{"role": "user", "content": "hi"}])["max_tokens"], 8192)
        with self.assertRaises(ValueError):
            build_client("unknown-source", api_key="k")

    def test_load_secret_env_file_and_failure(self):
        with mock.patch.dict(os.environ, {"SUB_API_KEY": "  from-env  "}, clear=False):
            secret, origin = load_secret(["SUB_API_KEY"])
            self.assertEqual(secret, "from-env")
            self.assertEqual(origin, "env:SUB_API_KEY")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "credentials.yaml"
            path.write_text("version: 1\nrefs:\n  SUB_API_KEY: sk-file-value\n"
                            "records: {}\n", encoding="utf-8")
            env = {key: value for key, value in os.environ.items() if key != "SUB_API_KEY"}
            with mock.patch.dict(os.environ, env, clear=True):
                secret, origin = load_secret(["SUB_API_KEY"], key_file=path)
                self.assertEqual(secret, "sk-file-value")
                self.assertIn("credentials.yaml", origin)
                with self.assertRaises(ValueError):
                    load_secret(["OPENCODE_GO_API_KEY"], key_file=path)
                with self.assertRaises(ValueError):
                    load_secret(["MISSING_KEY"])


class ConcurrencyTests(unittest.TestCase):
    def test_run_ordered_keeps_order_and_captures_errors(self):
        def worker(item, index):
            if item == "bad":
                raise RuntimeError("boom")
            return f"{index}:{item}"
        results = run_ordered(["a", "bad", "c"], worker, workers=3)
        self.assertEqual(results[0], "0:a")
        self.assertIsInstance(results[1], RuntimeError)
        self.assertEqual(results[2], "2:c")

    def test_serial_mode_matches(self):
        self.assertEqual(run_ordered([1, 2], lambda item, index: item * 2, workers=1), [2, 4])


if __name__ == "__main__":
    unittest.main()
