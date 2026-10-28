"""benchmark/kev_prefix/aggregate.py 的单元测试（纯合成样例）。"""
import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "aggregate.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agg = load_module("kev_prefix_aggregate", MODULE_PATH)


def row(record_id, question, keys, label, p, variant="clean", parent=None, line=0):
    return {"id": record_id, "group": record_id, "question": question, "source": "holdout",
            "task": "choice", "type": "choice", "variant": variant, "keys": list(keys), "label": label,
            "control_id": None, "pair_id": None, "sibling": None, "parent": parent or record_id,
            "p": list(p), "raw_probability_sum": sum(p), "zero_count": 0,
            "logits": [math.log(x) for x in p], "inference_temperature": 1.0}


JOIN = {
    "holdout/0": {"id": "holdout/0", "variant": "clean", "item_id": "db-secret-0001", "domain": "knowledge_reasoning",
                  "lang": "en", "group_id": "holdout/0", "parent_id": None, "state_chars": 300,
                  "questions": [{"qid": "q0", "rid": "db-secret-0001#weather", "kind": "choice", "num_options": 3, "overlong": False}]},
    "holdout/1": {"id": "holdout/1", "variant": "clean", "item_id": "db-secret-0002", "domain": "decision_mechanics",
                  "lang": "en", "group_id": "fam-A", "parent_id": None, "state_chars": 900,
                  "questions": [{"qid": "q0", "rid": "db-secret-0002#claim", "kind": "choice", "num_options": 3, "overlong": False},
                                {"qid": "q1", "rid": "db-secret-0002#extra", "kind": "choice", "num_options": 3, "overlong": True}]},
    "holdout/1/q0/permuted": {"id": "holdout/1/q0/permuted", "variant": "permuted", "item_id": "db-secret-0002",
                              "domain": "decision_mechanics", "lang": "en", "group_id": "fam-A",
                              "parent_id": "holdout/1", "state_chars": 900,
                              "questions": [{"qid": "q0", "rid": "db-secret-0002#claim", "kind": "choice", "num_options": 3, "overlong": False}]},
}


def rows_for(record_probs):
    rows = []
    for record_id, questions in record_probs.items():
        for question, (keys, label, p) in questions.items():
            rows.append(row(record_id, question, keys, label, p))
    return rows


RUN_A = rows_for({
    "holdout/0": {"q0": (["opt_1", "opt_2", "opt_3"], 1, [0.2, 0.7, 0.1])},
    "holdout/1": {"q0": (["opt_1", "opt_2", "opt_3"], 0, [0.6, 0.3, 0.1]),
                  "q1": (["opt_1", "opt_2", "opt_3"], 2, [0.1, 0.2, 0.7])},
})
RUN_B = rows_for({
    "holdout/0": {"q0": (["opt_1", "opt_2", "opt_3"], 1, [0.4, 0.3, 0.3])},
    "holdout/1": {"q0": (["opt_1", "opt_2", "opt_3"], 0, [0.5, 0.3, 0.2]),
                  "q1": (["opt_1", "opt_2", "opt_3"], 2, [0.2, 0.3, 0.5])},
})


class MetricPrimitiveTest(unittest.TestCase):
    def test_softmax_normalised(self):
        p = agg.softmax([1.0, 1.0, 1.0])
        self.assertAlmostEqual(sum(p), 1.0)
        self.assertAlmostEqual(p[0], 1 / 3)

    def test_ece_zero_when_perfectly_calibrated(self):
        self.assertAlmostEqual(agg.ece([0.5, 0.5, 0.5, 0.5], [True, False, True, False], 10), 0.0, places=9)

    def test_coverage_at_error(self):
        # 第一组 (0.9, 正确) 错误率 0；第二组 (0.8, 错误) 累计 1/2 = 0.5 <= 0.5 -> 全覆盖
        self.assertAlmostEqual(agg.coverage_at_error([0.9, 0.8], [True, False], 0.5), 1.0)

    def test_option_and_state_buckets(self):
        self.assertEqual(agg.option_bucket(2), "2")
        self.assertEqual(agg.option_bucket(4), "3-4")
        self.assertEqual(agg.option_bucket(41), ">26")
        self.assertEqual(agg.state_bucket(300), "<=400")
        self.assertEqual(agg.state_bucket(5000), ">3000")

    def test_metrics_values(self):
        rows = [row("r", "q", ["a", "b"], 1, [0.25, 0.75])]
        m = agg.metrics(rows)
        self.assertEqual(m["n"], 1)
        self.assertAlmostEqual(m["acc"], 1.0)
        self.assertAlmostEqual(m["brier"], 0.125)
        self.assertAlmostEqual(m["nll"], -math.log(0.75))


class SingleModelCiTest(unittest.TestCase):
    def test_ci_structure_and_determinism(self):
        enriched, _ = agg.attach(RUN_A, JOIN)
        first = agg.single_model_ci(enriched, samples=50, seed=1, nonlinear_samples=20)
        second = agg.single_model_ci(enriched, samples=50, seed=1, nonlinear_samples=20)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        for metric in ("acc", "brier", "nll", "ece_10", "ece_15", "coverage_at_5pct_error"):
            self.assertIn(metric, first)
            self.assertIn("ci95", first[metric])
            self.assertLessEqual(first[metric]["ci95"][0], first[metric]["ci95"][1])

    def test_coverage_detail(self):
        detail = agg.coverage_at_error_detail([0.9, 0.8], [True, False], 0.05)
        self.assertEqual(detail["accepted_n"], 1)  # 接受第一组后错误率 0<=5%*1，第二组 1/2=50%>5% 不接受
        self.assertAlmostEqual(detail["coverage"], 0.5)
        self.assertAlmostEqual(detail["accepted_error_rate"], 0.0)


class AttachTest(unittest.TestCase):
    def test_attach_filters_overlong_and_unknown(self):
        rows = list(RUN_A)
        rows.append(row("holdout/999", "q0", ["opt_1", "opt_2"], 0, [0.5, 0.5]))
        enriched, dropped = agg.attach(rows, JOIN)
        self.assertEqual(len(enriched), 2)  # q0 x2，q1 overlong 被排除
        self.assertEqual(dropped["overlong"], 1)
        self.assertEqual(dropped["unknown_record"], 1)
        self.assertEqual([r["kind"] for r in enriched], ["choice", "choice"])

    def test_attach_subset(self):
        enriched, _ = agg.attach(RUN_A, JOIN, only_rids={"db-secret-0001#weather"})
        self.assertEqual(len(enriched), 1)


class PairedBootstrapTest(unittest.TestCase):
    def test_deterministic_and_signed(self):
        enriched_a, _ = agg.attach(RUN_A, JOIN)
        enriched_b, _ = agg.attach(RUN_B, JOIN)
        first = agg.paired_bootstrap(enriched_a, enriched_b, samples=200, seed=7)
        second = agg.paired_bootstrap(enriched_a, enriched_b, samples=200, seed=7)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(first["n_pairs"], 2)
        self.assertGreater(first["deltas"]["acc"]["delta"], 0)  # A 更准
        self.assertFalse(first["deltas"]["brier"]["ci95"][0] is None)

    def test_raw_t1_differs_when_temperature_not_one(self):
        enriched, _ = agg.attach(RUN_A, JOIN)
        warmed = [dict(row, inference_temperature=2.0) for row in enriched]
        served = agg.metrics(warmed)
        raw = agg.metrics(warmed, raw=True)
        self.assertAlmostEqual(served["n"], raw["n"])
        self.assertGreater(raw["mean_conf"], served["mean_conf"])  # T=2 时 served 更平缓，raw 更尖锐
        self.assertEqual(served["acc"], raw["acc"])  # 单调变换不改变 argmax


class VariantTest(unittest.TestCase):
    def test_permuted_flip_detected(self):
        clean = row("holdout/0", "q0", ["opt_1", "opt_2"], 1, [0.3, 0.7])
        variant = row("holdout/0/q0/permuted", "q0", ["opt_2", "opt_1"], 1, [0.7, 0.3],
                      variant="permuted", parent="holdout/0")
        stats = agg.variant_stats([clean, variant], "permuted")
        self.assertEqual(stats["n_pairs"], 1)
        self.assertEqual(stats["flip_rate"], 0.0)  # 概率随选项移动，argmax 不变
        self.assertAlmostEqual(stats["mean_max_delta"], 0.0)
        self.assertIn("ci95", stats)

    def test_permuted_order_change_measured_by_key(self):
        clean = row("holdout/0", "q0", ["opt_1", "opt_2"], 1, [0.3, 0.7])
        variant = row("holdout/0/q0/permuted", "q0", ["opt_2", "opt_1"], 1, [0.6, 0.4],
                      variant="permuted", parent="holdout/0")
        stats = agg.variant_stats([clean, variant], "permuted")
        self.assertAlmostEqual(stats["mean_max_delta"], 0.1, places=9)
        self.assertEqual(stats["accuracy_unchanged_rate"], 1.0)


class ExportCheckTest(unittest.TestCase):
    def test_rejects_leaked_id(self):
        with self.assertRaises(ValueError):
            agg.export_check({"bad": "db-secret-0001#weather"}, JOIN)

    def test_accepts_aggregate(self):
        enriched, _ = agg.attach(RUN_A, JOIN)
        output = {"runs": {"a": agg.metrics(enriched)}, "groups": 2}
        self.assertTrue(agg.export_check(output, JOIN))


class CliTest(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            join_path = tmp / "join.jsonl"
            join_path.write_text("".join(json.dumps(v) + "\n" for v in JOIN.values()), encoding="utf-8")
            out = tmp / "aggregate.json"
            runs = []
            for name, rows in (("kev", RUN_A), ("seed43", RUN_B)):
                directory = tmp / name
                directory.mkdir()
                (directory / "rows.json").write_text(json.dumps(rows), encoding="utf-8")
                (directory / "report.json").write_text(json.dumps({"latency_ms": {"median": 1.0, "p95": 2.0},
                                                                   "coverage": {"requested_records": 2}}), encoding="utf-8")
                runs += ["--run", f"{name}={directory}"]
            code = agg.main(["--join", str(join_path), "--out", str(out), "--reference", "kev",
                             "--bootstrap-samples", "100"] + runs)
            self.assertEqual(code, 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "kev-prefix-aggregate/1")
            self.assertEqual(report["runs"]["kev"]["served"]["overall"]["n"], 2)
            self.assertIn("seed43 vs kev", report["paired"])
            text = out.read_text(encoding="utf-8")
            self.assertNotIn("db-secret-0001", text)
            self.assertNotIn("#weather", text)
            self.assertNotIn("fam-A", text)


if __name__ == "__main__":
    unittest.main()