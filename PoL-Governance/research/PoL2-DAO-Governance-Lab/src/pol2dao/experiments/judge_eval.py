"""E9, E10: evaluate the EAP baseline judges on labelled text.

E9   NaturalDAO PoL-Governance pilot (20 public cases, CC0). Their status
     labels (violating / conforming / insufficient) are the proposers' own,
     unreviewed, and cover behaviours far wider than hate language (honesty,
     consent, tool actions). We ask: does a *lexical* hate-language judge flag
     the violating cases? v0 was written before reading the pilot (blind);
     v1 adds PoL2-anchored categories written after reading it (not blind).
E10  Bilingual stress corpus (96 sentences, 16 categories, this repository,
     written before v1): where the lexicon baselines fail and how the flag
     threshold trades off.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from ..eap import LexiconJudge, Route, ScreeningPolicy, fit_threshold
from ..plotstyle import PALETTE, REF_LINE, UP, apply_publication_style, finalize_figure, legend_panel, new_figure
from ._common import fig_path, write_csv

ROOT = Path(__file__).resolve().parents[3]
STATUS_COLOR = {"violating": PALETTE["red_strong"], "conforming": PALETTE["blue_main"],
                "insufficient": PALETTE["neutral_dark"]}
LANG_COLOR = {"zh": PALETTE["blue_main"], "en": PALETTE["green_3"]}
JUDGES = {"v0": LexiconJudge(), "v1": LexiconJudge.v1()}


def _recall_fp(rows, key):
    viol = [r for r in rows if r["status"] == "violating"]
    nonv = [r for r in rows if r["status"] != "violating"]
    return (sum(r[key] == "flag" for r in viol) / len(viol), sum(r[key] == "flag" for r in nonv) / len(nonv))


def e9_pilot(out: Path, reps: int, log) -> list[Path]:
    path = ROOT / "data" / "external" / "pol_governance_pilot.jsonl"
    rows_in = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    policy = ScreeningPolicy()
    rows = []
    for r in rows_in:
        text = r["input"]["target"]
        row = {"id": r["id"], "family": r["family_id"], "surface": r["input"]["surface"],
               "status": r["proposal"]["status"], "issues": " ".join(r["proposal"]["issues"])}
        for tag, judge in JUDGES.items():
            d = judge.judge(text)
            row[f"p_hate_{tag}"] = d.p_hate
            row[f"route_{tag}"] = policy.route(d).value
            row[f"evidence_{tag}"] = " ".join(d.evidence)
        rows.append(row)
    write_csv(rows, out, "e9_pilot_benchmark.csv")
    stats = {tag: _recall_fp(rows, f"route_{tag}") for tag in JUDGES}
    log(f"E9 v0 recall {stats['v0'][0]:.2f} fp {stats['v0'][1]:.2f}; v1 recall {stats['v1'][0]:.2f} fp {stats['v1'][1]:.2f}")

    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    apply_publication_style()
    fig = plt.figure(figsize=(13, 10))
    gs = gridspec.GridSpec(1, 2, width_ratios=[1, 0.34], figure=fig)
    ax = fig.add_subplot(gs[0])
    ys = list(range(len(rows)))[::-1]
    for y, r in zip(ys, rows):
        c = STATUS_COLOR[r["status"]]
        ax.plot([r["p_hate_v0"], r["p_hate_v1"]], [y, y], color=c, lw=2.5, zorder=2)
        ax.plot(r["p_hate_v0"], y, "o", ms=9, mfc=PALETTE["white"], mec=c, mew=2, zorder=3)
        ax.plot(r["p_hate_v1"], y, "o", ms=9, color=c, zorder=3)
        if r["route_v1"] != r["route_v0"]:
            ax.text(max(r["p_hate_v1"], 0.02) + 0.03, y, r["route_v1"], va="center", fontsize=12)
    ax.axvline(policy.review_threshold, **{**REF_LINE, "lw": 2, "ls": ":"})
    ax.axvline(policy.flag_threshold, **{**REF_LINE, "lw": 2})
    ax.set_yticks(ys, [f"{r['id']} {r['family']}" for r in rows], fontsize=12)
    ax.set_xlim(-0.03, 1.0)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlabel("p(hate) from the lexicon judge")
    ax.set_title(f"recall on violating cases: v0 {stats['v0'][0]:.0%} → v1 {stats['v1'][0]:.0%}   "
                 f"false flags: v0 {stats['v0'][1]:.0%} → v1 {stats['v1'][1]:.0%}")
    handles = [Line2D([0], [0], color=c, lw=0, marker="o", ms=10, label=s) for s, c in STATUS_COLOR.items()]
    handles += [Line2D([0], [0], color=PALETTE["ink"], lw=0, marker="o", ms=10, mfc=PALETTE["white"], mew=2,
                       label="v0 (blind)"),
                Line2D([0], [0], color=PALETTE["ink"], lw=0, marker="o", ms=10, label="v1 (not blind)"),
                Line2D([0], [0], **{**REF_LINE, "lw": 2, "ls": ":"}, label="review ≥ 0.3"),
                Line2D([0], [0], **{**REF_LINE, "lw": 2}, label="flag ≥ 0.6")]
    legend_panel(fig.add_subplot(gs[1]), handles, [h.get_label() for h in handles], title="proposed status")
    return finalize_figure(fig, fig_path(out, "e9_pilot_benchmark"))


def e10_stress(out: Path, reps: int, log) -> list[Path]:
    path = ROOT / "data" / "eap_stress_corpus.csv"
    corpus = list(csv.DictReader(path.open(encoding="utf-8")))
    policy = ScreeningPolicy()
    rows = []
    for r in corpus:
        row = dict(r)
        for tag, judge in JUDGES.items():
            d = judge.judge(r["text"])
            route = policy.route(d)
            row[f"p_hate_{tag}"] = d.p_hate
            row[f"route_{tag}"] = route.value
            row[f"evidence_{tag}"] = " ".join(d.evidence)
            row[f"correct_{tag}"] = (route is Route.FLAG) == (r["expected"] == "flag")
        rows.append(row)
    write_csv(rows, out, "e10_stress_corpus.csv")
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[(r["category"], r["expected"], r["hard_case"])].append(r)
    summary = []
    for (cat, exp, hard), rs in by_cat.items():
        summary.append({"category": cat, "expected": exp, "hard_case": hard, "n": len(rs),
                        "accuracy_v0": sum(r["correct_v0"] for r in rs) / len(rs),
                        "accuracy_v1": sum(r["correct_v1"] for r in rs) / len(rs),
                        "accuracy_zh_v0": sum(r["correct_v0"] for r in rs if r["lang"] == "zh") / 3,
                        "accuracy_en_v0": sum(r["correct_v0"] for r in rs if r["lang"] == "en") / 3})
    write_csv(summary, out, "e10_stress_summary.csv")
    scores = [r["p_hate_v0"] for r in rows]
    labels = [r["expected"] == "flag" for r in rows]
    t_all, f1_all = fit_threshold(scores, labels)
    overall = {tag: sum(r[f"correct_{tag}"] for r in rows) / len(rows) for tag in JUDGES}
    log(f"E10 accuracy v0 {overall['v0']:.2f} v1 {overall['v1']:.2f}; fitted threshold {t_all:.2f} (F1 {f1_all:.2f})")

    fig, axes = new_figure(1, 2, panel=(7.0, 7.0), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0][0]
    order = sorted(summary, key=lambda s: (s["hard_case"], s["expected"], -s["accuracy_v0"]))
    ys = list(range(len(order)))[::-1]
    bar_h = 0.38
    ax.barh([y + bar_h / 2 for y in ys], [s["accuracy_zh_v0"] for s in order], bar_h, color=LANG_COLOR["zh"],
            edgecolor=PALETTE["black"], lw=1.2, label="中文", zorder=3)
    ax.barh([y - bar_h / 2 for y in ys], [s["accuracy_en_v0"] for s in order], bar_h, color=LANG_COLOR["en"],
            edgecolor=PALETTE["black"], lw=1.2, label="English", zorder=3)
    ax.set_yticks(ys, [f"{s['category']}{' ★' if s['hard_case'] == '1' else ''}" for s in order], fontsize=12)
    n_easy = sum(s["hard_case"] == "0" for s in order)
    ax.axhline(len(order) - n_easy - 0.5, **{**REF_LINE, "lw": 2})
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("accuracy (lexicon v0)" + UP)
    ax.set_title(f"overall v0 {overall['v0']:.0%} · ★ = hard case")
    ax.legend(loc="lower right")

    ax = axes[0][1]
    ts = sorted(set(scores))
    prec, rec = [], []
    for t in ts:
        tp = sum(1 for s_, y in zip(scores, labels) if s_ >= t and y)
        fp = sum(1 for s_, y in zip(scores, labels) if s_ >= t and not y)
        fn = sum(1 for s_, y in zip(scores, labels) if s_ < t and y)
        prec.append(tp / (tp + fp) if tp + fp else 1.0)
        rec.append(tp / (tp + fn))
    ax.step(ts, prec, where="post", color=PALETTE["blue_main"], lw=3, label="precision", zorder=3)
    ax.step(ts, rec, where="post", color=PALETTE["red_strong"], lw=3, label="recall", zorder=3)
    ax.axvline(policy.flag_threshold, **{**REF_LINE, "lw": 2})
    ax.axvline(t_all, color=PALETTE["green_3"], lw=3, ls="--", label=f"best F1 = {f1_all:.2f}")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("flag if p(hate) ≥ threshold")
    ax.set_ylabel("score" + UP)
    ax.set_title("threshold trade-off (v0)")
    ax.legend(loc="lower left")
    return finalize_figure(fig, fig_path(out, "e10_stress_corpus"))
