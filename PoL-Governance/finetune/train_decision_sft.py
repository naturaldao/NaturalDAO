#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track A: 决策模型单 token 字母选择 SFT 训练脚本 (finetune/train_decision_sft.py)

功能：
- 基于 Qwen3-1.7B (或其他因果语言模型) + LoRA 微调
- 仅优化封闭选择（noul / choice / score）的选项字母预测 (A..Z)
- completion-only 标签（prompt 部分 -100）
- 支持纯 CPU dry-run、显存与步骤记录、断点续跑、训练清单 (train-manifest.json)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 引入项目通用决策与安全护栏模块
try:
    from finetune.decision_common import (
        INDEX_TO_LETTER,
        LETTER_TO_INDEX,
        LETTERS,
        MAX_OPTIONS,
        SimpleStubTokenizer,
        build_completion_only_sample,
        check_output_dir_guard,
        compute_file_sha256,
        compute_stratified_metrics,
        format_prompt_and_answer,
        get_git_commit,
    )
except ImportError:
    # 允许直接在 finetune/ 目录下执行 python train_decision_sft.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from finetune.decision_common import (
        INDEX_TO_LETTER,
        LETTER_TO_INDEX,
        LETTERS,
        MAX_OPTIONS,
        SimpleStubTokenizer,
        build_completion_only_sample,
        check_output_dir_guard,
        compute_file_sha256,
        compute_stratified_metrics,
        format_prompt_and_answer,
        get_git_commit,
    )

# 动态加载深度学习依赖，以便在无 torch 环境下仍可通过 py_compile 和 dry-run 数据校验
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.optim import AdamW
    from torch.utils.data import DataLoader, Dataset
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        get_cosine_schedule_with_warmup,
    )
    from peft import LoraConfig, PeftModel, get_peft_model
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


def unwrap_causal_lm(model: Any) -> Optional[Any]:
    """取 LoRA 包装内部的因果 LM（供只计算末位 token 的轻量损失使用）。"""
    if hasattr(model, "base_model") and hasattr(model.base_model, "model"):
        inner = model.base_model.model
        if hasattr(inner, "lm_head") and hasattr(inner, "model"):
            return inner
    if hasattr(model, "lm_head") and hasattr(model, "model"):
        return model
    return None


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track A 决策模型 SFT 训练脚本 (Qwen3 + LoRA 字母选择)"
    )
    # 数据与模型路径
    parser.add_argument(
        "--train-view",
        type=str,
        required=True,
        help="训练视图 JSONL 路径 (例如 general-train-view.jsonl)",
    )
    parser.add_argument(
        "--eval-view",
        type=str,
        default=None,
        help="评测视图 JSONL 路径 (例如 general-validation-view.jsonl)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen3-1.7B",
        help="底座模型名称或本地路径 (默认 Qwen/Qwen3-1.7B)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="训练产物输出目录 (必须在仓库外，例如 D:/pol2-train/runs/track-a-1.7b)",
    )

    # 训练超参数
    parser.add_argument("--epochs", type=int, default=2, help="训练轮数 (默认 2)")
    parser.add_argument("--batch-size", type=int, default=4, help="单步微批次大小 (默认 4)")
    parser.add_argument(
        "--grad-accum", type=int, default=8, help="梯度累积步数 (默认 8，有效批次 32)"
    )
    parser.add_argument("--lr", type=float, default=1e-4, help="AdamW 学习率 (默认 1e-4)")
    parser.add_argument(
        "--seq-len", type=int, default=1536, help="最大序列长度 (默认 1536)"
    )
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank (默认 16)")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha (默认 32)")
    parser.add_argument(
        "--lora-dropout", type=float, default=0.05, help="LoRA dropout (默认 0.05)"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=0,
        help="最大训练步数 (0 表示按 epoch 循环，默认 0)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="限制训练集加载行数 (0 表示无限制，调试用)",
    )
    parser.add_argument(
        "--eval-limit",
        type=int,
        default=500,
        help="周期评测采样的最大验证行数 (默认 500)",
    )
    parser.add_argument(
        "--eval-every",
        type=int,
        default=200,
        help="每隔多少 step 运行一次周期评测 (默认 200)",
    )
    parser.add_argument(
        "--seed", type=int, default=20261023, help="全局随机种子 (默认 20261023)"
    )

    # 控制开关
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅加载并校验数据与 batch，打印前 3 条样本，不加载模型不训练",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="从 output-dir 已有检查点恢复训练",
    )
    parser.add_argument(
        "--no-grad-ckpt",
        action="store_true",
        help="关闭 gradient checkpointing（显存足够时可提速）",
    )

    return parser.parse_args(argv)


class DecisionDataset:
    """封装决策数据视图的解析与样本构造。"""

    def __init__(
        self,
        jsonl_path: Path,
        tokenizer: Any,
        seq_len: int = 1536,
        limit: int = 0,
    ):
        self.jsonl_path = jsonl_path
        self.tokenizer = tokenizer
        self.seq_len = seq_len
        self.limit = limit

        self.samples: List[Dict[str, Any]] = []
        self.stats = {
            "total_read": 0,
            "valid": 0,
            "skipped_options_gt_26": 0,
            "skipped_invalid_answer_idx": 0,
            "skipped_missing_prompt": 0,
            "skipped_missing_options": 0,
            "skipped_non_single_token_answer": 0,
            "skipped_seq_len_too_short": 0,
        }

        self._load_and_process()

    def _load_and_process(self):
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

                prompt_prefix, letter, skip_reason = format_prompt_and_answer(row)
                if skip_reason:
                    key = f"skipped_{skip_reason}"
                    if key in self.stats:
                        self.stats[key] += 1
                    continue

                # 编码 prompt 与 answer
                if hasattr(self.tokenizer, "encode"):
                    prompt_ids = self.tokenizer.encode(prompt_prefix, add_special_tokens=True)
                    # 为确保字母 token 的单 token 特征，对包含换行与答案字母的完整串作编码
                    full_text = prompt_prefix + letter
                    full_ids = self.tokenizer.encode(full_text, add_special_tokens=True)
                    answer_ids = full_ids[len(prompt_ids):]
                    if len(answer_ids) != 1:
                        # 尝试直接对单个字母编码
                        letter_ids = self.tokenizer.encode(letter, add_special_tokens=False)
                        if len(letter_ids) == 1:
                            answer_ids = letter_ids
                        else:
                            self.stats["skipped_non_single_token_answer"] += 1
                            continue
                else:
                    self.stats["skipped_non_single_token_answer"] += 1
                    continue

                input_ids, labels, err = build_completion_only_sample(
                    prompt_ids, answer_ids, self.seq_len
                )
                if err:
                    key = f"skipped_{err}"
                    if key in self.stats:
                        self.stats[key] += 1
                    continue

                self.samples.append({
                    "rid": row.get("rid", f"row_{line_idx}"),
                    "kind": row.get("kind", "choice"),
                    "lang": row.get("lang", "zh"),
                    "route": row.get("route", "classification"),
                    "prompt_prefix": prompt_prefix,
                    "letter": letter,
                    "input_ids": input_ids,
                    "labels": labels,
                    "raw_row": row,
                })
                self.stats["valid"] += 1

                if self.limit > 0 and len(self.samples) >= self.limit:
                    break

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.samples[idx]


def collate_fn(batch: List[Dict[str, Any]], pad_token_id: int) -> Dict[str, Any]:
    """批量对齐 collate 函数，对 input_ids 填充 pad_token_id，对 labels 填充 -100。"""
    max_len = max(len(x["input_ids"]) for x in batch)
    batch_input_ids = []
    batch_labels = []
    batch_attention_mask = []

    for item in batch:
        inp = item["input_ids"]
        lbl = item["labels"]
        pad_len = max_len - len(inp)

        # 右侧 padding
        padded_inp = inp + [pad_token_id] * pad_len
        padded_lbl = lbl + [-100] * pad_len
        attn_mask = [1] * len(inp) + [0] * pad_len

        batch_input_ids.append(padded_inp)
        batch_labels.append(padded_lbl)
        batch_attention_mask.append(attn_mask)

    if torch is not None:
        return {
            "input_ids": torch.tensor(batch_input_ids, dtype=torch.long),
            "labels": torch.tensor(batch_labels, dtype=torch.long),
            "attention_mask": torch.tensor(batch_attention_mask, dtype=torch.long),
            "rids": [x["rid"] for x in batch],
        }
    return {
        "input_ids": batch_input_ids,
        "labels": batch_labels,
        "attention_mask": batch_attention_mask,
        "rids": [x["rid"] for x in batch],
    }


def evaluate_letter_accuracy(
    model: Any,
    tokenizer: Any,
    eval_view_path: Path,
    device: Any,
    limit: int = 500,
) -> Dict[str, Any]:
    """在验证集上采样评测单字母预测准确率。"""
    if not eval_view_path.exists():
        return {}

    eval_records: List[Dict[str, Any]] = []
    model.eval()

    # 预计算大写字母 A..Z 的首 token id
    letter_token_map: Dict[str, int] = {}
    for letter in LETTERS:
        encoded = tokenizer.encode(letter, add_special_tokens=False)
        if encoded:
            letter_token_map[letter] = encoded[0]

    with open(eval_view_path, "r", encoding="utf-8") as f:
        count = 0
        for line in f:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue

            prompt_prefix, gold_letter, skip_reason = format_prompt_and_answer(row)
            if skip_reason:
                continue

            options = row.get("options", [])
            candidate_letters = [INDEX_TO_LETTER[i] for i in range(len(options))]
            cand_token_ids = [letter_token_map[l] for l in candidate_letters if l in letter_token_map]
            if len(cand_token_ids) != len(candidate_letters):
                continue

            prompt_ids = tokenizer.encode(prompt_prefix, add_special_tokens=True)
            inp_tensor = torch.tensor([prompt_ids], dtype=torch.long, device=device)

            with torch.no_grad():
                with torch.amp.autocast(device_type=device.type, dtype=torch.float16, enabled=(device.type == "cuda")):
                    outputs = model(input_ids=inp_tensor)
                    # 取末位 prompt token 的 logits
                    next_token_logits = outputs.logits[0, -1, :]
                    candidate_logits = next_token_logits[cand_token_ids]
                    pred_idx = torch.argmax(candidate_logits).item()
                    pred_letter = candidate_letters[pred_idx]

            eval_records.append({
                "rid": row.get("rid", f"row_{count}"),
                "kind": row.get("kind", "choice"),
                "lang": row.get("lang", "zh"),
                "num_options": len(options),
                "route": row.get("route", "classification"),
                "correct": (pred_letter == gold_letter),
                "gold_letter": gold_letter,
                "pred_letter": pred_letter,
            })

            count += 1
            if limit > 0 and count >= limit:
                break

    model.train()
    return compute_stratified_metrics(eval_records)


def run_dry_run(args: argparse.Namespace) -> int:
    """执行 dry-run 验证流程：检查数据、构建 batch、打印首 3 条样本，不加载模型。"""
    print("=" * 60)
    print("[DRY-RUN] 开启 Track A 数据校验与样本形状检查")
    print(f"  训练数据: {args.train_view}")
    print(f"  模型基座: {args.model}")
    print(f"  最大长: {args.seq_len}")
    print("=" * 60)

    # 尝试加载真实 Tokenizer，若失败/无依赖则回退至 SimpleStubTokenizer
    tokenizer = None
    if TORCH_AVAILABLE:
        try:
            tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            print(f"[DRY-RUN] 成功加载 AutoTokenizer: {args.model}")
        except Exception as e:
            print(f"[DRY-RUN] 无法加载 AutoTokenizer ({e})，使用 SimpleStubTokenizer 模拟")
            tokenizer = SimpleStubTokenizer()
    else:
        print("[DRY-RUN] 当前 Python 环境未安装 transformers，使用 SimpleStubTokenizer")
        tokenizer = SimpleStubTokenizer()

    train_path = Path(args.train_view)
    dataset = DecisionDataset(
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

    print("\n[DRY-RUN] 前 3 条样本结构检验:")
    show_count = min(3, len(dataset))
    for i in range(show_count):
        item = dataset[i]
        prompt_tail = item["prompt_prefix"][-120:].replace("\n", "\\n")
        lbl_non_ignore = sum(1 for x in item["labels"] if x != -100)
        print(f"\n--- 样本 #{i+1} (rid: {item['rid']}) ---")
        print(f"  Kind/Lang: {item['kind']} / {item['lang']}")
        print(f"  Prompt 尾部: ...{prompt_tail}")
        print(f"  答案字母: {item['letter']}")
        print(f"  Input IDs 长度: {len(item['input_ids'])}")
        print(f"  Labels 长度: {len(item['labels'])} (有效预测标签数: {lbl_non_ignore}, 最后一个 token 标签: {item['labels'][-1]})")

    # 模拟构建 1 个批次
    batch_size = min(args.batch_size, len(dataset))
    sub_batch = [dataset[i] for i in range(batch_size)]
    batch_collated = collate_fn(sub_batch, pad_token_id=getattr(tokenizer, "pad_token_id", 0) or 0)

    if TORCH_AVAILABLE and isinstance(batch_collated["input_ids"], torch.Tensor):
        print(f"\n[DRY-RUN] 模拟批次形状: input_ids={batch_collated['input_ids'].shape}, labels={batch_collated['labels'].shape}")
    else:
        print(f"\n[DRY-RUN] 模拟批次样本数: {len(batch_collated['input_ids'])}, 批次最大长度: {len(batch_collated['input_ids'][0])}")

    print("\n[DRY-RUN] 校验通过！未加载模型权重，未进行任何 GPU 训练计算。")
    print("=" * 60)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    # 1. 严格检查输出目录护栏（必须在仓库外，否则 exit 2）
    output_dir = check_output_dir_guard(args.output_dir)

    # 2. 检查输入数据文件
    train_view_path = Path(args.train_view)
    if not train_view_path.exists():
        sys.stderr.write(f"Error: 训练集文件不存在: {train_view_path}\n")
        return 1

    eval_view_path = Path(args.eval_view) if args.eval_view else None
    if eval_view_path and not eval_view_path.exists():
        sys.stderr.write(f"Error: 验证集文件不存在: {eval_view_path}\n")
        return 1

    # 3. Dry-Run 模式优先处理
    if args.dry_run:
        return run_dry_run(args)

    # 4. 正常训练依赖检查
    if not TORCH_AVAILABLE:
        sys.stderr.write(
            "Error: 当前环境未安装 torch / transformers / peft！\n"
            "真实训练请使用 Lead 预先配置好的虚拟环境 (例如 D:/pol2-train/.venv)。\n"
        )
        return 1

    # 5. 设置随机种子
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir = output_dir / "adapter"
    manifest_path = output_dir / "train-manifest.json"

    # 6. 计算输入数据校验和与初始清单信息
    train_sha256 = compute_file_sha256(train_view_path)
    eval_sha256 = compute_file_sha256(eval_view_path) if eval_view_path else "none"
    git_commit = get_git_commit()

    print("=" * 60)
    print("PoL-Governance Track A: Qwen3-1.7B 决策模型 SFT 训练")
    print(f"  Git Commit: {git_commit}")
    print(f"  Train View: {train_view_path} (SHA256: {train_sha256[:12]}...)")
    print(f"  Eval View:  {eval_view_path} (SHA256: {eval_sha256[:12]}...)")
    print(f"  Output Dir: {output_dir}")
    print(f"  Epochs: {args.epochs}, Batch Size: {args.batch_size}, Grad Accum: {args.grad_accum}")
    print(f"  Seq Len: {args.seq_len}, LR: {args.lr}, LoRA r: {args.lora_r}")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"运行设备: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}, 总显存: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")

    # 7. 加载 Tokenizer
    print("正在加载 Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # 8. 加载并构建训练数据集
    print("正在解析与编码训练数据...")
    dataset = DecisionDataset(
        jsonl_path=train_view_path,
        tokenizer=tokenizer,
        seq_len=args.seq_len,
        limit=args.limit,
    )
    print(f"有效训练样本数: {len(dataset)}，过滤统计: {dataset.stats}")
    if len(dataset) == 0:
        sys.stderr.write("Error: 没有有效样本可用于训练！\n")
        return 1

    train_loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.pad_token_id),
    )

    # 9. 加载模型与配置 LoRA
    print(f"正在加载基座模型: {args.model}...")
    torch_dtype = torch.float16 if device.type == "cuda" else torch.float32
    attn_impl = "sdpa" if device.type == "cuda" else None

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch_dtype,
        attn_implementation=attn_impl,
        trust_remote_code=True,
    )
    model.to(device)

    # 开启梯度检查点节省显存（--no-grad-ckpt 可关闭以提速）
    if getattr(args, "no_grad_ckpt", False):
        print("已按 --no-grad-ckpt 关闭 gradient_checkpointing")
    else:
        try:
            model.gradient_checkpointing_enable()
            print("已成功开启 gradient_checkpointing")
        except Exception as e:
            print(f"未能开启 gradient_checkpointing: {e}")

    # 配置 LoRA
    if args.resume and adapter_dir.exists():
        print(f"正在从已存在的 adapter 恢复: {adapter_dir}")
        model = PeftModel.from_pretrained(model, str(adapter_dir), is_trainable=True)
    else:
        peft_config = LoraConfig(
            task_type="CAUSAL_LM",
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

    # 10. 优化器与学习率调度器
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = AdamW(trainable_params, lr=args.lr, weight_decay=0.01)

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

    # 11. 训练主循环
    print("\n开始训练...")
    global_step = 0
    accum_loss = 0.0
    accum_count = 0
    start_time = time.time()
    eval_history = []
    step_records = []

    model.train()
    optimizer.zero_grad()

    stop_training = False
    for epoch in range(1, args.epochs + 1):
        if stop_training:
            break
        print(f"\n--- Epoch {epoch}/{args.epochs} ---")
        epoch_start_time = time.time()

        for batch_idx, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            attention_mask = batch["attention_mask"].to(device)

            with torch.amp.autocast(device_type=device.type, dtype=torch.float16, enabled=(device.type == "cuda")):
                # 轻量损失：本任务每个样本只在最后一个 token 有监督标签；直接对该位置过 lm_head，
                # 避免计算 [B, L, vocab] 全量 logits（ROCm/CUDA 上可省 10-100x 显存与大量算力）。
                base_lm = unwrap_causal_lm(model)
                seq_lens = attention_mask.sum(dim=1) - 1
                prev_positions = seq_lens - 1
                row_idx = torch.arange(labels.size(0), device=labels.device)
                targets = labels[row_idx, seq_lens]
                supervised = (labels != -100).sum(dim=1)
                lean_ok = bool(
                    base_lm is not None
                    and torch.all(targets != -100)
                    and torch.all(supervised == 1)
                    and torch.all(prev_positions >= 0)
                )
                if lean_ok:
                    hidden = base_lm.model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        use_cache=False,
                    ).last_hidden_state
                    # 因果 LM：位置 t 的 logits 预测 token t+1；监督标签在末位 token 上，
                    # 因此取倒数第二个位置的 hidden（绝不能取标签自身位置，否则是标签泄漏）。
                    prev_hidden = hidden[row_idx, prev_positions]
                    vocab_logits = base_lm.lm_head(prev_hidden)
                    loss = F.cross_entropy(vocab_logits.float(), targets) / args.grad_accum
                else:
                    outputs = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels,
                    )
                    loss = outputs.loss / args.grad_accum

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

                # 显存监控
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

                # 周期评测
                if eval_view_path and (global_step % args.eval_every == 0):
                    print(f"\n[Eval @ Step {global_step}] 正在运行验证集评测 (采样上限 {args.eval_limit})...")
                    eval_res = evaluate_letter_accuracy(
                        model=model,
                        tokenizer=tokenizer,
                        eval_view_path=eval_view_path,
                        device=device,
                        limit=args.eval_limit,
                    )
                    eval_res["step"] = global_step
                    eval_res["epoch"] = epoch
                    eval_history.append(eval_res)
                    print(f"[Eval @ Step {global_step}] 整体准确率: {eval_res.get('accuracy', 0.0):.4f} (总样本: {eval_res.get('total', 0)})")
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

    # 12. 保存 LoRA Adapter 与 Tokenizer
    print(f"\n训练完成，正在保存 adapter 至: {adapter_dir}")
    adapter_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))

    # 13. 写入训练清单 (train-manifest.json)
    manifest = {
        "status": "completed",
        "model_base": args.model,
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
        },
        "eval_history": eval_history,
        "recent_step_records": step_records[-50:],
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"训练清单已写入: {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
