"""Render the PoL2 revocation-recovery result in the repository figure style."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STYLE_ROOT = ROOT / "PoL-Governance" / "Research" / "PoL2-DAO-Governance-Lab" / "src"
sys.path.insert(0, str(STYLE_ROOT))

from pol2dao.plotstyle import (  # noqa: E402
    PALETTE, FigureStyle, finalize_figure, new_figure,
)


CONDITION_ORDER = [
    "revoked_before_grasp",
    "revoked_before_place_recovery_denied",
    "revoked_before_place_recovery_unknown",
    "revoked_before_place_recovery_only",
    "continuous_task_grant_control",
]
CONDITION_LABELS = ["抓取前\n撤回", "晚撤回\n无权限", "晚撤回\n未知权限",
                    "晚撤回\n恢复许可", "持续\n授权"]
OUTCOME_ROWS = [
    ("任务目标完成", "task_complete", False),
    ("物体返回源位", "object_on_source", False),
    ("物体仍被夹持", "bilateral_gripper_contact", True),
    ("物体有支撑接触", "any_verified_support_contact", False),
]


def draw_flow(ax) -> None:
    from matplotlib.patches import FancyBboxPatch

    ink = PALETTE["ink"]
    soft = PALETTE["ink_soft"]
    boxes = [
        (0.025, 0.66, 0.19, 0.19, "任务执行中\n授权 GRANTED", PALETTE["blue_main"], PALETTE["white"]),
        (0.275, 0.66, 0.19, 0.19, "执行中撤回\n授权 DENIED", PALETTE["red_strong"], PALETTE["red_1"]),
        (0.525, 0.66, 0.19, 0.19, "阻断目标放置\n物体仍被夹持", PALETTE["neutral_dark"], PALETTE["white"]),
        (0.775, 0.66, 0.20, 0.19, "检查独立的\n恢复权限", PALETTE["blue_secondary"], PALETTE["white"]),
    ]
    for x, y, w, h, label, edge, face in boxes:
        patch = FancyBboxPatch((x, y), w, h,
                               boxstyle="round,pad=0.012,rounding_size=0.02",
                               linewidth=1.5, edgecolor=edge, facecolor=face)
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=10.5, color=ink, linespacing=1.2)
    for left, right in ((0.215, 0.275), (0.465, 0.525), (0.715, 0.775)):
        ax.annotate("", xy=(right - 0.006, 0.755), xytext=(left + 0.006, 0.755),
                    arrowprops={"arrowstyle": "-|>", "lw": 1.6, "color": soft})

    # Explicit two-way branch: restoring the scene is distinct from completing
    # the revoked task. The unauthorized/unknown branch is shown as unresolved.
    # Connect the branch to the actual permission-check node. The previous
    # version left a visible gap between the vertical stem and split line.
    ax.plot([0.875, 0.875], [0.66, 0.52], color=soft, lw=1.2)
    ax.plot([0.255, 0.875], [0.52, 0.52], color=soft, lw=1.2)
    ax.annotate("", xy=(0.255, 0.41), xytext=(0.255, 0.52),
                arrowprops={"arrowstyle": "-|>", "lw": 1.5, "color": PALETTE["green_3"]})
    ax.annotate("", xy=(0.755, 0.41), xytext=(0.755, 0.52),
                arrowprops={"arrowstyle": "-|>", "lw": 1.5, "color": PALETTE["red_strong"]})

    outcomes = [
        (0.035, 0.11, 0.44, 0.30, "RECOVERY_ONLY", "沿受限路径返回源位 → 松爪 → 复核",
         "本次：源位支撑成立；任务目标未完成", PALETTE["green_3"], PALETTE["green_1"]),
        (0.525, 0.11, 0.44, 0.30, "DENIED / UNKNOWN", "不发出恢复动作；物体保持悬持",
         "本次：无支撑接触；物理中间态未解决", PALETTE["red_strong"], PALETTE["red_1"]),
    ]
    for x, y, w, h, title, line1, line2, edge, face in outcomes:
        patch = FancyBboxPatch((x, y), w, h,
                               boxstyle="round,pad=0.014,rounding_size=0.02",
                               linewidth=1.5, edgecolor=edge, facecolor=face)
        ax.add_patch(patch)
        ax.text(x + 0.025, y + h - 0.065, title, ha="left", va="center",
                fontsize=10.5, fontweight="bold", color=ink)
        ax.text(x + 0.025, y + 0.145, line1, ha="left", va="center",
                fontsize=9.3, color=ink)
        ax.text(x + 0.025, y + 0.055, line2, ha="left", va="center",
                fontsize=8.8, color=soft)


def draw_matrix(ax, cases: list[dict]) -> None:
    from matplotlib.patches import FancyBboxPatch

    ink = PALETTE["ink"]
    soft = PALETTE["ink_soft"]
    by_id = {case["case_id"]: case for case in cases}
    ordered = [by_id[name] for name in CONDITION_ORDER]
    matrix = np.asarray([[bool(case[key]) for case in ordered]
                         for _, key, _ in OUTCOME_ROWS], dtype=bool)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    left = 0.335
    right = 0.99
    centers = np.linspace(left + 0.065, right - 0.065, len(CONDITION_LABELS))
    header_y = 0.85
    row_ys = [0.66, 0.47, 0.28, 0.09]
    for x, label in zip(centers, CONDITION_LABELS):
        ax.text(x, header_y, label, ha="center", va="center", fontsize=8.8,
                color=ink, linespacing=1.15)
        ax.text(x, header_y - 0.085, "n=1", ha="center", va="center",
                fontsize=7.5, color=soft)

    for i, ((label, _, adverse_if_true), y) in enumerate(zip(OUTCOME_ROWS, row_ys)):
        ax.text(0.015, y, label, ha="left", va="center", fontsize=9.4, color=ink)
        ax.plot([0.015, 0.985], [y - 0.095, y - 0.095], color=PALETTE["neutral"],
                lw=0.65, zorder=0)
        for j, x in enumerate(centers):
            value = bool(matrix[i, j])
            if value and adverse_if_true:
                face = PALETTE["red_1"]
                edge = PALETTE["red_strong"]
                label_color = PALETTE["red_strong"]
            elif value:
                face = PALETTE["green_1"]
                edge = PALETTE["green_3"]
                label_color = PALETTE["ink"]
            else:
                face = PALETTE["white"]
                edge = PALETTE["neutral"]
                label_color = soft
            tile = FancyBboxPatch((x - 0.043, y - 0.050), 0.086, 0.100,
                                  boxstyle="round,pad=0.004,rounding_size=0.012",
                                  linewidth=0.9, edgecolor=edge, facecolor=face)
            ax.add_patch(tile)
            ax.text(x, y, "是" if value else "否", ha="center", va="center",
                    fontsize=9.1, color=label_color)


def render(result_path: Path, output_stem: Path) -> list[Path]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    # Compact article figure: reduce the default 16 pt house typography for
    # this dense, two-panel state diagram while retaining legibility in print.
    compact = FigureStyle(font_size=11, axes_linewidth=1.0)
    fig, axes = new_figure(2, 1, panel=(8.4, 2.8), style=compact,
                           gridspec_kw={"height_ratios": [1.0, 0.92]})
    axes = axes[:, 0]
    axes[0].set_title("A  撤回后的机器恢复分支", loc="left", color=PALETTE["ink"], pad=7)
    axes[0].set_xlim(0, 1)
    axes[0].set_ylim(0, 1)
    axes[0].axis("off")
    draw_flow(axes[0])

    axes[1].set_title("B  五个条件的仿真物理终态", loc="left", color=PALETTE["ink"], pad=7)
    draw_matrix(axes[1], result["cases"])

    fig.tight_layout(pad=0.75, h_pad=0.55)
    return finalize_figure(fig, output_stem, formats=("png", "pdf"), dpi=300, tight=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=Path,
                        help="path to the experiment JSON")
    parser.add_argument("--output-stem", required=True, type=Path,
                        help="output path without .png/.pdf")
    args = parser.parse_args()
    outputs = render(args.result, args.output_stem)
    print("\n".join(str(path) for path in outputs))


if __name__ == "__main__":
    main()
