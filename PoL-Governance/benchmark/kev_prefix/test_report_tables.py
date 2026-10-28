"""benchmark/kev_prefix/report_tables.py 的单元测试（纯合成 aggregate JSON，无私有数据）。"""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "report_tables.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rt = load_module("kev_prefix_report_tables", MODULE_PATH)

KEV = "kev-4b-v1.0"
SEED = "seed-43"


# ----------------------------------------------------------------------------- 合成 aggregate JSON

def metric(*, n=10, acc=0.7, brier=0.42, nll=0.91, ece_10=0.101, ece_15=0.1234,
           mean_conf=0.75, confident_error_rate=0.05, coverage=0.8, aurc=0.21):
    return {
        "n": n, "acc": acc, "brier": brier, "nll": nll, "mean_conf": mean_conf,
        "confidence_bias": mean_conf - acc, "ece_10": ece_10, "ece_15": ece_15,
        "coverage_at_0_9": 0.5, "confident_error_rate": confident_error_rate,
        "accuracy_at_0_9": 0.8, "error_rate_at_0_9": 0.2,
        "coverage_at_5pct_error": coverage, "coverage_at_1pct_error": 0.6, "aurc": aurc,
    }


def mini(n, acc, ece_15):
    """分层表只用到 n/acc/ece_15；真实 aggregate 里字段更多，这里保持最小。"""
    return {"n": n, "acc": acc, "ece_15": ece_15}


def build_aggregate():
    kev_served = metric(n=10, acc=0.7, brier=0.42, nll=0.91, ece_10=0.101, ece_15=0.1234)
    seed_served = metric(n=10, acc=0.75, brier=0.4, nll=0.88, ece_10=0.09, ece_15=0.11,
                         mean_conf=0.78, confident_error_rate=0.03, coverage=0.9, aurc=0.18)
    kev_raw = metric(n=10, acc=0.7, brier=0.45, nll=1.0, ece_10=0.14, ece_15=0.15,
                     mean_conf=0.8, confident_error_rate=0.07, coverage=0.75, aurc=0.23)
    return {
        "schema": "kev-prefix-aggregate/1",
        "generated_at": "2026-10-27T16:00:00+00:00",
        "note": "synthetic fixture",
        "settings": {"exclude_overlong": True, "subset_rids": False,
                     "bootstrap_samples": 100, "bootstrap_seed": 0},
        "suite": {"join_sha256": "0" * 64, "records": 12, "clean_questions": 10},
        "runs": {
            KEV: {
                "coverage": {"clean_rows_in_rows_json": 10, "primary_questions": 10,
                             "dropped": {"unknown_record": 0, "variant": 0,
                                         "overlong": 1, "not_in_subset": 0}},
                "served": {
                    "overall": kev_served,
                    "by_kind": {"choice": mini(6, 0.6667, 0.1), "noul": mini(4, 0.75, 0.15)},
                    "by_lang": {"en": mini(10, 0.7, 0.1234)},
                    "by_domain": {"knowledge_reasoning": mini(6, 0.6667, 0.1),
                                  "decision_mechanics": mini(4, 0.75, 0.15)},
                    "by_option_bucket": {"2": mini(5, 0.6, 0.1), "3-4": mini(5, 0.8, 0.14)},
                    "by_state_chars": {"<=400": mini(3, 0.6667, 0.1),
                                       "401-1200": mini(7, 0.7143, 0.13)},
                },
                "raw_t1": {"overall": kev_raw},
                "run_metadata": {"temperature": 2.41,
                                 "latency_ms": {"median": 123.456, "p95": 250.0},
                                 "coverage": {"requested_records": 12},
                                 "environment": {"dtype": "bf16"},
                                 "suite_sha256": "a" * 64, "date_facts": None, "rotations": None},
            },
            SEED: {
                "coverage": {"clean_rows_in_rows_json": 10, "primary_questions": 10,
                             "dropped": {"unknown_record": 1, "variant": 0,
                                         "overlong": 0, "not_in_subset": 0}},
                "served": {
                    "overall": seed_served,
                    "by_kind": {"choice": mini(5, 0.8, 0.08), "noul": mini(2, 0.5, 0.2),
                                "score": mini(3, 1.0, 0.05)},
                    "by_lang": {"en": mini(10, 0.75, 0.11)},
                    "by_domain": {"knowledge_reasoning": mini(7, 0.7143, 0.1)},
                    "by_option_bucket": {"2": mini(6, 0.8333, 0.07), ">26": mini(4, 0.5, 0.2)},
                    "by_state_chars": {"<=400": mini(4, 0.75, 0.1), ">3000": mini(6, 0.8333, 0.09)},
                },
                "raw_t1": None,
                "run_metadata": {"temperature": 1.0,
                                 "latency_ms": {"median": 98.7, "p95": None},
                                 "coverage": None, "environment": None,
                                 "suite_sha256": None, "date_facts": None, "rotations": None},
            },
        },
        "variants": {
            KEV: {"permuted": None, "isolation": None},
            SEED: {"permuted": {"n_pairs": 6, "mean_max_delta": 0.0123, "max_max_delta": 0.5,
                                "median_max_delta": 0.0111, "flip_rate": 0.1666666,
                                "accuracy_unchanged_rate": 0.8333333},
                   "isolation": None},
        },
        "paired": {
            f"{SEED} vs {KEV}": {
                "served": {
                    "n_pairs": 10, "groups": 10, "samples": 100, "seed": 0,
                    "unit": "group_id cluster (item/family), paired by (id, question)",
                    "deltas": {
                        "acc": {"delta": 0.05, "ci95": [-0.0123, 0.1123]},
                        "nll": {"delta": 0.125, "ci95": [0.0101, 0.24]},
                        "brier": {"delta": -0.02, "ci95": [-0.03, -0.01]},
                        "ece_10": {"delta": -0.0313, "ci95": [-0.05, -0.0125]},
                    },
                },
                "raw_t1": {"error": "no paired questions with logits"},
            },
        },
        "provenance": {"aggregate_sha256": "1" * 64, "reference": KEV},
    }


AGG = build_aggregate()


def invoke(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = rt.main(list(args))
    return code, out.getvalue(), err.getvalue()


def table_lines(text, name):
    """取一个 Markdown 表块的表头 + 数据行（不含分隔行）。"""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"### {name} "))
    block = []
    for line in lines[start + 1:]:
        if line.startswith("### ") or line.startswith("## "):
            break
        if line.startswith("| ") and not line.startswith("| ---"):
            block.append(line)
    return block


# ----------------------------------------------------------------------------- 格式化

class FormatTest(unittest.TestCase):
    def test_integers_and_ratios(self):
        self.assertEqual(rt.fmt_int(10), "10")
        self.assertEqual(rt.fmt_int(10.0), "10")
        self.assertEqual(rt.fmt_int(0), "0")
        self.assertEqual(rt.fmt_ratio(0.7), "0.7000")
        self.assertEqual(rt.fmt_ratio(0), "0.0000")
        self.assertEqual(rt.fmt_latency(12.34), "12.34")
        self.assertEqual(rt.fmt_latency(12.3), "12.30")

    def test_missing_never_becomes_zero(self):
        for value in (None, float("nan"), float("inf"), float("-inf"), True, "", "0.5", [], {}):
            self.assertEqual(rt.fmt_ratio(value), rt.MISSING)
        self.assertEqual(rt.fmt_int(None), rt.MISSING)
        self.assertEqual(rt.fmt_signed(None), rt.MISSING)
        self.assertEqual(rt.fmt_ci(None), rt.MISSING)

    def test_signed_delta_and_ci(self):
        self.assertEqual(rt.fmt_signed(0.01234), "+0.0123")
        self.assertEqual(rt.fmt_signed(-0.01234), "-0.0123")
        self.assertEqual(rt.fmt_signed(0), "+0.0000")
        self.assertEqual(rt.fmt_ci([-0.01, 0.02]), "[-0.0100, +0.0200]")
        self.assertEqual(rt.fmt_ci([None, 0.02]), rt.MISSING)
        self.assertEqual(rt.fmt_ci([0.01]), rt.MISSING)

    def test_compact(self):
        self.assertEqual(rt.fmt_compact(None), rt.MISSING)
        self.assertEqual(rt.fmt_compact({}), "{}")
        self.assertEqual(rt.fmt_compact({"b": 2, "a": 1}), "a=1, b=2")
        self.assertEqual(rt.fmt_compact({"nested": {"x": 1}}), 'nested={"x":1}')


# ----------------------------------------------------------------------------- 表结构

class TableShapeTest(unittest.TestCase):
    def setUp(self):
        self.tables = rt.build_tables(AGG)

    def test_table_names_and_sections(self):
        self.assertEqual(list(self.tables), [
            "main_served", "main_raw_t1", "calibration",
            "strata_kind", "strata_lang", "strata_domain",
            "strata_option_bucket", "strata_state_chars",
            "paired_served", "paired_raw_t1", "variants", "latency",
        ])
        for name, table in self.tables.items():
            self.assertEqual(table["name"], name)
            self.assertIn(table["section"], rt.SECTION_ORDER)
            self.assertTrue(table["columns"])

    def test_main_served_columns_and_values(self):
        table = self.tables["main_served"]
        self.assertEqual([column[0] for column in table["columns"]], [
            "run", "n", "acc", "brier", "nll", "ece_10", "ece_15",
            "coverage_at_5pct_error", "aurc",
        ])
        self.assertEqual(len(table["rows"]), 2)
        row = table["rows"][0]
        self.assertEqual(row["run"], KEV)
        self.assertEqual(row["n"], "10")
        self.assertEqual(row["acc"], "0.7000")
        self.assertEqual(row["brier"], "0.4200")
        self.assertEqual(row["nll"], "0.9100")
        self.assertEqual(row["ece_10"], "0.1010")
        self.assertEqual(row["ece_15"], "0.1234")
        self.assertEqual(row["coverage_at_5pct_error"], "0.8000")
        self.assertEqual(row["aurc"], "0.2100")
        self.assertEqual(table["rows"][1]["acc"], "0.7500")

    def test_raw_t1_missing_run_uses_dash(self):
        table = self.tables["main_raw_t1"]
        self.assertEqual([column[0] for column in table["columns"]],
                         ["run", "n", "acc", "brier", "nll", "ece_15"])
        self.assertEqual(len(table["rows"]), 2)
        self.assertEqual(table["rows"][0]["ece_15"], "0.1500")
        missing = table["rows"][1]
        self.assertEqual(missing["run"], SEED)
        for key in ("n", "acc", "brier", "nll", "ece_15"):
            self.assertEqual(missing[key], rt.MISSING)

    def test_calibration_served_and_raw(self):
        rows = self.tables["calibration"]["rows"]
        self.assertEqual(len(rows), 4)
        self.assertEqual([(row["run"], row["mode"]) for row in rows],
                         [(KEV, "served"), (KEV, "raw_t1"),
                          (SEED, "served"), (SEED, "raw_t1")])
        self.assertEqual(rows[0]["mean_conf"], "0.7500")
        self.assertEqual(rows[0]["confident_error_rate"], "0.0500")
        self.assertEqual(rows[0]["coverage_at_5pct_error"], "0.8000")
        self.assertEqual(rows[1]["ece_10"], "0.1400")
        self.assertEqual(rows[1]["ece_15"], "0.1500")
        self.assertEqual(rows[3]["n"], rt.MISSING)
        self.assertEqual(rows[3]["mean_conf"], rt.MISSING)

    def test_strata_kind_rows_and_columns(self):
        table = self.tables["strata_kind"]
        self.assertEqual([row["bucket"] for row in table["rows"]], ["choice", "noul", "score"])
        self.assertEqual([column[0] for column in table["columns"]], [
            "bucket", f"{KEV} n", f"{KEV} acc", f"{KEV} ece_15",
            f"{SEED} n", f"{SEED} acc", f"{SEED} ece_15",
        ])
        choice, _, score = table["rows"]
        self.assertEqual(choice[f"{KEV} n"], "6")
        self.assertEqual(choice[f"{KEV} acc"], "0.6667")
        self.assertEqual(choice[f"{SEED} acc"], "0.8000")
        self.assertEqual(score[f"{KEV} n"], rt.MISSING)
        self.assertEqual(score[f"{SEED} n"], "3")
        self.assertEqual(score[f"{SEED} ece_15"], "0.0500")

    def test_strata_bucket_order(self):
        tables = self.tables
        self.assertEqual([row["bucket"] for row in tables["strata_option_bucket"]["rows"]],
                         ["2", "3-4", ">26"])
        self.assertEqual([row["bucket"] for row in tables["strata_state_chars"]["rows"]],
                         ["<=400", "401-1200", ">3000"])
        self.assertEqual([row["bucket"] for row in tables["strata_domain"]["rows"]],
                         ["decision_mechanics", "knowledge_reasoning"])
        self.assertEqual([row["bucket"] for row in tables["strata_lang"]["rows"]], ["en"])

    def test_paired_deltas_and_ci(self):
        table = self.tables["paired_served"]
        self.assertEqual([column[0] for column in table["columns"]], [
            "comparison", "n_pairs",
            "acc_delta", "acc_ci95", "nll_delta", "nll_ci95",
            "brier_delta", "brier_ci95", "ece_10_delta", "ece_10_ci95",
        ])
        self.assertEqual(len(table["rows"]), 1)
        row = table["rows"][0]
        self.assertEqual(row["comparison"], f"{SEED} vs {KEV}")
        self.assertEqual(row["n_pairs"], "10")
        self.assertEqual(row["acc_delta"], "+0.0500")
        self.assertEqual(row["acc_ci95"], "[-0.0123, +0.1123]")
        self.assertEqual(row["nll_delta"], "+0.1250")
        self.assertEqual(row["brier_delta"], "-0.0200")
        self.assertEqual(row["ece_10_delta"], "-0.0313")
        self.assertEqual(row["ece_10_ci95"], "[-0.0500, -0.0125]")

    def test_paired_unavailable_mode_uses_dash(self):
        rows = self.tables["paired_raw_t1"]["rows"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["comparison"], f"{SEED} vs {KEV}")
        for key in ("n_pairs", "acc_delta", "acc_ci95", "nll_delta", "brier_delta", "ece_10_ci95"):
            self.assertEqual(row[key], rt.MISSING)

    def test_variants(self):
        rows = self.tables["variants"]["rows"]
        self.assertEqual(len(rows), 4)
        self.assertEqual([(row["run"], row["variant"]) for row in rows], [
            (KEV, "permuted"), (KEV, "isolation"),
            (SEED, "permuted"), (SEED, "isolation"),
        ])
        seed_permuted = rows[2]
        self.assertEqual(seed_permuted["n_pairs"], "6")
        self.assertEqual(seed_permuted["mean_max_delta"], "0.0123")
        self.assertEqual(seed_permuted["max_max_delta"], "0.5000")
        self.assertEqual(seed_permuted["median_max_delta"], "0.0111")
        self.assertEqual(seed_permuted["flip_rate"], "0.1667")
        self.assertEqual(seed_permuted["accuracy_unchanged_rate"], "0.8333")
        self.assertEqual(rows[0]["n_pairs"], rt.MISSING)

    def test_latency_and_coverage(self):
        rows = self.tables["latency"]["rows"]
        self.assertEqual(len(rows), 2)
        kev, seed = rows
        self.assertEqual(kev["temperature"], "2.4100")
        self.assertEqual(kev["latency_median_ms"], "123.46")
        self.assertEqual(kev["latency_p95_ms"], "250.00")
        self.assertEqual(kev["coverage_primary_questions"], "10")
        self.assertEqual(kev["coverage_dropped"],
                         "not_in_subset=0, overlong=1, unknown_record=0, variant=0")
        self.assertEqual(kev["coverage_report"], "requested_records=12")
        self.assertEqual(seed["temperature"], "1.0000")
        self.assertEqual(seed["latency_median_ms"], "98.70")
        self.assertEqual(seed["latency_p95_ms"], rt.MISSING)
        self.assertEqual(seed["coverage_report"], rt.MISSING)

    def test_absent_sections_keep_explicit_dashes(self):
        tables = rt.build_tables({"runs": {"solo": {}}})
        variant_rows = tables["variants"]["rows"]
        self.assertEqual(len(variant_rows), 2)
        self.assertTrue(all(row["n_pairs"] == rt.MISSING for row in variant_rows))
        self.assertEqual(tables["paired_served"]["rows"], ())

    def test_empty_aggregate(self):
        tables = rt.build_tables({})
        self.assertEqual(len(tables), 12)
        self.assertTrue(all(not table["rows"] for table in tables.values()))
        payload = rt.tables_payload(rt.select_tables(tables, "all"))
        self.assertTrue(all(rows == [] for rows in payload.values()))
        text = rt.render_markdown(tables)
        self.assertEqual(text.count("_（无数据）_"), 12)
        self.assertTrue(text.endswith("\n"))


# ----------------------------------------------------------------------------- Markdown

class MarkdownTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = rt.build_tables(AGG)
        cls.text = rt.render_markdown(cls.tables)

    def test_sections_and_table_headings(self):
        for section in rt.SECTION_ORDER:
            self.assertIn(f"## {section}", self.text)
        for name in self.tables:
            self.assertIn(f"### {name} ·", self.text)

    def test_table_row_counts_match_payload(self):
        for name, table in self.tables.items():
            lines = table_lines(self.text, name)
            self.assertEqual(len(lines), 1 + len(table["rows"]), name)

    def test_main_table_header_and_rows(self):
        lines = table_lines(self.text, "main_served")
        self.assertEqual(
            lines[0],
            "| run | n（样本量） | acc | brier | nll | ece_10 | ece_15 | coverage@5%err | aurc |",
        )
        self.assertEqual(len(lines) - 1, 2)
        self.assertTrue(lines[1].startswith(f"| {KEV} |"))
        self.assertTrue(lines[2].startswith(f"| {SEED} |"))

    def test_missing_is_dash_not_zero(self):
        lines = table_lines(self.text, "main_raw_t1")
        seed = next(line for line in lines[1:] if line.startswith(f"| {SEED} |"))
        cells = [cell.strip() for cell in seed.strip("|").split("|")]
        self.assertEqual(cells[1:], [rt.MISSING] * 5)
        self.assertNotIn("0.0000", cells[1:])

    def test_deltas_are_signed_with_ci(self):
        self.assertIn("+0.0500", self.text)
        self.assertIn("-0.0200", self.text)
        self.assertIn("[-0.0123, +0.1123]", self.text)
        self.assertIn("95% CI", self.text)

    def test_output_is_newline_terminated_and_gbk_safe(self):
        self.assertTrue(self.text.endswith("\n"))
        self.text.encode("gbk")  # Windows GBK 控制台不应 UnicodeEncodeError


# ----------------------------------------------------------------------------- JSON

class JsonPayloadTest(unittest.TestCase):
    def test_payload_is_table_name_to_rows(self):
        tables = rt.build_tables(AGG)
        payload = rt.tables_payload(tables)
        self.assertEqual(list(payload), list(tables))
        self.assertEqual(len(payload["main_served"]), 2)
        self.assertEqual(payload["main_served"][0]["acc"], "0.7000")
        self.assertEqual(payload["main_raw_t1"][1]["acc"], rt.MISSING)
        self.assertEqual(len(payload["strata_kind"]), 3)
        self.assertEqual(len(payload["paired_served"]), 1)
        self.assertEqual(len(payload["variants"]), 4)
        for rows in payload.values():
            for row in rows:
                self.assertTrue(all(isinstance(value, str) for value in row.values()))


# ----------------------------------------------------------------------------- CLI

class CliTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "aggregate.json"
        self.path.write_text(json.dumps(AGG, ensure_ascii=False), encoding="utf-8")

    def test_default_is_all_markdown(self):
        code, out, err = invoke("--aggregate", str(self.path))
        self.assertEqual((code, err), (0, ""))
        for section in rt.SECTION_ORDER:
            self.assertIn(f"## {section}", out)
        self.assertIn("### main_served ·", out)

    def test_section_filter_markdown(self):
        code, out, err = invoke("--aggregate", str(self.path), "--section", "main")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("### main_served", out)
        self.assertIn("### main_raw_t1", out)
        self.assertNotIn("## paired", out)
        self.assertNotIn("### calibration", out)
        self.assertNotIn("### variants", out)

    def test_section_filter_json(self):
        code, out, err = invoke("--aggregate", str(self.path), "--section", "paired",
                                "--format", "json")
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(list(data), ["paired_served", "paired_raw_t1"])
        self.assertEqual(len(data["paired_served"]), 1)
        self.assertEqual(data["paired_raw_t1"][0]["acc_delta"], rt.MISSING)
        self.assertTrue(out.isascii())  # ensure_ascii=True，Windows 管道安全

    def test_strata_json_has_five_tables(self):
        code, out, _ = invoke("--aggregate", str(self.path), "--section", "strata",
                              "--format", "json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(list(data), list(rt.SECTION_TABLES["strata"]))
        self.assertEqual(len(data["strata_kind"]), 3)

    def test_all_json_matches_tables(self):
        code, out, _ = invoke("--aggregate", str(self.path), "--format", "json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(list(data), list(rt.build_tables(AGG)))
        self.assertEqual(data["main_served"][1]["acc"], "0.7500")
        self.assertEqual(data["latency"][0]["coverage_report"], "requested_records=12")

    def test_invalid_section_exits_2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                rt.main(["--aggregate", str(self.path), "--section", "nope"])
        self.assertEqual(context.exception.code, 2)

    def test_missing_file_returns_2(self):
        code, out, err = invoke("--aggregate", str(Path(self.directory.name) / "absent.json"))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("cannot read", err)

    def test_invalid_json_returns_2(self):
        bad = Path(self.directory.name) / "bad.json"
        bad.write_text("{", encoding="utf-8")
        code, _, err = invoke("--aggregate", str(bad))
        self.assertEqual(code, 2)
        self.assertIn("invalid JSON", err)

    def test_non_object_root_returns_2(self):
        bad = Path(self.directory.name) / "list.json"
        bad.write_text("[1, 2]", encoding="utf-8")
        code, _, err = invoke("--aggregate", str(bad))
        self.assertEqual(code, 2)
        self.assertIn("JSON object", err)


if __name__ == "__main__":
    unittest.main()
