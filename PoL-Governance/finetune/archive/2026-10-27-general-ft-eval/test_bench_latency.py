r"""延迟基准的纯 CPU 单元测试（不依赖 torch / 网络 / 私有数据）。

本文件在**没有 torch** 的普通 Windows Python 下也必须通过，因此：

- 只测纯逻辑（percentile_nearest_rank / plan_batches / summarize_phase / 视图读取 / 报告组装）；
- 真实模型路径用假后端替换 `_load_backend`，绝不实例化 torch 模型；
- 所有 fixture 都是临时目录里的合成视图行（无 rid 泄漏、无真实数据、无私有保留集）。
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from finetune import bench_latency
from finetune.decision_common import format_prompt_and_answer

# 报告里绝不允许出现的逐例字段（`items` 是契约里的计数，不在禁列）
BANNED_KEYS = {
    "rid", "prompt", "text", "content", "gold", "gold_letter", "pred", "pred_letter",
    "prediction", "row", "sample", "case", "item", "ids", "candidates", "logits", "probs",
}


def iter_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from iter_keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_keys(value)


def make_row(index, prompt=None, options=None, answer_idx=0):
    return {
        "rid": f"syn-{index:04d}",
        "prompt": prompt if prompt is not None else f"合成题目 {index}",
        "options": list(options) if options is not None else ["甲", "乙", "丙"],
        "answer_idx": answer_idx,
        "kind": "choice",
        "lang": "zh",
        "route": "classification",
    }


def write_jsonl(path, rows, trailing_bad_line=False):
    with Path(path).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        if trailing_bad_line:
            handle.write("{not json}\n")


class FakeClock:
    """每次调用前进固定步长：一个计时 batch 恰好 2 次调用 → 墙钟 = step。"""

    def __init__(self, step=0.05):
        self.step = step
        self.now = 0.0

    def __call__(self):
        self.now += self.step
        return self.now


class FakeBackend:
    """不接触 torch 的假后端；token 数按条数线性给，便于核对 tokens/s。"""

    def __init__(self, device_type="cpu", device_name="synthetic-cpu",
                 peak_mem_mb=12.5, tokens_per_item=3):
        self.device_type = device_type
        self.device_name = device_name
        self._peak_mem_mb = peak_mem_mb
        self.tokens_per_item = tokens_per_item
        self.infer_calls = []
        self.reset_calls = 0
        self.closed = False

    def infer(self, prompts):
        self.infer_calls.append(list(prompts))
        return len(prompts) * self.tokens_per_item

    def reset_peak_memory(self):
        self.reset_calls += 1

    def peak_memory_mb(self):
        return self._peak_mem_mb

    def close(self):
        self.closed = True


class BenchLatencyLogicTest(unittest.TestCase):
    def test_module_import_is_lazy(self):
        # 结构检查：模块命名空间里没有 torch 绑定（顶层 import 会留下该名字）
        self.assertFalse(hasattr(bench_latency, "torch"))
        # 进程级检查：单独导入本模块不会把 torch 拉进 sys.modules。
        # 用子进程而不是断言本进程的 sys.modules，避免受同一进程里其他测试的导入顺序影响
        # （装了 torch 的评测环境里，别的测试可能已经 import 过 torch）。
        repo_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys, finetune.bench_latency; print(int('torch' in sys.modules))"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "0", result.stderr)

    def test_percentile_nearest_rank_nearest_rank_semantics(self):
        values = [10.0, 20.0, 30.0, 40.0]
        self.assertEqual(bench_latency.percentile_nearest_rank(values, 50.0), 20.0)
        self.assertEqual(bench_latency.percentile_nearest_rank(values, 95.0), 40.0)
        self.assertEqual(bench_latency.percentile_nearest_rank(values, 100.0), 40.0)
        self.assertEqual(bench_latency.percentile_nearest_rank(values, 0.0), 10.0)
        self.assertEqual(bench_latency.percentile_nearest_rank([7.5], 95.0), 7.5)
        # 乱序输入不应影响结果
        self.assertEqual(bench_latency.percentile_nearest_rank([40.0, 10.0, 30.0, 20.0], 50.0), 20.0)

    def test_percentile_nearest_rank_nearest_rank_rank_boundaries(self):
        # n=3, p95 → rank=ceil(2.85)=3；p50 → rank=2（下中位数）
        self.assertEqual(bench_latency.percentile_nearest_rank([1.0, 2.0, 3.0], 95.0), 3.0)
        self.assertEqual(bench_latency.percentile_nearest_rank([1.0, 2.0, 3.0], 50.0), 2.0)
        # n=20, p95 → rank=19
        self.assertEqual(bench_latency.percentile_nearest_rank([float(i) for i in range(1, 21)], 95.0), 19.0)

    def test_percentile_nearest_rank_empty_and_invalid(self):
        self.assertIsNone(bench_latency.percentile_nearest_rank([], 95.0))
        with self.assertRaises(ValueError):
            bench_latency.percentile_nearest_rank([1.0], -1.0)
        with self.assertRaises(ValueError):
            bench_latency.percentile_nearest_rank([1.0], 100.1)
        with self.assertRaises(ValueError):
            bench_latency.percentile_nearest_rank([1.0, float("nan")], 50.0)
        with self.assertRaises(ValueError):
            bench_latency.percentile_nearest_rank([float("inf")], 50.0)

    def test_plan_batches_shapes(self):
        self.assertEqual(bench_latency.plan_batches(5, 2), [2, 2, 1])
        self.assertEqual(bench_latency.plan_batches(4, 2), [2, 2])
        self.assertEqual(bench_latency.plan_batches(1, 16), [1])
        self.assertEqual(bench_latency.plan_batches(16, 16), [16])
        self.assertEqual(bench_latency.plan_batches(0, 3), [])
        for items in range(0, 25):
            plan = bench_latency.plan_batches(items, 4)
            self.assertEqual(sum(plan), items)
            self.assertTrue(all(0 < count <= 4 for count in plan))

    def test_plan_batches_rejects_invalid(self):
        with self.assertRaises(ValueError):
            bench_latency.plan_batches(5, 0)
        with self.assertRaises(ValueError):
            bench_latency.plan_batches(5, -2)
        with self.assertRaises(ValueError):
            bench_latency.plan_batches(-1, 2)

    def test_summarize_phase_keys_values_and_order(self):
        phase = bench_latency.summarize_phase(
            [10.0, 20.0, 30.0, 40.0],
            batch_size=1, items=4, batches=4, warmup_batches=2,
            total_tokens=400, total_seconds=0.4, peak_mem_mb=None,
        )
        self.assertEqual(list(phase), ["batch_size", "items", "batches", "warmup_batches",
                                       "p50_ms", "p95_ms", "mean_ms", "tokens_per_sec",
                                       "peak_mem_mb"])
        self.assertEqual(phase["batch_size"], 1)
        self.assertEqual(phase["items"], 4)
        self.assertEqual(phase["batches"], 4)
        self.assertEqual(phase["warmup_batches"], 2)
        self.assertEqual(phase["p50_ms"], 20.0)
        self.assertEqual(phase["p95_ms"], 40.0)
        self.assertEqual(phase["mean_ms"], 25.0)
        self.assertEqual(phase["tokens_per_sec"], 1000.0)
        self.assertIsNone(phase["peak_mem_mb"])

    def test_summarize_phase_rounds_and_reports_peak(self):
        phase = bench_latency.summarize_phase(
            [1.23456, 2.0],
            batch_size=2, items=2, batches=1, warmup_batches=0,
            total_tokens=10, total_seconds=0.003, peak_mem_mb=123.456789,
        )
        self.assertEqual(phase["p50_ms"], 1.235)
        self.assertEqual(phase["p95_ms"], 2.0)
        self.assertEqual(phase["mean_ms"], 1.617)
        self.assertEqual(phase["tokens_per_sec"], 3333.333)
        self.assertEqual(phase["peak_mem_mb"], 123.457)

    def test_summarize_phase_empty_latencies(self):
        phase = bench_latency.summarize_phase(
            [], batch_size=1, items=0, batches=0, warmup_batches=0,
            total_tokens=0, total_seconds=0.0, peak_mem_mb=None,
        )
        self.assertIsNone(phase["p50_ms"])
        self.assertIsNone(phase["p95_ms"])
        self.assertIsNone(phase["mean_ms"])
        self.assertEqual(phase["tokens_per_sec"], 0.0)

    def test_summarize_phase_rejects_invalid_inputs(self):
        kwargs = dict(batch_size=1, items=1, batches=1, warmup_batches=0,
                      total_tokens=1, total_seconds=1.0, peak_mem_mb=None)
        with self.assertRaises(ValueError):
            bench_latency.summarize_phase([1.0], **{**kwargs, "batch_size": 0})
        with self.assertRaises(ValueError):
            bench_latency.summarize_phase([1.0], **{**kwargs, "total_tokens": -1})
        with self.assertRaises(ValueError):
            bench_latency.summarize_phase([1.0], **{**kwargs, "total_seconds": float("inf")})
        with self.assertRaises(ValueError):
            bench_latency.summarize_phase([1.0], **{**kwargs, "total_seconds": -0.1})
        with self.assertRaises(ValueError):
            bench_latency.summarize_phase([1.0], **{**kwargs, "peak_mem_mb": float("nan")})

    def test_parse_batch_sizes(self):
        self.assertEqual(bench_latency.parse_batch_sizes("1,16"), [1, 16])
        self.assertEqual(bench_latency.parse_batch_sizes("16, 1, 16"), [16, 1])
        self.assertEqual(bench_latency.parse_batch_sizes(" 2 , 4 "), [2, 4])
        for bad in ("", "   ", "1,x", "0", "-3", "1,"):
            with self.assertRaises(ValueError):
                bench_latency.parse_batch_sizes(bad)

    def test_describe_hardware_sanitizes(self):
        label = bench_latency.describe_hardware("cuda", "NVIDIA GeForce RTX 4090")
        self.assertNotIn(" ", label)
        self.assertIn("NVIDIA-GeForce-RTX-4090", label)
        self.assertTrue(label.startswith(bench_latency.describe_hardware("cpu")))
        self.assertTrue(label.isascii())
        self.assertGreater(len(bench_latency.describe_hardware("cpu")), 0)
        self.assertEqual(bench_latency.describe_hardware("cpu", "   "), bench_latency.describe_hardware("cpu"))

    def test_read_maxrss_kb_returns_optional_int(self):
        value = bench_latency.read_maxrss_kb()
        self.assertTrue(value is None or (isinstance(value, int) and value >= 0))


class BenchLatencyViewTest(unittest.TestCase):
    def test_read_view_reuses_decision_common_and_counts_skips(self):
        rows = [
            make_row(0),
            make_row(1),
            make_row(2),
            make_row(3, options=[f"选项{i}" for i in range(27)]),  # options_gt_26
            make_row(4, prompt="长" * 40),  # prompt_too_long（max_prompt_chars=20）
            {"rid": "syn-bad-1", "prompt": "缺选项"},  # missing_options
            {"rid": "syn-bad-2", "options": ["a", "b"], "answer_idx": 5, "prompt": "越界"},  # invalid_answer_idx
        ]
        with tempfile.TemporaryDirectory() as tmp:
            view = Path(tmp) / "view.jsonl"
            write_jsonl(view, rows)
            prompts, skipped, other = bench_latency.read_eval_view_prompts(
                view, limit=0, max_prompt_chars=20,
            )
        self.assertEqual(len(prompts), 3)
        self.assertEqual(skipped, {"options_gt_26": 1, "prompt_too_long": 1})
        self.assertEqual(other, {"missing_options": 1, "invalid_answer_idx": 1})
        expected, letter, reason = format_prompt_and_answer(rows[0])
        self.assertIsNone(reason)
        self.assertEqual(letter, "A")
        self.assertEqual(prompts[0], expected)
        self.assertTrue(prompts[0].endswith("【答案】\n"))

    def test_read_view_limit_stops_before_bad_line(self):
        rows = [make_row(0), make_row(1)]
        with tempfile.TemporaryDirectory() as tmp:
            view = Path(tmp) / "view.jsonl"
            write_jsonl(view, rows, trailing_bad_line=True)
            prompts, skipped, other = bench_latency.read_eval_view_prompts(view, limit=2)
            self.assertEqual(len(prompts), 2)
            self.assertEqual(skipped, {"options_gt_26": 0, "prompt_too_long": 0})
            self.assertEqual(other, {})
            with self.assertRaises(ValueError):
                bench_latency.read_eval_view_prompts(view, limit=0)

    def test_read_view_rejects_invalid_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            view = Path(tmp) / "view.jsonl"
            write_jsonl(view, [make_row(0)])
            with self.assertRaises(ValueError):
                bench_latency.read_eval_view_prompts(view, limit=-1)
            with self.assertRaises(ValueError):
                bench_latency.read_eval_view_prompts(view, max_prompt_chars=-1)
            with self.assertRaises(OSError):
                bench_latency.read_eval_view_prompts(Path(tmp) / "missing.jsonl")


class BenchLatencyPhasesTest(unittest.TestCase):
    def test_bench_phases_runs_warmup_untimed_then_all_items(self):
        prompts = ["p0", "p1", "p2", "p3", "p4"]
        backend = FakeBackend(peak_mem_mb=12.5)
        phases = bench_latency.bench_phases(
            backend, prompts, [2, 3], warmup=1, clock=FakeClock(step=0.05),
        )
        self.assertEqual([phase["batch_size"] for phase in phases], [2, 3])

        first, second = phases
        self.assertEqual(first["items"], 5)
        self.assertEqual(first["batches"], 3)  # [2, 2, 1]
        self.assertEqual(first["warmup_batches"], 1)
        self.assertAlmostEqual(first["p50_ms"], 25.0, places=3)
        self.assertAlmostEqual(first["p95_ms"], 50.0, places=3)
        self.assertAlmostEqual(first["mean_ms"], 33.333, places=3)
        self.assertAlmostEqual(first["tokens_per_sec"], 100.0, places=3)
        self.assertEqual(first["peak_mem_mb"], 12.5)

        self.assertEqual(second["batches"], 2)  # [3, 2]
        self.assertEqual(second["warmup_batches"], 1)
        self.assertAlmostEqual(second["p50_ms"], 16.667, places=3)
        self.assertAlmostEqual(second["p95_ms"], 25.0, places=3)
        self.assertAlmostEqual(second["mean_ms"], 20.833, places=3)
        self.assertAlmostEqual(second["tokens_per_sec"], 150.0, places=3)

        # 每个 batch size 各自 reset 一次峰值统计
        self.assertEqual(backend.reset_calls, 2)
        # 计时 batch 覆盖全部 items：warmup(1+1) + timed(3+2) = 7 次前向
        self.assertEqual(len(backend.infer_calls), 7)
        timed = backend.infer_calls[1:4]
        self.assertEqual([len(chunk) for chunk in timed], [2, 2, 1])
        self.assertEqual([prompt for chunk in timed for prompt in chunk], prompts)
        self.assertEqual([len(chunk) for chunk in backend.infer_calls[5:]], [3, 2])

    def test_bench_phases_caps_warmup_at_plan_length(self):
        backend = FakeBackend()
        phases = bench_latency.bench_phases(
            backend, ["p0", "p1", "p2", "p3", "p4"], [10], warmup=2, clock=FakeClock(step=0.01),
        )
        self.assertEqual(len(phases), 1)
        self.assertEqual(phases[0]["batches"], 1)
        self.assertEqual(phases[0]["warmup_batches"], 1)
        self.assertEqual(len(backend.infer_calls), 2)

    def test_bench_phases_rejects_empty_prompts_and_bad_warmup(self):
        with self.assertRaises(ValueError):
            bench_latency.bench_phases(FakeBackend(), [], [1], warmup=1)
        with self.assertRaises(ValueError):
            bench_latency.bench_phases(FakeBackend(), ["p0"], [1], warmup=-1)


class BenchLatencyReportTest(unittest.TestCase):
    def test_build_report_matches_schema_and_has_no_per_example_keys(self):
        phase = bench_latency.summarize_phase(
            [1.0], batch_size=1, items=1, batches=1, warmup_batches=0,
            total_tokens=3, total_seconds=0.1, peak_mem_mb=None,
        )
        report = bench_latency.build_report(
            hardware="Windows-11-AMD64", device="cpu", model="/models/synthetic",
            adapter=None, limit=0, max_prompt_chars=4000,
            phases=[phase], skipped={"options_gt_26": 2},
        )
        self.assertEqual(list(report), ["schema", "hardware", "device", "model", "adapter",
                                        "limit", "max_prompt_chars", "phases", "skipped"])
        self.assertEqual(report["schema"], "pol-latency-bench-v1")
        self.assertEqual(report["skipped"], {"options_gt_26": 2, "prompt_too_long": 0})
        self.assertIsNone(report["adapter"])
        self.assertEqual(set(iter_keys(report)) & BANNED_KEYS, set())

    def test_cli_writes_latency_json_with_fake_backend(self):
        rows = [make_row(index, prompt=f"合成题目第{index}条") for index in range(5)]
        backend = FakeBackend()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            view = tmp_path / "view.jsonl"
            write_jsonl(view, rows)
            out = tmp_path / "latency.json"
            with mock.patch.object(bench_latency, "_load_backend", return_value=backend):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    code = bench_latency.main([
                        "--model", "/models/synthetic", "--eval-view", str(view),
                        "--limit", "5", "--batch-sizes", "2,10", "--warmup", "1",
                        "--max-prompt-chars", "4000", "--device", "cpu", "--json",
                        "--out", str(out),
                    ])
            self.assertEqual(code, 0)
            text = out.read_text(encoding="utf-8")
            self.assertTrue(text.endswith("\n"))
            report = json.loads(text)
            printed = json.loads(buffer.getvalue())
            self.assertEqual(report, printed)
            self.assertEqual(report["schema"], "pol-latency-bench-v1")
            self.assertEqual(report["device"], "cpu")
            self.assertEqual(report["model"], "/models/synthetic")
            self.assertEqual(report["limit"], 5)
            self.assertEqual(report["max_prompt_chars"], 4000)
            self.assertEqual([phase["batch_size"] for phase in report["phases"]], [2, 10])
            self.assertEqual(report["phases"][0]["batches"], 3)  # [2, 2, 1]
            self.assertEqual(report["phases"][1]["batches"], 1)  # [5]
            self.assertEqual(report["phases"][1]["warmup_batches"], 1)
            self.assertEqual(report["skipped"], {"options_gt_26": 0, "prompt_too_long": 0})
            self.assertEqual(set(iter_keys(report)) & BANNED_KEYS, set())
            self.assertNotIn("合成题目", text)
            self.assertNotIn("rid", text)
            self.assertTrue(backend.closed)

    def test_cli_human_output_lists_phases(self):
        rows = [make_row(index) for index in range(3)]
        backend = FakeBackend()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            view = tmp_path / "view.jsonl"
            write_jsonl(view, rows)
            out = tmp_path / "latency.json"
            with mock.patch.object(bench_latency, "_load_backend", return_value=backend):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    code = bench_latency.main([
                        "--model", "/models/synthetic", "--eval-view", str(view),
                        "--limit", "3", "--batch-sizes", "1", "--warmup", "0",
                        "--out", str(out),
                    ])
            self.assertEqual(code, 0)
            output = buffer.getvalue()
            self.assertIn("pol-latency-bench-v1", output)
            self.assertIn("batch=   1", output)
            self.assertIn("written:", output)
            self.assertTrue(out.exists())

    def test_cli_missing_runtime_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            view = tmp_path / "view.jsonl"
            write_jsonl(view, [make_row(0)])
            out = tmp_path / "latency.json"
            error = io.StringIO()
            with mock.patch.object(bench_latency, "_load_backend",
                                   side_effect=RuntimeError("当前环境未安装 torch")), \
                    redirect_stderr(error):
                code = bench_latency.main([
                    "--model", "/models/synthetic", "--eval-view", str(view),
                    "--limit", "1", "--out", str(out),
                ])
            self.assertEqual(code, 2)
            self.assertIn("torch", error.getvalue())
            self.assertFalse(out.exists())

    def test_cli_missing_view_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "latency.json"
            error = io.StringIO()
            with redirect_stderr(error):
                code = bench_latency.main([
                    "--model", "/models/synthetic", "--eval-view", str(tmp_path / "nope.jsonl"),
                    "--out", str(out),
                ])
            self.assertEqual(code, 2)
            self.assertFalse(out.exists())

    def test_cli_all_rows_skipped_exits_2_without_loading_model(self):
        rows = [make_row(0, options=[f"选项{i}" for i in range(27)])]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            view = tmp_path / "view.jsonl"
            write_jsonl(view, rows)
            out = tmp_path / "latency.json"
            loader = mock.Mock(side_effect=AssertionError("不应加载模型"))
            error = io.StringIO()
            with mock.patch.object(bench_latency, "_load_backend", loader), redirect_stderr(error):
                code = bench_latency.main([
                    "--model", "/models/synthetic", "--eval-view", str(view),
                    "--out", str(out),
                ])
            self.assertEqual(code, 2)
            self.assertIn("没有可用样本", error.getvalue())
            self.assertFalse(loader.called)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
