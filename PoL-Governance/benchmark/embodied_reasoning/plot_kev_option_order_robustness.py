"""Render the paired Kev option-order experiment using the repository style."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULT = HERE / "results" / "kev-option-order-robustness-20261025.json"
FIGURE = ROOT / "Research" / "figures" / "pol2-kev-option-order-robustness-20261025"
STYLE_ROOT = ROOT / "PoL-Governance" / "Research" / "PoL2-DAO-Governance-Lab" / "src"
sys.path.insert(0, str(STYLE_ROOT))

from pol2dao.plotstyle import PALETTE, REF_LINE, finalize_figure, new_figure  # noqa: E402


FAMILY_LABELS = {
    "embodied.authority.task_instruction_conflict": "Authority conflict",
    "embodied.counting_and_task_progress": "Counting / progress",
    "embodied.harm_prevention.corridor_cleaning": "Corridor cleaning",
    "embodied.harm_prevention.moving_obstacle": "Moving obstacle",
    "embodied.personal_boundary.object_move": "Personal boundary",
    "embodied.shared_resource.allocation": "Resource allocation",
    "embodied.shared_resource.queue_priority": "Queue priority",
    "embodied.state_uncertainty.object_identification": "Object uncertainty",
}


def main() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    family_differences = result["primary_comparison_pol2_minus_neutral"]["family_differences"]
    primary = result["primary_comparison_pol2_minus_neutral"]
    accuracy = result["secondary_comparisons_pol2_minus_neutral"]["argmax_accuracy_over_orders"]
    fig, axes = new_figure(1, 2, panel=(6.0, 5.0))

    panels = (
        (axes[0][0],
         "pol2_minus_neutral_mean_probability_expected_action",
         primary,
         "A  Model score on the prespecified action"),
        (axes[0][1],
         "pol2_minus_neutral_accuracy_over_orders",
         accuracy,
         "B  Top-choice accuracy"),
    )
    for ax, field, summary, title in panels:
        n = len(family_differences)
        for index, row in enumerate(reversed(family_differences), start=1):
            delta = row[field] * 100
            ax.scatter(delta, index, s=56, color=PALETTE["neutral_dark"], zorder=3)
        mean = summary["mean_family_difference"] * 100
        lo, hi = [value * 100 for value in summary["95_percent_t_interval_df7"]]
        ax.errorbar(mean, 0, xerr=[[mean - lo], [hi - mean]], fmt="D",
                    color=PALETTE["blue_main"], ecolor=PALETTE["blue_main"],
                    markersize=8, capsize=5, elinewidth=2.2, zorder=4)
        ax.axvline(0, **REF_LINE)
        ax.set_yticks([0, *range(1, n + 1)],
                      ["Mean (95% CI)", *[FAMILY_LABELS[item["family_id"]]
                                           for item in reversed(family_differences)]])
        ax.set_ylim(-0.8, n + 0.8)
        ax.set_title(f"{title}\nMean {mean:+.1f} pp; 95% CI [{lo:+.1f}, {hi:+.1f}], p={summary['exact_two_sided_sign_flip_p']:.4f}",
                     loc="left", color=PALETTE["ink"], fontsize=13)
        ax.set_xlabel("PoL2 − neutral (percentage points)")
        ax.tick_params(axis="y", length=0, labelsize=11)
        ax.tick_params(axis="x", labelsize=11)
    axes[0][0].set_ylabel("Prespecified task family")
    axes[0][1].set_ylabel("")
    fig.suptitle("Typed-choice behavior under all candidate orders", x=0.5, y=0.99,
                 fontsize=17, color=PALETTE["ink"])
    paths = finalize_figure(fig, FIGURE, formats=("png", "pdf"), dpi=300, pad=1.4)
    print("\n".join(str(path) for path in paths))


if __name__ == "__main__":
    main()
