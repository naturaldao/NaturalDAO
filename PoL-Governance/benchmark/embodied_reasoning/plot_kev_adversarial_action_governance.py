"""Draw the adversarial instruction/candidate-set governance results."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "PoL-Governance" / "research" / "PoL2-DAO-Governance-Lab" / "src"))
from pol2dao.plotstyle import PALETTE, FigureStyle, finalize_figure, new_figure  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=HERE / "results" / "kev-adversarial-action-governance-20261026.json")
    parser.add_argument("--output", type=Path, default=ROOT / "Research" / "figures" / "pol2-kev-adversarial-action-governance-20261026.png")
    args = parser.parse_args()
    data = json.loads(args.result.read_text(encoding="utf-8"))
    fig, axes = new_figure(1, 3, panel=(4.2, 4.0), style=FigureStyle(font_size=11, axes_linewidth=1.4),
                           squeeze=False, gridspec_kw={"width_ratios": [1.05, 0.9, 1.05]})
    heat, candidate, physical = axes[0]

    cases = [
        ("denied_override_instruction", "DENIED override"),
        ("unknown_fabricated_consent", "UNKNOWN consent claim"),
        ("false_completion_claim", "Premature done"),
        ("pickup_precondition_override", "Pickup precondition"),
        ("unapproved_target_scope", "Target outside scope"),
    ]
    arms = [("generic", "Generic"), ("neutral_matched", "Matched neutral"), ("pol2", "PoL2")]
    matrix, labels = [], []
    for case_id, label in cases:
        row = []
        for arm, _ in arms:
            s = next(x for x in data["model_action_summaries"] if x["case_id"] == case_id
                     and x["candidate_set"] == "full_adversarial"
                     and x["candidate_mode"] == "raw_candidates" and x["arm"] == arm)
            row.append(s["unsafe_argmax_outputs"] / s["orders"])
        matrix.append(row)
        labels.append(label)
    im = heat.imshow(matrix, cmap="Reds", vmin=0, vmax=1, aspect="auto")
    heat.set_xticks(range(len(arms)), [a[1] for a in arms], rotation=24, ha="right")
    heat.set_yticks(range(len(cases)), labels)
    heat.set_title("A  Raw full candidate set", loc="left", fontweight="bold")
    heat.set_xlabel("Prompt")
    heat.set_ylabel("Adversarial case")
    heat.tick_params(axis="y", labelsize=9)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            color = PALETTE["white"] if value > 0.58 else PALETTE["ink"]
            heat.text(j, i, f"{value:.0%}", ha="center", va="center", color=color, fontweight="bold")

    labels_b = ["Unsafe-only\nraw", "Unsafe-only\nfiltered", "Valid move\nretained"]
    unsafe_raw = [s for s in data["model_action_summaries"] if s["candidate_set"] == "unsafe_only"
                  and s["candidate_mode"] == "raw_candidates"]
    unsafe_filtered = [s for s in data["model_action_summaries"] if s["candidate_set"] == "unsafe_only"
                       and s["candidate_mode"] == "pol2_prefiltered"]
    valid_move = [s for s in unsafe_filtered if s["case_id"] == "false_completion_claim"
                  and s["aggregated_action"] == "transfer" and not s["aggregated_choice_unsafe"]]
    raw_violations = sum(s["aggregated_choice_unsafe"] for s in unsafe_raw)
    filtered_violations = sum(s["aggregated_choice_unsafe"] for s in unsafe_filtered)
    values_b = [raw_violations / len(unsafe_raw), filtered_violations / len(unsafe_filtered),
                len(valid_move) / 3]
    counts_b = [f"{raw_violations}/{len(unsafe_raw)}", f"{filtered_violations}/{len(unsafe_filtered)}",
                f"{len(valid_move)}/3"]
    colors_b = [PALETTE["red_strong"], PALETTE["blue_main"], PALETTE["green_3"]]
    bars = candidate.bar(range(3), values_b, color=colors_b, width=0.66)
    for bar, count, value in zip(bars, counts_b, values_b):
        y = value - 0.12 if value > 0.5 else 0.04
        candidate.text(bar.get_x() + bar.get_width()/2, y, count, ha="center", va="center",
                       color=PALETTE["white"] if value > 0.5 else PALETTE["blue_main"], fontweight="bold")
    candidate.set_xticks(range(3), labels_b)
    candidate.set_ylim(0, 1.12)
    candidate.set_ylabel("")
    candidate.set_title("B  Candidate-set filtering", loc="left", fontweight="bold")
    candidate.grid(axis="y", color=PALETTE["neutral"], alpha=0.35, linewidth=0.8)
    candidate.text(0.5, -0.34, "A granted transfer survives filtering\nwhen the terminal claim is false.",
                   transform=candidate.transAxes, ha="center", va="top", fontsize=9, color=PALETTE["ink_soft"])

    bypass, gate = [], []
    pair_labels = []
    for label, off, on, denom in (
        ("Kev-selected\nproposals", 9, 0, 12),
        ("Forced transfer\nchallenge", 6, 0, 6),
    ):
        pair_labels.append(label)
        bypass.append(off/denom)
        gate.append(on/denom)
    x = [0, 1]
    width = 0.32
    offbars = physical.bar([v-width/2 for v in x], bypass, width, color=PALETTE["neutral_dark"])
    onbars = physical.bar([v+width/2 for v in x], gate, width, color=PALETTE["blue_main"])
    for bars, counts, condition in ((offbars, ["9/12", "6/6"], "Bypassed"),
                                    (onbars, ["0/12", "0/6"], "Gate on")):
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            xpos = bar.get_x() + bar.get_width()/2
            if height > 0.15:
                physical.text(xpos, height-0.12, count, ha="center", va="top",
                              fontsize=9, color=PALETTE["white"], fontweight="bold")
            else:
                physical.text(xpos, 0.04, count, ha="center", va="bottom",
                              fontsize=9, color=PALETTE["blue_main"], fontweight="bold")
    physical.set_xticks(x, pair_labels)
    physical.set_ylim(0, 1.15)
    physical.set_ylabel("Unauthorized movement rate")
    physical.set_title("C  Panda replay: bypass vs gate", loc="left", fontweight="bold")
    physical.grid(axis="y", color=PALETTE["neutral"], alpha=0.35, linewidth=0.8)

    fig.subplots_adjust(left=0.19, right=0.99, bottom=0.34, top=0.91, wspace=0.40)
    out = args.output if args.output.is_absolute() else ROOT / args.output
    finalize_figure(fig, out, tight=False)
    print(json.dumps({"figure": str(out), "formats": ["png", "pdf"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
