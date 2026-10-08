"""Figure (corpus): the evidence base. (a) daily first submissions by source and tier; (b) axis x source coverage.

Reads data/papers.csv, data/zenodo_preprints.csv, data/grey_literature.csv and data/evidence_coding.csv;
documents reclassified as context (excluded_reason set) and the two trackers are not counted.
"""
import csv
from collections import Counter
from datetime import date, timedelta

import matplotlib.pyplot as plt
import numpy as np

from f4p_style import DATA_DIR, PALETTE, apply_publication_style, finalize_figure

TIER_EN = {"核心": "Core", "相关": "Related", "背景": "Background"}
TIER_COLOR = {"Core": PALETTE["blue_main"], "Related": PALETTE["blue_secondary"], "Background": PALETTE["neutral"]}
AXES = ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]
AXIS_LABEL = {
    "G1": "G1 Detection",
    "G2": "G2 Attackability",
    "G3": "G3 Semantic fairness",
    "G4": "G4 Honesty",
    "G5": "G5 Decision chains",
    "G6": "G6 Oversight",
    "G7": "G7 Public scale",
}
RELEASE = date(2026, 9, 15)
CUTOFF = date(2026, 10, 1)


def read(name):
    return list(csv.DictReader((DATA_DIR / name).open(encoding="utf-8")))


def main():
    ev = read("evidence_coding.csv")
    excluded = {r["doc"] for r in ev if r["excluded_reason"]}
    counted_grey = {r["doc"] for r in ev if r["source"] == "grey" and not r["excluded_reason"]}
    greykey = {"G-CheckPoint": "checkpoint2026jev", "G-Simmons": "simmons2026saidno", "G-ZhBench": "qin2026zhdecisionbench",
               "G-Replication": "jkf87_2026replication", "G-Molas": "molas2026calibrated", "G-Grazian": "grazian2026calibrated",
               "G-Bernoulli": "yurin2026confident", "G-Willison": "willison2026jev", "G-Sev": "le2026sev"}
    papers = [p for p in read("papers.csv") if "arx" + p["arxiv_id"].split(".")[-1] not in excluded]
    zenodo = [z for z in read("zenodo_preprints.csv") if "zen" + z["doi"].rsplit(".", 1)[1] not in excluded]
    grey = [g for g in read("grey_literature.csv") if greykey.get(g["id"]) in counted_grey]
    apply_publication_style(font_size=15, axes_linewidth=2)
    fig, (ax_t, ax_h) = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1.2, 1]})

    # (a) daily first submissions, stacked: arXiv tiers, then other preprints (alphaXiv + Zenodo)
    days = [RELEASE + timedelta(d) for d in range((CUTOFF - RELEASE).days + 1)]
    x = np.arange(len(days))
    bottom = np.zeros(len(days))
    arxiv = [p for p in papers if p["arxiv_id"]]
    for tier in ("Core", "Related", "Background"):
        c = Counter(p["published"] for p in arxiv if TIER_EN.get(p["tier"]) == tier)
        y = np.array([c.get(d.isoformat(), 0) for d in days])
        ax_t.bar(x, y, bottom=bottom, color=TIER_COLOR[tier], edgecolor="black", linewidth=1.2,
                 width=0.8, label=f"arXiv {tier.lower()} (n={int(y.sum())})")
        bottom += y
    other_dates = [p["published"] for p in papers if not p["arxiv_id"]] + [z["date"] for z in zenodo]
    c = Counter(other_dates)
    y = np.array([c.get(d.isoformat(), 0) for d in days])
    ax_t.bar(x, y, bottom=bottom, color="white", edgecolor="black", linewidth=1.2, hatch="//", width=0.8,
             label=f"Zenodo / alphaXiv (n={int(y.sum())})")
    bottom += y
    gc = Counter(g["date"] for g in grey)
    gy = np.array([gc.get(d.isoformat(), 0) for d in days])
    ax_t.scatter(x[gy > 0], bottom[gy > 0] + 0.6, marker="v", s=70, color=PALETTE["red_strong"],
                 zorder=3, label=f"Grey literature (n={int(gy.sum())})")
    ax_t.axvline(0, color=PALETTE["ink"], linewidth=1.5, linestyle="--")
    ax_t.text(0.35, 0.3 * bottom.max(), "Jev release (15 Sep)", fontsize=12, rotation=90, va="bottom")
    ticks = [i for i, d in enumerate(days) if (d - RELEASE).days % 4 == 0]
    ax_t.set_xticks(ticks)
    ax_t.set_xticklabels([days[i].strftime("%d %b") for i in ticks])
    ax_t.set_ylabel("Documents per day")
    ax_t.set_ylim(0, bottom.max() + 3)
    ax_t.set_xlim(-0.8, len(days) - 0.2)
    ax_t.legend(loc="upper left", bbox_to_anchor=(0.08, 1.0), fontsize=11.5)
    ax_t.set_title("(a) First submissions after release", loc="left", fontsize=15)

    # (b) coded studies per requirement and source type (rows of evidence_coding.csv that enter the tallies)
    sources = ["arXiv", "Zenodo / alphaXiv", "Grey literature"]
    col_of = {"arxiv": 0, "zenodo": 1, "alphaxiv": 1, "grey": 2}
    mat = np.zeros((len(AXES), len(sources)), dtype=int)
    for r in ev:
        if r["in_tally"] == "yes":
            mat[AXES.index(r["axis"]), col_of[r["source"]]] += 1
    ax_h.imshow(mat, cmap="Blues", vmin=0, vmax=max(6, mat.max()), aspect="auto")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            ax_h.text(j, i, str(v) if v else "–", ha="center", va="center", fontsize=13,
                      color="white" if v >= 0.55 * mat.max() else PALETTE["ink"])
    ax_h.set_xticks(range(len(sources)))
    ax_h.set_xticklabels([s.replace(" ", "\n", 1) for s in sources], fontsize=12)
    ax_h.set_yticks(range(len(AXES)))
    ax_h.set_yticklabels([f"{AXIS_LABEL[a]} (n={mat[i].sum()})" for i, a in enumerate(AXES)], fontsize=12)
    ax_h.tick_params(length=0)
    for s in ax_h.spines.values():
        s.set_visible(False)
    ax_h.set_xticks(np.arange(-0.5, len(sources)), minor=True)
    ax_h.set_yticks(np.arange(-0.5, len(AXES)), minor=True)
    ax_h.grid(which="minor", color="white", linewidth=2)
    ax_h.tick_params(which="minor", length=0)
    ax_h.set_title("(b) Coded studies per requirement", loc="left", fontsize=15)

    finalize_figure(fig, "fig_corpus")
    print("matrix", mat.tolist(), "column sums", mat.sum(0).tolist())


if __name__ == "__main__":
    main()
