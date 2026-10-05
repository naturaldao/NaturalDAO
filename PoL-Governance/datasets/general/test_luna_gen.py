# -*- coding: utf-8 -*-
"""test_luna_gen.py —— luna_gen 的离线测试（不联网、不读真实密钥）。

覆盖：路由固定、taxonomy 对齐、提示内容、dry-run 不联网、--live 的各种硬门禁、
密钥不落盘、HTTP 重试与错误分类、fixture 回放、与 luna_clean 的端到端串联。
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import luna_clean as lc  # noqa: E402
import luna_gen as lg  # noqa: E402

FIXED_TIME = "2026-09-30T12:00:00+00:00"


def simple_response(state="同事在会上反复打断你，你准备指出这一点。"):
    payload = {"items": [{"state": state, "lang": "zh",
                          "questions": [{"key": "contains_harm", "kind": "noul",
                                         "prompt": "这个情境包含伤害吗？"}],
                          "targets": {"contains_harm": {"answer": "no",
                                                        "probs": {"yes": 0.1, "no": 0.9}}}}]}
    return json.dumps(payload, ensure_ascii=False)


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.headers = {}

    def read(self, size=None):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResponse(*item)


def chat_body(text, finish_reason="stop", prompt_tokens=100, completion_tokens=200):
    return {"choices": [{"message": {"content": text}, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                      "total_tokens": prompt_tokens + completion_tokens}}


class RouteTests(unittest.TestCase):
    def test_routes_are_pinned(self):
        self.assertEqual(lg.ROUTES["luna"]["base_url"], "https://sub.461561.xyz/v1")
        self.assertEqual(lg.ROUTES["luna"]["model"], "gpt-6-luna")
        self.assertEqual(lg.ROUTES["luna"]["key_env"], "SUB_API_KEY")
        self.assertIsNone(lg.ROUTES["luna"]["session_header"])
        self.assertEqual(lg.ROUTES["opencode-go"]["base_url"], "https://opencode.ai/zen/go/v1")
        self.assertEqual(lg.ROUTES["opencode-go"]["model"], "deepseek-v4.1-flash")
        self.assertEqual(lg.ROUTES["opencode-go"]["key_env"], "OPENCODE_GO_API_KEY")
        self.assertEqual(lg.ROUTES["opencode-go"]["session_header"], "x-opencode-session")

    def test_client_url_is_chat_completions(self):
        client = lg.LunaClient(api_key="k", opener=FakeOpener([]))
        self.assertEqual(client.url, "https://sub.461561.xyz/v1/chat/completions")


class PromptTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = lg.load_taxonomy()

    def test_prompt_lists_keys_and_rules(self):
        specs = self.taxonomy.domains["risk_harm"]
        prompt = lg.build_prompt("risk_harm", specs, "zh", 2)
        self.assertIn("risk_harm", prompt)
        self.assertIn("items", prompt)
        self.assertIn("probs", prompt)
        self.assertIn("markdown", prompt)
        self.assertIn("3", prompt)
        for spec in specs:
            self.assertIn(spec["key"], prompt)
            self.assertIn(spec["kind"], prompt)

    def test_prompt_is_deterministic(self):
        specs = self.taxonomy.domains["pol2_axis"]
        self.assertEqual(lg.build_prompt("pol2_axis", specs, "zh", 2),
                         lg.build_prompt("pol2_axis", specs, "zh", 2))

    def test_prompt_differs_by_domain(self):
        first = lg.build_prompt("risk_harm", self.taxonomy.domains["risk_harm"], "zh", 1)
        second = lg.build_prompt("pol2_axis", self.taxonomy.domains["pol2_axis"], "zh", 1)
        self.assertNotEqual(first, second)

    def test_describe_spec_for_each_kind(self):
        for specs in self.taxonomy.domains.values():
            for spec in specs:
                line = lg.describe_spec(spec)
                self.assertIn(spec["key"], line)
                self.assertIn(spec["kind"], line)

    def test_fallback_prompt_uses_readme_domains(self):
        taxonomy = lg.fallback_taxonomy()
        self.assertEqual(sorted(taxonomy.domains), sorted(lg.FALLBACK_DOMAINS))
        for domain, specs in taxonomy.domains.items():
            self.assertTrue(specs, domain)
            prompt = lg.build_prompt(domain, specs)
            self.assertIn(domain, prompt)

    def test_plan_ids_unique_and_deterministic(self):
        first = lg.build_plan(self.taxonomy, samples=2, created_at=FIXED_TIME)
        second = lg.build_plan(self.taxonomy, samples=2, created_at=FIXED_TIME)
        self.assertEqual([row["id"] for row in first], [row["id"] for row in second])
        self.assertEqual(len({row["id"] for row in first}), len(first))

    def test_plan_unknown_domain_raises(self):
        with self.assertRaises(lg.Failure):
            lg.build_plan(self.taxonomy, domains=["not_a_domain"])


class TaxonomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.domains, cls.source = lc.open_taxonomy()

    def test_fallback_when_missing(self):
        taxonomy = lg.load_taxonomy(Path("no-such-dir") / "taxonomy.py")
        self.assertIn("readme-fallback", taxonomy.source)
        self.assertEqual(sorted(taxonomy.domains), sorted(lg.FALLBACK_DOMAINS))

    def test_real_taxonomy_is_used_when_present(self):
        if self.module is None:
            self.skipTest("taxonomy.py 不可用")
        taxonomy = lg.load_taxonomy()
        self.assertEqual(taxonomy.source, "taxonomy.py")
        for domain in self.module.DOMAINS:
            self.assertIn(domain, taxonomy.domains)
        for domain, specs in taxonomy.domains.items():
            for spec in specs:
                self.assertIn(spec["key"], self.module.QUESTION_KEYS)
                key_spec = self.module.key_spec(spec["key"])
                self.assertEqual(spec["kind"], key_spec.kind)
                if spec["kind"] == "choice" and not spec.get("options_from_state"):
                    self.assertEqual({option["key"] for option in spec["options"]},
                                     set(key_spec.option_keys()))
                if spec["kind"] == "score":
                    self.assertEqual((spec["scale"]["min"], spec["scale"]["max"]),
                                     key_spec.scale[:2])

    def test_key_set_all_expands_beyond_core(self):
        if self.module is None:
            self.skipTest("taxonomy.py 不可用")
        args = lg.build_parser().parse_args(["--key-set", "all", "--domains", "pol2_axis"])
        taxonomy = lg._select_taxonomy(args)
        core = lg.load_taxonomy().domains["pol2_axis"]
        self.assertGreater(len(taxonomy.domains["pol2_axis"]), len(core))


class DryRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.plan = self.dir / "plan.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def read_jsonl(path):
        return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def test_dry_run_writes_plan_and_never_calls_model(self):
        def boom(*args, **kwargs):
            raise AssertionError("dry-run 不应该调用模型")

        with mock.patch.object(lg.LunaClient, "complete", boom):
            code = lg.main(["--dry-run", "--out-plan", str(self.plan), "--domains", "risk_harm",
                            "--samples", "2", "--created-at", FIXED_TIME, "--json"])
        self.assertEqual(code, 0)
        rows = self.read_jsonl(self.plan)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertTrue(row["id"].startswith("luna-risk_harm-"))
            self.assertTrue(row["prompt"])
            self.assertTrue(row["keys"])
            self.assertEqual(row["created_at"], FIXED_TIME)

    def test_dry_run_stdout_is_jsonl(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = lg.main(["--domains", "risk_harm", "--samples", "1"])
        self.assertEqual(code, 0)
        rows = [json.loads(line) for line in buffer.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(rows), 1)
        self.assertIn("prompt", rows[0])

    def test_list_domains(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = lg.main(["--list-domains"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(sorted(payload["domains"]), sorted(lg.FALLBACK_DOMAINS))

    def test_unknown_domain_exits_2(self):
        with self.assertRaises(SystemExit) as caught:
            lg.main(["--domains", "nope", "--dry-run"])
        self.assertEqual(caught.exception.code, 2)


class LiveGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.raw = self.dir / "raw.jsonl"
        self.fixture = self.dir / "fixture.jsonl"
        self.fixture.write_text(json.dumps({"response": simple_response()}, ensure_ascii=False) +
                                chr(10), encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {}, clear=False)

    def tearDown(self):
        self.tmp.cleanup()

    def test_live_requires_limit(self):
        with self.assertRaises(SystemExit) as caught:
            lg.main(["--live", "--raw-out", str(self.raw), "--domains", "risk_harm"])
        self.assertEqual(caught.exception.code, 2)

    def test_live_requires_raw_out(self):
        with self.assertRaises(SystemExit) as caught:
            lg.main(["--live", "--limit", "1", "--domains", "risk_harm", "--fixture",
                     str(self.fixture)])
        self.assertEqual(caught.exception.code, 2)

    def test_live_requires_min_max_tokens(self):
        with self.assertRaises(SystemExit) as caught:
            lg.main(["--live", "--limit", "1", "--max-tokens", "512", "--raw-out", str(self.raw),
                     "--domains", "risk_harm", "--fixture", str(self.fixture)])
        self.assertEqual(caught.exception.code, 2)

    def test_bulk_limit_needs_approval(self):
        with self.assertRaises(SystemExit) as caught:
            lg.main(["--live", "--limit", str(lg.BULK_LIMIT + 1), "--raw-out", str(self.raw),
                     "--domains", "risk_harm", "--fixture", str(self.fixture)])
        self.assertEqual(caught.exception.code, 2)

    def test_bulk_limit_with_approval_runs_fixture(self):
        with mock.patch.dict(os.environ, {"LUNA_BULK_APPROVED": "1"}):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = lg.main(["--live", "--limit", "1", "--raw-out", str(self.raw),
                                "--domains", "risk_harm", "--fixture", str(self.fixture)])
        self.assertEqual(code, 0)
        self.assertTrue(self.raw.is_file())

    def test_missing_key_exits_2(self):
        with mock.patch.dict(os.environ, {"SUB_API_KEY": ""}):
            with self.assertRaises(SystemExit) as caught:
                lg.main(["--live", "--limit", "1", "--raw-out", str(self.raw),
                         "--domains", "risk_harm"])
        self.assertEqual(caught.exception.code, 2)


class KeyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_key_from_env(self):
        with mock.patch.dict(os.environ, {"SUB_API_KEY": "sk-env"}):
            self.assertEqual(lg.load_key("SUB_API_KEY"), "sk-env")

    def test_load_key_from_file(self):
        path = self.dir / "key.txt"
        path.write_text("sk-file" + chr(10) + "second-line" + chr(10), encoding="utf-8")
        self.assertEqual(lg.load_key(None, str(path)), "sk-file")

    def test_load_key_missing_raises(self):
        with mock.patch.dict(os.environ, {"SUB_API_KEY": ""}):
            with self.assertRaises(lg.Failure):
                lg.load_key("SUB_API_KEY")
        with self.assertRaises(lg.Failure):
            lg.load_key(None, str(self.dir / "nope.txt"))

    def test_fingerprint_is_not_the_secret(self):
        secret = "sk-super-secret"
        self.assertNotEqual(lg.fingerprint(secret), secret)
        self.assertEqual(len(lg.fingerprint(secret)), 12)
        self.assertIsNone(lg.fingerprint(""))


class ClientTests(unittest.TestCase):
    def test_payload_shape(self):
        client = lg.LunaClient(api_key="k", model="gpt-6-luna", max_tokens=4096,
                               response_format="json_object", opener=FakeOpener([]))
        payload = client.payload([{"role": "user", "content": "hi"}])
        self.assertEqual(payload["model"], "gpt-6-luna")
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["messages"][0]["content"], "hi")

    def test_response_format_can_be_disabled(self):
        client = lg.LunaClient(api_key="k", response_format="none", opener=FakeOpener([]))
        self.assertNotIn("response_format", client.payload([{"role": "user", "content": "hi"}]))

    def test_headers_for_luna(self):
        client = lg.LunaClient(api_key="k", opener=FakeOpener([]))
        headers = client.headers_for()
        self.assertEqual(headers["Authorization"], "Bearer k")
        self.assertNotIn("x-opencode-session", headers)

    def test_headers_for_opencode(self):
        client = lg.LunaClient(route="opencode-go", api_key="k", opener=FakeOpener([]))
        headers = client.headers_for()
        session = headers["x-opencode-session"]
        self.assertEqual(len(session), 36)
        self.assertEqual(session.count("-"), 4)

    def test_successful_call_records_usage_and_finish_reason(self):
        opener = FakeOpener([(200, chat_body(simple_response(), finish_reason="length",
                                             prompt_tokens=11, completion_tokens=22))])
        client = lg.LunaClient(api_key="k", opener=opener)
        result = client.complete("prompt")
        self.assertEqual(result["finish_reason"], "length")
        self.assertEqual(result["usage"]["prompt_tokens"], 11)
        self.assertEqual(result["usage"]["completion_tokens"], 22)
        self.assertEqual(result["usage"]["total_tokens"], 33)
        self.assertIsNone(result["usage"]["cost_usd"])
        self.assertEqual(result["attempts"], 1)

    def test_retry_then_success(self):
        opener = FakeOpener([(503, {"error": "busy"}), (200, chat_body(simple_response()))])
        sleeps = []
        client = lg.LunaClient(api_key="k", opener=opener, sleeper=sleeps.append, max_attempts=3)
        result = client.complete("prompt")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(len(sleeps), 1)
        self.assertGreater(sleeps[0], 0)

    def test_client_error_is_not_retried(self):
        opener = FakeOpener([(400, {"error": "bad request"})])
        client = lg.LunaClient(api_key="k", opener=opener, max_attempts=3)
        with self.assertRaises(lg.CallFailure) as caught:
            client.complete("prompt")
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(len(opener.requests), 1)

    def test_extract_text_falls_back_to_reasoning(self):
        body = {"choices": [{"message": {"content": "  ", "reasoning_content": "answer"},
                            "finish_reason": "stop"}]}
        text, finish = lg.LunaClient.extract_text(body)
        self.assertEqual(text, "answer")
        self.assertEqual(finish, "stop")

    def test_extract_text_empty_raises(self):
        with self.assertRaises(lg.CallFailure):
            lg.LunaClient.extract_text({"choices": [{"message": {}}]})
        with self.assertRaises(lg.CallFailure):
            lg.LunaClient.extract_text({})

    def test_usage_defaults_to_none(self):
        usage = lg.LunaClient.extract_usage({})
        self.assertIsNone(usage["prompt_tokens"])
        self.assertIsNone(usage["total_tokens"])
        self.assertIsNone(usage["cost_usd"])

    def test_no_redirect(self):
        self.assertIsNone(lg.NoRedirect().redirect_request(None, None, 302, "", {}, "http://x"))


class FixtureClientTests(unittest.TestCase):
    def test_by_id_and_queue(self):
        client = lg.FixtureClient(rows=[{"id": "a", "response": "A"},
                                        {"response": "B"}])
        self.assertEqual(client.complete("p", request_id="a")["text"], "A")
        self.assertEqual(client.complete("p", request_id="zzz")["text"], "B")
        with self.assertRaises(lg.CallFailure):
            client.complete("p", request_id="zzz")

    def test_live_with_fixture_writes_raw_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.jsonl"
            fixture = Path(tmp) / "fixture.jsonl"
            fixture.write_text(json.dumps({"id": "luna-risk_harm-0000",
                                           "response": simple_response(),
                                           "finish_reason": "length"}, ensure_ascii=False) +
                               chr(10), encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = lg.main(["--live", "--limit", "1", "--raw-out", str(raw),
                                "--calls-log", str(Path(tmp) / "calls.jsonl"),
                                "--domains", "risk_harm", "--fixture", str(fixture),
                                "--created-at", FIXED_TIME])
            self.assertEqual(code, 0)
            summary = json.loads(buffer.getvalue().strip().splitlines()[-1])
            self.assertEqual(summary["ok"], 1)
            row = json.loads(raw.read_text(encoding="utf-8").strip())
            self.assertEqual(row["id"], "luna-risk_harm-0000")
            self.assertEqual(row["finish_reason"], "length")
            self.assertEqual(row["domain"], "risk_harm")
            self.assertTrue(row["prompt"])
            self.assertEqual(row["created_at"], FIXED_TIME)

    def test_failed_call_is_recorded_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.jsonl"
            empty_fixture = Path(tmp) / "empty.jsonl"
            empty_fixture.write_text("", encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = lg.main(["--live", "--limit", "1", "--raw-out", str(raw),
                                "--domains", "risk_harm", "--fixture", str(empty_fixture)])
            self.assertEqual(code, 1)
            row = json.loads(raw.read_text(encoding="utf-8").strip())
            self.assertIsNone(row["response"])
            self.assertIn("error", row)


class SecretHygieneTests(unittest.TestCase):
    def test_key_is_never_written_to_outputs(self):
        secret = "sk-do-not-leak-123"

        class StubClient:
            def __init__(self, **kwargs):
                self.api_key = kwargs.get("api_key")
                self.model = kwargs.get("model") or "stub-model"

            def complete(self, prompt, request_id=None, max_tokens=None):
                return {"text": simple_response(), "finish_reason": "stop",
                        "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3,
                                  "cost_usd": None},
                        "latency_ms": 1.0, "attempts": 1, "status_code": 200,
                        "request_sha256": "digest", "model": self.model, "route": "luna"}

        with tempfile.TemporaryDirectory() as tmp:
            key_file = Path(tmp) / "key.txt"
            key_file.write_text(secret, encoding="utf-8")
            raw = Path(tmp) / "raw.jsonl"
            calls = Path(tmp) / "calls.jsonl"
            with mock.patch.object(lg, "LunaClient", StubClient):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = lg.main(["--live", "--limit", "1", "--raw-out", str(raw),
                                    "--calls-log", str(calls), "--domains", "risk_harm",
                                    "--key-file", str(key_file)])
            self.assertEqual(code, 0)
            for path in (raw, calls):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(secret, text)
            log_row = json.loads(calls.read_text(encoding="utf-8").strip())
            self.assertEqual(log_row["key_fingerprint"], lg.fingerprint(secret))
            self.assertNotEqual(log_row["key_fingerprint"], secret)


class EndToEndTests(unittest.TestCase):
    def test_fixture_generation_then_cleaning(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            raw = tmpdir / "raw.jsonl"
            items = tmpdir / "items.jsonl"
            rejects = tmpdir / "rejects.jsonl"
            fixture = tmpdir / "fixture.jsonl"
            fixture.write_text(json.dumps({"response": simple_response()}, ensure_ascii=False) +
                               chr(10), encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = lg.main(["--live", "--limit", "1", "--raw-out", str(raw),
                                "--domains", "risk_harm", "--fixture", str(fixture),
                                "--created-at", FIXED_TIME])
            self.assertEqual(code, 0)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = lc.main(["--input", str(raw), "--items", str(items),
                                "--rejects", str(rejects), "--created-at", FIXED_TIME])
            self.assertEqual(code, 0)
            summary = json.loads(buffer.getvalue().strip().splitlines()[-1])
            self.assertEqual(summary["items"], 1)
            self.assertEqual(summary["rows_without_output"], 0)
            item = json.loads(items.read_text(encoding="utf-8").strip())
            self.assertTrue(item["id"].startswith("db-luna-"))
            self.assertEqual(item["domain"], "risk_harm")
            self.assertIn("not_ground_truth", item["meta"]["quality_flags"])

    def test_taxonomy_gate_accepts_generated_item(self):
        module, _domains, _source = lc.open_taxonomy()
        if module is None:
            self.skipTest("taxonomy.py 不可用")
        taxonomy = lg.load_taxonomy()
        keys = [spec["key"] for spec in taxonomy.domains["risk_harm"]]
        response_text = json.dumps({"items": [{
            "state": "邻居在公共区域堆放杂物，你打算先沟通。", "lang": "zh",
            "questions": module.build_questions("risk_harm", keys),
            "targets": {"contains_harm": {"answer": False}}}]}, ensure_ascii=False)
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.jsonl"
            raw.write_text(json.dumps({"id": "luna-risk_harm-0000", "domain": "risk_harm",
                                       "response": response_text}, ensure_ascii=False) + chr(10),
                           encoding="utf-8")
            items = Path(tmp) / "items.jsonl"
            rejects = Path(tmp) / "rejects.jsonl"
            with contextlib.redirect_stdout(io.StringIO()):
                code = lc.main(["--input", str(raw), "--items", str(items),
                                "--rejects", str(rejects), "--created-at", FIXED_TIME])
            self.assertEqual(code, 0)
            item = json.loads(items.read_text(encoding="utf-8").strip())
            self.assertEqual(module.item_errors(item), [])


if __name__ == "__main__":
    unittest.main()
