#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deep statistics for the Kev prefix-evaluation report.

Reads the raw evaluation rows from the private evaluation workspace (outside the repo),
computes aggregate-only statistics (no per-example output), and writes deep-stats.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

PRIV = Path("/home/wenbo/priv-eval")
RUNS = ["kev-original", "seed43", "seed17", "seed29"]
LABELS = {"kev-original": "Kev-4B original", "seed43": "M10 seed-43", "seed17": "M10 seed-17", "seed29": "M10 seed-29"}
BINS = 15
EPS = 1e-12


def load_json(path):
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def row_probs(row, raw=False):
    p = np.asarray(row["p"], dtype=float)
    if raw:
        if row.get("logits") is None:
            raise ValueError("raw probabilities need logits")
        t = float(row.get("inference_temperature") or 1.0)
        z = np.asarray(row["logits"], dtype=float) * t
        z = z - z.max()
        e = np.exp(z)
        p = e / e.sum()
    return p


def nll_of(row, p):
    label = int(row["label"])
    logits = row.get("logits")
    if logits is not None:
        z = np.asarray(logits, dtype=float)
        top = z.max()
        return float(top + math.log(np.exp(z - top).sum()) - z[label])
    return float(-math.log(max(p[label], EPS)))


def ece_bins(conf, correct, bins=BINS):
    edges = np.linspace(0.0, 1.0, bins + 1)
    out = []
    total = len(conf)
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf >= lo) & ((conf <= hi) if hi >= 1.0 else (conf < hi))
        count = int(mask.sum())
        if count:
            out.append([float(lo), float(hi), count, float(conf[mask].mean()), float(correct[mask].mean()),
                        float(correct[mask].mean() - conf[mask].mean())])
        else:
            out.append([float(lo), float(hi), 0, None, None, None])
    return out


def ece_from_bins(bins):
    total = sum(b[2] for b in bins)
    return sum(b[2] / total * abs(b[4] - b[3]) for b in bins if b[2])


def risk_curve(conf, correct):
    order = np.argsort(-conf, kind="stable")
    conf_sorted = conf[order]
    correct_sorted = correct[order]
    cum_errors = np.cumsum(~correct_sorted)
    ends = np.r_[np.flatnonzero(conf_sorted[1:] != conf_sorted[:-1]), len(order) - 1]
    accepted = ends + 1
    errors = cum_errors[ends]
    n = len(order)
    return accepted, errors, n


def coverage_at_error(conf, correct, budget=0.05):
    accepted, errors, n = risk_curve(conf, correct)
    ok = np.flatnonzero(errors <= budget * accepted)
    if not len(ok):
        return {"coverage": 0.0, "accepted_n": 0, "error_rate": None, "accuracy": None}
    index = int(ok[-1])
    accepted_n = int(accepted[index])
    error_rate = float(errors[index] / accepted_n)
    return {"coverage": accepted_n / n, "accepted_n": accepted_n, "error_rate": error_rate,
            "accuracy": 1.0 - error_rate}


def aurc(conf, correct):
    accepted, errors, n = risk_curve(conf, correct)
    previous = 0
    area = 0.0
    for count, error in zip(accepted, errors):
        area += (count - previous) * (error / count)
        previous = count
    return float(area / accepted[-1])


def wilson(k, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [max(0.0, centre - half), min(1.0, centre + half)]


def brier_decomposition(prob, correct):
    prob = np.asarray(prob, dtype=float)
    correct = np.asarray(correct, dtype=float)
    base = float(correct.mean())
    total = 0.0
    reliability = 0.0
    resolution = 0.0
    edges = np.linspace(0.0, 1.0, BINS + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (prob >= lo) & ((prob <= hi) if hi >= 1.0 else (prob < hi))
        count = int(mask.sum())
        if count:
            total += count
            mean_p = float(prob[mask].mean())
            observed = float(correct[mask].mean())
            reliability += count / len(prob) * (mean_p - observed) ** 2
            resolution += count / len(prob) * (observed - base) ** 2
    return {"reliability": reliability, "resolution": resolution,
            "uncertainty": float(base * (1 - base)), "base_rate": base, "n": len(prob)}


def histogram(values, bins=40, lo=None, hi=None):
    values = np.asarray(values, dtype=float)
    if lo is None:
        lo = float(np.min(values))
    if hi is None:
        hi = float(np.max(values))
    if hi <= lo:
        hi = lo + 1e-9
    counts, edges = np.histogram(values, bins=bins, range=(lo, hi))
    return {"edges": [float(x) for x in edges], "counts": [int(x) for x in counts],
            "lo": float(lo), "hi": float(hi)}


def ecdf_points(values, points=80):
    values = np.sort(np.asarray(values, dtype=float))
    if not len(values):
        return []
    xs = np.linspace(0.0, 1.0, points)
    idx = np.clip((xs * (len(values) - 1)).astype(int), 0, len(values) - 1)
    return [[float(values[i]), float((i + 1) / len(values))] for i in idx]


def cluster_bootstrap_delta(rows_a, rows_b, clusters, metric, nums=2000, seed=0):
    rng = np.random.default_rng(seed)
    keys, inverse = np.unique(clusters, return_inverse=True)
    n_clusters = len(keys)
    counts = np.bincount(inverse, minlength=n_clusters).astype(float)
    if metric == "acc":
        a = rows_a.astype(float)
        b = rows_b.astype(float)
    else:
        a, b = rows_a, rows_b
    sums_a = np.bincount(inverse, weights=a, minlength=n_clusters)
    sums_b = np.bincount(inverse, weights=b, minlength=n_clusters)
    draws = np.empty(nums, dtype=float)
    for i in range(nums):
        pick = rng.integers(0, n_clusters, size=n_clusters)
        weight = counts[pick]
        total = weight.sum()
        draws[i] = (sums_a[pick].sum() - sums_b[pick].sum()) / total
    return draws


def permutation_delta(diff, clusters, nums=2000, seed=1):
    """Cluster sign-flip randomization test for a paired mean difference."""
    rng = np.random.default_rng(seed)
    keys, inverse = np.unique(clusters, return_inverse=True)
    n_clusters = len(keys)
    cluster_sum = np.bincount(inverse, weights=diff, minlength=n_clusters)
    observed = float(diff.mean())
    count = 0
    extremes = 0
    draws = np.empty(nums)
    for i in range(nums):
        signs = rng.choice([-1.0, 1.0], size=n_clusters)
        value = float((cluster_sum * signs).sum() / len(diff))
        draws[i] = value
        if abs(value) >= abs(observed) - 1e-15:
            extremes += 1
    return {"observed": observed, "p_value": (extremes + 1) / (nums + 1), "hist": histogram(draws, bins=42)}


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return {"b": int(b), "c": int(c), "p_value": 1.0, "p_chi2": 1.0}
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    p_exact = min(1.0, 2 * tail)
    stat = (b - c) ** 2 / n
    p_chi2 = math.erfc(math.sqrt(max(stat, 0.0) / 2))  # chi-square 1 df survival, valid for stat
    return {"b": int(b), "c": int(c), "p_value": float(p_exact), "p_chi2": float(p_chi2)}


def holm(pvalues):
    items = sorted(((p, i) for i, p in enumerate(pvalues)), key=lambda x: x[0])
    m = len(pvalues)
    adjusted = [1.0] * m
    previous = 0.0
    for rank, (p, index) in enumerate(items):
        value = min(1.0, (m - rank) * p)
        previous = max(previous, value)
        adjusted[index] = previous
    return adjusted


def main():
    join = {}
    with (PRIV / "join-eval.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                join[row["id"]] = row
    rids = {line.strip() for line in (PRIV / "rids-training-context.txt").read_text(encoding="utf-8").splitlines() if line.strip()}
    models = {}
    for name in RUNS:
        rows_path = PRIV / "runs" / name / "rows.json"
        rows = load_json(rows_path)
        selected = []
        for row in rows:
            if row.get("variant") != "clean":
                continue
            record = join.get(row["id"])
            if record is None:
                continue
            question = next((q for q in record["questions"] if q["qid"] == row["question"]), None)
            if question is None or question["rid"] not in rids:
                continue
            selected.append((row, record, question))
        selected.sort(key=lambda item: (item[0]["id"], item[0]["question"]))
        models[name] = selected
    counts = {name: len(rows) for name, rows in models.items()}
    if len(set(counts.values())) != 1:
        raise SystemExit(f"inconsistent primary row counts: {counts}")

    keys = [(row["id"], row["question"]) for row, _, _ in models[RUNS[0]]]
    for name in RUNS:
        if [(row["id"], row["question"]) for row, _, _ in models[name]] != keys:
            raise SystemExit(f"pairing mismatch for {name}")

    clusters = np.asarray([record["group_id"] for _, record, _ in models[RUNS[0]]])
    state_chars = np.asarray([record["state_chars"] for _, record, _ in models[RUNS[0]]])
    option_counts = np.asarray([len(row["keys"]) for row, _, _ in models[RUNS[0]]])
    kinds = np.asarray([row["type"] for row, _, _ in models[RUNS[0]]])
    domains = np.asarray([record["domain"] for _, record, _ in models[RUNS[0]]])

    per_model = {}
    arrays = {}
    for name in RUNS:
        probs_served = [row_probs(row, raw=False) for row, _, _ in models[name]]
        probs_raw = [row_probs(row, raw=True) for row, _, _ in models[name]]
        labels = np.asarray([int(row["label"]) for row, _, _ in models[name]])
        conf = np.asarray([float(p.max()) for p in probs_served])
        pred = np.asarray([int(np.argmax(p)) for p in probs_served])
        correct = pred == labels
        brier = np.asarray([float(((p - np.eye(len(p))[y]) ** 2).sum()) for p, y in zip(probs_served, labels)])
        nll = np.asarray([nll_of(row, p) for (row, _, _), p in zip(models[name], probs_served)])
        raw_conf = np.asarray([float(p.max()) for p in probs_raw])
        raw_correct = np.asarray([int(np.argmax(p)) == y for p, y in zip(probs_raw, labels)])
        noul_mask = kinds == "noul"
        score_mask = kinds == "score"
        arrays[name] = {"correct": correct, "brier": brier, "nll": nll, "conf": conf,
                        "prob_served": probs_served, "labels": labels, "pred": pred}
        entry = {
            "label": LABELS[name],
            "n": int(len(labels)),
            "acc": float(correct.mean()),
            "acc_ci": wilson(int(correct.sum()), len(correct)),
            "brier": float(brier.mean()),
            "nll": float(nll.mean()),
            "mean_conf": float(conf.mean()),
            "confident_error_rate": float(((conf >= 0.9) & ~correct).mean()),
            "coverage_at_0_9": float((conf >= 0.9).mean()),
            "reliability": ece_bins(conf, correct),
            "reliability_raw": ece_bins(raw_conf, raw_correct),
            "ece_10": ece_from_bins(ece_bins(conf, correct, 10)),
            "ece_15": ece_from_bins(ece_bins(conf, correct, 15)),
            "risk_curve": None,
            "coverage_at_5pct": coverage_at_error(conf, correct, 0.05),
            "coverage_at_1pct": coverage_at_error(conf, correct, 0.01),
            "aurc": aurc(conf, correct),
            "confidence_accuracy": [],
            "kind": {},
            "domain": {},
            "option_bucket": {},
            "state_chars_bucket": {},
            "score_error_hist": None,
            "score_matrix": None,
            "brier_decomposition_noul": None,
            "noul_reliability": None,
        }
        accepted, errors, total = risk_curve(conf, correct)
        points = np.linspace(0, len(accepted) - 1, 61).astype(int)
        entry["risk_curve"] = [[float(accepted[i] / total), float(errors[i] / accepted[i])] for i in points]
        deciles = np.argsort(np.argsort(conf)) * 10 // len(conf)
        for d in range(10):
            mask = deciles == d
            entry["confidence_accuracy"].append([d, float(conf[mask].mean()), float(correct[mask].mean()), int(mask.sum())])
        def strata(mask_array, values):
            out = {}
            for value in sorted(set(values.tolist())):
                mask = values == value
                if not mask.any():
                    continue
                k = int(correct[mask].sum())
                n = int(mask.sum())
                out[str(value)] = {"n": n, "acc": k / n, "acc_ci": wilson(k, n),
                                   "brier": float(brier[mask].mean()),
                                   "ece_15": ece_from_bins(ece_bins(conf[mask], correct[mask], 15))}
            return out
        entry["kind"] = strata(kinds, kinds)
        entry["domain"] = strata(domains, domains)
        option_bucket = np.asarray(["2" if c == 2 else "3-4" if c <= 4 else "5-8" if c <= 8 else "9-26" if c <= 26 else ">26" for c in option_counts])
        entry["option_bucket"] = strata(option_bucket, option_bucket)
        char_bucket = np.asarray(["<=400" if c <= 400 else "401-1200" if c <= 1200 else "1201-3000" if c <= 3000 else ">3000" for c in state_chars])
        entry["state_chars_bucket"] = strata(char_bucket, char_bucket)
        # score expected-level error
        if score_mask.any():
            expected = np.asarray([float(np.dot(np.arange(len(p)), p)) for (row, _, _), p in zip(models[name], probs_served)])
            gold = labels.astype(float)
            errors_abs = np.abs(expected[score_mask] - gold[score_mask])
            hist, edges = np.histogram(errors_abs, bins=[0, 0.5, 1, 1.5, 2, 3, 4, 8])
            entry["score_error_hist"] = {"edges": [float(e) for e in edges], "counts": [int(c) for c in hist]}
            matrix = np.zeros((5, 5), dtype=int)
            pred_level = np.clip(np.rint(expected[score_mask]).astype(int), 0, 4)
            gold_level = np.clip(gold[score_mask].astype(int), 0, 4)
            for g, p in zip(gold_level, pred_level):
                matrix[g, p] += 1
            entry["score_matrix"] = matrix.tolist()
        if noul_mask.any():
            p_yes = np.asarray([float(p[1]) for (row, _, _), p in zip(models[name], probs_served) if row["type"] == "noul"])
            y_yes = labels[noul_mask].astype(bool)
            entry["noul_reliability"] = ece_bins(p_yes, y_yes)
            entry["brier_decomposition_noul"] = brier_decomposition(p_yes, y_yes)
        per_model[name] = entry

    paired = {}
    for seed in ["seed43", "seed17", "seed29"]:
        base = arrays["kev-original"]
        cand = arrays[seed]
        b = int((base["correct"] & ~cand["correct"]).sum())
        c = int((cand["correct"] & ~base["correct"]).sum())
        delta = {
            "n": int(len(base["correct"])),
            "mcnemar": mcnemar_exact(b, c),
            "delta_acc": float(cand["correct"].mean() - base["correct"].mean()),
            "delta_brier": float(cand["brier"].mean() - base["brier"].mean()),
            "delta_nll": float(cand["nll"].mean() - base["nll"].mean()),
        }
        for metric, arr_a, arr_b in (("acc", base["correct"].astype(float), cand["correct"].astype(float)),
                                     ("brier", base["brier"], cand["brier"]),
                                     ("nll", base["nll"], cand["nll"])):
            draws = -cluster_bootstrap_delta(arr_a, arr_b, clusters, metric, seed=0)
            delta["bootstrap_" + metric] = {
                "delta": float(arr_b.mean() - arr_a.mean()),
                "ci": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
                "hist": histogram(draws, bins=42),
            }
        delta["permutation_acc"] = permutation_delta((cand["correct"].astype(float) - base["correct"].astype(float)), clusters)
        delta["permutation_brier"] = permutation_delta((cand["brier"] - base["brier"]), clusters)
        delta["permutation_nll"] = permutation_delta((cand["nll"] - base["nll"]), clusters)
        paired[seed] = delta
    # paired per-stratum changes and per-question delta distributions
    kind_domain_keys = np.asarray([kd[0] + " / " + kd[1] for kd in zip(kinds, domains)])
    for seed in ["seed43", "seed17", "seed29"]:
        base = arrays["kev-original"]
        cand = arrays[seed]
        entry = {"kind": {}, "domain": {}, "option_bucket": {}, "kind_domain": {}}
        for label, values in (("kind", kinds), ("domain", domains), ("option_bucket", option_bucket),
                              ("kind_domain", kind_domain_keys)):
            for value in sorted(set(values.tolist())):
                mask = values == value
                entry[label][str(value)] = {"n": int(mask.sum()),
                                            "delta_acc": float(cand["correct"][mask].mean() - base["correct"][mask].mean()),
                                            "base_acc": float(base["correct"][mask].mean()),
                                            "cand_acc": float(cand["correct"][mask].mean())}
        diff_brier = cand["brier"] - base["brier"]
        diff_conf = cand["conf"] - base["conf"]
        entry["brier_delta_hist"] = histogram(diff_brier, bins=60)
        entry["confidence_delta_hist"] = histogram(diff_conf, bins=60)
        paired[seed]["strata_pairs"] = entry
    acc_p = [paired[s]["mcnemar"]["p_value"] for s in ["seed43", "seed17", "seed29"]]
    brier_p = [paired[s]["permutation_brier"]["p_value"] for s in ["seed43", "seed17", "seed29"]]
    paired_holm = {"acc": dict(zip(["seed43", "seed17", "seed29"], holm(acc_p))),
                   "brier": dict(zip(["seed43", "seed17", "seed29"], holm(brier_p)))}

    sample_curve = {}
    for name in ["kev-original", "seed43"]:
        correct = arrays[name]["correct"]
        p = float(correct.mean())
        curve = []
        for n in (100, 200, 400, 800, 1600, 3200, 6400):
            if n > len(correct):
                continue
            lo, hi = wilson(int(round(p * n)), n)
            curve.append([n, (hi - lo) / 2])
        sample_curve[name] = curve

    variants = {}
    for name in RUNS:
        rows = load_json(PRIV / "runs" / name / "rows.json")
        clean = {(row["id"], row["question"]): row for row in rows if row.get("variant") == "clean"}
        out = {}
        for variant in ("permuted", "isolation"):
            pairs = []
            for row in rows:
                if row.get("variant") != variant:
                    continue
                parent = row.get("parent")
                base = clean.get((parent, row["question"]))
                if base is None:
                    continue
                bmap = dict(zip(base["keys"], base["p"]))
                cmap = dict(zip(row["keys"], row["p"]))
                if set(bmap) != set(cmap):
                    continue
                delta = max(abs(cmap[k] - bmap[k]) for k in bmap)
                order = [k for k in base["keys"]]
                flip = int(np.argmax([cmap[k] for k in order]) != np.argmax([bmap[k] for k in order]))
                pairs.append((delta, flip))
            if pairs:
                deltas = np.asarray([p[0] for p in pairs])
                flips = np.asarray([p[1] for p in pairs], dtype=float)
                out[variant] = {"n": len(pairs), "mean_delta": float(deltas.mean()),
                                "median_delta": float(np.median(deltas)),
                                "p95_delta": float(np.quantile(deltas, 0.95)),
                                "flip_rate": float(flips.mean()),
                                "ecdf": ecdf_points(deltas),
                                "flip_counts": [int(flips.sum()), int(len(flips) - flips.sum())]}
        variants[name] = out

    jev = load_json(PRIV.parent / "jev-runs" / "jev-summary-final.json") if (PRIV.parent / "jev-runs" / "jev-summary-final.json").is_file() else None
    import glob
    jev_files = {}
    for name in ("kev-original", "seed43"):
        path = Path("/home/wenbo/jev-runs") / (name + "-jevbench-mini.json")
        if path.is_file():
            report = load_json(path)
            scores = report.get("scores", {})
            jev_files[name] = {
                "overall": float(scores.get("overall")),
                "ci": scores.get("ci", {}).get("overall"),
                "pillars": {k: float(v) for k, v in (scores.get("pillars") or {}).items()},
                "n_cases": scores.get("n_cases"),
                "min_n": scores.get("min_n"),
                "suite": report.get("result", {}).get("suite"),
            }
    local_kev = jev_files.get("kev-original")
    official_kev = None
    official_ci = None
    official_dims = None
    official_accuracy = None
    leaderboard = []
    official_test = None
    try:
        from huggingface_hub import hf_hub_download
        lb_path = hf_hub_download("JevBench/jevbench", "data/leaderboard.jsonl", repo_type="dataset")
        for line in Path(lb_path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            entry = {"model": row.get("model"), "name": row.get("name") or row.get("model"),
                     "family": row.get("family"), "reference": bool(row.get("reference")),
                     "overall": float(row["overall"]), "ci": [float(row["ci_low"]), float(row["ci_high"])],
                     "rank": [row.get("rank_low"), row.get("rank_high")],
                     "accuracy": row.get("accuracy"), "brier": row.get("brier"), "log_loss": row.get("log_loss"),
                     "dims": {k: row.get(k) for k in ("REP", "BAT", "MEA", "LOG", "CHO")}}
            leaderboard.append(entry)
            if entry["model"] == "kev-4b":
                official_kev = entry["overall"]
                official_ci = entry["ci"]
                official_dims = entry["dims"]
                official_accuracy = entry["accuracy"]
    except Exception as error:
        print("warning: could not load official JevBench leaderboard:", error)
        leaderboard = []
    def two_sample(local, official_overall, official_interval):
        se_local = (local["ci"][1] - local["ci"][0]) / (2 * 1.959964)
        se_official = (official_interval[1] - official_interval[0]) / (2 * 1.959964)
        se = math.sqrt(se_local ** 2 + se_official ** 2)
        z = (local["overall"] - official_overall) / se
        p = math.erfc(abs(z) / math.sqrt(2))
        return {"delta": local["overall"] - official_overall, "se": se, "z": z, "p_value": p,
                "local_ci": local["ci"], "official_ci": official_interval,
                "local_temperature": None}
    if local_kev and local_kev["ci"] and official_ci:
        official_test = two_sample(local_kev, official_kev, official_ci)
    seed_test = None
    if "seed43" in jev_files and jev_files["seed43"].get("ci") and official_ci:
        seed_test = two_sample(jev_files["seed43"], official_kev, official_ci)

    # dataset profile: original holdout counts and the rows actually evaluated in the primary analysis
    items_path = PRIV / "items.jsonl"
    items = []
    with items_path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                items.append(json.loads(line))
    kind_counts = {"choice": 0, "noul": 0, "score": 0}
    option_counts_all = []
    state_chars_all = []
    domain_counts = {"decision_mechanics": 0, "knowledge_reasoning": 0}
    for item in items:
        state_chars_all.append(len(str(item.get("state") or "")))
        domain = item.get("domain")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        for question in item.get("questions") or []:
            kind = question.get("kind")
            kind_counts[kind] = kind_counts.get(kind, 0) + 1
            options = question.get("options") or []
            scale = question.get("scale") or {}
            if kind == "score":
                option_counts_all.append(int(scale.get("max", 0)) - int(scale.get("min", 0)) + 1)
            else:
                option_counts_all.append(len(options))
    state_chars_all = np.asarray(state_chars_all, dtype=float)
    option_counts_all = np.asarray(option_counts_all, dtype=float)
    dataset = {
        "items": len(items),
        "questions": int(sum(kind_counts.values())),
        "kind_questions": kind_counts,
        "domain_items": domain_counts,
        "evaluated_items": int(len(set(record_id for (record_id, question) in keys))),
        "evaluated_questions": int(len(keys)),
        "evaluated_kind_questions": {k: int(sum(1 for row, _, _ in models["kev-original"] if row["type"] == k)) for k in ("choice", "noul", "score")},
        "state_chars": {"p10": float(np.percentile(state_chars_all, 10)), "p50": float(np.percentile(state_chars_all, 50)),
                        "p90": float(np.percentile(state_chars_all, 90)), "max": float(state_chars_all.max())},
        "state_chars_hist": histogram(state_chars_all, bins=36),
        "option_counts_hist": histogram(option_counts_all, bins=[2, 3, 4, 5, 6, 7, 8, 9, 10, 13, 16, 21, 26, 41, 80]),
    }
    state_tokens = json.loads((PRIV / "training-context-stats.json").read_text(encoding="utf-8"))["state_tokens"]
    dataset["state_tokens"] = state_tokens
    output = {
        "schema": "kev-prefix-deep-stats/1",
        "dataset": dataset,
        "generated_at": "2026-10-28",
        "n_primary": int(len(keys)),
        "n_clusters": int(len(set(clusters.tolist()))),
        "cluster_definition": "item/record cluster with declared-group merge",
        "models": RUNS,
        "labels": LABELS,
        "per_model": per_model,
        "paired": paired,
        "paired_holm": paired_holm,
        "sample_size_curve": sample_curve,
        "variants": variants,
        "jevbench": {"files": jev_files, "official_kev": official_kev,
                     "official_kev_ci": official_ci, "official_dims": official_dims,
                     "official_accuracy": official_accuracy,
                     "leaderboard": leaderboard,
                     "official_vs_local": official_test, "official_vs_seed43": seed_test},
    }
    out_path = Path("/home/wenbo/priv-eval/deep-stats.json")
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", out_path, "models", RUNS, "n", len(keys), "clusters", output["n_clusters"])


if __name__ == "__main__":
    main()