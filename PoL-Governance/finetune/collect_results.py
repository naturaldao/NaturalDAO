"""把评测产物汇总成结果卡表格（纯 CPU / 纯标准库）。

支持两类输入：
- 决策评测 JSON：finetune/eval_decision.py --json 的输出；
- 通用能力（lm-eval）JSON：lm_eval --output_path 的输出（读取 results.<task> 下的 acc 指标）；
- 逐行预测 JSONL（可选）：用于 base vs tuned 的配对 bootstrap 置信区间。

示例：
    python finetune/collect_results.py \
        --eval-json base=evals/base-val.json --eval-json track-a=evals/track-a-val.json \
        --lm-eval-json base=evals/lm-eval-base.json --lm-eval-json tuned=evals/lm-eval-track-a.json \
        --preds base=evals/base-val-preds.jsonl --preds tuned=evals/track-a-val-preds.jsonl \
        --out results/summary.md
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

BOOTSTRAP_ROUNDS = 1000


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def read_predictions(path: Path) -> Dict[str, bool]:
    """读逐行预测，返回 rid -> 是否正确。"""
    result: Dict[str, bool] = {}
    with path.open("r", encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            rid = row.get("rid")
            correct = row.get("correct")
            if not isinstance(rid, str) or not isinstance(correct, bool):
                raise ValueError(f"{path}:{number}: need rid(str) and correct(bool)")
            result[rid] = correct
    if not result:
        raise ValueError(f"{path}: no predictions")
    return result


def paired_bootstrap(base: Dict[str, bool], tuned: Dict[str, bool],
                     rounds: int = BOOTSTRAP_ROUNDS, seed: int = 20261023,
                     alpha: float = 0.05) -> Dict[str, Any]:
    rids = sorted(set(base) & set(tuned))
    if len(rids) < 20:
        raise ValueError(f"too few paired rows: {len(rids)}")
    deltas = [int(tuned[rid]) - int(base[rid]) for rid in rids]
    observed = sum(deltas) / len(deltas)
    base_accuracy = sum(1 for rid in rids if base[rid]) / len(rids)
    tuned_accuracy = sum(1 for rid in rids if tuned[rid]) / len(rids)
    rng = random.Random(seed)
    samples = []
    for _ in range(rounds):
        total = 0
        for _ in range(len(deltas)):
            total += deltas[rng.randrange(len(deltas))]
        samples.append(total / len(deltas))
    samples.sort()
    lower = samples[int(rounds * alpha / 2)]
    upper = samples[int(rounds * (1 - alpha / 2)) - 1]
    return {
        "rows": len(deltas),
        "base_accuracy": base_accuracy,
        "tuned_accuracy": tuned_accuracy,
        "delta": observed,
        "ci95": [lower, upper],
        "rounds": rounds,
        "seed": seed,
    }


def _metric_block(row: Dict[str, Any], key: str) -> Dict[str, float]:
    block = row.get(key) or {}
    if not isinstance(block, dict):
        return {}
    return {str(name): float(value.get("accuracy", 0.0)) for name, value in block.items()
            if isinstance(value, dict) and "accuracy" in value}


def render_eval_table(entries: List[Tuple[str, Dict[str, Any]]]) -> str:
    if not entries:
        return ""
    columns = ["整体", "choice", "noul", "score", "en", "zh", "选项2", "选项3-4", "选项5-8", "选项9-26"]
    lines = ["| 决策评测 | " + " | ".join(columns) + " |", "|---|" + "---:|" * len(columns)]
    values: Dict[str, Dict[str, float]] = {}
    for label, row in entries:
        bucket = _metric_block(row, "by_option_bucket")
        current = {
            "整体": float(row.get("accuracy", 0.0)),
            "choice": _metric_block(row, "by_kind").get("choice", 0.0),
            "noul": _metric_block(row, "by_kind").get("noul", 0.0),
            "score": _metric_block(row, "by_kind").get("score", 0.0),
            "en": _metric_block(row, "by_lang").get("en", 0.0),
            "zh": _metric_block(row, "by_lang").get("zh", 0.0),
            "选项2": bucket.get("2", 0.0),
            "选项3-4": bucket.get("3-4", 0.0),
            "选项5-8": bucket.get("5-8", 0.0),
            "选项9-26": bucket.get("9-26", 0.0),
        }
        values[label] = current
        lines.append(f"| {label}（n={row.get('total', 0)}） | " +
                     " | ".join(f"{current[column]:.4f}" for column in columns) + " |")
    if len(entries) == 2:
        (base_label, _), (tuned_label, _) = entries
        deltas = [f"{values[tuned_label][column] - values[base_label][column]:+.4f}" for column in columns]
        lines.append(f"| 差值（{tuned_label} − {base_label}） | " + " | ".join(deltas) + " |")
    return "\n".join(lines)


def render_lm_eval_table(entries: List[Tuple[str, Dict[str, Any]]],
                         average_tasks: Optional[Sequence[str]] = None) -> str:
    if not entries:
        return ""
    rows: Dict[str, Dict[str, float]] = {}
    for label, payload in entries:
        results = payload.get("results") or {}
        if not isinstance(results, dict):
            continue
        metrics: Dict[str, float] = {}
        for task, values in results.items():
            if not isinstance(values, dict):
                continue
            for key in ("acc,none", "acc_norm,none"):
                if key in values:
                    try:
                        metrics[task] = float(values[key])
                    except (TypeError, ValueError):
                        pass
                    break
            else:
                for key, value in values.items():
                    if key.startswith("acc") and "," in key:
                        try:
                            metrics[task] = float(value)
                        except (TypeError, ValueError):
                            pass
                        break
        if average_tasks:
            picked = [metrics[task] for task in average_tasks if task in metrics]
        else:
            picked = list(metrics.values())
        if picked:
            metrics["__average__"] = sum(picked) / len(picked)
        rows[label] = metrics
    tasks = sorted({task for metrics in rows.values() for task in metrics})
    if not tasks:
        return ""
    lines = ["| 通用能力（lm-eval） | " + " | ".join(tasks) + " |",
             "|---|" + "---:|" * len(tasks)]
    for label, metrics in rows.items():
        lines.append(f"| {label} | " + " | ".join(
            f"{metrics[task]:.4f}" if task in metrics else "—" for task in tasks) + " |")
    if len(rows) == 2:
        labels = list(rows)
        base, tuned = rows[labels[0]], rows[labels[1]]
        deltas = [f"{tuned[task] - base[task]:+.4f}" if task in tuned and task in base else "—"
                  for task in tasks]
        lines.append(f"| 差值（{labels[1]} − {labels[0]}） | " + " | ".join(deltas) + " |")
    return "\n".join(lines)


def parse_assignments(values: Optional[Sequence[str]], flag: str) -> List[Tuple[str, Path]]:
    if not values:
        return []
    entries = []
    for value in values:
        if "=" not in value:
            raise ValueError(f"{flag} expects LABEL=PATH, got {value!r}")
        label, path = value.split("=", 1)
        entries.append((label, Path(path)))
    return entries


def build_markdown(args: argparse.Namespace) -> str:
    parts: List[str] = ["# 评测汇总", ""]
    eval_entries = [(label, load_json(path)) for label, path in
                    parse_assignments(args.eval_json, "--eval-json")]
    parts.append(render_eval_table(eval_entries))
    if eval_entries:
        parts.append("")
    lm_entries = [(label, load_json(path)) for label, path in
                  parse_assignments(args.lm_eval_json, "--lm-eval-json")]
    average_tasks = [task.strip() for task in args.lm_eval_average_tasks.split(",")
                     if task.strip()] if args.lm_eval_average_tasks else None
    parts.append(render_lm_eval_table(lm_entries, average_tasks))
    if lm_entries:
        parts.append("")
    preds = [(label, read_predictions(path)) for label, path in
             parse_assignments(args.preds, "--preds")]
    if len(preds) == 2:
        (base_label, base), (tuned_label, tuned) = preds
        stats = paired_bootstrap(base, tuned, rounds=args.bootstrap_rounds, seed=args.seed)
        stats["base_label"] = base_label
        stats["tuned_label"] = tuned_label
        parts.append("## 配对 bootstrap（decision accuracy）")
        parts.append("")
        parts.append(f"- {base_label}: {stats['base_accuracy']:.4f}"
                     f"（配对行 {stats['rows']}）")
        parts.append(f"- {tuned_label}: {stats['tuned_accuracy']:.4f}")
        parts.append(f"- 差值 {stats['delta']:+.4f}，95% CI "
                     f"[{stats['ci95'][0]:+.4f}, {stats['ci95'][1]:+.4f}]，"
                     f"{stats['rounds']} 次重采样，seed={stats['seed']}")
        parts.append("")
    parts.append("> 说明：本表由 finetune/collect_results.py 生成；"
                 "test 只做回归，结论口径见 finetune/EVAL-PROTOCOL.md。")
    return "\n".join(parts)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--eval-json", action="append", help="决策评测 LABEL=PATH（可重复）")
    parser.add_argument("--lm-eval-json", action="append", help="lm-eval LABEL=PATH（可重复）")
    parser.add_argument("--preds", action="append", help="逐行预测 LABEL=PATH（恰好两个时做配对 bootstrap）")
    parser.add_argument("--lm-eval-average-tasks", help="逗号分隔的任务名，用于均值（默认全部有 acc 的任务）")
    parser.add_argument("--bootstrap-rounds", type=int, default=BOOTSTRAP_ROUNDS)
    parser.add_argument("--seed", type=int, default=20261023)
    parser.add_argument("--out", type=Path, help="输出 markdown；省略则打印到 stdout")
    args = parser.parse_args(argv)
    try:
        markdown = build_markdown(args)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(markdown + "\n", encoding="utf-8")
            print(f"written: {args.out}")
        else:
            print(markdown)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"collect_results failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
