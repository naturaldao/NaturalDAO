#!/usr/bin/env python3
"""convert.py 原生四元组模式（--native）的离线测试，全部用内存 fixture，不联网。

覆盖 task-16 的验收点：原生键名不动、options/target 等长可对齐、概率归一、
group 聚合、0-5 档不被压、硬标签转单点分布且可复原、state 不被加工、id 稳定。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


convert = load_module("decision_base_convert_native", HERE / "convert.py")
taxonomy = convert.load_taxonomy(HERE / "taxonomy.py")
NATIVE = convert.NATIVE_CONVERTERS
CREATED_AT = "2026-10-05T04:00:00+00:00"
REVISION = "e" * 40


def manifest(converter, **overrides):
    base = {"dataset": "Example/data", "revision": REVISION, "config": "default",
            "split": "train", "license": "apache-2.0", "lang": "en",
            "converter": converter, "complete": True, "revision_stable": True,
            "source_url": "https://huggingface.co/datasets/Example/data"}
    base.update(overrides)
    return base


def context():
    return convert.Context(taxonomy, created_at=CREATED_AT, log=lambda *_a, **_k: None)


def run(converter, rows, slug="jev-distill-v3", **manifest_overrides):
    return convert.convert_unit(context(), slug, manifest(converter, **manifest_overrides),
                                rows, converters=NATIVE)


def jev_row(row_idx, kind, options, target, question="Rate claim reliability for this scenario on a 0-5 scale.",
            family="knowledge", domain="fact_checking", state=None):
    # state 默认带行号：条目按 state 去重，测试里各行的情境必须互不相同
    state = state if state is not None else f"Scenario {row_idx}: a statistic in the draft contradicts its source."
    return (row_idx, {"id": f"v3_{row_idx:04x}_s", "kind": kind, "options": options, "target": target,
                      "state": state, "question": question, "domain": domain, "family": family,
                      "source": "yuri_v3"})


class JevDistillTests(unittest.TestCase):
    def test_score_keeps_native_six_levels(self):
        rows = [jev_row(0, "score", ["0", "1", "2", "3", "4", "5"],
                        [0.01, 0.01, 0.05, 0.41, 0.51, 0.01])]
        items, report = run("jev_typed", rows)
        self.assertEqual((len(items), report["invalid"]), (1, 0))
        question = items[0]["questions"][0]
        self.assertEqual(question["kind"], "score")
        self.assertEqual(question["scale"], {"min": 0, "max": 5,
                                             "labels": ["0", "1", "2", "3", "4", "5"]})
        target = items[0]["targets"][question["key"]]
        self.assertEqual(len(target["probs"]), 6)
        self.assertEqual(target["answer"], "4")
        self.assertAlmostEqual(sum(target["probs"].values()), 1.0, places=6)

    def test_question_text_is_the_native_key_and_origin_is_source(self):
        rows = [jev_row(0, "noul", ["false", "true"], [0.5, 0.5])]
        items, _ = run("jev_typed", rows)
        question = items[0]["questions"][0]
        self.assertEqual(question["key"], "Rate claim reliability for this scenario on a 0-5 scale.")
        self.assertEqual(question["source_key"], question["key"])
        self.assertEqual(question["origin"], "source")
        self.assertEqual(question["prompt"], question["key"])

    def test_native_noul_options_are_not_rewritten_to_yes_no(self):
        rows = [jev_row(0, "noul", ["false", "true"], [1.0, 0.0])]
        items, _ = run("jev_typed", rows)
        options = items[0]["questions"][0]["options"]
        self.assertEqual([o["key"] for o in options], ["false", "true"])
        self.assertEqual(len(options), len(items[0]["targets"][items[0]["questions"][0]["key"]]["probs"]))

    def test_domain_comes_from_the_native_family_field(self):
        rows = [jev_row(0, "noul", ["false", "true"], [1.0, 0.0], family="knowledge"),
                jev_row(1, "noul", ["false", "true"], [1.0, 0.0], family="agent",
                        domain="tool_selection")]
        items, _ = run("jev_typed", rows)
        self.assertEqual([item["domain"] for item in items],
                         ["knowledge_reasoning", "decision_mechanics"])
        self.assertEqual(items[0]["meta"]["domain_rule"], "family:knowledge")

    def test_state_is_not_clipped_in_native_mode(self):
        long_state = "x" * 20000
        rows = [jev_row(0, "noul", ["false", "true"], [1.0, 0.0], state=long_state)]
        items, _ = run("jev_typed", rows)
        self.assertEqual(len(items[0]["state"]), 20000)

    def test_renormalization_is_flagged_and_unnormalizable_is_dropped(self):
        rows = [jev_row(0, "choice", ["a", "b"], [0.6, 0.6]),
                jev_row(1, "choice", ["a", "b"], [0.0, 0.0])]
        items, _ = run("jev_typed", rows)
        self.assertIn("probs_normalized", items[0]["meta"]["quality_flags"])
        self.assertAlmostEqual(sum(items[0]["targets"][items[0]["questions"][0]["key"]]["probs"].values()),
                               1.0, places=6)
        self.assertNotIn("probs", items[1]["targets"][items[1]["questions"][0]["key"]])


class OpenJevTests(unittest.TestCase):
    def rows(self):
        common = {"group_id": "case:42", "split": "train", "source": "customer-control-v1",
                  "state_json": json.dumps("Customer needs a password reset."),
                  "original_line_number": 7}
        return [
            (0, dict(common, id="case:42:category", kind="choice",
                     question="Determine the broad category of this support ticket.",
                     options=["billing", "account"], target=[0.2, 0.8])),
            (1, dict(common, id="case:42:bug_severity", kind="score",
                     question="How severe is the reported issue?",
                     options=["Cosmetic", "Degraded", "Blocking"], target=[1.0, 0.0, 0.0])),
            (2, dict(common, id="case:42:refund_requested", kind="noul",
                     question="Is the user asking for a refund?",
                     options=["no", "yes"], target=[1.0, 0.0])),
        ]

    def test_group_becomes_one_item_with_native_question_keys(self):
        items, report = run("open_jev", self.rows(), slug="open-jev")
        self.assertEqual((len(items), report["items"]), (1, 1))
        item = items[0]
        self.assertEqual([q["key"] for q in item["questions"]],
                         ["category", "bug_severity", "refund_requested"])
        self.assertTrue(all(q["origin"] == "source" for q in item["questions"]))
        self.assertEqual(sorted(item["targets"]), ["bug_severity", "category", "refund_requested"])
        self.assertEqual(item["state"], "Customer needs a password reset.")
        self.assertIn("grouped_questions:3", item["meta"]["quality_flags"])

    def test_every_question_has_matching_option_and_target_lengths(self):
        items, _ = run("open_jev", self.rows(), slug="open-jev")
        item = items[0]
        for question in item["questions"]:
            target = item["targets"][question["key"]]
            if question["kind"] == "score":
                self.assertEqual(len(target["probs"]), len(question["scale"]["labels"]))
            else:
                self.assertEqual(len(target["probs"]), len(question["options"]))
            self.assertAlmostEqual(sum(target["probs"].values()), 1.0, places=6)

    def test_object_state_is_serialized_as_json_not_python_repr(self):
        rows = self.rows()
        for _, payload in rows:
            payload["state_json"] = json.dumps({"health": 100.0, "ammo": 50.0})
        items, report = run("open_jev", rows, slug="open-jev")
        self.assertEqual(len(items), 1)
        self.assertEqual(json.loads(items[0]["state"]), {"health": 100.0, "ammo": 50.0})
        self.assertNotIn("'", items[0]["state"])          # 不能是 Python repr
        self.assertEqual(report["skipped"], {})

    def test_duplicate_question_key_in_one_group_is_skipped(self):
        rows = self.rows()
        rows.append((3, dict(rows[0][1])))
        items, report = run("open_jev", rows, slug="open-jev")
        self.assertEqual(len(items[0]["questions"]), 3)
        self.assertEqual(report["skipped"].get("duplicate_question_key"), 1)


class JevDecisionsTests(unittest.TestCase):
    def general_row(self, row_idx=0):
        return (row_idx, {
            "id": f"hash{row_idx}", "source": "nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1",
            "state": {"system": "policy", "user_goal": "reset my password", "history": []},
            "question": "Given the current state and available options,\nwhich option should be selected?",
            "question_type": "choice",
            "answer_options": [{"type": "action", "label": "verify_email", "description": "verify"},
                               {"type": "action", "label": "reset_password", "description": "reset"}],
            "target_index": 1})

    def default_row(self, row_idx=0):
        return (row_idx, {
            "id": f"hash{row_idx}", "source": "nvidia/Nemotron-RL", "decision_type": "tool_choice",
            "state": {"system": "policy", "user_goal": "sensor readings are odd", "history": []},
            "candidates": [{"id": "tool::diagnose", "name": "diagnose_equipment"},
                           {"id": "tool::schedule", "name": "schedule_field_service"}],
            "target": {"candidate_id": "tool::schedule", "action_name": "schedule_field_service"}})

    def test_target_index_becomes_answer_plus_point_mass(self):
        items, _ = run("jev_decisions_v1", [self.general_row()], slug="jev-decisions-general-50k")
        item = items[0]
        question = item["questions"][0]
        target = item["targets"][question["key"]]
        self.assertEqual(question["key"], self.general_row()[1]["question"])
        self.assertEqual(target["answer"], question["options"][1]["key"])
        self.assertEqual(target["probs"][target["answer"]], 1.0)
        self.assertEqual(len(target["probs"]), len(question["options"]))
        self.assertEqual(sum(target["probs"].values()), 1.0)

    def test_candidate_id_becomes_answer_and_key_is_native_decision_type(self):
        items, _ = run("jev_decisions_v1", [self.default_row()], slug="jev-decisions-strata")
        item = items[0]
        question = item["questions"][0]
        self.assertEqual(question["key"], "tool_choice")
        self.assertEqual(question["source_key"], "tool_choice")
        self.assertIn("prompt_falls_back_to_native_decision_type", item["meta"]["quality_flags"])
        target = item["targets"]["tool_choice"]
        self.assertEqual(target["answer"], question["options"][1]["key"])

    def test_out_of_range_target_index_is_skipped(self):
        row = self.general_row()
        row[1]["target_index"] = 5
        items, report = run("jev_decisions_v1", [row], slug="jev-decisions-general-50k")
        self.assertEqual(items, [])
        self.assertEqual(report["skipped"].get("target_index_out_of_range"), 1)

    def test_more_than_sixteen_options_is_flagged_not_truncated(self):
        row = self.general_row()
        row[1]["answer_options"] = [{"label": f"action_{index}"} for index in range(18)]
        row[1]["target_index"] = 3
        items, _ = run("jev_decisions_v1", [row], slug="jev-decisions-general-50k")
        question = items[0]["questions"][0]
        self.assertEqual(len(question["options"]), 18)
        self.assertIn("option_count_over_16:18", items[0]["meta"]["quality_flags"])


class SystemoneLiteTests(unittest.TestCase):
    def row(self):
        return (0, {"task": "debate.winner",
                    "state": json.dumps({"question": "We should open-source the core library"}),
                    "instructions": "Given the claims and evidence flags, who should win the debate?",
                    "criteria_keys": ["A", "B"],
                    "criteria_values": ["oppose: Side B", "support: Side A"],
                    "label_alias": "A", "label_key": "oppose",
                    "meta": json.dumps({"gym": "debate_judge"})})

    def test_task_is_the_key_and_label_alias_picks_the_criteria_value(self):
        items, _ = run("systemone_lite", [self.row()], slug="systemone-lite-general")
        item = items[0]
        question = item["questions"][0]
        self.assertEqual(question["key"], "debate.winner")
        self.assertEqual(question["prompt"], "Given the claims and evidence flags, who should win the debate?")
        self.assertEqual([o["label"] for o in question["options"]],
                         ["oppose: Side B", "support: Side A"])
        target = item["targets"]["debate.winner"]
        self.assertEqual(target["answer"], question["options"][0]["key"])
        self.assertEqual(target["probs"][target["answer"]], 1.0)

    def test_unusable_label_alias_is_skipped(self):
        row = self.row()
        row[1]["label_alias"] = "Z"
        items, report = run("systemone_lite", [row], slug="systemone-lite-general")
        self.assertEqual(items, [])
        self.assertEqual(report["skipped"].get("criteria_misaligned"), 1)


class SystemOne270mTests(unittest.TestCase):
    def rows(self):
        prompt = ("<state>\n2026-09-21 ERROR NullPointerException in MFA module\n</state>\n\n"
                  "Question: Determine the primary category of this alert.\nOptions:\n"
                  "A. authentication - failed logins\nB. mfa_error - MFA processing problem\n"
                  "C. system_error - general error\n\nAnswer with one letter.\nAnswer:")
        common = {"prompt": prompt, "state_id": "abc123", "domain": "security alert"}
        return [(0, dict(common, letters=["A", "B", "C"], target=[0.0001, 0.9998, 0.0001],
                         label="mfa_error", qtype="choice")),
                (1, dict(common, letters=["A", "B"], target=[0.0001, 0.9999], label="yes",
                         qtype="noul"))]

    def test_state_and_question_are_extracted_verbatim_and_grouped(self):
        items, _ = run("system_one_270m", self.rows(), slug="system-one-270m")
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["state"], "2026-09-21 ERROR NullPointerException in MFA module")
        self.assertEqual([q["key"] for q in item["questions"]],
                         ["Determine the primary category of this alert.",
                          "Determine the primary category of this alert."][:1])
        question = item["questions"][0]
        self.assertEqual(question["options"][1]["label"], "mfa_error - MFA processing problem")
        target = item["targets"][question["key"]]
        self.assertEqual(target["answer"], question["options"][1]["key"])
        self.assertAlmostEqual(sum(target["probs"].values()), 1.0, places=6)


class ProceduralTests(unittest.TestCase):
    def row(self):
        questions = {
            "starts_before_noon": {"type": "score", "criteria": [str(index) for index in range(10)],
                                   "instructions": "How many tasks start before 12:00?"},
            "done_by_deadline": {"type": "noul", "instructions": "Does the last task end at or before 13:20?"},
            "longest_task": {"type": "choice", "instructions": "Which task takes the longest?",
                             "criteria": {"backup check": "backup check", "client call": "client call"}},
        }
        answers = {
            "starts_before_noon": {"type": "score", "score": 6.0,
                                   "probabilities": {str(index): (1.0 if index == 6 else 0.0)
                                                     for index in range(10)}},
            "done_by_deadline": {"type": "noul", "noul": 0.0},
            "longest_task": {"type": "choice", "choice": "client call",
                             "probabilities": {"backup check": 0.0, "client call": 1.0}},
        }
        return (0, {"id": "arithmetic:train:0", "task": "arithmetic", "level": 0,
                    "state": "Starting at 12:00: backup check (25 min), then planning (15 min).",
                    "questions": json.dumps(questions), "answers": json.dumps(answers)})

    def test_native_question_keys_are_preserved(self):
        items, _ = run("procedural", [self.row()], slug="procedural-typed-decisions")
        item = items[0]
        self.assertEqual([q["key"] for q in item["questions"]],
                         ["starts_before_noon", "done_by_deadline", "longest_task"])
        self.assertTrue(all(q["origin"] == "source" for q in item["questions"]))
        self.assertEqual(item["meta"]["native_task"], "arithmetic")

    def test_ten_level_score_keeps_all_levels_and_integer_answer(self):
        items, _ = run("procedural", [self.row()], slug="procedural-typed-decisions")
        question = next(q for q in items[0]["questions"] if q["key"] == "starts_before_noon")
        target = items[0]["targets"]["starts_before_noon"]
        self.assertEqual(question["scale"]["max"], 9)
        self.assertEqual(len(question["scale"]["labels"]), 10)
        self.assertEqual(target["answer"], "6")
        self.assertEqual(len(target["probs"]), 10)
        self.assertAlmostEqual(sum(target["probs"].values()), 1.0, places=6)

    def test_noul_scalar_becomes_yes_no_distribution(self):
        items, _ = run("procedural", [self.row()], slug="procedural-typed-decisions")
        question = next(q for q in items[0]["questions"] if q["key"] == "done_by_deadline")
        target = items[0]["targets"]["done_by_deadline"]
        self.assertEqual([o["key"] for o in question["options"]], ["yes", "no"])
        self.assertEqual(target["probs"], {"yes": 0.0, "no": 1.0})
        self.assertEqual(target["answer"], "no")
        self.assertIn("noul_options_canonical", items[0]["meta"]["quality_flags"])

    def test_choice_answer_is_reconstructable_from_options(self):
        items, _ = run("procedural", [self.row()], slug="procedural-typed-decisions")
        question = next(q for q in items[0]["questions"] if q["key"] == "longest_task")
        target = items[0]["targets"]["longest_task"]
        labels = {option["key"]: option["label"] for option in question["options"]}
        self.assertEqual(labels[target["answer"]], "client call")
        self.assertEqual(target["probs"][target["answer"]], 1.0)


class ValidatorTests(unittest.TestCase):
    def item(self):
        rows = [jev_row(0, "choice", ["a", "b"], [0.25, 0.75],
                        question="Pick one.", family="agent", domain="tool_selection",
                        state="scenario")]
        return run("jev_typed", rows)[0][0]

    def test_valid_item_passes(self):
        self.assertEqual(convert.native_item_errors(self.item()), [])

    def test_missing_origin_is_rejected(self):
        item = self.item()
        del item["questions"][0]["origin"]
        self.assertTrue(any("origin" in error for error in convert.native_item_errors(item)))

    def test_source_key_must_equal_key(self):
        item = self.item()
        item["questions"][0]["source_key"] = "renamed"
        self.assertTrue(any("source_key" in error for error in convert.native_item_errors(item)))

    def test_probs_must_align_with_options(self):
        item = self.item()
        item["targets"][item["questions"][0]["key"]]["probs"] = {"a": 1.0}
        errors = convert.native_item_errors(item)
        self.assertTrue(any("不等长" in error for error in errors), errors)

    def test_probs_must_normalize(self):
        item = self.item()
        item["targets"][item["questions"][0]["key"]]["probs"] = {"a": 0.2, "b": 0.2}
        self.assertTrue(any("未归一" in error for error in convert.native_item_errors(item)))

    def test_target_without_question_is_rejected(self):
        item = self.item()
        item["targets"]["ghost"] = {"answer": "a"}
        self.assertTrue(any("ghost" in error for error in convert.native_item_errors(item)))


class IdAndReportTests(unittest.TestCase):
    def test_ids_are_stable_and_unique(self):
        rows = [jev_row(index, "noul", ["false", "true"], [1.0, 0.0],
                        question=f"Question number {index}?") for index in range(3)]
        first, _ = run("jev_typed", rows)
        second, _ = run("jev_typed", rows)
        self.assertEqual([item["id"] for item in first], [item["id"] for item in second])
        self.assertEqual(len({item["id"] for item in first}), 3)
        for item in first:
            self.assertTrue(convert.NATIVE_ID_PATTERN.match(item["id"]), item["id"])

    def test_report_counts_native_targets(self):
        rows = [jev_row(0, "choice", ["a", "b"], [0.2, 0.8], family="agent", domain="tool_selection"),
                jev_row(1, "noul", ["false", "true"], [1.0, 0.0])]
        _items, report = run("jev_typed", rows)
        self.assertEqual(report["items"], 2)
        self.assertEqual(report["with_targets"], 2)
        self.assertEqual(report["native_target_rate"], 1.0)
        self.assertEqual(report["target_classes"]["hard_label"], 0)   # 原生分布不是硬标签


class MainIntegrationTests(unittest.TestCase):
    def test_native_default_output_and_scope_restriction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for slug, converter in (("jev-distill-v3", "jev_typed"),
                                    ("prosocial-dialog", "prosocial_dialog")):
                directory = root / slug
                directory.mkdir()
                (directory / "manifest.json").write_text(
                    json.dumps(manifest(converter)), encoding="utf-8")
                (directory / "rows.jsonl").write_text(json.dumps(
                    {"row_idx": 0, "row": jev_row(0, "noul", ["false", "true"], [1.0, 0.0])[1]}) + "\n",
                    encoding="utf-8")
            out = root / "items.jsonl"
            code = convert.main(["--native", "--raw-root", str(root), "--out", str(out),
                                 "--created-at", CREATED_AT, "--taxonomy", str(HERE / "taxonomy.py")])
            self.assertEqual(code, 0)   # 范围外单元记在 out_of_scope，不算失败
            written = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(written), 1)
            self.assertEqual(written[0]["questions"][0]["origin"], "source")
            # 原生模式的报告必须写在独立的 items.native.report.json 下
            summary = json.loads((root / "items.native.report.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["mode"], "native")
            self.assertEqual([unit["slug"] for unit in summary["out_of_scope"]], ["prosocial-dialog"])
            self.assertEqual(summary["skipped_units"], [])
            # 且不得覆盖共享的 convert-report.json（这是被复核抓到的回归点）
            self.assertFalse((root / "convert-report.json").exists())


if __name__ == "__main__":
    unittest.main()
