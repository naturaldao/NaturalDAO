"""decision-base/ask.py 的离线测试：全部 fixture / 假 opener，不联网、不需要密钥。

    uv run --no-project --offline python -m unittest discover -s datasets/decision-base -p "test_*.py" -q

两类 fixture：
1. 手搓条目一律用 taxonomy.build_questions() 生成（题型只认 taxonomy 一个真源，不再手写形状）；
2. fixtures/ask-items-sample.jsonl 是**真实 items.jsonl 的截取样本**（10 条，覆盖 noul/choice/score、
   含与不含 targets、含 options_from_state 的 next_step_candidate、含 4 问条目），
   专门防"手搓 fixture 与 convert.py 实际输出漂移"——2026-09-30 的 scale.labels 形状事故就是漂移造成的。

覆盖（对应 task-8 验收）：请求展平、概率归一、断点续跑、失败不写 ok、
缺参数退出码 2、密钥不落盘、契约 2.2 校验、report/verify、真实样本回归。
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
import taxonomy  # noqa: E402  - 题型/问题键的唯一真源

SENTINEL_KEY = "sk-SECRET-sentinel-0123456789-do-not-persist"
JEV_ENDPOINT = "https://jev.example.invalid/v1/answers"
REAL_SAMPLE = Path(__file__).resolve().parent / "fixtures" / "ask-items-sample.jsonl"

CHOICE_KEY = "action_selection"        # decision_mechanics，5 个固定选项
NOUL_KEY = "information_sufficient"    # decision_mechanics
SCORE_KEY = "risk_of_action"           # decision_mechanics，0..4
RISK_KEYS = ("contains_harm", "harm_severity", "recommended_action")


def option_keys(key):
    return list(taxonomy.key_spec(key).option_keys())


def scale_bounds(key):
    low, high, _ = taxonomy.key_spec(key).scale
    return low, high


def make_item(item_id, domain="decision_mechanics", lang="zh", keys=None, targets=None,
              state="情境文本"):
    """契约 2.1 的条目；questions 由 taxonomy.build_questions 产出，避免手写漂移。"""
    item = {"id": item_id, "domain": domain, "lang": lang, "state": state,
            "questions": taxonomy.build_questions(domain, keys, lang=lang),
            "source": {"dataset": "unit-test/fixture", "revision": "0" * 40, "config": "default",
                       "split": "train", "row": 0, "license": "cc0-1.0",
                       "url": "https://example.invalid/unit-test"},
            "meta": {"converter": "test_ask.py", "converter_version": "0.1",
                     "created_at": "2026-09-30T00:00:00+00:00", "quality_flags": []}}
    if targets is not None:
        item["targets"] = targets
    return item


ITEMS = [
    make_item("db-test-00000001", keys=[CHOICE_KEY, NOUL_KEY, SCORE_KEY]),
    make_item("db-test-00000002", domain="risk_harm", lang="en", keys=list(RISK_KEYS)),
    make_item("db-test-00000003", domain="knowledge_reasoning", lang="en",
              keys=["evidence_sufficiency"]),
]
TOTAL_REQUESTS = sum(len(item["questions"]) for item in ITEMS)


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


def request_for(key, lang="zh", domain=None):
    """按真实路径构造一条请求（经 taxonomy.build_questions → request_from_question）。"""
    spec = taxonomy.key_spec(key)
    domain = domain or spec.domains[0]
    item = make_item("db-test-00000001", domain=domain, lang=lang, keys=[key])
    return ask.request_from_question(item, item["questions"][0])


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
                         [f"db-test-00000001.{CHOICE_KEY}", f"db-test-00000001.{NOUL_KEY}",
                          f"db-test-00000001.{SCORE_KEY}", "db-test-00000002.contains_harm",
                          "db-test-00000002.harm_severity", "db-test-00000002.recommended_action",
                          "db-test-00000003.evidence_sufficiency"])
        first = rows[0]
        self.assertEqual(first["state"], "情境文本")
        self.assertEqual(first["question"], taxonomy.key_spec(CHOICE_KEY).prompt("zh"))
        self.assertEqual([option["key"] for option in first["options"]], option_keys(CHOICE_KEY))
        self.assertEqual(first["kind"], "choice")
        self.assertEqual(first["domain"], "decision_mechanics")
        low, high = scale_bounds(SCORE_KEY)
        self.assertEqual(rows[2]["scale"], {"min": low, "max": high,
                                            "labels": taxonomy.key_spec(SCORE_KEY).score_scale("zh")["labels"]})
        self.assertIsInstance(rows[2]["scale"]["labels"], list)
        self.assertNotIn("options", rows[2])
        self.assertEqual(last_json(out)["requests_count"], TOTAL_REQUESTS)
        self.assertTrue(last_json(out)["item_schema_checked"])

    def test_selection_filters(self):
        code, out, _ = run_cli(["plan", "--items", str(self.items), "--out", str(self.tmp / "r.jsonl"),
                                "--keys", CHOICE_KEY, "--domains", "decision_mechanics"])
        self.assertEqual(code, 0)
        self.assertEqual([row["qid"] for row in read_jsonl(self.tmp / "r.jsonl")],
                         [f"db-test-00000001.{CHOICE_KEY}"])
        code, _, _ = run_cli(["plan", "--items", str(self.items), "--out", str(self.tmp / "r2.jsonl"),
                              "--limit", "2"])
        self.assertEqual(code, 0)
        self.assertEqual(len(read_jsonl(self.tmp / "r2.jsonl")), 2)

    def test_duplicate_qid_rejected(self):
        rows = [make_item("db-test-00000001", keys=[NOUL_KEY]),
                make_item("db-test-00000001", keys=[NOUL_KEY])]
        path = write_jsonl(self.tmp / "dup.jsonl", rows)
        code, _, err = run_cli(["plan", "--items", str(path), "--out", str(self.tmp / "r.jsonl")])
        self.assertEqual(code, 2)
        self.assertIn("duplicate qid", err)

    def test_malformed_questions_rejected(self):
        bad_cases = {
            "noul options": {"key": "contains_harm", "kind": "noul", "prompt": "p",
                             "options": [{"key": "yes", "label": "是"}, {"key": "maybe", "label": "也许"}]},
            "choice needs options": {"key": "recommended_action", "kind": "choice", "prompt": "p"},
            "score needs scale": {"key": "harm_severity", "kind": "score", "prompt": "p"},
            "scale labels as object": {"key": "harm_severity", "kind": "score", "prompt": "p",
                                       "scale": {"min": 0, "max": 4,
                                                 "labels": {"0": "a", "1": "b", "2": "c", "3": "d", "4": "e"}}},
            "scale labels wrong length": {"key": "harm_severity", "kind": "score", "prompt": "p",
                                          "scale": {"min": 0, "max": 4, "labels": ["a", "b"]}},
            "unknown key": {"key": "not_a_real_key", "kind": "noul", "prompt": "p",
                            "options": [{"key": "yes", "label": "是"}, {"key": "no", "label": "否"}]},
        }
        for label, question in bad_cases.items():
            with self.subTest(label):
                item = make_item("db-test-00000009", domain="risk_harm", keys=[NOUL_KEY])
                item["questions"] = [question]
                path = write_jsonl(self.tmp / "bad.jsonl", [item])
                code, _, _ = run_cli(["plan", "--items", str(path), "--out", str(self.tmp / "r.jsonl")])
                self.assertEqual(code, 2)
        empty = make_item("db-test-00000010", keys=[NOUL_KEY])
        empty["questions"] = []
        path = write_jsonl(self.tmp / "empty.jsonl", [empty])
        code, _, _ = run_cli(["plan", "--items", str(path), "--out", str(self.tmp / "r.jsonl")])
        self.assertEqual(code, 2)

    def test_choice_option_cap(self):
        item = make_item("db-test-00000011", keys=[CHOICE_KEY])
        item["questions"][0]["options"] = [{"key": f"k{index}", "label": f"L{index}"}
                                           for index in range(17)]
        path = write_jsonl(self.tmp / "cap.jsonl", [item])
        code, _, err = run_cli(["plan", "--items", str(path), "--out", str(self.tmp / "r.jsonl")])
        self.assertEqual(code, 2)
        self.assertIn("16", err)

    def test_item_schema_checked_by_default_and_skippable(self):
        item = make_item("db-test-00000012", keys=[NOUL_KEY])
        del item["source"]["license"]
        path = write_jsonl(self.tmp / "noschema.jsonl", [item])
        code, _, err = run_cli(["plan", "--items", str(path), "--out", str(self.tmp / "r.jsonl")])
        self.assertEqual(code, 2)
        self.assertIn("README 2.1", err)
        code, _, _ = run_cli(["plan", "--items", str(path), "--out", str(self.tmp / "r.jsonl"),
                              "--skip-item-schema"])
        self.assertEqual(code, 0)


# ------------------------------------------------------------------ 概率与答案收敛

class OutcomeTests(BaseCase):
    def test_probs_normalized(self):
        keys = option_keys(CHOICE_KEY)
        weights = {key: 1 for key in keys}
        weights[keys[2]] = 6
        outcome = ask.resolve_outcome({"answer": keys[0], "probs": weights}, request_for(CHOICE_KEY))
        self.assertEqual(outcome["execution_status"], "ok")
        self.assertAlmostEqual(sum(outcome["probs"].values()), 1.0)
        self.assertAlmostEqual(outcome["probs"][keys[2]], 0.6)

    def test_partial_probs_normalized_and_flagged(self):
        keys = option_keys(CHOICE_KEY)
        outcome = ask.resolve_outcome({"answer": keys[0], "probs": {keys[0]: 1, keys[1]: 3}},
                                      request_for(CHOICE_KEY))
        self.assertEqual(outcome["execution_status"], "ok")
        self.assertAlmostEqual(sum(outcome["probs"].values()), 1.0)
        self.assertTrue(outcome["flags"]["probs_partial"])

    def test_answer_derived_from_probs_argmax(self):
        keys = option_keys(CHOICE_KEY)
        probs = {key: 1 for key in keys}
        probs[keys[3]] = 9
        outcome = ask.resolve_outcome({"probs": probs}, request_for(CHOICE_KEY))
        self.assertEqual(outcome["answer"], keys[3])
        self.assertTrue(outcome["flags"]["answer_from_probs"])

    def test_probs_key_outside_domain_dropped_answer_kept(self):
        keys = option_keys(CHOICE_KEY)
        outcome = ask.resolve_outcome({"answer": keys[0], "probs": {"yes": 1, "no": 1}},
                                      request_for(CHOICE_KEY))
        self.assertEqual(outcome["execution_status"], "ok")
        self.assertEqual(outcome["answer"], keys[0])
        self.assertIsNone(outcome["probs"])
        self.assertTrue(outcome["flags"]["probs_dropped"])

    def test_negative_probs_dropped(self):
        keys = option_keys(CHOICE_KEY)
        outcome = ask.resolve_outcome({"answer": keys[0],
                                       "probs": {keys[0]: -1, keys[1]: 2, keys[2]: 1}},
                                      request_for(CHOICE_KEY))
        self.assertEqual(outcome["execution_status"], "ok")
        self.assertIsNone(outcome["probs"])

    def test_invalid_answer_marks_invalid(self):
        outcome = ask.resolve_outcome({"answer": "maybe"}, request_for(CHOICE_KEY))
        self.assertEqual(outcome["execution_status"], "invalid")
        self.assertIsNone(outcome["answer"])
        self.assertIsNone(outcome["probs"])

    def test_label_and_case_folded_coercion(self):
        spec = taxonomy.key_spec(CHOICE_KEY)
        labels = {option["key"]: option["label"] for option in spec.option_pairs("zh")}
        first_key = option_keys(CHOICE_KEY)[0]
        outcome = ask.resolve_outcome({"answer": labels[first_key]}, request_for(CHOICE_KEY))
        self.assertEqual(outcome["answer"], first_key)
        self.assertTrue(outcome["flags"]["coerced"])
        outcome = ask.resolve_outcome({"answer": first_key.upper()}, request_for(CHOICE_KEY))
        self.assertEqual(outcome["answer"], first_key)

    def test_score_coercion(self):
        low, high = scale_bounds(SCORE_KEY)
        self.assertEqual(ask.resolve_outcome({"answer": low}, request_for(SCORE_KEY))["answer"], low)
        self.assertEqual(ask.resolve_outcome({"answer": float(low)}, request_for(SCORE_KEY))["answer"], low)
        self.assertEqual(ask.resolve_outcome({"answer": str(high)}, request_for(SCORE_KEY))["answer"], high)
        self.assertEqual(ask.resolve_outcome({"answer": high + 1}, request_for(SCORE_KEY))["execution_status"],
                         "invalid")
        self.assertEqual(ask.resolve_outcome({"answer": low + 0.5}, request_for(SCORE_KEY))["execution_status"],
                         "invalid")

    def test_score_probs_keys_are_levels(self):
        low, high = scale_bounds(SCORE_KEY)
        probs = {str(level): 1 for level in range(low, high + 1)}
        probs[str(low + 1)] = 3
        probs[str(low + 2)] = 3
        outcome = ask.resolve_outcome({"probs": probs}, request_for(SCORE_KEY))
        self.assertEqual(outcome["execution_status"], "ok")
        self.assertEqual(outcome["answer"], low + 1)          # 平票取较小分级
        self.assertAlmostEqual(sum(outcome["probs"].values()), 1.0)
        self.assertEqual(sorted(outcome["probs"]), [str(level) for level in range(low, high + 1)])

    def test_non_dict_raw_is_invalid(self):
        self.assertEqual(ask.resolve_outcome("yes", request_for(NOUL_KEY))["execution_status"], "invalid")
        self.assertEqual(ask.resolve_outcome(None, request_for(NOUL_KEY))["execution_status"], "invalid")

    def test_build_row_failure_has_null_answer_and_no_probs(self):
        request = request_for(CHOICE_KEY)
        row = ask.build_answer_row(request, "jev-1.13", "1.13", ask.failure_outcome("timeout", "boom"))
        self.assertIsNone(row["answer"])
        self.assertNotIn("probs", row)
        self.assertEqual(row["execution_status"], "timeout")
        ask.validate_answer_row(row, question=request)

    def test_contract_fields_present(self):
        request = request_for(CHOICE_KEY)
        row = ask.build_answer_row(request, "jev-1.13", "1.13",
                                  ask.resolve_outcome({"answer": option_keys(CHOICE_KEY)[0]}, request))
        self.assertEqual(set(row), set(ask.ANSWER_REQUIRED))
        self.assertEqual(row["qid"], f"db-test-00000001.{CHOICE_KEY}")
        self.assertEqual(row["id"], "db-test-00000001")
        self.assertEqual(row["key"], CHOICE_KEY)
        self.assertEqual(row["kind"], "choice")
        ask.validate_answer_row(row, question=request)

    def test_contract_rejects_bad_rows(self):
        request = request_for(CHOICE_KEY)
        row = ask.build_answer_row(request, "jev-1.13", "1.13",
                                   ask.resolve_outcome({"answer": option_keys(CHOICE_KEY)[0]}, request))
        for field, value in (("answer", "nope"), ("latency_ms", -1), ("source", "../evil")):
            bad = dict(row)
            bad[field] = value
            with self.assertRaises(ValueError):
                ask.validate_answer_row(bad, question=request)
        bad = dict(row)
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
        self.assertEqual(len(rows), TOTAL_REQUESTS)
        for row in rows:
            ask.validate_answer_row(row, question=questions[row["qid"]])
            self.assertEqual(row["execution_status"], "ok")
            self.assertEqual(row["source"], "fixture")
        summary = last_json(out)
        self.assertEqual(summary["ok_selected"], TOTAL_REQUESTS)
        self.assertEqual(summary["remaining_not_ok"], 0)

    def test_resume_skips_ok(self):
        self.assertEqual(self.run_fixture()[0], 0)
        before = {row["qid"]: row for row in self.answers()}
        code, out, _ = self.run_fixture()
        self.assertEqual(code, 0)
        summary = last_json(out)
        self.assertEqual(summary["attempted"], 0)
        self.assertEqual(summary["skipped_ok"], TOTAL_REQUESTS)
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
        self.assertEqual(len(rows), TOTAL_REQUESTS)
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
        self.assertEqual(summary["attempted"], TOTAL_REQUESTS - len(kept))
        self.assertEqual(len(self.answers()), TOTAL_REQUESTS)

    def test_journal_resume_without_answers_file(self):
        self.assertEqual(self.run_fixture()[0], 0)
        (self.tmp / "answers.fixture.jsonl").unlink()
        code, out, _ = self.run_fixture()
        self.assertEqual(code, 0)
        self.assertEqual(last_json(out)["attempted"], 0)
        self.assertEqual(last_json(out)["skipped_ok"], TOTAL_REQUESTS)
        self.assertEqual(len(self.answers()), TOTAL_REQUESTS)

    def test_retry_collapses_to_one_row_per_qid(self):
        self.run_fixture(["--fixture-fail-rate", "0.6"])
        self.run_fixture(["--retry-failed"])
        rows = self.answers()
        qids = [row["qid"] for row in rows]
        self.assertEqual(len(qids), len(set(qids)))
        self.assertEqual(len(rows), TOTAL_REQUESTS)

    def test_compaction_preserves_rows_outside_limit(self):
        self.assertEqual(self.run_fixture()[0], 0)
        self.assertEqual(len(self.answers()), TOTAL_REQUESTS)
        code, out, _ = self.run_fixture(["--limit", "2", "--retry-failed"])
        self.assertEqual(code, 0)
        self.assertEqual(last_json(out)["selected"], 2)
        self.assertEqual(len(self.answers()), TOTAL_REQUESTS)  # 未选中的行不能被压缩掉

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
        qid = f"db-test-00000001.{CHOICE_KEY}"
        keys = option_keys(CHOICE_KEY)
        body = jev_body({qid: {"answer": keys[0],
                               "probs": {key: (3 if key == keys[1] else 1) for key in keys}}})
        opener = FakeOpener([http_error(500, "boom"), FakeResponse(200, body)])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, _ = run_cli(self.jev_argv(limit="1"), deps=deps)
        self.assertEqual(code, 0)
        self.assertEqual(len(opener.requests), 2)
        rows = self.answers("jev-1.13")
        self.assertEqual([row["qid"] for row in rows], [qid])
        self.assertEqual(rows[0]["answer"], keys[0])
        self.assertAlmostEqual(rows[0]["probs"][keys[1]], 3 / (3 + len(keys) - 1), places=5)
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
        others = jev_body({"db-test-00000002.contains_harm": {"answer": "yes"}})
        opener = FakeOpener([FakeResponse(200, others), FakeResponse(200, {"unexpected": True})])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, _ = run_cli(self.jev_argv(limit="1"), deps=deps)
        self.assertEqual(code, 1)
        rows = self.answers("jev-1.13")
        self.assertEqual(rows[0]["qid"], f"db-test-00000001.{CHOICE_KEY}")
        self.assertEqual(rows[0]["execution_status"], "invalid")
        self.assertIsNone(rows[0]["answer"])
        code, _, _ = run_cli(self.jev_argv(limit="1", extra=["--retry-failed"]), deps=deps)
        self.assertEqual(code, 1)
        log = read_jsonl(self.tmp / "calls.jev-1.13.jsonl")
        reasons = [row["failure_reason"] for row in log if row["phase"] == "outcome"]
        self.assertTrue(any("missing qid" in reason for reason in reasons))
        self.assertTrue(any("unrecognized Jev response" in reason for reason in reasons))

    def test_jev_list_shape_accepted(self):
        qid = f"db-test-00000001.{CHOICE_KEY}"
        keys = option_keys(CHOICE_KEY)
        body = {"answers": [{"qid": qid, "answer": keys[1],
                             "probs": {keys[0]: 3, keys[1]: 1, keys[2]: 0}},
                            {"qid": "db-test-00000003.evidence_sufficiency", "answer": "sufficient"}]}
        opener = FakeOpener([FakeResponse(200, body)])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, _ = run_cli(self.jev_argv(limit="1"), deps=deps)
        self.assertEqual(code, 0)
        rows = self.answers("jev-1.13")
        self.assertEqual(rows[0]["answer"], keys[1])
        self.assertTrue(rows[0]["probs"].get(keys[1], 0) > 0)

    def test_unknown_qid_in_response_ignored_but_logged(self):
        qid = "db-test-00000002.contains_harm"
        body = {"answers": {qid: {"answer": "yes"}, "db-zzz.other": {"answer": "x"}}}
        opener = FakeOpener([FakeResponse(200, body)])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, _, _ = run_cli(self.jev_argv(limit="1", domains="risk_harm"), deps=deps)
        self.assertEqual(code, 0)
        log = read_jsonl(self.tmp / "calls.jev-1.13.jsonl")
        batches = [row for row in log if row["phase"] == "batch"]
        self.assertEqual(batches[0]["unknown_qids"], ["db-zzz.other"])

    def test_batch_size_packs_multiple_qids_per_request(self):
        body = jev_body({f"db-test-00000001.{CHOICE_KEY}": {"answer": option_keys(CHOICE_KEY)[0]},
                         f"db-test-00000001.{NOUL_KEY}": {"answer": "no"}})
        opener = FakeOpener([FakeResponse(200, body)])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, out, _ = run_cli(self.jev_argv(limit="2", extra=["--batch-size", "2"]), deps=deps)
        self.assertEqual(code, 0)
        self.assertEqual(len(opener.requests), 1)
        payload = opener.body(0)
        self.assertEqual([item["qid"] for item in payload["requests"]],
                         [f"db-test-00000001.{CHOICE_KEY}", f"db-test-00000001.{NOUL_KEY}"])
        by_qid = {row["qid"]: row for row in self.answers("jev-1.13")}
        self.assertEqual(by_qid[f"db-test-00000001.{NOUL_KEY}"]["answer"], "no")
        self.assertEqual(last_json(out)["call_summary"]["batches"], 1)

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
        self.assertEqual(len(plan), TOTAL_REQUESTS)
        self.assertEqual(plan[0]["body"]["api_version"], "1.13")
        self.assertEqual(len(plan[0]["body"]["requests"]), 1)
        self.assertEqual(plan[0]["body"]["requests"][0]["question"],
                         taxonomy.key_spec(CHOICE_KEY).prompt("zh"))

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
        responses = [FakeResponse(200, jev_body({"db-test-00000002.contains_harm": {"answer": "yes"}}))
                     for _ in range(TOTAL_REQUESTS)]
        opener = FakeOpener(responses)
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"JEV_API_KEY": SENTINEL_KEY})
        code, out, err = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                                  "--backend", "jev", "--live", "--endpoint", JEV_ENDPOINT,
                                  "--api-version", "1.13", "--integration-confirmed", "--workers", "1",
                                  "--quiet"], deps=deps)
        self.assertEqual(code, 1)  # 大多数响应里没有对应 qid → invalid；密钥仍不许落盘
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
        opener = FakeOpener([FakeResponse(200, jev_body({"db-test-00000002.contains_harm": {"answer": "yes"}}))])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={})
        code, _, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                              "--backend", "jev", "--live", "--endpoint", JEV_ENDPOINT,
                              "--api-version", "1.13", "--integration-confirmed", "--key-file",
                              str(key_file), "--domains", "risk_harm", "--limit", "1"], deps=deps)
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
        code, _, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                              "--backend", "openai-compatible", "--live",
                              "--base-url", "https://api.example.invalid/v1", "--model", "m",
                              "--source", "grok-4.7", "--domains", "risk_harm", "--limit", "1",
                              "--quiet"], deps=deps)
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
        self.assertIn("可选答案", opener.body(0)["messages"][0]["content"])

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
                              "--source", "grok-4.7", "--domains", "risk_harm", "--limit", "1", "--quiet"],
                             deps=deps)
        self.assertEqual(code, 0)
        self.assertEqual(self.answers("grok-4.7")[0]["answer"], "yes")

    def test_chat_empty_content_invalid(self):
        opener = FakeOpener([FakeResponse(200, {"choices": [{"message": {"content": ""}}]})])
        deps = ask.Deps(opener=opener, sleeper=lambda seconds: None, environ={"ASK_API_KEY": "k"})
        code, _, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                              "--backend", "openai-compatible", "--live",
                              "--base-url", "https://api.example.invalid/v1", "--model", "m",
                              "--source", "grok-4.7", "--domains", "risk_harm", "--limit", "1", "--quiet"],
                             deps=deps)
        self.assertEqual(code, 1)
        self.assertEqual(self.answers("grok-4.7")[0]["execution_status"], "invalid")

    def test_json_extractor(self):
        self.assertEqual(ask.extract_json_object('prefix {"a": {"b": 1}} suffix'), {"a": {"b": 1}})
        self.assertEqual(ask.extract_json_object('{"s": "}"}'), {"s": "}"})
        with self.assertRaises(ValueError):
            ask.extract_json_object("no json here")
        with self.assertRaises(ValueError):
            ask.extract_json_object("{unbalanced")


# ------------------------------------------------------------------ 真实产物回归 fixture

class RealSampleTests(unittest.TestCase):
    """直接读 datasets/decision-base/fixtures/ask-items-sample.jsonl（真实 items.jsonl 截取）。"""

    @classmethod
    def setUpClass(cls):
        if not REAL_SAMPLE.is_file():
            raise unittest.SkipTest(f"missing real sample fixture: {REAL_SAMPLE}")
        cls.items = read_jsonl(REAL_SAMPLE)
        cls.expected = sum(len(item["questions"]) for item in cls.items)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="dbask-real-")
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_sample_is_representative_and_taxonomy_clean(self):
        self.assertGreaterEqual(len(self.items), 8)
        kinds = {question["kind"] for item in self.items for question in item["questions"]}
        self.assertEqual(kinds, {"noul", "choice", "score"})
        self.assertTrue(any(item.get("targets") for item in self.items))
        self.assertTrue(any(not item.get("targets") for item in self.items))
        self.assertTrue(any(any(isinstance(value, dict) and value.get("probs")
                                for value in (item.get("targets") or {}).values())
                            for item in self.items))
        self.assertTrue(any(any(question["key"] == "next_step_candidate"
                                for question in item["questions"]) for item in self.items))
        self.assertTrue(any(len(item["questions"]) >= 4 for item in self.items))
        for item in self.items:
            self.assertEqual(taxonomy.item_errors(item), [], item["id"])
            for question in item["questions"]:
                self.assertEqual(taxonomy.validate_question(question), [])
                if question["kind"] == "score":
                    scale = question["scale"]
                    self.assertIsInstance(scale["labels"], list)   # 真实形状：min..max 的字符串数组
                    self.assertEqual(len(scale["labels"]), scale["max"] - scale["min"] + 1)
                    self.assertIs(type(scale["min"]), int)
                    self.assertIs(type(scale["max"]), int)
                else:
                    self.assertIsInstance(question["options"], list)
                    self.assertNotIn("scale", question)

    def test_plan_on_real_sample(self):
        out = self.tmp / "requests.jsonl"
        code, stdout, _ = run_cli(["plan", "--items", str(REAL_SAMPLE), "--out", str(out)])
        self.assertEqual(code, 0)
        rows = read_jsonl(out)
        self.assertEqual(len(rows), self.expected)
        for row in rows:
            if row["kind"] == "score":
                self.assertIsInstance(row["scale"]["labels"], list)
                self.assertEqual(len(row["scale"]["labels"]),
                                 row["scale"]["max"] - row["scale"]["min"] + 1)
                self.assertNotIn("options", row)
            else:
                self.assertTrue(row["options"])
                self.assertNotIn("scale", row)
        summary = last_json(stdout)
        self.assertEqual(summary["requests_count"], self.expected)
        self.assertTrue(summary["item_schema_checked"])
        self.assertEqual(summary["kinds"]["noul"] + summary["kinds"]["choice"]
                         + summary["kinds"]["score"], self.expected)

    def test_next_step_candidate_options_survive(self):
        out = self.tmp / "requests.jsonl"
        self.assertEqual(run_cli(["plan", "--items", str(REAL_SAMPLE), "--out", str(out)])[0], 0)
        rows = [row for row in read_jsonl(out) if row["key"] == "next_step_candidate"]
        self.assertTrue(rows)
        for row in rows:
            self.assertGreaterEqual(len(row["options"]), 2)
            for option in row["options"]:
                self.assertTrue(option["key"] and option["label"])

    def test_fixture_backend_end_to_end_then_verify(self):
        code, stdout, _ = run_cli(["run", "--items", str(REAL_SAMPLE), "--out", str(self.tmp),
                                   "--backend", "fixture", "--quiet"])
        self.assertEqual(code, 0)
        self.assertEqual(last_json(stdout)["ok_selected"], self.expected)
        answers = self.tmp / "answers.fixture.jsonl"
        code, stdout, _ = run_cli(["verify", "--items", str(REAL_SAMPLE), "--answers", str(answers)])
        self.assertEqual(code, 0)
        self.assertIn("complete : True", stdout)
        rows = read_jsonl(answers)
        self.assertEqual(len(rows), self.expected)
        requests = {request["qid"]: request for request in ask.load_requests(REAL_SAMPLE)[0]}
        for row in rows:
            self.assertEqual(row["execution_status"], "ok")
            self.assertIn(row["kind"], ("noul", "choice", "score"))
            if row["kind"] == "score":
                self.assertIs(type(row["answer"]), int)
                self.assertEqual(sorted(row["probs"]),
                                 sorted(ask.expected_prob_keys(requests[row["qid"]])))
            else:
                self.assertIn(row["answer"], [option["key"]
                                              for option in requests[row["qid"]]["options"]])
        code, stdout, _ = run_cli(["report", "--calls", str(self.tmp / "calls.fixture.jsonl"),
                                   "--answers", str(answers), "--items", str(REAL_SAMPLE)])
        self.assertEqual(code, 0)
        self.assertIn("coverage     : expected=", stdout)

    def test_score_answer_domain_uses_real_scale(self):
        requests = ask.load_requests(REAL_SAMPLE)[0]
        score_request = next(row for row in requests if row["kind"] == "score")
        low, high = score_request["scale"]["min"], score_request["scale"]["max"]
        self.assertEqual(ask.resolve_outcome({"answer": high}, score_request)["execution_status"], "ok")
        self.assertEqual(ask.resolve_outcome({"answer": high + 1}, score_request)["execution_status"],
                         "invalid")
        outcome = ask.resolve_outcome({"probs": {str(level): 1 for level in range(low, high + 1)}},
                                      score_request)
        self.assertEqual(outcome["execution_status"], "ok")
        self.assertEqual(sorted(outcome["probs"]), [str(level) for level in range(low, high + 1)])


# ------------------------------------------------------------------ 报告与核对

class ReportVerifyTests(BaseCase):
    def test_report_and_verify(self):
        self.run_fixture(["--fixture-fail-rate", "0.6"])
        calls = self.tmp / "calls.fixture.jsonl"
        answers = self.tmp / "answers.fixture.jsonl"
        code, out, _ = run_cli(["report", "--calls", str(calls), "--answers", str(answers),
                                "--items", str(self.items), "--json"])
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertEqual(report["attempts"], TOTAL_REQUESTS)
        self.assertEqual(report["answers_rows"], TOTAL_REQUESTS)
        self.assertEqual(report["coverage"]["expected"], TOTAL_REQUESTS)
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
        self.assertIn(f"missing={TOTAL_REQUESTS - 3}", out)


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

    def test_expected_prob_keys_follow_taxonomy(self):
        low, high = scale_bounds(SCORE_KEY)
        self.assertEqual(ask.expected_prob_keys(request_for(SCORE_KEY)),
                         [str(level) for level in range(low, high + 1)])
        self.assertEqual(ask.expected_prob_keys(request_for(NOUL_KEY)), ["yes", "no"])
        self.assertEqual(ask.expected_prob_keys(request_for(CHOICE_KEY)), option_keys(CHOICE_KEY))

    def test_dry_run_writes_no_calls_file(self):
        code, _, _ = run_cli(["run", "--items", str(self.items), "--out", str(self.tmp),
                              "--backend", "fixture", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertFalse((self.tmp / "calls.fixture.jsonl").exists())
        plan = read_jsonl(self.tmp / "requests.fixture.jsonl")
        self.assertEqual(len(plan), TOTAL_REQUESTS)


if __name__ == "__main__":
    unittest.main()
