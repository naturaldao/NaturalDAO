#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track B: 决策模型候选评分头训练脚本 (finetune/train_decision_scorer.py)

功能：
- 基于 Qwen3-1.7B（或其他因果语言模型底座，取 AutoModel 的 transformer 部分，无 lm_head）
  + LoRA(all-linear) + 新 Linear(hidden->1) pointer head（全参）
- 每个选项行（"OP: <label>"，模板 tv-1b）末 token 的 hidden state -> scalar，
  题内 masked softmax；原生支持变长候选（2..26）
- 硬标签 masked CE；软标签（仅 route=distillation 且 soft 有效）masked KL(T)，
  lambda 混合（--lambda-soft，默认 0.3）
- fp16 AMP + GradScaler（Turing 无 bf16）、gradient checkpointing、左侧截断保留选项区
- 支持纯 CPU dry-run（不加载模型权重，forward 形状校验用随机初始化 tiny 模型）、
  断点续跑、训练清单 train-manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 减少 Windows + CUDA 的显存碎片（与 laya 训练脚本一致）
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# 引入项目通用决策与安全护栏模块
try:
    from finetune.decision_common import (
        MAX_OPTIONS,
        SimpleStubTokenizer,
        check_output_dir_guard,
        compute_file_sha256,
        compute_stratified_metrics,
        get_git_commit,
    )
    from finetune.decision_scorer import (
        MASKED_LOGIT_FILL,
        MARKER_SCHEME_INFO,
        TRACK_B_TEMPLATE_VERSION,
        build_scorer_sample,
        check_input_view_guard,
        collate_scorer_batch,
        masked_ce,
        masked_mixed_loss,
    )
except ImportError:
    # 允许直接在 finetune/ 目录下执行 python train_decision_scorer.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from finetune.decision_common import (
        MAX_OPTIONS,
        SimpleStubTokenizer,
        check_output_dir_guard,
        compute_file_sha256,
        compute_stratified_metrics,
        get_git_commit,
    )
    from finetune.decision_scorer import (
        MASKED_LOGIT_FILL,
        MARKER_SCHEME_INFO,
        TRACK_B_TEMPLATE_VERSION,
        build_scorer_sample,
        check_input_view_guard,
        collate_scorer_batch,
        masked_ce,
        masked_mixed_loss,
    )

# 动态加载深度学习依赖，以便在无 torch 环境下仍可通过 py_compile（dry-run 退化为纯数据校验）
try:
    import torch
    from torch.optim import AdamW
    from torch.utils.data import DataLoader
    from transformers import (
        AutoConfig,
        AutoModel,
        AutoTokenizer,
        LlamaConfig,
        get_cosine_schedule_with_warmup,
    )
    from peft import LoraConfig, PeftModel, get_peft_model
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

# 延迟导入：DecisionScorer 定义在 decision_scorer.py，无 torch 时该类仍可导入但不可实例化
from finetune.decision_scorer import DecisionScorer, load_scorer_head, save_scorer_head  # noqa: E402


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track B 决策模型候选评分头训练脚本 (Qwen3 + LoRA + pointer head, masked CE/KL)"
    )
    # 数据与模型路径
    parser.add_argument(
        "--train-view", type=str, required=True,
        help="训练视图 JSONL 路径 (例如 general-train-view.jsonl)",
    )
    parser.add_argument(
        "--eval-view", type=str, default=None,
        help="评测视图 JSONL 路径 (例如 general-validation-view.jsonl)",
    )
    parser.add_argument(
        "--model", type=str, default="Qwen/Qwen3-1.7B",
        help="底座模型名称或本地路径 (默认 Qwen/Qwen3-1.7B；推荐本地路径如 D:/pol2-train/models/Qwen3-1.7B)",
    )
    parser.add_argument(
        "--output-dir", type=str, required=True,
        help="训练产物输出目录 (必须在仓库外，例如 D:/pol2-train/runs/track-b-1.7b)",
    )

    # 训练超参数（与 Track A 对齐）
    parser.add_argument("--epochs", type=int, default=2, help="训练轮数 (默认 2)")
    parser.add_argument("--batch-size", type=int, default=4, help="单步微批次大小 (默认 4)")
    parser.add_argument("--grad-accum", type=int, default=8, help="梯度累积步数 (默认 8，有效批次 32)")
    parser.add_argument("--lr", type=float, default=1e-4, help="LoRA AdamW 学习率 (默认 1e-4)")
    parser.add_argument("--seq-len", type=int, default=1536, help="最大序列长度 (默认 1536)")
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank (默认 16)")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha (默认 32)")
    parser.add_argument("--lora-dropout", type=float, default=0.05, help="LoRA dropout (默认 0.05)")
    parser.add_argument(
        "--max-steps", type=int, default=0,
        help="最大训练步数 (0 表示按 epoch 循环，默认 0)",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="限制训练集加载行数 (0 表示无限制，调试用)",
    )
    parser.add_argument(
        "--eval-limit", type=int, default=500,
        help="周期评测采样的最大验证行数 (默认 500)",
    )
    parser.add_argument(
        "--eval-every", type=int, default=200,
        help="每隔多少 step 运行一次周期评测 (默认 200)",
    )
    parser.add_argument("--seed", type=int, default=20261023, help="全局随机种子 (默认 20261023)")

    # Track B 专属超参数
    parser.add_argument(
        "--lambda-soft", type=float, default=0.3,
        help="soft 蒸馏行 KL 的混合权重 lambda（默认 0.3；仅 route=distillation 且 soft 有效行启用）",
    )
    parser.add_argument(
        "--soft-temperature", type=float, default=2.0,
        help="软标签 KL 的温度 T（默认 2.0；学生 logits / T，target 按 p**(1/T) 重整化）",
    )
    parser.add_argument(
        "--head-lr-mult", type=float, default=5.0,
        help="pointer head 相对 LoRA 学习率的倍数（默认 5.0，即 head lr = lr * 5）",
    )
    parser.add_argument(
        "--shuffle-options", action="store_true",
        help="每个 epoch 打乱每题选项顺序（防位置偏置；代价是每 epoch 重新 tokenize）",
    )

    # 控制开关
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅加载并校验数据、构造 batch 并做前向形状校验（随机 tiny 模型，不加载模型权重）",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="从 output-dir 已有 adapter 与 scorer_head.pt 恢复训练",
    )

    return parser.parse_args(argv)


class ScorerDataset:
    """封装决策训练视图的解析与 Track B 样本构造。"""

    def __init__(
        self,
        jsonl_path: Path,
        tokenizer: Any,
        seq_len: int = 1536,
        limit: int = 0,
        shuffle_options: bool = False,
        shuffle_seed: int = 0,
    ):
        self.jsonl_path = jsonl_path
        self.tokenizer = tokenizer
        self.seq_len = seq_len
        self.limit = limit
        self.shuffle_options = shuffle_options
        self._rng = random.Random(shuffle_seed) if shuffle_options else None

        self.samples: List[Dict[str, Any]] = []
        self.stats: Dict[str, int] = {
            "total_read": 0,
            "valid": 0,
            "skipped_missing_options": 0,
            "skipped_options_gt_26": 0,
            "skipped_invalid_answer_idx": 0,
            "skipped_missing_prompt": 0,
            "skipped_prompt_without_option_marker": 0,
            "skipped_seq_len_too_short_for_options": 0,
            "soft_rows": 0,
            "soft_invalid_fallback_hard": 0,
        }

        self._rows: List[Dict[str, Any]] = []
        self._load_rows()
        self.rebuild(shuffle=False)

    def _load_rows(self) -> None:
        if not self.jsonl_path.exists():
            raise FileNotFoundError(f"数据文件不存在: {self.jsonl_path}")
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                line_str = line.strip()
                if not line_str:
                    continue
                self.stats["total_read"] += 1
                try:
                    row = json.loads(line_str)
                except Exception:
                    continue
                if not isinstance(row, dict):
                    continue
                row["_line_idx"] = line_idx  # 内部字段，构造样本时被忽略
                self._rows.append(row)
                if self.limit > 0 and len(self._rows) >= self.limit:
                    break

    def _permute_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """按当前 RNG 打乱一题的选项顺序（options/labels/answer_idx/soft 同步置换）。"""
        assert self._rng is not None
        options = row.get("options") or []
        labels = row.get("option_labels")
        n = len(options)
        perm = list(range(n))
        self._rng.shuffle(perm)
        new_labels = None
        if isinstance(labels, list) and len(labels) == n:
            new_labels = [labels[i] for i in perm]
        new_soft = None
        soft = row.get("soft")
        if isinstance(soft, list) and len(soft) == n:
            new_soft = [soft[i] for i in perm]
        answer_idx = row.get("answer_idx")
        new_answer = None
        if isinstance(answer_idx, int) and 0 <= answer_idx < n:
            new_answer = perm.index(answer_idx)
        new_row = dict(row)
        new_row["options"] = [options[i] for i in perm]
        if new_labels is not None:
            new_row["option_labels"] = new_labels
        if new_soft is not None:
            new_row["soft"] = new_soft
        if new_answer is not None:
            new_row["answer_idx"] = new_answer
        return new_row

    def rebuild(self, shuffle: bool = True) -> None:
        """重新构造样本（--shuffle-options 时每 epoch 调用一次做选项置换）。"""
        samples: List[Dict[str, Any]] = []
        soft_rows = 0
        soft_fallback = 0
        for row in self._rows:
            r = self._permute_row(row) if (shuffle and self._rng is not None) else row
            sample, skip_reason = build_scorer_sample(r, self.tokenizer, self.seq_len)
            if sample is None:
                key = f"skipped_{skip_reason}"
                if key in self.stats:
                    self.stats[key] += 1
                continue
            if r.get("route") == "distillation":
                if sample.get("soft") is not None:
                    soft_rows += 1
                else:
                    soft_fallback += 1
            samples.append(sample)
        self.samples = samples
        self.stats["valid"] = len(samples)
        self.stats["soft_rows"] = soft_rows
        self.stats["soft_invalid_fallback_hard"] = soft_fallback

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.samples[idx]


def _autocast_context(device: Any):
    """fp16 autocast 上下文（仅 CUDA；Turing 无 bf16）。"""
    return torch.amp.autocast(device_type=device.type, dtype=torch.float16, enabled=(device.type == "cuda"))


def build_tiny_check_model(max_token_id: int) -> Any:
    """构造随机初始化 tiny Llama 模型（hidden 32 / 2 层 / 2 头 / intermediate 64）。

    供 dry-run 前向形状校验与单元测试使用；vocab 覆盖实际 token id 上限。
    不加载任何预训练权重。
    """
    vocab_size = max(128, int(max_token_id) + 2)
    config = LlamaConfig(
        vocab_size=vocab_size,
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=2,
    )
    return AutoModel.from_config(config)


def evaluate_scorer_accuracy(
    scorer: Any,
    eval_view_path: Path,
    tokenizer: Any,
    device: Any,
    limit: int = 500,
    batch_size: int = 8,
    seq_len: int = 1536,
    lambda_soft: float = 0.3,
    soft_temperature: float = 2.0,
) -> Dict[str, Any]:
    """在验证视图上评测题内 argmax 准确率（分层）与平均 NLL。"""
    if not eval_view_path.exists():
        return {}

    dataset = ScorerDataset(
        jsonl_path=eval_view_path,
        tokenizer=tokenizer,
        seq_len=seq_len,
        limit=limit,
    )
    if len(dataset) == 0:
        return {}

    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=lambda b: collate_scorer_batch(b, pad_token_id=getattr(tokenizer, "pad_token_id", 0) or 0),
    )

    records: List[Dict[str, Any]] = []
    nll_sum = 0.0
    nll_count = 0
    scorer.eval()
    for batch in loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        marker_positions = batch["marker_positions"].to(device)
        option_mask = batch["option_mask"].to(device)
        answer_idx = batch["answer_idx"].to(device)

        with torch.no_grad(), _autocast_context(device):
            logits = scorer(input_ids=input_ids, attention_mask=attention_mask, marker_positions=marker_positions)
        logits = logits.float()
        pred = logits.argmax(dim=-1)

        row_ce = masked_ce(logits, answer_idx, option_mask)
        nll_sum += float(row_ce.sum().item())
        nll_count += int(option_mask.any(dim=-1).sum().item())

        for i, rid in enumerate(batch["rids"]):
            records.append({
                "rid": rid,
                "correct": bool(pred[i].item() == answer_idx[i].item()),
                "kind": batch["kinds"][i],
                "lang": batch["langs"][i],
                "num_options": batch["option_counts"][i],
                "route": batch["routes"][i],
            })
    scorer.train()

    metrics = compute_stratified_metrics(records)
    metrics["mean_nll"] = round(nll_sum / max(1, nll_count), 6)
    return metrics


def run_dry_run(args: argparse.Namespace) -> int:
    """dry-run：数据校验 + batch 构造 + 前向形状校验（不加载模型权重）。"""
    print("=" * 60)
    print("[DRY-RUN] 开启 Track B 候选评分头数据校验与样本形状检查")
    print(f"  模板版本: {TRACK_B_TEMPLATE_VERSION}（marker: {MARKER_SCHEME_INFO['option_line_prefix']}<label>，"
          f"锚点: {MARKER_SCHEME_INFO['anchor']}）")
    print(f"  训练数据: {args.train_view}")
    print(f"  模型基座: {args.model}")
    print(f"  最大长: {args.seq_len}")
    print("=" * 60)

    # 1. Tokenizer：优先真实（本地目录离线加载），失败回退 SimpleStubTokenizer
    tokenizer = None
    if TORCH_AVAILABLE:
        try:
            tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            print(f"[DRY-RUN] 成功加载 AutoTokenizer: {args.model} (pad_token_id={tokenizer.pad_token_id})")
        except Exception as e:
            print(f"[DRY-RUN] 无法加载 AutoTokenizer ({e})，使用 SimpleStubTokenizer 模拟")
            tokenizer = SimpleStubTokenizer()
    else:
        print("[DRY-RUN] 当前 Python 环境未安装 transformers，使用 SimpleStubTokenizer")
        tokenizer = SimpleStubTokenizer()

    # 2. 数据解析
    train_path = Path(args.train_view)
    dataset = ScorerDataset(
        jsonl_path=train_path,
        tokenizer=tokenizer,
        seq_len=args.seq_len,
        limit=args.limit if args.limit > 0 else 100,  # dry-run 默认检查前 100 行
    )

    print("\n[DRY-RUN] 数据读取与过滤统计:")
    for k, v in dataset.stats.items():
        print(f"  - {k}: {v}")

    if len(dataset) == 0:
        print("[DRY-RUN] 警告: 未找到有效样本！")
        return 0

    # 3. 前 3 条样本结构检验
    print("\n[DRY-RUN] 前 3 条样本结构检验:")
    show_count = min(3, len(dataset))
    for i in range(show_count):
        item = dataset[i]
        decoded = tokenizer.decode(item["input_ids"]) if hasattr(tokenizer, "decode") else ""
        options_tail = decoded.split("【选项】")[-1][-160:].replace("\n", "\\n")
        soft_info = "有" if item["soft"] is not None else "无"
        print(f"\n--- 样本 #{i + 1} (rid: {item['rid']}) ---")
        print(f"  Kind/Lang/Route: {item['kind']} / {item['lang']} / {item['route']}")
        print(f"  选项数: {item['option_count']}，answer_idx: {item['answer_idx']}，soft: {soft_info}")
        print(f"  选项段尾部: ...{options_tail}")
        print(f"  marker_positions: {item['marker_positions']}")
        print(f"  Input IDs 长度: {len(item['input_ids'])}")

    # 4. 构造一个真实批次
    batch_size = min(args.batch_size, len(dataset))
    sub_batch = [dataset[i] for i in range(batch_size)]
    pad_id = getattr(tokenizer, "pad_token_id", 0) or 0
    batch = collate_scorer_batch(sub_batch, pad_token_id=pad_id)

    if TORCH_AVAILABLE:
        print(f"\n[DRY-RUN] 模拟批次形状: input_ids={tuple(batch['input_ids'].shape)}, "
              f"marker_positions={tuple(batch['marker_positions'].shape)}, "
              f"option_mask={tuple(batch['option_mask'].shape)}")

        # 5. 前向形状校验：随机初始化 tiny 模型（不加载任何模型权重）
        max_id = int(batch["input_ids"].max().item())
        tiny_base = build_tiny_check_model(max_id)
        tiny_scorer = DecisionScorer(tiny_base)
        with torch.no_grad():
            logits = tiny_scorer(
                input_ids=batch["input_ids"],
                attention_mask=batch["attention_mask"],
                marker_positions=batch["marker_positions"],
            )
        expected_shape = (batch_size, batch["marker_positions"].shape[1])
        ok_shape = tuple(logits.shape) == expected_shape
        padding_filled = bool((logits[~batch["option_mask"]] == MASKED_LOGIT_FILL).all().item())
        with torch.no_grad():
            per_row = masked_mixed_loss(
                logits, batch["answer_idx"], batch["soft"], batch["option_mask"],
                batch["has_soft"], lambda_soft=args.lambda_soft, temperature=args.soft_temperature,
            )
        print(f"[DRY-RUN] tiny 随机模型前向: logits 形状 {tuple(logits.shape)} (期望 {expected_shape}, "
              f"匹配={ok_shape})，padding 选项位 -1e4 填充={padding_filled}")
        print(f"[DRY-RUN] masked 混合损失(随机 logits, lambda={args.lambda_soft}, T={args.soft_temperature}): "
              f"均值 {float(per_row.mean().item()):.4f}")
        del tiny_base, tiny_scorer, logits

        # 6. best-effort 读取底座 config（仅 config.json，不加载权重）
        model_path = Path(args.model)
        if model_path.is_dir():
            try:
                cfg = AutoConfig.from_pretrained(args.model, trust_remote_code=True)
                print(f"[DRY-RUN] 底座 config 读取成功: hidden_size={getattr(cfg, 'hidden_size', '?')}, "
                      f"layers={getattr(cfg, 'num_hidden_layers', '?')}（未加载权重）")
            except Exception as e:
                print(f"[DRY-RUN] 底座 config 读取失败 ({e})，跳过")
        else:
            print("[DRY-RUN] --model 不是本地目录，跳过底座 config 读取（不访问网络、不加载权重）")
    else:
        print(f"\n[DRY-RUN] 模拟批次样本数: {len(batch['input_ids'])}, 批次最大长度: {len(batch['input_ids'][0])}")
        print("[DRY-RUN] 当前环境无 torch，跳过前向形状校验")

    print("\n[DRY-RUN] 校验通过！未加载模型权重（前向形状校验使用随机初始化 tiny 模型），未进行任何 GPU 训练计算。")
    print("=" * 60)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    # 1. 护栏：输出目录必须在仓库外（复用 Track A guard，exit 2）
    output_dir = check_output_dir_guard(args.output_dir)

    # 2. 护栏：训练/评测视图文件名不得含 benchmark/holdout/private（exit 2）
    train_view_path = check_input_view_guard(args.train_view)
    if not train_view_path.exists():
        sys.stderr.write(f"Error: 训练集文件不存在: {train_view_path}\n")
        return 1
    eval_view_path = None
    if args.eval_view:
        eval_view_path = check_input_view_guard(args.eval_view)
        if not eval_view_path.exists():
            sys.stderr.write(f"Error: 验证集文件不存在: {eval_view_path}\n")
            return 1

    # 3. Dry-Run 优先处理
    if args.dry_run:
        return run_dry_run(args)

    # 4. 正常训练依赖检查
    if not TORCH_AVAILABLE:
        sys.stderr.write(
            "Error: 当前环境未安装 torch / transformers / peft！\n"
            "真实训练请使用 Lead 预先配置好的虚拟环境 (例如 D:/pol2-train/.venv)。\n"
        )
        return 1

    # 5. 随机种子
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir = output_dir / "adapter"
    tokenizer_dir = output_dir / "tokenizer"
    head_path = output_dir / "scorer_head.pt"
    manifest_path = output_dir / "train-manifest.json"

    # 6. 输入校验和与清单信息
    train_sha256 = compute_file_sha256(train_view_path)
    eval_sha256 = compute_file_sha256(eval_view_path) if eval_view_path else "none"
    git_commit = get_git_commit()

    print("=" * 60)
    print("PoL-Governance Track B: Qwen3-1.7B 决策模型候选评分头训练")
    print(f"  模板版本: {TRACK_B_TEMPLATE_VERSION}")
    print(f"  Git Commit: {git_commit}")
    print(f"  Train View: {train_view_path} (SHA256: {train_sha256[:12]}...)")
    print(f"  Eval View:  {eval_view_path} (SHA256: {eval_sha256[:12]}...)")
    print(f"  Output Dir: {output_dir}")
    print(f"  Epochs: {args.epochs}, Batch Size: {args.batch_size}, Grad Accum: {args.grad_accum}")
    print(f"  Seq Len: {args.seq_len}, LR: {args.lr} (head lr x{args.head_lr_mult}), LoRA r: {args.lora_r}")
    print(f"  Lambda Soft: {args.lambda_soft}, Soft Temperature: {args.soft_temperature}")
    print(f"  Shuffle Options: {args.shuffle_options}, Seed: {args.seed}")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"运行设备: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}, "
              f"总显存: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")

    # 7. Tokenizer
    print("正在加载 Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    pad_token_id = tokenizer.pad_token_id or 0

    # 8. 训练数据集
    print("正在解析与编码训练数据（分段 tokenize 构造 marker 选项段）...")
    dataset = ScorerDataset(
        jsonl_path=train_view_path,
        tokenizer=tokenizer,
        seq_len=args.seq_len,
        limit=args.limit,
        shuffle_options=args.shuffle_options,
        shuffle_seed=args.seed + 1,
    )
    print(f"有效训练样本数: {len(dataset)}，过滤统计: {dataset.stats}")
    if len(dataset) == 0:
        sys.stderr.write("Error: 没有有效样本可用于训练！\n")
        return 1

    train_loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_scorer_batch(b, pad_token_id=pad_token_id),
    )

    # 9. 底座模型（AutoModel：transformer 部分，无 lm_head）
    print(f"正在加载基座模型: {args.model}...")
    torch_dtype = torch.float16 if device.type == "cuda" else torch.float32
    attn_impl = "sdpa" if device.type == "cuda" else None
    load_kwargs = {"attn_implementation": attn_impl, "trust_remote_code": True}
    try:
        # transformers 5.x 使用 dtype；旧版本回退 torch_dtype
        model = AutoModel.from_pretrained(args.model, dtype=torch_dtype, **load_kwargs)
    except TypeError:
        model = AutoModel.from_pretrained(args.model, torch_dtype=torch_dtype, **load_kwargs)
    model.to(device)

    # 梯度检查点
    try:
        model.gradient_checkpointing_enable()
        if hasattr(model, "config"):
            model.config.use_cache = False
        print("已成功开启 gradient_checkpointing")
    except Exception as e:
        print(f"未能开启 gradient_checkpointing: {e}")

    # 10. LoRA（all-linear）或断点恢复
    resumed = False
    if args.resume and adapter_dir.exists():
        print(f"正在从已存在的 adapter 恢复: {adapter_dir}")
        model = PeftModel.from_pretrained(model, str(adapter_dir), is_trainable=True)
        resumed = True
    else:
        peft_config = LoraConfig(
            task_type=None,
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            bias="none",
            target_modules="all-linear",
        )
        try:
            model = get_peft_model(model, peft_config)
            print("LoRA 已挂载 (target_modules='all-linear')")
        except Exception as e:
            print(f"警告: all-linear 挂载失败 ({e})，正在回退到标准投影矩阵...")
            peft_config.target_modules = [
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ]
            model = get_peft_model(model, peft_config)
            print(f"LoRA 已挂载 (target_modules={peft_config.target_modules})")
    model.print_trainable_parameters()

    # gradient checkpointing + PEFT：确保 embedding 输出携带梯度
    try:
        if hasattr(model, "enable_input_require_grads"):
            model.enable_input_require_grads()
            print("已启用 enable_input_require_grads")
    except Exception as e:
        print(f"enable_input_require_grads 失败 ({e})，尝试 forward hook 兜底")
        try:
            emb = model.get_input_embeddings()
            emb.register_forward_hook(lambda module, inputs, output: output.requires_grad_(True))
        except Exception as e2:
            print(f"forward hook 兜底也失败: {e2}（LoRA 梯度可能无法回传，请检查）")

    # 11. DecisionScorer（base + pointer head；resume 时载入 head 权重）
    scorer = DecisionScorer(model).to(device)
    print(f"DecisionScorer: hidden_size={scorer.hidden_size}, "
          f"head 参数量={sum(p.numel() for p in scorer.pointer_head.parameters())}")
    if args.resume and head_path.exists():
        config = load_scorer_head(scorer.pointer_head, str(head_path))
        print(f"已从 {head_path} 恢复 pointer head（config: {config}）")

    # 12. 优化器（head lr 可倍率）与调度器
    head_params = [p for p in scorer.pointer_head.parameters() if p.requires_grad]
    base_trainable = [p for p in scorer.base.parameters() if p.requires_grad]
    optimizer = AdamW(
        [
            {"params": base_trainable, "lr": args.lr},
            {"params": head_params, "lr": args.lr * args.head_lr_mult},
        ],
        weight_decay=0.01,
    )

    steps_per_epoch = max(1, len(train_loader) // args.grad_accum)
    if args.max_steps > 0:
        total_training_steps = args.max_steps
    else:
        total_training_steps = steps_per_epoch * args.epochs
    warmup_steps = max(1, int(total_training_steps * 0.03))
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_training_steps,
    )
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    # 13. 训练主循环
    print("\n开始训练...")
    global_step = 0
    accum_loss = 0.0
    accum_count = 0
    start_time = time.time()
    eval_history = []
    step_records = []

    scorer.train()
    optimizer.zero_grad()

    stop_training = False
    for epoch in range(1, args.epochs + 1):
        if stop_training:
            break
        if args.shuffle_options and epoch > 1:
            print(f"[Epoch {epoch}] 重新打乱选项顺序并重建样本（--shuffle-options）...")
            dataset.rebuild(shuffle=True)
        print(f"\n--- Epoch {epoch}/{args.epochs} ---")
        epoch_start_time = time.time()

        for batch_idx, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            marker_positions = batch["marker_positions"].to(device)
            option_mask = batch["option_mask"].to(device)
            answer_idx = batch["answer_idx"].to(device)
            soft = batch["soft"].to(device)
            has_soft = batch["has_soft"].to(device)

            with _autocast_context(device):
                logits = scorer(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    marker_positions=marker_positions,
                )
                per_row = masked_mixed_loss(
                    logits, answer_idx, soft, option_mask, has_soft,
                    lambda_soft=args.lambda_soft, temperature=args.soft_temperature,
                )
                loss = per_row.mean() / args.grad_accum

            scaler.scale(loss).backward()
            accum_loss += loss.item() * args.grad_accum
            accum_count += 1

            if (batch_idx + 1) % args.grad_accum == 0 or (batch_idx + 1) == len(train_loader):
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
                scheduler.step()
                global_step += 1

                avg_loss = accum_loss / max(1, accum_count)
                accum_loss = 0.0
                accum_count = 0
                current_lr = scheduler.get_last_lr()[0]

                peak_vram_mb = 0.0
                if device.type == "cuda":
                    peak_vram_mb = torch.cuda.max_memory_allocated() / (1024**2)

                if global_step % 10 == 0 or global_step == 1:
                    print(
                        f"Step {global_step}/{total_training_steps} | "
                        f"Loss: {avg_loss:.4f} | LR: {current_lr:.2e} | "
                        f"VRAM: {peak_vram_mb:.1f}MB | "
                        f"Elapsed: {time.time() - start_time:.1f}s"
                    )

                step_records.append({
                    "step": global_step,
                    "loss": round(avg_loss, 4),
                    "lr": current_lr,
                    "peak_vram_mb": round(peak_vram_mb, 1),
                })

                # 周期评测（题内 argmax accuracy 分层）
                if eval_view_path and (global_step % args.eval_every == 0):
                    print(f"\n[Eval @ Step {global_step}] 正在运行验证集评测 (采样上限 {args.eval_limit})...")
                    eval_res = evaluate_scorer_accuracy(
                        scorer=scorer,
                        eval_view_path=eval_view_path,
                        tokenizer=tokenizer,
                        device=device,
                        limit=args.eval_limit,
                        batch_size=max(1, args.batch_size),
                        seq_len=args.seq_len,
                        lambda_soft=args.lambda_soft,
                        soft_temperature=args.soft_temperature,
                    )
                    eval_res["step"] = global_step
                    eval_res["epoch"] = epoch
                    eval_history.append(eval_res)
                    print(f"[Eval @ Step {global_step}] 整体准确率: {eval_res.get('accuracy', 0.0):.4f} "
                          f"(总样本: {eval_res.get('total', 0)}, mean_nll: {eval_res.get('mean_nll', 0.0):.4f})")
                    print(f"  by_kind: {eval_res.get('by_kind')}")
                    print(f"  by_lang: {eval_res.get('by_lang')}")

                if args.max_steps > 0 and global_step >= args.max_steps:
                    stop_training = True
                    break

        print(f"Epoch {epoch} 耗时: {time.time() - epoch_start_time:.1f}s")

    total_duration = time.time() - start_time
    peak_vram_final = 0.0
    if device.type == "cuda":
        peak_vram_final = torch.cuda.max_memory_allocated() / (1024**2)

    # 14. 保存 adapter / scorer_head.pt / tokenizer
    print(f"\n训练完成，正在保存产物至: {output_dir}")
    adapter_dir.mkdir(parents=True, exist_ok=True)
    scorer.base.save_pretrained(str(adapter_dir))

    head_config = {
        "hidden_size": scorer.hidden_size,
        "template_version": TRACK_B_TEMPLATE_VERSION,
        "marker_scheme": MARKER_SCHEME_INFO,
        "max_options": MAX_OPTIONS,
        "model_base": args.model,
    }
    save_scorer_head(scorer.pointer_head, head_path, config=head_config)
    print(f"  adapter -> {adapter_dir}")
    print(f"  scorer_head.pt -> {head_path}")

    tokenizer_dir.mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(str(tokenizer_dir))
    print(f"  tokenizer -> {tokenizer_dir}")

    # 15. 训练清单
    manifest = {
        "status": "completed",
        "track": "B",
        "model_base": args.model,
        "template_version": TRACK_B_TEMPLATE_VERSION,
        "marker_scheme": MARKER_SCHEME_INFO,
        "git_commit": git_commit,
        "config": vars(args),
        "data": {
            "train_view": str(train_view_path),
            "train_sha256": train_sha256,
            "eval_view": str(eval_view_path) if eval_view_path else None,
            "eval_sha256": eval_sha256,
            "dataset_stats": dataset.stats,
            "train_sample_count": len(dataset),
        },
        "training_summary": {
            "total_steps": global_step,
            "total_duration_seconds": round(total_duration, 2),
            "peak_vram_mb": round(peak_vram_final, 1),
            "final_lr": scheduler.get_last_lr()[0] if scheduler else 0.0,
            "random_seed": args.seed,
            "resumed_from_adapter": resumed,
        },
        "eval_history": eval_history,
        "recent_step_records": step_records[-50:],
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  train-manifest.json -> {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
