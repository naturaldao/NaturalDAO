"""决策模型概率校准（温度缩放）与评测。

输入是 finetune/eval_decision.py --predictions 导出的逐行预测 JSONL（每行含 candidate_probs），
只用标准库：拟合温度 T、在指定半区上报告 NLL / Brier / ECE / MCE / 准确率。

用法：
    python finetune/calibrate.py fit --predictions preds.jsonl --out temperature.json
    python finetune/calibrate.py apply --predictions preds.jsonl --temperature 1.7 --json

评测协议见 EVAL-PROTOCOL.md §2.1/§3.2：validation 按 sha256(rid) 奇偶固定切半，
calibration 半只用于拟合温度，selection 半用于复算指标。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

EPS = 1e-12
ECE_BINS = 15


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rid_half(rid: str) -> str:
    """确定性半区：'calibration'（sha256 奇）或 'selection'（偶）。"""
    value = int(sha256_hex(rid), 16)
    return "calibration" if value % 2 else "selection"


def read_predictions(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{number}: invalid JSON: {error}") from error
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{number}: each line must be an object")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no predictions")
    return rows


def candidate_distribution(row: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """返回归一化的候选分布；缺失/非法返回 None。"""
    probs = row.get("candidate_probs")
    if not isinstance(probs, dict) or len(probs) < 2:
        return None
    values: Dict[str, float] = {}
    for letter, value in probs.items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(number) or number < 0:
            return None
        values[str(letter)] = number
    total = sum(values.values())
    if total <= 0:
        return None
    return {letter: value / total for letter, value in values.items()}


def _gold(row: Dict[str, Any]) -> Optional[str]:
    gold = row.get("gold_letter")
    return str(gold) if gold is not None else None


def scaled_probs(probs: Dict[str, float], temperature: float) -> Dict[str, float]:
    if temperature <= 0:
        raise ValueError("temperature must be > 0")
    if abs(temperature - 1.0) < 1e-12:
        return dict(probs)
    logs = {letter: math.log(max(value, EPS)) / temperature for letter, value in probs.items()}
    peak = max(logs.values())
    exps = {letter: math.exp(value - peak) for letter, value in logs.items()}
    total = sum(exps.values())
    return {letter: value / total for letter, value in exps.items()}


def temperature_nll(rows: Sequence[Dict[str, Any]], temperature: float) -> Tuple[float, int]:
    total = 0.0
    count = 0
    for row in rows:
        probs = candidate_distribution(row)
        gold = _gold(row)
        if probs is None or gold is None or gold not in probs:
            continue
        scaled = scaled_probs(probs, temperature)
        total -= math.log(max(scaled.get(gold, EPS), EPS))
        count += 1
    if count == 0:
        raise ValueError("no usable rows for calibration")
    return total / count, count


def fit_temperature(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    usable = [row for row in rows if candidate_distribution(row) is not None
              and _gold(row) in (candidate_distribution(row) or {})]
    if not usable:
        raise ValueError("no usable rows for calibration")
    # log-space 粗网格 + 局部黄金分割细化（纯标准库，确定性）
    logs = [math.log(0.05) + i * (math.log(10.0) - math.log(0.05)) / 200 for i in range(201)]
    best = min(logs, key=lambda value: temperature_nll(usable, math.exp(value))[0])
    lo, hi = best - 0.02, best + 0.02
    phi = (math.sqrt(5.0) - 1.0) / 2.0
    for _ in range(60):
        mid1 = hi - phi * (hi - lo)
        mid2 = lo + phi * (hi - lo)
        if temperature_nll(usable, math.exp(mid1))[0] < temperature_nll(usable, math.exp(mid2))[0]:
            hi = mid2
        else:
            lo = mid1
    temperature = math.exp((lo + hi) / 2.0)
    nll, count = temperature_nll(usable, temperature)
    return {"temperature": round(temperature, 6), "nll": round(nll, 6), "rows": count}


def ece_bins(confidences: Sequence[float], correct: Sequence[bool], bins: int = ECE_BINS) -> List[Dict[str, float]]:
    if len(confidences) != len(correct):
        raise ValueError("confidence/correct length mismatch")
    buckets = []
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        members = [i for i, value in enumerate(confidences)
                   if (lower <= value < upper) or (index == bins - 1 and value == 1.0)]
        if not members:
            buckets.append({"bin": index, "count": 0, "avg_confidence": 0.0,
                            "accuracy": 0.0, "gap": 0.0})
            continue
        confidence = sum(confidences[i] for i in members) / len(members)
        accuracy = sum(1.0 for i in members if correct[i]) / len(members)
        buckets.append({"bin": index, "count": len(members),
                        "avg_confidence": confidence, "accuracy": accuracy,
                        "gap": abs(confidence - accuracy)})
    return buckets


def evaluate(rows: Sequence[Dict[str, Any]], temperature: float) -> Dict[str, Any]:
    nll = 0.0
    brier = 0.0
    count = 0
    correct = 0
    confidences: List[float] = []
    correct_flags: List[bool] = []
    skipped = 0
    for row in rows:
        probs = candidate_distribution(row)
        gold = _gold(row)
        if probs is None or gold is None or gold not in probs:
            skipped += 1
            continue
        scaled = scaled_probs(probs, temperature)
        nll -= math.log(max(scaled[gold], EPS))
        brier += sum((value - (1.0 if letter == gold else 0.0)) ** 2
                     for letter, value in scaled.items())
        prediction = max(scaled.items(), key=lambda item: item[1])[0]
        is_correct = prediction == gold
        correct += 1 if is_correct else 0
        confidences.append(scaled[prediction])
        correct_flags.append(is_correct)
        count += 1
    if count == 0:
        raise ValueError("no usable rows for evaluation")
    buckets = ece_bins(confidences, correct_flags)
    ece = sum(bucket["count"] * bucket["gap"] for bucket in buckets) / count
    mce = max(bucket["gap"] for bucket in buckets) if buckets else 0.0
    return {
        "temperature": round(temperature, 6),
        "rows": count,
        "skipped": skipped,
        "accuracy": round(correct / count, 6),
        "nll": round(nll / count, 6),
        "brier": round(brier / count, 6),
        "ece": round(ece, 6),
        "mce": round(mce, 6),
        "bins": buckets,
    }


def filter_half(rows: Iterable[Dict[str, Any]], half: str) -> List[Dict[str, Any]]:
    if half == "all":
        return list(rows)
    if half not in ("calibration", "selection"):
        raise ValueError(f"unknown half: {half}")
    return [row for row in rows if rid_half(str(row.get("rid", ""))) == half]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    fit = sub.add_parser("fit", help="在 calibration 半区拟合温度")
    fit.add_argument("--predictions", type=Path, required=True)
    fit.add_argument("--out", type=Path, help="温度与 NLL 写到 JSON")
    fit.add_argument("--json", action="store_true")

    apply = sub.add_parser("apply", help="用给定温度在指定半区报告指标")
    apply.add_argument("--predictions", type=Path, required=True)
    apply.add_argument("--temperature", type=float, required=True)
    apply.add_argument("--half", choices=("calibration", "selection", "all"), default="selection")
    apply.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        rows = read_predictions(args.predictions)
        if args.command == "fit":
            result = fit_temperature(filter_half(rows, "calibration"))
            result["half"] = "calibration"
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps({**result, "predictions": str(args.predictions)},
                                               ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False) if args.json
                  else "temperature = {temperature} (nll={nll}, rows={rows})".format(**result))
            return 0
        subset = filter_half(rows, args.half)
        result = evaluate(subset, args.temperature)
        result["half"] = args.half
        print(json.dumps(result, ensure_ascii=False) if args.json
              else "temperature = {temperature} | rows={rows} | acc={accuracy} | "
                   "nll={nll} | brier={brier} | ece={ece}".format(**result))
        return 0
    except (ValueError, OSError) as error:
        print(f"calibrate failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
