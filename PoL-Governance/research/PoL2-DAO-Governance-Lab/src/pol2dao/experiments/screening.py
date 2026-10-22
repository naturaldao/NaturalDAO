"""E4, E5, E8: the safety valve -- its operating point, its bias, and its timing.

E4  operating point   AUROC x false-flag rate of a synthetic judge -> who benefits
E5  judge bias        a judge that mistakes dissent for hostility
E8  dynamics          minority voice over the course of a deliberation
"""

from __future__ import annotations

import random
from dataclasses import replace
from pathlib import Path
from statistics import mean

from .. import simulate
from ..plotstyle import (DIV_CMAP, DOWN, PALETTE, REF_LINE, UP, finalize_figure, heatmap, new_figure,
                         plot_line)
from ._common import BASELINE, COND, HOSTILE, cell, fig_path, frange, seed, write_csv

STRAT = "strategic"
WIN = "P(minority's option wins)" + UP
SCEN_COLOR = {"baseline": PALETTE["blue_main"], "hostile": PALETTE["red_strong"]}
SCEN_LABEL = {"baseline": "no hostility", "hostile": "hostile talk"}


# ---------------------------------------------------------------------------
# E4 operating point of the judge
# ---------------------------------------------------------------------------

def e4_operating_point(out: Path, reps: int, log) -> list[Path]:
    aurocs = [0.70, 0.80, 0.886, 0.95, 0.99]   # 0.886 = median zero-shot AUROC in the survey
    ffr = [0.005, 0.01, 0.02, 0.05, 0.10, 0.20]
    rows = []
    grids = {}
    for sc_name, sc in (("hostile", replace(HOSTILE, power_holders="majority")),
                        ("baseline", replace(BASELINE, power_holders="majority"))):
        ref = cell(sc, COND["pol2-no-screening"], reps, STRAT, key=("E4ref", sc_name))
        g = [[0.0] * len(ffr) for _ in aurocs]
        for i, a in enumerate(aurocs):
            for j, f in enumerate(ffr):
                fl = simulate.noisy_flagger(a, f, seed=seed("E4", a, f))
                r = cell(sc, COND["pol2"], reps, STRAT, fl, key=("E4", sc_name, a, f))
                g[i][j] = r["minority_win"] - ref["minority_win"]
                rows.append({"scenario": sc_name, "auroc": a, "false_flag_rate": f,
                             "minority_win": r["minority_win"], "minority_win_ci": r["minority_win_ci"],
                             "no_screening": ref["minority_win"], "gain": g[i][j],
                             "hostile_miss_rate": r["hostile_miss_rate"], "benign_flag_rate": r["benign_flag_rate"]})
            log(f"E4 {sc_name} auroc={a}")
        grids[sc_name] = g
    write_csv(rows, out, "e4_operating_point.csv")
    fig, axes = new_figure(1, 2, panel=(7.2, 5.4))
    for k, (ax, sc_name) in enumerate(zip(axes[0], ("hostile", "baseline"))):
        heatmap(ax, grids[sc_name], [f"{f:.0%}" if f >= 0.01 else f"{f:.1%}" for f in ffr],
                [f"{a:.3g}" for a in aurocs], DIV_CMAP, -0.25, 0.25, fmt="{:+.2f}", fontsize=11,
                colorbar=k == 1, cbar_label="Δ " + WIN)
        ax.set_title(SCEN_LABEL[sc_name])
        ax.set_xlabel("false-flag rate on benign messages")
        if k == 0:
            ax.set_ylabel("judge AUROC")
    return finalize_figure(fig, fig_path(out, "e4_judge_operating_point"))


# ---------------------------------------------------------------------------
# E5 judge bias against dissent
# ---------------------------------------------------------------------------

def e5_judge_bias(out: Path, reps: int, log) -> list[Path]:
    biases = frange(0, 2.5, 6)
    rows = []
    refs = {}
    for sc_name, sc in (("hostile", replace(HOSTILE, power_holders="majority")),
                        ("baseline", replace(BASELINE, power_holders="majority"))):
        refs[sc_name] = cell(sc, COND["pol2-no-screening"], reps, STRAT, key=("E5ref", sc_name))
        for b in biases:
            fl = simulate.noisy_flagger(0.886, 0.02, critic_bias=b, seed=seed("E5", b))
            r = cell(sc, COND["pol2"], reps, STRAT, fl, key=("E5", sc_name, b))
            rows.append({"scenario": sc_name, "critic_bias": b, "minority_win": r["minority_win"],
                         "minority_win_ci": r["minority_win_ci"], "regret": r["regret"], "regret_ci": r["regret_ci"],
                         "critical_flag_rate": r["critical_flag_rate"], "hostile_miss_rate": r["hostile_miss_rate"],
                         "no_screening_minority_win": refs[sc_name]["minority_win"],
                         "no_screening_regret": refs[sc_name]["regret"]})
        log(f"E5 {sc_name}")
    write_csv(rows, out, "e5_judge_bias.csv")
    fig, axes = new_figure(1, 2, panel=(6.4, 5.2))
    for sc_name in ("baseline", "hostile"):
        rs = [r for r in rows if r["scenario"] == sc_name]
        col = SCEN_COLOR[sc_name]
        plot_line(axes[0][0], [r["critical_flag_rate"] for r in rs], [r["minority_win"] for r in rs], color=col,
                  err=[r["minority_win_ci"] for r in rs], label=SCEN_LABEL[sc_name])
        axes[0][0].axhline(refs[sc_name]["minority_win"], color=col, alpha=0.4, lw=3, ls="--")
        plot_line(axes[0][1], biases, [r["regret"] for r in rs], color=col, err=[r["regret_ci"] for r in rs],
                  label=SCEN_LABEL[sc_name])
        axes[0][1].axhline(refs[sc_name]["regret"], color=col, alpha=0.4, lw=3, ls="--")
    axes[0][0].set_xlabel("share of the minority's critical\nmessages that get flagged")
    axes[0][0].set_ylabel(WIN)
    axes[0][0].set_ylim(0.3, 0.85)
    axes[0][1].set_xlabel("judge bias against dissent (σ)")
    axes[0][1].set_ylabel("equal-weight regret" + DOWN)
    from matplotlib.lines import Line2D

    h, l = axes[0][0].get_legend_handles_labels()
    h.append(Line2D([0], [0], color=PALETTE["black"], alpha=0.4, lw=3, ls="--"))
    l.append("no screening")
    axes[0][0].legend(h, l, loc="lower left")
    return finalize_figure(fig, fig_path(out, "e5_judge_bias"))


# ---------------------------------------------------------------------------
# E8 dynamics of voice
# ---------------------------------------------------------------------------

def e8_dynamics(out: Path, reps: int, log) -> list[Path]:
    sc = replace(HOSTILE, rounds=6, power_holders="majority")
    conds = ["ranked-20/80", "quadratic-equal", "pol2-free-talk", "pol2"]
    n = sc.n
    total = sc.rounds * n
    rows = []
    curves = {}
    fl = simulate.lexicon_flagger()
    for cname in conds:
        rng = random.Random(seed("E8", cname))
        acc = [0.0] * total
        for _ in range(reps):
            tr: list = []
            simulate.run_once(sc, COND[cname], STRAT, rng, fl, trace=tr)
            for i, m in enumerate(tr):
                acc[i] += m
        curves[cname] = [a / reps for a in acc]
        for rd in range(sc.rounds):
            rows.append({"condition": cname, "round": rd + 1,
                         "minority_share": mean(curves[cname][rd * n:(rd + 1) * n])})
        log(f"E8 {cname}")
    write_csv(rows, out, "e8_dynamics.csv")
    fig, axes = new_figure(1, 1, panel=(11, 5.0))
    ax = axes[0][0]
    half = n // 2                          # one-round moving average, full windows only (no edge artefacts)
    xs = list(range(half + 1, total - half + 1))
    for cname in conds:
        c = curves[cname]
        smooth = [mean(c[i - half:i + half + 1]) for i in range(half, total - half)]
        plot_line(ax, xs, smooth, cname, marker="")
    ax.axhline(sc.minority_frac, **REF_LINE, label="fair share (20 %)")
    ax.set_xticks([n * k + n / 2 for k in range(sc.rounds)], [str(k + 1) for k in range(sc.rounds)])
    ax.set_xlabel("deliberation round")
    ax.set_ylabel("minority share of messages" + UP)
    ax.set_ylim(0, 0.25)
    ax.set_xlim(0, total)
    ax.legend(loc="lower right", ncols=3)
    return finalize_figure(fig, fig_path(out, "e8_voice_dynamics"))
