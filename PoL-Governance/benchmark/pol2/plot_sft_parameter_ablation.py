"""Render the parameter-ablation results as a compact research figure."""
from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "PoL-Governance" / "benchmark" / "pol2" / "results" / "sft-parameter-ablation-20261028"
OUT = ROOT / "Research" / "figures" / "pol2-sft-parameter-ablation-20261028"
SEEDS = (20261026, 20261027, 20261028)


def boot(values: list[float], seed: int, n: int = 10000) -> tuple[float, float, float]:
    rng = random.Random(seed)
    draws = sorted(statistics.mean(rng.choice(values) for _ in values) for _ in range(n))
    return statistics.mean(values), draws[249], draws[9749]


def main() -> None:
    summary = json.loads((DATA / "results.json").read_text(encoding="utf-8"))
    preds: dict[str, dict[str, dict]] = defaultdict(dict)
    for line in (DATA / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        preds[row["arm"]][row["case_id"]] = row

    case_ids = sorted(preds["base"])
    full_arms = [f"sft_seed_{s}" for s in SEEDS]
    head_arms = [f"sft_head_plus_initial_lora_seed_{s}" for s in SEEDS]
    case_values = {
        "Base checkpoint": {c: preds["base"][c]["accuracy"] for c in case_ids},
        "Rule summaries": {c: preds["retrieval"][c]["accuracy"] for c in case_ids},
        "SFT head + initial LoRA": {c: statistics.mean(preds[a][c]["accuracy"] for a in head_arms) for c in case_ids},
        "Full PoL2 SFT": {c: statistics.mean(preds[a][c]["accuracy"] for a in full_arms) for c in case_ids},
    }

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
        "axes.titlesize": 12, "axes.labelsize": 10, "xtick.labelsize": 9,
        "ytick.labelsize": 9, "pdf.fonttype": 42, "ps.fonttype": 42,
        "axes.spines.top": False, "axes.spines.right": False})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 4.75), gridspec_kw={"width_ratios": [1.02, 1.2]})
    fig.subplots_adjust(left=.09, right=.98, top=.81, bottom=.2, wspace=.35)
    colors = ["#697586", "#537A9B", "#C18A36", "#176B58"]

    # Panel A: paired-case bootstrap intervals, averaging repeated SFT seeds first.
    for i, (label, values) in enumerate(case_values.items()):
        mean, lo, hi = boot(list(values.values()), 20261031 + i)
        ax1.errorbar(mean, i, xerr=[[mean - lo], [hi - mean]], fmt="o", ms=7,
                     color=colors[i], ecolor=colors[i], capsize=3, lw=1.8, zorder=3)
        ax1.text(hi + .012, i, f"{mean*100:.1f}%", va="center", fontsize=9, color="#263238")
    ax1.axvline(.593, color="#8A7A58", ls=(0, (4, 3)), lw=1.1, alpha=.9)
    ax1.set_yticks(range(4), list(case_values))
    ax1.invert_yaxis()
    ax1.set_xlim(.30, .91)
    ax1.set_xlabel("Accepted-verdict accuracy (95% case bootstrap interval)")
    ax1.set_title("A  Learned LoRA adds beyond the SFT head", loc="left", fontweight="bold", pad=12)
    ax1.grid(axis="x", color="#D9DEE5", lw=.7, alpha=.75)
    ax1.set_axisbelow(True)

    # Panel B: paired full-SFT minus same-head/pretrained-LoRA delta by stage.
    stage_order = ["requirement", "plan", "operation", "output", "clarification", "knowledge_update"]
    stage_labels = {"requirement": "Requirement", "plan": "Plan", "operation": "Operation",
                    "output": "Output", "clarification": "Clarification", "knowledge_update": "Knowledge update"}
    ys, labels, means, los, his = [], [], [], [], []
    for stage in stage_order:
        ids = [c for c in case_ids if preds["base"][c]["stage"] == stage]
        if not ids:
            continue
        diffs = [statistics.mean(preds[a][c]["accuracy"] for a in full_arms)
                 - statistics.mean(preds[a][c]["accuracy"] for a in head_arms) for c in ids]
        m, lo, hi = boot(diffs, 20261040 + len(ys))
        ys.append(len(ys)); labels.append(f"{stage_labels[stage]}  (n={len(ids)})")
        means.append(m); los.append(lo); his.append(hi)
    for y, m, lo, hi in zip(ys, means, los, his):
        color = "#176B58" if m >= 0 else "#B5534B"
        ax2.errorbar(m * 100, y, xerr=[[(m - lo) * 100], [(hi - m) * 100]], fmt="o", ms=6,
                     color=color, ecolor=color, capsize=2.8, lw=1.6, zorder=3)
    ax2.axvline(0, color="#525A63", lw=1)
    ax2.set_yticks(ys, labels)
    ax2.invert_yaxis()
    ax2.set_xlabel("Accuracy gain from learned LoRA (percentage points)")
    ax2.set_title("B  LoRA effect varies by review stage", loc="left", fontweight="bold", pad=12)
    ax2.grid(axis="x", color="#D9DEE5", lw=.7, alpha=.75)
    ax2.set_axisbelow(True)

    fig.suptitle("Parameter ablation of prompt-free PoL2 decision behavior", x=.09, y=.97,
                 ha="left", fontsize=15, fontweight="bold", color="#172B3A")
    fig.text(.09, .89, "Same 81-case evaluation used in the prior pilot · 3 SFT seeds · 7 candidate-order rotations",
             ha="left", fontsize=9.5, color="#53616E")
    fig.text(.09, .055, "Dashed line: 59.3% majority-label baseline from the training split. Intervals resample cases; small stage slices are uncertain.",
             ha="left", fontsize=8.5, color="#59636E")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT.with_suffix(".png"), dpi=320, facecolor="white", bbox_inches="tight")
    fig.savefig(OUT.with_suffix(".pdf"), facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"png": str(OUT.with_suffix('.png')), "pdf": str(OUT.with_suffix('.pdf')),
                      "overall_delta_pp": summary["paired_bootstrap"]["full_sft_vs_sft_head_plus_initial_lora"]["mean_difference"] * 100}))


if __name__ == "__main__":
    main()
