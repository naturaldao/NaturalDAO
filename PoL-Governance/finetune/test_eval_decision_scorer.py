#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track B 独立评测脚本的纯 CPU 单元测试 (finetune/test_eval_decision_scorer.py)

覆盖（全部离线、纯 CPU，不下载/加载任何真实模型权重或真实数据）：
1. build_batches：按 token 长度升序组批、覆盖全部下标、batch_size 边界、等长稳定排序，
   以及组批后 collate 的 padding/mask 正确性；
2. score_batch：题内 masked softmax / argmax、无效选项位（-1e4）概率为 0 且不会被选中、
   不同选项数（trim 到真实选项数）与手算 softmax 一致；
3. build_prediction_row：--predictions 行字段、gold/pred 字母映射、candidate_probs 为
   {字母: 概率} 且和为 1（6 位小数误差 < 1e-4）；
4. aggregate_metrics：total/correct/accuracy 与 by_kind/by_lang/by_option_bucket/by_route
   分层、skipped_stats 透传、duration_seconds/samples_per_second 等键名与
   eval_decision.py 同口径；
5. EvalScorerDataset + build_skipped_stats：options_gt_26 / prompt_too_long / 各
   ScorerDataset 跳过原因 / other / unparseable 计数与 total_read 恒等式
   （合成 JSONL，包含超长 prompt、>26 选项、坏 JSON、空选项段）；
6. compute_marker_scores：省显存前向（last hidden -> gather 选项位 -> pointer_head）与
   DecisionScorer.forward 在小模型 + 随机 LoRA/head 权重下数值一致；resolve_transformer
   对 PeftModel(generic/CAUSAL_LM)、AutoModel、AutoModelForCausalLM、普通模块的识别；
   无法识别时回退 DecisionScorer.forward 的数值一致；
7. dump_predictions：JSONL 写出/读回字段与概率归一（LF 换行）；
8. CLI 参数错误 exit 2：缺必填参数、未知参数、视图缺失、adapter 目录缺失、head 缺失、
   predictions 路径落在仓库内。

缺 torch/transformers/peft 时整组 skip（与 finetune/test_decision_scorer.py 相同写法）。
"""

from __future__ import annotations

import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

# 确保在任何工作目录下均能导入 finetune 包
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 公开仓库的 check.py 在未安装模型依赖的环境里也要能通过：缺依赖时跳过整组测试（同 Track A/B）。
_MISSING = [name for name in ("torch", "transformers", "peft")
            if importlib.util.find_spec(name) is None]
if _MISSING:
    raise unittest.SkipTest("Track B eval tests need training deps: missing " + ", ".join(_MISSING))

import torch

from finetune.decision_common import SimpleStubTokenizer, get_repo_root
from finetune.decision_scorer import (
    MASKED_LOGIT_FILL,
    OPTIONS_SECTION_HEADER,
    TRACK_B_TEMPLATE_VERSION,
    DecisionScorer,
    build_scorer_sample,
    collate_scorer_batch,
)
import finetune.eval_decision_scorer as eval_decision_scorer
from finetune.train_decision_scorer import ScorerDataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModel, AutoModelForCausalLM, LlamaConfig


# ---------------------------------------------------------------------------
# 测试辅助
# ---------------------------------------------------------------------------

INSTRUCTION = "You are a closed-choice decision model."


class EmptyOpStubTokenizer(SimpleStubTokenizer):
    """把 "OP: "（空选项标签的 marker 行）编码为空，用于触发 empty_option_segment。"""

    def encode(self, text, add_special_tokens=False):
        if text == "OP: ":
            return []
        return super().encode(text, add_special_tokens=add_special_tokens)


def make_row(
    rid="syn_item#01",
    labels=("alpha", "beta", "gamma"),
    answer_idx=1,
    route="classification",
    soft=None,
    kind="choice",
    lang="en",
    prompt=None,
):
    """构造一行 tv-1 训练视图（含字母选项段；Track B 会丢弃并重建 marker 选项段）。"""
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    option_lines = "\n".join(
        f"{letters[i % len(letters)]}. {label}" for i, label in enumerate(labels)
    )
    if prompt is None:
        prompt = (
            INSTRUCTION + "\n\n"
            + "【情境】\nA situation text.\n\n【问题】\nWhich option is best?\n\n"
            + OPTIONS_SECTION_HEADER + "\n" + option_lines
        )
    return {
        "rid": rid,
        "src": "general-v5",
        "split": "validation",
        "lang": lang,
        "domain": "test",
        "kind": kind,
        "prompt": prompt,
        "options": [f"opt{i}" for i in range(len(labels))],
        "option_labels": list(labels),
        "answer_idx": answer_idx,
        "soft": soft,
        "soft_conf": None,
        "scale": None,
        "route": route,
        "source_slug": "test",
        "template_version": "tv-1",
    }


def tiny_llama_config(vocab_size=128):
    """tiny LlamaConfig：hidden 32 / 2 层 / 2 头 / intermediate 64 / vocab 128。"""
    return LlamaConfig(
        vocab_size=vocab_size,
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=2,
        num_key_value_heads=2,
    )


def write_jsonl(path: Path, rows, malformed_lines=()) -> Path:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        for line in malformed_lines:
            fh.write(line + "\n")
    return path


# ---------------------------------------------------------------------------
# 1. 长度排序分批 / collate padding
# ---------------------------------------------------------------------------

class TestBuildBatches(unittest.TestCase):

    @staticmethod
    def _samples(lengths):
        return [{"input_ids": list(range(length))} for length in lengths]

    def test_sorted_ascending_and_batch_sizes(self):
        """按 token 长度升序切批：覆盖全部下标、每批不超过 batch_size、各批内有序。"""
        samples = self._samples([10, 3, 7, 2, 5])
        batches = eval_decision_scorer.build_batches(samples, 2)

        flat = [index for batch in batches for index in batch]
        self.assertEqual(sorted(flat), list(range(len(samples))))  # 每个下标恰好一次
        lengths = [len(samples[i]["input_ids"]) for i in flat]
        self.assertEqual(lengths, sorted(lengths))                 # 全局升序
        self.assertEqual([len(batch) for batch in batches], [2, 2, 1])
        for batch in batches:
            self.assertLessEqual(len(batch), 2)
            self.assertEqual(len(set(batch)), len(batch))

    def test_batch_size_larger_than_samples(self):
        samples = self._samples([4, 1, 9])
        batches = eval_decision_scorer.build_batches(samples, 16)
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0], [1, 0, 2])  # 按长度 1,4,9 排序

    def test_equal_lengths_keep_original_order(self):
        """等长样本稳定排序：结果可复现，顺序等于原始下标顺序。"""
        samples = self._samples([5, 5, 5, 5, 5])
        batches = eval_decision_scorer.build_batches(samples, 2)
        self.assertEqual([i for batch in batches for i in batch], [0, 1, 2, 3, 4])

    def test_invalid_batch_size_raises(self):
        with self.assertRaises(ValueError):
            eval_decision_scorer.build_batches(self._samples([1]), 0)
        with self.assertRaises(ValueError):
            eval_decision_scorer.build_batches(self._samples([1]), -3)

    def test_batches_feed_collate_padding(self):
        """组批 + collate 后形状/attention/padding/marker 正确（短行右侧补 pad）。"""
        tok = SimpleStubTokenizer()
        rows = [
            make_row(rid="r1", labels=("aa", "bb", "cc", "dd"), answer_idx=2),
            make_row(rid="r2", labels=("x", "y"), answer_idx=0, lang="zh", kind="noul",
                     prompt="【情境】\nQQQ\n\n【问题】\nP?\n\n" + OPTIONS_SECTION_HEADER + "\nA. x\nB. y"),
            make_row(rid="r3", labels=("m",), answer_idx=0),
        ]
        samples = []
        for row in rows:
            sample, reason = build_scorer_sample(row, tok, seq_len=512)
            self.assertIsNone(reason)
            samples.append(sample)

        batches = eval_decision_scorer.build_batches(samples, 2)
        total = 0
        for indices in batches:
            sub = [samples[i] for i in indices]
            batch = collate_scorer_batch(sub, pad_token_id=tok.pad_token_id)
            max_len = max(len(s["input_ids"]) for s in sub)
            max_opts = max(s["option_count"] for s in sub)
            self.assertEqual(batch["input_ids"].shape, (len(sub), max_len))
            self.assertEqual(batch["marker_positions"].shape, (len(sub), max_opts))
            for row, sample in enumerate(sub):
                n = len(sample["input_ids"])
                self.assertTrue(bool((batch["attention_mask"][row, :n] == 1).all()))
                if n < max_len:
                    self.assertTrue(bool((batch["attention_mask"][row, n:] == 0).all()))
                    self.assertTrue(bool((batch["input_ids"][row, n:] == tok.pad_token_id).all()))
                opts = sample["option_count"]
                if opts < max_opts:
                    self.assertTrue(bool((batch["marker_positions"][row, opts:] == -1).all()))
                    self.assertTrue(bool((batch["option_mask"][row, opts:] == False).all()))
            total += len(sub)
        self.assertEqual(total, len(samples))


# ---------------------------------------------------------------------------
# 2. score_batch：masked softmax / argmax / 无效位
# ---------------------------------------------------------------------------

class TestScoreBatch(unittest.TestCase):

    def test_masked_softmax_matches_manual_and_argmax(self):
        scores = torch.tensor([[1.0, 2.0, MASKED_LOGIT_FILL],
                               [5.0, 7.0, MASKED_LOGIT_FILL]])
        mask = torch.tensor([[True, True, False],
                             [True, True, False]])
        results = eval_decision_scorer.score_batch(scores, mask, [2, 2])

        for result, values in zip(results, ([1.0, 2.0], [5.0, 7.0])):
            probs = result["probs"]
            self.assertEqual(len(probs), 2)                   # trim 到真实选项数
            denom = sum(math.exp(v) for v in values)
            for index, value in enumerate(values):
                self.assertAlmostEqual(probs[index], math.exp(value) / denom, places=6)
            self.assertAlmostEqual(sum(probs), 1.0, places=6)

        # 行 0 有效位 argmax=1（2.0），行 1 有效位 argmax=1（7.0）
        self.assertEqual([r["pred_idx"] for r in results], [1, 1])

    def test_invalid_positions_never_selected_and_zero_prob(self):
        """无效（padding）位填 -1e4：概率严格为 0，argmax 不会选中它。"""
        scores = torch.tensor([[3.0, 1.0, MASKED_LOGIT_FILL],
                               [MASKED_LOGIT_FILL, 2.0, 4.0]])
        mask = torch.tensor([[True, True, False],
                             [False, True, True]])
        # 第二行在前缀假设下不应出现（collate 总是选项在前、padding 在后）；
        # 这里直接验证 masked_softmax 对任意 mask 的行为，再由 score_batch 的 trim 规则检查前缀。
        probs = eval_decision_scorer.masked_softmax(scores, mask)
        self.assertEqual(probs[0, 2].item(), 0.0)
        self.assertEqual(probs[1, 0].item(), 0.0)
        self.assertAlmostEqual(float(probs[0, :2].sum()), 1.0, places=6)
        self.assertAlmostEqual(float(probs[1, 1:].sum()), 1.0, places=6)
        # 前缀 mask（真实使用场景）：无效位于末尾
        prefix_mask = torch.tensor([[True, True, False], [True, True, False]])
        prefix_scores = torch.tensor([[3.0, 1.0, MASKED_LOGIT_FILL],
                                      [2.0, 4.0, MASKED_LOGIT_FILL]])
        results = eval_decision_scorer.score_batch(prefix_scores, prefix_mask, [2, 2])
        self.assertEqual([r["pred_idx"] for r in results], [0, 1])
        for result in results:
            self.assertNotEqual(result["pred_idx"], 2)

    def test_different_option_counts(self):
        """不同选项数的行：probs 长度等于该题真实选项数；单选项行概率为 1。"""
        scores = torch.tensor([[1.0, 2.0, 3.0],
                               [9.0, MASKED_LOGIT_FILL, MASKED_LOGIT_FILL]])
        mask = torch.tensor([[True, True, True],
                             [True, False, False]])
        results = eval_decision_scorer.score_batch(scores, mask, [3, 1])
        self.assertEqual(len(results[0]["probs"]), 3)
        self.assertEqual(len(results[1]["probs"]), 1)
        self.assertAlmostEqual(sum(results[0]["probs"]), 1.0, places=6)
        self.assertEqual(results[1]["probs"], [1.0])
        self.assertEqual(results[1]["pred_idx"], 0)
        self.assertEqual(results[0]["pred_idx"], 2)

    def test_masked_fill_constant_aligns_with_training(self):
        self.assertEqual(MASKED_LOGIT_FILL, -1e4)


# ---------------------------------------------------------------------------
# 3. 逐行预测记录（供 calibrate.py）
# ---------------------------------------------------------------------------

class TestPredictionRow(unittest.TestCase):

    def test_fields_and_probability_sum(self):
        meta = {"rid": "r#1", "kind": "choice", "lang": "zh", "num_options": 3,
                "answer_idx": 1, "route": "distillation"}
        row = eval_decision_scorer.build_prediction_row(meta, [0.2, 0.5, 0.3], 1)

        for key in ("rid", "kind", "lang", "num_options", "gold_letter",
                    "candidate_probs", "correct", "route"):
            self.assertIn(key, row)
        self.assertEqual(row["rid"], "r#1")
        self.assertEqual(row["kind"], "choice")
        self.assertEqual(row["lang"], "zh")
        self.assertEqual(row["num_options"], 3)
        self.assertEqual(row["gold_letter"], "B")
        self.assertEqual(row["pred_letter"], "B")
        self.assertTrue(row["correct"])
        self.assertEqual(row["route"], "distillation")
        self.assertEqual(row["candidate_probs"], {"A": 0.2, "B": 0.5, "C": 0.3})
        self.assertAlmostEqual(sum(row["candidate_probs"].values()), 1.0, places=9)

    def test_wrong_prediction_flagged(self):
        meta = {"rid": "r#2", "kind": "noul", "lang": "en", "num_options": 2,
                "answer_idx": 1, "route": "classification"}
        row = eval_decision_scorer.build_prediction_row(meta, [0.7, 0.3], 0)
        self.assertFalse(row["correct"])
        self.assertEqual(row["gold_letter"], "B")
        self.assertEqual(row["pred_letter"], "A")

    def test_rounding_error_stays_below_tolerance(self):
        """candidate_probs 保留 6 位小数：归一化误差 < 1e-4（calibrate.py 可接受）。"""
        probs = [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0]
        meta = {"rid": "r#3", "kind": "choice", "lang": "en", "num_options": 3,
                "answer_idx": 0, "route": "classification"}
        row = eval_decision_scorer.build_prediction_row(meta, probs, 0)
        self.assertLess(abs(sum(row["candidate_probs"].values()) - 1.0), 1e-4)
        # 26 选项均匀分布：最差累计误差仍 < 1e-4
        n = 26
        meta26 = {"rid": "r#4", "kind": "choice", "lang": "en", "num_options": n,
                  "answer_idx": n - 1, "route": "classification"}
        row26 = eval_decision_scorer.build_prediction_row(meta26, [1.0 / n] * n, n - 1)
        self.assertLess(abs(sum(row26["candidate_probs"].values()) - 1.0), 1e-4)
        self.assertEqual(sorted(row26["candidate_probs"]), [chr(ord("A") + i) for i in range(n)])
        self.assertEqual(row26["gold_letter"], "Z")
        self.assertTrue(row26["correct"])


# ---------------------------------------------------------------------------
# 4. 汇总指标聚合（与 eval_decision.py 同口径）
# ---------------------------------------------------------------------------

class TestAggregateMetrics(unittest.TestCase):

    def _records(self):
        return [
            {"rid": "a", "kind": "choice", "lang": "en", "num_options": 2,
             "route": "classification", "correct": True},
            {"rid": "b", "kind": "choice", "lang": "zh", "num_options": 4,
             "route": "classification", "correct": False},
            {"rid": "c", "kind": "noul", "lang": "en", "num_options": 5,
             "route": "distillation", "correct": True},
            {"rid": "d", "kind": "score", "lang": "zh", "num_options": 10,
             "route": "classification", "correct": True},
        ]

    def test_stratified_metrics_and_keys(self):
        skipped = {"options_gt_26": 2, "prompt_too_long": 1}
        metrics = eval_decision_scorer.aggregate_metrics(
            self._records(), skipped, 2.0, "view.jsonl", "model-x", "adapter-x", "head.pt")

        # eval_decision.py 的键名与口径
        for key in ("total", "correct", "accuracy", "by_kind", "by_lang",
                    "by_option_bucket", "by_route", "skipped_stats",
                    "duration_seconds", "samples_per_second",
                    "eval_view", "model", "adapter"):
            self.assertIn(key, metrics)
        self.assertEqual(metrics["total"], 4)
        self.assertEqual(metrics["correct"], 3)
        self.assertEqual(metrics["accuracy"], 0.75)
        self.assertEqual(metrics["skipped_stats"], skipped)
        self.assertEqual(metrics["duration_seconds"], 2.0)
        self.assertEqual(metrics["samples_per_second"], 2.0)
        self.assertEqual(metrics["eval_view"], "view.jsonl")
        self.assertEqual(metrics["model"], "model-x")
        self.assertEqual(metrics["adapter"], "adapter-x")
        self.assertEqual(metrics["head"], "head.pt")

        # 分层：每组 total 之和等于总样本数
        for key in ("by_kind", "by_lang", "by_option_bucket", "by_route"):
            self.assertEqual(sum(v["total"] for v in metrics[key].values()), 4, key)
        self.assertEqual(metrics["by_kind"]["choice"]["total"], 2)
        self.assertEqual(metrics["by_kind"]["choice"]["correct"], 1)
        self.assertEqual(metrics["by_kind"]["choice"]["accuracy"], 0.5)
        self.assertEqual(metrics["by_lang"]["zh"]["total"], 2)
        self.assertEqual(metrics["by_route"]["distillation"]["total"], 1)
        self.assertEqual(metrics["by_option_bucket"]["2"]["total"], 1)
        self.assertEqual(metrics["by_option_bucket"]["3-4"]["total"], 1)
        self.assertEqual(metrics["by_option_bucket"]["5-8"]["total"], 1)
        self.assertEqual(metrics["by_option_bucket"]["9-26"]["total"], 1)

        # 可 JSON 序列化（--json 输出）
        json.dumps(metrics, ensure_ascii=False)

    def test_empty_records(self):
        metrics = eval_decision_scorer.aggregate_metrics(
            [], {"prompt_too_long": 3}, 0.0, "v", "m", "a", "h")
        self.assertEqual(metrics["total"], 0)
        self.assertEqual(metrics["correct"], 0)
        self.assertEqual(metrics["accuracy"], 0.0)
        self.assertEqual(metrics["samples_per_second"], 0.0)
        self.assertEqual(metrics["skipped_stats"], {"prompt_too_long": 3})

    def test_duration_guard_avoids_division_by_zero(self):
        metrics = eval_decision_scorer.aggregate_metrics(
            self._records(), {}, 0.0, "v", "m", "a", "h")
        self.assertEqual(metrics["duration_seconds"], 0.0)
        self.assertGreaterEqual(metrics["samples_per_second"], 0.0)
        self.assertTrue(math.isfinite(metrics["samples_per_second"]))


# ---------------------------------------------------------------------------
# 5. 跳过计数：EvalScorerDataset + build_skipped_stats
# ---------------------------------------------------------------------------

class TestSkipStats(unittest.TestCase):

    def _rows(self):
        long_prompt = ("【情境】\n" + "S" * 1200 + "\n\n【问题】\nQ?\n\n"
                       + OPTIONS_SECTION_HEADER + "\nA. a\nB. b")
        return [
            make_row(rid="ok", labels=("aa", "bb", "cc"), answer_idx=1),
            make_row(rid="big", labels=[f"o{i}" for i in range(28)], answer_idx=0),
            make_row(rid="badans", labels=("a", "b"), answer_idx=5),
            make_row(rid="noopts", labels=("a", "b"), answer_idx=0),
            make_row(rid="noprompt", labels=("a", "b"), answer_idx=0, prompt=""),
            make_row(rid="nomarker", labels=("a", "b"), answer_idx=0,
                     prompt="no section header here"),
            make_row(rid="long", labels=("a", "b"), answer_idx=0, prompt=long_prompt),
            make_row(rid="long_big", labels=[f"o{i}" for i in range(28)],
                     answer_idx=0, prompt=long_prompt),
            make_row(rid="emptyseg", labels=("", "b"), answer_idx=0),
        ]

    def _build_dataset(self, tmp_path: Path, max_prompt_chars: int):
        rows = self._rows()
        rows[3]["options"] = []  # noopts
        view = Path(tmp_path) / "eval-view.jsonl"
        write_jsonl(view, rows, malformed_lines=["{not valid json"])
        dataset = eval_decision_scorer.EvalScorerDataset(
            jsonl_path=view,
            tokenizer=EmptyOpStubTokenizer(),
            seq_len=4096,
            limit=0,
            max_prompt_chars=max_prompt_chars,
        )
        return dataset, view

    def test_skip_reasons_and_total_read_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset, _ = self._build_dataset(Path(tmp), max_prompt_chars=1000)
            stats = eval_decision_scorer.build_skipped_stats(dataset)

            self.assertIsInstance(dataset, ScorerDataset)  # 复用训练用数据集
            self.assertEqual(len(dataset), 1)              # 只有 "ok" 行可评测
            self.assertEqual(dataset.prompt_too_long, 1)   # 只有 long_ok 超长
            self.assertEqual(stats["options_gt_26"], 2)    # big + long_big（优先级高于超长）
            self.assertEqual(stats["prompt_too_long"], 1)
            self.assertEqual(stats["invalid_answer_idx"], 1)
            self.assertEqual(stats["missing_options"], 1)
            self.assertEqual(stats["missing_prompt"], 1)
            self.assertEqual(stats["prompt_without_option_marker"], 1)
            self.assertEqual(stats["seq_len_too_short_for_options"], 0)
            self.assertEqual(stats["other"], 1)            # empty_option_segment
            self.assertEqual(stats["unparseable"], 1)      # 坏 JSON 行
            # total_read = total + total_skipped（10 = 9 行 JSON + 1 行坏 JSON）
            self.assertEqual(
                stats["total_skipped"],
                stats["options_gt_26"] + stats["prompt_too_long"]
                + stats["invalid_answer_idx"] + stats["missing_options"]
                + stats["missing_prompt"] + stats["prompt_without_option_marker"]
                + stats["seq_len_too_short_for_options"] + stats["other"] + stats["unparseable"],
            )
            self.assertEqual(len(dataset) + stats["total_skipped"], 10)

    def test_max_prompt_chars_zero_disables_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset, _ = self._build_dataset(Path(tmp), max_prompt_chars=0)
            stats = eval_decision_scorer.build_skipped_stats(dataset)
            self.assertEqual(dataset.prompt_too_long, 0)
            self.assertEqual(stats["prompt_too_long"], 0)
            # long_ok 不再被过滤，成为有效样本（token 数 < seq_len 4096）
            self.assertEqual(len(dataset), 2)
            # 其余跳过原因不变：仅 prompt_too_long 归零（9 行 JSON 中 long 行变为有效）
            self.assertEqual(stats["total_skipped"], 8)
            self.assertEqual(len(dataset) + stats["total_skipped"], 10)

    def test_should_skip_prompt_too_long_precedence(self):
        """结构非法行不会被记成 prompt_too_long（优先级与 Track A 一致）。"""
        long_prompt = "【情境】\n" + "S" * 50 + "\n\n【选项】\nA. a\nB. b"
        self.assertFalse(
            eval_decision_scorer.should_skip_prompt_too_long(
                make_row(labels=[f"o{i}" for i in range(28)], answer_idx=0, prompt=long_prompt), 10))
        self.assertFalse(
            eval_decision_scorer.should_skip_prompt_too_long(
                make_row(labels=("a", "b"), answer_idx=9, prompt=long_prompt), 10))
        self.assertFalse(
            eval_decision_scorer.should_skip_prompt_too_long(
                make_row(labels=("a", "b"), answer_idx=0, prompt=""), 10))
        self.assertFalse(
            eval_decision_scorer.should_skip_prompt_too_long(
                make_row(labels=(), answer_idx=0), 10))
        self.assertTrue(
            eval_decision_scorer.should_skip_prompt_too_long(
                make_row(labels=("a", "b"), answer_idx=0, prompt=long_prompt), 10))
        # 关闭限制时不跳过
        self.assertFalse(
            eval_decision_scorer.should_skip_prompt_too_long(
                make_row(labels=("a", "b"), answer_idx=0, prompt=long_prompt), 0))

    def test_track_a_prompt_chars_matches_suffix_convention(self):
        prompt = "abc\n\n"
        self.assertEqual(
            eval_decision_scorer.track_a_prompt_chars(prompt),
            len("abc") + len(eval_decision_scorer.TRACK_A_ANSWER_SUFFIX),
        )
        self.assertEqual(eval_decision_scorer.track_a_prompt_chars(None), 0)


# ---------------------------------------------------------------------------
# 6. 省显存前向：resolve_transformer / compute_marker_scores
# ---------------------------------------------------------------------------

class TestEfficientForward(unittest.TestCase):

    def _peft_causal_lm(self):
        torch.manual_seed(0)
        config = tiny_llama_config()
        base = AutoModelForCausalLM.from_config(config)
        peft_model = get_peft_model(
            base,
            LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0, bias="none",
                       target_modules="all-linear", task_type="CAUSAL_LM"),
        )
        # 默认 lora_B 零初始化会掩盖 LoRA 是否真正生效：随机化后再做数值对照
        with torch.no_grad():
            for name, param in peft_model.named_parameters():
                if "lora_B" in name:
                    param.normal_(0.0, 0.5)
        return peft_model

    def test_resolve_transformer_variants(self):
        config = tiny_llama_config()
        causal = AutoModelForCausalLM.from_config(config)
        plain = AutoModel.from_config(config)
        peft_causal = get_peft_model(
            AutoModelForCausalLM.from_config(config),
            LoraConfig(r=2, lora_alpha=4, lora_dropout=0.0, bias="none",
                       target_modules="all-linear", task_type="CAUSAL_LM"),
        )
        peft_generic = get_peft_model(
            AutoModel.from_config(config),
            LoraConfig(r=2, lora_alpha=4, lora_dropout=0.0, bias="none",
                       target_modules="all-linear", task_type=None),
        )
        for model in (causal, plain, peft_causal, peft_generic):
            transformer = eval_decision_scorer.resolve_transformer(model)
            self.assertIsNotNone(transformer)
            self.assertEqual(type(transformer).__name__, "LlamaModel")
        # 无法识别的普通模块 -> None（触发回退路径）
        self.assertIsNone(eval_decision_scorer.resolve_transformer(torch.nn.Linear(2, 2)))
        self.assertIsNone(eval_decision_scorer.resolve_transformer(None))

    def test_fast_path_matches_decision_scorer_with_lora(self):
        """省显存前向（last hidden + gather + pointer head）与 DecisionScorer.forward 数值一致。"""
        peft_model = self._peft_causal_lm()
        scorer = DecisionScorer(peft_model)
        torch.manual_seed(1)
        with torch.no_grad():
            scorer.pointer_head.weight.normal_(0.0, 0.1)
            scorer.pointer_head.bias.normal_(0.0, 0.1)

        input_ids = torch.randint(3, 120, (2, 9))
        attention_mask = torch.ones_like(input_ids)
        marker_positions = torch.tensor([[3, 6, 8], [2, 5, -1]])

        with torch.no_grad():
            reference = scorer(
                input_ids=input_ids,
                attention_mask=attention_mask,
                marker_positions=marker_positions,
            )
            fast = eval_decision_scorer.compute_marker_scores(
                scorer,
                input_ids=input_ids,
                attention_mask=attention_mask,
                marker_positions=marker_positions,
                transformer=eval_decision_scorer.resolve_transformer(peft_model),
            )
        self.assertEqual(tuple(fast.shape), (2, 3))
        self.assertTrue(torch.allclose(reference, fast, atol=1e-5, rtol=0.0),
                        f"max diff = {(reference - fast).abs().max().item():.3e}")
        # padding 选项位（marker=-1）统一填 -1e4
        self.assertEqual(fast[1, 2].item(), MASKED_LOGIT_FILL)
        self.assertEqual(reference[1, 2].item(), MASKED_LOGIT_FILL)

    def test_fallback_matches_reference_when_transformer_unresolved(self):
        """resolve_transformer 返回 None 时回退 DecisionScorer.forward，数值一致。"""
        torch.manual_seed(2)
        base = AutoModel.from_config(tiny_llama_config())
        scorer = DecisionScorer(base)
        with torch.no_grad():
            scorer.pointer_head.weight.normal_(0.0, 0.1)
            scorer.pointer_head.bias.normal_(0.0, 0.1)

        input_ids = torch.randint(3, 120, (2, 6))
        attention_mask = torch.ones_like(input_ids)
        marker_positions = torch.tensor([[1, 3], [2, 5]])

        with torch.no_grad():
            reference = scorer(input_ids=input_ids, attention_mask=attention_mask,
                               marker_positions=marker_positions)
            with mock.patch.object(eval_decision_scorer, "resolve_transformer",
                                   return_value=None):
                fallback = eval_decision_scorer.compute_marker_scores(
                    scorer, input_ids=input_ids, attention_mask=attention_mask,
                    marker_positions=marker_positions)
        self.assertTrue(torch.allclose(reference, fallback, atol=1e-5, rtol=0.0))


# ---------------------------------------------------------------------------
# 7. --predictions 文件往返
# ---------------------------------------------------------------------------

class TestDumpPredictions(unittest.TestCase):

    def test_jsonl_roundtrip(self):
        records = [
            eval_decision_scorer.build_prediction_row(
                {"rid": "a#1", "kind": "choice", "lang": "en", "num_options": 2,
                 "answer_idx": 0, "route": "classification"},
                [0.6, 0.4], 0),
            eval_decision_scorer.build_prediction_row(
                {"rid": "b#2", "kind": "noul", "lang": "zh", "num_options": 3,
                 "answer_idx": 2, "route": "distillation"},
                [0.1, 0.2, 0.7], 2),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "preds.jsonl"
            written = eval_decision_scorer.dump_predictions(path, records)
            self.assertEqual(written, path)
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw)  # LF 换行
            lines = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
            self.assertEqual(len(lines), 2)
            for original, loaded in zip(records, lines):
                self.assertEqual(loaded, original)
                for key in ("rid", "kind", "lang", "num_options", "gold_letter",
                            "candidate_probs", "correct", "route"):
                    self.assertIn(key, loaded)
                self.assertLess(abs(sum(loaded["candidate_probs"].values()) - 1.0), 1e-4)
            self.assertEqual(lines[0]["rid"], "a#1")
            self.assertEqual(lines[1]["rid"], "b#2")

    def test_empty_records_writes_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.jsonl"
            eval_decision_scorer.dump_predictions(path, [])
            self.assertEqual(path.read_text(encoding="utf-8"), "")


# ---------------------------------------------------------------------------
# 8. CLI 参数错误 -> exit 2
# ---------------------------------------------------------------------------

class TestCLIExitCodes(unittest.TestCase):

    def _run_main(self, argv):
        stderr = io.StringIO()
        stdout = io.StringIO()
        code = None
        with redirect_stderr(stderr), redirect_stdout(stdout):
            code = eval_decision_scorer.main(argv)
        return code, stderr.getvalue(), stdout.getvalue()

    def _run_main_system_exit(self, argv):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as context:
                eval_decision_scorer.main(argv)
        return context.exception.code

    def test_missing_required_arguments_exit_2(self):
        self.assertEqual(self._run_main_system_exit([]), 2)

    def test_unknown_argument_exit_2(self):
        self.assertEqual(
            self._run_main_system_exit(
                ["--eval-view", "v.jsonl", "--adapter-dir", "a", "--bogus-flag"]),
            2)

    def test_invalid_int_argument_exit_2(self):
        self.assertEqual(
            self._run_main_system_exit(
                ["--eval-view", "v.jsonl", "--adapter-dir", "a", "--batch-size", "abc"]),
            2)

    def test_missing_eval_view_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = Path(tmp) / "adapter"
            adapter.mkdir()
            (adapter / "adapter_config.json").write_text("{}\n", encoding="utf-8")
            code, stderr, _ = self._run_main(
                ["--eval-view", str(Path(tmp) / "no-such-view.jsonl"),
                 "--adapter-dir", str(adapter)])
            self.assertEqual(code, 2)
            self.assertIn("不存在", stderr)

    def test_missing_adapter_dir_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            view = write_jsonl(Path(tmp) / "eval-view.jsonl", [make_row()])
            code, stderr, _ = self._run_main(
                ["--eval-view", str(view),
                 "--adapter-dir", str(Path(tmp) / "no-such-adapter")])
            self.assertEqual(code, 2)
            self.assertIn("adapter 目录不存在", stderr)

    def test_missing_head_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            view = write_jsonl(Path(tmp) / "eval-view.jsonl", [make_row()])
            adapter = Path(tmp) / "adapter"
            adapter.mkdir()
            (adapter / "adapter_config.json").write_text("{}\n", encoding="utf-8")
            code, stderr, _ = self._run_main(
                ["--eval-view", str(view), "--adapter-dir", str(adapter)])
            self.assertEqual(code, 2)
            self.assertIn("scorer head 文件不存在", stderr)

    def test_predictions_inside_repo_exit_2(self):
        """predictions 输出路径落在仓库内 -> 护栏 exit 2（沿用 Track A/B 输出目录护栏）。"""
        with tempfile.TemporaryDirectory() as tmp:
            view = write_jsonl(Path(tmp) / "eval-view.jsonl", [make_row()])
            inside = get_repo_root() / "finetune" / "runs_eval_scorer_guard" / "preds.jsonl"
            self.assertEqual(
                self._run_main_system_exit(
                    ["--eval-view", str(view), "--adapter-dir", str(Path(tmp) / "adapter"),
                     "--predictions", str(inside)]),
                2)


if __name__ == "__main__":
    unittest.main()
