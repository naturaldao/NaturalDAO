"""Figures for ``pol2dao simulate`` and ``pol2dao published`` (needs matplotlib).

Style comes from :mod:`pol2dao.plotstyle`; see docs/figure-style.md.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .plotstyle import (DOWN, PALETTE, UP, annotate_bars, apply_publication_style, bar, cond_handles,
                        finalize_figure, legend_panel, new_figure)

BEHAVIORS = ("sincere", "strategic")


def simulation_figure(rows: list[dict], metric: str, path: str | Path, ylabel: str) -> list[Path]:
    """2x2 panels (scenario x who holds 20/80 power); in each, the 7 conditions for both voter behaviours."""
    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as plt

    apply_publication_style()
    panels = [("baseline", "random"), ("baseline", "majority"), ("hostile", "random"), ("hostile", "majority")]
    conds = list(dict.fromkeys(r["condition"] for r in rows))
    arrow = DOWN if metric == "regret" else UP
    fig = plt.figure(figsize=(19, 9.5))
    gs = gridspec.GridSpec(2, 3, width_ratios=[1, 1, 0.42], figure=fig)
    width = 0.8 / len(conds)
    top = 1.0 if metric != "regret" else max(r[metric] + r.get(f"{metric}_ci", 0) for r in rows) * 1.15
    for k, (sc, h) in enumerate(panels):
        ax = fig.add_subplot(gs[k // 2, k % 2])
        for j, c in enumerate(conds):
            vals, errs = [], []
            for beh in BEHAVIORS:
                r = next(x for x in rows if x["scenario"] == sc and x["power_holders"] == h
                         and x["behavior"] == beh and x["condition"] == c)
                vals.append(r[metric])
                errs.append(r.get(f"{metric}_ci", 0.0))
            xs = [i - 0.4 + width * (j + 0.5) for i in range(len(BEHAVIORS))]
            bar(ax, xs, vals, name=c, width=width, err=errs)
        ax.set_xticks(range(len(BEHAVIORS)), [f"{b} voters" for b in BEHAVIORS])
        ax.set_title(f"{'no hostility' if sc == 'baseline' else 'hostile talk'} · 20/80 power held by {h}")
        if k % 2 == 0:
            ax.set_ylabel(ylabel + arrow)
        ax.set_ylim(0, top)
    legend_panel(fig.add_subplot(gs[:, 2]), cond_handles(conds, "bar"), conds, title="condition")
    return finalize_figure(fig, path)


def published_counterfactual_figure(tokens_csv: Path, means_csv: Path, path: str | Path) -> list[Path]:
    """Ranked 20/80 conditions: actual token shares vs equal-budget shares (same split)."""
    tok = {(r["round"], r["cond"]): r for r in csv.DictReader(tokens_csv.open(encoding="utf-8"))}
    mea = {(r["round"], r["cond"]): r for r in csv.DictReader(means_csv.open(encoding="utf-8"))}
    fig, axes = new_figure(1, 2, panel=(6.2, 5.0), sharey=True)
    for ax, rnd in zip(axes[0], ("1", "2")):
        key = (rnd, "ranked-early")
        t = [float(tok[key][f"tokens_{i}"]) for i in range(1, 5)]
        a = [x / sum(t) for x in t]
        m = [float(mea[key][f"mean_r{i}"]) for i in range(1, 5)]
        e = [x / sum(m) for x in m]
        ax.set_ylim(0, 0.6)
        b1 = bar(ax, [x - 0.2 for x in range(4)], a, name="ranked-20/80", width=0.4, label="actual (20/80 budgets)")
        b2 = bar(ax, [x + 0.2 for x in range(4)], e, color=PALETTE["blue_main"], hatch="", width=0.4,
                 label="equal budgets, same split")
        for bars, vals in ((b1, a), (b2, e)):
            j = max(range(4), key=lambda i: vals[i])
            annotate_bars(ax, [bars[j]], ["win"], fmt="{}")
        ax.set_xticks(range(4), ["1", "2", "3", "4"])
        ax.set_xlabel("option")
        ax.set_title(f"round {rnd} · ranked · 20/80 (n = {tok[key]['n']})")
    axes[0][0].set_ylabel("share of spent tokens")
    axes[0][1].legend(loc="upper right")
    return finalize_figure(fig, path)
