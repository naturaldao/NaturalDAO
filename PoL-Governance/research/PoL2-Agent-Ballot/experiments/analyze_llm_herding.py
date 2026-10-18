"""Analyse a run of experiments/llm_herding.py.

Reads one ballot log (results/llm_herding/<run>.jsonl), reconstructs what each
agent saw in the open condition, and reports:

* collective accuracy, sealed vs open, with Wilson 95% intervals and the
  paired bootstrap interval of the difference;
* the "evidence ceiling": how often the majority of the agents' private
  evidence was itself correct (an agent group that only reports its own
  evidence cannot beat this);
* the conformity curve: P(vote against own evidence) as a function of the
  visible lead against the agent's evidence when it voted, next to the
  scripted conformist of experiment 1 (follows any lead of two or more);
* every ballot that went against the agent's own evidence, with its rationale.

Writes results/llm_herding/<run>.analysis.json and figures/llm_herding.png.

    python experiments/analyze_llm_herding.py                 # latest run
    python experiments/analyze_llm_herding.py path/to/run.jsonl
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "results" / "llm_herding"
FIG = HERE / "figures"


def wilson(k: int, n: int):
    if n == 0:
        return (0.0, 0.0)
    z = 1.959964
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * ((ph * (1 - ph) + z * z / (4 * n)) / n) ** 0.5 / d
    return (max(0.0, c - h), min(1.0, c + h))


def load(path: Path):
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    meta = lines[0].get("meta", {}) if lines and "meta" in lines[0] else {}
    return meta, [r for r in lines if "proposal" in r]


def analyse(path: Path) -> dict:
    meta, rows = load(path)
    # the run's meta line is written before the first request; if the provider
    # rejected `temperature`, summary.jsonl records what was actually used
    summary = path.parent / "summary.jsonl"
    if summary.exists():
        for line in summary.read_text(encoding="utf-8").splitlines():
            row = json.loads(line) if line.strip() else {}
            if row.get("run") == path.stem:
                meta = {**meta, "temperature": row.get("temperature", meta.get("temperature"))}
    by = defaultdict(list)  # (proposal, condition) -> ballots in voting order
    for r in rows:
        by[(r["proposal"], r["condition"])].append(r)
    proposals = sorted({r["proposal"] for r in rows})
    truth = {r["proposal"]: r["truth"] for r in rows}

    def majority(votes):
        a = sum(v == "advance" for v in votes)
        h = sum(v == "hold" for v in votes)
        return "advance" if a > h else "hold" if h > a else None

    correct = {c: {} for c in ("sealed", "open")}
    for p in proposals:
        for c in ("sealed", "open"):
            correct[c][p] = int(majority([b["choice"] for b in by[(p, c)]]) == truth[p])
    ceiling = {p: int(majority([b["evidence_says"] for b in by[(p, "sealed")]]) == truth[p]) for p in proposals}

    # conformity curve, open condition: lead against own evidence before voting
    curve = defaultdict(lambda: [0, 0])  # lead -> [against, total valid ballots]
    against_list = []
    invalid_list = []
    for c in ("sealed", "open"):
        for p in proposals:
            seen = []
            for b in by[(p, c)]:
                own = b["evidence_says"]
                lead = sum(v != own for v in seen) - sum(v == own for v in seen) if c == "open" else 0
                valid = b["choice"] in ("advance", "hold")
                dev = valid and b["choice"] != own
                if not valid:
                    invalid_list.append({"proposal": p, "condition": c, "agent": b["agent"], "evidence": own, "lead_against": lead,
                                         "reason": b.get("invalid_reason")})
                elif c == "open":
                    curve[lead][0] += dev
                    curve[lead][1] += 1
                if dev:
                    against_list.append({"proposal": p, "condition": c, "agent": b["agent"], "evidence": own, "choice": b["choice"],
                                         "lead_against": lead, "truth": truth[p], "rationale": b["rationale"]})
                if valid:
                    seen.append(b["choice"])

    # could the invalid ballots have changed any collective decision?
    flippable = []
    for (p, c) in {(x["proposal"], x["condition"]) for x in invalid_list}:
        votes = [b["choice"] for b in by[(p, c)] if b["choice"] in ("advance", "hold")]
        m = len(by[(p, c)]) - len(votes)
        outcomes = {majority(votes + ["advance"] * k + ["hold"] * (m - k)) == truth[p] for k in range(m + 1)}
        if len(outcomes) > 1:
            flippable.append({"proposal": p, "condition": c})

    n = len(proposals)
    diffs = [correct["sealed"][p] - correct["open"][p] for p in proposals]
    rng = random.Random(7)
    boots = sorted(sum(rng.choice(diffs) for _ in diffs) / n for _ in range(10000)) if n else [0]
    invalid = {c: sum(b["choice"] is None or b["choice"] == "" for p in proposals for b in by[(p, c)]) for c in ("sealed", "open")}
    ballots = {c: sum(len(by[(p, c)]) for p in proposals) for c in ("sealed", "open")}
    out = {
        "run": path.stem,
        "meta": meta,
        "proposals": n,
        "accuracy": {c: {"k": sum(correct[c].values()), "n": n, "rate": sum(correct[c].values()) / n, "ci95": wilson(sum(correct[c].values()), n)} for c in correct},
        "evidence_ceiling": {"k": sum(ceiling.values()), "n": n, "rate": sum(ceiling.values()) / n},
        "diff_sealed_minus_open": {"mean": sum(diffs) / n, "ci95": [boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots)) - 1]],
                                    "discordant": {"sealed_only": sum(d == 1 for d in diffs), "open_only": sum(d == -1 for d in diffs)}},
        "against_evidence": {c: {"k": sum(1 for a in against_list if a["condition"] == c), "n": ballots[c]} for c in ("sealed", "open")},
        "invalid": invalid,
        "invalid_ballots": invalid_list,
        "invalid_could_change_a_decision": flippable,
        "conformity_curve": {str(k): {"against": v[0], "total": v[1], "rate": v[0] / v[1], "ci95": wilson(v[0], v[1])} for k, v in sorted(curve.items())},
        "ballots_against_evidence": against_list,
    }
    return out


def plot(res: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    SEALED, OPEN, INK, MUTED, GRID = "#2459C9", "#C46A12", "#121826", "#6E7890", "#E3E7EE"
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": GRID,
                         "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "axes.axisbelow": True,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": "#465166"})
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.1), gridspec_kw={"width_ratios": [1, 1.35]})
    model = res["meta"].get("model", "?")

    ax = axes[0]
    for i, (c, col, name) in enumerate((("sealed", SEALED, "Sealed"), ("open", OPEN, "Open sequential"))):
        a = res["accuracy"][c]
        ax.bar(i, a["rate"], width=0.55, color=col)
        ax.errorbar(i, a["rate"], yerr=[[max(0.0, a["rate"] - a["ci95"][0])], [max(0.0, a["ci95"][1] - a["rate"])]], color=INK, capsize=4, lw=1)
        ax.text(i, 0.04, f"{a['k']}/{a['n']}\n{a['rate']:.2f}", ha="center", va="bottom", color="white", fontsize=10, fontweight="bold")
    ce = res["evidence_ceiling"]["rate"]
    ax.axhline(ce, color=INK, lw=1.1, ls=(0, (3, 2)))
    ax.text(1.36, ce + 0.02, f"majority of private\nevidence correct: {ce:.2f}", va="bottom", fontsize=8, color=MUTED)
    ax.set_xticks([0, 1], ["Sealed", "Open sequential"])
    ax.set_xlim(-0.5, 2.05)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("collective decision correct")
    ax.set_title(f"Accuracy · {model}\n{res['proposals']} proposals × 7 agents", loc="left", fontsize=11, fontweight="bold")

    ax = axes[1]
    curve = res["conformity_curve"]
    xs = sorted(int(k) for k in curve)
    ys = [curve[str(x)]["rate"] for x in xs]
    lo = [max(0.0, curve[str(x)]["rate"] - curve[str(x)]["ci95"][0]) for x in xs]
    hi = [max(0.0, curve[str(x)]["ci95"][1] - curve[str(x)]["rate"]) for x in xs]
    step_x = [min(xs) - 0.5] + [x for x in range(min(xs), max(xs) + 1)] + [max(xs) + 0.5]
    ax.step(step_x, [1 if x >= 2 else 0 for x in step_x], where="mid", color=MUTED, lw=1.2, ls=(0, (3, 2)), label="scripted conformist (exp. 1)")
    ax.errorbar(xs, ys, yerr=[lo, hi], fmt="o", ms=6, color=OPEN, mec="white", mew=1.2, elinewidth=1, capsize=0, label=model)
    for x, y in zip(xs, ys):
        ax.text(x, -0.09, f"n={curve[str(x)]['total']}", ha="center", fontsize=7.5, color=MUTED)
    ax.set_ylim(-0.13, 1.08)
    ax.set_xticks(xs)
    ax.set_xlabel("visible lead against the agent's own evidence when it voted")
    ax.set_ylabel("P(vote against own evidence)")
    ax.set_title("Who follows the crowd? Open condition", loc="left", fontsize=11, fontweight="bold")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    d = res["diff_sealed_minus_open"]
    fig.text(0.01, -0.03, f"Sealed − open accuracy {d['mean']:+.3f} (paired bootstrap 95% CI {d['ci95'][0]:+.3f} to {d['ci95'][1]:+.3f}). "
             f"Error bars: Wilson 95%. Ballots against own evidence: sealed {res['against_evidence']['sealed']['k']}/{res['against_evidence']['sealed']['n']}, "
             f"open {res['against_evidence']['open']['k']}/{res['against_evidence']['open']['n']}; invalid sealed {res['invalid']['sealed']}, open {res['invalid']['open']} "
             f"(could change a decision: {len(res['invalid_could_change_a_decision'])}). One task family, one model.", fontsize=8, color=MUTED, ha="left", va="top", wrap=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def main() -> None:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        runs = sorted((p for p in RUNS.glob("*.jsonl") if p.name != "summary.jsonl" and p.stat().st_size > 0), key=lambda p: p.stat().st_mtime)
        if not runs:
            sys.exit("no runs in " + str(RUNS))
        path = runs[-1]
    res = analyse(path)
    (path.parent / f"{path.stem}.analysis.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    FIG.mkdir(exist_ok=True)
    plot(res, FIG / "llm_herding.png")
    a = res["accuracy"]
    print(f"run {res['run']}  model {res['meta'].get('model')}  proposals {res['proposals']}")
    print(f"sealed {a['sealed']['k']}/{a['sealed']['n']} = {a['sealed']['rate']:.3f}   open {a['open']['k']}/{a['open']['n']} = {a['open']['rate']:.3f}   "
          f"evidence ceiling {res['evidence_ceiling']['rate']:.3f}")
    d = res["diff_sealed_minus_open"]
    print(f"sealed − open {d['mean']:+.3f}  CI {d['ci95'][0]:+.3f} … {d['ci95'][1]:+.3f}  discordant {d['discordant']}")
    print("against own evidence:", res["against_evidence"], " invalid:", res["invalid"])
    print("invalid ballots at leads:", [x["lead_against"] for x in res["invalid_ballots"]], " could change a decision:", res["invalid_could_change_a_decision"] or "none")
    print("conformity curve (lead: against/total):", {k: f"{v['against']}/{v['total']}" for k, v in res["conformity_curve"].items()})
    for b in res["ballots_against_evidence"]:
        print(f"  {b['proposal']} {b['condition']} {b['agent']} evidence={b['evidence']} -> {b['choice']} (lead {b['lead_against']}, truth {b['truth']}): {b['rationale'][:140]}")
    print("figure:", FIG / "llm_herding.png")


if __name__ == "__main__":
    main()
