"""Plot exploratory matched-seed training ablations for PoL2 contract SFT."""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RESULTS = HERE / "results"
OUT = ROOT / "Research" / "figures"
BASE = RESULTS / "kev-pol2-rule-composition-20261026" / "results.json"
ARMS = [
    ("2 ep · CE", "baseline", BASE, "pol2_sft"),
    ("2 ep · pairwise", "structured", RESULTS / "kev-pol2-structured-loss-20261026" / "results.json", "structured_pairwise"),
    ("2 ep · balanced val.", "balanced2", RESULTS / "kev-pol2-balanced-validation-20261026" / "results.json", "state_balanced_validation"),
    ("4 ep · balanced val.", "balanced4", RESULTS / "kev-pol2-4epoch-balanced-validation-20261026" / "results.json", "state_balanced_validation"),
    ("6 ep · balanced val.", "balanced6", RESULTS / "kev-pol2-6epoch-balanced-validation-20261026" / "results.json", "state_balanced_validation"),
]
COLORS = ["#64748B", "#BE6A42", "#4086A0", "#2A8A77", "#7555A5"]

def load_runs(path, summary_key):
    data = json.loads(path.read_text(encoding="utf-8"))
    if summary_key == "pol2_sft":
        return data["runs"]
    if summary_key == "baseline":
        return [r for r in data["runs"] if r["arm"] == "pol2_sft"]
    return data["runs"]

def main():
    loaded = []
    base_data = json.loads(BASE.read_text(encoding="utf-8"))
    for label, key, path, summary_key in ARMS:
        data = json.loads(path.read_text(encoding="utf-8"))
        if key == "baseline":
            runs = [r for r in data["runs"] if r["arm"] == "pol2_sft"]
        else:
            runs = data["runs"]
        loaded.append((label, key, runs))
    plt.rcParams.update({
        "font.family": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.spines.top": False, "axes.spines.right": False,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2), gridspec_kw={"width_ratios": [1.05, 1.4]})
    ax = axes[0]
    x = np.arange(len(loaded))
    for i, (label, key, runs) in enumerate(loaded):
        values = np.array([r["test"]["contract_exact"] for r in runs]) * 100
        ax.scatter(np.full(len(values), i), values, color=COLORS[i], s=34,
                   edgecolor="white", linewidth=0.7, zorder=3)
        mean = values.mean()
        ax.plot([i - .20, i + .20], [mean, mean], color=COLORS[i], lw=3, solid_capstyle="round")
        ax.text(i, mean + 1.8, f"{mean:.1f}%", ha="center", va="bottom", color=COLORS[i], fontweight="bold")
    ax.set_xticks(x, [a[0] for a in loaded], rotation=20, ha="right")
    ax.set_ylim(35, 67)
    ax.set_yticks([40, 45, 50, 55, 60, 65])
    ax.set_ylabel("Exact preferred-action match (%)")
    ax.set_title("(a) Held-out composition accuracy", loc="left", fontweight="bold")
    ax.grid(axis="y", color="#E2E8F0", linewidth=.8)
    ax.set_axisbelow(True)
    ax.axhline(50.124, color="#64748B", linewidth=1, linestyle=(0, (3, 3)), alpha=.6)

    ax = axes[1]
    actions = ("inspect", "wait", "done")
    barw = .14
    x = np.arange(len(actions))
    for i, (label, key, runs) in enumerate(loaded):
        vals = []
        seedvals = []
        for r in runs:
            pred = r["predictions"]
            by_action = [sum(p["policy_action"] == a and p["predicted_action"] == a for p in pred)
                         / max(1, sum(p["policy_action"] == a for p in pred)) for a in actions]
            seedvals.append(by_action)
        vals = np.mean(seedvals, axis=0) * 100
        offset = (i - (len(loaded)-1)/2) * barw
        ax.bar(x + offset, vals, width=barw, color=COLORS[i], label=label, zorder=3)
    ax.set_xticks(x, actions)
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("Exact action rate by required action (%)")
    ax.set_title("(b) Which decisions improve?", loc="left", fontweight="bold")
    ax.grid(axis="y", color="#E2E8F0", linewidth=.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=7.5, ncol=2, loc="upper center", bbox_to_anchor=(.5, -.19))
    fig.suptitle("Training changes for the PoL2 embodied-contract slice", fontsize=12, fontweight="bold", y=1.02)
    fig.text(.5, -.04, "Dots show three matched seeds; lines/bars show means. The public finite-state test is reused (exploratory).",
             ha="center", fontsize=8, color="#475569")
    fig.tight_layout(rect=(0, .04, 1, .96))
    OUT.mkdir(parents=True, exist_ok=True)
    stem = "pol2-training-improvement-ablation-20261026"
    fig.savefig(OUT / f"{stem}.png", dpi=320, bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(OUT / f"{stem}.png")

if __name__ == "__main__":
    main()
