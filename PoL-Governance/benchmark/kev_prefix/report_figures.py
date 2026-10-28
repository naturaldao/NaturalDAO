#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Matplotlib SVG figures for the Kev prefix-evaluation HTML report.

Consumes deep-stats.json (aggregate-only statistics), plus the aggregate JSON files for a
few cross-checks. Returns a dict of inline SVG strings; no files are written here.
"""
from __future__ import annotations

import io
import json
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

INK = "#14213d"
MUTED = "#667085"
LINE = "#e4e7ec"
GRID = "#eef0f4"
COLORS = {"kev-original": "#1f7a8c", "seed43": "#e07a5f", "seed17": "#6b7c93", "seed29": "#b08d57"}
LABELS = {"kev-original": "Kev-4B original", "seed43": "M10 seed-43", "seed17": "M10 seed-17", "seed29": "M10 seed-29"}
MODELS = ["kev-original", "seed43", "seed17", "seed29"]

_SVG_PNGS = []

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": LINE,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 100,
    "svg.fonttype": "none",
    "svg.hashsalt": "kev-report",
})


def _svg(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.06, transparent=False,
                facecolor="white")
    png_buf = io.BytesIO()
    fig.savefig(png_buf, format="png", dpi=130, bbox_inches="tight", pad_inches=0.08,
                transparent=False, facecolor="white")
    _SVG_PNGS.append(png_buf.getvalue())
    plt.close(fig)
    svg = buf.getvalue()
    svg = svg[svg.find("<svg"):]
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg, flags=re.S)
    svg = svg.replace("<svg ", '<svg style="max-width:100%;height:auto" ', 1)
    return svg


def get_pngs():
    return list(_SVG_PNGS)


def _pct(x):
    return 100.0 * float(x)


def fig_dataset(deep):
    ds = deep["dataset"]
    fig, axes = plt.subplots(1, 2, figsize=(9.8, 2.8))
    hist = ds["state_chars_hist"]
    centres = [(hist["edges"][i] + hist["edges"][i + 1]) / 2 for i in range(len(hist["counts"]))]
    widths = [(hist["edges"][i + 1] - hist["edges"][i]) for i in range(len(hist["counts"]))]
    axes[0].bar(centres, hist["counts"], width=widths, color="#1f7a8c", alpha=0.8)
    axes[0].set_xlabel("State length (characters)")
    axes[0].set_ylabel("Items")
    axes[0].set_title("How long is the input text?", fontsize=10)
    hist2 = ds["option_counts_hist"]
    centres = [(hist2["edges"][i] + hist2["edges"][i + 1]) / 2 for i in range(len(hist2["counts"]))]
    widths = [(hist2["edges"][i + 1] - hist2["edges"][i]) for i in range(len(hist2["counts"]))]
    axes[1].bar(centres, hist2["counts"], width=widths, color="#e07a5f", alpha=0.8)
    axes[1].set_xlabel("Answer options per question")
    axes[1].set_ylabel("Questions")
    axes[1].set_title("How many options must be compared?", fontsize=10)
    axes[1].set_xscale("log")
    ticks = [2, 3, 5, 8, 13, 21, 34, 55, 68]
    axes[1].set_xticks(ticks)
    axes[1].set_xticklabels([str(t) for t in ticks], fontsize=7)
    axes[1].minorticks_off()
    return _svg(fig)


def fig_accuracy(deep):
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    models = MODELS
    acc = [deep["per_model"][m]["acc"] for m in models]
    ci_lo = [deep["per_model"][m]["acc_ci"][0] for m in models]
    ci_hi = [deep["per_model"][m]["acc_ci"][1] for m in models]
    y = np.arange(len(models))[::-1]
    ax.barh(y, [a * 100 for a in acc], color=[COLORS[m] for m in models], height=0.55, alpha=0.9)
    ax.errorbar([a * 100 for a in acc], y, xerr=[[(a - l) * 100 for a, l in zip(acc, ci_lo)],
                                                 [(h - a) * 100 for a, h in zip(acc, ci_hi)]],
                fmt="none", ecolor=INK, elinewidth=1.2, capsize=4)
    for yi, a in zip(y, acc):
        ax.text(a * 100 + 0.35, yi, f"{a*100:.2f}%", va="center", fontsize=9, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels([LABELS[m] for m in models], color=INK)
    ax.set_xlabel("Accuracy (%) with 95% Wilson interval")
    ax.set_xlim(min(ci_lo) * 100 - 2.5, max(ci_hi) * 100 + 2.5)
    ax.grid(axis="y", visible=False)
    return _svg(fig)


def fig_forest(deep, agg):
    metrics = [("bootstrap_acc", "Accuracy (pp)", 100.0), ("bootstrap_brier", "Brier", 1.0),
               ("bootstrap_nll", "NLL", 1.0)]
    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.0), gridspec_kw={"width_ratios": [1.15, 1, 1]})
    for ax, (key, label, scale) in zip(axes, metrics):
        rows = []
        for si, seed in enumerate(["seed43", "seed17", "seed29"]):
            data = deep["paired"][seed][key]
            rows.append((seed, data["delta"] * scale, data["ci"][0] * scale, data["ci"][1] * scale))
        y = np.arange(len(rows))[::-1]
        for yi, (seed, delta, lo, hi) in zip(y, rows):
            color = COLORS[seed]
            ax.errorbar(delta, yi, xerr=[[delta - lo], [hi - delta]], fmt="o", color=color,
                        ecolor=color, elinewidth=1.4, capsize=4, markersize=6)
            ax.text(hi + (abs(hi - lo) * 0.03 + 0.0005 * scale), yi, f"{delta:+.3f}", va="center",
                    fontsize=8, color=INK)
        ax.axvline(0, color=MUTED, linewidth=1, linestyle="--")
        ax.set_yticks(y)
        ax.set_yticklabels([LABELS[s] for s in ["seed43", "seed17", "seed29"]], fontsize=8)
        ax.set_title(label + " change vs original", fontsize=10)
        ax.grid(axis="y", visible=False)
    fig.text(0.5, -0.02, "Points: paired cluster-bootstrap estimate; bars: 95% percentile interval (1,000 resamples). Positive = tuned model larger.",
             ha="center", fontsize=8, color=MUTED)
    return _svg(fig)


def _reliability(ax, bins, color, label):
    xs, ys, ns = [], [], []
    for lo, hi, count, mean_conf, acc, gap in bins:
        if count:
            xs.append(mean_conf * 100)
            ys.append(acc * 100)
            ns.append(count)
    ax.plot([0, 100], [0, 100], color=MUTED, linewidth=1, linestyle="--", label="perfect calibration")
    ax.plot(xs, ys, "o-", color=color, linewidth=1.6, markersize=4, label=label)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Mean predicted confidence in bin (%)")
    ax.set_ylabel("Observed accuracy in bin (%)")


def fig_reliability(deep):
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.5), sharey=True)
    for ax, mode, title in ((axes[0], "reliability", "as shipped (served)"),
                            (axes[1], "reliability_raw", "raw T = 1 (before shipped temperature)")):
        for model in ("kev-original", "seed43"):
            _reliability(ax, deep["per_model"][model][mode], COLORS[model], LABELS[model])
        ax.set_title(title, fontsize=10)
        ax.legend(fontsize=7, loc="upper left", frameon=False)
    fig.text(0.5, -0.04, "Each point is one of 15 confidence bins; distance from the diagonal is calibration error.",
             ha="center", fontsize=8, color=MUTED)
    return _svg(fig)


def fig_noul_reliability(deep):
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    for model in ("kev-original", "seed43"):
        bins = deep["per_model"][model]["noul_reliability"]
        xs = [b[3] * 100 for b in bins if b[2]]
        ys = [b[4] * 100 for b in bins if b[2]]
        ax.plot(xs, ys, "o-", color=COLORS[model], label=LABELS[model])
    ax.plot([0, 100], [0, 100], "--", color=MUTED, linewidth=1)
    ax.set_xlabel("Predicted P(yes) (%)")
    ax.set_ylabel("Observed P(yes) (%)")
    ax.set_title("Yes/no (noul) probability calibration", fontsize=10)
    ax.legend(fontsize=7, frameon=False)
    return _svg(fig)


def fig_risk_coverage(deep):
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for model in MODELS:
        curve = deep["per_model"][model]["risk_curve"]
        xs = [p[0] * 100 for p in curve]
        ys = [p[1] * 100 for p in curve]
        ax.plot(xs, ys, color=COLORS[model], linewidth=1.8, label=LABELS[model])
    ax.axhline(5, color="#c53030", linewidth=1, linestyle="--")
    ax.text(102, 5.6, "5% error budget", color="#c53030", fontsize=8, ha="left")
    ax.set_xlabel("Coverage: share of questions answered (%)")
    ax.set_ylabel("Selective risk: error rate on answered (%)")
    ax.set_title("Risk-coverage curves (lower is better)", fontsize=10)
    ax.legend(fontsize=7, frameon=False)
    ax.set_xlim(0, 100)
    return _svg(fig)


def fig_bootstrap(deep):
    fig, axes = plt.subplots(1, 3, figsize=(10.6, 2.9))
    specs = [("bootstrap_acc", 100.0, "Accuracy change (pp)"), ("bootstrap_brier", 1.0, "Brier change"),
             ("bootstrap_nll", 1.0, "NLL change")]
    for ax, (key, scale, label) in zip(axes, specs):
        data = deep["paired"]["seed43"][key]
        hist = data["hist"]
        centres = [(hist["edges"][i] + hist["edges"][i + 1]) / 2 * scale for i in range(len(hist["counts"]))]
        widths = [(hist["edges"][i + 1] - hist["edges"][i]) * scale for i in range(len(hist["counts"]))]
        ax.bar(centres, hist["counts"], width=widths, color=COLORS["seed43"], alpha=0.75)
        ax.axvline(0, color=MUTED, linewidth=1, linestyle=":")
        ax.axvline(data["delta"] * scale, color=INK, linewidth=1.4)
        for q in data["ci"]:
            ax.axvline(q * scale, color=INK, linewidth=1, linestyle="--")
        ax.set_title(label, fontsize=10)
        ax.set_yticks([])
        ax.grid(axis="y", visible=False)
    fig.text(0.5, -0.04, "Bootstrap distribution of the seed-43 minus original change (2,000 cluster resamples); black = estimate, dashed = 95% interval.",
             ha="center", fontsize=8, color=MUTED)
    return _svg(fig)


def fig_permutation(deep):
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 2.9))
    for ax, key, label in ((axes[0], "permutation_acc", "Accuracy change (pp)"),
                           (axes[1], "permutation_brier", "Brier change")):
        data = deep["paired"]["seed43"][key]
        hist = data["hist"]
        scale = 100.0 if "acc" in key else 1.0
        centres = [(hist["edges"][i] + hist["edges"][i + 1]) / 2 * scale for i in range(len(hist["counts"]))]
        widths = [(hist["edges"][i + 1] - hist["edges"][i]) * scale for i in range(len(hist["counts"]))]
        ax.bar(centres, hist["counts"], width=widths, color="#6b7c93", alpha=0.6)
        ax.axvline(data["observed"] * scale, color="#c53030", linewidth=1.5)
        ax.set_title(label + " under the null (p = " + f"{data['p_value']:.4f})", fontsize=10)
        ax.set_yticks([])
        ax.grid(axis="y", visible=False)
    fig.text(0.5, -0.04, "Cluster sign-flip randomization test: histogram is the distribution when the model label is randomly swapped; red line is the observed change.",
             ha="center", fontsize=8, color=MUTED)
    return _svg(fig)


def fig_confidence_deciles(deep):
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.1), sharey=True)
    for model in ("kev-original", "seed43"):
        rows = deep["per_model"][model]["confidence_accuracy"]
        xs = [r[0] for r in rows]
        conf = [r[1] * 100 for r in rows]
        acc = [r[2] * 100 for r in rows]
        axes[0].plot(xs, acc, "o-", color=COLORS[model], label=LABELS[model])
        axes[1].plot(xs, conf, "o-", color=COLORS[model], label=LABELS[model])
    axes[0].set_title("Accuracy by confidence decile", fontsize=10)
    axes[1].set_title("Mean confidence by decile", fontsize=10)
    for ax in axes:
        ax.set_xlabel("Confidence decile (0 = least confident)")
        ax.legend(fontsize=7, frameon=False)
    axes[0].set_ylabel("Accuracy (%)")
    axes[1].set_ylabel("Mean top-class probability (%)")
    return _svg(fig)


def fig_kind_bars(deep):
    fig, ax = plt.subplots(figsize=(7.6, 3.2))
    kinds = ["choice", "noul", "score"]
    width = 0.19
    x = np.arange(len(kinds))
    for i, model in enumerate(MODELS):
        vals, los, his = [], [], []
        for kind in kinds:
            item = deep["per_model"][model]["kind"][kind]
            vals.append(item["acc"] * 100)
            los.append((item["acc"] - item["acc_ci"][0]) * 100)
            his.append((item["acc_ci"][1] - item["acc"]) * 100)
        ax.bar(x + (i - 1.5) * width, vals, width, color=COLORS[model], label=LABELS[model], alpha=0.9)
        ax.errorbar(x + (i - 1.5) * width, vals, yerr=[los, his], fmt="none", ecolor=INK, elinewidth=0.9, capsize=2)
    ax.set_xticks(x)
    ax.set_xticklabels(["choice", "noul (yes/no)", "score (rating)"])
    ax.set_ylabel("Accuracy (%) with 95% Wilson interval")
    ax.set_title("Accuracy by question type", fontsize=10)
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.grid(axis="x", visible=False)
    return _svg(fig)


def fig_domain_bars(deep):
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    domains = ["decision_mechanics", "knowledge_reasoning"]
    x = np.arange(len(domains))
    width = 0.19
    for i, model in enumerate(MODELS):
        vals, los, his = [], [], []
        for domain in domains:
            item = deep["per_model"][model]["domain"][domain]
            vals.append(item["acc"] * 100)
            los.append((item["acc"] - item["acc_ci"][0]) * 100)
            his.append((item["acc_ci"][1] - item["acc"]) * 100)
        ax.bar(x + (i - 1.5) * width, vals, width, color=COLORS[model], label=LABELS[model], alpha=0.9)
        ax.errorbar(x + (i - 1.5) * width, vals, yerr=[los, his], fmt="none", ecolor=INK, elinewidth=0.9, capsize=2)
    ax.set_xticks(x)
    ax.set_xticklabels(["decision mechanics", "knowledge / reasoning"])
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Accuracy by domain", fontsize=10)
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.grid(axis="x", visible=False)
    return _svg(fig)


def fig_option_curve(deep):
    buckets = ["2", "3-4", "5-8", "9-26", ">26"]
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    for model in MODELS:
        xs, ys, los, his = [], [], [], []
        for i, bucket in enumerate(buckets):
            item = deep["per_model"][model]["option_bucket"].get(bucket)
            if not item:
                continue
            xs.append(i)
            ys.append(item["acc"] * 100)
            los.append((item["acc"] - item["acc_ci"][0]) * 100)
            his.append((item["acc_ci"][1] - item["acc"]) * 100)
        ax.errorbar(xs, ys, yerr=[los, his], fmt="o-", color=COLORS[model], label=LABELS[model],
                    linewidth=1.4, markersize=5, elinewidth=0.9, capsize=2)
    ax.set_xticks(range(len(buckets)))
    ax.set_xticklabels(["2", "3-4", "5-8", "9-26", ">26"])
    ax.set_xlabel("Number of answer options in the question")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Accuracy vs option count", fontsize=10)
    ax.legend(fontsize=7, frameon=False)
    return _svg(fig)


def fig_length_bars(deep):
    available = deep["per_model"][MODELS[0]]["state_chars_bucket"].keys()
    buckets = [b for b in ["<=400", "401-1200", "1201-3000", ">3000"] if b in available]
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    x = np.arange(len(buckets))
    width = 0.19
    for i, model in enumerate(MODELS):
        vals, los, his = [], [], []
        for bucket in buckets:
            item = deep["per_model"][model]["state_chars_bucket"][bucket]
            vals.append(item["acc"] * 100)
            los.append((item["acc"] - item["acc_ci"][0]) * 100)
            his.append((item["acc_ci"][1] - item["acc"]) * 100)
        ax.bar(x + (i - 1.5) * width, vals, width, color=COLORS[model], label=LABELS[model], alpha=0.9)
        ax.errorbar(x + (i - 1.5) * width, vals, yerr=[los, his], fmt="none", ecolor=INK, elinewidth=0.9, capsize=2)
    ax.set_xticks(x)
    ax.set_xticklabels(buckets, fontsize=8)
    ax.set_xlabel("Input length (characters)")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Accuracy by input length", fontsize=10)
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.grid(axis="x", visible=False)
    return _svg(fig)


def fig_kind_brier(deep):
    kinds = ["choice", "noul", "score"]
    fig, ax = plt.subplots(figsize=(7.0, 2.9))
    x = np.arange(len(kinds))
    width = 0.19
    for i, model in enumerate(MODELS):
        vals = [deep["per_model"][model]["kind"][k]["brier"] for k in kinds]
        ax.bar(x + (i - 1.5) * width, vals, width, color=COLORS[model], label=LABELS[model], alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(["choice", "noul", "score"])
    ax.set_ylabel("Brier (lower is better)")
    ax.set_title("Probability error by question type", fontsize=10)
    ax.legend(fontsize=7, frameon=False, ncol=2)
    ax.grid(axis="x", visible=False)
    return _svg(fig)


def fig_heatmap(deep):
    combo = deep["paired"]["seed43"]["strata_pairs"]["kind_domain"]
    kinds = ["choice", "noul", "score"]
    domains = ["decision_mechanics", "knowledge_reasoning"]
    matrix = np.zeros((len(domains), len(kinds)))
    counts = np.zeros((len(domains), len(kinds)), dtype=int)
    for j, domain in enumerate(domains):
        for i, kind in enumerate(kinds):
            key = kind + " / " + domain
            if key in combo:
                matrix[j, i] = combo[key]["delta_acc"] * 100
                counts[j, i] = combo[key]["n"]
    cmap = LinearSegmentedColormap.from_list("div", ["#c53030", "#f7f7f7", "#1f7a8c"])
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    limit = max(0.5, float(np.abs(matrix).max()))
    im = ax.imshow(matrix, cmap=cmap, vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(len(kinds)))
    ax.set_xticklabels(kinds)
    ax.set_yticks(range(len(domains)))
    ax.set_yticklabels(domains)
    for j in range(len(domains)):
        for i in range(len(kinds)):
            if counts[j, i]:
                ax.text(i, j, f"{matrix[j, i]:+.1f}pp\nn={counts[j, i]}", ha="center", va="center",
                        fontsize=8, color=INK)
    ax.set_title("seed-43 minus original accuracy (pp) by type x domain", fontsize=10)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Accuracy change (pp)")
    return _svg(fig)


def fig_sample_size(deep):
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    for model in ("kev-original", "seed43"):
        rows = deep["sample_size_curve"][model]
        ax.plot([r[0] for r in rows], [r[1] * 100 for r in rows], "o-", color=COLORS[model], label=LABELS[model])
    ax.set_xscale("log")
    ax.set_xlabel("Number of evaluation questions (log scale)")
    ax.set_ylabel("Half-width of 95% accuracy interval (pp)")
    ax.set_title("Why small samples cannot rank close models", fontsize=10)
    ax.legend(fontsize=7, frameon=False)
    return _svg(fig)


def fig_variant_ecdf(deep):
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.0), sharey=True)
    for ax, variant, title in ((axes[0], "permuted", "Option order permuted"),
                               (axes[1], "isolation", "Questions asked separately")):
        for model in MODELS:
            data = deep["variants"][model].get(variant)
            if not data:
                continue
            xs = [p[0] for p in data["ecdf"]]
            ys = [p[1] for p in data["ecdf"]]
            ax.plot(xs, ys, color=COLORS[model], linewidth=1.6, label=LABELS[model])
        ax.set_xlabel("Max probability change vs the original question")
        ax.set_title(title, fontsize=10)
    axes[0].set_ylabel("Share of questions at or below x")
    axes[0].set_xscale("symlog", linthresh=0.01)
    axes[1].set_xscale("symlog", linthresh=0.01)
    axes[0].legend(fontsize=7, frameon=False)
    axes[0].set_ylim(0, 1.02)
    return _svg(fig)


def fig_score_confusion(deep):
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.4))
    for ax, model in zip(axes, ("kev-original", "seed43")):
        matrix = np.asarray(deep["per_model"][model]["score_matrix"], dtype=float)
        matrix = matrix / np.maximum(matrix.sum(axis=1, keepdims=True), 1)
        im = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1)
        for i in range(5):
            for j in range(5):
                ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center",
                        fontsize=7, color="white" if matrix[i, j] > 0.55 else INK)
        ax.set_xticks(range(5))
        ax.set_yticks(range(5))
        ax.set_xlabel("Predicted level")
        ax.set_ylabel("Gold level")
        ax.set_title(LABELS[model], fontsize=9)
        ax.grid(False)
    return _svg(fig)


def fig_brier_decomp(deep):
    fig, ax = plt.subplots(figsize=(7.0, 2.9))
    models = ["kev-original", "seed43", "seed17", "seed29"]
    parts = [("reliability", "Reliability (↓ better)"), ("resolution", "Resolution (↑ better)")]
    width = 0.19
    x = np.arange(len(models))
    for i, (key, label) in enumerate(parts):
        vals = [deep["per_model"][m]["brier_decomposition_noul"][key] for m in models]
        ax.bar(x + (i - 0.5) * width, vals, width, color=["#c53030", "#1f7a8c"][i], label=label)
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[m] for m in models], fontsize=8)
    ax.set_ylabel("Brier component")
    ax.set_title("Yes/no Brier decomposition", fontsize=10)
    ax.legend(fontsize=7, frameon=False)
    ax.grid(axis="x", visible=False)
    return _svg(fig)


def fig_jev_radar(deep):
    dims = ["REP", "BAT", "MEA", "LOG", "CHO"]
    official = deep["jevbench"].get("official_dims") or {"REP": 0.744, "BAT": 1.0, "MEA": 0.301, "LOG": 0.675, "CHO": 0.875}
    angles = np.linspace(0, 2 * math.pi, len(dims), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(5.2, 4.4), subplot_kw={"polar": True})
    series = [("kev-original", "Kev-4B original (local)", COLORS["kev-original"], 1.6),
              ("seed43", "M10 seed-43 (local)", COLORS["seed43"], 1.6)]
    for key, label, color, linewidth in series:
        vals = [deep["jevbench"]["files"][key]["pillars"][d] * 100 for d in dims]
        vals += vals[:1]
        ax.plot(angles, vals, color=color, linewidth=linewidth, label=label)
        ax.fill(angles, vals, color=color, alpha=0.10)
    vals = [official[d] * 100 for d in dims]
    vals += vals[:1]
    ax.plot(angles, vals, color=MUTED, linewidth=1.2, linestyle="--", label="Kev-4B official leaderboard")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dims, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=7, color=MUTED)
    ax.set_title("JevBench coherence dimensions (higher = more coherent)", fontsize=10, pad=14)
    ax.legend(fontsize=7, loc="lower right", bbox_to_anchor=(1.15, -0.12), frameon=False)
    return _svg(fig)


def fig_jev_leaderboard(deep, leaderboard):
    rows = sorted([r for r in leaderboard if not r.get("reference")], key=lambda r: r["overall"])
    extra = sorted([r for r in leaderboard if r.get("reference")], key=lambda r: r["overall"])
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    ys = np.arange(len(rows))
    ax.scatter([r["overall"] * 100 for r in rows], ys, s=22, color=MUTED, alpha=0.65)
    for y, row in zip(ys, rows):
        ax.text(row["overall"] * 100 + 0.5, y, f"{row['overall']*100:.1f}", va="center", fontsize=6.5, color=MUTED)
    ax.set_yticks(ys)
    ax.set_yticklabels([r["name"] for r in rows], fontsize=6.2)
    ours = [("Kev-4B original (local, bf16)", deep["jevbench"]["files"]["kev-original"]["overall"] * 100, COLORS["kev-original"]),
            ("M10 seed-43 (local, bf16)", deep["jevbench"]["files"]["seed43"]["overall"] * 100, COLORS["seed43"])]
    for row in extra:
        ax.scatter(row["overall"] * 100, len(rows) + 0.6, s=20, marker="x", color="#c53030", alpha=0.7)
    for label, value, color in ours:
        ax.axvline(value, color=color, linewidth=1.4, linestyle="--")
        ax.text(value, len(rows) - 0.2, label, rotation=90, va="top", ha="right", fontsize=7, color=color)
    ax.set_xlabel("JevBench-mini coherence overall (0-100)")
    ax.set_title("Published JevBench leaderboard and our local runs", fontsize=10)
    ax.grid(axis="y", visible=False)
    return _svg(fig)


def fig_latency(deep, agg):
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    models = MODELS
    med = [agg["runs"][m]["run_metadata"]["latency_ms"]["median"] for m in models]
    p95 = [agg["runs"][m]["run_metadata"]["latency_ms"]["p95"] for m in models]
    x = np.arange(len(models))
    ax.bar(x - 0.18, med, 0.35, color=[COLORS[m] for m in models], alpha=0.9, label="median")
    ax.bar(x + 0.18, p95, 0.35, color=[COLORS[m] for m in models], alpha=0.45, label="p95")
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[m] for m in models], fontsize=8)
    ax.set_ylabel("Milliseconds per question")
    ax.set_yscale("log")
    ax.set_title("GPU latency per evaluation question (ms, log scale)", fontsize=10)
    ax.legend(fontsize=7, frameon=False)
    ax.grid(axis="x", visible=False)
    return _svg(fig)


def fig_score_error_hist(deep):
    fig, ax = plt.subplots(figsize=(6.2, 2.8))
    width = 0.38
    for i, model in enumerate(("kev-original", "seed43")):
        hist = deep["per_model"][model]["score_error_hist"]
        xs = np.arange(len(hist["counts"]))
        ax.bar(xs + (i - 0.5) * width, hist["counts"], width, color=COLORS[model], label=LABELS[model], alpha=0.9)
    ax.set_xticks(np.arange(7))
    ax.set_xticklabels(["0-0.5", "0.5-1", "1-1.5", "1.5-2", "2-3", "3-4", "4+"], fontsize=7)
    ax.set_xlabel("Absolute difference between expected and gold rating level")
    ax.set_ylabel("Number of score questions")
    ax.set_title("Score questions: how far off are the ratings?", fontsize=10)
    ax.legend(fontsize=7, frameon=False)
    ax.grid(axis="x", visible=False)
    return _svg(fig)


def build_figures(deep, agg, leaderboard):
    figs = {}
    figs["dataset"] = fig_dataset(deep)
    figs["accuracy"] = fig_accuracy(deep)
    figs["forest"] = fig_forest(deep, agg)
    figs["bootstrap"] = fig_bootstrap(deep)
    figs["permutation"] = fig_permutation(deep)
    figs["kind_bars"] = fig_kind_bars(deep)
    figs["length_bars"] = fig_length_bars(deep)
    figs["domain_bars"] = fig_domain_bars(deep)
    figs["option_curve"] = fig_option_curve(deep)
    figs["heatmap"] = fig_heatmap(deep)
    figs["kind_brier"] = fig_kind_brier(deep)
    figs["score_error_hist"] = fig_score_error_hist(deep)
    figs["sample_size"] = fig_sample_size(deep)
    figs["reliability"] = fig_reliability(deep)
    figs["noul_reliability"] = fig_noul_reliability(deep)
    figs["brier_decomp"] = fig_brier_decomp(deep)
    figs["risk_coverage"] = fig_risk_coverage(deep)
    figs["confidence_deciles"] = fig_confidence_deciles(deep)
    figs["variant_ecdf"] = fig_variant_ecdf(deep)
    figs["jev_radar"] = fig_jev_radar(deep)
    figs["jev_leaderboard"] = fig_jev_leaderboard(deep, leaderboard)
    figs["latency"] = fig_latency(deep, agg)
    return figs