"""Figure 3: the safety valve is a detector, and a fragile one (axes G1-G3).

All values are transcribed from full texts; locators in comments.
"""
import matplotlib.pyplot as plt
import numpy as np

from f4p_style import PALETTE, apply_publication_style, finalize_figure

DATA = {
    # (a) F1 at the default threshold 0.5 versus a fitted threshold
    "threshold": [
        # arXiv:2609.29429 Sec 4.4: median F1 0.706 at t=0.5 -> 0.822 cross-validated threshold
        ("Just Ask Jev\n(median, 31 benchmarks)", 0.706, 0.822),
        # jkf87 replication README: TensorTrust hijacking, F1 0.158 at 0.5 -> 0.947 at 0.35 (cross-validated)
        ("Independent replication\n(TensorTrust hijacking)", 0.158, 0.947),
    ],
    # (b) targeted flip rate from natural context additions, arXiv:2609.30243 Sec 4.2 / Table 1
    "jevout": [
        ("Jev (hosted)", 312, 508),
        ("Qwen3-1.7B typed", 238, 328),
        ("Von", 240, 328),
        ("Qwen (plain)", 185, 285),
    ],
    # (c) answer flip rate when the definitions bound to a name pair are swapped, arXiv:2609.26758 Table 1 / Table 6
    "names": {
        "pairs": ["0 / 1", "A / B", "false / true", "no / yes"],
        "Laya (open)": [0.0650, 0.0600, 0.4967, 0.7692],
        "Open-Jev (open)": [0.0361, 0.2600, 0.4783, 0.1950],
        "Jev (hosted)": [0.0208, 0.0167, 0.3192, 0.3250],
    },
    # (d) AUC when yes/no names are aligned vs reassigned, arXiv:2609.26758 Sec 4.2, Sec 4.5
    "auc": [("Laya (open)", 0.938, 0.232), ("Jev (hosted)", 0.815, 0.581)],
}


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h


def main():
    apply_publication_style(font_size=14, axes_linewidth=2)
    fig, axes = plt.subplots(2, 2, figsize=(13, 10.5))
    axes = axes.ravel()

    # (a)
    ax = axes[0]
    labels = [d[0] for d in DATA["threshold"]]
    x = np.arange(len(labels))
    w = 0.36
    b1 = ax.bar(x - w / 2, [d[1] for d in DATA["threshold"]], w, color=PALETTE["red_2"], edgecolor="black",
                linewidth=1.5, label="Default threshold 0.5")
    b2 = ax.bar(x + w / 2, [d[2] for d in DATA["threshold"]], w, color=PALETTE["green_3"], edgecolor="black",
                linewidth=1.5, label="Threshold fitted on local data")
    for bars in (b1, b2):
        for r in bars:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.02, f"{r.get_height():.3f}",
                    ha="center", va="bottom", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11.5)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("F1 (failure detection)")
    ax.legend(loc="upper left", fontsize=11.5)
    ax.set_title("(a) Ranking is good, thresholds are local", loc="left", fontsize=14)

    # (b)
    ax = axes[1]
    labels = [d[0] for d in DATA["jevout"]]
    stats = [wilson(k, n) for _, k, n in DATA["jevout"]]
    p = np.array([s[0] for s in stats])
    err = np.array([[s[0] - s[1] for s in stats], [s[2] - s[0] for s in stats]])
    colors = [PALETTE["blue_main"]] + [PALETTE["neutral"]] * 3
    bars = ax.bar(np.arange(len(labels)), p, 0.62, yerr=err, capsize=5, color=colors, edgecolor="black",
                  linewidth=1.5, error_kw={"linewidth": 1.5})
    for r, (_, k, n) in zip(bars, DATA["jevout"]):
        ax.text(r.get_x() + r.get_width() / 2, 0.04, f"{k}/{n}", ha="center", va="bottom", fontsize=11,
                color="white" if r.get_facecolor()[0] < 0.5 else PALETTE["ink"])
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=11.5)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Correct decisions flipped to\nattacker's target (95% CI)")
    ax.set_title("(b) Natural context flips decisions", loc="left", fontsize=14)

    # (c)
    ax = axes[2]
    pairs = DATA["names"]["pairs"]
    models = ["Laya (open)", "Open-Jev (open)", "Jev (hosted)"]
    cols = [PALETTE["neutral"], PALETTE["blue_secondary"], PALETTE["blue_main"]]
    hatches = ["//", "", ""]
    w = 0.26
    x = np.arange(len(pairs))
    for i, (m, c, h) in enumerate(zip(models, cols, hatches)):
        ax.bar(x + (i - 1) * w, DATA["names"][m], w, color=c, edgecolor="black", linewidth=1.3, hatch=h, label=m)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{q}" for q in pairs])
    ax.set_xlabel("Name pair whose bound definitions are swapped")
    ax.set_ylabel("Answers that change")
    ax.set_ylim(0, 0.9)
    ax.legend(loc="upper left", fontsize=11.5)
    ax.set_title("(c) The head follows the option name", loc="left", fontsize=14)

    # (d)
    ax = axes[3]
    for i, (m, a, r) in enumerate(DATA["auc"]):
        c = PALETTE["neutral_dark"] if i == 0 else PALETTE["blue_main"]
        ax.plot([0, 1], [a, r], "-o", color=c, linewidth=2.5, markersize=10, label=m)
        ax.text(-0.08, a, f"{a:.3f}", ha="right", va="center", fontsize=12, color=c)
        ax.text(1.08, r, f"{r:.3f}", ha="left", va="center", fontsize=12, color=c)
    ax.axhline(0.5, color=PALETTE["red_strong"], linestyle="--", linewidth=1.5)
    ax.text(0.5, 0.47, "chance", color=PALETTE["red_strong"], ha="center", va="top", fontsize=11.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["definitions\naligned", "definitions\nswapped"])
    ax.set_xlim(-0.45, 1.45)
    ax.set_ylim(0, 1)
    ax.set_ylabel("AUC")
    ax.legend(loc="lower left", fontsize=11.5)
    ax.set_title("(d) Always well-typed, still inverted", loc="left", fontsize=14)

    finalize_figure(fig, "fig_fragility")


if __name__ == "__main__":
    main()
