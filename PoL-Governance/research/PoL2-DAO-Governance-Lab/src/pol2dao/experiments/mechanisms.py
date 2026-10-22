"""E0-E3, E6: which mechanism does what, and when.

E0  decomposition   ranked-20/80 -> pol2, one mechanism at a time
E1  sensitivity     intimidation x hate rate, persuasion x hate rate (heatmaps)
E2  intensity       how strong must the minority's preference be for each rule?
E3  scale           pod size and minority share
E6  sybil           fake identities under linear vs quadratic voting
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ..plotstyle import (DIV_CMAP, DOWN, PALETTE, REF_LINE, SEQ_CMAP, UP, annotate_bars, bar, finalize_figure,
                         heatmap, new_figure, plot_line)
from ..simulate import Condition
from ._common import BASELINE, COND, HOSTILE, cell, fig_path, frange, write_csv

STRAT = "strategic"
WIN = "P(minority's option wins)" + UP


# ---------------------------------------------------------------------------
# E0 decomposition
# ---------------------------------------------------------------------------

STEPS = [
    ("ranked\n20/80\nfree talk", Condition("s0", "linear", "20/80")),
    ("+ equal\npower", Condition("s1", "linear", "equal")),
    ("+ quadratic\nvoting", Condition("s2", "quadratic", "equal")),
    ("+ turn-\ntaking", Condition("s3", "quadratic", "equal", "round_robin")),
    ("+ EAP\nscreening", Condition("s4", "quadratic", "equal", "round_robin", True)),
]


def e0_decomposition(out: Path, reps: int, log) -> list[Path]:
    rows = []
    for sc_name, sc in (("baseline", replace(BASELINE, power_holders="majority")),
                        ("hostile", replace(HOSTILE, power_holders="majority"))):
        for label, cond in STEPS:
            c = cell(sc, cond, reps, STRAT, key=("E0", sc_name))
            rows.append({"scenario": sc_name, "step": label.replace("\n", " "),
                         "minority_win": c["minority_win"], "minority_win_ci": c["minority_win_ci"],
                         "regret": c["regret"], "minority_voice_share": c["minority_voice_share"]})
    write_csv(rows, out, "e0_decomposition.csv")
    log("E0 done")
    fig, axes = new_figure(1, 2, panel=(7.6, 5.6), sharey=True)
    for ax, sc_name in zip(axes[0], ("baseline", "hostile")):
        rs = [r for r in rows if r["scenario"] == sc_name]
        vals = [r["minority_win"] for r in rs]
        ax.set_ylim(0, 1.0)
        prev = 0.0
        for i, v in enumerate(vals):
            if i == 0:
                b = bar(ax, [i], [v], name="ranked-20/80", width=0.62)
                annotate_bars(ax, b, [v])
            else:
                d = v - prev
                bar(ax, [i], [d], color=PALETTE["green_3"] if d >= 0 else PALETTE["red_2"], hatch="",
                    width=0.62, bottom=prev)
                ax.plot([i - 1 + 0.31, i - 0.31], [prev, prev], color=PALETTE["black"], lw=1.2, zorder=2)
                ax.text(i, max(v, prev) + 0.02, f"{d:+.2f}", ha="center", va="bottom")
            prev = v
        k = len(vals)
        ax.plot([k - 1 + 0.31, k - 0.31], [prev, prev], color=PALETTE["black"], lw=1.2, zorder=2)
        b = bar(ax, [k], [prev], name="pol2", width=0.62, err=[rs[-1]["minority_win_ci"]])
        ax.text(k, prev + rs[-1]["minority_win_ci"] + 0.02, f"{prev:.2f}", ha="center", va="bottom")
        ax.set_xticks(range(k + 1), [s[0] for s in STEPS] + ["pol2\ntotal"], fontsize=12)
        ax.set_title("no hostility" if sc_name == "baseline" else "hostile talk (30 % of majority messages)")
    axes[0][0].set_ylabel(WIN)
    return finalize_figure(fig, fig_path(out, "e0_mechanism_decomposition"))


# ---------------------------------------------------------------------------
# E1 sensitivity heatmaps
# ---------------------------------------------------------------------------

def e1_sensitivity(out: Path, reps: int, log) -> list[Path]:
    hate = frange(0, 0.6, 7)
    intim = frange(0, 1, 6)
    pers = frange(0, 0.6, 6)
    rows = []
    grids = {}
    for name, param, values in (("intimidation", "intimidation", intim), ("persuasion", "persuasion", pers)):
        g = {c: [[0.0] * len(hate) for _ in values] for c in ("quadratic-equal", "pol2")}
        for i, v in enumerate(values):
            for j, h in enumerate(hate):
                sc = replace(BASELINE, hate_rate=h, **{param: v}, power_holders="majority")
                for cname in g:
                    r = cell(sc, COND[cname], reps, STRAT, key=("E1", name, i, j))
                    g[cname][i][j] = r["minority_win"]
                    rows.append({"param": param, "value": v, "hate_rate": h, "condition": cname,
                                 "minority_win": r["minority_win"], "minority_win_ci": r["minority_win_ci"],
                                 "regret": r["regret"]})
            log(f"E1 {name} row {i + 1}/{len(values)}")
        grids[name] = (values, g)
    write_csv(rows, out, "e1_sensitivity.csv")
    fig, axes = new_figure(2, 3, panel=(6.4, 5.2))
    hl = [f"{h:.1f}" for h in hate]
    for r_, name in enumerate(("intimidation", "persuasion")):
        values, g = grids[name]
        vl = [f"{v:.1f}" for v in values]
        diff = [[g["pol2"][i][j] - g["quadratic-equal"][i][j] for j in range(len(hate))] for i in range(len(values))]
        heatmap(axes[r_][0], g["quadratic-equal"], hl, vl, SEQ_CMAP, 0, 1, fontsize=10, cbar_label=WIN)
        heatmap(axes[r_][1], g["pol2"], hl, vl, SEQ_CMAP, 0, 1, fontsize=10, cbar_label=WIN)
        heatmap(axes[r_][2], diff, hl, vl, DIV_CMAP, -0.9, 0.9, fmt="{:+.2f}", fontsize=10,
                cbar_label="pol2 − quadratic-equal")
        axes[r_][0].set_ylabel(name)
        for c_ in range(3):
            axes[r_][c_].set_xlabel("hate rate")
    for c_, t in enumerate(("quadratic-equal (Sharma et al.)", "pol2", "difference")):
        axes[0][c_].set_title(t)
    return finalize_figure(fig, fig_path(out, "e1_sensitivity_heatmaps"))


# ---------------------------------------------------------------------------
# E2 preference intensity
# ---------------------------------------------------------------------------

def e2_intensity(out: Path, reps: int, log) -> list[Path]:
    """Scale the minority's intensity: minority_u = (0, 0, s, 0.2 s), s in [0.3, 1]."""
    scales = frange(0.3, 1.0, 8)
    conds = ["ranked-equal", "quadratic-equal", "pol2"]
    rows = []
    for s in scales:
        sc = replace(HOSTILE, minority_u=(0.0, 0.0, s, 0.2 * s), power_holders="majority")
        for cname in conds:
            for beh in ("sincere", "strategic"):
                r = cell(sc, COND[cname], reps, beh, key=("E2", s, beh))
                rows.append({"intensity": s, "condition": cname, "behavior": beh,
                             "minority_win": r["minority_win"], "minority_win_ci": r["minority_win_ci"],
                             "optimum_hit": r["optimum_hit"], "optimum_is_minority_fav": r["optimum_is_minority_fav"],
                             "regret": r["regret"], "regret_ci": r["regret_ci"]})
        log(f"E2 intensity {s:.2f}")
    write_csv(rows, out, "e2_intensity.csv")
    fig, axes = new_figure(1, 3, panel=(5.6, 5.0))
    opt = [r["optimum_is_minority_fav"] for r in rows if r["condition"] == conds[0] and r["behavior"] == STRAT]
    first = next((s for s, o in zip(scales, opt) if o > 0.5), None)
    for ax, (beh, metric, title, lab) in zip(axes[0], (
            ("strategic", "minority_win", "strategic voters", WIN),
            ("strategic", "regret", "strategic voters", "equal-weight regret" + DOWN),
            ("sincere", "minority_win", "sincere voters", WIN))):
        for cname in conds:
            rs = [r for r in rows if r["condition"] == cname and r["behavior"] == beh]
            plot_line(ax, scales, [r[metric] for r in rs], cname, err=[r[f"{metric}_ci"] for r in rs])
        if first is not None:
            ax.axvline(first, **REF_LINE)
        ax.set_title(title)
        ax.set_xlabel("minority intensity s")
        ax.set_ylabel(lab)
        if metric != "regret":
            ax.set_ylim(0, 1)
    axes[0][0].legend(loc="upper left")
    return finalize_figure(fig, fig_path(out, "e2_preference_intensity"))


# ---------------------------------------------------------------------------
# E3 scale
# ---------------------------------------------------------------------------

def e3_scale(out: Path, reps: int, log) -> list[Path]:
    sizes = [10, 15, 25, 40, 60, 100]
    fracs = [0.1, 0.2, 0.3, 0.4]
    conds = ["ranked-20/80", "quadratic-equal", "pol2"]
    keep = ("minority_win", "minority_win_ci", "regret", "minority_voice_share", "nakamoto", "nakamoto_ci",
            "influence_gini")
    rows = []
    for n in sizes:
        for cname in conds:
            r = cell(replace(HOSTILE, n=n, power_holders="majority"), COND[cname], reps, STRAT, key=("E3n", n))
            rows.append({"sweep": "n", "value": n, "condition": cname, **{k: r[k] for k in keep}})
        log(f"E3 n={n}")
    for f in fracs:
        for cname in conds:
            r = cell(replace(HOSTILE, minority_frac=f, power_holders="majority"), COND[cname], reps, STRAT,
                     key=("E3f", f))
            rows.append({"sweep": "minority_frac", "value": f, "condition": cname, **{k: r[k] for k in keep}})
    write_csv(rows, out, "e3_scale.csv")
    fig, axes = new_figure(1, 3, panel=(5.6, 5.0))
    for cname in conds:
        rn = [r for r in rows if r["sweep"] == "n" and r["condition"] == cname]
        plot_line(axes[0][0], sizes, [r["minority_win"] for r in rn], cname, err=[r["minority_win_ci"] for r in rn])
        plot_line(axes[0][1], sizes, [r["nakamoto"] / n for r, n in zip(rn, sizes)], cname,
                  err=[r["nakamoto_ci"] / n for r, n in zip(rn, sizes)])
        rf = [r for r in rows if r["sweep"] == "minority_frac" and r["condition"] == cname]
        plot_line(axes[0][2], fracs, [r["minority_win"] for r in rf], cname, err=[r["minority_win_ci"] for r in rf])
    for ax in axes[0][:2]:
        ax.set_xscale("log")
        ax.set_xticks(sizes, [str(s) for s in sizes])
        ax.minorticks_off()
        ax.set_xlabel("pod size n")
    axes[0][0].set_ylabel(WIN)
    axes[0][0].set_ylim(0, 1)
    axes[0][1].set_ylabel("Nakamoto coefficient / n" + UP)
    axes[0][1].set_ylim(0, 0.55)
    axes[0][2].set_ylabel(WIN)
    axes[0][2].set_ylim(0, 1.02)
    axes[0][2].set_xlabel("minority share (n = 25)")
    axes[0][0].legend(loc="center right")
    return finalize_figure(fig, fig_path(out, "e3_scale"))


# ---------------------------------------------------------------------------
# E6 sybil attack
# ---------------------------------------------------------------------------

def e6_sybil(out: Path, reps: int, log) -> list[Path]:
    ids = [1, 2, 3, 5, 8]
    attackers = [1, 3, 5]
    rows = []
    for mode in ("split", "fresh"):
        for a in attackers:
            for s in ids:
                sc = replace(BASELINE, sybil_attackers=a, sybil_ids=s, sybil_mode=mode)
                for cname in ("ranked-equal", "quadratic-equal"):
                    r = cell(sc, COND[cname], reps, STRAT, key=("E6", mode, a, s))
                    rows.append({"mode": mode, "attackers": a, "ids_per_attacker": s, "condition": cname,
                                 "minority_win": r["minority_win"], "minority_win_ci": r["minority_win_ci"],
                                 "majority_win": r["majority_win"], "influence_gini": r["influence_gini"],
                                 "nakamoto": r["nakamoto"]})
            log(f"E6 {mode} attackers={a}")
    write_csv(rows, out, "e6_sybil.csv")
    fig, axes = new_figure(1, 2, panel=(6.4, 5.2), sharey=True)
    for ax, mode in zip(axes[0], ("split", "fresh")):
        for cname in ("quadratic-equal", "ranked-equal"):
            for a, ls, alpha in ((1, ":", 0.55), (5, "-", 1.0)):
                rs = [r for r in rows if r["mode"] == mode and r["attackers"] == a and r["condition"] == cname]
                err = [r["minority_win_ci"] for r in rs] if a == 5 else None   # one band per colour
                plot_line(ax, ids, [r["minority_win"] for r in rs], cname, ls=ls, err=err,
                          label=f"{cname}, {a} attacker{'s' if a > 1 else ''}", alpha=alpha)
        ax.set_xticks(ids, [str(i) for i in ids])
        ax.set_xlabel("identities per attacker")
        ax.set_ylim(0, 0.85)
        ax.set_title({"split": "one budget split over the identities",
                      "fresh": "a full budget for every identity"}[mode])
    axes[0][0].set_ylabel(WIN)
    axes[0][0].legend(loc="lower left", fontsize=12)
    return finalize_figure(fig, fig_path(out, "e6_sybil_attack"))
