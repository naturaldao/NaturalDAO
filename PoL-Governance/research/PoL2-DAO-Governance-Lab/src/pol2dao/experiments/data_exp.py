"""E11-E13: the published DAO data, the decision chain, and the literature map.

E11  published overview   token shares in all 8 round x condition cells, the
                          equal-budget counterfactual, and budget concentration
E12  decision chain       verification cost and tamper localisation
E13  literature map       PoL2-Jev survey papers per governance axis, and which
                          module of this repository answers to each axis
"""

from __future__ import annotations

import csv
import json
import time
from collections import Counter
from pathlib import Path

from ..ledger import DecisionChain, Entry
from ..metrics import gini, nakamoto
from ..plotstyle import (DOWN, PALETTE, REF_LINE, annotate_bars, bar, cond_handles, finalize_figure,
                         new_figure, plot_line)
from ..replay import from_published
from ..voting import budgets
from ._common import fig_path, write_csv

ROOT = Path(__file__).resolve().parents[3]
FILE_TO_COND = {"quadratic-equal": "quadratic-equal", "quadratic-early": "quadratic-20/80",
                "ranked-equal": "ranked-equal", "ranked-early": "ranked-20/80"}


def e11_published(out: Path, reps: int, log) -> list[Path]:
    tok = list(csv.DictReader((ROOT / "data" / "sharma2026_token_totals.csv").open(encoding="utf-8")))
    mea = {(r["round"], r["cond"]): r for r in
           csv.DictReader((ROOT / "data" / "sharma2026_table1_means.csv").open(encoding="utf-8"))}
    cf = {(str(r["round"]), r["cond"]): r for r in from_published()}
    rows = []
    for r in tok:
        key = (r["round"], r["cond"])
        t = [float(r[f"tokens_{i}"]) for i in range(1, 5)]
        m = [float(mea[key][f"mean_r{i}"]) for i in range(1, 5)]
        n = int(r["n"])
        bud = budgets(n, "20/80" if "early" in key[1] else "equal", holders=range(round(0.2 * n)))
        rows.append({"round": key[0], "cond": key[1], "n": n,
                     **{f"actual_share_{i + 1}": t[i] / sum(t) for i in range(4)},
                     **{f"equal_share_{i + 1}": m[i] / sum(m) for i in range(4)},
                     "actual_winner_by_tokens": max(range(4), key=lambda j: t[j]) + 1,
                     "actual_winner_by_rule": int(r["winner_by_rule"]),
                     "equal_budget_winner_linear": cf[key]["equal_budget_winner"] or "",
                     "budget_gini": gini(bud), "budget_nakamoto": nakamoto(bud)})
    write_csv(rows, out, "e11_published_overview.csv")
    log("E11 done")
    order = ["quadratic-equal", "quadratic-early", "ranked-equal", "ranked-early"]
    fig, axes = new_figure(2, 4, panel=(4.6, 4.2), sharey=True)
    for i, rnd in enumerate(("1", "2")):
        for j, cond in enumerate(order):
            ax = axes[i][j]
            r = next(x for x in rows if x["round"] == rnd and x["cond"] == cond)
            a = [r[f"actual_share_{k + 1}"] for k in range(4)]
            e = [r[f"equal_share_{k + 1}"] for k in range(4)]
            ax.set_ylim(0, 0.6)
            name = FILE_TO_COND[cond]
            if "early" in cond:
                ba = bar(ax, [x - 0.2 for x in range(4)], a, name=name, width=0.4)
                be = bar(ax, [x + 0.2 for x in range(4)], e, color=PALETTE["blue_main"], hatch="", width=0.4)
                we = max(range(4), key=lambda k: e[k])
                annotate_bars(ax, [be[we]], ["win" if cond.startswith("ranked") else "win?"], fmt="{}", fontsize=12)
            else:
                ba = bar(ax, list(range(4)), a, name=name, width=0.6)
            wa = r["actual_winner_by_rule"] - 1          # quadratic cells are decided by sqrt(tokens)
            annotate_bars(ax, [ba[wa]], ["win"], fmt="{}", fontsize=12)
            ax.set_xticks(range(4), ["1", "2", "3", "4"])
            ax.set_title(f"round {rnd} · {name} · n={r['n']}", fontsize=14)
            if j == 0:
                ax.set_ylabel("share of tokens")
            if i == 1:
                ax.set_xlabel("option")
    handles = cond_handles([FILE_TO_COND[c] for c in order], "bar")
    from matplotlib.patches import Patch

    handles.append(Patch(facecolor=PALETTE["blue_main"], edgecolor=PALETTE["black"], lw=1.5,
                         label="equal budgets, same split"))
    fig.legend(handles=handles, loc="upper center", ncols=5, bbox_to_anchor=(0.5, 1.0), fontsize=13)
    fig.tight_layout(pad=2, rect=(0, 0, 1, 0.93))
    return finalize_figure(fig, fig_path(out, "e11_published_overview"), tight=False)


def e12_ledger(out: Path, reps: int, log) -> list[Path]:
    sizes = [10, 100, 1_000, 10_000]
    rows = []
    for n in sizes:
        chain = DecisionChain()
        t0 = time.perf_counter()
        for i in range(n):
            chain.append("ballot", {"voter": f"p{i}", "tokens": [i % 7, 3, 0, 1], "budget": 100})
        t_append = time.perf_counter() - t0
        t0 = time.perf_counter()
        ok, _ = chain.verify()
        t_verify = time.perf_counter() - t0
        path = chain.to_jsonl(out / "tables" / "_tmp_chain.jsonl")
        size = path.stat().st_size
        path.unlink()
        rows.append({"entries": n, "append_ms": t_append * 1e3, "verify_ms": t_verify * 1e3,
                     "bytes_per_entry": size / n, "intact": ok})
        log(f"E12 n={n} verify {t_verify * 1e3:.1f} ms")
    chain = DecisionChain()
    for i in range(200):
        chain.append("message", {"speaker": f"p{i % 5}", "text": f"msg {i}"})
    detected = []
    for i in range(0, 200, 10):
        entries = [json.loads(json.dumps(e.to_dict())) for e in chain]
        entries[i]["payload"]["text"] = "edited"
        c2 = DecisionChain()
        c2._entries = [Entry(**e) for e in entries]
        ok, bad = c2.verify()
        detected.append({"edited_index": i, "detected_at": bad, "intact": ok})
    write_csv(rows, out, "e12_ledger_performance.csv")
    write_csv(detected, out, "e12_ledger_tamper.csv")
    fig, axes = new_figure(1, 2, panel=(5.8, 5.0))
    plot_line(axes[0][0], sizes, [r["verify_ms"] for r in rows], color=PALETTE["blue_main"], label="verify")
    plot_line(axes[0][0], sizes, [r["append_ms"] for r in rows], color=PALETTE["neutral_dark"], marker="s",
              label="append")
    axes[0][0].set_xscale("log")
    axes[0][0].set_yscale("log")
    axes[0][0].set_xlabel("entries")
    axes[0][0].set_ylabel("time (ms)" + DOWN)
    axes[0][0].set_title(f"≈{rows[-1]['bytes_per_entry']:.0f} bytes per entry")
    axes[0][0].legend(loc="upper left")
    axes[0][1].plot([0, 200], [0, 200], **{**REF_LINE, "lw": 2})
    axes[0][1].plot([d["edited_index"] for d in detected], [d["detected_at"] for d in detected], "o", ms=9,
                    color=PALETTE["blue_main"], zorder=3)
    axes[0][1].set_xlabel("index of the edited entry")
    axes[0][1].set_ylabel("index reported by verify()")
    axes[0][1].set_title("tampering is localised exactly")
    return finalize_figure(fig, fig_path(out, "e12_decision_chain"))


AXIS_TO_MODULE = {
    "G1": "eap.py (judge)", "G2": "eap.py + protocol (escalate)", "G3": "eap.py (criticism ≠ hate)",
    "G4": "eap.py (absence, fit_threshold)", "G5": "ledger.py + protocol (decision record)",
    "G6": "protocol.py (question / explain / escalate)", "G7": "simulate.py + autonomy.py",
}
TIER_COLOR = {"核心": PALETTE["blue_main"], "相关": PALETTE["green_3"], "背景": PALETTE["neutral"]}


def e13_literature(out: Path, reps: int, log) -> list[Path]:
    papers = list(csv.DictReader((ROOT / "data" / "external" / "pol2_survey_papers.csv").open(encoding="utf-8")))
    axes_def = json.loads((ROOT / "data" / "external" / "pol2_axes.json").open(encoding="utf-8").read())["axes"]
    tiers = list(TIER_COLOR)
    counts = {a: Counter() for a in axes_def}
    for pr in papers:
        for a in pr["pol_axes"].split():
            if a in counts:
                counts[a][pr["tier"]] += 1
    rows = [{"axis": a, "name_zh": axes_def[a]["name_zh"], **{t: counts[a][t] for t in tiers},
             "total": sum(counts[a].values()), "module_here": AXIS_TO_MODULE[a],
             "pol2_refs": "; ".join(axes_def[a]["pol2_refs"])} for a in axes_def]
    write_csv(rows, out, "e13_literature_map.csv")
    log("E13 done")
    fig, axes = new_figure(1, 1, panel=(12, 5.6))
    ax = axes[0][0]
    ys = list(range(len(rows)))[::-1]
    left = [0] * len(rows)
    for t in tiers:
        vals = [r[t] for r in rows]
        if not any(vals):
            continue
        ax.barh(ys, vals, 0.62, left=left, color=TIER_COLOR[t], edgecolor=PALETTE["black"], lw=1.5, label=t,
                zorder=3)
        left = [l + v for l, v in zip(left, vals)]
    for y, r, tot in zip(ys, rows, left):
        ax.text(tot + 0.15, y, r["module_here"], va="center", fontsize=12, color=PALETTE["ink_soft"])
    ax.set_yticks(ys, [f"{r['axis']} {r['name_zh']}" for r in rows])
    ax.set_xlim(0, 11)
    ax.set_xlabel("papers (a paper can sit on several axes)")
    ax.legend(title="tier", loc="lower right")
    return finalize_figure(fig, fig_path(out, "e13_literature_map"))
