"""check_aggregate_export 的纯标准库单元测试（无网络 / 无 GPU / 无私有数据）。

所有样例都在测试内按 spec 第 1 节合成，不依赖 final_eval_aggregate.py 或其他模块。
"""
from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from finetune import check_aggregate_export as checker


def ci(accuracy):
    """构造包含点估计的粗略 CI（检查器只要求包含点估计且单调）。"""
    return [max(0.0, round(accuracy - 0.1, 6)), min(1.0, round(accuracy + 0.1, 6))]


def block(total, correct):
    accuracy = round(correct / total, 6) if total else 0.0
    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "ci95_wilson": ci(accuracy),
    }


def model(total, correct, missing=0, expected=None):
    expected = total if expected is None else expected
    accuracy = round(correct / total, 6) if total else 0.0
    if total == 96 and correct == 40:
        languages = {"en": block(60, 25), "zh": block(36, 15)}
        buckets = {"2": block(10, 4), "3-4": block(26, 11),
                   "5-8": block(40, 17), "9-26": block(20, 8)}
        routes = {"classification": block(70, 30), "distillation": block(26, 10)}
    elif total == 96 and correct == 50:
        languages = {"en": block(60, 32), "zh": block(36, 18)}
        buckets = {"2": block(10, 5), "3-4": block(26, 14),
                   "5-8": block(40, 20), "9-26": block(20, 11)}
        routes = {"classification": block(70, 37), "distillation": block(26, 13)}
    else:
        languages = {"en": block(total, correct), "zh": {}}
        buckets = {"2": block(total, correct), "3-4": {}, "5-8": {}, "9-26": {}}
        routes = {"classification": block(total, correct), "distillation": {}}
    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "accuracy_ci95_wilson": ci(accuracy),
        "accuracy_with_missing": round(correct / expected, 6) if expected else 0.0,
        "missing_rows": missing,
        "by_kind": {"choice": block(total, correct), "noul": {}, "score": {}},
        "by_lang": languages,
        "by_option_bucket": buckets,
        "by_route": routes,
    }


def metric(accuracy, nll, brier, ece, mce, rows=96):
    return {"rows": rows, "accuracy": accuracy, "nll": nll,
            "brier": brier, "ece": ece, "mce": mce}


def make_aggregate():
    """最小但完整的合法 aggregate.json（view_rows=100，skipped=4）。"""
    base_accuracy = round(40 / 96, 6)
    tuned_accuracy = round(50 / 96, 6)
    return {
        "schema": "pol-final-eval-aggregate-v1",
        "protocol": "finetune/EVAL-PROTOCOL.md#v1",
        "coverage": {
            "view_rows": 100,
            "skipped": {"options_gt_26": 4},
            "skipped_total": 4,
            "expected_evaluated": 96,
            "models": {
                "base": {"evaluated": 96, "missing": 0},
                "tuned": {"evaluated": 96, "missing": 0},
            },
        },
        "models": {
            "base": model(96, 40),
            "tuned": model(96, 50),
        },
        "paired": {
            "base_label": "base",
            "tuned_label": "tuned",
            "rows": 96,
            "base_accuracy": base_accuracy,
            "tuned_accuracy": tuned_accuracy,
            "delta": round(tuned_accuracy - base_accuracy, 6),
            "ci95": [-0.02, 0.24],
            "rounds": 1000,
            "seed": 20261023,
            "method": "paired_item_bootstrap",
        },
        "calibration": {
            "status": "fitted",
            "temperature": 1.234,
            "fit_half": "calibration",
            "fit_rows": 30,
            "fit_method": "grid+golden_section_nll",
            "raw": metric(tuned_accuracy, 1.25, 0.62, 0.11, 0.22),
            "calibrated": metric(tuned_accuracy, 1.05, 0.55, 0.05, 0.12),
            "accuracy_unchanged": True,
        },
    }


def dump(document):
    return json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")


def violation_text(report):
    return "\n".join(report.violations)


def make_bins(counts):
    """按 calibrate.ece_bins 的口径造 15 箱（gap = |avg_confidence - accuracy|）。"""
    assert len(counts) == checker.BIN_COUNT
    bins = []
    for index, count in enumerate(counts):
        if count == 0:
            bins.append({"bin": index, "count": 0, "avg_confidence": 0.0,
                         "accuracy": 0.0, "gap": 0.0})
            continue
        avg_confidence = round((index + 0.5) / checker.BIN_COUNT, 6)
        shift = 0.1 if index % 2 else -0.1
        accuracy = round(min(1.0, max(0.0, avg_confidence + shift)), 6)
        bins.append({
            "bin": index,
            "count": count,
            "avg_confidence": avg_confidence,
            "accuracy": accuracy,
            "gap": round(abs(avg_confidence - accuracy), 6),
        })
    return bins


def make_v2_aggregate():
    """make_aggregate() + spec「增补 v2」D 节的新键（全部自洽，可整体通过）。"""
    document = make_aggregate()
    counts = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 10, 8, 6, 6]
    low = sum(1 for count in counts if count < checker.LOW_SAMPLE_THRESHOLD)
    for block, ece_ci in (
        (document["calibration"]["raw"], [0.05, 0.2]),
        (document["calibration"]["calibrated"], [0.01, 0.1]),
    ):
        block["bins"] = make_bins(counts)
        block["low_sample_bins"] = low
        block["low_sample_flag"] = low > 0
        block["ece_ci95_group"] = ece_ci
        block["ece_rounds"] = 2000
    for label in ("base", "tuned"):
        document["coverage"]["models"][label]["completion_rate"] = 1.0
        document["models"][label]["evaluated_accuracy"] = document["models"][label]["accuracy"]
    document["paired"]["completed_only"] = {
        "rows": 90,
        "base_accuracy": 0.4,
        "tuned_accuracy": 0.5,
        "delta": 0.1,
        "ci95_item": [0.02, 0.19],
        "ci95_group": [-0.01, 0.22],
        "scope": "both_completed",
    }
    delta = document["paired"]["delta"]
    document["paired"]["cluster"] = {
        "cluster_key": "rid_prefix_before_hash",
        "clusters": 40,
        "cluster_size_median": 3,
        "cluster_size_iqr": [1, 6],
        "cluster_size_max": 10,
        "kish_neff": 30.5,
        "delta": delta,
        "ci95": [round(delta - 0.09, 6), round(delta + 0.12, 6)],
        "rounds": 10000,
        "method": "paired_group_cluster_bootstrap",
        "reliability": "cautious",
    }
    return document


class CheckAggregateExportTest(unittest.TestCase):
    def test_double_rounding_delta_bug_regression(self):
        """历史 bug：两个 accuracy 各自 round6 后相减与 delta 差 1e-6 → 必须接受。

        真实数字：base 7859/15573=0.504655、tuned 12124/15573=0.778527，
        delta=round((12124-7859)/15573,6)=0.273871，而 tuned-base=0.273872。
        """
        document = make_aggregate()
        total = 15573
        base_correct, tuned_correct = 7859, 12124
        base_acc = round(base_correct / total, 6)
        tuned_acc = round(tuned_correct / total, 6)
        delta = round((tuned_correct - base_correct) / total, 6)
        self.assertNotEqual(delta, round(tuned_acc - base_acc, 6))
        document["coverage"].update({
            "view_rows": total, "skipped": {}, "skipped_total": 0,
            "expected_evaluated": total,
            "models": {"base": {"evaluated": total, "missing": 0},
                       "tuned": {"evaluated": total, "missing": 0}},
        })
        document["models"]["base"] = model(total, base_correct)
        document["models"]["tuned"] = model(total, tuned_correct)
        document["paired"].update({
            "rows": total, "base_accuracy": base_acc, "tuned_accuracy": tuned_acc,
            "delta": delta, "ci95": [-0.02, 0.42],
        })
        for block in ("raw", "calibrated"):
            document["calibration"][block]["rows"] = total
        report = checker.check_bytes(dump(document))
        self.assertTrue(report.ok, violation_text(report))

    def test_seed_out_of_range_rejected(self):
        document = make_aggregate()
        document["paired"]["seed"] = 2 ** 63
        report = checker.check_bytes(dump(document))
        self.assertFalse(report.ok)
        self.assertIn("seed", violation_text(report))

    def test_rid_like_model_label_rejected(self):
        """模型标签必须是 `[A-Za-z0-9._-]{1,24}`；带 '#' 的长 rid 不得当标签。"""
        document = make_aggregate()
        bad = "db-bigbench-00183cfc#formal"
        document["models"] = {bad: document["models"]["base"],
                              "tuned": document["models"]["tuned"]}
        document["coverage"]["models"] = {bad: document["coverage"]["models"]["base"],
                                         "tuned": document["coverage"]["models"]["tuned"]}
        document["paired"]["base_label"] = bad
        report = checker.check_bytes(dump(document))
        self.assertFalse(report.ok)
        self.assertIn("model label", violation_text(report))

    def test_skipped_rid_disguised_as_reason_rejected(self):
        """把 rid 伪装成 coverage.skipped 的键（34 字符安全标识符）→ 必须判违规。"""
        document = make_aggregate()
        document["coverage"]["skipped"] = {
            "options_gt_26": 3,
            "db-bigbench-00183cfcformal_fallacies": 1,
        }
        document["coverage"]["skipped_total"] = 4
        report = checker.check_bytes(dump(document))
        self.assertFalse(report.ok)
        self.assertIn("unknown skip reason", violation_text(report))

    def setUp(self):
        self.document = make_aggregate()

    def assert_fails(self, document, needle=None):
        report = checker.check_bytes(dump(document))
        self.assertFalse(report.ok, "expected violations")
        if needle is not None:
            self.assertIn(needle, violation_text(report))
        return report

    # ---- 合法样例 ----
    def test_valid_sample_passes(self):
        report = checker.check_bytes(dump(self.document))
        self.assertTrue(report.ok, violation_text(report))
        self.assertGreater(report.checks, 0)
        self.assertEqual(report.size, len(dump(self.document)))

    def test_valid_sample_through_check_document(self):
        report = checker.check_document(copy.deepcopy(self.document))
        self.assertTrue(report.ok, violation_text(report))

    def test_pending_temperature_sample_passes(self):
        self.document["calibration"] = {
            "status": "pending_temperature",
            "temperature": None,
            "fit_half": None,
            "fit_rows": 0,
            "fit_method": None,
            "raw": metric(round(50 / 96, 6), 1.25, 0.62, 0.11, 0.22),
            "calibrated": None,
            "accuracy_unchanged": True,
        }
        report = checker.check_bytes(dump(self.document))
        self.assertTrue(report.ok, violation_text(report))

    def test_custom_model_labels_pass(self):
        document = copy.deepcopy(self.document)
        document["coverage"]["models"] = {
            "track-base": document["coverage"]["models"].pop("base"),
            "track-tuned": document["coverage"]["models"].pop("tuned"),
        }
        document["models"] = {
            "track-base": document["models"].pop("base"),
            "track-tuned": document["models"].pop("tuned"),
        }
        document["paired"]["base_label"] = "track-base"
        document["paired"]["tuned_label"] = "track-tuned"
        report = checker.check_bytes(dump(document))
        self.assertTrue(report.ok, violation_text(report))

    def test_pending_temperature_minimal_passes(self):
        # final_eval_aggregate 在未给温度时只写 status 一个键。
        self.document["calibration"] = {"status": "pending_temperature"}
        report = checker.check_bytes(dump(self.document))
        self.assertTrue(report.ok, violation_text(report))

    def test_paired_label_not_in_models_rejected(self):
        self.document["paired"]["base_label"] = "track-base"
        self.assert_fails(self.document, "not present in $.models")

    def test_coverage_model_labels_mismatch_rejected(self):
        coverage_models = self.document["coverage"]["models"]
        coverage_models["track-tuned"] = coverage_models.pop("tuned")
        self.assert_fails(self.document, "coverage.models labels")

    def test_cli_json_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregate.json"
            path.write_bytes(dump(self.document))
            size = path.stat().st_size
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = checker.main(["--in", str(path), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(set(payload), {"status", "checks", "bytes"})
        self.assertEqual(payload["status"], "pass")
        self.assertGreater(payload["checks"], 0)
        self.assertEqual(payload["bytes"], size)

    # ---- 逐例信息 / 文本 ----
    def test_rid_key_rejected(self):
        self.document["rid"] = "db-test-000001#q"
        report = self.assert_fails(self.document, "forbidden key")
        self.assertIn("rid", violation_text(report))

    def test_nested_per_example_key_rejected(self):
        self.document["models"]["base"]["by_kind"]["choice"]["sample"] = 1
        self.assert_fails(self.document, "forbidden key")

    def test_chinese_string_rejected(self):
        self.document["paired"]["base_label"] = "中文"
        report = self.assert_fails(self.document, "CJK")
        self.assertIn("base_label", violation_text(report))

    def test_overlong_string_rejected(self):
        self.document["paired"]["tuned_label"] = "a" * 65
        self.assert_fails(self.document, "neither an allowed enum value")

    def test_unknown_key_rejected(self):
        self.document["coverage"]["extra"] = 1
        self.assert_fails(self.document, "unknown key")

    def test_missing_layer_key_rejected(self):
        del self.document["models"]["tuned"]["by_lang"]["zh"]
        self.assert_fails(self.document, "missing required key")

    def test_invalid_enum_rejected(self):
        self.document["calibration"]["status"] = "done"
        self.assert_fails(self.document, "unknown status")

    def test_long_printable_run_rejected(self):
        raw = b'{"schema":"' + b"a" * 250 + b'"}'
        report = checker.check_bytes(raw)
        self.assertFalse(report.ok)
        self.assertIn("printable run", violation_text(report))

    def test_unicode_escape_rejected(self):
        raw = b'{"schema":"\\u4e2d"}'
        report = checker.check_bytes(raw)
        self.assertIn("escape sequence", violation_text(report))

    def test_duplicate_key_rejected(self):
        raw = (b'{"schema":"pol-final-eval-aggregate-v1",'
               b'"schema":"pol-final-eval-aggregate-v1"}')
        report = checker.check_bytes(raw)
        self.assertIn("duplicate JSON key", violation_text(report))

    def test_non_finite_number_rejected(self):
        self.document["models"]["base"]["accuracy"] = float("inf")
        raw = dump(self.document)
        self.assertIn(b"Infinity", raw)
        report = checker.check_bytes(raw)
        self.assertFalse(report.ok)

    # ---- 数值自洽 ----
    def test_accuracy_mismatch_rejected(self):
        self.document["models"]["base"]["accuracy"] = 0.5
        self.assert_fails(self.document, "accuracy")

    def test_ci_without_point_estimate_rejected(self):
        self.document["models"]["base"]["accuracy_ci95_wilson"] = [0.9, 1.0]
        self.assert_fails(self.document, "does not contain point estimate")

    def test_reversed_ci_rejected(self):
        self.document["models"]["base"]["accuracy_ci95_wilson"] = [0.5, 0.4]
        self.assert_fails(self.document, "CI lower")

    def test_stratified_total_mismatch_rejected(self):
        self.document["models"]["base"]["by_kind"]["choice"]["total"] = 95
        self.assert_fails(self.document, "stratified totals")

    def test_stratified_correct_mismatch_rejected(self):
        self.document["models"]["base"]["by_lang"]["en"]["correct"] = 24
        self.assert_fails(self.document, "stratified correct")

    def test_model_total_coverage_mismatch_rejected(self):
        self.document["models"]["base"]["total"] = 95
        self.document["models"]["base"]["accuracy"] = round(40 / 95, 6)
        self.document["models"]["base"]["accuracy_ci95_wilson"] = ci(round(40 / 95, 6))
        self.document["models"]["base"]["accuracy_with_missing"] = round(40 / 96, 6)
        self.assert_fails(self.document, "coverage.models evaluated")

    def test_accuracy_with_missing_mismatch_rejected(self):
        self.document["models"]["base"]["accuracy_with_missing"] = 0.9
        self.assert_fails(self.document, "accuracy_with_missing")

    def test_calibration_rows_mismatch_rejected(self):
        self.document["calibration"]["raw"]["rows"] = 95
        self.assert_fails(self.document, "models.tuned.total")

    def test_ece_above_one_rejected(self):
        self.document["calibration"]["raw"]["ece"] = 1.5
        self.assert_fails(self.document, "ece")

    def test_negative_nll_rejected(self):
        self.document["calibration"]["calibrated"]["nll"] = -0.1
        self.assert_fails(self.document, "nll")

    def test_fitted_requires_positive_fit_rows(self):
        self.document["calibration"]["fit_rows"] = 0
        self.assert_fails(self.document, "fit_rows")

    def test_fitted_requires_accuracy_unchanged(self):
        self.document["calibration"]["accuracy_unchanged"] = False
        self.assert_fails(self.document, "accuracy_unchanged")

    def test_pending_temperature_with_fabricated_temperature_rejected(self):
        self.document["calibration"] = {
            "status": "pending_temperature",
            "temperature": 2.0,
            "fit_half": None,
            "fit_rows": 0,
            "fit_method": None,
            "raw": metric(round(50 / 96, 6), 1.25, 0.62, 0.11, 0.22),
            "calibrated": None,
            "accuracy_unchanged": True,
        }
        report = checker.check_bytes(dump(self.document))
        self.assertFalse(report.ok)
        # pending 允许 temperature=null；这里仅要求不静默伪造（不强制拒绝 2.0，但至少要有自洽约束）
        self.assertIn("temperature", violation_text(report).lower())

    def test_paired_delta_mismatch_rejected(self):
        self.document["paired"]["delta"] = 0.5
        self.assert_fails(self.document, "delta")

    def test_paired_rows_exceed_evaluated_rejected(self):
        self.document["paired"]["rows"] = 120
        self.assert_fails(self.document, "min evaluated")

    def test_paired_accuracy_mismatch_rejected(self):
        self.document["paired"]["base_accuracy"] = 0.4
        self.document["paired"]["delta"] = round(0.520833 - 0.4, 6)
        self.assert_fails(self.document, "models.base.accuracy")

    def test_view_rows_inconsistent_with_skipped_rejected(self):
        self.document["coverage"]["view_rows"] = 99
        self.assert_fails(self.document, "view_rows")

    # ---- 体积 ----
    def test_oversized_file_rejected(self):
        raw = dump(self.document)
        report = checker.check_bytes(raw, max_bytes=len(raw) - 1)
        self.assertFalse(report.ok)
        self.assertIn("max_bytes", violation_text(report))

    def test_cli_max_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregate.json"
            path.write_bytes(dump(self.document))
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = checker.main(["--in", str(path), "--max-bytes", "100"])
        self.assertEqual(code, 2)
        self.assertIn("VIOLATION:", buffer.getvalue())

    # ---- CLI 失败形态 ----
    def test_cli_json_failure_shape(self):
        self.document["rid"] = "db-test-000001#q"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregate.json"
            path.write_bytes(dump(self.document))
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = checker.main(["--in", str(path), "--json"])
        self.assertEqual(code, 2)
        lines = [line for line in buffer.getvalue().splitlines() if line.strip()]
        self.assertTrue(any(line.startswith("VIOLATION:") for line in lines))
        payload = json.loads(lines[-1])
        self.assertEqual(set(payload), {"status", "violations"})
        self.assertEqual(payload["status"], "fail")
        self.assertIsInstance(payload["violations"], list)
        self.assertTrue(payload["violations"])

    def test_cli_missing_file_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = checker.main(["--in", str(Path(tmp) / "missing.json")])
        self.assertEqual(code, 2)


class CheckAggregateExportV2Test(unittest.TestCase):
    """spec「增补 v2」D 节：新键放行 + 每个新违规各一例。"""

    def setUp(self):
        self.document = make_v2_aggregate()

    def assert_fails(self, document, needle=None):
        report = checker.check_bytes(dump(document))
        self.assertFalse(report.ok, "expected violations")
        if needle is not None:
            self.assertIn(needle, violation_text(report))
        return report

    def test_ece_ci_without_containing_point_passes(self):
        """ECE 是比值估计：簇 bootstrap 百分位区间不保证包含点估计。

        真实案例（2026-10-27 validation）：ece=0.005765，cluster CI [0.008096, 0.017519]；
        旧检查会误判为违规——这是合法的统计输出，必须接受；区间结构仍需合法。
        """
        block = self.document["calibration"]["raw"]
        block["ece"] = 0.005765
        block["ece_ci95_group"] = [0.008096, 0.017519]
        report = checker.check_bytes(dump(self.document))
        self.assertTrue(report.ok, violation_text(report))
        block["ece_ci95_group"] = [0.3, 0.2]
        self.assert_fails(self.document, "ece_ci95_group")

    # ---- 合法 v2 样例 ----
    def test_v2_sample_passes(self):
        report = checker.check_bytes(dump(self.document))
        self.assertTrue(report.ok, violation_text(report))
        self.assertTrue(checker.check_document(copy.deepcopy(self.document)).ok)

    def test_reliability_boundaries_pass(self):
        cluster = self.document["paired"]["cluster"]
        cluster["clusters"] = 50
        cluster["kish_neff"] = 40.0
        cluster["reliability"] = "ok"
        report = checker.check_bytes(dump(self.document))
        self.assertTrue(report.ok, violation_text(report))
        cluster["clusters"] = 29
        cluster["kish_neff"] = 20.0
        cluster["reliability"] = "low"
        report = checker.check_bytes(dump(self.document))
        self.assertTrue(report.ok, violation_text(report))

    # ---- v2 自洽违规（每个新检查各一例）----
    def test_completion_rate_mismatch_rejected(self):
        self.document["coverage"]["models"]["base"]["completion_rate"] = 0.5
        self.assert_fails(self.document, "completion_rate")

    def test_evaluated_accuracy_mismatch_rejected(self):
        self.document["models"]["base"]["evaluated_accuracy"] = 0.5
        self.assert_fails(self.document, "evaluated_accuracy")

    def test_itt_accuracy_above_completed_accuracy_rejected(self):
        # 4 行缺失：expected_evaluated=100、完成子集 total=96。
        self.document["coverage"]["view_rows"] = 104
        self.document["coverage"]["expected_evaluated"] = 100
        for label in ("base", "tuned"):
            self.document["coverage"]["models"][label] = {
                "evaluated": 96, "missing": 4, "completion_rate": 0.96,
            }
            self.document["models"][label]["missing_rows"] = 4
        self.document["models"]["base"]["accuracy_with_missing"] = round(40 / 100, 6)
        self.document["models"]["tuned"]["accuracy_with_missing"] = round(50 / 100, 6)
        # 合法：ITT(0.4) < 完成子集(0.416667)。
        report = checker.check_bytes(dump(self.document))
        self.assertTrue(report.ok, violation_text(report))
        self.document["models"]["base"]["accuracy_with_missing"] = 0.45
        report = self.assert_fails(self.document, "accuracy_with_missing")
        self.assertIn("> accuracy", violation_text(report))

    def test_cluster_delta_mismatch_rejected(self):
        self.document["paired"]["cluster"]["delta"] = 0.5
        self.assert_fails(self.document, "paired.delta")

    def test_cluster_ci95_without_delta_rejected(self):
        self.document["paired"]["cluster"]["ci95"] = [0.2, 0.3]
        self.assert_fails(self.document, "does not contain point estimate")

    def test_cluster_rounds_below_minimum_rejected(self):
        self.document["paired"]["cluster"]["rounds"] = 999
        self.assert_fails(self.document, "rounds")

    def test_cluster_zero_clusters_rejected(self):
        self.document["paired"]["cluster"]["clusters"] = 0
        self.assert_fails(self.document, "clusters")

    def test_reliability_threshold_mismatch_rejected(self):
        # 40 簇应为 cautious；写成 ok 即违规。
        self.document["paired"]["cluster"]["reliability"] = "ok"
        self.assert_fails(self.document, "reliability")

    def test_cluster_key_value_rejected(self):
        self.document["paired"]["cluster"]["cluster_key"] = "rid_prefix"
        self.assert_fails(self.document, "cluster_key")

    def test_bins_wrong_length_rejected(self):
        raw = self.document["calibration"]["raw"]
        raw["bins"] = raw["bins"][:-1]
        self.assert_fails(self.document, "15 bins")

    def test_bins_duplicate_index_rejected(self):
        self.document["calibration"]["raw"]["bins"][1]["bin"] = 0
        self.assert_fails(self.document, "exactly once")

    def test_bins_unknown_key_rejected(self):
        self.document["calibration"]["raw"]["bins"][0]["extra"] = 1
        self.assert_fails(self.document, "unknown key")

    def test_bins_gap_mismatch_rejected(self):
        self.document["calibration"]["raw"]["bins"][1]["gap"] = 0.5
        self.assert_fails(self.document, "gap")

    def test_low_sample_bins_mismatch_rejected(self):
        self.document["calibration"]["calibrated"]["low_sample_bins"] = 3
        self.assert_fails(self.document, "low_sample_bins")

    def test_low_sample_flag_mismatch_rejected(self):
        self.document["calibration"]["calibrated"]["low_sample_flag"] = False
        self.assert_fails(self.document, "low_sample_flag")

    def test_completed_only_rows_exceed_paired_rejected(self):
        self.document["paired"]["completed_only"]["rows"] = 120
        self.assert_fails(self.document, "> paired.rows")

    def test_completed_only_ci95_group_without_delta_rejected(self):
        self.document["paired"]["completed_only"]["ci95_group"] = [0.2, 0.3]
        self.assert_fails(self.document, "ci95_group")

    def test_completed_only_ci95_item_without_delta_rejected(self):
        self.document["paired"]["completed_only"]["ci95_item"] = [0.2, 0.3]
        self.assert_fails(self.document, "ci95_item")

    def test_cluster_size_iqr_wrong_shape_rejected(self):
        self.document["paired"]["cluster"]["cluster_size_iqr"] = [1, 2, 3]
        self.assert_fails(self.document, "cluster_size_iqr")


if __name__ == "__main__":
    unittest.main()
