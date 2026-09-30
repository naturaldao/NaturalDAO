"""decision-base/ask.py 的离线测试：全部 fixture / 假 opener，不联网、不需要密钥。

    uv run --no-project --offline python -m unittest discover -s datasets/decision-base -p "test_*.py" -q

覆盖（对应 task-8 验收）：请求展平、概率归一、断点续跑、失败不写 ok、
缺参数退出码 2、密钥不落盘、契约 2.2 校验、report/verify。
"""
from __future__ import annotations

import email.message
import io
import json
import socket
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ask  # noqa: E402

SENTINEL_KEY = "sk-SECRET-sentinel-0123456789-do-not-persist"
JEV_ENDPOINT = "https://jev.example.invalid/v1/answers"


def noul(prompt="是否具有伤害倾向？"):
    return {"key": "harmful", "kind": "noul", "prompt": prompt,
            "options": [{"key": "yes", "label": "是"}, {"key": "no", "label": "否"}]}


def choice(prompt="最合适的第一步动作？"):
    return {"key": "action", "kind": "choice", "prompt": prompt,
            "options": [{"key": "allow", "label": "允许"}, {"key": "repair", "label": "修复"},
                        {"key": "block", "label": "阻止"}]}


def score(prompt="潜在伤害分级？"):
    return {"key": "severity", "kind": "score", "prompt": prompt,
            "scale": {"min": 0, "max": 3, "labels": {"0": "无", "1": "轻", "2": "中", "3": "重"}}}


def item(item_id, domain="decision_mechanics", lang="zh", questions=None, state="情境文本"):
    return {"id": item_id, "domain": domain, "lang": lang, "state": state,
            "questions": questions if questions is not None else [noul(), choice(), score()]}


ITEMS = [
    item("db-t00000001", questions=[choice(), noul(), score()]),
    item("db-t00000002", domain="risk_harm", lang="en", state="English state",
         questions=[noul("Does this create harm?")]),
    item("db-t00000003", domain="knowledge_reasoning", questions=[choice("选哪个？")]),
]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status = status
        self._body = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.headers = headers or {}

    def read(self, size=-1):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    """按顺序回放响应；元素可以是 FakeResponse / Exception / callable(request)。"""

    def __init__(self, responses=()):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append({"url": request.full_url, "headers": dict(request.headers),
                              "body": request.data, "timeout": timeout})
        if not self.responses:
            raise AssertionError("unexpected HTTP call: " + request.full_url)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            item = item(request)
        if isinstance(item, Exception):
            raise item
        return item

    def header(self, index, name):
        for key, value in self.requests[index]["headers"].items():
            if key.lower() == name.lower():
                return value
        return None

    def body(self, index):
        return json.loads(self.requests[index]["body"].decode("utf-8"))


def http_error(code, body=b"", headers=None):
    message = email.message.Message()
    for key, value in (headers or {}).items():
        message[key] = value
    payload = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    return urllib.error.HTTPError("http://x", code, "err", message, io.BytesIO(payload))


def run_cli(argv, deps=None):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = ask.main(argv, deps=deps)
    return code, out.getvalue(), err.getvalue()


def last_json(text):
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return json.loads(lines[-1])


class BaseCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="dbask-test-")
        self.tmp = Path(self._tmp.name)
        self.items = write_jsonl(self.tmp / "items.jsonl", ITEMS)

    def tearDown(self):
        self._tmp.cleanup()

    def run_fixture(self, extra=(), out=None, items=None):
        argv = ["run", "--items", str(items or self.items), "--out", str(out or self.tmp),
                "--backend", "fixture", "--quiet", *extra]
        return run_cli(argv)

    def answers(self, source="fixture", out=None):
        return read_jsonl((Path(out) if out else self.tmp) / f"answers.{source}.jsonl")


# ------------------------------------------------------------------ 请求展平

class FlattenTests(BaseCase):
    def test_plan_rows_carry_qid_state_question_options(self):
        code, out, _ = run_cli(["plan", "--items", str(self.items), "--out", str(self.tmp / "requests.jsonl")])
        self.assertEqual(code, 0)
        rows = read_jsonl(self.tmp / "requests.jsonl")
        self.assertEqual([row["qid"] for row in rows],
                         ["db-t00000001.action", "db-t00000001.harmful", "db-t00000001.severity",
                          "db-t00000002.harmful", "db-t00000003.action"])
        first = rows[0]
        self.assertEqual(first["state"], "情境文本")
        self.assertEqual(first["question"], "最合适的第一步动作？")
        self.assertEqual([option["key"] for option in first["options"]], ["allow", "repair", "block"])
        self.assertEqual(first["kind"], "choice")
        self.assertEqual(first["domain"], "decision_mechanics")
        self.assertEqual(rows[2]["scale"]["max"], 3)
        self.assertNotIn("options", rows[2])
        self.assertEqual(last_json(out)["requests_count"], 5)

    def test_selection_filters(self):
        code, out, _ = run_cli(["plan", "--items", str(self.items), "--out", str(self.tmp / "r.jsonl"),
                                "--keys", "action", "--domains", "decision_mechanics"])
        self.assertEqual(code, 0)
        self.assertEqual([row["qid"] for row in read_jsonl(self.tmp / "r.jsonl")],
                         ["db-t00000001.action"])
        code, _, _ = run_cli(["plan", "--items", str(self.items), "--out", str(self.tmp / "r2.jsonl"),
                              "--limit", "2"])
        self.assertEqual(code, 0)
        self.assertEqual(len(read_jsonl(self.tmp / "r2.jsonl")), 2)

    def test_duplicate_qid_rejected(self):
        rows = [item("db-x00000001", questions=[noul()]), item("db-x00000001", questions=[noul()])]
        path = write_jsonl(self.tmp / "dup.jsonl", rows)
        code, _, err = run_cli(["plan", "--items", str(path), "--out", str(self.tmp / "r.jsonl")])
        self.assertEqual(code, 2)
        self.assertIn("duplicate qid", err)

    def test_malformed_questions_rejected(self):
        cases = {
            "noul keys": item("db-x00000002", questions=[{"key": "k", "kind": "noul", "prompt": "p",
                                                          "options": [{"key": "yes", "label": "是"},
                                                                      {"key": "maybe", "label": "也许"}]}]),
            "requires options": item("db-x00000003", questions=[{"key": "k", "kind": "choice", "prompt": "p"}]),
            "requires scale": item("db-x00000004", questions=[{"key": "k", "kind": "score", "prompt": "p"}]),
            "empty questions": {"id": "db-x00000005", "domain": "d", "lang": "zh", "state": "s",
                                "questions": []},
        }
        for label, rows in cases.items():
            with self.subTest(label):
                path = write_jsonl(self.tmp / "bad.jsonl", [rows])
                code, _, _ = run_cli(["plan", "--items", str(path), "--out", str(self.tmp / "r.jsonl")])
                self.assertEqual(code, 2)

    def test_choice_option_cap(self):
        options = [{"key": f"k{index}", "label": f"L{index}"} for index in range(17)]
        rows = [item("db-x00000006", questions=[{"key": "k", "kind": "choice", "prompt": "p",
                                                 "options": options}])]
        path = write_jsonl(self.tmp / "cap.jsonl", rows)
        code, _, err = run_cli(["plan", "--items", str(path), "--out", str(self.tmp / "r.jsonl")])
        self.assertEqual(code, 2)
        self.assertIn("16", err)


# ------------------------------------------------------------------ 概率与答案收敛

class OutcomeTests(BaseCase):
    def q(self, kind="choice"):
        return {"qid": "db-t00000001.action", "id": "db-t00000001", "key": "action", "kind": kind,
                "state": "s", "question": "q", "options": choice()["options"]} if kind == "choice" else \
               {"qid": "db-t00000001.severity", "id": "db-t00000001", "key": "severity", "kind": "score",
                "state": "s", "question": "q", "scale": score()["scale"]}

    def test_probs_normalized(self):
        outcome = ask.resolve_outcome({"answer": "allow", "probs": {"allow": 2, "repair": 2, "block": 4}},
                                      self.q())
        self.assertEqual(outcome["execution_status"], "ok")
        self.assertAlmostEqual(sum(outcome["probs"].values()), 1.0)
        self.assertAlmostEqual(outcome["probs"]["block"], 0.5)

    def test_answer_derived_from_probs_argmax(self):
        outcome = ask.resolve_outcome({"probs": {"allow": 1, "repair": 9, "block": 1}}, self.q())
        self.assertEqual(outcome["answer"], "repair")
        self.assertTrue(outcome["flags"]["answer_from_probs"])

    def test_probs_key_mismatch_dropped_answer_kept(self):
        outcome = ask.resolve_outcome({"answer": "allow", "probs": {"yes": 1, "no": 1}}, self.q())
        self.assertEqual(outcome["execution_status"], "ok")
        self.assertEqual(outcome["answer"], "allow")
        self.assertIsNone(outcome["probs"])
        self.assertTrue(outcome["flags"]["probs_dropped"])

    def test_negative_probs_dropped(self):
        outcome = ask.resolve_outcome({"answer": "allow", "probs": {"allow": -1, "repair": 2, "block": 1}},
                                      self.q())
        self.assertEqual(outcome["execution_status"], "ok")
        self.assertIsNone(outcome["probs"])

    def test_invalid_answer_marks_invalid(self):
        outcome = ask.resolve_outcome({"answer": "maybe"}, self.q())
        self.assertEqual(outcome["execution_status"], "invalid")
        self.assertIsNone(outcome["answer"])
        self.assertIsNone(outcome["probs"])

    def test_label_and_case_folded_coercion(self):
        outcome = ask.resolve_outcome({"answer": "修复"}, self.q())
        self.assertEqual(outcome["answer"], "repair")
        outcome = ask.resolve_outcome({"answer": "REPAIR"}, self.q())
        self.assertEqual(outcome["answer"], "repair")

    def test_score_coercion(self):
        self.assertEqual(ask.resolve_outcome({"answer": 2.0}, self.q("score"))["answer"], 2)
        self.assertEqual(ask.resolve_outcome({"answer": "2"}, self.q("score"))["answer"], 2)
        self.assertEqual(ask.resolve_outcome({"answer": 4}, self.q("score"))["execution_status"], "invalid")
        self.assertEqual(ask.resolve_outcome({"answer": 1.5}, self.q("score"))["execution_status"], "invalid")

    def test_score_probs_keys_are_scale_labels(self):
        outcome = ask.resolve_outcome({"probs": {"0": 1, "1": 3, "2": 3, "3": 0}}, self.q("score"))
        self.assertEqual(outcome["answer"], 1)
        self.assertAlmostEqual(sum(outcome["probs"].values()), 1.0)

    def test_non_dict_raw_is_invalid(self):
        self.assertEqual(ask.resolve_outcome("yes", self.q())["execution_status"], "invalid")
        self.assertEqual(ask.resolve_outcome(None, self.q())["execution_status"], "invalid")

    def test_build_row_failure_has_null_answer_and_no_probs(self):
        request = self.q()
        row = ask.build_answer_row(request, "jev-1.13", "1.13", ask.failure_outcome("timeout", "boom"))
        self.assertIsNone(row["answer"])
        self.assertNotIn("probs", row)
        self.assertEqual(row["execution_status"], "timeout")
        ask.validate_answer_row(row, question=request)

    def test_contract_fields_present(self):
        request = self.q()
        row = ask.build_answer_row(request, "jev-1.13", "1.13",
                                   ask.resolve_outcome({"answer": "allow"}, request))
        self.assertEqual(set(row), set(ask.ANSWER_REQUIRED))
        self.assertEqual(row["qid"], "db-t00000001.action")
        self.assertEqual(row["id"], "db-t00000001")
        self.assertEqual(row["key"], "action")
        self.assertEqual(row["kind"], "choice")
        ask.validate_answer_row(row, question=request)

    def test_contract_rejects_bad_rows(self):
        request = self.q()
        row = ask.build_answer_row(request, "jev-1.13", "1.13",
                                   ask.resolve_outcome({"answer": "allow"}, request))
        bad = dict(row)
        bad["answer"] = "nope"
        with self.assertRaises(ValueError):
            ask.validate_answer_row(bad, question=request)
        bad = dict(row)
        bad["latency_ms"] = -1
        with self.assertRaises(ValueError):
            ask.validate_answer_row(bad, question=request)
        bad = dict(row)
        bad["source"] = "../evil"
        with self.assertRaises(ValueError):
            ask.validate_answer_row(bad, question=request)
        bad = dict(row)
        bad["execution_status"] = "ok"
        bad["answer"] = None
        with self.assertRaises(ValueError):
            ask.validate_answer_row(bad, question=request)


# ------------------------------------------------------------------ 断点续跑 / 失败重跑

class ResumeTests(BaseCase):
    def test_fixture_run_writes_contract_answers(self):
        code, out, _ = self.run_fixture()
        self.assertEqual(code, 0)
        rows = self.answers()
        questions = {request["qid"]: request for request in ask.load_requests(self.items)[0]}
        self.assertEqual(len(rows), 5)
        for row in rows:
            ask.validate_answer_row(row, question=questions[row["qid"]])
            self.assertEqual(row["execution_status"], "ok")
            self.assertEqual(row["source"], "fixture")
        self.assertEqual(last_json(out)["ok_selected"], 5)
        self.assertEqual(last_json(out)["remaining_not_ok"], 0)

    def test_resume_skips_ok(self):
        self.assertEqual(self.run_fixture()[0], 0)
        before = {row["qid"]: row for row in self.answers()}
        code, out, _ = self.run_fixture()
        self.assertEqual(code, 0)
        summary = last_json(out)
        self.assertEqual(summary["attempted"], 0)
        self.assertEqual(summary["skipped_ok"], 5)
        after = {row["qid"]: row for row in self.answers()}
        self.assertEqual(before, after)

    def test_failures_skipped_by_default_then_retried(self):
        code, out, _ = self.run_fixture(["--fixture-fail-rate", "0.6"])
        self.assertEqual(code, 1)
        summary = last_json(out)
        self.assertGreater(summary["new_failures"]["timeout"] + summary["new_failures"]["error"], 0)
        failed = [row for row in self.answers() if row["execution_status"] != "ok"]
        self.assertTrue(failed)
        for row in failed:
            self.assertIsNone(row["answer"])
            self.assertNotIn("probs", row)
        code, out, _ = self.run_fixture(["--fixture-fail-rate", "0.6"])
        summary = last_json(out)
        self.assertEqual(summary["attempted"], 0)
        self.assertEqual(summary["skipped_failed"], len(failed))
        self.assertIn("--retry-failed", summary["hint"])
        self.assertEqual(code, 1)  # 选中范围内仍有非 ok：退出 1，不假装跑完
        code, out, _ = self.run_fixture(["--retry-failed"])
        self.assertEqual(code, 0)
        summary = last_json(out)
        self.assertEqual(summary["attempted"], len(failed))
        self.assertEqual(summary["remaining_not_ok"], 0)
        rows = self.answers()
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["execution_status"] == "ok" for row in rows))

    def test_interrupt_keeps_finished_rows_and_resumes(self):
        original_wait = ask.wait
        state = {"calls": 0}

        def fake_wait(futures, return_when=None):
            state["calls"] += 1
            if state["calls"] == 2:
                raise KeyboardInterrupt()
            return original_wait(futures, return_when=return_when)

        ask.wait = fake_wait
        try:
            code, out, err = self.run_fixture()
        finally:
            ask.wait = original_wait
        self.assertEqual(code, 1)
        self.assertIn("interrupted", err)
        kept = self.answers()
        self.assertGreaterEqual(len(kept), 1)          # 已完成的行已落盘（journal → answers）
        self.assertTrue(all(row["execution_status"] == "ok" for row in kept))
        code, out, _ = self.run_fixture()              # 重跑同一条命令即可续跑
        self.assertEqual(code, 0)
        summary = last_json(out)
        self.assertEqual(summary["skipped_ok"], len(kept))
        self.assertEqual(summary["attempted"], 5 - len(kept))
        self.assertEqual(len(self.answers()), 5)

    def test_journal_resume_without_answers_file(self):
        self.assertEqual(self.run_fixture()[0], 0)
        (self.tmp / "answers.fixture.jsonl").unlink()
        code, out, _ = self.run_fixture()
        self.assertEqual(code, 0)
        self.assertEqual(last_json(out)["attempted"], 0)
        self.assertEqual(last_json(out)["skipped_ok"], 5)
        self.assertEqual(len(self.answers()), 5)

    def test_retry_collapses_to_one_row_per_qid(self):
        self.run_fixture(["--fixture-fail-rate", "0.6"])
        self.run_fixture(["--retry-failed"])
        rows = self.answers()
        qids = [row["qid"] for row in rows]
        self.assertEqual(len(qids), len(set(qids)))
        self.assertEqual(len(rows), 5)

    def test_compaction_preserves_rows_outside_limit(self):
        self.assertEqual(self.run_fixture()[0], 0)
        self.assertEqual(len(self.answers()), 5)
        code, out, _ = self.run_fixture(["--limit", "2", "--retry-failed"])
        self.assertEqual(code, 0)
        self.assertEqual(last_json(out)["selected"], 2)
        self.assertEqual(len(self.answers()), 5)  # 未选中的行不能被压缩掉

    def test_invalid_existing_answer_file_exits_2(self):
        self.run_fixture()
        path = self.tmp / "answers.fixture.jsonl"
        rows = read_jsonl(path)
        rows[0]["answer"] = "not-an-option"
        write_jsonl(path, rows)
        code, _, err = self.run_fixture()
        self.assertEqual(code, 2)
        self.assertIn("answer", err)


# ------------------------------------------------------------------ 失败分类与不写 ok

class FailureTests(BaseCase):
    def test_backend_crash_is_not_ok(self):
        original = ask.FixtureBackend.execute

        def boom(self, unit):
            raise RuntimeError("simulated crash")

        ask.FixtureBackend.execute = boom
        try:
            code, out, _ = self.run_fixture()
        finally:
            ask.FixtureBackend.execute = original
        self.assertEqual(code, 1)
        rows = self.answers()
        self.assertTrue(all(row["execution_status"] == "error" for row in rows))
        self.assertTrue(all(row["answer"] is None for row in rows))

    def test_http_500_retried_then_ok(self):
        opener = FakeOpener([http_error(500, "boom"),
                             FakeResponse(200, jev_body({"db-t00000001.action": {"answer": "allow",
                                                                                 "probs": {"allow": 1,
                                                                                           "repair": 3,
                                                                                           "block": 0}}}))])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, _ = run_cli(self.jev_argv(limit="1"), deps=deps)
        self.assertEqual(code, 0)
        self.assertEqual(len(opener.requests), 2)
        rows = self.answers("jev-1.13")
        self.assertEqual([row["qid"] for row in rows], ["db-t00000001.action"])
        self.assertEqual(rows[0]["answer"], "allow")
        self.assertAlmostEqual(rows[0]["probs"]["repair"], 0.75)
        log = read_jsonl(self.tmp / "calls.jev-1.13.jsonl")
        attempts = [row for row in log if row["phase"] == "attempt"]
        self.assertEqual([row["status_code"] for row in attempts], [500, 200])
        self.assertEqual(attempts[1]["retries"], 1)

    def test_http_401_not_retried(self):
        opener = FakeOpener([http_error(401, "nope")])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, out, _ = run_cli(self.jev_argv(limit="1"), deps=deps)
        self.assertEqual(code, 1)
        self.assertEqual(len(opener.requests), 1)
        rows = self.answers("jev-1.13")
        self.assertEqual(rows[0]["execution_status"], "error")
        self.assertIsNone(rows[0]["answer"])
        self.assertEqual(last_json(out)["remaining_not_ok"], 1)

    def test_timeout_classified(self):
        opener = FakeOpener([socket.timeout("timed out"), socket.timeout("timed out"),
                             socket.timeout("timed out")])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, _ = run_cli(self.jev_argv(limit="1"), deps=deps)
        self.assertEqual(code, 1)
        rows = self.answers("jev-1.13")
        self.assertEqual(rows[0]["execution_status"], "timeout")
        self.assertIsNone(rows[0]["answer"])
        self.assertEqual(len(opener.requests), 3)
        log = read_jsonl(self.tmp / "calls.jev-1.13.jsonl")
        self.assertEqual([row["failure_kind"] for row in log if row["phase"] == "attempt"],
                         ["timeout", "timeout", "timeout"])

    def test_jev_missing_qid_and_unknown_shape_are_invalid(self):
        others = jev_body({"db-t00000002.harmful": {"answer": "yes"}})
        opener = FakeOpener([FakeResponse(200, others), FakeResponse(200, {"unexpected": True})])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, _ = run_cli(self.jev_argv(limit="1"), deps=deps)
        self.assertEqual(code, 1)
        rows = self.answers("jev-1.13")
        self.assertEqual(rows[0]["qid"], "db-t00000001.action")
        self.assertEqual(rows[0]["execution_status"], "invalid")
        self.assertIsNone(rows[0]["answer"])
        code, _, _ = run_cli(self.jev_argv(limit="1", extra=["--retry-failed"]), deps=deps)
        self.assertEqual(code, 1)
        rows = self.answers("jev-1.13")
        self.assertEqual(rows[0]["execution_status"], "invalid")
        log = read_jsonl(self.tmp / "calls.jev-1.13.jsonl")
        reasons = [row["failure_reason"] for row in log if row["phase"] == "outcome"]
        self.assertTrue(any("missing qid" in reason for reason in reasons))
        self.assertTrue(any("unrecognized Jev response" in reason for reason in reasons))

    def test_jev_list_shape_accepted(self):
        body = {"answers": [{"qid": "db-t00000001.action", "answer": "repair",
                             "probs": {"allow": 3, "repair": 1, "block": 0}},
                            {"qid": "db-t00000003.action", "answer": "allow"}]}
        opener = FakeOpener([FakeResponse(200, body)])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, _ = run_cli(self.jev_argv(limit="1"), deps=deps)
        self.assertEqual(code, 0)
        rows = self.answers("jev-1.13")
        self.assertEqual(rows[0]["answer"], "repair")
        self.assertAlmostEqual(sum(rows[0]["probs"].values()), 1.0)

    def test_batch_size_packs_multiple_qids_per_request(self):
        body = jev_body({"db-t00000001.action": {"answer": "allow"},
                         "db-t00000001.harmful": {"answer": "no"}})
        opener = FakeOpener([FakeResponse(200, body)])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, out, _ = run_cli(self.jev_argv(limit="2", extra=["--batch-size", "2"]), deps=deps)
        self.assertEqual(code, 0)
        self.assertEqual(len(opener.requests), 1)
        payload = opener.body(0)
        self.assertEqual([item["qid"] for item in payload["requests"]],
                         ["db-t00000001.action", "db-t00000001.harmful"])
        by_qid = {row["qid"]: row for row in self.answers("jev-1.13")}
        self.assertEqual(by_qid["db-t00000001.action"]["answer"], "allow")
        self.assertEqual(by_qid["db-t00000001.harmful"]["answer"], "no")
        summary = last_json(out)
        self.assertEqual(summary["call_summary"]["batches"], 1)

    def test_unknown_qid_in_response_ignored_but_logged(self):
        body = {"answers": {"db-t00000002.harmful": {"answer": "yes"}, "db-zzz.other": {"answer": "x"}}}
        opener = FakeOpener([FakeResponse(200, body)])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, _ = run_cli(self.jev_argv(limit="1", domains="risk_harm"), deps=deps)
        self.assertEqual(code, 0)
        log = read_jsonl(self.tmp / "calls.jev-1.13.jsonl")
        batches = [row for row in log if row["phase"] == "batch"]
        self.assertEqual(batches[0]["unknown_qids"], ["db-zzz.other"])

    # -- helpers -----------------------------------------------------------
    def jev_argv(self, limit=None, domains=None, extra=()):
        argv = ["run", "--items", str(self.items), "--out", str(self.tmp), "--backend", "jev", "--live",
                "--endpoint", JEV_ENDPOINT, "--api-version", "1.13", "--integration-confirmed",
                "--workers", "1", "--quiet", *extra]
        if limit:
            argv += ["--limit", limit]
        if domains:
            argv += ["--domains", domains]
        return argv


def jev_body(payload):
    return {"answers": payload}


# ------------------------------------------------------------------ 配置与退出码 2

class ConfigTests(BaseCase):
    def jev_argv(self, extra=(), live=True):
        argv = ["run", "--items", str(self.items), "--out", str(self.tmp), "--backend", "jev"]
        if live:
            argv.append("--live")
        return argv + list(extra)

    def test_jev_live_missing_endpoint(self):
        deps = ask.Deps(opener=FakeOpener([]), sleeper=lambda seconds: None,
                        environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, err = run_cli(self.jev_argv(["--api-version", "1.13", "--integration-confirmed"]), deps)
        self.assertEqual(code, 2)
        self.assertIn("endpoint", err)

    def test_jev_live_missing_version(self):
        deps = ask.Deps(opener=FakeOpener([]), sleeper=lambda seconds: None,
                        environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, err = run_cli(self.jev_argv(["--endpoint", JEV_ENDPOINT, "--integration-confirmed"]), deps)
        self.assertEqual(code, 2)
        self.assertIn("--api-version", err)

    def test_jev_live_missing_key(self):
        deps = ask.Deps(opener=FakeOpener([]), sleeper=lambda seconds: None, environ={})
        code, _, err = run_cli(self.jev_argv(["--endpoint", JEV_ENDPOINT, "--api-version", "1.13",
                                              "--integration-confirmed"]), deps)
        self.assertEqual(code, 2)
        self.assertIn("JEV_API_KEY", err)

    def test_jev_live_missing_integration_confirmed(self):
        deps = ask.Deps(opener=FakeOpener([]), sleeper=lambda seconds: None,
                        environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, err = run_cli(self.jev_argv(["--endpoint", JEV_ENDPOINT, "--api-version", "1.13"]), deps)
        self.assertEqual(code, 2)
        self.assertIn("integration-confirmed", err)
        self.assertEqual(len(deps.opener.requests), 0)

    def test_jev_dry_run_needs_endpoint_but_no_key(self):
        deps = ask.Deps(opener=FakeOpener([]), sleeper=lambda seconds: None, environ={})
        code, _, err = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                                "--backend", "jev", "--api-version", "1.13"], deps=deps)
        self.assertEqual(code, 2)
        self.assertIn("endpoint", err)
        code, out, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                                "--backend", "jev", "--endpoint", JEV_ENDPOINT,
                                "--api-version", "1.13"], deps=deps)
        self.assertEqual(code, 0)
        self.assertEqual(last_json(out)["mode"], "dry-run")
        self.assertEqual(len(deps.opener.requests), 0)
        plan = read_jsonl(self.tmp / "requests.jev-1.13.jsonl")
        self.assertEqual(len(plan), 5)
        self.assertEqual(plan[0]["body"]["api_version"], "1.13")
        self.assertEqual(len(plan[0]["body"]["requests"]), 1)
        self.assertEqual(plan[0]["body"]["requests"][0]["question"], "最合适的第一步动作？")

    def test_fixture_rejects_live_and_foreign_source(self):
        code, _, err = self.run_fixture(["--live"])
        self.assertEqual(code, 2)
        self.assertIn("fixture", err)
        code, _, err = self.run_fixture(["--source", "jev-1.13"])
        self.assertEqual(code, 2)
        self.assertIn("fixture", err)

    def test_missing_items_file(self):
        code, _, err = run_cli(["plan", "--items", str(self.tmp / "nope.jsonl"),
                                "--out", str(self.tmp / "r.jsonl")])
        self.assertEqual(code, 2)
        self.assertIn("nope.jsonl", err)

    def test_openai_compatible_requires_model_and_base_url(self):
        deps = ask.Deps(opener=FakeOpener([]), sleeper=lambda seconds: None, environ={})
        argv = ["run", "--items", str(self.items), "--out", str(self.tmp),
                "--backend", "openai-compatible", "--live", "--base-url", "https://api.example.invalid/v1",
                "--source", "grok-4.7"]
        code, _, err = run_cli(argv, deps=deps)
        self.assertEqual(code, 2)
        self.assertIn("model", err)
        argv = ["run", "--items", str(self.items), "--out", str(self.tmp),
                "--backend", "openai-compatible", "--live", "--model", "m", "--source", "grok-4.7"]
        code, _, err = run_cli(argv, deps=deps)
        self.assertEqual(code, 2)
        self.assertIn("base-url", err)

    def test_workers_and_endpoint_validation(self):
        deps = ask.Deps(opener=FakeOpener([]), sleeper=lambda seconds: None,
                        environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, err = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                                "--backend", "fixture", "--workers", "0"], deps=deps)
        self.assertEqual(code, 2)
        self.assertIn("workers", err)
        code, _, err = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                                "--backend", "jev", "--live", "--endpoint", "http://jev.example.invalid/x",
                                "--api-version", "1", "--integration-confirmed"], deps=deps)
        self.assertEqual(code, 2)
        self.assertIn("HTTP", err)

    def test_unknown_backend_and_command_exit_2(self):
        with self.assertRaises(SystemExit) as caught:
            run_cli(["run", "--items", str(self.items), "--out", str(self.tmp), "--backend", "nope"])
        self.assertEqual(caught.exception.code, 2)

    def test_report_missing_calls_file(self):
        code, _, err = run_cli(["report", "--calls", str(self.tmp / "nope.jsonl")])
        self.assertEqual(code, 2)
        self.assertIn("call log", err)


# ------------------------------------------------------------------ 密钥不落盘

class SecretTests(BaseCase):
    def test_key_never_written_anywhere(self):
        opener = FakeOpener([FakeResponse(200, jev_body({"db-t00000002.harmful": {"answer": "yes"}}))
                             for _ in range(5)])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, out, err = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                                  "--backend", "jev", "--live", "--endpoint", JEV_ENDPOINT,
                                  "--api-version", "1.13", "--integration-confirmed", "--workers", "1",
                                  "--quiet"], deps=deps)
        self.assertEqual(code, 1)  # 4 条响应里没有对应 qid → invalid；密钥仍不许落盘
        code_dry, _, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                                  "--backend", "jev", "--endpoint", JEV_ENDPOINT,
                                  "--api-version", "1.13"], deps=deps)
        self.assertEqual(code_dry, 0)
        files = [path for path in self.tmp.rglob("*") if path.is_file()]
        self.assertTrue(files)
        for path in files:
            content = path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn(SENTINEL_KEY, content, f"secret leaked into {path.name}")
        self.assertNotIn(SENTINEL_KEY, out)
        self.assertNotIn(SENTINEL_KEY, err)
        log = read_jsonl(self.tmp / "calls.jev-1.13.jsonl")
        attempts = [row for row in log if row["phase"] == "attempt"]
        self.assertTrue(attempts)
        for row in attempts:
            self.assertEqual(row["key_fingerprint"], ask.fingerprint(SENTINEL_KEY))
        self.assertEqual(opener.header(0, "authorization"), "Bearer " + SENTINEL_KEY)

    def test_key_file_refs_supported(self):
        key_file = self.tmp / "credentials.yaml"
        key_file.write_text("refs:\n  JEV_API_KEY: " + SENTINEL_KEY + "\n", encoding="utf-8")
        opener = FakeOpener([FakeResponse(200, jev_body({"db-t00000002.harmful": {"answer": "yes"}}))])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={})
        code, _, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                              "--backend", "jev", "--live", "--endpoint", JEV_ENDPOINT,
                              "--api-version", "1.13", "--integration-confirmed", "--key-file",
                              str(key_file), "--domains", "risk_harm"], deps=deps)
        self.assertEqual(code, 0)
        self.assertEqual(opener.header(0, "authorization"), "Bearer " + SENTINEL_KEY)
        log = read_jsonl(self.tmp / "calls.jev-1.13.jsonl")
        origins = [row.get("key_source") for row in log if row.get("key_source")]
        self.assertTrue(origins)
        for origin in origins:
            self.assertTrue(origin.startswith("file:"), origin)
            self.assertIn("JEV_API_KEY", origin)
        for path in self.tmp.rglob("*"):
            if path.is_file() and path.name != "credentials.yaml":
                self.assertNotIn(SENTINEL_KEY, path.read_text(encoding="utf-8", errors="replace"))


# ------------------------------------------------------------------ openai-compatible

class ChatBackendTests(BaseCase):
    def chat(self, content):
        return {"choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}

    def test_chat_backend_parses_answer(self):
        opener = FakeOpener([FakeResponse(200, self.chat('{"answer": "yes", "probs": {"yes": 3, "no": 1}}'))])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"ASK_API_KEY": "k"})
        code, out, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                                "--backend", "openai-compatible", "--live",
                                "--base-url", "https://api.example.invalid/v1", "--model", "m",
                                "--source", "grok-4.7", "--domains", "risk_harm", "--quiet"], deps=deps)
        self.assertEqual(code, 0)
        rows = self.answers("grok-4.7")
        self.assertEqual(rows[0]["answer"], "yes")
        self.assertEqual(rows[0]["source_version"], "m")
        self.assertAlmostEqual(sum(rows[0]["probs"].values()), 1.0)
        log = read_jsonl(self.tmp / "calls.grok-4.7.jsonl")
        attempt = [row for row in log if row["phase"] == "attempt"][0]
        self.assertEqual(attempt["prompt_tokens"], 10)
        self.assertEqual(attempt["total_tokens"], 15)
        self.assertEqual(opener.header(0, "authorization"), "Bearer k")
        self.assertEqual(opener.body(0)["model"], "m")

    def test_chat_json_embedded_in_prose(self):
        opener = FakeOpener([FakeResponse(200, self.chat('说明文字，下面是结果：\n{"answer": "no"}\n以上。'))])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"ASK_API_KEY": "k"})
        code, _, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                              "--backend", "openai-compatible", "--live",
                              "--base-url", "https://api.example.invalid/v1", "--model", "m",
                              "--source", "grok-4.7", "--domains", "risk_harm", "--limit", "1", "--quiet"],
                             deps=deps)
        self.assertEqual(code, 0)
        self.assertEqual(self.answers("grok-4.7")[0]["answer"], "no")

    def test_chat_reasoning_content_fallback(self):
        body = {"choices": [{"message": {"content": None, "reasoning_content": '{"answer": "yes"}'}}]}
        opener = FakeOpener([FakeResponse(200, body)])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"ASK_API_KEY": "k"})
        code, _, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                              "--backend", "openai-compatible", "--live",
                              "--base-url", "https://api.example.invalid/v1", "--model", "m",
                              "--source", "grok-4.7", "--domains", "risk_harm", "--quiet"], deps=deps)
        self.assertEqual(code, 0)
        self.assertEqual(self.answers("grok-4.7")[0]["answer"], "yes")

    def test_chat_empty_content_invalid(self):
        opener = FakeOpener([FakeResponse(200, {"choices": [{"message": {"content": ""}}]})])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"ASK_API_KEY": "k"})
        code, _, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                              "--backend", "openai-compatible", "--live",
                              "--base-url", "https://api.example.invalid/v1", "--model", "m",
                              "--source", "grok-4.7", "--domains", "risk_harm", "--quiet"], deps=deps)
        self.assertEqual(code, 1)
        self.assertEqual(self.answers("grok-4.7")[0]["execution_status"], "invalid")

    def test_json_extractor(self):
        self.assertEqual(ask.extract_json_object('prefix {"a": {"b": 1}} suffix'), {"a": {"b": 1}})
        self.assertEqual(ask.extract_json_object('{"s": "}"}'), {"s": "}"})
        with self.assertRaises(ValueError):
            ask.extract_json_object("no json here")
        with self.assertRaises(ValueError):
            ask.extract_json_object("{unbalanced")


# ------------------------------------------------------------------ 报告与核对

class ReportVerifyTests(BaseCase):
    def test_report_and_verify(self):
        self.run_fixture(["--fixture-fail-rate", "0.4"])
        calls = self.tmp / "calls.fixture.jsonl"
        answers = self.tmp / "answers.fixture.jsonl"
        code, out, _ = run_cli(["report", "--calls", str(calls), "--answers", str(answers),
                                "--items", str(self.items), "--json"])
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertEqual(report["attempts"], 5)
        self.assertEqual(report["answers_rows"], 5)
        self.assertEqual(report["coverage"]["expected"], 5)
        self.assertTrue(report["outcomes"])
        code, out, _ = run_cli(["report", "--calls", str(calls), "--answers", str(answers),
                                "--items", str(self.items)])
        self.assertEqual(code, 0)
        self.assertIn("attempts", out)
        self.assertIn("coverage", out)
        self.assertIn("top_failures", out)
        failed = [row for row in self.answers() if row["execution_status"] != "ok"]
        code, out, _ = run_cli(["verify", "--items", str(self.items), "--answers", str(answers)])
        self.assertEqual(code, 1 if failed else 0)
        self.assertIn("complete", out)
        if failed:
            self.assertIn("failed  ", out)
        code, out, _ = run_cli(["verify", "--items", str(self.items), "--answers", str(answers),
                                "--allow-incomplete"])
        self.assertEqual(code, 0)

    def test_verify_complete_and_violations(self):
        self.run_fixture()
        answers = self.tmp / "answers.fixture.jsonl"
        code, out, _ = run_cli(["verify", "--items", str(self.items), "--answers", str(answers)])
        self.assertEqual(code, 0)
        self.assertIn("complete : True", out)
        rows = read_jsonl(answers)
        rows[0]["answer"] = "not-an-option"
        write_jsonl(answers, rows)
        code, out, _ = run_cli(["verify", "--items", str(self.items), "--answers", str(answers)])
        self.assertEqual(code, 2)
        self.assertIn("violation", out)

    def test_verify_missing_answers_row(self):
        self.run_fixture()
        answers = self.tmp / "answers.fixture.jsonl"
        rows = read_jsonl(answers)[:3]
        write_jsonl(answers, rows)
        code, out, _ = run_cli(["verify", "--items", str(self.items), "--answers", str(answers)])
        self.assertEqual(code, 1)
        self.assertIn("missing=2", out)


# ------------------------------------------------------------------ 其他内部件

class InternalTests(BaseCase):
    def test_rate_limiter_spacing(self):
        state = {"now": 0.0}
        sleeps = []

        def clock():
            return state["now"]

        def sleeper(seconds):
            sleeps.append(seconds)
            state["now"] += seconds

        limiter = ask.RateLimiter(2.0, clock=clock, sleeper=sleeper)
        limiter.wait()
        limiter.wait()
        limiter.wait()
        self.assertEqual(len(sleeps), 2)
        self.assertAlmostEqual(sum(sleeps), 1.0, places=6)
        self.assertEqual(ask.RateLimiter(0.0).wait(), 0.0)

    def test_merge_rows_keeps_order_and_prior_rows(self):
        prior = [{"qid": "a", "v": 1}, {"qid": "z", "v": 1}]
        new = {"b": {"qid": "b", "v": 2}, "a": {"qid": "a", "v": 3}}
        merged = ask.merge_rows(prior, new, ["b", "a"])
        self.assertEqual([row["qid"] for row in merged], ["b", "a", "z"])
        self.assertEqual(merged[1]["v"], 3)

    def test_fingerprint_and_output_path(self):
        self.assertEqual(len(ask.fingerprint("abc")), 8)
        self.assertEqual(ask.fingerprint("abc"), ask.fingerprint("abc"))
        self.assertNotEqual(ask.fingerprint("abc"), ask.fingerprint("abd"))
        directory = self.tmp / "out"
        directory.mkdir()
        self.assertEqual(ask.resolve_output_path(directory, "jev-1.13").name, "answers.jev-1.13.jsonl")
        self.assertEqual(ask.resolve_output_path(self.tmp / "a.jsonl", "x").name, "a.jsonl")
        self.assertEqual(ask.resolve_output_path(self.tmp / "newdir", "x").name, "answers.x.jsonl")

    def test_call_summary_cost_null_without_prices(self):
        log = ask.CallLog()
        log.record({"phase": "attempt", "ok": True, "latency_ms": 10.0, "source": "s",
                    "prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5})
        summary = log.summary()
        self.assertEqual(summary["attempts"], 1)
        self.assertIsNone(summary["cost_usd"])
        self.assertEqual(summary["total_tokens"], 5)

    def test_normalize_probs_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            ask.normalize_probs({})
        with self.assertRaises(ValueError):
            ask.normalize_probs({"a": 0, "b": 0})
        with self.assertRaises(ValueError):
            ask.normalize_probs({"a": 1, "c": 1}, keys=["a", "b"])
        with self.assertRaises(ValueError):
            ask.normalize_probs({"a": True})

    def test_dry_run_writes_no_calls_file(self):
        code, _, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                              "--backend", "fixture", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertFalse((self.tmp / "calls.fixture.jsonl").exists())
        plan = read_jsonl(self.tmp / "requests.fixture.jsonl")
        self.assertEqual(len(plan), 5)


if __name__ == "__main__":
    unittest.main()
