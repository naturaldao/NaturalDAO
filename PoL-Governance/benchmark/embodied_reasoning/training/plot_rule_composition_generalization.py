"""Render figure for the held-out PoL2 contract composition diagnostic."""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
RESULT = Path(__file__).resolve().parent / "results" / "kev-pol2-rule-composition-20261026" / "results.json"
OUT = ROOT / "Research" / "figures"
ARMS = ("pol2_sft", "task_only")
ARM_LABELS = {"pol2_sft": "PoL2-contract SFT", "task_only": "Task-only SFT"}
COLORS = {"pol2_sft": "#167C80", "task_only": "#D07A39"}
TARGETS = ("inspect", "wait", "done")
PREDICTIONS = ("transfer", "inspect", "wait", "done")
METRICS = (
    ("contract_exact", "Exact contract action"),
    ("admissible", "Admissible action"),
    ("unauthorized_transfer", "Forbidden transfer"),
    ("false_done", "False done report"),
)

def main():
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    plt.rcParams.update({
        "font.family": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.spines.top": False, "axes.spines.right": False,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })
    fig = plt.figure(figsize=(10.2, 5.2))
    gs = fig.add_gridspec(1, 2, width_ratios=(1.12, 1.38),
                          left=0.07, right=0.985, top=0.86, bottom=0.20, wspace=0.40)
    sub = gs[0, 0].subgridspec(2, 1, hspace=0.52)
    for i, arm in enumerate(ARMS):
        ax = fig.add_subplot(sub[i, 0])
        counts = np.zeros((len(TARGETS), len(PREDICTIONS)), dtype=float)
        for run in data["runs"]:
            if run["arm"] != arm:
                continue
            for row in run["predictions"]:
                if row["policy_action"] in TARGETS:
                    counts[TARGETS.index(row["policy_action"]),
                           PREDICTIONS.index(row["predicted_action"])] += 1
        row_sums = counts.sum(axis=1, keepdims=True)
        pct = np.divide(counts, row_sums, out=np.zeros_like(counts), where=row_sums != 0) * 100
        im = ax.imshow(pct, cmap="Blues", vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(PREDICTIONS)), PREDICTIONS)
        ax.set_yticks(range(len(TARGETS)), TARGETS)
        ax.set_title(f"({chr(97+i)}) {ARM_LABELS[arm]}", loc="left", fontweight="bold", pad=6)
        if i == 1:
            ax.set_xlabel("Predicted action")
        if i == 0:
            ax.set_ylabel("Required action")
        for r in range(len(TARGETS)):
            for c in range(len(PREDICTIONS)):
                value = pct[r, c]
                ax.text(c, r, f"{value:.0f}%", ha="center", va="center",
                        color="white" if value >= 57 else "#15202B", fontsize=8)
        ax.set_xticks(np.arange(-.5, len(PREDICTIONS), 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(TARGETS), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.5)
        ax.tick_params(which="minor", bottom=False, left=False)
    ax = fig.add_subplot(gs[0, 1])
    ybase = np.arange(len(METRICS))[::-1]
    offsets = {"pol2_sft": 0.13, "task_only": -0.13}
    for j, (key, label) in enumerate(METRICS):
        y = ybase[j]
        for arm in ARMS:
            values = [r["test"][key] for r in data["runs"] if r["arm"] == arm]
            mean = float(np.mean(values))
            ax.plot([0, mean], [y + offsets[arm]]*2, color=COLORS[arm], lw=5,
                    alpha=0.30, solid_capstyle="round")
            for k, value in enumerate(values):
                jitter = (k - 1) * 0.12
                ax.scatter(value*100, y + offsets[arm] + jitter, s=28,
                           color=COLORS[arm], edgecolor="white", linewidth=0.6,
                           zorder=3, marker=("o" if arm == "pol2_sft" else "s"))
            ax.scatter(mean*100, y + offsets[arm], s=56, marker="D",
                       color=COLORS[arm], edgecolor="white", linewidth=0.8, zorder=4)
            label_x = 104 if arm == "pol2_sft" else 117
            ax.text(label_x, y + offsets[arm], f"{mean*100:.1f}%",
                    va="center", ha="left", fontsize=8, color=COLORS[arm], fontweight="bold")
    ax.set_yticks(ybase, [m[1] for m in METRICS])
    ax.set_xlim(0, 132)
    ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100"])
    ax.set_xlabel("Cases (%)")
    ax.set_title("(c) Rule fidelity and safety outcomes", loc="left", fontweight="bold", pad=6)
    ax.grid(axis="x", color="#DDE3E8", linewidth=0.8)
    ax.set_axisbelow(True)
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=COLORS["pol2_sft"],
               markeredgecolor="white", label=ARM_LABELS["pol2_sft"], markersize=7),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=COLORS["task_only"],
               markeredgecolor="white", label=ARM_LABELS["task_only"], markersize=7),
        Line2D([0], [0], marker="D", color="#66717B", label="Mean", markersize=6, linewidth=0),
    ]
    fig.legend(handles=handles, frameon=False, loc="lower center",
               bbox_to_anchor=(0.74, 0.025), ncol=3, fontsize=8,
               columnspacing=1.4, handletextpad=0.5)
    fig.suptitle("Held-out combinations of PoL2 embodied-contract rules",
                 fontsize=12, fontweight="bold", y=0.97)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "pol2-rule-composition-generalization-20261026.png", dpi=320, bbox_inches="tight")
    fig.savefig(OUT / "pol2-rule-composition-generalization-20261026.pdf", bbox_inches="tight")
    plt.close(fig)
    print(OUT / "pol2-rule-composition-generalization-20261026.png")

if __name__ == "__main__":
    main()
