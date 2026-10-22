"""Figure (PRISMA 2020-style flow): identification, screening and inclusion per retrieval route.

Counts from the search log (scratchpad search/new_papers.md, sections 1.1-1.2) and data/*.csv.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from f4p_style import PALETTE, apply_publication_style, finalize_figure

FS = 11.5


def box(ax, x, y, w, h, text, face="white", edge=None, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8", facecolor=face,
                                edgecolor=edge or PALETTE["blue_main"], linewidth=1.6))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=FS, linespacing=1.3,
            fontweight="bold" if bold else "normal")


def excl(ax, x, y, w, h, text):
    box(ax, x, y, w, h, text, face=PALETTE["red_1"], edge=PALETTE["red_strong"])


def arrow(ax, p, q):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=14, linewidth=1.5, color=PALETTE["ink"]))


def main():
    apply_publication_style(font_size=FS, axes_linewidth=2)
    fig, ax = plt.subplots(figsize=(13, 10))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    for y, lab in [(88, "Identification"), (60, "Screening"), (12, "Included")]:
        ax.text(1, y, lab, rotation=90, ha="center", va="center", fontsize=FS + 1, fontweight="bold",
                color=PALETTE["blue_main"])

    # arXiv column
    box(ax, 4, 83, 27, 11, "arXiv API, 18 queries (4 Oct)\n955 records, 606 unique")
    excl(ax, 4, 70, 27, 8, "Before 15 Sep: 517")
    arrow(ax, (17.5, 82.6), (17.5, 78.4))
    box(ax, 4, 58, 27, 9, "Dated on/after 15 Sep: 89\n(63 in v0.2 corpus; 1 excluded\nin v0.2 at full text)")
    arrow(ax, (17.5, 69.6), (17.5, 67.4))
    box(ax, 4, 45, 27, 9, "New records screened: 25")
    arrow(ax, (17.5, 57.6), (17.5, 54.4))
    excl(ax, 4, 33, 27, 9, "Excluded: 5 by title,\n4 at abstract (name clash,\nno typed model)")
    arrow(ax, (17.5, 44.6), (17.5, 42.4))
    box(ax, 4, 22, 27, 8, "Full text assessed: 16\nexcluded 1 (unrelated 'Jev')")
    arrow(ax, (17.5, 32.6), (17.5, 30.4))

    # Zenodo column
    box(ax, 36, 83, 26, 11, "Zenodo REST API, 11 queries\n~330 records screened")
    excl(ax, 36, 70, 26, 8, "No keyword/date match: ~268")
    arrow(ax, (49, 82.6), (49, 78.4))
    box(ax, 36, 58, 26, 9, "Matched: 61 (+1 by hand)")
    arrow(ax, (49, 69.6), (49, 67.4))
    excl(ax, 36, 43, 26, 12, "Excluded 21: duplicates 6,\ncompanion deposits 5,\noff-topic/tool-only 9,\nnot a typed model 1")
    arrow(ax, (49, 57.6), (49, 55.4))
    box(ax, 36, 31, 26, 9, "Eligible: 41; excluded 13\napps/tools without evaluation;\nfull text: 28, excluded 1")
    arrow(ax, (49, 42.6), (49, 40.4))

    # other routes
    box(ax, 67, 83, 30, 11, "Trackers: All about Jev (52 papers),\nAwesome System One Models (213);\nHF Papers, OpenReview, SSRN, web")
    excl(ax, 67, 66, 30, 12, "Already found or pre-release\nbackground; SSRN = Zenodo\nduplicate; no new items")
    arrow(ax, (82, 82.6), (82, 78.4))
    box(ax, 67, 47, 30, 12, "From trackers: arXiv 2\n(1 reclassified as context),\nalphaXiv 1, grey sources 9\n(2 commentary: context)")

    # included
    box(ax, 4, 3, 27, 13, "arXiv papers: 79\n(63 + 1 tracker + 15 new)\nread in full", face="#E7EEF7", bold=True)
    arrow(ax, (17.5, 21.6), (17.5, 16.4))
    box(ax, 36, 3, 26, 13, "Zenodo records: 27\nread in full", face="#E7EEF7", bold=True)
    arrow(ax, (49, 30.6), (49, 16.4))
    box(ax, 67, 3, 30, 13, "alphaXiv: 1\ngrey literature: 7\nread in full", face="#E7EEF7", bold=True)
    arrow(ax, (82, 46.6), (82, 16.4))

    finalize_figure(fig, "fig_prisma", pad=0.5)


if __name__ == "__main__":
    main()
