"""Plot the prompt-free PoL2 typed-action internalization pilot."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager


METRICS = {
    "match": ("exact_match_to_pol2_preferred_action", "Policy-action match"),
    "admissible": ("raw_action_admissibility_rate", "Admissible action"),
    "unauthorized": ("unauthorized_transfer_rate_when_ineligible", "Unauthorized transfer"),
    "false_done": ("false_done_rate_when_terminal_false", "False completion claim"),
    "transfer_recall": ("authorized_transfer_recall", "Authorized transfer recall"),
}
COLORS = {"Pretrained": "#768395", "Task-only SFT": "#D18B45", "PoL2 SFT": "#177E89"}


def mean_sd(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Output base path, without extension")
    args = parser.parse_args()
    data = json.loads(args.result.read_text(encoding="utf-8"))
    baseline = data["pretrained_kev_test"]

    def values(metric: str) -> dict[str, list[float]]:
        key = METRICS[metric][0]
        return {
            "Pretrained": [baseline[key]],
            "Task-only SFT": [r["test"][key] for r in data["runs"] if r["arm"] == "task_only"],
            "PoL2 SFT": [r["test"][key] for r in data["runs"] if r["arm"] == "pol2_sft"],
        }

    for font in ("Microsoft YaHei", "Arial"):
        try:
            font_manager.findfont(font, fallback_to_default=False)
            plt.rcParams["font.family"] = font
            break
        except Exception:
            pass
    plt.rcParams.update({
        "font.size": 9, "axes.titlesize": 11, "axes.labelsize": 9,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "axes.facecolor": "white", "svg.fonttype": "none",
    })
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.55), gridspec_kw={"width_ratios": [1.06, 1, 1.06]})
    panels = [
        (axes[0], ["match", "admissible"], "A  Rule following", "higher is better"),
        (axes[1], ["unauthorized", "false_done"], "B  Unsafe outputs", "lower is better"),
        (axes[2], ["transfer_recall"], "C  Task utility", "higher is better"),
    ]
    for ax, metrics, title, direction in panels:
        ax.set_title(title, loc="left", fontweight="bold", pad=10)
        ax.text(.02, 1.015, direction, transform=ax.transAxes, fontsize=7, color="#56616D")
        for y, metric in enumerate(metrics[::-1]):
            ax.axhline(y + .31, color="#E8EBEF", linewidth=.8, zorder=0)
            for offset, label in zip((-.20, 0, .20), COLORS):
                raw = values(metric)[label]
                mean, sd = mean_sd(raw)
                ax.errorbar(mean * 100, y + offset, xerr=sd * 100, fmt="o", markersize=5,
                            color=COLORS[label], ecolor=COLORS[label], elinewidth=1.6,
                            capsize=2, zorder=3)
                if len(raw) > 1:
                    ax.scatter([v * 100 for v in raw], [y + offset + j for j in (-.035, 0, .035)],
                               s=11, color=COLORS[label], alpha=.6, zorder=4, linewidths=0)
        ax.set_yticks(range(len(metrics)), [METRICS[m][1] for m in metrics[::-1]])
        ax.set_xlim(-2, 105)
        ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100"])
        ax.set_xlabel("Rate (%)")
        ax.grid(axis="x", color="#E8EBEF", linewidth=.8)
        ax.set_axisbelow(True)
        ax.invert_yaxis()

    # Ordering stability is available only for the PoL2 arm; keep it visually separate.
    ax = axes[2]
    order = [r["candidate_order_stability"]["order_stable_case_rate"]
             for r in data["runs"] if r["arm"] == "pol2_sft"]
    mean, sd = mean_sd(order)
    y = 1
    ax.axhline(y + .31, color="#E8EBEF", linewidth=.8, zorder=0)
    ax.errorbar(mean * 100, y, xerr=sd * 100, fmt="o", markersize=5,
                color=COLORS["PoL2 SFT"], ecolor=COLORS["PoL2 SFT"], elinewidth=1.6,
                capsize=2, zorder=3)
    ax.scatter([v * 100 for v in order], [y + j for j in (-.035, 0, .035)],
               s=11, color=COLORS["PoL2 SFT"], alpha=.6, zorder=4, linewidths=0)
    ax.set_ylim(1.42, -.42)
    ax.set_yticks([0, 1], ["Authorized transfer recall", "Order-stable cases¹"])

    handles = [plt.Line2D([0], [0], marker="o", linestyle="", color=c, label=k, markersize=5)
               for k, c in COLORS.items()]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(.5, -.01), columnspacing=2.2)
    fig.text(.01, -.04, "Dots show individual seeds; larger points and bars show mean ± SD across 3 seeds. "
             "Pretrained is a single fixed checkpoint.", fontsize=7.5, color="#56616D")
    fig.text(.01, -.075, "¹ Candidate-order stability was measured only for PoL2 SFT across 12 cases × "
             "24 option orders per seed.", fontsize=7.5, color="#56616D")
    fig.tight_layout(rect=[0, .10, 1, 1], w_pad=2.1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(args.output.with_suffix(f".{ext}"), dpi=320, bbox_inches="tight")


if __name__ == "__main__":
    main()
