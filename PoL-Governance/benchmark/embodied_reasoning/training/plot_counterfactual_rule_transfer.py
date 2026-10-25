"""Render the held-out counterfactual transfer results as an academic figure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_RESULT = HERE / "results" / "kev-pol2-counterfactual-causal-20261026" / "counterfactual_results.json"
DEFAULT_OUT = HERE.parents[3] / "Research" / "figures" / "pol2-counterfactual-rule-transfer-20261026"
COLORS = {"pretrained_kev": "#87909A", "task_only": "#356A8A", "pol2_sft": "#D27A35"}
FACTORS = ("permission", "scope", "freshness", "location", "terminal")
FACTOR_LABELS = {"permission": "Authorization", "scope": "Scope", "freshness": "Observation freshness",
                 "location": "Object location", "terminal": "Completion state"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    data = json.loads(args.result.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.titlesize": 11,
                         "axes.labelsize": 9, "pdf.fonttype": 42, "ps.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 4.0), constrained_layout=True)

    # A. Full 864-case grid, seed-level dots and mean; pretrained baseline once.
    ax = axes[0]
    names = ("pretrained_kev", "task_only", "pol2_sft")
    labels = ("Kev base", "Task-only", "PoL2 SFT")
    for i, (name, label) in enumerate(zip(names, labels)):
        vals = ([data["metrics_by_model_seed"][name]["case_metrics"]["exact_policy_action_accuracy"]]
                if name == "pretrained_kev" else
                [data["metrics_by_model_seed"][f"{name}_seed_{s}"]["case_metrics"]["exact_policy_action_accuracy"]
                 for s in data["design"]["seeds"]])
        ax.scatter(np.linspace(i - 0.08, i + 0.08, len(vals)), vals, s=26, color=COLORS[name], zorder=3)
        ax.hlines(np.mean(vals), i - 0.22, i + 0.22, color=COLORS[name], lw=2.6)
    ax.set_xticks(range(3), labels, rotation=20, ha="right")
    ax.set_ylim(0, 1.03)
    ax.set_ylabel("Exact match to contract action")
    ax.set_title("A  Held-out language grid", loc="left", fontweight="bold")
    ax.text(0.02, 0.98, "864 cases · 6 unseen instruction families", transform=ax.transAxes,
            va="top", fontsize=8, color="#52606D")
    ax.grid(axis="y", color="#E8EBEE", lw=0.8)

    # B/C. Cluster-bootstrap intervals over shared state-context groups.
    factor_y = np.arange(len(FACTORS))[::-1]
    for ax, metric, title, xlabel in (
        (axes[1], "directional_rule_response", "B  Decisive-fact response", "Correct paired response"),
        (axes[2], "irrelevant_to_target_invariance", "C  Same-target invariance", "Prediction unchanged"),
    ):
        for offset, arm in ((-0.10, "task_only"), (0.10, "pol2_sft")):
            xs, xerr_lo, xerr_hi = [], [], []
            for factor in FACTORS:
                cell = data["pooled_across_seed_cluster_bootstrap"][arm][factor][metric]
                mean = cell["mean_cluster_score"]
                if mean is None:
                    ax.text(0.52, factor_y[FACTORS.index(factor)], "All pairs change target",
                            ha="center", va="center", fontsize=7.5, color="#68737D")
                    xs.append(np.nan); xerr_lo.append(0); xerr_hi.append(0)
                    continue
                lo, hi = cell["cluster_bootstrap_95_ci"]
                xs.append(mean); xerr_lo.append(mean - lo); xerr_hi.append(hi - mean)
            ax.errorbar(xs, factor_y + offset, xerr=[xerr_lo, xerr_hi], fmt="o", ms=5,
                        capsize=2.5, lw=1.3, color=COLORS[arm], label="Task-only" if arm == "task_only" else "PoL2 SFT")
        ax.set_yticks(factor_y, [FACTOR_LABELS[x] for x in FACTORS])
        ax.set_xlim(0, 1.03); ax.set_ylim(-0.55, len(FACTORS) - 0.45)
        ax.set_xlabel(xlabel); ax.set_title(title, loc="left", fontweight="bold")
        ax.grid(axis="x", color="#E8EBEE", lw=0.8)
    axes[2].legend(frameon=False, loc="lower right", fontsize=8)
    fig.suptitle("Counterfactual transfer under a frozen embodied-action contract", x=0.01,
                 ha="left", fontsize=12, fontweight="bold")
    fig.savefig(args.output.with_suffix(".png"), dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(args.output.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    print(json.dumps({"png": str(args.output.with_suffix('.png')), "pdf": str(args.output.with_suffix('.pdf'))}))


if __name__ == "__main__":
    main()
