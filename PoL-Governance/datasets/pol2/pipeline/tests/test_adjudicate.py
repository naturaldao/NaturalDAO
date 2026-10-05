"""裁决：交叉验证、血缘剔除、分歧进 pending、概率归一、人工覆盖。"""
import json
import tempfile
import unittest
from pathlib import Path

import adjudicate
from common import read_jsonl, read_labels, validate_label
from helpers import answers_for, make_case, make_questions


def jsonl(rows):
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


class AdjudicateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out = self.root / "out"
        self.case = make_case()
        self.questions = make_questions(self.case)
        self.cases_path = self.root / "train.cases.jsonl"
        self.questions_path = self.root / "train.questions.jsonl"
        self.cases_path.write_text(jsonl([self.case]), encoding="utf-8")
        self.questions_path.write_text(jsonl(self.questions), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_adjudicate(self, source_groups, *extra, human=None):
        argv = ["--cases", str(self.cases_path), "--questions", str(self.questions_path),
                "--out", str(self.out), "--region", "train", *extra]
        for index, (source, kwargs) in enumerate(source_groups.items()):
            path = self.root / f"answers.{index}.jsonl"
            path.write_text(jsonl(answers_for(self.case, self.questions, source, **kwargs)),
                            encoding="utf-8")
            argv += ["--answers", str(path)]
        if human is not None:
            human_path = self.root / "human.jsonl"
            human_path.write_text(jsonl(human), encoding="utf-8")
            argv += ["--human-labels", str(human_path)]
        return adjudicate.main(argv)

    def labels(self):
        path = self.out / "train.labels.jsonl"
        return read_jsonl(path) if path.exists() else []

    def pending(self):
        path = self.out / "train.pending.jsonl"
        return read_jsonl(path) if path.exists() else []

    def test_two_lineages_agree_produce_label(self):
        code = self.run_adjudicate({"gpt-6.1-sol": {}, "grok-4.7": {}})
        self.assertEqual(code, 0)
        labels = self.labels()
        self.assertEqual(len(labels), 1)
        label = validate_label(labels[0])
        self.assertEqual(label["status"], "violating")
        self.assertEqual(label["polarity"], "hate")
        self.assertEqual(label["issues"], ["coercion_manipulation"])
        self.assertEqual(label["acceptable_actions"], ["repair"])
        self.assertEqual(label["citations"], ["PoL.2.10"])
        self.assertEqual(label["review"]["review_level"], "model_cross_checked")
        self.assertEqual(label["review"]["sources"], ["gpt-6.1-sol", "grok-4.7"])
        self.assertEqual(label["review"]["adjudicated_by"], "auto_multi_lineage")
        self.assertEqual(self.pending(), [])

    def test_same_family_agreement_is_not_truth(self):
        code = self.run_adjudicate({"gpt-6.1-sol": {}, "gpt-6.1-sol-alt": {}},
                                   "--lineage", "gpt-6.1-sol-alt=openai-sol")
        self.assertEqual(code, 0)
        self.assertEqual(self.labels(), [])
        pending = self.pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["reason"], "unresolved_questions")
        states = {row["key"]: row["state"] for row in pending[0]["questions"]}
        self.assertEqual(states["status"], "same_family_only")

    def test_luna_never_contributes_to_labels(self):
        code = self.run_adjudicate({"luna": {}, "gpt-6.1-sol": {}})
        self.assertEqual(code, 0)
        self.assertEqual(self.labels(), [])
        pending = self.pending()[0]
        self.assertEqual(pending["sources"], ["gpt-6.1-sol"])

    def test_generator_lineage_is_removed(self):
        self.case["provenance"]["generator_lineage"] = "openai-sol"
        self.cases_path.write_text(jsonl([self.case]), encoding="utf-8")
        code = self.run_adjudicate({"gpt-6.1-sol": {}, "grok-4.7": {}})
        self.assertEqual(code, 0)
        self.assertEqual(self.labels(), [])
        self.assertEqual(self.pending()[0]["sources"], ["grok-4.7"])

    def test_missing_generator_lineage_is_pending(self):
        del self.case["provenance"]["generator_lineage"]
        self.cases_path.write_text(jsonl([self.case]), encoding="utf-8")
        self.run_adjudicate({"gpt-6.1-sol": {}, "grok-4.7": {}})
        self.assertEqual(self.labels(), [])
        self.assertEqual(self.pending()[0]["reason"], "missing_generator_lineage")

    def test_disagreement_records_values_and_blocks(self):
        code = self.run_adjudicate({"gpt-6.1-sol": {},
                                    "grok-4.7": {"status": "conforming", "issues": ()}})
        self.assertEqual(code, 0)
        self.assertEqual(self.labels(), [])
        pending = self.pending()[0]
        self.assertEqual(pending["reason"], "unresolved_questions")
        status = next(row for row in pending["questions"] if row["key"] == "status")
        self.assertEqual(status["state"], "disagreed")
        self.assertEqual(status["values"], {"gpt-6.1-sol": "violating",
                                            "grok-4.7": "conforming"})

    def test_majority_needs_explicit_flag(self):
        groups = {"gpt-6.1-sol": {}, "grok-4.7": {},
                  "mimo-v2.6-pro": {"status": "conforming", "issues": ()}}
        self.run_adjudicate(groups)
        self.assertEqual(self.labels(), [])
        self.out = self.root / "out2"
        self.run_adjudicate(groups, "--allow-majority")
        labels = self.labels()
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["review"]["agreement"], "majority")
        self.assertTrue(labels[0]["review"]["disagreements"])

    def test_unmapped_sources_cannot_supply_independence(self):
        self.run_adjudicate({"teacher-a": {}, "teacher-b": {}})
        self.assertEqual(self.labels(), [])
        states = {row["key"]: row["state"] for row in self.pending()[0]["questions"]}
        self.assertEqual(states["status"], "insufficient_lineages")
        self.out = self.root / "out2"
        self.run_adjudicate({"teacher-a": {}, "teacher-b": {}},
                            "--lineage", "teacher-a=family-a", "--lineage", "teacher-b=family-b")
        self.assertEqual(len(self.labels()), 1)

    def test_inconsistent_answers_are_pending(self):
        self.run_adjudicate({"gpt-6.1-sol": {"issues": ()}, "grok-4.7": {"issues": ()}})
        self.assertEqual(self.labels(), [])
        self.assertEqual(self.pending()[0]["reason"], "inconsistent_answers")
        self.assertIn("violating without any yes-issue", self.pending()[0]["note"])

    def test_probs_are_averaged_and_normalized(self):
        probs = {"conforming": 0.1, "violating": 0.8, "insufficient": 0.1}
        self.run_adjudicate({"gpt-6.1-sol": {"probs": probs}, "grok-4.7": {"probs": probs}})
        label = self.labels()[0]
        self.assertAlmostEqual(sum(label["probs"].values()), 1.0)
        self.assertAlmostEqual(label["probs"]["violating"], 0.8)
        report = json.loads((self.out / "adjudication.train.json").read_text(encoding="utf-8"))
        self.assertEqual(report["labels"], 1)
        self.assertEqual(report["pending"], 0)
        self.assertEqual(report["review_levels"], {"model_cross_checked": 1})

    def test_human_labels_override_and_are_marked(self):
        human = [{"id": self.case["id"], "status": "insufficient", "polarity": "unclear",
                  "issues": [], "evidence": "insufficient", "acceptable_actions": ["clarify"],
                  "brief_reason": "人工复核认为信息不足。", "reviewer": "wenbo"}]
        self.run_adjudicate({"gpt-6.1-sol": {}, "grok-4.7": {}}, human=human)
        labels = self.labels()
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]["review"]["review_level"], "human_reviewed")
        self.assertEqual(labels[0]["review"]["adjudicated_by"], "wenbo")
        self.assertEqual(labels[0]["review"]["sources"], ["human:wenbo"])

    def test_unknown_qid_answer_is_refused(self):
        bad = answers_for(self.case, self.questions, "gpt-6.1-sol")
        bad[0]["qid"] = "pol2-train-999999.status"
        path = self.root / "bad.jsonl"
        path.write_text(jsonl(bad), encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            adjudicate.main(["--cases", str(self.cases_path), "--questions",
                             str(self.questions_path), "--answers", str(path),
                             "--out", str(self.out), "--region", "train"])
        self.assertEqual(caught.exception.code, 2)

    def test_duplicate_source_answer_is_refused(self):
        rows = answers_for(self.case, self.questions, "gpt-6.1-sol")
        path = self.root / "dup.jsonl"
        path.write_text(jsonl(rows + rows[:1]), encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            adjudicate.main(["--cases", str(self.cases_path), "--questions",
                             str(self.questions_path), "--answers", str(path),
                             "--out", str(self.out), "--region", "train"])
        self.assertEqual(caught.exception.code, 2)

    def test_labels_pass_full_contract_validation(self):
        self.run_adjudicate({"gpt-6.1-sol": {}, "grok-4.7": {}})
        for row in read_labels(self.out / "train.labels.jsonl"):
            validate_label(row)


if __name__ == "__main__":
    unittest.main()
