"""Figure (framework): PoL2 clauses -> axes G1-G7 (with balance of evidence) -> five tensions.

Evidence codes (S = supports the use PoL2 specifies, Q = qualifies it, N = negative) are read from
data/evidence_coding.csv; see the codebook in the paper's appendix.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from f4p_style import DATA_DIR, PALETTE, apply_publication_style, finalize_figure

CLAUSES = [  # must match Table 1 (tab:clauses) in sections/03_method.tex
    ("§5.4.1 Safety valve", ["G1", "G2"]),
    ("Art. 7 Anomaly detection", ["G1"]),
    ("§4.3.3.1 Truncation, self-reflection", ["G2", "G4"]),
    ("§1.5, §4.3.1 Not labels; equal conn.", ["G3"]),
    ("§4.3.2 Love/hate; state of absence", ["G3", "G4"]),
    ("§4.3.3.3 Semantic recognition", ["G3"]),
    ("Art. 4, 5(4)-(5), 9(2) Decision chain", ["G5"]),
    ("Art. 9(7) Non-intervention", ["G6"]),
    ("Art. 10 AI adjudication", ["G6"]),
    ("Art. 2(1), §5.5-5.6 Public scale", ["G7"]),
]

# Evidence codes live in data/evidence_coding.csv (one row per document x axis, with rationale and
# locator), coded for detector use with the symmetric v3 codebook. Only rows with in_tally = yes
# are counted: non-empirical items and items without a typed model are excluded.
def load_evidence():
    import csv
    ev = {}
    with (DATA_DIR / "evidence_coding.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["in_tally"] == "yes":
                ev.setdefault(r["axis"], {})[r["doc"]] = r["code"]
    return ev


EVIDENCE = load_evidence()
AXIS_NAME = {
    "G1": "Detection", "G2": "Attackability", "G3": "Semantic fairness", "G4": "Honesty",
    "G5": "Decision chains", "G6": "Oversight", "G7": "Public scale",
}
TENSIONS = [  # links follow the evidence cited for each tension in sections/05_synthesis.tex
    ("T1 Emotion in language\nvs. persons' states", ["G3", "G4"]),
    ("T2 Binary verdicts vs.\nthree-valued ethics", ["G3", "G4"]),
    ("T3 Transparency vs.\nclosed models", ["G3", "G5", "G7"]),
    ("T4 AI-only adjudication\nvs. correlated errors", ["G6"]),
    ("T5 Assessing persons vs.\nequal connection", ["G2", "G3", "G7"]),
]
COL = {"S": PALETTE["green_3"], "Q": PALETTE["highlight"], "N": PALETTE["red_strong"]}


def main():
    apply_publication_style(font_size=13, axes_linewidth=2)
    fig, ax = plt.subplots(figsize=(12.5, 9.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    axes = list(AXIS_NAME)
    ax_y = {a: 90 - i * 13 for i, a in enumerate(axes)}
    cl_y = [95 - i * 8.6 for i in range(len(CLAUSES))]
    t_y = [88 - i * 17.5 for i in range(len(TENSIONS))]

    # column headers
    for x, txt in [(13, "PoL2 clauses"), (49, "Requirements and evidence"), (86, "Tensions in the text")]:
        ax.text(x, 101, txt, ha="center", va="bottom", fontsize=14, fontweight="bold")

    # clause boxes
    for (txt, links), y in zip(CLAUSES, cl_y):
        ax.add_patch(FancyBboxPatch((0.5, y - 3), 25, 6, boxstyle="round,pad=0.2,rounding_size=0.8",
                                    facecolor="white", edgecolor=PALETTE["blue_main"], linewidth=1.6))
        ax.text(1.5, y, txt, ha="left", va="center", fontsize=12.5)
        for a in links:
            ax.plot([25.9, 33.6], [y, ax_y[a]], color=PALETTE["neutral_dark"], linewidth=0.9, alpha=0.6, zorder=0)

    # axis boxes with stacked evidence bars
    unit = 22.0 / max(len(v) for v in EVIDENCE.values())
    for a in axes:
        y = ax_y[a]
        ax.add_patch(FancyBboxPatch((34, y - 4), 30, 8, boxstyle="round,pad=0.2,rounding_size=0.8",
                                    facecolor=PALETTE["blue_main"], edgecolor="black", linewidth=1.4))
        ax.text(35, y + 1.6, f"{a}  {AXIS_NAME[a]}", ha="left", va="center", fontsize=13.5, color="white",
                fontweight="bold")
        codes = list(EVIDENCE[a].values())
        x = 35
        for k in ("S", "Q", "N"):
            n = codes.count(k)
            if n:
                ax.add_patch(plt.Rectangle((x, y - 3.1), n * unit, 2.6, facecolor=COL[k], edgecolor="black",
                                           linewidth=1))
                ax.text(x + n * unit / 2, y - 1.8, str(n), ha="center", va="center", fontsize=11.5,
                        color="white" if k == "N" else PALETTE["ink"])
                x += n * unit
        ax.text(x + 0.8, y - 1.8, f"n={len(codes)}", ha="left", va="center", fontsize=11.5, color="white")

    # tension boxes
    for (txt, links), y in zip(TENSIONS, t_y):
        ax.add_patch(FancyBboxPatch((73, y - 5.5), 26.5, 11, boxstyle="round,pad=0.2,rounding_size=0.8",
                                    facecolor=PALETTE["red_1"], edgecolor=PALETTE["red_strong"], linewidth=1.6))
        ax.text(74.2, y, txt, ha="left", va="center", fontsize=12.5)
        for a in links:
            ax.plot([64.4, 72.6], [ax_y[a], y], color=PALETTE["red_strong"], linewidth=1.1, alpha=0.55, zorder=0)

    # legend
    for i, (k, lab) in enumerate([("S", "supports"), ("Q", "qualifies"), ("N", "negative")]):
        ax.add_patch(plt.Rectangle((36 + i * 9.5, -3.2), 2.2, 2.6, facecolor=COL[k], edgecolor="black", linewidth=1))
        ax.text(38.7 + i * 9.5, -1.9, lab, ha="left", va="center", fontsize=12.5)
    ax.set_ylim(-5, 104)
    finalize_figure(fig, "fig_framework", pad=0.5)


if __name__ == "__main__":
    main()
