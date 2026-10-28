"""Kev prefix/前后对照评测的聚合与统计（纯标准库，离线，不含逐例输出）。

输入：一次 Kev benchmark 的运行目录（rows.json / report.json）与 build_suite.py 产出的 join.jsonl。
输出：只含聚合数字的 JSON——整体/分层指标、served 与 raw(T=1) 两套校准、配对 cluster bootstrap CI、
      permuted/isolation 变体指标、覆盖与失败计数。不输出 item id / rid / 逐例预测。

指标口径对齐 kev.metrics（与 Kev 官方 report 可交叉核对）：
- acc = argmax 正确率；Brier = mean(sum((p-onehot)^2))；NLL = logsumexp(z)-z[label]（有 logits 时，精确）；
- ECE = 10 箱（Kev 口径）与 15 箱（EVAL-PROTOCOL 口径）等宽置信度加权绝对差；
- coverage_at_5pct_error / AURC 与 kev.metrics 同定义（整置信度组接收，样本内最大值，非部署保证）；
- score 题另报 score_mae 与 ranked_probability_score。
- served = 按 checkpoint 自带温度（head.pt temperature）输出；raw_t1 = 还原 raw logits（z*T）后的 T=1 口径。
- 配对比较：同一 (id, question) 上，按 join 的 group_id 做 cluster bootstrap（同 item/同族一起抽）。

    python benchmark/kev_prefix/aggregate.py --join <仓库外>/join.jsonl \\
        --run kev-4b-v1.0=<仓库外>/runs/kev-4b --run seed-43=<仓库外>/runs/seed-43 \\
        --reference kev-4b-v1.0 --out <仓库外>/aggregate.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "kev-prefix-aggregate/1"
EPSILON = 1e-9
NLL_FLOOR = 1e-12
OPTION_BUCKETS = (("2", 2, 2), ("3-4", 3, 4), ("5-8", 5, 8), ("9-26", 9, 26), (">26", 27, 10 ** 9))
STATE_CHAR_BUCKETS = (("<=400", 0, 400), ("401-1200", 401, 1200), ("1201-3000", 1201, 3000), (">3000", 3001, 10 ** 9))


# ----------------------------------------------------------------------------- 基础数学

def softmax(values):
    top = max(values)
    exps = [math.exp(v - top) for v in values]
    total = sum(exps)
    return [v / total for v in exps]


def logsumexp(values):
    top = max(values)
    return top + math.log(sum(math.exp(v - top) for v in values))


def option_bucket(n):
    for name, lo, hi in OPTION_BUCKETS:
        if lo <= n <= hi:
            return name
    return ">26"


def state_bucket(chars):
    for name, lo, hi in STATE_CHAR_BUCKETS:
        if lo <= chars <= hi:
            return name
    return ">3000"


# ----------------------------------------------------------------------------- 指标

def row_probs(row, raw=False):
    """served: 记录中的 p；raw: 用 raw logits（z * inference_temperature）重新 softmax。"""
    if not raw:
        return list(row["p"])
    if "logits" not in row:
        raise ValueError("raw metrics require recorded logits")
    temperature = row.get("inference_temperature") or 1.0
    return softmax([float(z) * temperature for z in row["logits"]])


def row_logits(row, raw=False):
    if "logits" not in row:
        return None
    values = [float(z) for z in row["logits"]]
    if raw:
        temperature = row.get("inference_temperature") or 1.0
        values = [z * temperature for z in values]
    return values


def row_nll(row, raw=False):
    logits = row_logits(row, raw=raw)
    label = row["label"]
    if logits is not None:
        return logsumexp(logits) - logits[label]
    p = row_probs(row, raw=raw)
    return -math.log(max(p[label], EPSILON))


def row_brier(row, raw=False):
    p = row_probs(row, raw=raw)
    label = row["label"]
    return sum((value - (1.0 if i == label else 0.0)) ** 2 for i, value in enumerate(p))


def argmax_index(values):
    best = 0
    for i, value in enumerate(values):
        if value > values[best]:
            best = i
    return best


def ece(confidences, corrects, bins=10):
    if not confidences:
        return None
    total = 0.0
    edges = [i / bins for i in range(bins + 1)]
    for lo, hi in zip(edges[:-1], edges[1:]):
        members = [(c, k) for c, k in zip(confidences, corrects)
                   if (lo <= c < hi) or (hi == 1.0 and lo <= c <= hi)]
        if not members:
            continue
        share = len(members) / len(confidences)
        mean_conf = sum(c for c, _ in members) / len(members)
        mean_acc = sum(1.0 for _, k in members if k) / len(members)
        total += share * abs(mean_acc - mean_conf)
    return total


def risk_curve(confidences, corrects):
    order = sorted(range(len(confidences)), key=lambda i: -confidences[i])
    thresholds, accepted, errors = [], [], []
    cum_errors = 0
    for position, index in enumerate(order, start=1):
        cum_errors += 0 if corrects[index] else 1
        if position == len(order) or confidences[order[position]] != confidences[index]:
            thresholds.append(confidences[index])
            accepted.append(position)
            errors.append(cum_errors)
    return thresholds, accepted, errors


def coverage_at_error(confidences, corrects, budget=0.05):
    thresholds, accepted, errors = risk_curve(confidences, corrects)
    if not accepted:
        return 0.0
    ok = [i for i, (a, e) in enumerate(zip(accepted, errors)) if e <= budget * a]
    return accepted[ok[-1]] / accepted[-1] if ok else 0.0


def coverage_at_error_detail(confidences, corrects, budget=0.05):
    """coverage、接受集样本量/错误率与准确率（coverage 点的可审计明细）。"""
    thresholds, accepted, errors = risk_curve(confidences, corrects)
    total = accepted[-1] if accepted else 0
    if not total:
        return {"coverage": 0.0, "accepted_n": 0, "accepted_error_rate": None, "accepted_accuracy": None}
    ok = [i for i, (a, e) in enumerate(zip(accepted, errors)) if e <= budget * a]
    if not ok:
        return {"coverage": 0.0, "accepted_n": 0, "accepted_error_rate": None, "accepted_accuracy": None}
    index = ok[-1]
    n, e = accepted[index], errors[index]
    return {"coverage": n / total, "accepted_n": n, "accepted_error_rate": e / n, "accepted_accuracy": 1 - e / n}


def aurc(confidences, corrects):
    thresholds, accepted, errors = risk_curve(confidences, corrects)
    if not accepted:
        return 0.0
    area = 0.0
    previous = 0
    for count, error in zip(accepted, errors):
        area += (count - previous) * (error / count)
        previous = count
    return area / accepted[-1]


def metrics(rows, raw=False, ece_bins=(10, 15)):
    """聚合指标；rows 需含 p/label/type/logits/inference_temperature。"""
    if not rows:
        return {"n": 0}
    probs = [row_probs(row, raw=raw) for row in rows]
    labels = [row["label"] for row in rows]
    confidences = [max(p) for p in probs]
    corrects = [argmax_index(p) == y for p, y in zip(probs, labels)]
    nlls = [row_nll(row, raw=raw) for row in rows]
    briers = [row_brier(row, raw=raw) for row in rows]
    n = len(rows)
    result = {
        "n": n,
        "acc": sum(corrects) / n,
        "brier": sum(briers) / n,
        "nll": sum(nlls) / n,
        "mean_conf": sum(confidences) / n,
        "confidence_bias": sum(confidences) / n - sum(corrects) / n,
    }
    for bins in ece_bins:
        result[f"ece_{bins}"] = ece(confidences, corrects, bins)
    high = [i for i, c in enumerate(confidences) if c >= 0.9]
    result["coverage_at_0_9"] = len(high) / n
    result["confident_error_rate"] = sum(1 for i in range(n) if confidences[i] >= 0.9 and not corrects[i]) / n
    result["accuracy_at_0_9"] = (sum(1 for i in high if corrects[i]) / len(high)) if high else None
    result["error_rate_at_0_9"] = (sum(1 for i in high if not corrects[i]) / len(high)) if high else None
    result["coverage_at_5pct_error"] = coverage_at_error(confidences, corrects, 0.05)
    result["coverage_at_1pct_error"] = coverage_at_error(confidences, corrects, 0.01)
    result["coverage_at_5pct_error_detail"] = coverage_at_error_detail(confidences, corrects, 0.05)
    result["aurc"] = aurc(confidences, corrects)
    score_rows = [i for i, row in enumerate(rows) if row.get("type") == "score"]
    if score_rows:
        maes, rps = [], []
        for i in score_rows:
            p, y = probs[i], labels[i]
            levels = [float(j) for j in range(len(p))]
            maes.append(abs(sum(level * value for level, value in zip(levels, p)) - y))
            target = [1.0 if j == y else 0.0 for j in range(len(p))]
            cum_p, cum_t = 0.0, 0.0
            terms = []
            for j in range(len(p) - 1):
                cum_p += p[j]
                cum_t += target[j]
                terms.append((cum_p - cum_t) ** 2)
            rps.append(sum(terms) / len(terms))
        result["score_mae"] = sum(maes) / len(maes)
        result["ranked_probability_score"] = sum(rps) / len(rps)
    return result


def grouped_metrics(rows, key_name, raw=False):
    groups = {}
    for row in rows:
        groups.setdefault(row.get(key_name), []).append(row)
    return {str(name): metrics(members, raw=raw) for name, members in sorted(groups.items(), key=lambda kv: str(kv[0]))}


def _cluster_rows(rows):
    clusters = {}
    for index, row in enumerate(rows):
        clusters.setdefault(row["group"], []).append(index)
    keys = sorted(clusters)
    return keys, [clusters[key] for key in keys]


def single_model_ci(rows, *, samples=1000, seed=0, nonlinear_samples=200):
    """单模型指标的 record/group-cluster bootstrap CI95（additive 用簇和加速；ECE/coverage 重抽样行）。"""
    if not rows:
        return None
    keys, clusters = _cluster_rows(rows)
    n_clusters = len(keys)
    sums = [{"n": 0, "acc": 0.0, "brier": 0.0, "nll": 0.0} for _ in keys]
    confs, corrects = [], []
    for cluster_index, indices in enumerate(clusters):
        for index in indices:
            row = rows[index]
            p, label = row["p"], row["label"]
            correct = argmax_index(p) == label
            bucket = sums[cluster_index]
            bucket["n"] += 1
            bucket["acc"] += 1.0 if correct else 0.0
            bucket["brier"] += sum((value - (1.0 if i == label else 0.0)) ** 2 for i, value in enumerate(p))
            logits = row.get("logits")
            if logits is not None:
                z = [float(v) for v in logits]
                bucket["nll"] += logsumexp(z) - z[label]
            else:
                bucket["nll"] += -math.log(max(p[label], EPSILON))
            confs.append(max(p))
            corrects.append(correct)
    rng = random.Random(seed)
    draws = {metric: [] for metric in ("acc", "brier", "nll")}
    for _ in range(samples):
        n = 0.0
        acc = brier = nll = 0.0
        for _ in range(n_clusters):
            bucket = sums[rng.randrange(n_clusters)]
            n += bucket["n"]
            acc += bucket["acc"]
            brier += bucket["brier"]
            nll += bucket["nll"]
        draws["acc"].append(acc / n)
        draws["brier"].append(brier / n)
        draws["nll"].append(nll / n)
    point = metrics(rows)
    out = {}
    for metric, values in draws.items():
        values.sort()
        out[metric] = {"value": point[metric],
                       "ci95": [values[min(len(values) - 1, int(0.025 * samples))],
                                values[min(len(values) - 1, max(0, int(0.975 * samples) - 1))]]}
    nonlinear = {"ece_10": [], "ece_15": [], "coverage_at_5pct_error": []}
    for _ in range(nonlinear_samples):
        picked = []
        for _ in range(n_clusters):
            picked.extend(clusters[rng.randrange(n_clusters)])
        conf = [confs[i] for i in picked]
        corr = [corrects[i] for i in picked]
        nonlinear["ece_10"].append(ece(conf, corr, 10))
        nonlinear["ece_15"].append(ece(conf, corr, 15))
        nonlinear["coverage_at_5pct_error"].append(coverage_at_error(conf, corr, 0.05))
    for metric, values in nonlinear.items():
        values.sort()
        out[metric] = {"value": point[metric],
                       "ci95": [values[min(len(values) - 1, int(0.025 * nonlinear_samples))],
                                values[min(len(values) - 1, max(0, int(0.975 * nonlinear_samples) - 1))]],
                       "samples": nonlinear_samples}
    return out


# ----------------------------------------------------------------------------- 数据装配

def read_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_join(path):
    join = {}
    for row in read_jsonl(path):
        join[row["id"]] = row
    return join


def attach(rows, join, *, exclude_overlong=True, only_rids=None):
    """把 rows.json 的 clean rows 与 join 元数据对齐，返回 (enriched, dropped)。"""
    enriched, dropped = [], {"unknown_record": 0, "variant": 0, "overlong": 0, "not_in_subset": 0}
    for row in rows:
        if row.get("variant") != "clean":
            dropped["variant"] += 1
            continue
        record = join.get(row["id"])
        if record is None or row["question"] not in {q["qid"] for q in record["questions"]}:
            dropped["unknown_record"] += 1
            continue
        question = next(q for q in record["questions"] if q["qid"] == row["question"])
        if exclude_overlong and question.get("overlong"):
            dropped["overlong"] += 1
            continue
        if only_rids is not None and question["rid"] not in only_rids:
            dropped["not_in_subset"] += 1
            continue
        enriched.append({
            "key": (row["id"], row["question"]),
            "group": record["group_id"],
            "kind": row["type"], "lang": record["lang"], "domain": record["domain"],
            "num_options": len(row["keys"]), "option_bucket": option_bucket(len(row["keys"])),
            "state_bucket": state_bucket(record["state_chars"]),
            "p": list(row["p"]), "label": int(row["label"]), "keys": list(row["keys"]),
            "logits": row.get("logits"), "inference_temperature": row.get("inference_temperature"),
            "type": row["type"],
        })
    return enriched, dropped


def load_run(name, directory):
    directory = Path(directory)
    rows_path = directory / "rows.json"
    report_path = directory / "report.json"
    if not rows_path.is_file():
        raise SystemExit(f"missing {rows_path}")
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    return name, rows, report


# ----------------------------------------------------------------------------- 配对 bootstrap

def cluster_indices(rows):
    clusters = {}
    for index, row in enumerate(rows):
        clusters.setdefault(row["group"], []).append(index)
    keys = sorted(clusters)
    return [clusters[key] for key in keys], len(keys)


def _metric_values(rows, indices, raw=False):
    """在给定行下标上算 additive 指标与 ECE（供 bootstrap 用）。"""
    n = len(indices)
    acc = 0.0
    brier = 0.0
    nll = 0.0
    confs, corrects = [], []
    for index in indices:
        row = rows[index]
        p = row_probs(row, raw=raw)
        label = row["label"]
        conf = max(p)
        correct = argmax_index(p) == label
        acc += 1.0 if correct else 0.0
        brier += sum((value - (1.0 if i == label else 0.0)) ** 2 for i, value in enumerate(p))
        nll += row_nll(row, raw=raw)
        confs.append(conf)
        corrects.append(correct)
    return {"acc": acc / n, "brier": brier / n, "nll": nll / n, "ece_10": ece(confs, corrects, 10)}


def paired_bootstrap(rows_a, rows_b, *, samples=1000, seed=0, raw=False, baseline_metrics=("acc", "brier", "nll", "ece_10")):
    """按 (id,question) 配对、按 group cluster 重抽样的指标差值 CI95。"""
    index_b = {row["key"]: row for row in rows_b}
    a_rows = [row for row in rows_a if row["key"] in index_b]
    b_rows = [index_b[row["key"]] for row in a_rows]
    if not a_rows:
        raise ValueError("no paired questions")
    clusters, n_clusters = cluster_indices(a_rows)
    point_a = _metric_values(a_rows, list(range(len(a_rows))), raw=raw)
    point_b = _metric_values(b_rows, list(range(len(b_rows))), raw=raw)
    point = {metric: point_a[metric] - point_b[metric] for metric in baseline_metrics}
    rng = random.Random(seed)
    draws = {metric: [] for metric in baseline_metrics}
    for _ in range(samples):
        picked = []
        for _ in range(n_clusters):
            picked.extend(clusters[rng.randrange(n_clusters)])
        values_a = _metric_values(a_rows, picked, raw=raw)
        values_b = _metric_values(b_rows, picked, raw=raw)
        for metric in baseline_metrics:
            draws[metric].append(values_a[metric] - values_b[metric])
    out = {"n_pairs": len(a_rows), "groups": n_clusters, "samples": samples, "seed": seed,
           "unit": "group_id cluster (item/family), paired by (id, question)", "deltas": {}}
    for metric in baseline_metrics:
        values = sorted(draws[metric])
        if not values:
            lo = hi = None
        else:
            lo = values[min(len(values) - 1, int(0.025 * samples))]
            hi = values[min(len(values) - 1, max(0, int(0.975 * samples) - 1))]
        out["deltas"][metric] = {"delta": point[metric], "ci95": [lo, hi]}
    return out


# ----------------------------------------------------------------------------- 变体分析

def variant_stats(all_rows, variant_name):
    """permuted/isolation：与同一 run 的 clean 记录配对比较。"""
    clean = {(row["id"], row["question"]): row for row in all_rows if row.get("variant") == "clean"}
    variant_rows = [row for row in all_rows if row.get("variant") == variant_name]
    if not variant_rows:
        return None
    deltas, flips, same_acc, pairs = [], 0, 0, 0
    delta_values, flip_values, same_values, groups = [], [], [], []
    for row in variant_rows:
        parent = row.get("parent")
        parent_row = clean.get((parent, row["question"]))
        if parent_row is None:
            continue
        base = dict(zip(parent_row["keys"], parent_row["p"]))
        current = dict(zip(row["keys"], row["p"]))
        if set(base) != set(current):
            continue
        delta = max(abs(current[key] - base[key]) for key in base)
        deltas.append(delta)
        flip = argmax_index([current[k] for k in base]) != argmax_index([base[k] for k in base])
        flips += 1 if flip else 0
        same = 1 if (argmax_index([current[k] for k in base]) == row["label"]) == (argmax_index([base[k] for k in base]) == parent_row["label"]) else 0
        same_acc += same
        pairs += 1
        delta_values.append(delta)
        flip_values.append(1.0 if flip else 0.0)
        same_values.append(float(same))
        groups.append(row.get("group") or parent_row.get("group"))
    if not pairs:
        return None
    deltas.sort()
    point = {"n_pairs": pairs, "mean_max_delta": sum(deltas) / pairs, "max_max_delta": deltas[-1],
             "median_max_delta": deltas[len(deltas) // 2], "flip_rate": flips / pairs,
             "accuracy_unchanged_rate": same_acc / pairs}
    point["ci95"] = _variant_ci(delta_values, flip_values, same_values, groups)
    return point


def _variant_ci(deltas, flips, sames, groups, samples=1000, seed=0):
    """按 record/group cluster 对变体指标做 bootstrap CI95（与主表同 seed）。"""
    clusters = {}
    for index, group in enumerate(groups):
        clusters.setdefault(group, []).append(index)
    keys = sorted(clusters)
    if not keys or samples < 1:
        return None
    rng = random.Random(seed)
    draws = {"mean_max_delta": [], "flip_rate": [], "accuracy_unchanged_rate": []}
    for _ in range(samples):
        picked = []
        for _ in range(len(keys)):
            picked.extend(clusters[keys[rng.randrange(len(keys))]])
        total = len(picked)
        draws["mean_max_delta"].append(sum(deltas[i] for i in picked) / total)
        draws["flip_rate"].append(sum(flips[i] for i in picked) / total)
        draws["accuracy_unchanged_rate"].append(sum(sames[i] for i in picked) / total)
    out = {}
    for name, values in draws.items():
        values.sort()
        out[name] = [values[min(len(values) - 1, int(0.025 * samples))],
                     values[min(len(values) - 1, max(0, int(0.975 * samples) - 1))]]
    return out


# ----------------------------------------------------------------------------- 出口检查

def export_check(output, join):
    """聚合文件不得含 item id / rid / 私有 group id。"""
    text = json.dumps(output, ensure_ascii=False)
    forbidden = set()
    for record in join.values():
        if record.get("item_id"):
            forbidden.add(record["item_id"])
        for question in record["questions"]:
            if question.get("rid"):
                forbidden.add(question["rid"])
        if record.get("group_id"):
            forbidden.add(str(record["group_id"]))
    leaked = [value for value in forbidden if len(value) >= 4 and value in text]
    if leaked:
        raise ValueError(f"aggregate output leaks {len(leaked)} identifier-like strings (e.g. {leaked[0][:12]!r})")
    return True


# ----------------------------------------------------------------------------- CLI

def summarize_run(name, rows, report, join, *, exclude_overlong, only_rids, compute_ci=True, ece_bins=(10, 15)):
    enriched, dropped = attach(rows, join, exclude_overlong=exclude_overlong, only_rids=only_rids)
    if not enriched:
        raise SystemExit(f"run {name}: no rows after filtering")
    clusters = _cluster_rows(enriched)[1]
    served = metrics(enriched, raw=False, ece_bins=ece_bins)
    raw_ok = all(row.get("logits") for row in enriched)
    summary = {
        "coverage": {
            "clean_rows_in_rows_json": sum(1 for row in rows if row.get("variant") == "clean"),
            "primary_questions": len(enriched),
            "clusters": len(clusters),
            "dropped": dropped,
        },
        "served": {
            "overall": served,
            "by_kind": grouped_metrics(enriched, "kind"),
            "by_lang": grouped_metrics(enriched, "lang"),
            "by_domain": grouped_metrics(enriched, "domain"),
            "by_option_bucket": grouped_metrics(enriched, "option_bucket"),
            "by_state_chars": grouped_metrics(enriched, "state_bucket"),
        },
        "run_metadata": {
            "temperature": report.get("calibration", {}).get("inference_temperature") if report else None,
            "latency_ms": report.get("latency_ms") if report else None,
            "coverage": report.get("coverage") if report else None,
            "environment": report.get("environment") if report else None,
            "suite_sha256": report.get("suite_sha256") if report else None,
            "date_facts": report.get("date_facts") if report else None,
            "rotations": report.get("rotations") if report else None,
        },
    }
    if raw_ok:
        summary["raw_t1"] = {"overall": metrics(enriched, raw=True, ece_bins=ece_bins)}
    else:
        summary["raw_t1"] = None
    if compute_ci:
        summary["ci"] = single_model_ci(enriched, seed=0)
    else:
        summary["ci"] = None
    return enriched, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--join", type=Path, required=True)
    parser.add_argument("--run", action="append", required=True, help="name=<run dir with rows.json/report.json>")
    parser.add_argument("--reference", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--include-overlong", action="store_true", help="include view-rule overlong questions (sensitivity)")
    parser.add_argument("--subset-rids", type=Path, help="only aggregate questions whose rid is listed (one per line)")
    parser.add_argument("--no-ci", action="store_true", help="skip single-model cluster bootstrap CIs (faster)")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)
    join = load_join(args.join)
    only_rids = None
    if args.subset_rids:
        only_rids = {line.strip() for line in Path(args.subset_rids).read_text(encoding="utf-8").splitlines() if line.strip()}
    runs, reports = {}, {}
    for spec in args.run:
        name, _, directory = spec.partition("=")
        if not name or not directory:
            parser.error(f"bad --run {spec!r}; expected name=dir")
        _, rows, report = load_run(name, directory)
        runs[name], reports[name] = rows, report
    if args.reference not in runs:
        parser.error(f"--reference {args.reference!r} not in runs")
    enriched, summaries = {}, {}
    for name, rows in runs.items():
        enriched[name], summaries[name] = summarize_run(
            name, rows, reports[name], join, exclude_overlong=not args.include_overlong, only_rids=only_rids,
            compute_ci=not args.no_ci)
    output = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": args.note,
        "settings": {
            "exclude_overlong": not args.include_overlong,
            "subset_rids": bool(only_rids),
            "bootstrap_samples": args.bootstrap_samples,
            "bootstrap_seed": args.seed,
        },
        "suite": {
            "join_sha256": hashlib.sha256(Path(args.join).read_bytes()).hexdigest(),
            "records": len(join),
            "clean_questions": sum(len(row["questions"]) for row in join.values() if row["variant"] == "clean"),
        },
        "runs": summaries,
        "variants": {name: {"permuted": variant_stats(runs[name], "permuted"),
                            "isolation": variant_stats(runs[name], "isolation")} for name in runs},
        "paired": {},
        "provenance": {
            "aggregate_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "reference": args.reference,
        },
    }
    for name in runs:
        if name == args.reference:
            continue
        comparison = {}
        for label, raw in (("served", False), ("raw_t1", True)):
            try:
                comparison[label] = paired_bootstrap(enriched[name], enriched[args.reference],
                                                     samples=args.bootstrap_samples, seed=args.seed,
                                                     raw=(label == "raw_t1"))
            except ValueError as error:
                comparison[label] = {"error": str(error)}
        output["paired"][f"{name} vs {args.reference}"] = comparison
    export_check(output, join)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runs": {name: {"n": summaries[name]["served"]["overall"]["n"],
                                     "acc": summaries[name]["served"]["overall"]["acc"],
                                     "nll": summaries[name]["served"]["overall"]["nll"]} for name in summaries},
                      "paired": {key: {label: comparison.get(label, {}).get("deltas", {}).get("acc")
                                       for label in ("served", "raw_t1")}
                                 for key, comparison in output["paired"].items()}},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())