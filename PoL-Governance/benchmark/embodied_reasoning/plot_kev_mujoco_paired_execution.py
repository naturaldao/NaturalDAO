"""Publication-style figure for the Kev-to-MuJoCo paired execution pilot."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLOTSTYLE = ROOT / "PoL-Governance" / "research" / "PoL2-DAO-Governance-Lab" / "src"
sys.path.insert(0, str(PLOTSTYLE))
from pol2dao.plotstyle import PALETTE, FigureStyle, finalize_figure, new_figure  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=HERE / "results" / "kev-mujoco-paired-execution-20261025b.json")
    parser.add_argument("--output", type=Path, default=ROOT / "Research" / "figures" / "pol2-kev-mujoco-paired-execution-20261025.png")
    args = parser.parse_args()
    data = json.loads(args.result.read_text(encoding="utf-8"))
    style = FigureStyle(font_size=12, axes_linewidth=1.5)
    fig, axes = new_figure(1, 2, panel=(5.4, 3.7), style=style, squeeze=False,
                           gridspec_kw={"width_ratios": [1.05, 1]})
    ax = axes[0, 0]
    arms = [
        ("generic", "Generic", PALETTE["red_strong"], "o"),
        ("neutral_matched", "Length-matched neutral", PALETTE["neutral_dark"], "s"),
        ("pol2", "PoL2", PALETTE["blue_main"], "D"),
    ]
    permission_order = ["GRANTED", "DENIED", "UNKNOWN"]
    positions = {p: i for i, p in enumerate(permission_order)}
    rows = data["rows"]
    for arm, label, color, marker in arms:
        xs, means = [], []
        for permission in permission_order:
            by_layout = []
            for layout in data["design"]["layouts"]:
                values = [r["probabilities"]["transfer"] for r in rows
                          if r["arm"] == arm and r["permission"] == permission and r["layout_id"] == layout]
                by_layout.append(statistics.mean(values))
            x = positions[permission]
            xs.append(x)
            means.append(statistics.mean(by_layout))
            jitter = [-0.055, 0.0, 0.055]
            ax.scatter([x + j for j in jitter], by_layout, color=color, marker=marker,
                       s=22, alpha=0.45, zorder=3)
        ax.plot(xs, means, color=color, marker=marker, markersize=6, label=label, zorder=4)
    ax.set_xticks(range(3), ["Granted", "Denied", "Unknown"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Mean transfer score")
    ax.set_title("A  Model score by permission", loc="left", fontweight="bold")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.grid(axis="y", color=PALETTE["neutral"], alpha=0.35, linewidth=0.8)

    ax = axes[0, 1]
    challenge = data["adversarial_gate_challenge"]
    vals = [
        ("Unauthorized\nmovement", challenge["unauthorized_movements_gate_off"],
         challenge["unauthorized_movements_gate_on"], challenge["unauthorized_states"]),
        ("Authorized task\ncompleted", challenge["authorized_task_completions_gate_off"],
         challenge["authorized_task_completions_gate_on"], 3),
    ]
    xs = [0, 1]
    width = 0.32
    off = [v[1] / v[3] for v in vals]
    on = [v[2] / v[3] for v in vals]
    bars_off = ax.bar([x - width / 2 for x in xs], off, width, color=PALETTE["neutral_dark"],
                      label="Gate bypassed", edgecolor=PALETTE["white"], linewidth=0.8)
    bars_on = ax.bar([x + width / 2 for x in xs], on, width, color=PALETTE["blue_main"],
                     label="PoL2 gate on", edgecolor=PALETTE["white"], linewidth=0.8)
    for bars, counts, denominators, condition in (
        (bars_off, [v[1] for v in vals], [v[3] for v in vals], "Bypassed"),
        (bars_on, [v[2] for v in vals], [v[3] for v in vals], "Gate on"),
    ):
        for bar, count, denom in zip(bars, counts, denominators):
            x = bar.get_x() + bar.get_width() / 2
            if bar.get_height() > 0.2:
                ax.text(x, bar.get_height() - 0.16, f"{condition}\n{count}/{denom}",
                        ha="center", va="top", fontsize=8, color=PALETTE["white"], fontweight="bold")
            else:
                ax.text(x, 0.045, f"{condition}\n{count}/{denom}",
                        ha="center", va="bottom", fontsize=8, color=PALETTE["blue_main"], fontweight="bold")
    ax.set_xticks(xs, [v[0] for v in vals])
    ax.set_ylim(0, 1.55)
    ax.set_ylabel("Rate")
    ax.set_title("B  Forced-transfer gate challenge", loc="left", fontweight="bold")
    ax.grid(axis="y", color=PALETTE["neutral"], alpha=0.35, linewidth=0.8)
    fig.subplots_adjust(left=0.13, right=0.985, bottom=0.22, top=0.82, wspace=0.30)
    out = args.output if args.output.is_absolute() else ROOT / args.output
    finalize_figure(fig, out, tight=False)
    print(json.dumps({"figure": str(out), "formats": ["png", "pdf"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
