"""collect_results.py 的纯 CPU 单元测试（无第三方依赖）。"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from finetune import collect_results


def make_eval_dict(accuracy, kind_accuracy, total=100):
    return {
        "total": total,
        "correct": int(accuracy * total),
        "accuracy": accuracy,
        "by_kind": {name: {"total": 10, "correct": int(value * 10), "accuracy": value}
                    for name, value in kind_accuracy.items()},
        "by_lang": {"en": {"total": 80, "correct": int(accuracy * 80), "accuracy": accuracy},
                    "zh": {"total": 20, "correct": int(accuracy * 20), "accuracy": accuracy}},
        "by_option_bucket": {"2": {"total": 50, "correct": int(accuracy * 50), "accuracy": accuracy},
                             "5-8": {"total": 50, "correct": int(accuracy * 50), "accuracy": accuracy}},
        "by_route": {"classification": {"total": 100, "correct": int(accuracy * 100), "accuracy": accuracy}},
        "skipped_stats": {"options_gt_26": 0},
    }


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class CollectResultsTest(unittest.TestCase):
    def test_eval_table_with_delta(self):
        base = make_eval_dict(0.50, {"choice": 0.5, "noul": 0.4, "score": 0.3})
        tuned = make_eval_dict(0.80, {"choice": 0.8, "noul": 0.85, "score": 0.7})
        table = collect_results.render_eval_table([("base", base), ("tuned", tuned)])
        self.assertIn("base（n=100）", table)
        self.assertIn("0.8000", table)
        self.assertIn("差值（tuned − base）", table)
        self.assertIn("+0.3000", table)

    def test_lm_eval_table(self):
        base = {"results": {
            "ceval-valid": {"acc,none": 0.50, "acc_stderr,none": 0.01},
            "mmlu": {"acc,none": 0.40},
            "agieval": {"acc_norm,none": 0.30},
        }}
        tuned = {"results": {
            "ceval-valid": {"acc,none": 0.48},
            "mmlu": {"acc,none": 0.42},
            "agieval": {"acc_norm,none": 0.31},
        }}
        table = collect_results.render_lm_eval_table(
            [("base", base), ("tuned", tuned)],
            average_tasks=["ceval-valid", "mmlu", "agieval"])
        self.assertIn("ceval-valid", table)
        self.assertIn("__average__", table)
        self.assertIn("差值（tuned − base）", table)

    def _preds(self, correct_every, count=400):
        return {f"db-{index:05d}#q": (index % correct_every == 0) for index in range(count)}

    def test_paired_bootstrap(self):
        base = {f"db-{index:05d}#q": (index % 5 == 0) for index in range(400)}   # 20%
        tuned = {f"db-{index:05d}#q": (index % 2 == 0) for index in range(400)}  # 50%
        stats = collect_results.paired_bootstrap(base, tuned, rounds=300, seed=7)
        self.assertEqual(stats["rows"], 400)
        self.assertAlmostEqual(stats["base_accuracy"], 0.2, places=3)
        self.assertAlmostEqual(stats["tuned_accuracy"], 0.5, places=3)
        self.assertAlmostEqual(stats["delta"], 0.3, places=3)
        self.assertGreater(stats["ci95"][0], 0)
        again = collect_results.paired_bootstrap(base, tuned, rounds=300, seed=7)
        self.assertEqual(stats["ci95"], again["ci95"])

    def test_paired_bootstrap_rejects_tiny_overlap(self):
        base = {f"x-{index}": True for index in range(5)}
        tuned = {f"x-{index}": False for index in range(5)}
        with self.assertRaises(ValueError):
            collect_results.paired_bootstrap(base, tuned, rounds=10)

    def test_cli_writes_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            write_json(tmp_path / "base.json", make_eval_dict(0.5, {"choice": 0.5, "noul": 0.5, "score": 0.5}))
            write_json(tmp_path / "tuned.json", make_eval_dict(0.8, {"choice": 0.8, "noul": 0.8, "score": 0.8}))
            with (tmp_path / "base-preds.jsonl").open("w", encoding="utf-8") as fh:
                for index in range(100):
                    fh.write(json.dumps({"rid": f"x-{index}", "correct": index % 5 == 0}) + "\n")
            with (tmp_path / "tuned-preds.jsonl").open("w", encoding="utf-8") as fh:
                for index in range(100):
                    fh.write(json.dumps({"rid": f"x-{index}", "correct": index % 2 == 0}) + "\n")
            out = tmp_path / "summary.md"
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = collect_results.main([
                    "--eval-json", f"base={tmp_path / 'base.json'}",
                    "--eval-json", f"tuned={tmp_path / 'tuned.json'}",
                    "--preds", f"base={tmp_path / 'base-preds.jsonl'}",
                    "--preds", f"tuned={tmp_path / 'tuned-preds.jsonl'}",
                    "--out", str(out),
                ])
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8")
            self.assertIn("# 评测汇总", text)
            self.assertIn("配对 bootstrap", text)
            self.assertIn("差值", text)


    def test_resolve_lm_eval_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "lm-eval-base"
            model_dir = root / "__home__model"
            model_dir.mkdir(parents=True)
            older = model_dir / "results_2026-01-01T00-00-00.json"
            newer = model_dir / "results_2026-01-02T00-00-00.json"
            write_json(older, {"results": {"erased": {"acc,none": 0.1}}})
            write_json(newer, {"results": {"erased": {"acc,none": 0.9}}})
            # 显式设置 mtime，避免文件系统时间精度影响
            import os
            os.utime(older, (1_700_000_000, 1_700_000_000))
            os.utime(newer, (1_700_000_100, 1_700_000_100))
            resolved = collect_results.resolve_lm_eval_json(root)
            self.assertEqual(resolved, newer)
            self.assertEqual(collect_results.load_json(resolved)["results"]["erased"]["acc,none"], 0.9)

    def test_lm_eval_table_from_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "lm-eval"
            (root / "model").mkdir(parents=True)
            write_json(root / "model" / "results_2026-01-01T00-00-00.json",
                       {"results": {"ceval-valid": {"acc,none": 0.5}}})
            base = collect_results.load_json(collect_results.resolve_lm_eval_json(root))
            table = collect_results.render_lm_eval_table([("base", base)])
            self.assertIn("ceval-valid", table)
            self.assertIn("0.5000", table)

    def test_bad_assignment_returns_2(self):
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            code = collect_results.main(["--eval-json", "no-equals-sign"])
        self.assertEqual(code, 2)
        self.assertIn("LABEL=PATH", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
