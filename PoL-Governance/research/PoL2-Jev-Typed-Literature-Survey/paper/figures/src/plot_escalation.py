"""Figure 5: escalation chains (axis G6). Accept-when-confident cascades and correlated errors.

All values are transcribed from full texts; locators in comments.
"""
import matplotlib.pyplot as plt
import numpy as np

from f4p_style import PALETTE, apply_publication_style, finalize_figure

DATA = {
    # (a) Jev -> GPT-6 Astra cascades, arXiv:2609.26550. (label, fee share of GPT-6, delta pp, CI lo, CI hi)
    "jev_gpt6": [
        ("Held-out, all (v2 headline)", 0.414, 0.93, 0.24, 1.66),     # Table 4
        ("RewardBench part", 0.267, 1.27, 0.45, 2.03),                # Table 4
        ("JudgeBench part", 0.668, -0.74, -2.22, 0.74),               # Table 4
        ("v1, 510 pairs", 0.568, -0.59, -1.78, 0.59),                 # appendix, earlier figures
        ("Prospective live, 570", 0.755, 0.0, None, None),            # Table 5; Sec 9
    ],
    # (b) arXiv:2609.29769 Sec 6.2: LLM evaluators repeat Jev's most confident errors
    "repeat": {"observed": 0.960, "independent": 0.503, "count": "242 / 252"},
    # (c) arXiv:2609.29769 v2 Table 4: cross-fitted cascade minus best single evaluator (pp), all nine panels
    # Only rows that the full-text extraction could verify against prose are plotted.
    "vs_best": [("HealthBench", 1.5), ("USR-PC", 0.8), ("LFQA", 0.6), ("ELLIPSE", -0.1), ("USR-TC", -0.7),
                ("FED-Dialogue", -0.9), ("HelpSteer2", -0.9), ("RiceChem", -1.0), ("FED-Turn", -7.3)],
    "vs_best_summary": "6 of 9 panels below the best single evaluator",
}


def main():
    apply_publication_style(font_size=14, axes_linewidth=2)
    fig = plt.figure(figsize=(13, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.1, 1])
    axes = [fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]

    # (a)
    ax = axes[0]
    ax.axhline(0, color=PALETTE["ink"], linewidth=1.5)
    ax.text(0.01, 0.08, "GPT-6 alone", ha="left", va="bottom", fontsize=11.5, transform=ax.get_yaxis_transform())
    offsets = {0: (8, 6), 1: (8, 6), 2: (8, -16), 3: (-8, -18), 4: (10, 8)}
    for i, (lab, fee, d, lo, hi) in enumerate(DATA["jev_gpt6"]):
        if lo is None:
            c = PALETTE["blue_main"]
        elif lo > 0:
            c = PALETTE["green_3"]
        elif hi < 0:
            c = PALETTE["red_strong"]
        else:
            c = PALETTE["neutral_dark"]  # interval includes 0
        if lo is not None:
            ax.errorbar(fee, d, yerr=[[d - lo], [hi - d]], fmt="o", color=c, markersize=10, capsize=5,
                        markeredgecolor="black", elinewidth=1.8)
        else:
            ax.plot(fee, d, "D", color=c, markersize=10, markeredgecolor="black")
        dx, dy = offsets[i]
        ax.annotate(lab, (fee, d), textcoords="offset points", xytext=(dx, dy), fontsize=11,
                    ha="left" if dx > 0 else "right")
    ax.set_xlim(0.2, 1.0)
    ax.set_ylim(-2.6, 2.4)
    ax.set_xlabel("Fee as a share of GPT-6 alone")
    ax.set_ylabel("Accuracy change vs GPT-6 (pp, 95% CI)")
    ax.set_title("(a) Escalating to a reasoning model (Jev → GPT-6)", loc="left", fontsize=14)

    # (b)
    ax = axes[1]
    r = DATA["repeat"]
    bars = ax.bar([0, 1], [r["independent"], r["observed"]], 0.6,
                  color=[PALETTE["neutral"], PALETTE["red_strong"]], edgecolor="black", linewidth=1.5)
    for b, val in zip(bars, [r["independent"], r["observed"]]):
        ax.text(b.get_x() + b.get_width() / 2, val + 0.02, f"{val * 100:.1f}%", ha="center", fontsize=12)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["If errors were\nindependent", f"Observed\n({r['count']})"], fontsize=11.5)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("LLM evaluators repeating Jev's\nmost confident errors")
    ax.set_title("(b) Confident errors are repeated", loc="left", fontsize=14)

    # (c)
    ax = axes[2]
    labs = [d[0] for d in DATA["vs_best"]]
    vals = [d[1] for d in DATA["vs_best"]]
    cols = [PALETTE["green_3"] if v > 0 else PALETTE["red_2"] for v in vals]
    ax.barh(np.arange(len(labs)), vals, 0.6, color=cols, edgecolor="black", linewidth=1.5)
    for i, v in enumerate(vals):
        ax.text(v + (0.08 if v >= 0 else -0.08), i, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right",
                fontsize=12)
    ax.axvline(0, color=PALETTE["ink"], linewidth=1.5)
    ax.set_yticks(np.arange(len(labs)))
    ax.set_yticklabels(labs)
    ax.set_xlim(-8.6, 2.6)
    ax.set_xlabel("Cascade minus best single evaluator (pp)")
    ax.text(-3.0, -0.75, DATA["vs_best_summary"], ha="center", va="center", fontsize=10.5)
    ax.set_ylim(-1.2, len(labs) - 0.4)
    ax.set_title("(c) Escalating among peer evaluators", loc="left", fontsize=14)

    finalize_figure(fig, "fig_escalation")


if __name__ == "__main__":
    main()
