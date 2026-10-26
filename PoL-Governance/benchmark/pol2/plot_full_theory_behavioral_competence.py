"""Make the figure for the bounded PoL2 candidate-behavior evaluation."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

COLORS = {"Base": "#667085", "Rule summaries": "#D18B47", "Parameter SFT": "#147D78"}
SEEDS = (20261026, 20261027, 20261028)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True, help="Output base path, without extension")
    args = ap.parse_args()
    root = args.results
    data = json.loads((root / "results.json").read_text(encoding="utf-8"))
    preds = [json.loads(line) for line in (root / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    grouped = defaultdict(dict)
    for row in preds:
        grouped[row["arm"]][row["case_id"]] = row
    arms = ["base", "retrieval"] + [f"sft_seed_{seed}" for seed in SEEDS]
    labels = list(grouped["base"])
    base = data["base"]["case_order_accuracy"]
    retrieval = data["retrieval"]["case_order_accuracy"]
    sft_vals = [data["parameter_sft_seed_results"][i]["test"]["case_order_accuracy"] for i in range(len(SEEDS))]
    sft_mean = statistics.mean(sft_vals)

    plt.rcParams.update({
        "font.family": "Arial", "font.size": 9,
        "axes.titlesize": 11, "axes.labelsize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "svg.fonttype": "none", "pdf.fonttype": 42,
    })
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(10.4, 4.05), gridspec_kw={"width_ratios": [0.94, 1.4]})

    ax0.set_title("A  Overall accepted-verdict match", loc="left", fontweight="bold", pad=10)
    names = ["Base", "Rule summaries", "Parameter SFT"]
    means = [base, retrieval, sft_mean]
    xs = [0, 1, 2]
    for x, name, mean in zip(xs, names, means):
        ax0.bar(x, mean * 100, width=.58, color=COLORS[name], alpha=.90, zorder=2)
        ax0.text(x, mean * 100 + 2, f"{mean*100:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")
    offsets = [-.12, 0, .12]
    for i, value in enumerate(sft_vals):
        ax0.scatter([2 + offsets[i]], [value * 100], s=28, color="white", edgecolor=COLORS["Parameter SFT"], linewidth=1.5, zorder=4)
    train_counts = defaultdict(int)
    for row in json.loads("[" + ",".join((root / "train_cases.jsonl").read_text(encoding="utf-8").splitlines()) + "]"):
        for verdict in row["expected_verdict_in"]:
            train_counts[verdict] += 1
    majority_label = max(train_counts, key=train_counts.get)
    test_cases = json.loads("[" + ",".join((root / "test_cases_deduplicated.jsonl").read_text(encoding="utf-8").splitlines()) + "]")
    majority = sum(majority_label in r["expected_verdict_in"] for r in test_cases) / len(test_cases)
    ax0.axhline(majority * 100, color="#98A2B3", linestyle=(0, (4, 3)), linewidth=1.1, zorder=1)
    ax0.set_xticks(xs, names)
    ax0.set_ylim(0, 100)
    ax0.set_ylabel("Accepted verdicts (%)")
    ax0.grid(axis="y", color="#E8EBEF", linewidth=.8, zorder=0)
    ax0.set_axisbelow(True)

    ax1.set_title("B  Performance by review stage", loc="left", fontweight="bold", pad=25)
    stages = sorted({row["stage"] for row in grouped["base"].values()})
    stage_labels = {
        "requirement": "Requirement", "plan": "Plan", "operation": "Operation",
        "output": "Output", "clarification": "Clarification", "knowledge_update": "Knowledge update",
    }
    y = list(range(len(stages)))
    height = .22
    for offset, arm, label, color in [(-height, "base", "Base", COLORS["Base"]),
                                      (0, "retrieval", "Rule summaries", COLORS["Rule summaries"])]:
        vals = [statistics.mean(grouped[arm][cid]["order_accuracy"] for cid in labels
                                if grouped["base"][cid]["stage"] == stage) for stage in stages]
        ax1.barh([i + offset for i in y], [v * 100 for v in vals], height=height, color=color, label=label, zorder=2)
    vals = []
    for stage in stages:
        ids = [cid for cid in labels if grouped["base"][cid]["stage"] == stage]
        vals.append(statistics.mean(statistics.mean(grouped[f"sft_seed_{seed}"][cid]["order_accuracy"] for seed in SEEDS) for cid in ids))
    ax1.barh([i + height for i in y], [v * 100 for v in vals], height=height, color=COLORS["Parameter SFT"], label="Parameter SFT", zorder=2)
    counts = {stage: sum(grouped["base"][cid]["stage"] == stage for cid in labels) for stage in stages}
    ax1.set_yticks(y, [f"{stage_labels[s]}  (n={counts[s]})" for s in stages])
    ax1.invert_yaxis()
    ax1.set_xlim(0, 105)
    ax1.set_xlabel("Accepted verdicts across seven option rotations (%)")
    ax1.grid(axis="x", color="#E8EBEF", linewidth=.8, zorder=0)
    ax1.set_axisbelow(True)
    ax1.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(.57, 1.005), fontsize=7.5)

    fig.text(.01, .005,
             f"Dashed line: train-majority '{majority_label}' baseline ({majority*100:.1f}%). Cases are candidate labels, not validated gold; hollow points show 3 SFT seeds.",
             fontsize=7.2, color="#56616D")
    fig.tight_layout(rect=[0, .06, 1, .94], w_pad=2.5)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(args.output.with_suffix(f".{ext}"), dpi=320, bbox_inches="tight")


if __name__ == "__main__":
    main()
