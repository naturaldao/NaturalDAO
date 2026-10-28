"""build_training_view.py 的离线不变量测试（合成 fixture，不读真实大文件）。

覆盖简报全部测试要求：
- classification hard label（choice/score 下标）、noul；
- distillation soft 对齐与归一；
- drop / no_route / answer_not_in_options / degenerate_soft / answer_out_of_range 跳过计数；
- 渲染模板含选项 A/B/...；
- 选项数超过 26 时的双射字母进位 (A..Z, AA..)；
- 两次 build 输出逐字节一致（确定性）；
- benchmark / holdout 路径护栏 exit 2；
- rid 冲突或非法选项时报错。
"""
from __future__ import annotations

import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "datasets" / "general" / "build_training_view.py"


def write_gz(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_item(
    item_id: str,
    kind: str,
    options,
    answer=None,
    probs=None,
    *,
    prompt="应该选哪个？",
    lang="zh",
    key="q",
    state="情境文本",
):
    question = {"key": key, "kind": kind, "origin": "source", "prompt": prompt}
    if kind in ("choice", "noul"):
        question["options"] = options
    else:
        question["scale"] = options
    target = {}
    if answer is not None:
        target["answer"] = answer
    if probs is not None:
        target["probs"] = probs
    return {
        "id": item_id,
        "domain": "decision_mechanics",
        "lang": lang,
        "state": state,
        "questions": [question],
        "targets": {key: target},
        "source": {"slug": "fixture"},
        "meta": {"native_source": "fixture-source"},
    }


class BuildViewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.items = self.dir / "train.jsonl.gz"
        self.routes = self.dir / "target-types.jsonl.gz"
        self.out = self.dir / "out" / "view.jsonl"

    def run_build(self, *extra, items=None, routes=None, out=None, split="train"):
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--split",
            split,
            "--items",
            str(items or self.items),
            "--target-types",
            str(routes or self.routes),
            "--out",
            str(out or self.out),
            *extra,
        ]
        return subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def read_rows(self, out=None):
        out_path = out or self.out
        with out_path.open(encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_classification_and_noul(self):
        items = [
            # choice: answer 匹配 option key
            make_item("db-a", "choice", [{"key": "left", "label": "左边"}, {"key": "right", "label": "右边"}], "right"),
            # score: answer_idx = answer - scale.min
            make_item("db-b", "score", {"min": 1, "max": 4}, 3),
            # noul: answer 匹配 option label 或 key
            make_item("db-c", "noul", [{"key": "no", "label": "否"}, {"key": "yes", "label": "是"}], "yes"),
        ]
        write_gz(self.items, items)
        routes = [
            {"item_id": "db-a", "question_key": "q", "training_route": "classification"},
            {"item_id": "db-b", "question_key": "q", "training_route": "classification"},
            {"item_id": "db-c", "question_key": "q", "training_route": "classification"},
        ]
        write_gz(self.routes, routes)

        res = self.run_build()
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = {r["rid"]: r for r in self.read_rows()}

        # choice 断言
        self.assertEqual(rows["db-a#q"]["kind"], "choice")
        self.assertEqual(rows["db-a#q"]["options"], ["left", "right"])
        self.assertEqual(rows["db-a#q"]["option_labels"], ["左边", "右边"])
        self.assertEqual(rows["db-a#q"]["answer_idx"], 1)
        self.assertIsNone(rows["db-a#q"]["soft"])
        self.assertEqual(rows["db-a#q"]["route"], "classification")

        # score 断言
        self.assertEqual(rows["db-b#q"]["kind"], "score")
        self.assertEqual(rows["db-b#q"]["options"], ["1", "2", "3", "4"])
        self.assertEqual(rows["db-b#q"]["scale"], {"min": 1, "max": 4})
        self.assertEqual(rows["db-b#q"]["answer_idx"], 2)  # 3 - 1 = 2

        # noul 断言
        self.assertEqual(rows["db-c#q"]["kind"], "noul")
        self.assertEqual(rows["db-c#q"]["answer_idx"], 1)

    def test_distillation_soft_alignment_and_normalization(self):
        # probs 缺少一个 key（k3），应补 0 并归一
        items = [
            make_item(
                "db-distill-1",
                "choice",
                [{"key": "k1", "label": "L1"}, {"key": "k2", "label": "L2"}, {"key": "k3", "label": "L3"}],
                probs={"k1": 1.0, "k2": 3.0},  # sum = 4.0 -> [0.25, 0.75, 0.0]
            ),
        ]
        write_gz(self.items, items)
        routes = [
            {
                "item_id": "db-distill-1",
                "question_key": "q",
                "training_route": "distillation",
                "semantics_confidence": "high",
            },
        ]
        write_gz(self.routes, routes)

        res = self.run_build()
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = self.read_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["route"], "distillation")
        self.assertEqual(row["answer_idx"], 1)  # argmax 是 k2 (下标 1)
        self.assertAlmostEqual(row["soft"][0], 0.25)
        self.assertAlmostEqual(row["soft"][1], 0.75)
        self.assertAlmostEqual(row["soft"][2], 0.0)
        self.assertEqual(row["soft_conf"], "high")

    def test_skip_counts_and_fallbacks(self):
        items = [
            # 1. drop 路由
            make_item("db-drop", "choice", [{"key": "x", "label": "X"}, {"key": "y", "label": "Y"}], "x"),
            # 2. no_route: target-types 无记录且 target 为空
            make_item("db-noroute", "choice", [{"key": "x", "label": "X"}, {"key": "y", "label": "Y"}], answer=None),
            # 3. answer_not_in_options: 选项内不存在答案
            make_item("db-bad-ans", "choice", [{"key": "x", "label": "X"}, {"key": "y", "label": "Y"}], "z"),
            # 4. answer_out_of_range: score 越界
            make_item("db-bad-score", "score", {"min": 0, "max": 3}, 99),
            # 5. degenerate_soft: 软分布全等值（退化无信息）
            make_item(
                "db-degen",
                "choice",
                [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}],
                probs={"a": 0.5, "b": 0.5},
            ),
            # 正常保留条目，保证 build_view 不会因为全空而报错
            make_item("db-ok", "choice", [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}], "a"),
        ]
        write_gz(self.items, items)

        routes = [
            {"item_id": "db-drop", "question_key": "q", "training_route": "drop"},
            {"item_id": "db-bad-ans", "question_key": "q", "training_route": "classification"},
            {"item_id": "db-bad-score", "question_key": "q", "training_route": "classification"},
            {"item_id": "db-degen", "question_key": "q", "training_route": "distillation"},
            {"item_id": "db-ok", "question_key": "q", "training_route": "classification"},
        ]
        write_gz(self.routes, routes)

        res = self.run_build()
        self.assertEqual(res.returncode, 0, res.stderr)

        manifest = json.loads(self.out.with_suffix(".jsonl.manifest.json").read_text(encoding="utf-8"))
        skipped = manifest["skipped"]
        self.assertEqual(skipped.get("drop"), 1)
        self.assertEqual(skipped.get("no_route"), 1)
        self.assertEqual(skipped.get("answer_not_in_options"), 1)
        self.assertEqual(skipped.get("answer_out_of_range"), 1)
        self.assertEqual(skipped.get("degenerate_soft"), 1)
        self.assertEqual(manifest["rows"], 1)

    def test_prompt_rendering_and_bijective_letters(self):
        # 验证选项进位：27 个选项生成 A..Z, AA
        opts = [{"key": f"o{i}", "label": f"选项{i}"} for i in range(27)]
        items = [make_item("db-27", "choice", opts, "o26", state="这是测试情境", prompt="请选择最佳方案")]
        write_gz(self.items, items)
        routes = [{"item_id": "db-27", "question_key": "q", "training_route": "classification"}]
        write_gz(self.routes, routes)

        res = self.run_build()
        self.assertEqual(res.returncode, 0, res.stderr)
        row = self.read_rows()[0]
        prompt = row["prompt"]

        self.assertIn("你是只做封闭选择的决策模型", prompt)
        self.assertIn("【情境】\n这是测试情境", prompt)
        self.assertIn("【问题】\n请选择最佳方案", prompt)
        self.assertIn("A. 选项0", prompt)
        self.assertIn("Z. 选项25", prompt)
        self.assertIn("AA. 选项26", prompt)
        self.assertEqual(row["answer_idx"], 26)

    def test_deterministic(self):
        items = [
            make_item("db-2", "choice", [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}], "a"),
            make_item("db-1", "choice", [{"key": "x", "label": "X"}, {"key": "y", "label": "Y"}], "y"),
        ]
        write_gz(self.items, items)
        routes = [
            {"item_id": "db-1", "question_key": "q", "training_route": "classification"},
            {"item_id": "db-2", "question_key": "q", "training_route": "classification"},
        ]
        write_gz(self.routes, routes)

        first = self.run_build("--json")
        self.assertEqual(first.returncode, 0, first.stderr)
        sha1 = json.loads(first.stdout)["out_sha256"]

        out2 = self.dir / "out" / "view2.jsonl"
        second = self.run_build("--json", out=out2)
        self.assertEqual(second.returncode, 0, second.stderr)
        sha2 = json.loads(second.stdout)["out_sha256"]

        self.assertEqual(sha1, sha2)
        # 确认按 item_id 排序输出
        rows = self.read_rows()
        self.assertEqual(rows[0]["rid"], "db-1#q")
        self.assertEqual(rows[1]["rid"], "db-2#q")

    def test_benchmark_guard_exit_2(self):
        # 路径含 benchmark
        bad_items = self.dir / "benchmark.jsonl.gz"
        write_gz(bad_items, [make_item("db-x", "choice", [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}], "a")])
        res = self.run_build(items=bad_items)
        self.assertEqual(res.returncode, 2)
        self.assertIn("refusing", res.stderr)

        # 路径含 holdout
        bad_holdout = self.dir / "holdout-train.jsonl.gz"
        write_gz(bad_holdout, [make_item("db-y", "choice", [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}], "a")])
        res = self.run_build(items=bad_holdout)
        self.assertEqual(res.returncode, 2)
        self.assertIn("refusing", res.stderr)

        # split 指定 benchmark
        res = self.run_build(split="benchmark")
        self.assertEqual(res.returncode, 2)

    def test_rid_conflict_and_invalid_options(self):
        # 重复 rid
        bad_items = [
            make_item("db-dup", "choice", [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}], "a", key="q1"),
            make_item("db-dup", "choice", [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}], "a", key="q1"),
        ]
        write_gz(self.items, bad_items)
        routes = [{"item_id": "db-dup", "question_key": "q1", "training_route": "classification"}]
        write_gz(self.routes, routes)
        res = self.run_build()
        self.assertEqual(res.returncode, 2)
        self.assertIn("duplicate rid", res.stderr)

        # choice 选项数非法 (<2)
        bad_items = [make_item("db-few", "choice", [{"key": "a", "label": "A"}], "a")]
        write_gz(self.items, bad_items)
        routes = [{"item_id": "db-few", "question_key": "q", "training_route": "classification"}]
        write_gz(self.routes, routes)
        res = self.run_build()
        self.assertEqual(res.returncode, 2)
        self.assertIn("needs >=2 options", res.stderr)

        # score scale max < min
        bad_items = [make_item("db-bad-scale", "score", {"min": 5, "max": 2}, 3)]
        write_gz(self.items, bad_items)
        routes = [{"item_id": "db-bad-scale", "question_key": "q", "training_route": "classification"}]
        write_gz(self.routes, routes)
        res = self.run_build()
        self.assertEqual(res.returncode, 2)
        self.assertIn("scale max < min", res.stderr)

    def test_strict_route_flag(self):
        # 带有 answer 但无旁挂行：默认走 fallback，--strict-route 下进入 skipped.no_route
        items = [
            make_item("db-uncovered", "choice", [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}], "a"),
            make_item("db-ok", "choice", [{"key": "a", "label": "A"}, {"key": "b", "label": "B"}], "a"),
        ]
        write_gz(self.items, items)
        routes = [{"item_id": "db-ok", "question_key": "q", "training_route": "classification"}]
        write_gz(self.routes, routes)

        # 默认模式：兜底成功，共 2 行
        res_default = self.run_build()
        self.assertEqual(res_default.returncode, 0)
        self.assertEqual(len(self.read_rows()), 2)

        # strict 模式：db-uncovered 计入 no_route，仅保留 1 行
        res_strict = self.run_build("--strict-route")
        self.assertEqual(res_strict.returncode, 0)
        self.assertEqual(len(self.read_rows()), 1)
        manifest = json.loads(self.out.with_suffix(".jsonl.manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["skipped"]["no_route"], 1)


if __name__ == "__main__":
    unittest.main()
