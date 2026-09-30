"""教师取答案：结构、失败不写 ok、断点续跑、缺 id 处理、离线默认。"""
import json
import re
import tempfile
import unittest
from pathlib import Path

import fixtures
import teacher
from clients import CallFailure
from common import read_jsonl, validate_answer
from helpers import make_case, make_questions


def jsonl(rows):
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


class FakeTeacherClient:
    """离线替身：按提示里的选项列表作答。"""

    def __init__(self, mode="ok", model="fake-sol", lineage="openai-sol", probs=False):
        self.mode = mode
        self.model = model
        self.lineage = lineage
        self.probs = probs
        self.calls = 0

    def payload(self, messages, max_tokens=None):
        return {"model": self.model, "messages": messages, "max_output_tokens": max_tokens}

    def chat(self, messages, max_tokens=None):
        self.calls += 1
        prompt = messages[-1]["content"]
        if self.mode == "fail":
            raise CallFailure("timeout", "injected timeout")
        if self.mode == "invalid":
            return {"text": "无法判断", "latency_ms": 3.0, "attempts": 1, "usage": {}}
        keys = re.findall(r"^- ([^\s：]+)：", prompt, re.M)
        value = keys[0] if keys else 3
        payload = {"answer": value}
        if self.probs and keys:
            payload["probs"] = {key: 1.0 / len(keys) for key in keys}
        return {"text": json.dumps(payload, ensure_ascii=False), "latency_ms": 7.5,
                "attempts": 1, "usage": {"prompt_tokens": 8, "completion_tokens": 4,
                                         "total_tokens": 12, "cost_usd": None}}


class TeacherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.case = make_case()
        self.questions = make_questions(self.case)
        self.questions_path = self.root / "train.questions.jsonl"
        self.questions_path.write_text(jsonl(self.questions), encoding="utf-8")
        self.out_dir = self.root / "out"

    def tearDown(self):
        self.tmp.cleanup()

    def run_teacher(self, *extra, factory=None):
        return teacher.main(["--questions", str(self.questions_path), "--out-dir", str(self.out_dir),
                             "--region", "train", *extra], client_factory=factory)

    def test_fixture_mode_is_offline_and_valid(self):
        code = self.run_teacher("--fixture", "--source", "fixture")
        self.assertEqual(code, 0)
        rows = read_jsonl(self.out_dir / "train.answers.fixture.jsonl")
        self.assertEqual(len(rows), len(self.questions))
        for row in rows:
            validate_answer(row, question=next(q for q in self.questions if q["qid"] == row["qid"]))
            self.assertEqual(row["execution_status"], "ok")
            self.assertEqual(row["source"], "fixture")

    def test_fixture_mode_requires_fixture_source(self):
        with self.assertRaises(SystemExit) as caught:
            self.run_teacher("--fixture")
        self.assertEqual(caught.exception.code, 2)

    def test_default_mode_is_dry_run(self):
        code = self.run_teacher()
        self.assertEqual(code, 0)
        planned = read_jsonl(self.out_dir / "requests" / "glm-5.3.requests.jsonl")
        self.assertEqual(len(planned), len(self.questions))
        self.assertFalse((self.out_dir / "train.answers.glm-5.3.jsonl").exists())
        self.assertFalse((self.out_dir / "calls.glm-5.3.jsonl").exists())

    def test_failure_is_recorded_then_resumed(self):
        failing = FakeTeacherClient(mode="fail")
        code = self.run_teacher("--live", "--source", "gpt-6.1-sol",
                                factory=lambda args: failing)
        self.assertEqual(code, 1)
        path = self.out_dir / "train.answers.gpt-6.1-sol.jsonl"
        rows = read_jsonl(path)
        self.assertEqual(len(rows), len(self.questions))
        for row in rows:
            self.assertEqual(row["execution_status"], "timeout")
            self.assertIsNone(row["answer"])
            self.assertNotIn("probs", row)
        healthy = FakeTeacherClient(mode="ok")
        code = self.run_teacher("--live", "--source", "gpt-6.1-sol",
                                factory=lambda args: healthy)
        self.assertEqual(code, 0)
        self.assertEqual(healthy.calls, len(self.questions))
        rows = read_jsonl(path)
        self.assertEqual(len(rows), len(self.questions))
        self.assertEqual({row["qid"] for row in rows}, {row["qid"] for row in self.questions})
        for row in rows:
            self.assertEqual(row["execution_status"], "ok")

    def test_second_run_skips_ok_rows(self):
        first = FakeTeacherClient()
        self.run_teacher("--live", "--source", "gpt-6.1-sol", factory=lambda args: first)
        second = FakeTeacherClient()
        code = self.run_teacher("--live", "--source", "gpt-6.1-sol", factory=lambda args: second)
        self.assertEqual(code, 0)
        self.assertEqual(second.calls, 0)
        self.assertEqual(first.calls, len(self.questions))

    def test_invalid_output_is_not_ok(self):
        code = self.run_teacher("--live", "--source", "grok-4.7",
                                factory=lambda args: FakeTeacherClient(mode="invalid",
                                                                       lineage="xai-grok"))
        self.assertEqual(code, 1)
        rows = read_jsonl(self.out_dir / "train.answers.grok-4.7.jsonl")
        self.assertTrue(all(row["execution_status"] == "invalid" for row in rows))
        self.assertTrue(all(row["answer"] is None for row in rows))
        self.assertTrue(all("raw_sha256" in row["extra"] for row in rows))

    def test_probs_are_written_normalized(self):
        self.run_teacher("--live", "--source", "gpt-6.1-sol",
                         factory=lambda args: FakeTeacherClient(probs=True))
        rows = read_jsonl(self.out_dir / "train.answers.gpt-6.1-sol.jsonl")
        status = next(row for row in rows if row["qid"].endswith(".status"))
        self.assertAlmostEqual(sum(status["probs"].values()), 1.0)

    def test_limit_and_keys_filter(self):
        code = self.run_teacher("--dry-run", "--keys", "status", "--limit", "1")
        self.assertEqual(code, 0)
        planned = read_jsonl(self.out_dir / "requests" / "glm-5.3.requests.jsonl")
        self.assertEqual(len(planned), 1)
        self.assertTrue(planned[0]["qid"].endswith(".status"))

    def test_missing_qid_is_refused(self):
        broken = [dict(self.questions[0])]
        del broken[0]["qid"]
        self.questions_path.write_text(jsonl(broken), encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            self.run_teacher("--fixture", "--source", "fixture")
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
