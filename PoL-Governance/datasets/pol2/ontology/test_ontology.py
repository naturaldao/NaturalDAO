"""Unit tests for the PoL2 ontology, judging rules and minimal-pair matrix.

Run from the repository root:
    uv run --no-project --offline python -m unittest discover -s datasets/pol2/ontology -p "test_*.py" -q

The tests read the checked-in files; they never write to them and never claim
semantic truth. Model cross-checking is not a gold standard (see ../README.md 3.4).
"""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_ontology as co  # noqa: E402  (same-directory helper)


def _data() -> dict:
    return co.load_ontology()


def _matrix_text() -> str:
    return co._read(co.MATRIX_PATH)


class OntologyShapeTest(unittest.TestCase):
    def setUp(self):
        self.data = _data()

    def test_full_check_passes(self):
        report = co.check()
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["schema"], "pol2-labels/0.1")
        self.assertEqual(report["clauses"], 34)
        self.assertEqual(report["issues"], 15)
        self.assertEqual(report["love_languages"], 16)
        self.assertEqual(report["mitigations"], 8)
        self.assertEqual(report["axes"], 18)
        self.assertGreaterEqual(report["pairs"], 15)

    def test_required_sections_present(self):
        for key in ("clauses", "status", "polarity", "issues", "love_languages",
                    "mitigations", "evidence", "actions", "surfaces",
                    "legacy_label_map", "pending_review", "hard_rules"):
            self.assertIn(key, self.data)
        self.assertGreaterEqual(len(self.data["hard_rules"]), 4)

    def test_clause_ids_are_well_formed(self):
        for clause_id, entry in self.data["clauses"].items():
            self.assertRegex(clause_id, co.CLAUSE_RE.pattern, clause_id)
            for field in ("doc", "heading", "gist", "quote"):
                self.assertTrue(entry.get(field, "").strip(), clause_id + "." + field)

    def test_clause_ids_are_unique(self):
        keys = list(self.data["clauses"])
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_label_cites_a_known_clause(self):
        for section in ("status", "polarity", "issues", "love_languages",
                        "mitigations", "evidence", "actions", "surfaces"):
            for entry in self.data[section]:
                entry_id = entry.get("key") or entry["id"]
                self.assertIn(entry["clause"], self.data["clauses"], section + "." + entry_id)
                for extra in entry.get("clauses", []):
                    self.assertIn(extra, self.data["clauses"], section + "." + entry_id)

    def test_enum_sets_are_exact(self):
        self.assertEqual([e["key"] for e in self.data["status"]], list(co.STATUS_KEYS))
        self.assertEqual([e["key"] for e in self.data["polarity"]], list(co.POLARITY_KEYS))
        self.assertEqual([e["key"] for e in self.data["evidence"]], list(co.EVIDENCE_KEYS))
        self.assertEqual([e["key"] for e in self.data["actions"]], list(co.ACTION_KEYS))
        self.assertEqual([e["key"] for e in self.data["surfaces"]], list(co.SURFACE_KEYS))

    def test_no_duplicate_ids_within_a_section(self):
        for section in ("status", "polarity", "issues", "love_languages", "mitigations",
                        "evidence", "actions", "surfaces"):
            ids = [e.get("key") or e["id"] for e in self.data[section]]
            self.assertEqual(len(ids), len(set(ids)), section)

    def test_open_lists_are_disjoint(self):
        issues = {e["id"] for e in self.data["issues"]}
        love = {e["id"] for e in self.data["love_languages"]}
        mitigations = {e["id"] for e in self.data["mitigations"]}
        self.assertFalse(issues & love)
        self.assertFalse(issues & mitigations)
        self.assertFalse(love & mitigations)

    def test_core_issue_groups_match_dataset_contract(self):
        by_id = {e["id"]: e for e in self.data["issues"]}
        for issue_id, group in co.CORE_ISSUES.items():
            self.assertIn(issue_id, by_id)
            self.assertEqual(by_id[issue_id]["group"], group)
        self.assertEqual(len(co.CORE_ISSUES), 10)

    def test_governance_risk_issues_are_marked(self):
        risks = {e["id"] for e in self.data["issues"] if e["domain"] == "governance_risk"}
        self.assertEqual(risks, {"unnecessary_restriction", "tool_scope_overreach",
                                 "untrusted_instruction_injection"})

    def test_love_languages_cover_all_16_clauses(self):
        clauses = {e["clause"] for e in self.data["love_languages"]}
        self.assertEqual(clauses, {"PoL.2." + str(i) for i in range(1, 17)})

    def test_required_mitigations_present(self):
        ids = {e["id"] for e in self.data["mitigations"]}
        for required in co.REQUIRED_MITIGATIONS:
            self.assertIn(required, ids)
        for entry in self.data["mitigations"]:
            self.assertTrue(entry["effect"].strip(), entry["id"])

    def test_pending_review_is_explicit(self):
        pending = self.data["pending_review"]
        self.assertTrue(pending)
        ids = [item["id"] for item in pending]
        self.assertEqual(len(ids), len(set(ids)))
        for item in pending:
            self.assertIn(item["kind"], co.PENDING_KINDS)
            self.assertIn(item["clause"], self.data["clauses"])
        for section in ("polarity", "evidence", "issues", "mitigations"):
            for entry in self.data[section]:
                if entry.get("review_state") == "pending_review":
                    self.assertTrue(entry.get("note"), entry.get("id") or entry.get("key"))

    def test_legacy_map_matches_protocol_labels(self):
        legacy = {k: v for k, v in self.data["legacy_label_map"].items() if k != "note"}
        self.assertEqual(sorted(legacy), sorted(co.LEGACY_LABELS))
        issue_ids = {e["id"] for e in self.data["issues"]}
        for key, mapping in legacy.items():
            self.assertTrue(mapping["native_issues"], key)
            for target in mapping["native_issues"]:
                self.assertIn(target, issue_ids, key)

    def test_hard_rules_cover_the_four_base_rules(self):
        text = " ".join(self.data["hard_rules"])
        for marker in ("不得用情绪或措辞当行为性质", "温柔措辞不构成免责", "值守安全的恨"):
            self.assertIn(marker, text)
        self.assertIn("不是金标准", text)


class MatrixTest(unittest.TestCase):
    def setUp(self):
        self.data = _data()
        self.text = _matrix_text()
        self.axes, self.rows = co.parse_matrix(self.text)

    def test_every_axis_declares_required_topics(self):
        topics = " ".join(row.get("主题（必覆盖）", "") for row in self.axes.values())
        for topic in co.REQUIRED_TOPICS:
            self.assertIn(topic, topics, topic)

    def test_every_axis_has_at_least_one_pair(self):
        for axis_id in self.axes:
            pairs = [r for r in self.rows
                     if r[co.PAIR_HEADER_FIRST].startswith(axis_id + "-")]
            self.assertTrue(pairs, axis_id + " has no pair")

    def test_pairs_are_minimal_and_changed(self):
        report = co.check_matrix(self.data, self.text)
        self.assertEqual(report["axes"], len(self.axes))
        self.assertGreaterEqual(report["pairs"], len(self.axes))

    def test_pair_rows_share_one_plot(self):
        grouped = {}
        for row in self.rows:
            grouped.setdefault(row["scenario"], []).append(row)
        for scenario, rows in grouped.items():
            self.assertEqual(len(rows), 2, scenario)
            self.assertEqual(rows[0]["plot"], rows[1]["plot"], scenario)
            self.assertNotEqual(rows[0]["variant"], rows[1]["variant"], scenario)
            self.assertNotEqual(rows[0]["changed_fact"], rows[1]["changed_fact"], scenario)

    def test_expectation_values_are_ontology_keys(self):
        issue_ids = {e["id"] for e in self.data["issues"]}
        love_ids = {e["id"] for e in self.data["love_languages"]}
        mitigation_ids = {e["id"] for e in self.data["mitigations"]}
        for row in self.rows:
            pair_id = row[co.PAIR_HEADER_FIRST]
            self.assertIn(row["exp_status"], co.STATUS_KEYS, pair_id)
            self.assertIn(row["exp_polarity"], co.POLARITY_KEYS, pair_id)
            self.assertIn(row["exp_evidence"], co.EVIDENCE_KEYS, pair_id)
            for action in co._split_cell(row["exp_actions"], co.MATRIX_ACTIONS_SEP):
                self.assertIn(action, co.ACTION_KEYS, pair_id)
            for issue in co._split_cell(row["exp_issues"], co.MATRIX_LIST_SEP):
                self.assertIn(issue, issue_ids, pair_id)
            for mitigation in co._split_cell(row["exp_mitigations"], co.MATRIX_LIST_SEP):
                self.assertIn(mitigation, mitigation_ids, pair_id)
            for love in co._split_cell(row["exp_love_languages"], co.MATRIX_LIST_SEP):
                self.assertIn(love, love_ids, pair_id)

    def test_matrix_axis_clauses_are_known(self):
        for axis_id, row in self.axes.items():
            for clause in co._split_cell(row["clause"], co.MATRIX_ACTIONS_SEP):
                self.assertIn(clause, self.data["clauses"], axis_id)

    def test_every_issue_and_mitigation_appears_in_matrix(self):
        issues = {i for r in self.rows for i in co._split_cell(r["exp_issues"], co.MATRIX_LIST_SEP)}
        mitigations = {m for r in self.rows
                       for m in co._split_cell(r["exp_mitigations"], co.MATRIX_LIST_SEP)}
        self.assertEqual(issues, {e["id"] for e in self.data["issues"]})
        self.assertEqual(mitigations, {e["id"] for e in self.data["mitigations"]})

    def test_matrix_uses_every_action(self):
        actions = {a for r in self.rows for a in co._split_cell(r["exp_actions"], co.MATRIX_ACTIONS_SEP)}
        self.assertEqual(actions, set(co.ACTION_KEYS))

    def test_matrix_is_not_claimed_as_benchmark_data(self):
        self.assertIn("不是 benchmark 数据", self.text)
        self.assertIn("不参与训练", self.text)


class JudgeTest(unittest.TestCase):
    def setUp(self):
        self.data = _data()
        self.text = co._read(co.JUDGE_PATH)

    def test_judge_covers_every_label(self):
        for issue in self.data["issues"]:
            self.assertIn(issue["id"], self.text)
        for mitigation in self.data["mitigations"]:
            self.assertIn(mitigation["id"], self.text)
        for love in self.data["love_languages"]:
            self.assertIn(love["zh"], self.text)

    def test_judge_states_positive_negative_boundary(self):
        for phrase in ("正例", "反例", "边界例"):
            self.assertIn(phrase, self.text)

    def test_judge_defers_model_cross_checking(self):
        self.assertIn("model_cross_checked", self.text)
        self.assertIn("称作金标准", self.text)


class ReadmeTest(unittest.TestCase):
    def test_readme_replaced_and_links_local_files(self):
        text = co._read(co.README_PATH)
        self.assertNotIn("待填充", text)
        self.assertNotIn("占位符", text)
        for name in ("pol2-labels.v0.1.json", "JUDGE.md", "test-matrix.md",
                     "check_ontology.py", "test_ontology.py"):
            self.assertIn(name, text)


class CheckerCatchesProblemsTest(unittest.TestCase):
    """The checker must fail loudly when the contract is broken."""

    def test_rejects_unknown_clause_on_a_label(self):
        data = copy.deepcopy(_data())
        data["issues"][0]["clause"] = "PoL.9.99"
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_rejects_bad_polarity_key(self):
        data = copy.deepcopy(_data())
        data["polarity"][0]["key"] = "affection"
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_rejects_duplicate_issue_id(self):
        data = copy.deepcopy(_data())
        data["issues"].append(copy.deepcopy(data["issues"][0]))
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_rejects_missing_core_issue(self):
        data = copy.deepcopy(_data())
        data["issues"] = [i for i in data["issues"] if i["id"] != "public_erosion"]
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_rejects_wrong_love_language_clause(self):
        data = copy.deepcopy(_data())
        data["love_languages"][0]["clause"] = "PoL.2.16"
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_rejects_missing_mitigation(self):
        data = copy.deepcopy(_data())
        data["mitigations"] = [m for m in data["mitigations"] if m["id"] != "repair_behavior"]
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_rejects_unknown_matrix_issue(self):
        text = _matrix_text().replace("| violence_worship |", "| invented_issue |", 1)
        with self.assertRaises(co.OntologyError):
            co.check_matrix(_data(), text, require_topics=False)

    def test_rejects_pair_with_changed_plot(self):
        text = _matrix_text().replace(
            "A 在给伴侣 B 按摩肩膀，开始前 B 明确说过“可以”，过程中 A 没有新增动作 | 已撤回",
            "A 在别处做别的事情 | 已撤回", 1)
        with self.assertRaises(co.OntologyError):
            co.check_matrix(_data(), text, require_topics=False)

    def test_rejects_axis_without_pair(self):
        text = "\n".join(line for line in _matrix_text().splitlines()
                         if not line.startswith("| AX-15-"))
        with self.assertRaises(co.OntologyError):
            co.check_matrix(_data(), text, require_topics=False)

    def test_rejects_unknown_action_in_matrix(self):
        text = _matrix_text().replace("| sufficient | allow |", "| sufficient | delete |", 1)
        with self.assertRaises(co.OntologyError):
            co.check_matrix(_data(), text, require_topics=False)

    def test_rejects_missing_topic_coverage(self):
        text = _matrix_text().replace("工具越权（文本无害但调用越权）", "某工程主题")
        with self.assertRaises(co.OntologyError):
            co.check_matrix(_data(), text, require_topics=True)



class RenumberingGuardTest(unittest.TestCase):
    """Anchors must follow the audited upstream numbering (EAP 5->4, AI governance 3->5)."""

    def setUp(self):
        self.data = _data()

    def test_anchor_audit_records_the_audited_revision(self):
        audit = self.data["anchor_audit"]
        self.assertEqual(audit["audited_ref"], "origin/main")
        self.assertGreaterEqual(len(audit["audited_commit"]), co.MIN_AUDIT_COMMIT_LEN)
        self.assertEqual(audit["numbering"]["4"], "4. PoL2之伦理对齐协议.md")
        self.assertEqual(audit["numbering"]["5"], "5. AI和人类文明的治理：从恨2证明到爱2证明.md")
        self.assertIn("3. PoL2之冥想智慧公理.md", audit["numbering"].values())
        self.assertIn("PoL共识的工程策略.md", audit["unnumbered_docs"])

    def test_ontology_audit_matches_checker_constants(self):
        audit = self.data["anchor_audit"]
        self.assertEqual({str(k): Path(v).name for k, v in audit["numbering"].items()},
                         co.CANONICAL_NUMBERING)
        self.assertEqual(dict(audit["namespace_chapters"]), co.CANONICAL_CHAPTERS)
        self.assertEqual(tuple(audit["retired_clause_prefixes"]), co.CANONICAL_RETIRED)
        self.assertEqual(audit["audited_ref"], co.CANONICAL_AUDIT_REF)
        self.assertEqual(audit["audited_commit"], co.CANONICAL_AUDIT_COMMIT)

    def test_rejects_numbering_drift_between_json_and_checker(self):
        data = copy.deepcopy(self.data)
        data["anchor_audit"]["numbering"]["4"] = "4. 被改名的章节.md"
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_old_numbering_is_retired(self):
        retired = set(self.data["anchor_audit"]["retired_clause_prefixes"])
        self.assertLessEqual({"EAP.5.", "PoL.3.4", "PoL.3.6", "ENG.6."}, retired)
        for clause_id in self.data["clauses"]:
            for prefix in retired:
                self.assertFalse(clause_id.startswith(prefix), clause_id)

    def test_eap_lives_in_chapter_4_and_ai_governance_in_chapter_5(self):
        eap = [c for c in self.data["clauses"] if c.startswith("EAP.")]
        gov = [c for c in self.data["clauses"] if c.startswith("PoL.5.")]
        self.assertEqual(len(eap), 9)
        self.assertEqual(sorted(gov), ["PoL.5.4", "PoL.5.4.1", "PoL.5.6"])
        for clause_id in eap:
            self.assertEqual(clause_id.split(".")[1], "4", clause_id)

    def test_clause_chapter_matches_its_document(self):
        report = co.check_numbering(self.data)
        self.assertEqual(report["anchors_numbered"], 33)
        self.assertEqual(report["unnumbered_docs"], 1)

    def test_rejects_a_clause_that_reverts_to_the_old_numbering(self):
        data = copy.deepcopy(self.data)
        data["clauses"]["EAP.5.3.2"] = data["clauses"].pop("EAP.4.3.2")
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_rejects_clause_chapter_not_matching_its_doc(self):
        data = copy.deepcopy(self.data)
        data["clauses"]["EAP.3.2"] = data["clauses"].pop("EAP.4.3.2")
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_rejects_missing_anchor_audit(self):
        data = copy.deepcopy(self.data)
        del data["anchor_audit"]
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_rejects_a_document_outside_the_audited_numbering(self):
        data = copy.deepcopy(self.data)
        data["clauses"]["PoL.9.1"] = dict(data["clauses"]["PoL.1.1"], doc="9. 不存在的章节.md")
        with self.assertRaises(co.OntologyError):
            co.check_ontology(data)

    def test_default_check_does_not_depend_on_a_local_source_tree(self):
        report = co.check()
        self.assertEqual(report["source_alignment"],
                         "skipped (pass --source-root <exported PoL dir>)")


class SourceAlignmentTest(unittest.TestCase):
    """--source-root must verify heading numbers and verbatim quotes."""

    def _fixture(self, root: Path):
        (root / "4. PoL2之伦理对齐协议.md").write_text(
            "# 4. PoL2之伦理对齐协议\n\n## 4.3.2 原则二：扬爱抑恨\n\n"
            "负责安保的智能机器人发现紧急情况对人大声发出警示语或警示指令，"
            "不能视为对此人或其周围人的仇恨攻击。\n", encoding="utf-8")
        (root / "PoL共识的工程策略.md").write_text(
            "# PoL共识的工程策略\n\n明辨恨语甚至比爱语的对齐更加重要。\n", encoding="utf-8")
        data = {
            "anchor_audit": {
                "numbering": {"4": "4. PoL2之伦理对齐协议.md"},
                "unnumbered_docs": ["PoL共识的工程策略.md"],
            },
            "clauses": {
                "EAP.4.3.2": {
                    "doc": "4. PoL2之伦理对齐协议.md",
                    "quote": "负责安保的智能机器人发现紧急情况对人大声发出警示语或警示指令，不能视为对此人或其周围人的仇恨攻击",
                },
                "ENG.1": {"doc": "PoL共识的工程策略.md", "quote": "明辨恨语甚至比爱语的对齐更加重要"},
            },
        }
        return data

    def test_accepts_matching_headings_and_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._fixture(Path(tmp))
            report = co.check_source_alignment(data, tmp)
            self.assertEqual(report["anchors_verified"], 2)
            self.assertEqual(report["quotes_verified"], 2)

    def test_rejects_a_missing_section_heading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = self._fixture(root)
            (root / "4. PoL2之伦理对齐协议.md").write_text(
                "# 4. PoL2之伦理对齐协议\n\n## 4.9 别的节\n\n正文。\n", encoding="utf-8")
            with self.assertRaises(co.OntologyError):
                co.check_source_alignment(data, tmp)

    def test_rejects_a_quote_that_changed_upstream(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = self._fixture(root)
            (root / "PoL共识的工程策略.md").write_text(
                "# PoL共识的工程策略\n\n明辨爱语比明辨恨语更加重要。\n", encoding="utf-8")
            with self.assertRaises(co.OntologyError):
                co.check_source_alignment(data, tmp)

    def test_rejects_a_source_file_that_was_not_exported(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self._fixture(Path(tmp))
            (Path(tmp) / "PoL共识的工程策略.md").unlink()
            with self.assertRaises(co.OntologyError):
                co.check_source_alignment(data, tmp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
