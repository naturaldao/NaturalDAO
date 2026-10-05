"""契约校验：case / question / answer / label 四类记录与概率归一。"""
import unittest

from common import (normalize_probs, validate_answer, validate_case, validate_label,
                    validate_question)
from helpers import answer_row, make_case, make_questions


def valid_label(**overrides):
    label = {"id": "pol2-train-000001", "status": "violating", "polarity": "hate",
             "issues": ["coercion_manipulation"], "evidence": "sufficient",
             "acceptable_actions": ["repair"], "citations": ["PoL.2.10"],
             "brief_reason": "多源一致：违反持续同意要求。",
             "review": {"sources": ["glm-5.3", "jev-1.0"],
                        "agreement": "unanimous_multi_family", "disagreements": [],
                        "adjudicated_by": "auto_multi_lineage",
                        "review_level": "model_cross_checked"}}
    label.update(overrides)
    return label


class CaseTests(unittest.TestCase):
    def test_valid_paired_case(self):
        case = make_case()
        self.assertIs(validate_case(case), case)

    def test_unknown_field_rejected(self):
        case = make_case()
        case["split"] = "train"
        with self.assertRaises(ValueError) as caught:
            validate_case(case)
        self.assertIn("unknown field", str(caught.exception))

    def test_extra_object_is_the_only_extension(self):
        case = make_case()
        case["extra"] = {"note": "ok"}
        validate_case(case)
        case["extra"] = "not an object"
        with self.assertRaises(ValueError):
            validate_case(case)

    def test_id_must_encode_region(self):
        case = make_case(region="train")
        case["region"] = "validation"
        with self.assertRaises(ValueError):
            validate_case(case)

    def test_pair_fields_must_travel_together(self):
        case = make_case()
        del case["variant"]
        with self.assertRaises(ValueError):
            validate_case(case)

    def test_quality_flag_lives_in_provenance_only(self):
        case = make_case()
        case["quality_flag"] = ["weak_pair"]
        with self.assertRaises(ValueError):
            validate_case(case)
        case = make_case()
        case["provenance"]["quality_flag"] = ["weak_pair", "shortcut_risk"]
        validate_case(case)

    def test_generator_lineage_optional_but_checked(self):
        case = make_case()
        del case["provenance"]["generator_lineage"]
        validate_case(case)
        case["provenance"]["generator_lineage"] = ""
        with self.assertRaises(ValueError):
            validate_case(case)

    def test_context_needs_non_empty_strings(self):
        for bad in ([], [""], "上下文"):
            case = make_case()
            case["input"]["context"] = bad
            with self.assertRaises(ValueError):
                validate_case(case)


class QuestionTests(unittest.TestCase):
    def setUp(self):
        self.case = make_case()
        self.questions = make_questions(self.case)

    def test_qid_must_match_id_and_key(self):
        question = dict(self.questions[0])
        question["qid"] = "pol2-train-000001.other"
        with self.assertRaises(ValueError):
            validate_question(question)

    def test_noul_options_are_fixed(self):
        noul = next(row for row in self.questions if row["kind"] == "noul")
        self.assertEqual([option["key"] for option in noul["options"]], ["yes", "no"])
        broken = dict(noul)
        broken["options"] = [{"key": "yes", "label": "是"}, {"key": "maybe", "label": "也许"}]
        with self.assertRaises(ValueError):
            validate_question(broken)

    def test_score_requires_scale_and_choice_forbids_it(self):
        question = next(row for row in make_questions(self.case, with_score=True)
                        if row["kind"] == "score")
        validate_question(question)
        broken = dict(question)
        del broken["scale"]
        with self.assertRaises(ValueError):
            validate_question(broken)
        broken = dict(self.questions[0])
        broken["scale"] = {"min": 0, "max": 1, "labels": {"0": "a"}}
        with self.assertRaises(ValueError):
            validate_question(broken)

    def test_scale_labels_must_be_in_range(self):
        question = next(row for row in make_questions(self.case, with_score=True)
                        if row["kind"] == "score")
        question["scale"] = {"min": 0, "max": 5, "labels": {"0": "无", "9": "越界"}}
        with self.assertRaises(ValueError):
            validate_question(question)


class AnswerTests(unittest.TestCase):
    def setUp(self):
        self.case = make_case()
        self.questions = make_questions(self.case)
        self.status = next(row for row in self.questions if row["key"] == "status")

    def test_ok_answer_must_be_in_options(self):
        row = answer_row(self.status, "glm-5.3", "violating")
        validate_answer(row, question=self.status)
        row["answer"] = "unknown"
        with self.assertRaises(ValueError):
            validate_answer(row, question=self.status)

    def test_failure_is_never_ok(self):
        row = answer_row(self.status, "glm-5.3", None, execution_status="timeout")
        self.assertIsNone(row["answer"])
        validate_answer(row, question=self.status)
        row["answer"] = "violating"
        with self.assertRaises(ValueError):
            validate_answer(row, question=self.status)

    def test_failure_carries_no_probs(self):
        row = answer_row(self.status, "glm-5.3", None, execution_status="error")
        row["probs"] = {"conforming": 0.5, "violating": 0.5, "insufficient": 0.0}
        with self.assertRaises(ValueError):
            validate_answer(row, question=self.status)

    def test_probs_keys_and_sum(self):
        row = answer_row(self.status, "glm-5.3", "violating",
                         probs={"conforming": 0.1, "violating": 0.8, "insufficient": 0.1})
        validate_answer(row, question=self.status)
        row["probs"] = {"conforming": 0.1, "violating": 0.8}
        with self.assertRaises(ValueError):
            validate_answer(row, question=self.status)
        row["probs"] = {"conforming": 0.1, "violating": 0.8, "insufficient": 0.5}
        with self.assertRaises(ValueError):
            validate_answer(row, question=self.status)

    def test_latency_and_source_shape(self):
        row = answer_row(self.status, "glm-5.3", "violating")
        row["latency_ms"] = -1
        with self.assertRaises(ValueError):
            validate_answer(row)
        row = answer_row(self.status, "../escape", "violating")
        with self.assertRaises(ValueError):
            validate_answer(row)


class LabelTests(unittest.TestCase):
    def test_valid_label(self):
        label = valid_label()
        self.assertIs(validate_label(label), label)

    def test_review_level_has_only_two_values(self):
        for level in ("gold", "human_verified", ""):
            with self.assertRaises(ValueError):
                validate_label(valid_label(review={**valid_label()["review"],
                                                   "review_level": level}))

    def test_violating_requires_issue(self):
        with self.assertRaises(ValueError):
            validate_label(valid_label(issues=[]))

    def test_actions_and_citations_rules(self):
        with self.assertRaises(ValueError):
            validate_label(valid_label(acceptable_actions=[]))
        with self.assertRaises(ValueError):
            validate_label(valid_label(acceptable_actions=["ignore"]))
        with self.assertRaises(ValueError):
            validate_label(valid_label(citations=[]))

    def test_probs_must_normalize(self):
        label = valid_label(probs={"conforming": 0.2, "violating": 0.6, "insufficient": 0.2})
        validate_label(label)
        with self.assertRaises(ValueError):
            validate_label(valid_label(probs={"conforming": 0.2, "violating": 0.6,
                                              "insufficient": 0.5}))

    def test_review_field_set_is_fixed(self):
        review = dict(valid_label()["review"])
        review["notes"] = "extra"
        with self.assertRaises(ValueError):
            validate_label(valid_label(review=review))


class ProbabilityTests(unittest.TestCase):
    def test_rounding_is_normalized(self):
        result = normalize_probs({"a": 0.3333, "b": 0.3333, "c": 0.3333})
        self.assertAlmostEqual(sum(result.values()), 1.0)
        self.assertAlmostEqual(result["a"], 1 / 3, places=4)

    def test_rejects_bad_values(self):
        bad = [{"a": -0.1, "b": 1.1}, {"a": float("nan"), "b": 1.0}, {"a": 0.0, "b": 0.0},
               {"a": 0.5, "b": 0.4}, {}, {"a": 0.5, "b": 0.5, "c": 0.5}]
        for probs in bad:
            with self.assertRaises(ValueError):
                normalize_probs(probs)
        with self.assertRaises(ValueError):
            normalize_probs({"a": 0.5, "b": 0.5}, keys=["a", "c"])


if __name__ == "__main__":
    unittest.main()
