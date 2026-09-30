"""coverage.py 自检：分布统计、配额通过与不通过两条路径、CLI 退出码。"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import coverage as cov  # noqa: E402
import taxonomy  # noqa: E402


def make_item(index: int, domain: str, dataset: str = "src-a", lang: str = "en") -> dict:
    """造一条完全合法的条目（schema 警告应为 0）。"""
    slug = dataset.replace("/", "-").replace("_", "-")
    questions = taxonomy.build_questions(domain)
    targets = {}
    for question in questions:
        if question["kind"] == "noul":
            targets[question["key"]] = {"answer": "yes"}
        elif question["kind"] == "choice":
            targets[question["key"]] = {"answer": question["options"][0]["key"]}
        else:
            targets[question["key"]] = {"answer": question["scale"]["min"]}
    return {
        "id": f"db-{slug}-{index:08x}",
        "domain": domain,
        "lang": lang,
        "state": f"state {index} for {domain}",
        "questions": questions,
        "targets": targets,
        "source": {"dataset": dataset, "revision": "0" * 40, "config": "default",
                   "split": "train", "row": index, "license": "cc0-1.0",
                   "url": "https://example.invalid/x"},
        "meta": {"converter": "test", "converter_version": "0",
                 "created_at": "2026-09-30T00:00:00+08:00", "quality_flags": []},
    }


def fixture(items) -> Path:
    directory = tempfile.mkdtemp(prefix="db-coverage-")
    path = Path(directory) / "items.jsonl"
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items),
                    encoding="utf-8")
    return path


class FixtureTest(unittest.TestCase):
    def test_fixture_items_are_schema_clean(self):
        item = make_item(1, "risk_harm")
        self.assertEqual(taxonomy.item_errors(item), [])
        self.assertEqual(taxonomy.id_is_canonical(item["id"]), True)

    def test_all_domains_fixture_is_clean(self):
        for index, domain in enumerate(taxonomy.DOMAINS):
            self.assertEqual(taxonomy.item_errors(make_item(index, domain)), [], domain)


class QuotaPassTest(unittest.TestCase):
    def setUp(self):
        items = []
        index = 0
        for domain in taxonomy.DOMAINS:
            for _ in range(2):
                items.append(make_item(index, domain, dataset=f"src-{index % 3}"))
                index += 1
        self.items = items
        self.path = fixture(items)

    def test_report_passes_and_lists_distributions(self):
        report = cov.build_report(self.items, items_file=self.path, min_total=12,
                                  min_per_domain=2, max_source_share=0.5)
        self.assertTrue(report["ok"])
        self.assertEqual(report["quotas"]["violations"], [])
        distributions = report["distributions"]
        self.assertEqual(distributions["domain"]["risk_harm"]["count"], 2)
        self.assertEqual(distributions["lang"]["en"]["count"], 12)
        self.assertEqual(set(distributions["source.dataset"]), {"src-0", "src-1", "src-2"})
        self.assertAlmostEqual(distributions["source.dataset"]["src-0"]["share"], 1 / 3, places=5)
        self.assertEqual(sum(row["count"] for row in distributions["question_key"].values()),
                         sum(len(item["questions"]) for item in self.items))
        self.assertEqual(report["schema_issues"]["total"], 0)
        self.assertEqual(set(report["pol2_axis"]["axes_asked"]),
                         {key[len("issue_"):] for key in taxonomy.POL2_AXIS_KEYS})

    def test_cli_exit_code_zero_on_pass(self):
        self.assertEqual(cov.main(["--items", str(self.path), "--min-total", "12",
                                   "--min-per-domain", "2", "--max-source-share", "0.5",
                                   "--quiet"]), 0)

    def test_text_report_has_expected_sections(self):
        report = cov.build_report(self.items, items_file=self.path, min_total=12,
                                  min_per_domain=2, max_source_share=0.5)
        text = cov.format_report(report)
        for token in ("[domain]", "[原语 kind]", "[lang]", "[source.dataset]",
                      "[问题键 question_key]", "[pol2_axis]", "[配额校验]", "[通过]"):
            self.assertIn(token, text)


class QuotaFailTest(unittest.TestCase):
    def test_short_total_and_domains_and_source_share(self):
        items = [make_item(i, "risk_harm", dataset="src-big") for i in range(6)]
        report = cov.build_report(items, min_total=10, min_per_domain=2, max_source_share=0.4)
        self.assertFalse(report["ok"])
        violations = " | ".join(report["quotas"]["violations"])
        self.assertIn("总量 6 < 下限 10", violations)
        self.assertIn("覆盖域 human_judgment 只有 0 条", violations)
        self.assertIn("单一来源 src-big 占 100.0%", violations)
        self.assertEqual(report["gaps"]["total_shortfall"], 4)
        self.assertIn("human_judgment", report["gaps"]["domains"])
        self.assertEqual(report["gaps"]["sources_over_share"]["src-big"], 1.0)
        self.assertEqual(report["quotas"]["checks"][0]["id"], "total")

    def test_cli_exit_code_one_on_fail(self):
        path = fixture([make_item(i, "risk_harm", dataset="src-big") for i in range(6)])
        code = cov.main(["--items", str(path), "--min-total", "10", "--min-per-domain", "2",
                         "--max-source-share", "0.4", "--quiet"])
        self.assertEqual(code, 1)

    def test_single_source_over_share_is_blocked_alone(self):
        """总量与每域都达标，只有单一来源 >40% —— 也必须拦截。"""
        items = []
        for index in range(12):
            domain = taxonomy.DOMAINS[index % len(taxonomy.DOMAINS)]
            dataset = "src-big" if index < 9 else f"src-{index}"
            items.append(make_item(index, domain, dataset=dataset))
        report = cov.build_report(items, min_total=12, min_per_domain=2, max_source_share=0.4)
        self.assertFalse(report["ok"])
        self.assertEqual(len(report["quotas"]["violations"]), 1)
        self.assertIn("超过上限 40%", report["quotas"]["violations"][0])
        share_check = [c for c in report["quotas"]["checks"] if c["id"] == "max_source_share"][0]
        self.assertEqual(share_check["actual"], 0.75)
        self.assertFalse(share_check["ok"])

    def test_unknown_domain_and_duplicate_id_are_hard_violations(self):
        items = [make_item(0, "risk_harm"), make_item(0, "knowledge_reasoning")]
        items[1]["domain"] = "made_up_domain"
        items[1]["id"] = items[0]["id"]
        report = cov.build_report(items, min_total=0, min_per_domain=0, max_source_share=1.0)
        self.assertFalse(report["ok"])
        violations = " | ".join(report["quotas"]["violations"])
        self.assertIn("未知覆盖域", violations)
        self.assertIn("重复 id", violations)
        self.assertEqual(report["duplicate_ids"], [items[0]["id"]])
        self.assertIn("made_up_domain", report["unknown_domains"])

    def test_domain_min_override(self):
        items = [make_item(i, "risk_harm") for i in range(3)]
        report = cov.build_report(items, min_total=1, min_per_domain=0,
                                  domain_min={"risk_harm": 5}, max_source_share=1.0)
        self.assertFalse(report["ok"])
        self.assertIn("覆盖域 risk_harm 只有 3 条 < 下限 5", report["quotas"]["violations"][0])
        self.assertEqual(report["gaps"]["domains"], {"risk_harm": 2})


class SchemaWarningTest(unittest.TestCase):
    def test_schema_issues_warn_by_default_and_fail_with_strict(self):
        item = make_item(0, "social_moral")
        del item["meta"]["converter_version"]
        item["targets"]["moral_judgment"] = {"answer": "not_an_option"}
        item["questions"].append({"key": "ghost_key", "kind": "noul", "prompt": "p"})
        items = [item]
        report = cov.build_report(items, min_total=0, min_per_domain=0, max_source_share=1.0)
        self.assertTrue(report["ok"], report["quotas"]["violations"])
        self.assertGreaterEqual(report["schema_issues"]["total"], 3)
        self.assertIn("schema 警告", " ".join(report["warnings"]))

        path = fixture(items)
        self.assertEqual(cov.main(["--items", str(path), "--min-total", "0",
                                   "--min-per-domain", "0", "--max-source-share", "1",
                                   "--quiet"]), 0)
        self.assertEqual(cov.main(["--items", str(path), "--min-total", "0",
                                   "--min-per-domain", "0", "--max-source-share", "1",
                                   "--quiet", "--strict"]), 1)

    def test_json_out_writes_full_report(self):
        path = fixture([make_item(0, "human_judgment")])
        out = Path(tempfile.mkdtemp(prefix="db-coverage-out-")) / "report.json"
        code = cov.main(["--items", str(path), "--min-total", "1", "--min-per-domain", "0",
                         "--max-source-share", "1", "--json-out", str(out), "--quiet"])
        self.assertEqual(code, 0)
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(report["ok"])
        self.assertEqual(report["items"], 1)
        self.assertIn("distributions", report)
        self.assertIn("taxonomy", report)


class InputErrorTest(unittest.TestCase):
    def test_missing_file_exits_two(self):
        missing = Path(tempfile.mkdtemp(prefix="db-coverage-missing-")) / "items.jsonl"
        self.assertEqual(cov.main(["--items", str(missing), "--quiet"]), 2)

    def test_broken_json_exits_two(self):
        directory = tempfile.mkdtemp(prefix="db-coverage-bad-")
        path = Path(directory) / "items.jsonl"
        path.write_text('{"id": "db-x-00000001"}\nnot json\n', encoding="utf-8")
        self.assertEqual(cov.main(["--items", str(path), "--quiet"]), 2)
        with self.assertRaises(cov.ItemsError):
            cov.read_items(path)

    def test_read_items_requires_json_objects(self):
        directory = tempfile.mkdtemp(prefix="db-coverage-arr-")
        path = Path(directory) / "items.jsonl"
        path.write_text("[1, 2]\n", encoding="utf-8")
        with self.assertRaises(cov.ItemsError):
            cov.read_items(path)

    def test_bad_domain_min_exits_two(self):
        path = fixture([make_item(0, "risk_harm")])
        self.assertEqual(cov.main(["--items", str(path), "--domain-min", "nope=3", "--quiet"]), 2)
        self.assertEqual(cov.main(["--items", str(path), "--domain-min", "risk_harm=x", "--quiet"]), 2)
        self.assertEqual(cov.main(["--items", str(path), "--max-source-share", "2", "--quiet"]), 2)

    def test_parse_domain_min(self):
        self.assertEqual(cov.parse_domain_min(["risk_harm=7"]), {"risk_harm": 7})
        with self.assertRaises(ValueError):
            cov.parse_domain_min(["risk_harm"])


class CliSubprocessTest(unittest.TestCase):
    def test_script_runs_offline_with_expected_exit_code(self):
        path = fixture([make_item(i, taxonomy.DOMAINS[i % 6], dataset=f"src-{i % 3}")
                        for i in range(12)])
        completed = subprocess.run(
            [sys.executable, str(HERE / "coverage.py"), "--items", str(path),
             "--min-total", "12", "--min-per-domain", "2", "--max-source-share", "0.5"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(HERE))
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("decision-base 覆盖报告", completed.stdout)
        self.assertIn("[通过]", completed.stdout)


if __name__ == "__main__":
    unittest.main()
