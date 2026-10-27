"""最终评测聚合脚本（评测环境内运行）。

读取 base / tuned 两个模型的逐行预测 JSONL，按固定分层键汇总准确率、
Wilson 95% CI、paired bootstrap CI、校准指标，产出只含聚合数字的 JSON。

设计取舍：
- 分层键集合（kind/lang/option_bucket/route）硬编码为固定白名单，
  遇到未知值 exit 2（fail-closed），以发现视图 schema 变更。
- 校准函数全部复用 finetune.calibrate（candidate_distribution / scaled_probs /
  fit_temperature / evaluate / filter_half），不重新实现。
- 配对 bootstrap 复用 finetune.collect_results.paired_bootstrap（同算法同参数）。
- 输出中不含 rid / 任何逐例字段 / 列表型逐例数组。

增补 v2（spec「增补 v2」A/B/C）：
- paired.cluster：簇 = rid 中第一个 '#' 之前的前缀（无 '#' 用整条 rid；rid 缺失/非字符串
  → exit 2）。配对 group-cluster bootstrap：有放回抽 G 个簇，每簇存 [sum_delta, n]，
  每轮 Δ = Σsum_delta / Σn（按行加权，非簇等权）；--cluster-rounds 默认 10000，种子同 --seed；
  百分位 CI 下标 lower = samples[int(round(R*0.025))]，upper = samples[int(round(R*0.975)) - 1]。
  cluster_size_median / cluster_size_iqr 用线性插值分位数（numpy 默认 "linear"：
  位置 (n-1)*q，相邻两值线性插值），iqr = [q25, q75]；kish_neff = (Σn)^2 / Σn^2。
  reliability：G≥50 ok / 30≤G<50 cautious / G<30 low。主 CI 解释以 cluster.ci95 为准。
- paired.scope = "both_completed"：本轮无 --view（v3 ITT 未实现），主配对就是双方都完成的
  rid 交集；paired.completed_only 同集合，给出 ci95_item（collect_results.paired_bootstrap）
  与 ci95_group（簇 bootstrap），scope 同为 "both_completed"。
- models.*.accuracy = evaluated_accuracy = 完成子集 correct/evaluated；
  accuracy_with_missing = correct / expected_evaluated（主口径，缺行按错计）；
  coverage.models.*.completion_rate = evaluated / expected_evaluated。
- invalid 行（无 correct 且无 pred/gold，或 candidate_probs 非法）一律 exit 2；
  --allow-missing 只容忍「预测文件里缺行」。
- calibration.raw/calibrated：bins（calibrate.ece_bins 的 15 等宽箱，round 6）、
  low_sample_bins（count<20 的箱数）、low_sample_flag；ece_ci95_group 为按簇重采样的
  ECE 百分位 CI（--ece-cluster-rounds 默认 500，输出 ece_rounds）。

用法：
    python finetune/final_eval_aggregate.py \
      --preds base=/path/base-preds.jsonl --preds tuned=/path/tuned-preds.jsonl \
      --view-rows 6541 --out /path/aggregate.json

详见 .agent/notes/2026-10-27-final-eval-package-spec.md §1。
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------- 复用项目内模块 ----------
try:
    from finetune.calibrate import (
        ECE_BINS,
        candidate_distribution,
        evaluate as calibrate_evaluate,
        filter_half,
        fit_temperature,
        scaled_probs,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from finetune.calibrate import (
        ECE_BINS,
        candidate_distribution,
        evaluate as calibrate_evaluate,
        filter_half,
        fit_temperature,
        scaled_probs,
    )

try:
    from finetune.collect_results import paired_bootstrap
except ImportError:
    from finetune.collect_results import paired_bootstrap  # type: ignore[no-redef]


# ---------- 常量 ----------
LABEL_RE = re.compile(r"^[A-Za-z0-9._-]{1,24}$")

# 固定分层键白名单（遇到不在列表里的值 → exit 2）
VALID_KINDS = frozenset({"choice", "noul", "score"})
VALID_LANGS = frozenset({"en", "zh"})
VALID_ROUTES = frozenset({"classification", "distillation"})
VALID_BUCKETS = frozenset({"2", "3-4", "5-8", "9-26"})

# coverage.skipped 的键只能是已知跳过原因（与 check_aggregate_export.SKIPPED_REASONS 同一枚举）；
# 未知键 fail-closed，防止把任意字符串（例如 rid）伪装成跳过原因带出隔离环境。
SKIPPED_REASONS = frozenset(
    {
        "options_gt_26",
        "prompt_too_long",
        "invalid_answer_idx",
        "missing_prompt",
        "missing_options",
        "token_map_mismatch",
        "drop",
        "no_route",
        "unknown_route",
        "degenerate_soft",
        "no_target",
        "answer_out_of_range",
        "answer_not_in_options",
        "non_single_token_answer",
        "seq_len_too_short",
    }
)

Z95 = 1.959964  # Wilson CI z value


# ---------- 工具函数 ----------

def _round6(value: float) -> float:
    return round(value, 6)


def _option_bucket(num_options: int) -> str:
    """选项数分桶（与 decision_common.get_option_count_bucket 同逻辑，但只返回合法桶）。"""
    if num_options <= 2:
        return "2"
    elif num_options <= 4:
        return "3-4"
    elif num_options <= 8:
        return "5-8"
    elif num_options <= 26:
        return "9-26"
    else:
        return ">26"


def wilson_ci(correct: int, total: int, z: float = Z95) -> List[float]:
    """Wilson score 95% CI，返回 [lower, upper]，round 6。"""
    if total == 0:
        return [0.0, 0.0]
    p = correct / total
    denom = 1 + z * z / total
    centre = p + z * z / (2 * total)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    lower = max(0.0, (centre - spread) / denom)
    upper = min(1.0, (centre + spread) / denom)
    return [_round6(lower), _round6(upper)]


def _percentile(values: Sequence[float], fraction: float) -> float:
    """线性插值分位数；空输入返回 0。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def cluster_key(rid: Any) -> str:
    """簇键 = rid 中第一个 '#' 之前的前缀；无 '#' 时为整条 rid；rid 非字符串 → ValueError。"""
    if not isinstance(rid, str) or not rid:
        raise ValueError(f"rid missing or not a non-empty string: {type(rid).__name__}")
    return rid.split("#", 1)[0]


def reliability_label(clusters: int) -> str:
    """G≥50 → ok；30≤G<50 → cautious；G<30 → low。"""
    if clusters >= 50:
        return "ok"
    if clusters >= 30:
        return "cautious"
    return "low"


def paired_group_cluster_bootstrap(base: Dict[str, bool], tuned: Dict[str, bool],
                                   rounds: int = 10000, seed: int = 20261023,
                                   alpha: float = 0.05) -> Dict[str, Any]:
    """按 rid 前缀簇重采样；点估计与 delta 按行加权。"""
    rids = sorted(set(base) & set(tuned))
    if len(rids) < 20:
        raise ValueError(f"too few paired rows: {len(rids)}")
    if rounds < 1:
        raise ValueError("cluster rounds must be >= 1")
    # 每簇只保存 [sum_delta, n]：重采样时按行加权（Σsum / Σn），不是簇等权平均。
    groups: Dict[str, List[int]] = {}
    for rid in rids:
        key = cluster_key(rid)
        acc = groups.setdefault(key, [0, 0])
        acc[0] += int(tuned[rid]) - int(base[rid])
        acc[1] += 1
    names = sorted(groups)
    stats = [groups[name] for name in names]
    sizes = [n for _, n in stats]
    total = sum(sizes)
    delta = sum(s for s, _ in stats) / total
    rng = random.Random(seed)
    count = len(stats)
    samples: List[float] = []
    for _ in range(rounds):
        sum_delta = 0
        sum_n = 0
        for _ in range(count):
            s, n = stats[rng.randrange(count)]
            sum_delta += s
            sum_n += n
        samples.append(sum_delta / sum_n)
    samples.sort()
    lo = samples[int(round(rounds * alpha / 2))]
    hi = samples[int(round(rounds * (1.0 - alpha / 2))) - 1]
    neff = (total * total) / sum(size * size for size in sizes)
    q1, q3 = _percentile(sizes, 0.25), _percentile(sizes, 0.75)
    return {
        "cluster_key": "rid_prefix_before_hash",
        "clusters": len(groups),
        "cluster_size_median": _round6(_percentile(sizes, 0.5)),
        "cluster_size_iqr": [_round6(q1), _round6(q3)],
        "cluster_size_max": max(sizes),
        "kish_neff": _round6(neff),
        "delta": _round6(delta),
        "ci95": [_round6(lo), _round6(hi)],
        "rounds": rounds,
        "method": "paired_group_cluster_bootstrap",
        "reliability": reliability_label(len(groups)),
    }


# ---------- 预测行读取 ----------

def _parse_correct(row: Dict[str, Any]) -> Optional[bool]:
    """推导 correct：优先用字段；缺失时比较 pred/gold letter；都没有返回 None。"""
    correct = row.get("correct")
    if isinstance(correct, bool):
        return correct
    # 数字 0/1
    if isinstance(correct, (int, float)):
        return bool(correct)
    # 用 pred/gold letter 推导
    pred = row.get("pred_letter")
    gold = row.get("gold_letter")
    if isinstance(pred, str) and isinstance(gold, str):
        return pred == gold
    return None


def read_pred_rows(path: Path) -> List[Dict[str, Any]]:
    """读取逐行预测 JSONL，返回原始行字典列表。"""
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{lineno}: each line must be an object")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no predictions")
    return rows


# ---------- 分层聚合 ----------

def _empty_stratum() -> Dict[str, Any]:
    return {"total": 0, "correct": 0, "accuracy": 0.0, "ci95_wilson": [0.0, 0.0]}


def _finalize_stratum(s: Dict[str, Any]) -> Dict[str, Any]:
    total, correct = s["total"], s["correct"]
    s["accuracy"] = _round6(correct / total) if total > 0 else 0.0
    s["ci95_wilson"] = wilson_ci(correct, total)
    return s


def aggregate_model(
    rows: List[Dict[str, Any]],
    *,
    expected_evaluated: int,
    allow_missing: bool,
) -> Tuple[Dict[str, Any], int, int]:
    """聚合一个模型的预测行。

    返回 (model_block, evaluated, invalid_count)。
    遇到未知分层键时抛 ValueError。
    """
    total = 0
    correct = 0
    invalid = 0

    # 固定键初始化
    by_kind = {k: _empty_stratum() for k in sorted(VALID_KINDS)}
    by_lang = {k: _empty_stratum() for k in sorted(VALID_LANGS)}
    by_bucket = {k: _empty_stratum() for k in ["2", "3-4", "5-8", "9-26"]}
    by_route = {k: _empty_stratum() for k in sorted(VALID_ROUTES)}

    for row in rows:
        # 先校验分层键，即使 correct/probability 无效也不能绕过 schema 检查。
        kind = str(row.get("kind", ""))
        if kind not in VALID_KINDS:
            raise ValueError(f"unknown kind: {kind!r} (valid: {sorted(VALID_KINDS)})")
        lang = str(row.get("lang", ""))
        if lang not in VALID_LANGS:
            raise ValueError(f"unknown lang: {lang!r} (valid: {sorted(VALID_LANGS)})")
        num_options = row.get("num_options")
        if not isinstance(num_options, int) or isinstance(num_options, bool):
            raise ValueError(f"invalid num_options: {num_options!r}")
        bucket = _option_bucket(num_options)
        if bucket not in VALID_BUCKETS:
            raise ValueError(f"unknown option bucket: {bucket!r} (num_options={num_options})")
        route = str(row.get("route", ""))
        if route not in VALID_ROUTES:
            raise ValueError(f"unknown route: {route!r} (valid: {sorted(VALID_ROUTES)})")
        # v2：rid 是配对与簇键的基础，缺失/非字符串一律 fail-closed。
        cluster_key(row.get("rid"))

        c = _parse_correct(row)
        invalid_probability = "candidate_probs" in row and candidate_distribution(row) is None
        if c is None or invalid_probability:
            # v2：invalid 行一律 exit 2（--allow-missing 只容忍「缺行」，不容忍 invalid 行），
            # 与 check_aggregate_export 的 accuracy=correct/total 自洽检查保持一致。
            reason = "invalid candidate_probs" if invalid_probability else (
                "no correct field, and pred_letter/gold_letter both missing"
            )
            raise ValueError(f"invalid prediction row: {reason}")
        is_correct = bool(c)

        total += 1
        if is_correct:
            correct += 1

        by_kind[kind]["total"] += 1
        if is_correct:
            by_kind[kind]["correct"] += 1
        by_lang[lang]["total"] += 1
        if is_correct:
            by_lang[lang]["correct"] += 1
        by_bucket[bucket]["total"] += 1
        if is_correct:
            by_bucket[bucket]["correct"] += 1
        by_route[route]["total"] += 1
        if is_correct:
            by_route[route]["correct"] += 1

    evaluated = total
    missing = expected_evaluated - evaluated

    # invalid 行已经作为实际预测行计入 evaluated；只有缺失文件行不计入 evaluated。
    missing_rows = expected_evaluated - evaluated
    if missing_rows < 0:
        missing_rows = 0  # more rows than expected: evaluate all

    # accuracy_with_missing: correct / expected_evaluated (缺失按错计)
    accuracy_with_missing = _round6(correct / expected_evaluated) if expected_evaluated > 0 else 0.0

    # 每层 finalize
    for d in (by_kind, by_lang, by_bucket, by_route):
        for s in d.values():
            _finalize_stratum(s)

    overall_acc = _round6(correct / total) if total > 0 else 0.0

    block: Dict[str, Any] = {
        "total": evaluated,
        "correct": correct,
        "accuracy": _round6(correct / evaluated) if evaluated > 0 else 0.0,
        "evaluated_accuracy": _round6(correct / evaluated) if evaluated > 0 else 0.0,
        "accuracy_ci95_wilson": wilson_ci(correct, evaluated),
        "accuracy_with_missing": accuracy_with_missing,
        "missing_rows": missing_rows,
        "by_kind": by_kind,
        "by_lang": by_lang,
        "by_option_bucket": by_bucket,
        "by_route": by_route,
    }
    return block, evaluated, invalid


# ---------- 校准 ----------

LOW_SAMPLE_BIN_COUNT = 20  # 箱 count < 20 视为样本不足


def _bin_index(confidence: float, bins: int) -> int:
    """与 calibrate.ece_bins 完全相同的箱归属规则（[lower, upper)，最后一箱含 1.0）。"""
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        if (lower <= confidence < upper) or (index == bins - 1 and confidence == 1.0):
            return index
    return -1  # 理论上不可达（置信度 ∈ [0,1]）


def _ece_cluster_ci(rows: Sequence[Dict[str, Any]], temperature: float,
                    rounds: int, seed: int, alpha: float = 0.05) -> List[float]:
    """按 rid 簇重采样计算 ECE 的百分位 95% CI。

    口径与 calibrate.evaluate 一致（可用行、argmax 置信度、15 等宽箱）；每簇预先汇总
    每箱 [count, Σconfidence, Σcorrect]，重采样时 ECE = Σ_b |Σconf_b − Σcorrect_b| / N。
    """
    bins = ECE_BINS
    clusters: Dict[str, List[List[float]]] = {}
    for row in rows:
        probs = candidate_distribution(row)
        gold = row.get("gold_letter")
        gold = str(gold) if gold is not None else None
        if probs is None or gold is None or gold not in probs:
            continue
        scaled = scaled_probs(probs, temperature)
        prediction = max(scaled.items(), key=lambda item: item[1])[0]
        confidence = scaled[prediction]
        index = _bin_index(confidence, bins)
        if index < 0:
            continue
        acc = clusters.setdefault(cluster_key(row.get("rid")),
                                  [[0.0, 0.0, 0.0] for _ in range(bins)])
        acc[index][0] += 1
        acc[index][1] += confidence
        acc[index][2] += 1.0 if prediction == gold else 0.0
    names = sorted(clusters)
    stats = [clusters[name] for name in names]
    if not stats:
        return [0.0, 0.0]
    rng = random.Random(seed)
    count = len(stats)
    samples: List[float] = []
    for _ in range(rounds):
        totals = [[0.0, 0.0, 0.0] for _ in range(bins)]
        for _ in range(count):
            picked = stats[rng.randrange(count)]
            for b in range(bins):
                cell = picked[b]
                if cell[0]:
                    t = totals[b]
                    t[0] += cell[0]
                    t[1] += cell[1]
                    t[2] += cell[2]
        n = sum(t[0] for t in totals)
        samples.append(sum(abs(t[1] - t[2]) for t in totals) / n if n else 0.0)
    samples.sort()
    lo = samples[int(round(rounds * alpha / 2))]
    hi = samples[max(0, int(round(rounds * (1.0 - alpha / 2))) - 1)]
    return [_round6(lo), _round6(hi)]


def _calibration_block(
    tuned_rows: List[Dict[str, Any]],
    *,
    fit_preds_path: Optional[Path],
    fit_half: str,
    temperature: Optional[float],
    ece_cluster_rounds: int = 500,
    seed: int = 20261023,
) -> Dict[str, Any]:
    """构建 calibration 子对象。"""
    if fit_preds_path is not None and temperature is not None:
        raise ValueError("--fit-preds and --temperature are mutually exclusive")

    if temperature is None and fit_preds_path is None:
        return {"status": "pending_temperature"}

    result: Dict[str, Any] = {}

    if fit_preds_path is not None:
        # 从 validation 拟合温度
        fit_rows = read_pred_rows(fit_preds_path)
        subset = filter_half(fit_rows, fit_half)
        if not subset:
            raise ValueError(f"no rows after filter_half({fit_half!r})")
        fit_result = fit_temperature(subset)
        temp = fit_result["temperature"]
        result["status"] = "fitted"
        result["temperature"] = _round6(temp)
        result["fit_half"] = fit_half
        result["fit_rows"] = fit_result["rows"]
        result["fit_method"] = "grid+golden_section_nll"
    else:
        assert temperature is not None
        temp = temperature
        result["status"] = "applied"
        result["temperature"] = _round6(temp)

    # 用 calibrate.evaluate 在 tuned 全集上评估 raw 和 calibrated
    raw_eval = calibrate_evaluate(tuned_rows, 1.0)
    cal_eval = calibrate_evaluate(tuned_rows, temp)

    def _eval_block(ev: Dict[str, Any], temp_value: float) -> Dict[str, Any]:
        bins_out = [
            {
                "bin": int(b["bin"]),
                "count": int(b["count"]),
                "avg_confidence": _round6(b["avg_confidence"]),
                "accuracy": _round6(b["accuracy"]),
                "gap": _round6(b["gap"]),
            }
            for b in ev["bins"]
        ]
        if len(bins_out) != ECE_BINS:
            raise ValueError(f"expected {ECE_BINS} calibration bins, got {len(bins_out)}")
        low = sum(1 for b in bins_out if b["count"] < LOW_SAMPLE_BIN_COUNT)
        return {
            "rows": ev["rows"],
            "accuracy": _round6(ev["accuracy"]),
            "nll": _round6(ev["nll"]),
            "brier": _round6(ev["brier"]),
            "ece": _round6(ev["ece"]),
            "mce": _round6(ev["mce"]),
            "bins": bins_out,
            "low_sample_bins": low,
            "low_sample_flag": low > 0,
            "ece_ci95_group": _ece_cluster_ci(tuned_rows, temp_value,
                                              ece_cluster_rounds, seed),
            "ece_rounds": ece_cluster_rounds,
        }

    if ece_cluster_rounds < 1:
        raise ValueError("--ece-cluster-rounds must be >= 1")
    result["raw"] = _eval_block(raw_eval, 1.0)
    result["calibrated"] = _eval_block(cal_eval, temp)
    result["accuracy_unchanged"] = raw_eval["accuracy"] == cal_eval["accuracy"]

    return result


# ---------- 主流程 ----------

def _completion_rate(evaluated: int, expected: int) -> float:
    """completion_rate = evaluated / expected_evaluated（expected=0 时为 0.0），round 6。"""
    return _round6(evaluated / expected) if expected > 0 else 0.0


def build_aggregate(args: argparse.Namespace) -> Dict[str, Any]:
    """构建聚合 JSON 对象。"""
    # 解析 --preds
    if not args.preds or len(args.preds) != 2:
        raise ValueError("exactly two --preds required (base and tuned)")

    pred_entries: List[Tuple[str, Path]] = []
    for spec in args.preds:
        if "=" not in spec:
            raise ValueError(f"--preds expects LABEL=PATH, got {spec!r}")
        label, path_str = spec.split("=", 1)
        if not LABEL_RE.match(label):
            raise ValueError(f"invalid label: {label!r} (must match {LABEL_RE.pattern})")
        pred_entries.append((label, Path(path_str)))

    base_label, base_path = pred_entries[0]
    tuned_label, tuned_path = pred_entries[1]

    # skipped
    skipped: Dict[str, int] = {}
    if args.skipped:
        raw = json.loads(Path(args.skipped).read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            # 可能是 eval_decision --json 输出的完整 JSON；取 skipped_stats 子对象
            if "skipped_stats" in raw:
                raw = raw["skipped_stats"]
            for k, v in raw.items():
                key = str(k)
                if key not in SKIPPED_REASONS:
                    raise ValueError(
                        f"unknown skip reason in --skipped: {key!r} "
                        f"(allowed: {sorted(SKIPPED_REASONS)})"
                    )
                skipped[key] = int(v)

    skipped_total = sum(skipped.values())
    expected_evaluated = args.view_rows - skipped_total
    if expected_evaluated < 0:
        raise ValueError(f"skipped_total ({skipped_total}) > view_rows ({args.view_rows})")

    allow_missing = bool(args.allow_missing)

    # 读取各模型预测
    base_rows = read_pred_rows(base_path)
    tuned_rows = read_pred_rows(tuned_path)

    base_block, base_eval_count, base_invalid = aggregate_model(
        base_rows, expected_evaluated=expected_evaluated, allow_missing=allow_missing,
    )
    tuned_block, tuned_eval_count, tuned_invalid = aggregate_model(
        tuned_rows, expected_evaluated=expected_evaluated, allow_missing=allow_missing,
    )

    # missing 检查
    base_missing = expected_evaluated - base_eval_count
    tuned_missing = expected_evaluated - tuned_eval_count

    if not allow_missing:
        if base_missing > 0:
            raise ValueError(f"{base_label}: missing {base_missing} rows "
                             f"(expected {expected_evaluated}, got {base_eval_count})")
        if tuned_missing > 0:
            raise ValueError(f"{tuned_label}: missing {tuned_missing} rows "
                             f"(expected {expected_evaluated}, got {tuned_eval_count})")

    # coverage block
    coverage: Dict[str, Any] = {
        "view_rows": args.view_rows,
        "skipped": skipped,
        "skipped_total": skipped_total,
        "expected_evaluated": expected_evaluated,
        "models": {
            base_label: {"evaluated": base_eval_count, "missing": max(0, base_missing),
                         "completion_rate": _completion_rate(base_eval_count, expected_evaluated)},
            tuned_label: {"evaluated": tuned_eval_count, "missing": max(0, tuned_missing),
                          "completion_rate": _completion_rate(tuned_eval_count, expected_evaluated)},
        },
    }

    # paired bootstrap
    base_correct_map: Dict[str, bool] = {}
    for row in base_rows:
        rid = row.get("rid")
        c = _parse_correct(row)
        if isinstance(rid, str) and c is not None:
            base_correct_map[rid] = c

    tuned_correct_map: Dict[str, bool] = {}
    for row in tuned_rows:
        rid = row.get("rid")
        c = _parse_correct(row)
        if isinstance(rid, str) and c is not None:
            tuned_correct_map[rid] = c

    bootstrap_rounds = args.bootstrap_rounds
    seed = args.seed
    cluster_rounds = int(getattr(args, "cluster_rounds", 10000))
    if cluster_rounds < 1:
        raise ValueError("--cluster-rounds must be >= 1")

    paired_rows = sorted(set(base_correct_map) & set(tuned_correct_map))
    if len(paired_rows) < 20:
        raise ValueError(f"too few paired rows for bootstrap: {len(paired_rows)} (need >= 20)")

    boot = paired_bootstrap(
        base_correct_map, tuned_correct_map, rounds=bootstrap_rounds, seed=seed,
    )

    paired_block: Dict[str, Any] = {
        "base_label": base_label,
        "tuned_label": tuned_label,
        "rows": boot["rows"],
        "base_accuracy": _round6(boot["base_accuracy"]),
        "tuned_accuracy": _round6(boot["tuned_accuracy"]),
        "delta": _round6(boot["delta"]),
        "ci95": [_round6(boot["ci95"][0]), _round6(boot["ci95"][1])],
        "rounds": boot["rounds"],
        "seed": boot["seed"],
        "method": "paired_item_bootstrap",
        "scope": "both_completed",
    }

    # v2：group-cluster bootstrap（主 CI）与 completed_only 敏感性分析。
    cluster = paired_group_cluster_bootstrap(
        base_correct_map, tuned_correct_map, rounds=cluster_rounds, seed=seed,
    )
    paired_block["cluster"] = cluster
    # 本轮无 --view：主 paired 本身就是双方都完成的 rid 交集，因此 completed_only
    # 与主 paired 同集合；单独给出 item/group 两个 CI 便于与 v3 ITT 口径并列。
    paired_block["completed_only"] = {
        "rows": boot["rows"],
        "base_accuracy": _round6(boot["base_accuracy"]),
        "tuned_accuracy": _round6(boot["tuned_accuracy"]),
        "delta": _round6(boot["delta"]),
        "ci95_item": [_round6(boot["ci95"][0]), _round6(boot["ci95"][1])],
        "ci95_group": list(cluster["ci95"]),
        "scope": "both_completed",
    }

    # calibration
    fit_preds_path = Path(args.fit_preds) if args.fit_preds else None
    fit_half_val = args.fit_half or "calibration"
    temperature = args.temperature

    cal_block = _calibration_block(
        tuned_rows,
        fit_preds_path=fit_preds_path,
        fit_half=fit_half_val,
        temperature=temperature,
        ece_cluster_rounds=int(getattr(args, "ece_cluster_rounds", 500)),
        seed=seed,
    )

    # assemble output
    output: Dict[str, Any] = {
        "schema": "pol-final-eval-aggregate-v1",
        "protocol": "finetune/EVAL-PROTOCOL.md#v1",
        "coverage": coverage,
        "models": {
            base_label: base_block,
            tuned_label: tuned_block,
        },
        "paired": paired_block,
        "calibration": cal_block,
    }

    return output


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--preds", action="append",
                        help="LABEL=PATH，可重复，必须恰好两个")
    parser.add_argument("--view-rows", type=int, required=True,
                        help="评测视图总行数（分母基）")
    parser.add_argument("--skipped", type=str, default=None,
                        help="跳过统计 JSON 路径")
    parser.add_argument("--fit-preds", type=str, default=None,
                        help="validation 上 adapter 的逐行预测路径（用于拟合温度）")
    parser.add_argument("--fit-half", type=str, default=None,
                        choices=["calibration", "selection", "all"],
                        help="拟合半区（默认 calibration）")
    parser.add_argument("--temperature", type=float, default=None,
                        help="给定温度（只 apply 不拟合；与 --fit-preds 互斥）")
    parser.add_argument("--bootstrap-rounds", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261023)
    parser.add_argument("--cluster-rounds", type=int, default=10000,
                        help="paired group-cluster bootstrap 次数（默认 10000）")
    parser.add_argument("--ece-cluster-rounds", type=int, default=500,
                        help="ECE 簇重采样 CI 次数（默认 500）")
    parser.add_argument("--allow-missing", action="store_true",
                        help="缺行时不报错，缺失行按错误计入 accuracy_with_missing；"
                             "invalid 行（无 correct 且无 pred/gold）始终 exit 2")
    parser.add_argument("--out", type=Path, required=True,
                        help="输出聚合 JSON 路径")
    args = parser.parse_args(argv)

    # --fit-preds 与 --temperature 互斥
    if args.fit_preds is not None and args.temperature is not None:
        print("error: --fit-preds and --temperature are mutually exclusive",
              file=sys.stderr)
        return 2

    try:
        output = build_aggregate(args)
        text = json.dumps(output, indent=2, ensure_ascii=False)

        # 写文件
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")

        # stdout 摘要
        models = output.get("models", {})
        labels = list(models.keys())
        paired = output.get("paired", {})
        cal_status = output.get("calibration", {}).get("status", "?")
        summary_parts = []
        for label in labels:
            m = models[label]
            summary_parts.append(f"{label}: {m['correct']}/{m['total']} "
                                 f"acc={m['accuracy']}")
        summary_parts.append(f"delta={paired.get('delta', '?')} "
                             f"ci95={paired.get('ci95', '?')}")
        summary_parts.append(f"calibration={cal_status}")
        print(" | ".join(summary_parts))

        return 0
    except (ValueError, OSError) as error:
        print(f"final_eval_aggregate failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
