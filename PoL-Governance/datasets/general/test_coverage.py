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
        for token in ("[domain]", "[出题方 origin]", "[原语 kind]", "[lang]", "[source.dataset]",
                      "[问题键 question_key（taxonomy 出题）]", "[pol2_axis]", "[配额校验]", "[通过]"):
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
        by_id = {check["id"]: check for check in report["quotas"]["checks"]}
        self.assertFalse(by_id["total"]["ok"])
        self.assertEqual(by_id["total"]["actual"], 6)

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


def write_sources(payload) -> Path:
    """把某份 sources.json 内容写到临时目录，供配额绑定测试使用。"""
    directory = tempfile.mkdtemp(prefix="db-sources-")
    path = Path(directory) / "sources.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


class QuotaSourceTest(unittest.TestCase):
    """配额来源解析：命令行 > sources.json > README 默认，逐字段回退。"""

    def test_readme_default_policy_has_pol2_axis_400(self):
        resolved = cov.resolve_quotas(sources_path=Path(tempfile.mkdtemp()) / "none.json")
        self.assertEqual(resolved["status"], "readme-defaults")
        self.assertEqual(resolved["min_total"], 10000)
        self.assertEqual(resolved["min_per_domain"], 1200)
        self.assertEqual(resolved["domain_min"], {"pol2_axis": 400})
        self.assertAlmostEqual(resolved["max_source_share"], 0.4)
        self.assertTrue(any("不存在" in note for note in resolved["notes"]))
        self.assertTrue(any("pol2_axis" in note for note in resolved["notes"]))

    def test_sources_file_binding_end_to_end(self):
        sources = write_sources({"quotas": {"min_total": 3, "min_per_domain": 1,
                                            "domain_min": {"risk_harm": 2},
                                            "max_source_share": 0.9}})
        items = [make_item(i, taxonomy.DOMAINS[i], dataset=f"src-{i}") for i in range(6)]
        items.append(make_item(6, "risk_harm", dataset="src-6"))
        path = fixture(items)
        out = Path(tempfile.mkdtemp(prefix="db-coverage-out-")) / "report.json"
        code = cov.main(["--items", str(path), "--sources", str(sources),
                         "--json-out", str(out), "--quiet"])
        self.assertEqual(code, 0)
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["quotas"]["status"], "sources.json")
        self.assertEqual(report["quotas"]["min_total"], 3)
        self.assertEqual(report["quotas"]["per_domain"]["risk_harm"], 2)
        self.assertEqual(report["quotas"]["per_domain"]["pol2_axis"], 1)
        self.assertEqual(report["quotas"]["origin"]["min_total"], "sources.json")
        self.assertEqual(report["quotas"]["source_file"], str(sources))
        # 同一份 items 用 README 默认配额必然不达标：证明通过确实来自文件配额
        self.assertEqual(cov.main(["--items", str(path), "--sources", str(sources),
                                   "--no-sources", "--quiet"]), 1)

    def test_missing_sources_file_falls_back(self):
        missing = Path(tempfile.mkdtemp(prefix="db-sources-missing-")) / "none.json"
        path = fixture([make_item(0, "risk_harm")])
        out = Path(tempfile.mkdtemp(prefix="db-coverage-out-")) / "report.json"
        self.assertEqual(cov.main(["--items", str(path), "--sources", str(missing),
                                   "--json-out", str(out), "--quiet"]), 1)
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["quotas"]["status"], "readme-defaults")
        self.assertEqual(report["quotas"]["min_total"], 10000)
        self.assertEqual(report["quotas"]["per_domain"]["pol2_axis"], 400)
        self.assertIsNone(report["quotas"]["source_file"])

    def test_partial_fields_fall_back_to_mixed(self):
        sources = write_sources({"quotas": {"min_total": 5}})
        resolved = cov.resolve_quotas(sources_path=sources)
        self.assertEqual(resolved["status"], "mixed")
        self.assertEqual(resolved["min_total"], 5)
        self.assertEqual(resolved["origin"]["min_total"], "sources.json")
        self.assertEqual(resolved["origin"]["min_per_domain"], "readme-default")
        self.assertEqual(resolved["origin"]["max_source_share"], "readme-default")
        self.assertEqual(resolved["domain_min"], {"pol2_axis": 400})

    def test_cli_overrides_file_field_by_field(self):
        sources = write_sources({"quotas": {"min_total": 999, "max_source_share": 0.1}})
        resolved = cov.resolve_quotas(sources_path=sources, min_total=7)
        self.assertEqual(resolved["min_total"], 7)
        self.assertEqual(resolved["origin"]["min_total"], "cli")
        self.assertEqual(resolved["origin"]["max_source_share"], "sources.json")
        self.assertEqual(resolved["status"], "cli")

    def test_cli_min_per_domain_drops_default_exception(self):
        resolved = cov.resolve_quotas(use_sources=False, min_per_domain=0)
        self.assertEqual(resolved["domain_min"], {})
        self.assertEqual(resolved["origin"]["domain_min"], "readme-default")
        self.assertTrue(any("--domain-min" in note for note in resolved["notes"]))

    def test_file_domain_min_wins_over_default_exception(self):
        sources = write_sources({"quotas": {"min_per_domain": 1, "domain_min": {"pol2_axis": 0}}})
        resolved = cov.resolve_quotas(sources_path=sources)
        self.assertEqual(resolved["domain_min"], {"pol2_axis": 0})
        self.assertEqual(resolved["min_per_domain"], 1)
        # 文件只给了每域政策，总量与单来源上限仍回退 README → 整体是 mixed
        self.assertEqual(resolved["status"], "mixed")
        self.assertEqual(resolved["origin"]["min_per_domain"], "sources.json")
        self.assertEqual(resolved["origin"]["domain_min"], "sources.json")

    def test_file_base_without_exceptions_keeps_pol2_axis_default(self):
        sources = write_sources({"quotas": {"min_per_domain": 2000}})
        resolved = cov.resolve_quotas(sources_path=sources)
        self.assertEqual(resolved["min_per_domain"], 2000)
        self.assertEqual(resolved["domain_min"], {"pol2_axis": 400})
        self.assertEqual(resolved["origin"]["min_per_domain"], "sources.json")
        self.assertEqual(resolved["origin"]["domain_min"], "readme-default")

    def test_invalid_values_fall_back_with_notes(self):
        sources = write_sources({"quotas": {"min_total": -1, "max_source_share": "abc",
                                            "domain_min": {"nope": 5, "risk_harm": "x"}}})
        resolved = cov.resolve_quotas(sources_path=sources)
        self.assertEqual(resolved["min_total"], 10000)
        self.assertEqual(resolved["domain_min"], {"pol2_axis": 400})
        self.assertEqual(resolved["status"], "readme-defaults")
        joined = " | ".join(resolved["notes"])
        self.assertIn("min_total", joined)
        self.assertIn("max_source_share", joined)
        self.assertIn("不是覆盖域", joined)
        self.assertIn("没有任何合法条目", joined)

    def test_aliases_and_percent_share(self):
        sources = write_sources({"quota": {"total_min": 5, "per_domain_min": 2,
                                           "per_domain_overrides": {"risk_harm": 3},
                                           "source_share_cap": 40}})
        resolved = cov.resolve_quotas(sources_path=sources)
        self.assertEqual(resolved["min_total"], 5)
        self.assertEqual(resolved["min_per_domain"], 2)
        self.assertEqual(resolved["domain_min"], {"risk_harm": 3})
        self.assertAlmostEqual(resolved["max_source_share"], 0.4)
        self.assertEqual(resolved["status"], "sources.json")

    def test_broken_sources_json_falls_back(self):
        directory = tempfile.mkdtemp(prefix="db-sources-bad-")
        path = Path(directory) / "sources.json"
        path.write_text("{not json", encoding="utf-8")
        resolved = cov.resolve_quotas(sources_path=path)
        self.assertEqual(resolved["status"], "readme-defaults")
        self.assertTrue(any("无法解析" in note for note in resolved["notes"]))

    def test_sources_json_without_quotas_section_falls_back(self):
        sources = write_sources({"version": "0.1", "sources": []})
        resolved = cov.resolve_quotas(sources_path=sources)
        self.assertEqual(resolved["status"], "readme-defaults")
        self.assertTrue(any("没有 quotas 段" in note for note in resolved["notes"]))

    def test_text_report_states_quota_source(self):
        items = [make_item(i, taxonomy.DOMAINS[i], dataset=f"src-{i}") for i in range(6)]
        report = cov.build_report(items, min_total=1, min_per_domain=1, max_source_share=0.5,
                                  quota_meta={"status": "sources.json",
                                              "origin": {"min_total": "sources.json"},
                                              "source_file": "x/sources.json",
                                              "notes": ["示例说明"]})
        text = cov.format_report(report)
        self.assertIn("配额来源：sources.json", text)
        self.assertIn("file=x/sources.json", text)
        self.assertIn("示例说明", text)
        self.assertIn("min_total=sources.json", text)


def source_question(key, kind, options=None, scale=None, prompt="native question"):
    """构造一条 origin=source 的原生问题（key 即来源原生名）。"""
    question = {"key": key, "kind": kind, "prompt": prompt, "origin": "source", "source_key": key}
    if options is not None:
        question["options"] = options
    if scale is not None:
        question["scale"] = scale
    return question


def noul_options(*keys):
    return [{"key": key, "label": key} for key in keys]


def score_scale(minimum, maximum):
    return {"min": minimum, "max": maximum, "labels": [str(i) for i in range(minimum, maximum + 1)]}


def make_source_item(index, domain="decision_mechanics", dataset="src-native",
                     questions=None, targets=None):
    """一条 origin=source 的合法条目（默认问题集是原生 choice）。"""
    item = make_item(index, domain, dataset=dataset)
    item["questions"] = questions if questions is not None else [
        source_question("category", "choice",
                        options=[{"key": "a", "label": "A"}, {"key": "b", "label": "B"}])]
    item["targets"] = targets if targets is not None else {"category": {"answer": "a"}}
    return item


class OriginAwareTest(unittest.TestCase):
    """origin=source 的原生问题：不查 taxonomy 词表，改用条目自带的 options/scale。"""

    def test_origin_defaults_to_taxonomy(self):
        legacy = {"key": "contains_harm", "kind": "noul", "prompt": "p",
                  "options": noul_options("yes", "no")}
        self.assertEqual(cov.question_origin(legacy), "taxonomy")
        self.assertEqual(cov.question_errors(legacy), [])
        self.assertEqual(cov.question_origin(dict(legacy, origin="source")), "source")
        self.assertEqual(cov.question_origin({"origin": "banana"}), "taxonomy")

    def test_source_native_keys_are_not_unknown(self):
        questions = [source_question("bug_severity", "score", scale=score_scale(0, 5)),
                     source_question("refund_requested", "noul", options=noul_options("false", "true"))]
        item = make_source_item(0, questions=questions,
                                targets={"bug_severity": {"answer": "4"},
                                         "refund_requested": {"answer": "false"}})
        self.assertEqual(cov.item_errors(item), [])
        report = cov.build_report([item], min_total=1, min_per_domain=0, max_source_share=1.0)
        self.assertEqual(report["schema_issues"]["total"], 0)
        self.assertNotIn("未知问题键", " | ".join(report["schema_issues"]["counts"]))
        self.assertEqual(report["origin"]["questions"], {"source": 2})
        self.assertEqual(report["distributions"]["question_key"], {})
        self.assertEqual(set(report["distributions"]["question_key_source"]),
                         {"bug_severity", "refund_requested"})

    def test_source_noul_accepts_false_true_and_no_yes(self):
        for order in (("false", "true"), ("no", "yes"), ("true", "false")):
            question = source_question("is_relevant", "noul", options=noul_options(*order))
            self.assertEqual(cov.question_errors(question), [], order)
            item = make_source_item(1, questions=[question],
                                    targets={"is_relevant": {"answer": order[0]}})
            self.assertEqual(cov.item_errors(item), [], order)

    def test_source_noul_must_still_have_exactly_two_options(self):
        question = source_question("is_relevant", "noul", options=noul_options("a", "b", "c"))
        errors = cov.question_errors(question)
        self.assertTrue(any("恰好 2 个选项" in error for error in errors), errors)

    def test_taxonomy_noul_still_requires_yes_no(self):
        question = {"key": "contains_harm", "kind": "noul", "prompt": "p",
                    "options": noul_options("false", "true")}
        errors = cov.question_errors(question)
        self.assertTrue(any("['yes', 'no']" in error for error in errors), errors)

    def test_source_choice_may_exceed_16_options(self):
        options = [{"key": f"o{i}", "label": f"O{i}"} for i in range(57)]
        question = source_question("pick_one", "choice", options=options)
        self.assertEqual(cov.question_errors(question), [])
        item = make_source_item(2, questions=[question], targets={"pick_one": {"answer": "o56"}})
        self.assertEqual(cov.item_errors(item), [])
        report = cov.build_report([item], min_total=1, min_per_domain=0, max_source_share=1.0)
        self.assertEqual(report["schema_issues"]["total"], 0)

    def test_source_choice_needs_at_least_two_options(self):
        question = source_question("pick_one", "choice", options=[{"key": "only", "label": "Only"}])
        self.assertTrue(any("至少 2 个选项" in error for error in cov.question_errors(question)))

    def test_taxonomy_choice_still_capped_at_16(self):
        options = [{"key": f"o{i}", "label": f"O{i}"} for i in range(17)]
        question = {"key": "action_selection", "kind": "choice", "prompt": "p", "options": options}
        self.assertTrue(any("越界 [2,16]" in error for error in cov.question_errors(question)))

    def test_source_score_uses_its_own_scale(self):
        for maximum in (1, 4, 5, 9):
            question = source_question("severity", "score", scale=score_scale(0, maximum))
            self.assertEqual(cov.question_errors(question), [], maximum)
            item = make_source_item(3, questions=[question],
                                    targets={"severity": {"answer": str(maximum)}})
            self.assertEqual(cov.item_errors(item), [], maximum)
        question = source_question("severity", "score", scale=score_scale(0, 9))
        out_of_range = make_source_item(4, questions=[question],
                                        targets={"severity": {"answer": "10"}})
        self.assertTrue(any("越界 0..9" in error for error in cov.item_errors(out_of_range)))

    def test_source_score_labels_must_match_range(self):
        question = source_question("severity", "score",
                                   scale={"min": 0, "max": 4, "labels": ["a", "b", "c"]})
        self.assertTrue(any("scale.labels" in error for error in cov.question_errors(question)))

    def test_taxonomy_score_still_must_be_0_to_4(self):
        question = {"key": "harm_severity", "kind": "score", "prompt": "p",
                    "scale": score_scale(0, 9)}
        self.assertTrue(any("0..4" in error for error in cov.question_errors(question)))

    def test_source_target_answer_must_be_in_its_own_options(self):
        question = source_question("category", "choice",
                                   options=[{"key": "a", "label": "A"}, {"key": "b", "label": "B"}])
        item = make_source_item(5, questions=[question], targets={"category": {"answer": "zzz"}})
        self.assertTrue(any("不在该题的 2 个选项内" in error for error in cov.item_errors(item)))

    def test_source_probs_are_checked_against_own_options(self):
        question = source_question("category", "choice",
                                   options=[{"key": "a", "label": "A"}, {"key": "b", "label": "B"}])
        item = make_source_item(6, questions=[question],
                                targets={"category": {"probs": {"a": 0.6, "b": 0.4}}})
        self.assertEqual(cov.item_errors(item), [])
        bad = make_source_item(7, questions=[question],
                               targets={"category": {"probs": {"a": 0.6, "zzz": 0.4}}})
        self.assertTrue(any("不在该题的选项内" in error for error in cov.item_errors(bad)))

    def test_source_question_requires_source_key(self):
        question = source_question("category", "choice",
                                   options=[{"key": "a", "label": "A"}, {"key": "b", "label": "B"}])
        del question["source_key"]
        self.assertTrue(any("source_key" in error for error in cov.question_errors(question)))

    def test_source_key_equal_to_taxonomy_name_is_not_taxonomy_coverage(self):
        question = source_question("contains_harm", "noul", options=noul_options("yes", "no"))
        item = make_source_item(8, questions=[question],
                                targets={"contains_harm": {"answer": "yes"}})
        report = cov.build_report([item], min_total=1, min_per_domain=0, max_source_share=1.0)
        self.assertEqual(report["schema_issues"]["total"], 0)
        self.assertEqual(report["distributions"]["question_key"], {})
        self.assertIn("contains_harm", report["distributions"]["question_key_source"])
        self.assertEqual(report["pol2_axis"]["axes_asked"]["violence_worship"], 0)

    def test_item_errors_does_not_early_return(self):
        """未知键 + 形状错误必须一次报全，而不是被未知键挡住。"""
        broken = make_source_item(9)
        broken["questions"] = [{"key": "totally_unknown_native", "kind": "bogus", "prompt": "  "}]
        broken["targets"] = {"totally_unknown_native": {"answer": "x"},
                             "ghost_target": {"answer": "x"}}
        errors = cov.item_errors(broken)
        joined = " | ".join(errors)
        self.assertIn("未知问题键", joined)
        self.assertIn("kind=", joined)
        self.assertIn("prompt 必须是非空字符串", joined)
        self.assertIn("ghost_target", joined)
        self.assertIn("没有对应的 questions 条目", joined)

    def test_legacy_items_without_origin_stay_taxonomy(self):
        item = make_item(10, "risk_harm")
        report = cov.build_report([item], min_total=1, min_per_domain=0, max_source_share=1.0)
        self.assertEqual(report["schema_issues"]["total"], 0)
        self.assertEqual(report["origin"]["questions"], {"taxonomy": len(item["questions"])})
        self.assertEqual(report["origin"]["missing_or_invalid"], len(item["questions"]))
        self.assertEqual(len(report["distributions"]["question_key"]), len(item["questions"]))


class ProfileTest(unittest.TestCase):
    """--profile subset：子集只校验自己该负责的维度。"""

    def subset_items(self):
        return [make_source_item(i, domain="decision_mechanics" if i % 2 else "knowledge_reasoning")
                for i in range(20)]

    def test_subset_passes_what_full_rejects(self):
        path = fixture(self.subset_items())
        out = Path(tempfile.mkdtemp(prefix="db-coverage-out-")) / "report.json"
        code = cov.main(["--items", str(path), "--profile", "subset",
                         "--json-out", str(out), "--quiet"])
        self.assertEqual(code, 0)
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["profile"], "subset")
        self.assertTrue(report["ok"])
        self.assertFalse(report["quotas"]["enforce"]["total"])
        self.assertFalse(report["quotas"]["enforce"]["domains"])
        self.assertFalse(report["quotas"]["enforce"]["source_share"])
        self.assertTrue(report["quotas"]["enforce"]["require_origin"])
        # 同一份数据走全量档位必然不达标（20 条、单一来源 100%、只覆盖 2 个域）
        self.assertEqual(cov.main(["--items", str(path), "--quiet"]), 1)

    def test_subset_still_checks_non_empty_domain_and_id(self):
        empty = fixture([])
        self.assertEqual(cov.main(["--items", str(empty), "--profile", "subset", "--quiet"]), 1)
        items = self.subset_items()[:2]
        items[1]["domain"] = "made_up_domain"
        items[1]["id"] = items[0]["id"]
        self.assertEqual(cov.main(["--items", str(fixture(items)), "--profile", "subset",
                                   "--quiet"]), 1)

    def test_subset_requires_explicit_origin(self):
        item = make_item(0, "decision_mechanics")
        report = cov.build_report([item], min_total=0, min_per_domain=0, max_source_share=1.0,
                                  quota_meta={"profile": "subset",
                                              "enforce": {"require_origin": True,
                                                          "total": False, "domains": False,
                                                          "source_share": False}})
        self.assertFalse(report["ok"])
        self.assertIn("显式声明 origin", " ".join(report["quotas"]["violations"]))
        self.assertEqual(cov.main(["--items", str(fixture([item])), "--profile", "subset",
                                   "--quiet"]), 1)

    def test_subset_enforces_cli_thresholds_only(self):
        path = fixture(self.subset_items())
        self.assertEqual(cov.main(["--items", str(path), "--profile", "subset", "--quiet"]), 0)
        self.assertEqual(cov.main(["--items", str(path), "--profile", "subset",
                                   "--min-total", "100", "--quiet"]), 1)

    def test_subset_ignores_sources_json_quotas(self):
        sources = write_sources({"quotas": {"min_total": 999999, "min_per_domain": 88888,
                                            "max_source_share": 0.01}})
        path = fixture(self.subset_items())
        self.assertEqual(cov.main(["--items", str(path), "--profile", "subset",
                                   "--sources", str(sources), "--quiet"]), 0)

    def test_resolve_quotas_reports_profile_and_enforcement(self):
        resolved = cov.resolve_quotas(profile="subset", use_sources=False)
        self.assertEqual(resolved["profile"], "subset")
        self.assertEqual(resolved["enforce"]["total"], False)
        resolved = cov.resolve_quotas(profile="subset", use_sources=False, min_total=10)
        self.assertEqual(resolved["enforce"]["total"], True)
        with self.assertRaises(ValueError):
            cov.resolve_quotas(profile="nope")


if __name__ == "__main__":
    unittest.main()
