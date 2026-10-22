"""E7: PAI-autonomous decision (PoLEn ch. 7 Art. 2) vs human voting."""

from __future__ import annotations

import random
from pathlib import Path

from ..autonomy import pai_decide, report
from ..metrics import normalized_regret
from ..plotstyle import COND_STYLE, DOWN, PALETTE, UP, finalize_figure, new_figure, plot_line
from ..simulate import Scenario, _allocation, _ci
from ..voting import Ballot, tally
from ._common import BASELINE, fig_path, frange, seed, write_csv

METHODS = ["PAI raw sum", "PAI utilitarian", "PAI borda", "vote quadratic-equal", "vote ranked-equal"]
SHOWN = {  # figure shows 4 series; borda stays in the CSV
    "PAI raw sum": {"color": PALETTE["blue_main"], "ls": "-", "marker": "o"},
    "PAI utilitarian": {"color": PALETTE["green_3"], "ls": "-", "marker": "D"},
    "vote quadratic-equal": COND_STYLE["quadratic-equal"],
    "vote ranked-equal": COND_STYLE["ranked-equal"],
}


def _pod(sc: Scenario, rng: random.Random):
    n = sc.n
    n_min = max(1, round(sc.minority_frac * n))
    base = [sc.minority_u if i < n_min else sc.majority_u for i in range(n)]
    return [[min(max(x + rng.gauss(0, sc.noise), 0.0), 1.0) for x in b] for b in base]


def e7_autonomy(out: Path, reps: int, log) -> list[Path]:
    strategic_share = frange(0, 1, 6)
    noise = 0.1
    sc = BASELINE
    k = len(sc.majority_u)
    min_fav = max(range(k), key=lambda j: sc.minority_u[j])
    rows = []
    for s in strategic_share:
        rng = random.Random(seed("E7", s))
        acc = {m: {"minority_win": [], "regret": []} for m in METHODS}
        for _ in range(reps):
            u = _pod(sc, rng)
            n = len(u)
            strat = [rng.random() < s for _ in range(n)]
            reps_ = [report(u[i], noise, rng, strat[i]) for i in range(n)]
            winners = {"PAI raw sum": pai_decide(reps_, "raw"),
                       "PAI utilitarian": pai_decide(reps_, "utilitarian"),
                       "PAI borda": pai_decide(reps_, "borda")}
            for m, rule in (("vote quadratic-equal", "quadratic"), ("vote ranked-equal", "linear")):
                ballots = [Ballot(f"p{i}", _allocation(u[i], 100, rule, "strategic" if strat[i] else "sincere",
                                                       sc.temperature), 100) for i in range(n)]
                winners[m] = tally(ballots, rule).winner
            for m, w in winners.items():
                acc[m]["minority_win"].append(int(w == min_fav))
                acc[m]["regret"].append(normalized_regret(u, w))
        for m in METHODS:
            mw, rg = acc[m]["minority_win"], acc[m]["regret"]
            rows.append({"strategic_share": s, "method": m, "minority_win": sum(mw) / reps,
                         "minority_win_ci": _ci(mw), "regret": sum(rg) / reps, "regret_ci": _ci(rg)})
        log(f"E7 strategic share {s:.1f}")
    write_csv(rows, out, "e7_autonomy.csv")
    fig, axes = new_figure(1, 2, panel=(6.2, 5.2))
    for m, st in SHOWN.items():
        rs = [r for r in rows if r["method"] == m]
        for ax, metric in zip(axes[0], ("minority_win", "regret")):
            plot_line(ax, strategic_share, [r[metric] for r in rs], color=st["color"], ls=st["ls"],
                      marker=st["marker"], err=[r[f"{metric}_ci"] for r in rs], label=m)
    for ax in axes[0]:
        ax.set_xlabel("share of people who exaggerate")
    axes[0][0].set_ylabel("P(minority's option wins)" + UP)
    axes[0][0].set_ylim(0, 1.02)
    axes[0][1].set_ylabel("equal-weight regret" + DOWN)
    axes[0][0].legend(loc="upper right", fontsize=12)
    return finalize_figure(fig, fig_path(out, "e7_pai_autonomy_vs_voting"))
