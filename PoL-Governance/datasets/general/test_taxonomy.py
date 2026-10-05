"""taxonomy.py 自检：覆盖域、问题键形状、构造/校验 API、与 PoL2 本体一致。"""

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import taxonomy  # noqa: E402


class DomainsTest(unittest.TestCase):
    def test_six_domains_in_readme_order(self):
        self.assertEqual(taxonomy.DOMAINS, (
            "decision_mechanics", "human_judgment", "social_moral",
            "risk_harm", "knowledge_reasoning", "pol2_axis"))

    def test_no_fallback_domain(self):
        for forbidden in ("unknown", "other", "misc"):
            self.assertNotIn(forbidden, taxonomy.DOMAINS)

    def test_every_domain_has_enough_keys_and_core(self):
        for domain in taxonomy.DOMAINS:
            self.assertGreaterEqual(len(taxonomy.DOMAIN_KEYS[domain]), 5, domain)
            self.assertTrue(taxonomy.CORE_KEYS[domain], domain)

    def test_core_keys_are_applicable_to_their_domain(self):
        for domain, keys in taxonomy.CORE_KEYS.items():
            for key in keys:
                self.assertIn(key, taxonomy.DOMAIN_KEYS[domain])
                self.assertIn(domain, taxonomy.key_spec(key).domains)

    def test_keys_for_domain_rejects_unknown(self):
        with self.assertRaises(KeyError):
            taxonomy.keys_for_domain("nope")
        with self.assertRaises(KeyError):
            taxonomy.core_keys("nope")


class KeySpecTest(unittest.TestCase):
    def test_every_key_has_kind_domain_criterion_and_prompts(self):
        self.assertGreaterEqual(len(taxonomy.QUESTION_KEYS), 60)
        for key, spec in taxonomy.QUESTION_KEYS.items():
            self.assertEqual(key, spec.key)
            self.assertIn(spec.kind, taxonomy.KINDS, key)
            self.assertTrue(spec.domains, key)
            for domain in spec.domains:
                self.assertIn(domain, taxonomy.DOMAINS, key)
            for text in (spec.criterion, spec.prompt_zh, spec.prompt_en):
                self.assertIsInstance(text, str, key)
                self.assertTrue(text.strip(), key)

    def test_choice_keys_have_2_to_16_unique_options(self):
        for key, spec in taxonomy.QUESTION_KEYS.items():
            if spec.kind != "choice":
                continue
            if spec.options_from_state:
                self.assertEqual(spec.options, (), key)
                continue
            self.assertGreaterEqual(len(spec.options), taxonomy.MIN_CHOICE_OPTIONS, key)
            self.assertLessEqual(len(spec.options), taxonomy.MAX_CHOICE_OPTIONS, key)
            keys = [option[0] for option in spec.options]
            self.assertEqual(len(keys), len(set(keys)), key)
            for option_key, zh, en in spec.options:
                self.assertTrue(option_key.strip(), key)
                self.assertTrue(zh.strip() and en.strip(), key)

    def test_score_keys_are_0_to_4_with_matching_labels(self):
        scored = [spec for spec in taxonomy.QUESTION_KEYS.values() if spec.kind == "score"]
        self.assertGreaterEqual(len(scored), 4)
        for spec in scored:
            low, high, labels = spec.scale
            self.assertEqual((low, high), (0, 4), spec.key)
            self.assertEqual(len(labels), high - low + 1, spec.key)

    def test_noul_spec_has_fixed_yes_no(self):
        question = taxonomy.build_question("contains_harm")
        self.assertEqual([o["key"] for o in question["options"]], ["yes", "no"])

    def test_options_from_state_requires_options(self):
        with self.assertRaises(ValueError):
            taxonomy.build_question("next_step_candidate")
        question = taxonomy.build_question(
            "next_step_candidate",
            options=[{"key": "a", "label": "A"}, {"key": "b", "label": "B"}])
        self.assertEqual([o["key"] for o in question["options"]], ["a", "b"])

    def test_fixed_choice_options_reject_override(self):
        with self.assertRaises(ValueError):
            taxonomy.build_question("action_selection", options=[{"key": "x", "label": "X"},
                                                                 {"key": "y", "label": "Y"}])

    def test_noul_rejects_options(self):
        with self.assertRaises(ValueError):
            taxonomy.build_question("contains_harm", options=[{"key": "y", "label": "Y"}])

    def test_aliases_resolve_and_are_not_canonical_keys(self):
        for alias, canonical in taxonomy.QUESTION_KEY_ALIASES.items():
            self.assertNotIn(alias, taxonomy.QUESTION_KEYS, alias)
            self.assertEqual(taxonomy.resolve_key(alias), canonical)
            self.assertIs(taxonomy.key_spec(alias), taxonomy.QUESTION_KEYS[canonical])
        with self.assertRaises(KeyError):
            taxonomy.resolve_key("no_such_key")

    def test_legacy_polarity_values_map_to_ontology_enum(self):
        self.assertEqual(taxonomy.normalize_option("interaction_polarity", "neutral"), "neither")
        self.assertEqual(taxonomy.normalize_option("interaction_polarity", "uncertain"), "unclear")
        self.assertEqual(taxonomy.normalize_answer("contains_harm", True), "yes")
        with self.assertRaises(KeyError):
            taxonomy.normalize_option("interaction_polarity", "banana")

    def test_pol2_axis_binary_keys_cover_all_15_issues(self):
        self.assertEqual(len(taxonomy.POL2_AXIS_KEYS), 15)
        for key in taxonomy.POL2_AXIS_KEYS:
            self.assertIn(key, taxonomy.DOMAIN_KEYS["pol2_axis"])
            self.assertEqual(taxonomy.key_spec(key).kind, "noul")
        self.assertEqual(len(taxonomy.key_spec("pol2_issue").options), 15)
        self.assertEqual(len(taxonomy.key_spec("love_language").options), 16)
        self.assertEqual(len(taxonomy.key_spec("mitigation").options), 9)
        self.assertEqual(len(taxonomy.key_spec("recommended_action").options), 5)


class BuildTest(unittest.TestCase):
    def test_build_questions_defaults_to_core(self):
        for domain in taxonomy.DOMAINS:
            questions = taxonomy.build_questions(domain)
            self.assertEqual([q["key"] for q in questions], list(taxonomy.CORE_KEYS[domain]))
            for question in questions:
                self.assertEqual(taxonomy.validate_question(question), [])

    def test_build_questions_accepts_explicit_keys_and_lang(self):
        questions = taxonomy.build_questions("risk_harm", ["contains_harm"], lang="en")
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["prompt"], taxonomy.key_spec("contains_harm").prompt_en)

    def test_build_questions_rejects_empty_selection(self):
        with self.assertRaises(ValueError):
            taxonomy.build_questions("risk_harm", [])

    def test_questions_are_json_serializable(self):
        payload = [taxonomy.build_question(key) for key in taxonomy.QUESTION_KEYS
                   if not taxonomy.key_spec(key).options_from_state]
        text = json.dumps(payload, ensure_ascii=False)
        self.assertIn("contains_harm", text)

    def test_validate_question_catches_drift(self):
        good = taxonomy.build_questions("risk_harm")[0]
        self.assertEqual(taxonomy.validate_question(good), [])
        self.assertTrue(taxonomy.validate_question({**good, "kind": "score"}))
        self.assertTrue(taxonomy.validate_question({**good, "prompt": "  "}))
        self.assertTrue(taxonomy.validate_question({"key": "contains_harm_it", "kind": "noul"}))
        self.assertTrue(taxonomy.validate_question({"key": "contains_harm", "kind": "noul",
                                                    "prompt": "p",
                                                    "options": [{"key": "true", "label": "T"}]}))
        self.assertTrue(taxonomy.validate_question("not a dict"))

    def test_validate_question_rejects_alias_and_foreign_options(self):
        alias = {"key": "status", "kind": "choice", "prompt": "p",
                 "options": [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}]}
        self.assertTrue(taxonomy.validate_question(alias))

    def test_validate_target_accepts_canonical_answers(self):
        self.assertEqual(taxonomy.validate_target("contains_harm", {"answer": "yes"}), [])
        self.assertEqual(taxonomy.validate_target("contains_harm",
                                                  {"probs": {"yes": 0.7, "no": 0.3}}), [])
        self.assertEqual(taxonomy.validate_target("harm_severity", {"answer": 3}), [])
        self.assertEqual(taxonomy.validate_target("action_selection", {"answer": "use_tool"}), [])
        self.assertEqual(taxonomy.validate_target("contains_harm", None), [])

    def test_validate_target_catches_bad_values(self):
        self.assertTrue(taxonomy.validate_target("contains_harm", {"answer": "maybe"}))
        self.assertTrue(taxonomy.validate_target("harm_severity", {"answer": 9}))
        self.assertTrue(taxonomy.validate_target("harm_severity", {"answer": "3"}))
        self.assertTrue(taxonomy.validate_target("action_selection", {"answer": "fly"}))
        self.assertTrue(taxonomy.validate_target("contains_harm", {"probs": {"yes": 0.7, "no": 0.7}}))
        self.assertTrue(taxonomy.validate_target("contains_harm", {"probs": {"yes": 0.5}}))

    def test_item_errors_accepts_well_formed_item(self):
        item = {
            "id": "db-src-0000000a",
            "domain": "risk_harm",
            "lang": "en",
            "state": "A state to judge.",
            "questions": taxonomy.build_questions("risk_harm"),
            "targets": {"contains_harm": {"answer": "yes"}},
            "source": {"dataset": "src", "revision": "0" * 40, "config": "default",
                       "split": "train", "row": 1, "license": "cc0-1.0",
                       "url": "https://example.invalid/x"},
            "meta": {"converter": "test", "converter_version": "0", "created_at": "2026-09-30"},
        }
        self.assertEqual(taxonomy.item_errors(item), [])
        self.assertTrue(taxonomy.id_is_canonical(item["id"]))
        self.assertFalse(taxonomy.id_is_canonical("db-src-nope"))

    def test_item_errors_reports_missing_and_drift(self):
        broken = {"id": "db-x-00000001", "domain": "nope", "lang": "en", "state": "s",
                  "questions": [{"key": "ghost", "kind": "noul", "prompt": "p"}],
                  "targets": {"contains_harm": {"answer": "yes"}}, "source": {}, "meta": {}}
        errors = taxonomy.item_errors(broken)
        joined = " | ".join(errors)
        self.assertIn("不在 taxonomy", joined)
        self.assertIn("未知问题键", joined)
        self.assertIn("source 缺字段", joined)
        self.assertIn("meta 缺字段", joined)
        self.assertIn("没有对应的 questions 条目", joined)

    def test_summary_shape(self):
        summary = taxonomy.summary()
        self.assertEqual(summary["keys"], len(taxonomy.QUESTION_KEYS))
        self.assertEqual(set(summary["domains"]), set(taxonomy.DOMAINS))
        self.assertIn("pol2_axis", summary["per_domain"])
        self.assertEqual(sum(summary["key_kinds"].values()), len(taxonomy.QUESTION_KEYS))
        for domain in taxonomy.DOMAINS:
            self.assertEqual(sum(summary["per_domain_kinds"][domain].values()),
                             len(taxonomy.DOMAIN_KEYS[domain]), domain)


class OntologyAlignmentTest(unittest.TestCase):
    def test_ontology_mismatches_is_empty(self):
        if not taxonomy.ONTOLOGY_PATH.is_file():
            self.skipTest(f"本体文件不存在: {taxonomy.ONTOLOGY_PATH}")
        self.assertEqual(taxonomy.ontology_mismatches(), [])

    def test_issue_ids_match_ontology_file(self):
        if not taxonomy.ONTOLOGY_PATH.is_file():
            self.skipTest("本体文件不存在")
        ontology = taxonomy.load_ontology()
        self.assertEqual([row["id"] for row in ontology["issues"]],
                         [row[0] for row in taxonomy.POL2_ISSUES])
        self.assertEqual([row["key"] for row in ontology["actions"]],
                         [row[0] for row in taxonomy.POL2_ACTIONS])
        self.assertEqual([row["key"] for row in ontology["polarity"]],
                         [row[0] for row in taxonomy.POL2_POLARITY])


if __name__ == "__main__":
    unittest.main()
