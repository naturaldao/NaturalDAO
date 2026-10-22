"""校准脚本的纯 CPU 单元测试（标准库，不依赖 torch）。"""
from __future__ import annotations

import io
import json
import math
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from finetune import calibrate


def softmax(scores):
    peak = max(scores.values())
    exps = {letter: math.exp(score - peak) for letter, score in scores.items()}
    total = sum(exps.values())
    return {letter: value / total for letter, value in exps.items()}


def make_rows(count=1500, stated_power=1.0, seed=7):
    """生成合成预测：标签从真实分布 q 采样；stated probs ∝ q**stated_power。

    stated_power>1 表示模型过度自信（比真实分布更尖锐），此时最优温度应约等于 stated_power。
    """
    rng = random.Random(seed)
    letters = ["A", "B", "C", "D"]
    rows = []
    for index in range(count):
        scores = {letter: rng.gauss(0, 1.5) for letter in letters}
        q = softmax(scores)
        stated = softmax({letter: math.log(max(q[letter], 1e-9)) * stated_power for letter in letters})
        threshold = rng.random()
        cumulative = 0.0
        gold = letters[-1]
        for letter in letters:
            cumulative += q[letter]
            if threshold <= cumulative:
                gold = letter
                break
        rows.append({
            "rid": f"db-test-{index:06d}#q",
            "gold_letter": gold,
            "candidate_probs": {letter: round(stated[letter], 8) for letter in letters},
        })
    return rows


class CalibrateTest(unittest.TestCase):
    def test_rid_half_is_deterministic_and_partitions(self):
        rids = [f"db-x-{index}#q" for index in range(200)]
        first = {rid: calibrate.rid_half(rid) for rid in rids}
        second = {rid: calibrate.rid_half(rid) for rid in rids}
        self.assertEqual(first, second)
        calibration = [rid for rid in rids if first[rid] == "calibration"]
        selection = [rid for rid in rids if first[rid] == "selection"]
        self.assertEqual(len(calibration) + len(selection), len(rids))
        self.assertTrue(set(calibration).isdisjoint(selection))

    def test_fit_prefers_lower_nll_than_temperature_one(self):
        # stated_power=2.5 表示过度自信；最优 T 应约为 2.5
        rows = make_rows(stated_power=2.5)
        fit = calibrate.fit_temperature(rows)
        nll_at_fit, _ = calibrate.temperature_nll(rows, fit["temperature"])
        nll_at_one, _ = calibrate.temperature_nll(rows, 1.0)
        self.assertLess(nll_at_fit, nll_at_one)
        self.assertGreater(fit["temperature"], 1.5)
        self.assertLess(fit["temperature"], 4.0)

    def test_accuracy_invariant_under_temperature(self):
        rows = make_rows(stated_power=3.0)
        base = calibrate.evaluate(rows, 1.0)
        for temperature in (0.5, 2.0, 4.0):
            scaled = calibrate.evaluate(rows, temperature)
            self.assertEqual(base["accuracy"], scaled["accuracy"])
            self.assertEqual(base["rows"], scaled["rows"])

    def test_overconfidence_is_reduced(self):
        rows = make_rows(stated_power=3.0)
        raw = calibrate.evaluate(rows, 1.0)
        fit = calibrate.fit_temperature(rows)
        calibrated = calibrate.evaluate(rows, fit["temperature"])
        self.assertLess(calibrated["ece"], raw["ece"])
        self.assertLess(calibrated["nll"], raw["nll"])

    def test_missing_fields_are_skipped(self):
        rows = make_rows(count=20)
        rows.append({"rid": "bad-1", "gold_letter": "A"})
        rows.append({"rid": "bad-2", "candidate_probs": {"A": 1.0, "B": 0.0}})
        result = calibrate.evaluate(rows, 1.0)
        self.assertEqual(result["rows"], 20)
        self.assertEqual(result["skipped"], 2)

    def test_cli_fit_and_apply(self):
        rows = make_rows(count=400, stated_power=1.6)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "preds.jsonl"
            with path.open("w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = calibrate.main(["fit", "--predictions", str(path), "--json"])
            self.assertEqual(code, 0)
            fit = json.loads(buffer.getvalue())
            self.assertIn("temperature", fit)
            self.assertGreater(fit["temperature"], 0)

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = calibrate.main(["apply", "--predictions", str(path),
                                       "--temperature", str(fit["temperature"]),
                                       "--half", "selection", "--json"])
            self.assertEqual(code, 0)
            report = json.loads(buffer.getvalue())
            self.assertEqual(report["half"], "selection")
            self.assertIn("ece", report)

    def test_half_filter_covers_all_rows(self):
        rows = make_rows(count=50)
        calibration = calibrate.filter_half(rows, "calibration")
        selection = calibrate.filter_half(rows, "selection")
        self.assertEqual(len(calibration) + len(selection), len(rows))
        self.assertEqual(calibrate.filter_half(rows, "all"), rows)


if __name__ == "__main__":
    unittest.main()
