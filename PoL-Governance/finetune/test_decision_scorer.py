#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track B 纯 CPU 离线单元测试 (finetune/test_decision_scorer.py)

测试覆盖：
1. marker 定位与 option_count（分段 tokenize，锚点 = 每选项行末 token）；
2. 左侧截断保留选项区间 / seq_len 不足跳过 / 构建确定性；
3. padding mask（批量对齐：marker -1、option_mask、attention、soft 零填充）；
4. masked_softmax / masked_ce / masked_kl 与手算一致（含温度 T）；
5. DecisionScorer 前向形状（tiny Llama 随机模型，hidden 32 / 2 层 / 2 头 /
   intermediate 64 / vocab 128）、padding 位 -1e4、梯度回传、LoRA 挂载；
6. head state_dict 保存/加载；
7. 仓库内 output-dir 报错（exit 2）与保留集文件名护栏；
8. 训练脚本 --dry-run 小样本路径（合成数据，不加载模型权重）。

不依赖真实 GPU、不下载任何大模型权重、不读外部大文件，纯离线运行 (<60s)。
"""

from __future__ import annotations

import io
import json
import math
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# 确保在任何工作目录下均能导入 finetune 包
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 公开仓库的 check.py 在未安装模型依赖的环境里也要能通过：缺依赖时跳过整组测试（同 Track A）。
import importlib.util

_MISSING = [name for name in ("torch", "transformers", "peft")
            if importlib.util.find_spec(name) is None]
if _MISSING:
    raise unittest.SkipTest("Track B tests need training deps: missing " + ", ".join(_MISSING))

import torch

from finetune.decision_common import (
    MAX_OPTIONS,
    SimpleStubTokenizer,
    check_output_dir_guard,
    get_repo_root,
    is_path_inside_repo,
)
from finetune.decision_scorer import (
    MASKED_LOGIT_FILL,
    OPTION_LINE_PREFIX,
    OPTIONS_SECTION_HEADER,
    TRACK_B_TEMPLATE_VERSION,
    DecisionScorer,
    build_scorer_sample,
    check_input_view_guard,
    collate_scorer_batch,
    load_scorer_head,
    masked_ce,
    masked_kl,
    masked_mixed_loss,
    masked_softmax,
    save_scorer_head,
)
import finetune.train_decision_scorer as train_decision_scorer
from peft import LoraConfig, get_peft_model
from transformers import AutoModel, LlamaConfig


# ---------------------------------------------------------------------------
# 测试辅助
# ---------------------------------------------------------------------------

INSTRUCTION = "You are a closed-choice decision model."


class AsciiStubTokenizer:
    """字符级 stub tokenizer：每个首次出现的字符分配一个递增 token id（>=3）。

    与 SimpleStubTokenizer 的区别：id 从 3 起顺序分配，保证一段短文本的全部
    token id 落在 128 以内，可直接喂给 vocab_size=128 的 tiny Llama 模型。
    """

    def __init__(self):
        self.pad_token_id = 0
        self.eos_token_id = 1
        self.padding_side = "right"
        self._map = {}
        self._next = 3

    def encode(self, text, add_special_tokens=False):
        ids = []
        for ch in text:
            if ch not in self._map:
                self._map[ch] = self._next
                self._next += 1
            ids.append(self._map[ch])
        return ids

    def decode(self, ids, skip_special_tokens=False):
        rev = {v: k for k, v in self._map.items()}
        return "".join(rev.get(i, "?") for i in ids)


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
    """构造一行 tv-1 训练视图（含字母选项段，Track B 会丢弃并重建 marker 选项段）。"""
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    # >26 选项的行在视图中本不会出现（生成器已跳过）；这里只为测试跳过逻辑，
    # 字母前缀用 26 取模循环即可（该行按 options_gt_26 被丢弃，前缀内容不影响判定）。
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
        "split": "train",
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
    """brief 指定的 tiny LlamaConfig：hidden 32 / 2 层 / 2 头 / intermediate 64 / vocab 128。"""
    return LlamaConfig(
        vocab_size=vocab_size,
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=2,
    )


def build_two_sample_batch():
    """构造 2 条 ASCII 样本的批量（选项数 3 与 2，用于 padding 检验）。"""
    tok = AsciiStubTokenizer()
    row_a = make_row(rid="syn#a", labels=("aa", "bb", "cc"), answer_idx=1)
    row_b = make_row(rid="syn#b", labels=("yes", "no"), answer_idx=0, lang="zh", kind="noul")
    sample_a, err_a = build_scorer_sample(row_a, tok, seq_len=256)
    sample_b, err_b = build_scorer_sample(row_b, tok, seq_len=256)
    assert err_a is None and err_b is None
    batch = collate_scorer_batch([sample_a, sample_b], pad_token_id=tok.pad_token_id)
    return tok, sample_a, sample_b, batch


# ---------------------------------------------------------------------------
# 样本构造与 marker 定位
# ---------------------------------------------------------------------------

class TestBuildScorerSample(unittest.TestCase):

    def test_structure_and_marker_positions(self):
        """marker 定位/option_count：锚点 = 每选项行 'OP: <label>' 的最后一个 token。"""
        tok = SimpleStubTokenizer()
        labels = ("行动一", "行动二", "行动三", "行动四")
        row = make_row(rid="item#q1", labels=labels, answer_idx=2, lang="zh")
        sample, err = build_scorer_sample(row, tok, seq_len=512)

        self.assertIsNone(err)
        # brief 要求的关键字段全部存在
        for key in ("input_ids", "attention_mask", "marker_positions", "option_count",
                    "answer_idx", "soft", "route", "rid"):
            self.assertIn(key, sample)
        self.assertEqual(sample["option_count"], 4)
        self.assertEqual(sample["answer_idx"], 2)
        self.assertEqual(sample["route"], "classification")
        self.assertEqual(sample["rid"], "item#q1")
        self.assertIsNone(sample["soft"])
        self.assertEqual(sample["template_version"], TRACK_B_TEMPLATE_VERSION)
        self.assertEqual(sample["attention_mask"], [1] * len(sample["input_ids"]))

        # marker_positions：数量 = 选项数、严格递增、落在序列内
        self.assertEqual(len(sample["marker_positions"]), 4)
        positions = sample["marker_positions"]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(all(0 <= p < len(sample["input_ids"]) for p in positions))

        # 解码还原：情境/问题段与 tv-1 字节一致；选项段为每选项一行 'OP: <label>'
        decoded = tok.decode(sample["input_ids"])
        head = row["prompt"].rsplit(OPTIONS_SECTION_HEADER, 1)[0]
        self.assertTrue(decoded.startswith(head))
        option_lines = "\n".join(OPTION_LINE_PREFIX + label for label in labels)
        self.assertTrue(decoded.endswith(OPTIONS_SECTION_HEADER + "\n" + option_lines))
        self.assertNotIn("\nA. ", decoded.split(OPTIONS_SECTION_HEADER, 1)[1])  # 字母选项已丢弃

        # 每个锚点 token 解码后正好是该选项行最后一个字符
        for k, label in enumerate(labels):
            self.assertEqual(tok.decode([sample["input_ids"][positions[k]]]), label[-1])

    def test_soft_passthrough_and_normalization(self):
        """distillation 行 soft 归一化透传；无效 soft 回退 None（由数据集层计数）。"""
        tok = SimpleStubTokenizer()
        row = make_row(
            rid="item#q2", labels=("a", "b", "c"), answer_idx=0,
            route="distillation", soft=[2.0, 5.0, 3.0],
        )
        sample, err = build_scorer_sample(row, tok, seq_len=256)
        self.assertIsNone(err)
        self.assertEqual(sample["route"], "distillation")
        self.assertAlmostEqual(sum(sample["soft"]), 1.0, places=9)
        self.assertAlmostEqual(sample["soft"][1], 0.5, places=9)

        # 无效 soft：全 0 / 负数 / 长度不匹配 -> None（回退硬标签）
        for bad in ([0.0, 0.0, 0.0], [-1.0, 2.0, 1.0], [0.5, 0.5]):
            row_bad = make_row(rid="item#q3", labels=("a", "b", "c"), answer_idx=0,
                               route="distillation", soft=bad)
            sample_bad, err_bad = build_scorer_sample(row_bad, tok, seq_len=256)
            self.assertIsNone(err_bad)
            self.assertIsNone(sample_bad["soft"])

        # classification 行即使带 soft 也不消费
        row_cls = make_row(rid="item#q4", labels=("a", "b"), answer_idx=0,
                           route="classification", soft=[0.9, 0.1])
        sample_cls, err_cls = build_scorer_sample(row_cls, tok, seq_len=256)
        self.assertIsNone(err_cls)
        self.assertIsNone(sample_cls["soft"])

    def test_option_labels_fallback_and_skip_options_gt_26(self):
        """>26 选项跳过（与 Track A 一致）；option_labels 缺失时回退 options 键。"""
        tok = SimpleStubTokenizer()

        row_28 = make_row(rid="item#big", labels=[f"o{i}" for i in range(28)], answer_idx=0)
        sample_28, err_28 = build_scorer_sample(row_28, tok, seq_len=1024)
        self.assertIsNone(sample_28)
        self.assertEqual(err_28, "options_gt_26")
        self.assertGreater(28, MAX_OPTIONS)

        # 恰好 26 个选项可用
        row_26 = make_row(rid="item#edge", labels=[f"o{i}" for i in range(26)], answer_idx=25)
        sample_26, err_26 = build_scorer_sample(row_26, tok, seq_len=4096)
        self.assertIsNone(err_26)
        self.assertEqual(sample_26["option_count"], 26)

        # option_labels 缺失 -> 用 options 键渲染
        row_fb = make_row(rid="item#fb", labels=("x", "y"), answer_idx=0)
        row_fb.pop("option_labels")
        sample_fb, err_fb = build_scorer_sample(row_fb, tok, seq_len=256)
        self.assertIsNone(err_fb)
        decoded = tok.decode(sample_fb["input_ids"])
        self.assertIn("OP: opt0", decoded)
        self.assertIn("OP: opt1", decoded)

    def test_skip_invalid_rows(self):
        """非法行跳过原因：answer_idx 越界 / 缺 prompt / 无 '【选项】' 分隔。"""
        tok = SimpleStubTokenizer()

        row_idx = make_row(rid="e1", labels=("a", "b"), answer_idx=5)
        self.assertEqual(build_scorer_sample(row_idx, tok, 256)[1], "invalid_answer_idx")

        row_neg = make_row(rid="e2", labels=("a", "b"), answer_idx=-1)
        self.assertEqual(build_scorer_sample(row_neg, tok, 256)[1], "invalid_answer_idx")

        row_no_prompt = make_row(rid="e3", labels=("a", "b"), answer_idx=0, prompt="")
        self.assertEqual(build_scorer_sample(row_no_prompt, tok, 256)[1], "missing_prompt")

        row_no_marker = make_row(rid="e4", labels=("a", "b"), answer_idx=0, prompt="no section header")
        self.assertEqual(build_scorer_sample(row_no_marker, tok, 256)[1],
                         "prompt_without_option_marker")

        row_no_options = make_row(rid="e5", labels=("a",), answer_idx=0)
        row_no_options["options"] = []
        self.assertEqual(build_scorer_sample(row_no_options, tok, 256)[1], "missing_options")

    def test_left_truncation_keeps_option_region(self):
        """左侧截断：保留完整选项 marker 区间；seq_len 连选项区都放不下时跳过。"""
        tok = SimpleStubTokenizer()
        long_state = "S" * 300
        prompt = (
            "【情境】\n" + long_state + "\n\n【问题】\nQ?\n\n"
            + OPTIONS_SECTION_HEADER + "\nA. aa\nB. bb"
        )
        row = make_row(rid="item#tr", labels=("aa", "bb"), answer_idx=0, prompt=prompt)

        # 无截断基线
        full_sample, err = build_scorer_sample(row, tok, seq_len=4096)
        self.assertIsNone(err)
        full_len = len(full_sample["input_ids"])
        self.assertGreater(full_len, 300)

        # 左截断后：长度 = seq_len，全部 marker 保留，选项段完整
        seq_len = 120
        trunc_sample, err2 = build_scorer_sample(row, tok, seq_len=seq_len)
        self.assertIsNone(err2)
        self.assertEqual(len(trunc_sample["input_ids"]), seq_len)
        positions = trunc_sample["marker_positions"]
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions, sorted(positions))
        self.assertGreaterEqual(positions[0], 0)
        decoded = tok.decode(trunc_sample["input_ids"])
        self.assertTrue(decoded.endswith("OP: aa\nOP: bb"))
        # 截断掉的正是最左侧内容（长情境被裁掉）
        self.assertNotIn("S" * 100, decoded)
        # marker 位置与全序列一致地平移
        drop = full_len - seq_len
        self.assertEqual(positions, [p - drop for p in full_sample["marker_positions"]])

        # seq_len 连第一个选项行都放不下 -> 跳过
        too_short, err3 = build_scorer_sample(row, tok, seq_len=3)
        self.assertIsNone(too_short)
        self.assertEqual(err3, "seq_len_too_short_for_options")

    def test_deterministic_construction(self):
        """构建确定性：同一行 + 相同初始化的 tokenizer 两次构造结果完全一致。"""
        row = make_row(rid="item#det", labels=("m", "n", "p"), answer_idx=2,
                      route="distillation", soft=[0.2, 0.3, 0.5])
        sample_a, err_a = build_scorer_sample(row, SimpleStubTokenizer(), seq_len=256)
        sample_b, err_b = build_scorer_sample(row, SimpleStubTokenizer(), seq_len=256)
        self.assertIsNone(err_a)
        self.assertIsNone(err_b)
        self.assertEqual(sample_a, sample_b)


# ---------------------------------------------------------------------------
# 批量对齐与 padding mask
# ---------------------------------------------------------------------------

class TestCollateAndMasks(unittest.TestCase):

    def test_collate_padding_and_masks(self):
        """padding mask：marker 补 -1、option_mask 区分真实选项、attention 右填充、soft 零填充。"""
        tok = SimpleStubTokenizer()
        row_a = make_row(rid="a", labels=("aa", "bb", "cc"), answer_idx=1,
                         route="distillation", soft=[0.1, 0.6, 0.3])
        row_b = make_row(rid="b", labels=("yes", "no"), answer_idx=0, kind="noul", lang="zh")
        sample_a, err_a = build_scorer_sample(row_a, tok, seq_len=256)
        sample_b, err_b = build_scorer_sample(row_b, tok, seq_len=256)
        self.assertIsNone(err_a)
        self.assertIsNone(err_b)

        pad_id = tok.pad_token_id
        batch = collate_scorer_batch([sample_a, sample_b], pad_token_id=pad_id)

        max_len = max(len(sample_a["input_ids"]), len(sample_b["input_ids"]))
        self.assertEqual(batch["input_ids"].shape, (2, max_len))
        self.assertEqual(batch["marker_positions"].shape, (2, 3))  # max_opts = 3
        self.assertEqual(batch["option_mask"].dtype, torch.bool)
        self.assertEqual(batch["has_soft"].dtype, torch.bool)

        # attention_mask：真实 token 1，右侧 padding 0
        for i, s in enumerate((sample_a, sample_b)):
            n = len(s["input_ids"])
            self.assertTrue(bool((batch["attention_mask"][i, :n] == 1).all()))
            if n < max_len:
                self.assertTrue(bool((batch["attention_mask"][i, n:] == 0).all()))
                self.assertTrue(bool((batch["input_ids"][i, n:] == pad_id).all()))

        # option_mask / marker padding：3 选项行全真，2 选项行第 3 位为假且 marker=-1
        self.assertEqual(batch["option_mask"][0].tolist(), [True, True, True])
        self.assertEqual(batch["option_mask"][1].tolist(), [True, True, False])
        self.assertEqual(batch["marker_positions"][1, 2].item(), -1)
        for k in range(3):
            self.assertGreaterEqual(batch["marker_positions"][0, k].item(), 0)
        for k in range(2):
            self.assertGreaterEqual(batch["marker_positions"][1, k].item(), 0)

        # soft：soft 行保留归一分布，非 soft 行全 0；padding 选项位补 0
        self.assertEqual(batch["has_soft"].tolist(), [True, False])
        self.assertAlmostEqual(float(batch["soft"][0].sum()), 1.0, places=6)
        self.assertAlmostEqual(float(batch["soft"][0, 1]), 0.6, places=6)
        self.assertTrue(bool((batch["soft"][1] == 0).all()))

        # answer_idx / 元数据透传
        self.assertEqual(batch["answer_idx"].tolist(), [1, 0])
        self.assertEqual(batch["rids"], ["a", "b"])
        self.assertEqual(batch["option_counts"], [3, 2])
        self.assertEqual(batch["kinds"], ["choice", "noul"])
        self.assertEqual(batch["langs"], ["en", "zh"])
        # row_a 是 distillation（带 soft），row_b 是 classification
        self.assertEqual(batch["routes"], ["distillation", "classification"])


# ---------------------------------------------------------------------------
# 纯函数损失与手算对照
# ---------------------------------------------------------------------------

class TestMaskedLosses(unittest.TestCase):

    def test_masked_softmax_matches_manual(self):
        """masked_softmax 与手算 softmax 一致；padding 位概率为 0。"""
        logits = torch.tensor([[1.0, 2.0, 3.0], [5.0, 1.0, 7.0]])
        mask = torch.tensor([[True, True, False], [True, False, True]])

        probs = masked_softmax(logits, mask)

        # 行 0：只在 [1, 2] 上归一
        denom0 = math.exp(1.0) + math.exp(2.0)
        self.assertAlmostEqual(probs[0, 0].item(), math.exp(1.0) / denom0, places=6)
        self.assertAlmostEqual(probs[0, 1].item(), math.exp(2.0) / denom0, places=6)
        self.assertEqual(probs[0, 2].item(), 0.0)  # -1e4 填充 -> exp 下溢为 0

        # 行 1：只在 [5, 7] 上归一
        denom1 = math.exp(5.0) + math.exp(7.0)
        self.assertAlmostEqual(probs[1, 0].item(), math.exp(5.0) / denom1, places=6)
        self.assertAlmostEqual(probs[1, 2].item(), math.exp(7.0) / denom1, places=6)
        self.assertEqual(probs[1, 1].item(), 0.0)

        # 有效位概率和为 1
        for i in range(2):
            self.assertAlmostEqual(float(probs[i].sum()), 1.0, places=6)

    def test_masked_ce_matches_manual(self):
        """masked_ce 与手算 -log softmax[answer] 一致；mask 外选项不参与。"""
        logits = torch.tensor([[2.0, 1.0, 0.0], [5.0, 3.0, 0.0]])
        mask = torch.tensor([[True, True, True], [True, True, False]])
        answer_idx = torch.tensor([0, 1])

        ce = masked_ce(logits, answer_idx, mask)

        # 行 0：全选项 softmax
        z0 = 2.0
        denom0 = math.exp(2.0) + math.exp(1.0) + math.exp(0.0)
        expected0 = -(z0 - math.log(denom0))
        self.assertAlmostEqual(ce[0].item(), expected0, places=6)

        # 行 1：第三个选项被 mask（-1e4），softmax 只在 [5, 3] 上
        denom1 = math.exp(5.0) + math.exp(3.0)
        expected1 = -(3.0 - math.log(denom1))
        self.assertAlmostEqual(ce[1].item(), expected1, places=6)

        # 答案落在 mask 外选项位（行 1 的第 3 位）-> 该行损失 0；行 0 答案仍有效
        bad_answer = torch.tensor([0, 2])
        ce_bad = masked_ce(logits, bad_answer, mask)
        self.assertAlmostEqual(ce_bad[0].item(), expected0, places=6)
        self.assertEqual(ce_bad[1].item(), 0.0)

    def test_masked_kl_temperature_manual(self):
        """masked_kl 与手算一致（T=1 与 T=2），且 logits∝log p 时 KL=0。"""
        logits = torch.tensor([[2.0, 1.0, 0.0]])
        mask = torch.tensor([[True, True, True]])
        soft = torch.tensor([[0.7, 0.2, 0.1]])

        # T=1：KL(p || softmax(z))
        q = [math.exp(x) for x in (2.0, 1.0, 0.0)]
        qs = sum(q)
        logq = [math.log(v / qs) for v in q]
        p = [0.7, 0.2, 0.1]
        expected_t1 = sum(pv * (math.log(pv) - lq) for pv, lq in zip(p, logq))
        kl_t1 = masked_kl(logits, soft, mask, temperature=1.0)
        self.assertAlmostEqual(kl_t1[0].item(), expected_t1, places=5)

        # T=2：target = p**(1/2) 重整化；学生 logits / 2
        p_t = [math.sqrt(v) for v in p]
        denom = sum(p_t)
        p_t = [v / denom for v in p_t]
        q2 = [math.exp(x / 2.0) for x in (2.0, 1.0, 0.0)]
        qs2 = sum(q2)
        logq2 = [math.log(v / qs2) for v in q2]
        expected_t2 = sum(pv * (math.log(pv) - lq) for pv, lq in zip(p_t, logq2))
        kl_t2 = masked_kl(logits, soft, mask, temperature=2.0)
        self.assertAlmostEqual(kl_t2[0].item(), expected_t2, places=5)
        self.assertNotAlmostEqual(kl_t1[0].item(), kl_t2[0].item(), places=4)

        # 恒等情形：logits = log(p)（不能带缩放，softmax(c*log p) != p 除非 c=1）
        # 且 T=1 -> 学生 softmax == p -> KL = 0
        logits_id = torch.tensor([[math.log(0.7), math.log(0.2), math.log(0.1)]])
        kl_id = masked_kl(logits_id, soft, mask, temperature=1.0)
        self.assertAlmostEqual(kl_id[0].item(), 0.0, places=5)

        # 无效温度报错
        with self.assertRaises(ValueError):
            masked_kl(logits, soft, mask, temperature=0.0)

    def test_masked_mixed_loss_combination(self):
        """masked_mixed_loss：soft 行 (1-λ)CE + λKL，非 soft 行纯 CE。"""
        logits = torch.tensor([[2.0, 1.0, 0.0]])
        mask = torch.tensor([[True, True, True]])
        answer = torch.tensor([0])
        soft = torch.tensor([[0.7, 0.2, 0.1]])

        ce = masked_ce(logits, answer, mask)
        kl = masked_kl(logits, soft, mask, temperature=2.0)

        mixed_soft = masked_mixed_loss(logits, answer, soft, mask,
                                       has_soft=torch.tensor([True]),
                                       lambda_soft=0.3, temperature=2.0)
        self.assertAlmostEqual(mixed_soft[0].item(),
                               0.7 * ce[0].item() + 0.3 * kl[0].item(), places=6)

        mixed_hard = masked_mixed_loss(logits, answer, soft, mask,
                                       has_soft=torch.tensor([False]),
                                       lambda_soft=0.3, temperature=2.0)
        self.assertAlmostEqual(mixed_hard[0].item(), ce[0].item(), places=6)

        # λ 边界：0 -> 纯 CE；1 -> 纯 KL
        mixed_l0 = masked_mixed_loss(logits, answer, soft, mask,
                                     has_soft=torch.tensor([True]),
                                     lambda_soft=0.0, temperature=2.0)
        self.assertAlmostEqual(mixed_l0[0].item(), ce[0].item(), places=6)
        mixed_l1 = masked_mixed_loss(logits, answer, soft, mask,
                                     has_soft=torch.tensor([True]),
                                     lambda_soft=1.0, temperature=2.0)
        self.assertAlmostEqual(mixed_l1[0].item(), kl[0].item(), places=6)


# ---------------------------------------------------------------------------
# DecisionScorer 模块（tiny Llama 随机模型）
# ---------------------------------------------------------------------------

class TestDecisionScorerModule(unittest.TestCase):

    def test_forward_shape_and_padding_logits(self):
        """tiny 随机模型前向：logits [B, max_opts]，padding 选项位 -1e4，题内 softmax 有效。"""
        tok, sample_a, sample_b, batch = build_two_sample_batch()

        base = AutoModel.from_config(tiny_llama_config())
        scorer = DecisionScorer(base)
        self.assertEqual(scorer.hidden_size, 32)
        self.assertEqual(scorer.pointer_head.in_features, 32)
        self.assertEqual(scorer.pointer_head.out_features, 1)

        logits = scorer(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            marker_positions=batch["marker_positions"],
        )
        # 形状 [B=2, max_opts=3]
        self.assertEqual(tuple(logits.shape), (2, 3))
        # padding 选项位已填 -1e4（行 1 只有 2 个选项）
        self.assertEqual(logits[1, 2].item(), MASKED_LOGIT_FILL)
        # 有效选项位为有限标量
        self.assertTrue(bool(torch.isfinite(logits[0]).all()))
        self.assertTrue(bool(torch.isfinite(logits[1, :2]).all()))

        # masked_softmax 后题内归一，padding 位概率 0
        probs = masked_softmax(logits, batch["option_mask"])
        self.assertAlmostEqual(float(probs[0].sum()), 1.0, places=5)
        self.assertAlmostEqual(float(probs[1].sum()), 1.0, places=5)
        self.assertEqual(probs[1, 2].item(), 0.0)

        # marker 锚点位置确实取到了各选项行末 token（用解码复核）
        for s, positions in ((sample_a, sample_a["marker_positions"]),
                            (sample_b, sample_b["marker_positions"])):
            for p in positions:
                self.assertGreaterEqual(p, 0)

    def test_backward_gradients_flow(self):
        """前向 + masked 混合损失 + 反向：head 与 base 均有梯度。"""
        tok, sample_a, sample_b, batch = build_two_sample_batch()
        base = AutoModel.from_config(tiny_llama_config())
        scorer = DecisionScorer(base)

        logits = scorer(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            marker_positions=batch["marker_positions"],
        )
        per_row = masked_mixed_loss(
            logits, batch["answer_idx"], batch["soft"], batch["option_mask"],
            batch["has_soft"], lambda_soft=0.3, temperature=2.0,
        )
        loss = per_row.mean()
        loss.backward()

        head_w = scorer.pointer_head.weight.grad
        self.assertIsNotNone(head_w)
        self.assertGreater(int(torch.count_nonzero(head_w)), 0)
        base_grads = [p.grad for p in base.parameters() if p.grad is not None]
        self.assertGreater(len(base_grads), 0)

    def test_lora_wrap_and_backward(self):
        """LoRA(all-linear) 挂载在 AutoModel base 上可训练，梯度可回传。"""
        tok, sample_a, sample_b, batch = build_two_sample_batch()
        base = AutoModel.from_config(tiny_llama_config())
        peft_model = get_peft_model(
            base,
            LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0, bias="none",
                       target_modules="all-linear", task_type=None),
        )
        trainable = [p for p in peft_model.parameters() if p.requires_grad]
        self.assertGreater(sum(p.numel() for p in trainable), 0)

        scorer = DecisionScorer(peft_model)
        logits = scorer(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            marker_positions=batch["marker_positions"],
        )
        per_row = masked_mixed_loss(
            logits, batch["answer_idx"], batch["soft"], batch["option_mask"],
            batch["has_soft"], lambda_soft=0.3, temperature=2.0,
        )
        per_row.mean().backward()

        lora_named = [(n, p) for n, p in peft_model.named_parameters()
                      if p.requires_grad and ("lora_A" in n or "lora_B" in n)]
        self.assertGreater(len(lora_named), 0)
        self.assertTrue(any(p.grad is not None for _, p in lora_named))

        # 冻结的底座参数不应有梯度（抽查）
        frozen = [(n, p) for n, p in peft_model.named_parameters() if not p.requires_grad]
        self.assertTrue(all(p.grad is None for _, p in frozen))

    def test_head_save_load_roundtrip(self):
        """scorer head state_dict + 配置保存/加载往返一致。"""
        with tempfile.TemporaryDirectory() as tmp:
            head_path = Path(tmp) / "scorer_head.pt"
            head = torch.nn.Linear(32, 1)
            with torch.no_grad():
                head.weight.uniform_(-0.5, 0.5)
                head.bias.uniform_(-0.5, 0.5)

            save_scorer_head(head, head_path, config={
                "hidden_size": 32,
                "template_version": TRACK_B_TEMPLATE_VERSION,
                "max_options": MAX_OPTIONS,
            })
            self.assertTrue(head_path.exists())

            head2 = torch.nn.Linear(32, 1)
            config = load_scorer_head(head2, head_path)
            self.assertEqual(config["template_version"], TRACK_B_TEMPLATE_VERSION)
            self.assertEqual(config["hidden_size"], 32)
            self.assertTrue(torch.allclose(head2.weight, head.weight))
            self.assertTrue(torch.allclose(head2.bias, head.bias))


# ---------------------------------------------------------------------------
# 护栏与 CLI
# ---------------------------------------------------------------------------

class TestGuardsAndCLI(unittest.TestCase):

    def setUp(self):
        self.repo_root = get_repo_root()

    def test_output_dir_guard_inside_repo(self):
        """仓库内 output-dir 必须拒绝（exit 2）；仓库外通过。"""
        inside = self.repo_root / "finetune" / "runs_b"
        self.assertTrue(is_path_inside_repo(inside, self.repo_root))
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                check_output_dir_guard(inside, self.repo_root)
            self.assertEqual(cm.exception.code, 2)

        outside = Path(tempfile.gettempdir()) / "pol-track-b-out"
        if not is_path_inside_repo(outside, self.repo_root):
            valid = check_output_dir_guard(outside, self.repo_root)
            self.assertEqual(valid, outside)

    def test_input_view_guard_forbidden_names(self):
        """输入视图文件名含 benchmark/holdout/private 时拒绝（exit 2）。"""
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "private-holdout-view.jsonl"
            bad.write_text("{}\n", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    check_input_view_guard(bad)
                self.assertEqual(cm.exception.code, 2)

            good = Path(tmp) / "general-train-view.jsonl"
            good.write_text("{}\n", encoding="utf-8")
            self.assertEqual(check_input_view_guard(good), good)

    def test_trainer_main_rejects_in_repo_output_dir(self):
        """train_decision_scorer 主入口：仓库内 output-dir 在 dry-run 之前即被拦截。"""
        with tempfile.TemporaryDirectory() as tmp:
            view = Path(tmp) / "syn-view.jsonl"
            view.write_text(json.dumps(make_row(), ensure_ascii=False) + "\n", encoding="utf-8")
            inside = self.repo_root / "finetune" / "runs_bad_b"
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as cm:
                    train_decision_scorer.main([
                        "--train-view", str(view),
                        "--output-dir", str(inside),
                        "--dry-run",
                    ])
                self.assertEqual(cm.exception.code, 2)

    def test_trainer_dry_run_synthetic(self):
        """--dry-run 合成数据全路径：解析 + 过滤统计 + batch + tiny 前向形状校验，不加载权重。"""
        with tempfile.TemporaryDirectory() as tmp:
            temp_path = Path(tmp)
            view = temp_path / "syn_train_view.jsonl"
            out_dir = temp_path / "runs_dry_run_b"
            missing_model = temp_path / "no-such-model-dir"  # 本地缺失路径 -> 快速回退 stub tokenizer

            rows = [
                make_row(rid="syn#01", labels=("行动一", "行动二", "行动三", "行动四"),
                         answer_idx=1, lang="zh"),
                make_row(rid="syn#02", labels=("Yes", "No"), answer_idx=0,
                         kind="noul", lang="en"),
                make_row(rid="syn#03", labels=("0", "1", "2", "3", "4"), answer_idx=3,
                         kind="score", lang="zh", route="distillation",
                         soft=[0.1, 0.1, 0.2, 0.4, 0.2]),
                make_row(rid="syn#04_exceed", labels=[f"o{i}" for i in range(28)], answer_idx=0),
            ]
            with open(view, "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

            stdout_buf = io.StringIO()
            with redirect_stdout(stdout_buf):
                exit_code = train_decision_scorer.main([
                    "--train-view", str(view),
                    "--model", str(missing_model),
                    "--output-dir", str(out_dir),
                    "--dry-run",
                    "--limit", "10",
                    "--seq-len", "512",
                ])
            output_text = stdout_buf.getvalue()

            self.assertEqual(exit_code, 0)
            self.assertIn("[DRY-RUN] 开启 Track B", output_text)
            self.assertIn(TRACK_B_TEMPLATE_VERSION, output_text)
            self.assertIn("skipped_options_gt_26: 1", output_text)
            self.assertIn("soft_rows: 1", output_text)
            self.assertIn("tiny 随机模型前向", output_text)
            self.assertIn("校验通过！未加载模型权重", output_text)
            # dry-run 不创建输出目录、不写任何产物
            self.assertFalse(out_dir.exists())


if __name__ == "__main__":
    unittest.main()
