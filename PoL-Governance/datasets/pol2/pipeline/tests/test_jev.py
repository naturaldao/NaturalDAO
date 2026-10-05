"""Jev 适配器：prepare/run 两段式、未接入必须明确报错、绝不静默降级（离线）。"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jev
from common import read_jsonl, validate_answer
from helpers import make_case, make_questions


def jsonl(rows):
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


class JevTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.case = make_case()
        self.questions = make_questions(self.case)
        self.questions_path = self.root / "train.questions.jsonl"
        self.questions_path.write_text(jsonl(self.questions), encoding="utf-8")
        self.out = self.root / "jev"

    def tearDown(self):
        self.tmp.cleanup()

    def test_prepare_writes_request_pack(self):
        code = jev.main(["prepare", "--questions", str(self.questions_path), "--out", str(self.out)])
        self.assertEqual(code, 0)
        rows = read_jsonl(self.out / "jev-requests.jsonl")
        self.assertEqual(len(rows), len(self.questions))
        manifest = json.loads((self.out / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["state"], "prepared")
        self.assertEqual(manifest["protocol"], "unverified")
        with self.assertRaises(SystemExit) as caught:
            jev.main(["prepare", "--questions", str(self.questions_path), "--out", str(self.out)])
        self.assertEqual(caught.exception.code, 2)

    def test_run_without_configuration_fails_loudly(self):
        jev.main(["prepare", "--questions", str(self.questions_path), "--out", str(self.out)])
        for missing in (["--api-version", "1.0", "--integration-confirmed"],
                        ["--endpoint", "https://jev.example.com/v1", "--integration-confirmed"],
                        ["--endpoint", "https://jev.example.com/v1", "--api-version", "1.0"]):
            with self.assertRaises(SystemExit) as caught:
                jev.main(["run", "--out", str(self.out), *missing])
            self.assertEqual(caught.exception.code, 2)
        self.assertFalse((self.out / "train.answers.jev-1.0.jsonl").exists())

    def test_run_requires_key_and_endpoint_validation(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as caught:
                jev.main(["run", "--out", str(self.out), "--questions", str(self.questions_path),
                          "--endpoint", "https://jev.example.com/v1", "--api-version", "1.0",
                          "--integration-confirmed"])
            self.assertEqual(caught.exception.code, 2)
        with mock.patch.dict(os.environ, {"JEV_API_KEY": "k"}, clear=True):
            with self.assertRaises(SystemExit) as caught:
                jev.main(["run", "--out", str(self.out), "--questions", str(self.questions_path),
                          "--endpoint", "http://example.com/v1", "--api-version", "1.0",
                          "--integration-confirmed"])
            self.assertEqual(caught.exception.code, 2)

    def test_run_with_confirmed_shape_writes_answers(self):
        sent = {}

        def fake_sender(endpoint, payload, timeout, key=None, request_path="/answers"):
            sent.update({"endpoint": endpoint, "payload": payload, "key": key})
            return {"answers": {question["qid"]: {"answer": "yes"}
                                for question in self.questions}}

        with mock.patch.dict(os.environ, {"JEV_API_KEY": "k"}, clear=True):
            code = jev.main(["run", "--out", str(self.out),
                             "--questions", str(self.questions_path),
                             "--endpoint", "https://jev.example.com/v1", "--api-version", "1.0",
                             "--integration-confirmed"], sender=fake_sender)
        self.assertEqual(code, 1)
        rows = read_jsonl(self.out / "train.answers.jev-1.0.jsonl")
        self.assertEqual(rows[0]["source"], "jev-1.0")
        self.assertEqual(sent["payload"]["api_version"], "1.0")
        self.assertEqual(sent["key"], "k")
        by_qid = {row["qid"]: row for row in rows}
        status = next(row for row in self.questions if row["key"] == "status")
        self.assertEqual(by_qid[status["qid"]]["execution_status"], "invalid")
        issue = next(row for row in self.questions if row["kind"] == "noul")
        self.assertEqual(by_qid[issue["qid"]]["execution_status"], "ok")
        for row in rows:
            validate_answer(row)

    def test_dry_run_writes_no_answers(self):
        code = jev.main(["run", "--out", str(self.out), "--questions", str(self.questions_path),
                         "--dry-run"])
        self.assertEqual(code, 0)
        self.assertTrue((self.out / "jev-run-requests.jsonl").exists())
        self.assertFalse((self.out / "train.answers.jev-unverified.jsonl").exists())

    def test_parse_response_marks_shape_problems_invalid(self):
        question = next(row for row in self.questions if row["kind"] == "noul")
        outcomes = jev.parse_response({"answers": {question["qid"]: {"answer": "maybe"}}},
                                      [question])
        self.assertEqual(outcomes[question["qid"]]["execution_status"], "invalid")
        outcomes = jev.parse_response({"answers": {}}, [question])
        self.assertEqual(outcomes[question["qid"]]["execution_status"], "invalid")
        with self.assertRaises(ValueError):
            jev.parse_response({"results": {}}, [question])


if __name__ == "__main__":
    unittest.main()
