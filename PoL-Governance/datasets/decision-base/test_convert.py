#!/usr/bin/env python3
"""convert.py 的离线测试：全部用内存 fixture，不联网、不依赖已抓取的原始数据。

覆盖：id 确定性、契约校验（taxonomy.item_errors）、各来源映射规则、
直接映射 vs 有据可查映射的区分、硬标签不得伪装成概率、未映射的源答案不丢、
去重、超长 state 截断、不完整 manifest 跳过、重复转换结果一致。
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


convert = load_module("decision_base_convert", HERE / "convert.py")
taxonomy = convert.load_taxonomy(HERE / "taxonomy.py")

CREATED_AT = "2026-09-30T12:00:00+00:00"
REVISION = "f" * 40


def manifest(**overrides):
    base = {"dataset": "Example/data", "revision": REVISION, "config": "default",
            "split": "train", "license": "apache-2.0", "lang": "en",
            "converter": "jev_typed", "complete": True, "revision_stable": True,
            "source_url": "https://huggingface.co/datasets/Example/data"}
    base.update(overrides)
    return base


def context(**overrides):
    options = {"mappings": "all", "question_lang": "zh", "created_at": CREATED_AT,
               "log": lambda *_a, **_k: None}
    options.update(overrides)
    return convert.Context(taxonomy, **options)


def run(slug, rows, converter, **overrides):
    """把 (row_idx, payload) 列表跑过某个转换器，返回 (items, report)。"""
    data = manifest(converter=converter, **overrides.pop("manifest", {}))
    return convert.convert_unit(context(**overrides), slug, data, rows)


def jev_row(row_idx, kind, options, target, family="agent", domain="tool_selection",
            state=None, question="Which option is correct?"):
    return (row_idx, {"id": f"v3_{row_idx:04x}_x", "kind": kind, "options": options,
                      "target": target, "state": state or f"scenario {row_idx}",
                      "question": question, "domain": domain, "family": family,
                      "source": "yuri_v3"})


class IdTests(unittest.TestCase):
    def test_id_is_deterministic_and_well_formed(self):
        first = convert.item_id("slug", "D", REVISION, "c", "train", 7)
        second = convert.item_id("slug", "D", REVISION, "c", "train", 7)
        self.assertEqual(first, second)
        self.assertTrue(taxonomy.id_is_canonical(first), first)

    def test_id_changes_with_every_component(self):
        base = convert.item_id("slug", "D", REVISION, "c", "train", 7)
        variants = [
            convert.item_id("other", "D", REVISION, "c", "train", 7),
            convert.item_id("slug", "E", REVISION, "c", "train", 7),
            convert.item_id("slug", "D", "0" * 40, "c", "train", 7),
            convert.item_id("slug", "D", REVISION, "d", "train", 7),
            convert.item_id("slug", "D", REVISION, "c", "test", 7),
            convert.item_id("slug", "D", REVISION, "c", "train", 8),
        ]
        self.assertEqual(len({base, *variants}), 7)


class JevTypedTests(unittest.TestCase):
    def test_choice_row_becomes_candidate_question_with_distribution(self):
        rows = [jev_row(0, "choice", ["alpha", "beta", "gamma"], [0.1, 0.7, 0.2])]
        items, report = run("jev", rows, "jev_typed")
        self.assertEqual(report["items"], 1)
        item = items[0]
        self.assertEqual(item["domain"], "decision_mechanics")
        self.assertEqual(item["lang"], "en")
        candidate = [q for q in item["questions"] if q["key"] == "next_step_candidate"]
        self.assertEqual(len(candidate), 1)
        self.assertEqual([o["label"] for o in candidate[0]["options"]], ["alpha", "beta", "gamma"])
        target = item["targets"]["next_step_candidate"]
        self.assertEqual(target["answer"], candidate[0]["options"][1]["key"])
        self.assertAlmostEqual(sum(target["probs"].values()), 1.0, places=6)
        self.assertEqual(taxonomy.item_errors(item), [])

    def test_noul_and_score_rows_keep_source_answer_in_meta_only(self):
        rows = [jev_row(0, "noul", ["yes", "no"], [1.0, 0.0], family="knowledge"),
                jev_row(1, "score", ["0", "1", "2", "3", "4", "5"],
                        [0.01, 0.01, 0.05, 0.41, 0.51, 0.01], family="knowledge")]
        items, report = run("jev", rows, "jev_typed")
        self.assertEqual(len(items), 2)
        for item in items:
            self.assertNotIn("targets", item)
            self.assertIn("source_target_unmapped", " ".join(item["meta"]["quality_flags"]))
            self.assertEqual(item["meta"]["source_record"]["kind"],
                             "noul" if item["domain"] == "knowledge_reasoning" and
                             item["meta"]["source_record"]["options"] == ["yes", "no"] else "score")
        self.assertEqual(items[0]["domain"], "knowledge_reasoning")

    def test_family_table_maps_knowledge_and_agent(self):
        rows = [jev_row(0, "noul", ["yes", "no"], [1.0, 0.0], family="knowledge"),
                jev_row(1, "noul", ["yes", "no"], [1.0, 0.0], family="agent")]
        items, _ = run("jev", rows, "jev_typed")
        self.assertEqual([item["domain"] for item in items],
                         ["knowledge_reasoning", "decision_mechanics"])

    def test_unmappable_domain_is_skipped_not_guessed(self):
        rows = [(0, {"kind": "noul", "options": ["yes", "no"], "target": [1.0, 0.0],
                     "state": "s", "question": "q", "family": "", "domain": ""})]
        items, report = run("jev", rows, "jev_typed")
        self.assertEqual(items, [])
        self.assertEqual(report["skipped"]["domain_unmapped"], 1)

    def test_empty_state_is_skipped(self):
        rows = [jev_row(0, "noul", ["yes", "no"], [1.0, 0.0], state="   ")]
        items, report = run("jev", rows, "jev_typed")
        self.assertEqual(items, [])
        self.assertEqual(report["skipped"]["empty_state"], 1)

    def test_choice_with_too_many_options_is_not_mapped(self):
        rows = [jev_row(0, "choice", [f"o{index}" for index in range(17)],
                        [1 / 17] * 17)]
        items, _ = run("jev", rows, "jev_typed")
        self.assertEqual(len(items), 1)
        self.assertNotIn("targets", items[0])

    def test_duplicate_state_is_emitted_once(self):
        row = jev_row(0, "noul", ["yes", "no"], [1.0, 0.0])
        second = (1, dict(row[1]))
        items, report = run("jev", [row, second], "jev_typed")
        self.assertEqual(len(items), 1)
        self.assertEqual(report["duplicate_states"], 1)


class OpenJevTests(unittest.TestCase):
    def rows(self):
        common = {"group_id": "case:1", "split": "train", "source": "customer-control-v1",
                  "state_json": json.dumps("Customer needs a password reset."),
                  "original_line_number": 42}
        first = dict(common, id="case:1:category", kind="choice", question="Pick a category.",
                     options=["billing", "account"], target=[0.2, 0.8])
        second = dict(common, id="case:1:urgent", kind="noul", question="Is it urgent?",
                      options=["yes", "no"], target=[0.0, 1.0])
        return [(0, first), (1, second)]

    def test_group_becomes_one_item_with_source_questions_in_meta(self):
        items, report = run("open", self.rows(), "open_jev")
        self.assertEqual((len(items), report["items"]), (1, 1))
        item = items[0]
        self.assertEqual(item["state"], "Customer needs a password reset.")
        self.assertEqual(item["source"]["row"], 0)          # 取组内首行
        self.assertEqual(item["meta"]["group_id"], "case:1")
        self.assertEqual(len(item["meta"]["source_questions"]), 2)
        self.assertEqual(item["meta"]["source_questions"][1]["key"], "urgent")
        self.assertEqual(taxonomy.item_errors(item), [])
        self.assertIn("grouped_rows:2", item["meta"]["quality_flags"])

    def test_choice_member_maps_to_candidate_question(self):
        items, _ = run("open", self.rows(), "open_jev")
        target = items[0]["targets"]["next_step_candidate"]
        self.assertEqual(target["probs"], {"billing": 0.2, "account": 0.8})
        self.assertEqual(target["answer"], "account")

    def test_core_questions_present(self):
        items, _ = run("open", self.rows(), "open_jev")
        keys = {question["key"] for question in items[0]["questions"]}
        self.assertTrue(set(taxonomy.CORE_KEYS["decision_mechanics"]) <= keys)


class JevDecisionsTests(unittest.TestCase):
    def row(self, row_idx, source="nvidia/Nemotron-RL", candidate_count=3):
        candidates = [{"id": f"c{index}", "name": f"action_{index}"}
                      for index in range(candidate_count)]
        return (row_idx, {
            "id": f"hash{row_idx}", "source": source, "decision_type": "tool_choice",
            "status": "trainable",
            "state": {"system": "long system policy", "user_goal": f"goal {row_idx}",
                      "history": [], "environment_json": "{}"},
            "candidates": candidates,
            "target": {"candidate_id": "c1", "action_name": "action_1", "arguments_json": "{}"}})

    def test_hard_label_answer_without_probs(self):
        items, _ = run("jd", [self.row(0)], "jev_decisions_v1")
        item = items[0]
        self.assertEqual(item["state"], "goal 0")
        target = item["targets"]["next_step_candidate"]
        self.assertEqual(target["answer"], "action_1")
        self.assertNotIn("probs", target)
        self.assertIn("target_is_hard_label:no_probs", item["meta"]["quality_flags"])
        self.assertEqual(taxonomy.item_errors(item), [])

    def test_stratum_cap_limits_one_source(self):
        rows = [self.row(index) for index in range(10)]
        items, report = run("jd", rows, "jev_decisions_v1", stratum_cap=0.3)
        self.assertEqual(len(items), 3)
        self.assertEqual(report["skipped"]["stratum_capped:nvidia/Nemotron-RL"], 7)

    def test_two_sources_split_the_cap(self):
        rows = ([self.row(index) for index in range(6)]
                + [self.row(index + 100, source="Open-SWE-Traces") for index in range(6)])
        items, _ = run("jd", rows, "jev_decisions_v1", stratum_cap=0.25)
        strata = {item["meta"]["stratum"] for item in items}
        self.assertEqual(strata, {"nvidia/Nemotron-RL", "Open-SWE-Traces"})

    def test_general_clean_shape_uses_answer_options_and_target_index(self):
        row = (0, {"id": "hash", "source": "nvidia/Nemotron-RL-Agentic-Conversational-Tool-Use-Pivot-v1",
                   "state": {"system": "policy", "user_goal": "reset my password", "history": []},
                   "question": "which option should be selected?",
                   "question_type": "choice",
                   "answer_options": [{"type": "action", "label": "verify_email",
                                       "description": "Verify identity."},
                                      {"type": "action", "label": "reset_password",
                                       "description": "Reset it."}],
                   "target_index": 1})
        items, _ = run("jd2", [row], "jev_decisions_v1", stratum_cap=1.0)
        item = items[0]
        self.assertEqual(item["state"], "reset my password")
        candidate = [q for q in item["questions"] if q["key"] == "next_step_candidate"][0]
        self.assertEqual([o["label"] for o in candidate["options"]],
                         ["verify_email", "reset_password"])
        target = item["targets"]["next_step_candidate"]
        self.assertEqual(target["answer"], candidate["options"][1]["key"])
        self.assertNotIn("probs", target)
        self.assertEqual(taxonomy.item_errors(item), [])

    def test_too_many_candidates_is_flagged_with_the_count(self):
        row = self.row(0, candidate_count=17)
        items, _ = run("jd3", [row], "jev_decisions_v1", stratum_cap=1.0)
        self.assertNotIn("targets", items[0])
        self.assertIn("source_target_unmapped:candidate_count:17",
                      items[0]["meta"]["quality_flags"])

    def test_missing_candidate_answer_is_flagged(self):
        row = self.row(0)
        row[1]["target"] = {"candidate_id": "nope", "action_name": "nope"}
        items, _ = run("jd", [row], "jev_decisions_v1")
        self.assertNotIn("targets", items[0])
        self.assertIn("source_target_unmapped:answer_not_in_candidates",
                      items[0]["meta"]["quality_flags"])


class ProsocialTests(unittest.TestCase):
    def row(self):
        return (0, {"context": "Some problematic utterance.", "response": "A prosocial reply.",
                    "rots": ["Be kind."], "safety_label": "__needs_caution__",
                    "safety_annotations": ["needs caution", "needs caution", "casual"],
                    "safety_annotation_reasons": ["r1", "r2", "r3"], "source": "sbic",
                    "etc": "", "dialogue_id": 1, "response_id": 0, "episode_done": False})

    def test_labels_stay_in_meta_and_no_targets_invented(self):
        items, _ = run("pd", [self.row()], "prosocial_dialog")
        item = items[0]
        self.assertEqual(item["domain"], "social_moral")
        self.assertEqual(item["state"], "Some problematic utterance.")
        self.assertNotIn("targets", item)
        meta = item["meta"]
        self.assertEqual(meta["safety_annotation_counts"],
                         {"needs caution": 2, "casual": 1})
        self.assertEqual(meta["response"], "A prosocial reply.")
        self.assertIn("source_labels_in_meta_only:context_safety", meta["quality_flags"])
        self.assertEqual(taxonomy.item_errors(item), [])


class EthicsTests(unittest.TestCase):
    def test_label_kept_in_meta_without_supervised_mapping(self):
        items, _ = run("eth", [(0, {"input": "I told the truth.", "label": 1})], "ethics",
                       manifest={"domain": "social_moral", "config": "commonsense"})
        item = items[0]
        self.assertNotIn("targets", item)
        self.assertEqual(item["meta"]["label"], 1)
        self.assertIn("label_semantics_unverified", item["meta"]["quality_flags"])


    def test_scenario_and_pairwise_configs_are_handled(self):
        rows = [(0, {"scenario": "Is this a good excuse?", "excuse": "No.", "label": 0}),
                (1, {"baseline": "I forgot my mask at the pet store.",
                     "less_pleasant": "I forgot my mask at the nursing home."})]
        items, report = run("eth2", rows, "ethics",
                            manifest={"domain": "social_moral", "config": "deontology"})
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["state"], "Is this a good excuse?")
        self.assertIn("Option A:", items[1]["state"])
        self.assertIn("Option B:", items[1]["state"])
        self.assertEqual(report["skipped"], {})


class HelpSteerTests(unittest.TestCase):
    def test_scores_kept_in_meta_and_state_contains_prompt_and_response(self):
        row = (0, {"prompt": "c#", "response": "C# is a language.", "helpfulness": 3,
                   "correctness": 4, "coherence": 4, "complexity": 2, "verbosity": 1})
        items, _ = run("hs", [row], "helpsteer2")
        item = items[0]
        self.assertEqual(item["domain"], "human_judgment")
        self.assertIn("c#", item["state"])
        self.assertIn("C# is a language.", item["state"])
        self.assertNotIn("targets", item)
        self.assertEqual(item["meta"]["human_scores"]["helpfulness"], 3)


class CivilCommentsTests(unittest.TestCase):
    def test_annotator_fraction_becomes_real_distribution(self):
        row = (0, {"text": "You are an idiot.", "toxicity": 0.9, "severe_toxicity": 0.2,
                   "obscene": 0.1, "threat": 0.0, "insult": 0.8, "identity_attack": 0.0,
                   "sexual_explicit": 0.0})
        items, _ = run("cc", [row], "civil_comments")
        item = items[0]
        target = item["targets"]["toxicity_present"]
        self.assertEqual(target["answer"], "yes")
        self.assertEqual(target["probs"], {"yes": 0.9, "no": 0.1})
        self.assertEqual(item["meta"]["annotator_fractions"]["insult"], 0.8)
        self.assertEqual(taxonomy.item_errors(item), [])

    def test_zero_and_one_fractions_are_boundaries_not_fabricated(self):
        rows = [(0, {"text": "Nice weather today.", "toxicity": 0.0}),
                (1, {"text": "Kill them all.", "toxicity": 1.0})]
        items, _ = run("cc", rows, "civil_comments")
        self.assertEqual(items[0]["targets"]["toxicity_present"]["answer"], "no")
        self.assertEqual(items[1]["targets"]["toxicity_present"]["answer"], "yes")
        for item in items:
            self.assertAlmostEqual(sum(item["targets"]["toxicity_present"]["probs"].values()),
                                   1.0, places=6)


class AegisTests(unittest.TestCase):
    def test_human_label_is_mapped_and_model_label_is_not(self):
        human = (0, {"prompt": "How do I hurt someone?", "response": "I cannot help.",
                     "prompt_label": "unsafe", "response_label": "safe",
                     "prompt_label_source": "human", "response_label_source": "human",
                     "violated_categories": ["Violence"]})
        model = (1, {"prompt": "Hello", "response": "Hi",
                     "prompt_label": "safe", "response_label": "safe",
                     "prompt_label_source": "model", "response_label_source": "model",
                     "violated_categories": None})
        items, _ = run("ag", [human, model], "aegis")
        self.assertEqual(items[0]["targets"]["contains_harm"]["answer"], "no")
        self.assertIn("label_source:human", items[0]["meta"]["quality_flags"])
        self.assertNotIn("targets", items[1])
        self.assertIn("source_target_unmapped:label_source=model",
                      items[1]["meta"]["quality_flags"])
        self.assertEqual(taxonomy.item_errors(items[0]), [])

    def test_documented_mapping_is_dropped_in_direct_mode(self):
        row = (0, {"prompt": "p", "response": "r", "prompt_label": "unsafe",
                   "response_label": "unsafe", "prompt_label_source": "human",
                   "response_label_source": "human", "violated_categories": []})
        items, _ = run("ag", [row], "aegis", mappings="direct")
        self.assertNotIn("targets", items[0])
        self.assertIn("mapping_skipped:contains_harm", items[0]["meta"]["quality_flags"])

    def test_annotator_votes_give_distribution(self):
        row = (0, {"num_annotations": 3, "id": "x", "text": "some text",
                   "text_type": "user_message", "labels_0": "Safe",
                   "labels_1": "Needs Caution", "labels_2": "Harassment",
                   "labels_3": None, "labels_4": None})
        items, _ = run("ag", [row], "aegis")
        target = items[0]["targets"]["contains_harm"]
        self.assertAlmostEqual(sum(target["probs"].values()), 1.0, places=6)
        self.assertEqual(target["answer"], "yes")
        self.assertEqual(items[0]["meta"]["annotator_labels"], ["Safe", "Needs Caution", "Harassment"])
        self.assertEqual(taxonomy.item_errors(items[0]), [])


class MoralStoriesTests(unittest.TestCase):
    def row(self, label="1"):
        return (0, {"ID": "story-1", "norm": "Keep children safe.",
                    "situation": "Kent watched his kids in the yard.",
                    "intention": "Kent wants security.",
                    "moral_action": "Kent installs cameras.",
                    "moral_consequence": "The kids feel safer.",
                    "immoral_action": "Kent installs an electric fence.",
                    "immoral_consequence": "A child gets shocked.", "label": label})

    def test_two_sided_items_with_direct_judgment_labels(self):
        items, report = run("ms", [self.row()], "moral_stories")
        self.assertEqual(len(items), 2)
        judgments = {item["meta"]["domain_rule"]: item["targets"]["moral_judgment"]["answer"]
                     for item in items}
        self.assertEqual(judgments, {"moral_stories:moral": "acceptable",
                                     "moral_stories:immoral": "wrong"})
        for item in items:
            self.assertEqual(taxonomy.item_errors(item), [])
            self.assertEqual(item["domain"], "social_moral")

    def test_two_items_from_one_row_have_distinct_ids(self):
        items, _ = run("ms", [self.row()], "moral_stories")
        ids = [item["id"] for item in items]
        self.assertEqual(len(set(ids)), 2)
        self.assertEqual([item["source"]["row"] for item in items], [0, 0])
        for item in items:
            self.assertTrue(taxonomy.id_is_canonical(item["id"]), item["id"])

    def test_label_flips_the_answers(self):
        items, _ = run("ms", [self.row(label="0")], "moral_stories")
        judgments = {item["meta"]["domain_rule"]: item["targets"]["moral_judgment"]["answer"]
                     for item in items}
        self.assertEqual(judgments, {"moral_stories:moral": "wrong",
                                     "moral_stories:immoral": "acceptable"})

    def test_documented_consequence_mapping_dropped_in_direct_mode(self):
        items, _ = run("ms", [self.row()], "moral_stories", mappings="direct")
        for item in items:
            self.assertNotIn("expected_consequence", item.get("targets", {}))
            self.assertIn("moral_judgment", item["targets"])
            self.assertIn("mapping_skipped:expected_consequence", item["meta"]["quality_flags"])


class AssemblyTests(unittest.TestCase):
    def test_every_item_passes_contract_validation(self):
        rows = [jev_row(0, "choice", ["a", "b"], [0.4, 0.6]),
                jev_row(1, "noul", ["yes", "no"], [1.0, 0.0], family="knowledge"),
                jev_row(2, "score", ["0", "1"], [0.5, 0.5], family="biology")]
        items, _ = run("mix", rows, "jev_typed")
        self.assertEqual(len(items), 3)
        for item in items:
            self.assertEqual(taxonomy.item_errors(item), [], item["id"])
            for field in ("id", "domain", "lang", "state", "questions", "source", "meta"):
                self.assertIn(field, item)
            for field in ("dataset", "revision", "config", "split", "row", "license", "url"):
                self.assertIn(field, item["source"])
            self.assertTrue(item["questions"])

    def test_conversion_is_reproducible(self):
        rows = [jev_row(0, "choice", ["a", "b"], [0.25, 0.75])]
        first, _ = run("rep", rows, "jev_typed")
        second, _ = run("rep", rows, "jev_typed")
        self.assertEqual(json.dumps(first, ensure_ascii=False), json.dumps(second, ensure_ascii=False))

    def test_long_state_is_clipped_with_flag(self):
        rows = [jev_row(0, "noul", ["yes", "no"], [1.0, 0.0], state="x" * 7000)]
        items, _ = run("long", rows, "jev_typed")
        self.assertEqual(len(items[0]["state"]), convert.MAX_STATE_CHARS + len(" […]"))
        self.assertIn("state_truncated", items[0]["meta"]["quality_flags"])

    def test_unknown_converter_raises(self):
        with self.assertRaises(KeyError):
            run("x", [], "does_not_exist")

    def test_created_at_is_taken_from_context(self):
        items, _ = run("ts", [jev_row(0, "noul", ["yes", "no"], [1.0, 0.0])], "jev_typed")
        self.assertEqual(items[0]["meta"]["created_at"], CREATED_AT)
        self.assertEqual(items[0]["meta"]["converter"], "convert.py")


class SystemoneLiteTests(unittest.TestCase):
    def row(self, row_idx=0):
        return (row_idx, {
            "task": "debate.winner",
            "state": json.dumps({"question": "We should open-source the core library",
                                 "side_a": {"label": "support"}}),
            "instructions": "Given the claims and evidence flags, who should win the debate?",
            "criteria_keys": ["A", "B"],
            "criteria_values": ["oppose: Side B", "support: Side A"],
            "label_alias": "A", "label_key": "oppose",
            "meta": json.dumps({"gym": "debate_judge", "schema": "choice"})})

    def test_criteria_become_options_and_label_alias_is_the_answer(self):
        items, _ = run("sl", [self.row()], "systemone_lite")
        item = items[0]
        candidate = [q for q in item["questions"] if q["key"] == "next_step_candidate"][0]
        self.assertEqual([o["label"] for o in candidate["options"]],
                         ["oppose: Side B", "support: Side A"])
        target = item["targets"]["next_step_candidate"]
        self.assertEqual(target["answer"], candidate["options"][0]["key"])
        self.assertNotIn("probs", target)
        self.assertIn("debate_judge", item["meta"]["gym"])
        self.assertIn("open-source", item["state"])
        self.assertEqual(taxonomy.item_errors(item), [])

    def test_missing_label_alias_leaves_targets_empty(self):
        row = self.row()
        row[1]["label_alias"] = "Z"
        items, _ = run("sl", [row], "systemone_lite")
        self.assertNotIn("targets", items[0])
        self.assertIn("source_target_unmapped:label_alias", items[0]["meta"]["quality_flags"])


class SystemOne270mTests(unittest.TestCase):
    def rows(self):
        prompt = ("<state>\n2026-09-21 ERROR NullPointerException in MFA module\n</state>\n\n"
                  "Question: Determine the primary category of this alert.\nOptions:\n"
                  "A. authentication - failed logins\nB. mfa_error - MFA processing problem\n"
                  "C. system_error - general error\n\nAnswer with one letter.\nAnswer:")
        common = {"prompt": prompt, "state_id": "abc123", "domain": "security alert",
                  "ambiguity": "clear", "entropy": 0.00186}
        first = dict(common, letters=["A", "B", "C"], target=[0.0001, 0.9998, 0.0001],
                     label="mfa_error", qtype="choice", n_options=3)
        second = dict(common, letters=["A", "B"], target=[0.0001, 0.9999], label="yes",
                      qtype="noul", n_options=2)
        return [(0, first), (1, second)]

    def test_state_block_is_extracted_and_grouped_by_state_id(self):
        items, report = run("k", self.rows(), "system_one_270m")
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["state"], "2026-09-21 ERROR NullPointerException in MFA module")
        self.assertEqual(item["meta"]["state_id"], "abc123")
        self.assertEqual(len(item["meta"]["source_questions"]), 2)
        self.assertEqual(report["items"], 1)

    def test_choice_row_distribution_is_mapped(self):
        items, _ = run("k", self.rows(), "system_one_270m")
        candidate = [q for q in items[0]["questions"] if q["key"] == "next_step_candidate"][0]
        self.assertEqual([o["label"] for o in candidate["options"]],
                         ["authentication - failed logins", "mfa_error - MFA processing problem",
                          "system_error - general error"])
        target = items[0]["targets"]["next_step_candidate"]
        self.assertEqual(target["answer"], candidate["options"][1]["key"])
        self.assertAlmostEqual(sum(target["probs"].values()), 1.0, places=6)
        self.assertEqual(taxonomy.item_errors(items[0]), [])

    def test_unparsable_options_leave_targets_empty(self):
        rows = self.rows()
        rows[0][1]["prompt"] = rows[0][1]["prompt"].replace("B. mfa_error", "B mfa_error")
        items, _ = run("k", rows, "system_one_270m")
        self.assertNotIn("targets", items[0])
        self.assertIn("source_target_unmapped:qtype_or_options", items[0]["meta"]["quality_flags"])


class ProceduralTests(unittest.TestCase):
    def row(self):
        questions = {"longest_task": {"type": "choice", "instructions": "Which task takes longest?",
                                      "criteria": {"backup check": "backup check",
                                                   "planning": "planning",
                                                   "client call": "client call"}},
                     "done_by_deadline": {"type": "noul",
                                          "instructions": "Does the last task end before 13:20?"},
                     "starts_before_noon": {"type": "score", "criteria": [str(index) for index in range(10)],
                                            "instructions": "How many tasks start before 12:00?"}}
        answers = {"longest_task": {"type": "choice", "choice": "client call",
                                    "probabilities": {"backup check": 0.0, "planning": 0.0,
                                                      "client call": 1.0}, "confidence": 1.0},
                   "done_by_deadline": {"type": "noul", "noul": 0.0},
                   "starts_before_noon": {"type": "score", "score": 0.0,
                                          "probabilities": {str(index): (1.0 if index == 0 else 0.0)
                                                            for index in range(10)}}}
        return (0, {"id": "arithmetic:train:0", "task": "arithmetic", "level": 0,
                    "state": "Starting at 12:00: backup check (25 min), then planning (15 min).",
                    "questions": json.dumps(questions), "answers": json.dumps(answers)})

    def test_multi_question_row_maps_only_the_choice_head(self):
        items, _ = run("pr", [self.row()], "procedural")
        item = items[0]
        self.assertEqual(len(item["meta"]["source_questions"]), 3)
        target = item["targets"]["next_step_candidate"]
        candidate = [q for q in item["questions"] if q["key"] == "next_step_candidate"][0]
        self.assertEqual(target["answer"], candidate["options"][2]["key"])
        self.assertEqual(target["probs"], {"backup_check": 0.0, "planning": 0.0, "client_call": 1.0})
        self.assertEqual(item["meta"]["source_task"], "arithmetic")
        self.assertEqual(taxonomy.item_errors(item), [])

    def test_ten_level_score_is_not_forced_into_five_levels(self):
        items, _ = run("pr", [self.row()], "procedural")
        keys = {question["key"] for question in items[0]["questions"]}
        self.assertNotIn("risk_of_action", items[0].get("targets", {}))
        self.assertTrue(keys <= set(taxonomy.DOMAIN_KEYS["decision_mechanics"]))

    def test_state_that_is_json_is_rendered(self):
        row = self.row()
        row[1]["state"] = json.dumps({"events": [{"step": 1, "object": "item_1"}]})
        items, _ = run("pr", [row], "procedural")
        self.assertIn("item_1", items[0]["state"])


class ReportingTests(unittest.TestCase):
    def test_native_target_rate_is_reported_per_unit(self):
        rows = [jev_row(0, "choice", ["a", "b"], [0.2, 0.8]),
                jev_row(1, "noul", ["yes", "no"], [1.0, 0.0], family="knowledge")]
        items, report = run("rate", rows, "jev_typed")
        self.assertEqual(len(items), 2)
        self.assertEqual(report["with_targets"], 1)
        self.assertEqual(report["native_target_rate"], 0.5)
        self.assertEqual(report["pending_external_answers"], 1)
        self.assertEqual(report["target_classes"],
                         {"direct": 1, "documented": 0, "hard_label": 0, "distribution": 0})
        self.assertEqual(report["by_domain_with_targets"], {"decision_mechanics": 1})

    def test_documented_targets_are_counted_separately(self):
        row = (0, {"prompt": "p", "response": "r", "prompt_label": "unsafe",
                   "response_label": "unsafe", "prompt_label_source": "human",
                   "response_label_source": "human", "violated_categories": []})
        _items, report = run("ag", [row], "aegis")
        self.assertEqual(report["target_classes"],
                         {"direct": 0, "documented": 1, "hard_label": 0, "distribution": 0})
        self.assertEqual(report["native_target_rate_direct_only"], 0.0)

    def test_meta_payload_is_capped_with_digest(self):
        rows = [jev_row(0, "noul", ["yes", "no"], [1.0, 0.0], question="Q" * 9000)]
        items, _ = run("big", rows, "jev_typed")
        record = items[0]["meta"]["source_record"]
        self.assertTrue(record["_truncated"])
        self.assertGreater(record["_original_bytes"], convert.META_PAYLOAD_BYTES)
        self.assertRegex(record["_sha256"], r"^[0-9a-f]{64}$")
        self.assertLessEqual(len(record["_preview"]), 2048)
        self.assertIn("meta_truncated:source_record", items[0]["meta"]["quality_flags"])
        self.assertEqual(taxonomy.item_errors(items[0]), [])

    def test_line_separators_are_escaped_so_jsonl_stays_line_oriented(self):
        rows = [jev_row(0, "noul", ["yes", "no"], [1.0, 0.0],
                        state="first part\u2028second part")]
        items, _ = run("sep", rows, "jev_typed")
        line = convert.jsonl_line(items[0])
        self.assertEqual(line.count("\n"), 1)
        self.assertNotIn("\u2028", line)
        self.assertIn("\\u2028", line)
        restored = json.loads(line)
        self.assertEqual(restored["state"], "first part\u2028second part")
        self.assertEqual(len(convert.jsonl_line(items[0]).splitlines()), 1)

    def test_small_payloads_are_not_touched(self):
        rows = [jev_row(0, "noul", ["yes", "no"], [1.0, 0.0])]
        items, _ = run("small", rows, "jev_typed")
        self.assertIn("options", items[0]["meta"]["source_record"])
        self.assertNotIn("meta_truncated:source_record", items[0]["meta"]["quality_flags"])


class MainIntegrationTests(unittest.TestCase):
    def test_main_writes_items_and_visible_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "unit"
            directory.mkdir()
            (directory / "manifest.json").write_text(
                json.dumps(manifest(converter="jev_typed")), encoding="utf-8")
            rows = [jev_row(0, "choice", ["a", "b"], [0.3, 0.7]),
                    jev_row(1, "noul", ["yes", "no"], [1.0, 0.0], family="knowledge")]
            (directory / "rows.jsonl").write_text(
                "\n".join(json.dumps({"row_idx": row, "row": payload}) for row, payload in rows)
                + "\n", encoding="utf-8")
            out = root / "items.jsonl"
            code = convert.main(["--raw-root", str(root), "--out", str(out),
                                 "--created-at", CREATED_AT, "--taxonomy",
                                 str(HERE / "taxonomy.py")])
            self.assertEqual(code, 0)
            written = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(written), 2)
            summary = json.loads((out.with_name("convert-report.json")).read_text(encoding="utf-8"))
            self.assertEqual(summary["mappings_used"], "all")
            self.assertEqual(summary["mappings_default"], "all")
            self.assertIn("documented", summary["mappings_default_note"])
            self.assertEqual(summary["native_target_rate"], 0.5)
            self.assertEqual(summary["pending_external_answers"], 1)
            self.assertEqual(summary["by_domain_detail"]["decision_mechanics"]["with_targets"], 1)

    def test_main_reports_incomplete_units_as_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / "partial"
            directory.mkdir()
            (directory / "manifest.json").write_text(
                json.dumps(manifest(complete=False)), encoding="utf-8")
            (directory / "rows.jsonl").write_text("", encoding="utf-8")
            out = root / "items.jsonl"
            code = convert.main(["--raw-root", str(root), "--out", str(out),
                                 "--created-at", CREATED_AT])
            self.assertEqual(code, 1)
            summary = json.loads((out.with_name("convert-report.json")).read_text(encoding="utf-8"))
            self.assertEqual(summary["skipped_units"][0]["slug"], "partial")


class RawRootTests(unittest.TestCase):
    def test_load_units_skips_incomplete_and_unstable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for slug, extra in (("good", {}), ("partial", {"complete": False}),
                                ("unstable", {"revision_stable": False})):
                directory = root / slug
                directory.mkdir()
                (directory / "rows.jsonl").write_text("{}\n", encoding="utf-8")
                payload = manifest(complete=True, revision_stable=True)
                payload.update(extra)
                (directory / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
            units = {slug: problem for slug, _manifest, _rows, problem in
                     convert.load_units(root)}
            self.assertIsNone(units["good"])
            self.assertIn("未完成", units["partial"])
            self.assertIn("不可信", units["unstable"])

    def test_read_rows_respects_limit_and_skips_bad_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rows.jsonl"
            path.write_text("\n".join([json.dumps({"row_idx": 0, "row": {"a": 1}}),
                                       "not json",
                                       json.dumps({"row_idx": 1, "row": {"a": 2}})]),
                            encoding="utf-8")
            rows = convert.read_rows(path, limit=1)
            self.assertEqual(rows, [(0, {"a": 1})])


if __name__ == "__main__":
    unittest.main()
