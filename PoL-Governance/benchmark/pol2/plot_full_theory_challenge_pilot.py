"""Render the failed full-theory benchmark feasibility pilot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=ROOT / "Research/figures/pol2-full-theory-challenge-pilot-20261026.png")
    args = ap.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    plt.rcParams.update({"font.family": "Microsoft YaHei", "font.size": 11, "axes.unicode_minus": False})
    fig, ax = plt.subplots(figsize=(11.8, 4.3), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.3)
    ax.axis("off")

    def box(x, y, w, h, title, sub, color, edge):
        patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                               linewidth=1.5, edgecolor=edge, facecolor=color)
        ax.add_patch(patch)
        ax.text(x+w/2, y+h*0.66, title, ha="center", va="center", fontsize=14, weight="bold", color="#17212B")
        ax.text(x+w/2, y+h*0.31, sub, ha="center", va="center", fontsize=10.2, color="#334155", linespacing=1.35)

    ax.text(0.2, 4.05, "PoL2 完整理论挑战集：可行性门槛结果", fontsize=17, weight="bold", color="#102A43")
    ax.text(0.2, 3.72, "单条理论条目的 AI 生成先导；不是模型能力成绩", fontsize=10.5, color="#52606D")
    box(0.25, 1.55, 2.45, 1.55, "覆盖清单", "114 个来源条目\nPoL2 第 0–8 章", "#EEF4F8", "#486581")
    box(3.35, 1.55, 2.45, 1.55, "生成与标签裁定", "love2 单条概念\n6 个候选；裁定同意 6/6", "#F0F5F1", "#4C956C")
    box(6.45, 1.55, 2.45, 1.55, "盲化质量门", f"来源扎根 {audit['grounded_n']}/6\n表面线索 {audit['leakage_n']}/6", "#FFF7E6", "#D99A2B")
    box(9.55, 1.55, 2.2, 1.55, "停止训练", "有效类别仅 consistent\n不满足训练/测试覆盖", "#FDECEC", "#C44536")
    for x1, x2 in ((2.7, 3.35), (5.8, 6.45), (8.9, 9.55)):
        ax.annotate("", xy=(x2-0.08, 2.33), xytext=(x1+0.08, 2.33),
                    arrowprops={"arrowstyle": "-|>", "lw": 1.6, "color": "#627D98"})
    ax.text(0.25, 0.8, "放行标准：来源支持 ∧ 事实可判定 ∧ 无表面标签线索。", fontsize=11, weight="bold", color="#334E68")
    ax.text(0.25, 0.42, "结果：2/6 通过全部条件，且只覆盖 consistent；本轮未训练、未计算模型分数。", fontsize=10.5, color="#52606D")
    fig.tight_layout(pad=0.8)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(args.output)


if __name__ == "__main__":
    main()
