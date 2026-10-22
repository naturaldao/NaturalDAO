#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Track A: 决策模型单 token 字母选择评测脚本 (finetune/eval_decision.py)

功能：
- 加载 Base 语言模型（若无 --adapter 则评估 0-shot 基线）或 LoRA 微调模型
- 在指定决策视图 JSONL (如 general-test-view.jsonl / general-validation-view.jsonl) 上评测
- 计算整体 letter accuracy，并按 kind, lang, 选项数桶 (2, 3-4, 5-8, 9-26), route 分层统计
- 可选导出每行预测详情（--predictions 路径，必须在仓库外部）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# 引入项目通用决策与安全护栏模块
try:
    from finetune.decision_common import (
        INDEX_TO_LETTER,
        LETTER_TO_INDEX,
        LETTERS,
        MAX_OPTIONS,
        check_output_dir_guard,
        compute_stratified_metrics,
        format_prompt_and_answer,
        get_option_count_bucket,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from finetune.decision_common import (
        INDEX_TO_LETTER,
        LETTER_TO_INDEX,
        LETTERS,
        MAX_OPTIONS,
        check_output_dir_guard,
        compute_stratified_metrics,
        format_prompt_and_answer,
        get_option_count_bucket,
    )

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track A 决策模型评测脚本 (0-shot 基线 / LoRA 评测)"
    )
    parser.add_argument(
        "--eval-view",
        type=str,
        required=True,
        help="待评测视图 JSONL 路径 (例如 general-test-view.jsonl)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen3-1.7B",
        help="基座模型名称或本地路径 (默认 Qwen/Qwen3-1.7B)",
    )
    parser.add_argument(
        "--adapter",
        type=str,
        default=None,
        help="LoRA 权重目录 (可选，不提供时评测基座 0-shot 能力)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="评测样本数量上限 (0 表示全量评测)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="评测批次大小 (默认 8)",
    )
    parser.add_argument(
        "--predictions",
        type=str,
        default=None,
        help="输出逐行预测结果 JSONL 路径 (必须在仓库外，例如 D:/pol2-train/runs/.../preds.jsonl)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式向 stdout 输出汇总结果",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="推理设备 (auto/cuda/cpu，默认 auto)",
    )

    return parser.parse_args(argv)


def run_evaluation(args: argparse.Namespace) -> Dict[str, Any]:
    # 1. 护栏检查：如果指定了 predictions 文件，其输出目录必须不在仓库内
    if args.predictions:
        pred_path = Path(args.predictions)
        check_output_dir_guard(pred_path.parent)

    # 2. 检查依赖
    if not TORCH_AVAILABLE:
        sys.stderr.write(
            "Error: 当前环境未安装 torch / transformers / peft！\n"
            "真实评测请在装有推理环境的 Python 下运行 (例如 D:/pol2-train/.venv)。\n"
        )
        sys.exit(1)

    eval_view_path = Path(args.eval_view)
    if not eval_view_path.exists():
        sys.stderr.write(f"Error: 评测数据文件不存在: {eval_view_path}\n")
        sys.exit(1)

    # 3. 确定运行设备
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    if not args.json:
        print("=" * 60)
        print("PoL-Governance Track A 决策评测")
        print(f"  评测数据: {eval_view_path}")
        print(f"  基座模型: {args.model}")
        print(f"  LoRA Adapter: {args.adapter if args.adapter else '(None - 0-shot 基线)'}")
        print(f"  设备: {device}")
        print("=" * 60)

    # 4. 加载 Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    # 评测使用左侧填充，确保最后一个 token 的 logits 严格对齐在切片 index -1
    tokenizer.padding_side = "left"

    # 预计算字母 token id
    letter_token_map: Dict[str, int] = {}
    for letter in LETTERS:
        encoded = tokenizer.encode(letter, add_special_tokens=False)
        if encoded:
            letter_token_map[letter] = encoded[0]

    # 5. 加载模型
    torch_dtype = torch.float16 if device.type == "cuda" else torch.float32
    attn_impl = "sdpa" if device.type == "cuda" else None

    base_model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch_dtype,
        attn_implementation=attn_impl,
        trust_remote_code=True,
    )

    if args.adapter:
        if not args.json:
            print(f"正在加载 LoRA Adapter: {args.adapter}...")
        model = PeftModel.from_pretrained(base_model, args.adapter)
    else:
        model = base_model

    model.to(device)
    model.eval()

    # 6. 读取数据并批量评测
    records: List[Dict[str, Any]] = []
    skipped_stats = {
        "options_gt_26": 0,
        "invalid_answer_idx": 0,
        "missing_prompt": 0,
        "missing_options": 0,
        "token_map_mismatch": 0,
    }

    batch_items: List[Dict[str, Any]] = []

    def process_batch(batch: List[Dict[str, Any]]):
        if not batch:
            return

        prompts = [b["prompt_prefix"] for b in batch]
        encoded_inputs = tokenizer(
            prompts,
            padding=True,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            with torch.amp.autocast(device_type=device.type, dtype=torch.float16, enabled=(device.type == "cuda")):
                outputs = model(**encoded_inputs)
                # 获取每个序列最后一个 token 处的 logits: [batch_size, vocab_size]
                last_logits = outputs.logits[:, -1, :]

        for i, item in enumerate(batch):
            cand_token_ids = item["candidate_token_ids"]
            cand_letters = item["candidate_letters"]

            cand_logits = last_logits[i, cand_token_ids]
            probs = torch.softmax(cand_logits, dim=-1).tolist()
            pred_idx = torch.argmax(cand_logits).item()
            pred_letter = cand_letters[pred_idx]
            gold_letter = item["gold_letter"]
            is_correct = (pred_letter == gold_letter)

            prob_dist = {
                l: round(p, 4) for l, p in zip(cand_letters, probs)
            }

            records.append({
                "rid": item["rid"],
                "kind": item["kind"],
                "lang": item["lang"],
                "route": item["route"],
                "num_options": item["num_options"],
                "answer_idx": item["answer_idx"],
                "gold_letter": gold_letter,
                "pred_letter": pred_letter,
                "correct": is_correct,
                "candidate_probs": prob_dist,
            })

    start_time = time.time()
    total_evaluated = 0

    with open(eval_view_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue

            prompt_prefix, gold_letter, skip_reason = format_prompt_and_answer(row)
            if skip_reason:
                if skip_reason in skipped_stats:
                    skipped_stats[skip_reason] += 1
                continue

            options = row.get("options", [])
            cand_letters = [INDEX_TO_LETTER[i] for i in range(len(options))]
            cand_ids = [letter_token_map.get(l) for l in cand_letters]
            if any(cid is None for cid in cand_ids):
                skipped_stats["token_map_mismatch"] += 1
                continue

            batch_items.append({
                "rid": row.get("rid", f"row_{total_evaluated}"),
                "kind": row.get("kind", "choice"),
                "lang": row.get("lang", "zh"),
                "route": row.get("route", "classification"),
                "num_options": len(options),
                "answer_idx": row.get("answer_idx"),
                "gold_letter": gold_letter,
                "prompt_prefix": prompt_prefix,
                "candidate_letters": cand_letters,
                "candidate_token_ids": cand_ids,
            })

            total_evaluated += 1

            if len(batch_items) >= args.batch_size:
                process_batch(batch_items)
                batch_items = []
                if not args.json and total_evaluated % 100 == 0:
                    print(f"已评测: {total_evaluated} 条样本...")

            if args.limit > 0 and total_evaluated >= args.limit:
                break

        if batch_items:
            process_batch(batch_items)

    duration = time.time() - start_time
    metrics = compute_stratified_metrics(records)
    metrics["skipped_stats"] = skipped_stats
    metrics["duration_seconds"] = round(duration, 2)
    metrics["samples_per_second"] = round(total_evaluated / max(0.001, duration), 2)
    metrics["eval_view"] = str(eval_view_path)
    metrics["model"] = args.model
    metrics["adapter"] = args.adapter

    # 7. 导出预测详情
    if args.predictions:
        pred_p = Path(args.predictions)
        pred_p.parent.mkdir(parents=True, exist_ok=True)
        with open(pred_p, "w", encoding="utf-8") as pf:
            for rec in records:
                pf.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if not args.json:
            print(f"逐行预测详情已保存至: {pred_p}")

    # 8. 输出评测结果
    if args.json:
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 60)
        print("评测汇总报告")
        print("=" * 60)
        print(f"总样本数: {metrics['total']} | 正确数: {metrics['correct']} | 整体准确率: {metrics['accuracy']:.4f}")
        print(f"评测耗时: {metrics['duration_seconds']}s ({metrics['samples_per_second']} 样本/秒)")
        print("\n[按题型分层 (by_kind)]:")
        for k, v in metrics["by_kind"].items():
            print(f"  {k:10s}: {v['correct']}/{v['total']} ({v['accuracy']:.4f})")
        print("\n[按语言分层 (by_lang)]:")
        for l, v in metrics["by_lang"].items():
            print(f"  {l:10s}: {v['correct']}/{v['total']} ({v['accuracy']:.4f})")
        print("\n[按选项数分层 (by_option_bucket)]:")
        for b, v in metrics["by_option_bucket"].items():
            print(f"  {b:10s}: {v['correct']}/{v['total']} ({v['accuracy']:.4f})")
        print("\n[按路由分层 (by_route)]:")
        for r, v in metrics["by_route"].items():
            print(f"  {r:16s}: {v['correct']}/{v['total']} ({v['accuracy']:.4f})")
        print("\n[过滤统计]:", metrics["skipped_stats"])
        print("=" * 60)

    return metrics


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    run_evaluation(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
