"""Publication-style figure for the PoL2 activation interchange diagnostic."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
RESULT = HERE / "results" / "kev-pol2-counterfactual-causal-20261026" / "activation_interchange" / "results.json"
OUT = HERE.parents[3] / "Research" / "figures" / "pol2-field-activation-interchange-20261026"
FACTORS = ["authorization", "scope", "freshness", "location", "terminal"]
LABELS = ["Authorization", "Scope", "Freshness", "Location", "Terminal"]
BLUE = "#2864A5"
ORANGE = "#C65336"
GRAY = "#8A96A3"
INK = "#202B38"
MUTED = "#657487"
GRID = "#D9E0E7"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", type=Path, default=RESULT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    data = json.loads(args.result.read_text(encoding="utf-8"))
    rows = data["seed_results"]
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.labelsize": 9,
        "axes.titlesize": 11, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "axes.edgecolor": GRID, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": MUTED, "ytick.color": MUTED, "pdf.fonttype": 42,
        "ps.fonttype": 42, "figure.facecolor": "white", "axes.facecolor": "white",
    })
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.15), gridspec_kw={"width_ratios": [1.08, 1]})
    fig.subplots_adjust(left=.09, right=.985, bottom=.21, top=.80, wspace=.34)

    # Panel A: symmetric average of the two directional effects, shown by matched seed.
    x = np.arange(len(FACTORS))
    arms = [("task_only", GRAY, -.12), ("pol2_sft", BLUE, .12)]
    for factor_i, factor in enumerate(FACTORS):
        for arm, color, offset in arms:
            group = [r for r in rows if r["arm"] == arm and r["factor"] == factor]
            values = [((r["positive_state_into_negative_delta"] - r["negative_state_into_positive_delta"]) / 2) /
                      (r["positive_clean_margin"] - r["negative_clean_margin"]) for r in group]
            for seed_i, value in enumerate(values):
                jitter = (seed_i - 1) * .024
                ax1.scatter(x[factor_i] + offset + jitter, value, s=29, color=color,
                            edgecolor="white", linewidth=.55, zorder=3)
            ax1.scatter(x[factor_i] + offset, np.mean(values), s=95, marker="D", facecolor=color,
                        edgecolor="white", linewidth=1, zorder=4,
                        label=("Task-only SFT" if factor_i == 0 and arm == "task_only" else
                               "PoL2-contract SFT" if factor_i == 0 and arm == "pol2_sft" else None))
    ax1.axhline(0, color=INK, linewidth=.8)
    ax1.set_xticks(x, LABELS)
    ax1.set_ylabel("Fraction of clean action-margin gap transferred")
    ax1.set_ylim(0, 1.25)
    ax1.set_yticks([0, .25, .5, .75, 1, 1.25])
    ax1.legend(loc="upper left", frameon=False, fontsize=7.7, ncol=2, handletextpad=.4, columnspacing=.9)
    ax1.grid(axis="y", color=GRID, linewidth=.6, alpha=.8)
    ax1.set_axisbelow(True)
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.set_title("A  Bidirectional field-value interchange", loc="left", fontweight="bold", pad=10)

    # Panel B: one-layer authorization intervention. Individual seed curves are shown;
    # no inferential band is drawn because n=3 trained seeds is descriptive.
    auth = [r for r in rows if r["factor"] == "authorization"]
    layer_x = np.arange(1, len(auth[0]["positive_to_negative_layer_sweep"]) + 1)
    for arm, color, label in [("task_only", GRAY, "Task-only SFT"), ("pol2_sft", BLUE, "PoL2-contract SFT")]:
        arm_rows = [r for r in auth if r["arm"] == arm]
        curves = np.asarray([np.asarray(r["positive_to_negative_layer_sweep"]) /
                             (r["positive_clean_margin"] - r["negative_clean_margin"]) for r in arm_rows])
        for curve in curves:
            ax2.plot(layer_x, curve, color=color, alpha=.25, linewidth=1)
        ax2.plot(layer_x, curves.mean(axis=0), color=color, linewidth=2.2, label=label)
    ax2.axhline(0, color=INK, linewidth=.8)
    ax2.set_xlabel("Intervened transformer block")
    ax2.set_ylabel("Fraction of authorization margin gap transferred")
    ax2.set_xlim(1, 24)
    ax2.set_xticks([1, 4, 8, 12, 16, 20, 24])
    ax2.grid(axis="y", color=GRID, linewidth=.6, alpha=.8)
    ax2.set_axisbelow(True)
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.set_title("B  Authorization effect by block", loc="left", fontweight="bold", pad=10)
    ax2.legend(loc="upper right", frameon=False, fontsize=7.5, handlelength=2.2)

    fig.suptitle("Field-value activation swaps transfer decision margins in both models", x=.09, y=.965,
                 ha="left", fontsize=13, fontweight="bold", color=INK)
    fig.text(.09, .895,
             "Kev 0.8B · matched task-only vs PoL2-contract SFT · exact one-field pairs · three trained seeds per arm",
             ha="left", fontsize=8, color=MUTED)
    fig.text(.09, .035,
             "Each panel normalizes by its model's own clean margin gap. Same-value placebo effects = 0. Exploratory synthetic contract v0.2; points are seeds, not independent test cases. "
             "Causal dependence on these field representations does not establish complete PoL2 understanding.",
             ha="left", fontsize=7.2, color=MUTED)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out.with_suffix(".png"), dpi=320, bbox_inches="tight")
    fig.savefig(args.out.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    print(args.out.with_suffix(".png"))
    print(args.out.with_suffix(".pdf"))


if __name__ == "__main__":
    main()
