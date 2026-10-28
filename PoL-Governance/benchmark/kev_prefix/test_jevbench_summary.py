"""jevbench_summary.py 的单元测试（真实 fake backend 报告的裁剪 fixture，无私有数据）。"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "jevbench_summary.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


js = load_module("kev_prefix_jevbench_summary", MODULE_PATH)

_UNSET = object()

# 以下数值来自真实 fake 报告：
#   jevbench eval --backend fake:coherent --suite examples --out /tmp/jev-sample.json
#   jevbench eval --backend fake:biased   --suite examples --out /tmp/jev-biased.json
#   jevbench eval --backend fake:coherent --suite jevbench-mini --out /tmp/jev-mini.json
COHERENT = {
    "overall": 0.6501960784313725,
    "pillars": {
        "REP": 0.5333333333333333,
        "BAT": 1.0,
        "MEA": 0.11764705882352941,
        "LOG": 0.6,
        "CHO": 1.0,
    },
    "ci": {},
    "n_cases": 1,
    "n_checks": 50,
    "n_outcomes": 57,
    "min_n": 1,
}
BIASED = {
    "overall": 0.5235294117647059,
    "pillars": {
        "REP": 0.5333333333333333,
        "BAT": 0.6,
        "MEA": 0.11764705882352941,
        "LOG": 0.7,
        "CHO": 0.6666666666666666,
    },
    "ci": {},
    "n_cases": 1,
    "n_checks": 50,
    "n_outcomes": 57,
    "min_n": 1,
}
MINI = {
    "overall": 0.648545751633987,
    "pillars": {
        "REP": 0.5861111111111111,
        "BAT": 1.0,
        "MEA": 0.0857843137254902,
        "LOG": 0.5708333333333333,
        "CHO": 1.0,
    },
    "ci": {
        "overall": [0.6379455972511646, 0.6588315930294167],
        "graded_overall": [0.9263041666208127, 0.9332548849917625],
    },
    "n_cases": 240,
    "n_checks": 50,
    "n_outcomes": 1468,
    "min_n": 5,
}


def fake_report(
    *,
    name="fake:coherent",
    overall=COHERENT["overall"],
    pillars=None,
    ci=None,
    n_cases=COHERENT["n_cases"],
    n_checks=COHERENT["n_checks"],
    n_outcomes=COHERENT["n_outcomes"],
    min_n=COHERENT["min_n"],
    errors=(),
    suite_name="examples",
    suite_version="2",
    accuracy=_UNSET,
    generated_at=None,
    jevbench_version="0.1.0",
):
    """构造符合 jevbench 0.1.0 实际 schema 的最小报告；默认值取自 examples 实跑。"""
    pillars = dict(COHERENT["pillars"] if pillars is None else pillars)
    data = {
        "jevbench_report": 1,
        "name": name,
        "settings": {
            "tolerance": 0.05,
            "min_n": min_n,
            "bootstrap": 1000,
            "min_coverage": 0.95,
        },
        "scores": {
            "backend": name,
            "environment": {"python": "3.12.3", "httpx": "0.28.1"},
            "tolerance": "fixed 0.05",
            "min_n": min_n,
            "overall": overall,
            "pillars": pillars,
            "groups": {},
            "relations": {},
            "graded": {
                "relations": {},
                "groups": {},
                "pillars": dict(pillars),
                "overall": overall,
            },
            "ci": dict(ci or {}),
            "n_cases": n_cases,
            "bootstrap": 1000,
            "checks": {},
            "incomplete": [],
            "min_coverage": 0.95,
            "excluded": {"low_n": [], "exploratory": [], "diagnostic": []},
            "n_checks": n_checks,
            "n_outcomes": n_outcomes,
            "skipped_outcomes": 0,
            "mean_repeat_noise": None,
        },
        "result": {
            "jevbench_version": jevbench_version,
            "backend": name,
            "environment": {"python": "3.12.3", "httpx": "0.28.1"},
            "seed": 0,
            "repeats": 1,
            "trials": 1,
            "noise_multiplier": 2.0,
            "noise_floor": 0.05,
            "relations": ["batch_content"],
            "cases": ["support-001"],
            "requests": 43,
            "cache_hits": 9,
            "backend_seconds": 0.009,
            "wall_seconds": 0.04,
            "planned_tests": {"batch_content": 1},
            "concurrency": 1,
            "truncated_by_budget": False,
            "backend_down": None,
            "bases": {"support-001": {"base": {}, "noise": {}}},
            "outcomes": [
                {
                    "relation": "batch_content",
                    "check": "tv",
                    "case_id": "support-001",
                    "detail": {"rewrite": "SECRET-REQUEST-BODY"},
                    "violated": False,
                }
            ],
            "errors": list(errors),
            "suite": {
                "name": suite_name,
                "version": suite_version,
                "files": {},
                "plan": "tests.jsonl.gz",
            },
            "case_domains": {"support-001": "customer_support"},
            "selection": {
                "domains": None,
                "dimensions": None,
                "groups": None,
                "relations": None,
                "diagnostics": False,
            },
        },
    }
    if accuracy is not _UNSET:
        data["scores"]["accuracy"] = accuracy
    if generated_at is not None:
        data["generated_at"] = generated_at
    return data


def write_report(directory, filename, data):
    path = Path(directory) / filename
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def run_main(args):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = js.main(args)
    return code, stdout.getvalue(), stderr.getvalue()


def section_lines(markdown, name):
    lines = markdown.splitlines()
    heading = f"## {name}"
    if heading not in lines:
        raise AssertionError(f"missing section {heading!r} in:\n{markdown}")
    start = lines.index(heading)
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return lines[start + 1:end]


def section_table(markdown, name):
    table_lines = [line for line in section_lines(markdown, name) if line.startswith("|")]
    if len(table_lines) < 2:
        raise AssertionError(f"section {name!r} has no Markdown table")
    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(dict(zip(header, cells)))
    return header, rows


class SummaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def path(self, filename, data):
        return write_report(self.dir, filename, data)

    # ------------------------------------------------------------------ 主表

    def test_summary_table_columns_rows_and_metadata(self):
        coherent = self.path("coherent.json", fake_report(
            name="fake:coherent",
            generated_at="2026-10-27T16:00:00+00:00",
        ))
        biased = self.path("biased.json", fake_report(
            name="fake:biased",
            overall=BIASED["overall"],
            pillars=BIASED["pillars"],
            generated_at="2026-10-27T16:05:00+00:00",
        ))
        code, out, err = run_main([
            "--report", f"kev-original={coherent}",
            "--report", f"seed43={biased}",
        ])
        self.assertEqual(code, 0, err)
        for heading in ("## summary", "## deltas", "## metadata"):
            self.assertIn(heading, out)

        header, rows = section_table(out, "summary")
        self.assertEqual(header, [
            "model", "suite", "version", "overall", "REP", "BAT", "MEA",
            "LOG", "CHO", "accuracy", "95% CI", "min_n", "cases",
        ])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], {
            "model": "kev-original",
            "suite": "examples",
            "version": "2",
            "overall": "0.6502",
            "REP": "0.5333",
            "BAT": "1.0000",
            "MEA": "0.1176",
            "LOG": "0.6000",
            "CHO": "1.0000",
            "accuracy": "—",
            "95% CI": "—",
            "min_n": "1",
            "cases": "1",
        })
        self.assertEqual(rows[1]["model"], "seed43")
        self.assertEqual(rows[1]["overall"], "0.5235")
        self.assertEqual(rows[1]["BAT"], "0.6000")
        self.assertEqual(rows[1]["LOG"], "0.7000")
        self.assertEqual(rows[1]["CHO"], "0.6667")
        self.assertEqual(rows[1]["accuracy"], "—")
        self.assertEqual(rows[1]["95% CI"], "—")

        delta_header, deltas = section_table(out, "deltas")
        self.assertEqual(delta_header, [
            "comparison", "overall", "REP", "BAT", "MEA", "LOG", "CHO",
        ])
        self.assertEqual(deltas, [{
            "comparison": "seed43 - kev-original",
            "overall": "-0.1267",
            "REP": "+0.0000",
            "BAT": "-0.4000",
            "MEA": "+0.0000",
            "LOG": "+0.1000",
            "CHO": "-0.3333",
        }])

        metadata_header, metadata = section_table(out, "metadata")
        self.assertEqual(metadata_header, [
            "model", "jevbench", "suite", "version", "run date", "errors",
        ])
        self.assertEqual(metadata[0], {
            "model": "kev-original",
            "jevbench": "0.1.0",
            "suite": "examples",
            "version": "2",
            "run date": "2026-10-27",
            "errors": "0",
        })
        # 逐例内容绝不能出现在结果卡输出里
        self.assertNotIn("SECRET-REQUEST-BODY", out)
        self.assertNotIn("support-001", out)

    # ------------------------------------------------------------------ 缺失

    def test_missing_values_render_as_em_dash_not_zero(self):
        data = fake_report(name="fake:coherent", overall=None, pillars={"REP": 0.0})
        data["scores"].pop("overall")
        data["scores"].pop("min_n")
        data["settings"].pop("min_n")
        data["scores"].pop("n_cases")
        data["scores"]["ci"] = {}
        data["result"].pop("errors")
        data["result"].pop("suite")
        data["result"].pop("jevbench_version")
        report = self.path("missing.json", data)
        stamp = 1790000000
        os.utime(report, (stamp, stamp))

        code, out, err = run_main(["--report", f"partial={report}"])
        self.assertEqual(code, 0, err)
        _, rows = section_table(out, "summary")
        row = rows[0]
        for column in ("overall", "BAT", "MEA", "LOG", "CHO", "accuracy", "95% CI",
                       "min_n", "cases", "suite", "version"):
            self.assertEqual(row[column], "—", column)
        self.assertEqual(row["REP"], "0.0000")  # 真实 0 不能被吞成缺失

        _, metadata = section_table(out, "metadata")
        self.assertEqual(metadata[0]["jevbench"], "—")
        self.assertEqual(metadata[0]["suite"], "—")
        self.assertEqual(metadata[0]["version"], "—")
        self.assertEqual(metadata[0]["errors"], "—")
        expected_date = datetime.fromtimestamp(stamp).date().isoformat()
        self.assertEqual(metadata[0]["run date"], expected_date)

    def test_missing_delta_is_em_dash(self):
        a = self.path("delta-a.json", fake_report(
            name="fake:a", overall=0.5, pillars={"REP": 0.5},
            generated_at="2026-10-27T12:00:00Z"))
        b = self.path("delta-b.json", fake_report(
            name="fake:b", overall=0.6, pillars={"REP": 0.6},
            generated_at="2026-10-27T12:00:00Z"))
        code, out, err = run_main(["--report", f"A={a}", "--report", f"B={b}"])
        self.assertEqual(code, 0, err)
        _, rows = section_table(out, "deltas")
        self.assertEqual(rows[0]["overall"], "+0.1000")
        self.assertEqual(rows[0]["REP"], "+0.1000")
        self.assertEqual(rows[0]["BAT"], "—")
        self.assertEqual(rows[0]["MEA"], "—")

    # ------------------------------------------------------------------ 差值

    def test_adjacent_and_reference_deltas(self):
        def controlled(label, value):
            return fake_report(
                name=f"fake:{label}",
                overall=value,
                pillars={pillar: value for pillar in ("REP", "BAT", "MEA", "LOG", "CHO")},
                generated_at="2026-10-27T12:00:00Z",
            )

        a = self.path("a.json", controlled("a", 0.5))
        b = self.path("b.json", controlled("b", 0.6))
        c = self.path("c.json", controlled("c", 0.4))
        reports = ["--report", f"A={a}", "--report", f"B={b}", "--report", f"C={c}"]

        code, out, err = run_main(reports)
        self.assertEqual(code, 0, err)
        _, rows = section_table(out, "deltas")
        self.assertEqual([row["comparison"] for row in rows], ["B - A", "C - B"])
        self.assertEqual([row["overall"] for row in rows], ["+0.1000", "-0.2000"])

        code, out, err = run_main(reports + ["--reference", "A"])
        self.assertEqual(code, 0, err)
        _, rows = section_table(out, "deltas")
        self.assertEqual([row["comparison"] for row in rows], ["B - A", "C - A"])
        self.assertEqual([row["overall"] for row in rows], ["+0.1000", "-0.1000"])
        self.assertEqual(rows[0]["REP"], "+0.1000")
        self.assertEqual(rows[0]["CHO"], "+0.1000")

        code, out, err = run_main(reports + ["--reference", "B"])
        self.assertEqual(code, 0, err)
        _, rows = section_table(out, "deltas")
        self.assertEqual([row["comparison"] for row in rows], ["A - B", "C - B"])
        self.assertEqual([row["overall"] for row in rows], ["-0.1000", "-0.2000"])

    def test_unknown_reference_and_duplicate_names_fail(self):
        report = self.path("one.json", fake_report())
        code, _, err = run_main(["--report", f"A={report}", "--reference", "missing"])
        self.assertEqual(code, 2)
        self.assertIn("unknown --reference", err)

        code, _, err = run_main(["--report", f"A={report}", "--report", f"A={report}"])
        self.assertEqual(code, 2)
        self.assertIn("duplicate report name", err)

        code, _, err = run_main(["--report", str(report)])
        self.assertEqual(code, 2)
        self.assertIn("NAME=PATH", err)

    # ------------------------------------------------------------------ CI/accuracy

    def test_ci_and_optional_accuracy(self):
        report = self.path("mini.json", fake_report(
            name="fake:coherent",
            overall=MINI["overall"],
            pillars=MINI["pillars"],
            ci=MINI["ci"],
            n_cases=MINI["n_cases"],
            n_checks=MINI["n_checks"],
            n_outcomes=MINI["n_outcomes"],
            min_n=MINI["min_n"],
            suite_name="jevbench-mini",
            suite_version="1",
            accuracy=0.712345,
            generated_at="2026-10-27T12:00:00Z",
        ))
        code, out, err = run_main(["--report", f"seed43={report}"])
        self.assertEqual(code, 0, err)
        _, rows = section_table(out, "summary")
        row = rows[0]
        self.assertEqual(row["overall"], "0.6485")
        self.assertEqual(row["95% CI"], "[0.6379, 0.6588]")
        self.assertEqual(row["accuracy"], "0.7123")
        self.assertEqual(row["min_n"], "5")
        self.assertEqual(row["cases"], "240")
        self.assertEqual(row["suite"], "jevbench-mini")
        self.assertEqual(row["version"], "1")

    def test_accuracy_dict_value(self):
        report = self.path("acc.json", fake_report(accuracy={"value": 0.625}))
        code, out, err = run_main(["--report", f"A={report}"])
        self.assertEqual(code, 0, err)
        _, rows = section_table(out, "summary")
        self.assertEqual(rows[0]["accuracy"], "0.6250")

    # ------------------------------------------------------------------ JSON

    def test_json_summary_structure_and_out_file(self):
        coherent = self.path("coherent.json", fake_report(generated_at="2026-10-27T12:00:00Z"))
        mini = self.path("mini.json", fake_report(
            name="fake:mini",
            overall=MINI["overall"],
            pillars=MINI["pillars"],
            ci=MINI["ci"],
            n_cases=MINI["n_cases"],
            n_checks=MINI["n_checks"],
            n_outcomes=MINI["n_outcomes"],
            min_n=MINI["min_n"],
            suite_name="jevbench-mini",
            suite_version="1",
            generated_at="2026-10-27T12:05:00Z",
        ))
        out_path = self.dir / "nested" / "summary.json"
        code, out, err = run_main([
            "--report", f"kev-original={coherent}",
            "--report", f"seed43={mini}",
            "--format", "json",
            "--out", str(out_path),
        ])
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(json.loads(out_path.read_text(encoding="utf-8")), payload)
        self.assertTrue(out_path.read_text(encoding="utf-8").endswith("\n"))

        self.assertEqual(payload["schema"], "jevbench-summary/1")
        self.assertEqual(len(payload["models"]), 2)
        expected_keys = {
            "name", "report_name", "suite", "suite_version", "jevbench_version",
            "run_date", "errors", "overall", "pillars", "accuracy", "overall_ci",
            "min_n", "n_cases", "n_checks", "n_outcomes", "bootstrap",
        }
        self.assertEqual(set(payload["models"][0]), expected_keys)
        self.assertEqual(payload["models"][0]["name"], "kev-original")
        self.assertEqual(payload["models"][0]["report_name"], "fake:coherent")
        self.assertAlmostEqual(payload["models"][0]["overall"], COHERENT["overall"])
        self.assertAlmostEqual(payload["models"][0]["pillars"]["MEA"], COHERENT["pillars"]["MEA"])
        self.assertEqual(set(payload["models"][0]["pillars"]), {"REP", "BAT", "MEA", "LOG", "CHO"})
        self.assertIsNone(payload["models"][0]["accuracy"])
        self.assertIsNone(payload["models"][0]["overall_ci"])
        self.assertEqual(payload["models"][1]["overall_ci"], MINI["ci"]["overall"])
        self.assertEqual(payload["models"][1]["min_n"], 5)
        self.assertEqual(payload["models"][1]["n_cases"], 240)

        self.assertEqual(len(payload["comparisons"]), 1)
        comparison = payload["comparisons"][0]
        self.assertEqual(comparison["kind"], "adjacent")
        self.assertEqual(comparison["model"], "seed43")
        self.assertEqual(comparison["reference"], "kev-original")
        self.assertAlmostEqual(comparison["delta"]["overall"], MINI["overall"] - COHERENT["overall"])
        self.assertEqual(set(comparison["delta"]), {"overall", "REP", "BAT", "MEA", "LOG", "CHO"})

        # 摘要 JSON 里不能有逐例字段/内容
        text = out + out_path.read_text(encoding="utf-8")
        self.assertNotIn('"outcomes"', text)
        self.assertNotIn("SECRET-REQUEST-BODY", text)
        self.assertNotIn("support-001", text)
        self.assertNotIn('"bases"', text)

    def test_out_file_with_markdown_stdout(self):
        report = self.path("one.json", fake_report())
        out_path = self.dir / "summary.json"
        code, out, err = run_main(["--report", f"A={report}", "--out", str(out_path)])
        self.assertEqual(code, 0, err)
        self.assertIn("## summary", out)
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["models"][0]["name"], "A")

    # ------------------------------------------------------------------ 元数据

    def test_run_date_and_error_count(self):
        report = self.path("errors.json", fake_report(
            errors=[
                {"case": "support-001", "error": "SECRET-RESPONSE-BODY"},
                {"case": "support-002", "error": "another failure"},
            ],
            generated_at="2026-10-26T23:59:59Z",
        ))
        code, out, err = run_main(["--report", f"A={report}", "--format", "json"])
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["models"][0]["run_date"], "2026-10-26")
        self.assertEqual(payload["models"][0]["errors"], 2)
        self.assertNotIn("SECRET-RESPONSE-BODY", out)

        code, out, err = run_main(["--report", f"A={report}"])
        self.assertEqual(code, 0, err)
        _, metadata = section_table(out, "metadata")
        self.assertEqual(metadata[0]["run date"], "2026-10-26")
        self.assertEqual(metadata[0]["errors"], "2")
        self.assertNotIn("SECRET-RESPONSE-BODY", out)

    # ------------------------------------------------------------------ 校验

    def test_report_validation_errors(self):
        not_jevbench = self.dir / "not.json"
        not_jevbench.write_text(json.dumps({"scores": {}, "result": {}}), encoding="utf-8")
        code, _, err = run_main(["--report", f"X={not_jevbench}"])
        self.assertEqual(code, 2)
        self.assertIn("not a jevbench report", err)

        unsupported = self.path("v2.json", {**fake_report(), "jevbench_report": 2})
        code, _, err = run_main(["--report", f"X={unsupported}"])
        self.assertEqual(code, 2)
        self.assertIn("unsupported jevbench_report format", err)

        broken = self.dir / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        code, _, err = run_main(["--report", f"X={broken}"])
        self.assertEqual(code, 2)
        self.assertIn("invalid JSON", err)


if __name__ == "__main__":
    unittest.main()
