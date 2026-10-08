"""Figure (architecture): a reference design for the PoL2 safety valve with typed decision models as detectors."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from f4p_style import PALETTE, apply_publication_style, finalize_figure

FS_TITLE, FS_BODY = 14, 12.5


def box(ax, x, y, w, h, title, body, face, edge, text_color=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.2", facecolor=face,
                                edgecolor=edge, linewidth=2))
    c = text_color or PALETTE["ink"]
    ax.text(x + 1.2, y + h - 1.6, title, ha="left", va="top", fontsize=FS_TITLE, fontweight="bold", color=c)
    ax.text(x + 1.2, y + h - 6.4, body, ha="left", va="top", fontsize=FS_BODY, linespacing=1.35, color=c)


def arrow(ax, p, q, color=None, ls="-", rad=0.0, lw=2.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=20, linewidth=lw, linestyle=ls,
                                 color=color or PALETTE["ink"], connectionstyle=f"arc3,rad={rad}"))


def main():
    apply_publication_style(font_size=12, axes_linewidth=2)
    fig, ax = plt.subplots(figsize=(12.5, 10))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    blue, light = PALETTE["blue_main"], "#E7EEF7"
    grey = PALETTE["neutral_dark"]

    # row 1: surface -> rules -> detectors
    box(ax, 0.5, 70, 28, 28, "1  Surface + reference",
        "user input / assistant\noutput / tool action\n\nwith the policy, instruction\nor prior turn it is judged\nagainst (G1)", "white", blue)
    box(ax, 35.5, 70, 24, 28, "2  Hard rules",
        "authorisation scope\nenforced in code,\nnot by a model\n\ndeterministic policy\nchecks", "white", grey)
    box(ax, 66.5, 70, 33, 28, "3  Independent detectors",
        "≥2 independently built: typed model\n+ another family or a rule (G2, G6)\n\nconforming / violating / insufficient\n+ sufficiency question (G4)\n\nneutral, swap-tested names (G3)",
        light, blue)
    arrow(ax, (29.2, 84), (35.0, 84))
    arrow(ax, (60.2, 84), (66.0, 84))

    # row 2: calibration -> action -> human
    box(ax, 66.5, 33, 33, 27, "4  Local calibration",
        "per-category thresholds fitted\non held-out labelled data (G1, G4)\n\nprobabilities withheld; unneeded\nsensitive fields kept out; untrusted\nqueries restricted, logged (G2)", light, blue)
    box(ax, 35.5, 33, 24, 27, "5  Action",
        "agree + confident:\nallow / repair / brief hold\n(final block needs\na person; appeal)\n\nelse: clarify, or escalate\nwith stated grounds (G6)", "white", PALETTE["green_3"])
    box(ax, 0.5, 33, 28, 27, "6  Human review",
        "end of every chain\nthat could block (G6, T4)\n\n+ random audit of\nhigh-confidence\nautomatic decisions", PALETTE["red_1"], PALETTE["red_strong"])
    arrow(ax, (83, 69.4), (83, 60.6))
    arrow(ax, (66.0, 46.5), (60.2, 46.5))
    arrow(ax, (35.0, 46.5), (29.2, 46.5))

    # feedback loop: human review -> calibration
    arrow(ax, (14.5, 32.4), (75, 32.4), color=PALETTE["red_strong"], rad=0.18, lw=2.2)
    ax.text(45, 24.2, "questioning (Art. 9) and audit outcomes update the calibration set",
            ha="center", va="center", fontsize=FS_BODY, color=PALETTE["red_strong"])

    # decision record
    ax.add_patch(FancyBboxPatch((0.5, 1), 99, 16.5, boxstyle="round,pad=0.3,rounding_size=1.2",
                                facecolor=blue, edgecolor="black", linewidth=1.8))
    ax.text(2, 15.6, "7  Decision record → tamper-evident log; public copy delayed, coarsened (Art. 4, 5(5), 9(3); G5)",
            ha="left", va="top", fontsize=FS_TITLE, fontweight="bold", color="white")
    ax.text(2, 10.2, "question, options and definitions · hash of input fields · probabilities · model, weights and\n"
                     "calibration versions · rule or EAP clause cited as ground · written explanation · reviewer outcome",
            ha="left", va="top", fontsize=FS_BODY, color="white", linespacing=1.4)
    ax.text(99, 19.3, "every step is recorded", ha="right", va="bottom", fontsize=11.5, color=grey, style="italic")
    finalize_figure(fig, "fig_architecture", pad=0.5)


if __name__ == "__main__":
    main()
