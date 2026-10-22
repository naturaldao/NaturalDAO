"""Figure 4: honest probabilities and the missing "I don't know" (axis G4).

All values are transcribed from full texts; locators in comments.
"""
import matplotlib.pyplot as plt
import numpy as np

from f4p_style import PALETTE, apply_publication_style, finalize_figure

DATA = {
    # (a) |P(X) + P(not X) - 1|, 480 negation pairs; arXiv:2609.33209 Table 1, Sec 5.1
    "negation": [
        ("Jev (hosted)", 0.064, 0.055, 0.072),
        ("Qwen3.8-27B\nverbalised", 0.122, 0.098, 0.148),
        ("Qwen3.8-27B\nfirst token", 0.293, 0.270, 0.316),
    ],
    "noise_floor": 0.013,  # Sec 5.1, Jev repeat-noise floor
    # Jev violation concentrated where it is unsure, Sec 5.5
    "by_confidence": [("|s-0.5| < 0.2", 0.142, 0.124, 0.162), ("|s-0.5| >= 0.4", 0.018, 0.010, 0.029)],
    # (b) median soft accuracy (OVL) of Jev Choice on Sys1Cal-v1; arXiv:2609.35342 Table 3
    "soft_acc": [
        ("Raw Choice\n(binary)", 0.771, "raw"),
        ("Inverse-calibrated\n(binary)", 0.903, "fix"),
        ("True/Unknown/False\ninterval", 0.978, "interval"),
    ],
    # (c) expected calibration error before and after local recalibration
    "recal": [
        # arXiv:2609.24052 Table 6: Jev raw 0.0231 -> pooled Platt/isotonic out-of-fold 0.0069
        ("Crash narratives\n(2,416 labels)", 0.0231, 0.0069),
        # arXiv:2609.27607 Sec 5.6: sentence-level hold-out, raw 0.1235 -> isotonic 0.0077
        ("Radiology sentences\n(hold-out)", 0.1235, 0.0077),
    ],
    # (d) confidently wrong: empathy task, arXiv:2609.24574 Sec 4.4 / abstract
    # three balanced classes (166 each) -> majority base rate 1/3; 0.371 is Jev accuracy on all items
    "empathy": {"acc_confident": 0.383, "acc_all": 0.371, "base_rate": 1 / 3, "share_conf_ge_0.9": 0.78, "ece": 0.538},
}


def main():
    apply_publication_style(font_size=14, axes_linewidth=2)
    fig, axes = plt.subplots(2, 2, figsize=(13, 10.5))
    axes = axes.ravel()

    # (a)
    ax = axes[0]
    labels = [d[0] for d in DATA["negation"]]
    v = np.array([d[1] for d in DATA["negation"]])
    err = np.array([[d[1] - d[2] for d in DATA["negation"]], [d[3] - d[1] for d in DATA["negation"]]])
    cols = [PALETTE["blue_main"], PALETTE["neutral"], PALETTE["neutral"]]
    bars = ax.bar(np.arange(3), v, 0.6, yerr=err, capsize=5, color=cols, edgecolor="black", linewidth=1.5,
                  error_kw={"linewidth": 1.5})
    for r, val in zip(bars, v):
        ax.text(r.get_x() + r.get_width() / 2, val + 0.03, f"{val:.3f}", ha="center", fontsize=12)
    ax.axhline(DATA["noise_floor"], color=PALETTE["red_strong"], linestyle="--", linewidth=1.5)
    ax.text(2.35, DATA["noise_floor"] + 0.006, "Jev repeat-noise floor", color=PALETTE["red_strong"],
            ha="right", va="bottom", fontsize=11)
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(labels, fontsize=11.5)
    ax.set_ylabel(r"|P(X) + P(not X) $-$ 1|  (95% CI)")
    ax.set_ylim(0, 0.36)
    ax.set_title("(a) Complementary probabilities\n     do not sum to one", loc="left", fontsize=14)

    # (b)
    ax = axes[1]
    styles = {"raw": (PALETTE["red_2"], ""), "fix": (PALETTE["green_3"], ""), "interval": (PALETTE["green_1"], "//")}
    for i, (lab, val, kind) in enumerate(DATA["soft_acc"]):
        c, h = styles[kind]
        ax.bar(i, val, 0.62, color=c, edgecolor="black", linewidth=1.5, hatch=h)
        ax.text(i, val + 0.008, f"{val:.3f}", ha="center", va="bottom", fontsize=12)
    ax.set_xticks(range(3))
    ax.set_xticklabels([d[0] for d in DATA["soft_acc"]], fontsize=11.5)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Median soft accuracy (Sys1Cal-v1)")
    ax.text(2, 0.05, "more permissive\nmetric", ha="center", va="bottom", fontsize=10.5, color=PALETTE["ink"])
    ax.set_title("(b) Restoring a third value", loc="left", fontsize=14)

    # (c)
    ax = axes[2]
    labels = [d[0] for d in DATA["recal"]]
    x = np.arange(len(labels))
    w = 0.36
    for k, (col, lab) in enumerate([(PALETTE["red_2"], "Raw"), (PALETTE["green_3"], "Recalibrated (out-of-sample)")]):
        vals = [d[1 + k] for d in DATA["recal"]]
        bars = ax.bar(x + (k - 0.5) * w, vals, w, color=col, edgecolor="black", linewidth=1.5, label=lab)
        for r, val in zip(bars, vals):
            ax.text(r.get_x() + r.get_width() / 2, val + 0.003, f"{val:.4f}", ha="center", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11.5)
    ax.set_ylabel("Expected calibration error")
    ax.set_ylim(0, 0.145)
    ax.legend(loc="upper left", fontsize=11.5)
    ax.set_title("(c) Calibration is local", loc="left", fontsize=14)

    # (d)
    ax = axes[3]
    e = DATA["empathy"]
    vals = [e["base_rate"], e["acc_all"], e["acc_confident"]]
    cols = [PALETTE["neutral"], PALETTE["red_2"], PALETTE["red_strong"]]
    bars = ax.bar([0, 1, 2], vals, 0.6, color=cols, edgecolor="black", linewidth=1.5)
    for r, val in zip(bars, vals):
        ax.text(r.get_x() + r.get_width() / 2, val + 0.015, f"{val:.3f}", ha="center", fontsize=12)
    ax.axhline(0.9, color=PALETTE["blue_main"], linestyle="--", linewidth=1.5)
    ax.text(2.4, 0.91, "confidence of\nthese items ≥ 0.9", ha="right", va="bottom", fontsize=10.5,
            color=PALETTE["blue_main"])
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["Majority\nguess", "Jev,\nall items", "Jev,\nconf. ≥ 0.9"], fontsize=11.5)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Accuracy (empathy annotation)")
    ax.text(1.0, 0.62, f"{int(e['share_conf_ge_0.9'] * 100)}% of items at conf. ≥ 0.9\nECE {e['ece']:.3f}",
            ha="center", va="top", fontsize=11.5)
    ax.set_title("(d) Confident, near chance", loc="left", fontsize=14)

    finalize_figure(fig, "fig_honesty")


if __name__ == "__main__":
    main()
