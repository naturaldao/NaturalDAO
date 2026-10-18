"""Experiment 1 — does sealing ballots protect agent decisions from cascades?

Setup. N conformist agents each hold a private signal that is correct with
probability p. Under the *sealed* condition no agent sees any other vote
(the IVXV property). Under the *open* condition agents vote in sequence and
see the running tally, following it once it leads by `lead` votes.

Prediction (information-cascade theory, Bikhchandani–Hirshleifer–Welch 1992):
open sequential voting lets early wrong signals lock in; sealed voting keeps
the Condorcet jury property (accuracy rises with N when p > 0.5).

Two execution paths, same decision logic:
* `--protocol` (default for the headline run): every trial goes through the
  full ballot protocol — keys, sealed envelopes, receipts, decrypt, audit.
  ~15 ms per trial; 30 000 trials ≈ 8 min.
* the parameter sweeps (`--sweep`) run the agents' decision logic alone,
  without the cryptography, because the envelope cannot change what an
  agent chooses. `tests/test_experiment.py` checks that both paths give the
  same outcome for the same seed.

Honesty clause. This is a simulation of scripted agents with a hand-set
conformity rule. It shows what the protocol *protects against*, not that
real LLM agents behave this way. Whether LLM agents herd under open voting
is an empirical question — see experiments/llm_herding_protocol.md for the
pre-registered design, which has NOT been run.

Run:  python experiments/sealed_vs_open.py --trials 30000 --sweep --plot
Outputs go to experiments/results/ (JSON) and experiments/figures/ (PNG).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pol2_agent_ballot.agents import ConformistAgent, Proposal
from pol2_agent_ballot.event import Event, run_transition_ballot
from pol2_agent_ballot.identity import AgentIdentity
from pol2_agent_ballot.theory import cascade, condorcet

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FIGURES = HERE / "figures"
CHOICES = ["advance", "hold"]


# --------------------------------------------------------------------------
# decision logic (shared by both paths)
# --------------------------------------------------------------------------
def _agents(n: int, p: float, lead: int, rng: random.Random, with_keys: bool) -> List[ConformistAgent]:
    agents = [
        ConformistAgent(
            AgentIdentity.generate(f"a{i}") if with_keys else None,  # type: ignore[arg-type]
            truth="advance",
            accuracy=p,
            lead=lead,
            rng=random.Random(rng.random()),
        )
        for i in range(n)
    ]
    rng.shuffle(agents)
    return agents


def decide_fast(agents: List[ConformistAgent], sealed: bool) -> Tuple[bool, int]:
    """Decision logic only. Returns (collective decision correct, number of
    agents that voted against their own private signal)."""
    prop = Proposal("P", "advance?", "", CHOICES)
    visible: List[Tuple[str, str]] = []
    counts = {c: 0 for c in CHOICES}
    conformed = 0
    for i, a in enumerate(agents):
        ctx = {"visible_votes": [] if sealed else list(visible)}
        choice, rationale = a.decide(prop, ctx)
        if "following the majority" in rationale:
            conformed += 1
        counts[choice] += 1
        visible.append((f"a{i}", choice))
    n = len(agents)
    correct = counts["advance"] > n / 2
    return correct, conformed


def decide_protocol(agents: List[ConformistAgent], sealed: bool, organiser: AgentIdentity) -> Tuple[bool, int]:
    """Same decision through the full ballot protocol, with audit."""
    ev = Event("EXP", "cascade test")
    prop = Proposal("P", "advance?", "", CHOICES)
    run = run_transition_ballot(ev, prop, organiser, agents, threshold_k=2, rule="majority", quorum=0.0, sealed=sealed)
    if not run.audit.ok:
        raise RuntimeError(f"audit failed: {run.audit.failures}")
    conformed = sum(1 for b in run.election.decrypted.values() if "following the majority" in b.rationale)
    return run.tally.winner == "advance", conformed


# --------------------------------------------------------------------------
# runs
# --------------------------------------------------------------------------
def run_condition(n: int, p: float, lead: int, sealed: bool, trials: int, seed: int, protocol: bool) -> Dict:
    rng = random.Random(seed)
    organiser = AgentIdentity.generate("organiser") if protocol else None
    outcomes: List[int] = []
    conformed_total = 0
    t0 = time.time()
    for _ in range(trials):
        agents = _agents(n, p, lead, rng, with_keys=protocol)
        ok, conf = decide_protocol(agents, sealed, organiser) if protocol else decide_fast(agents, sealed)
        outcomes.append(int(ok))
        conformed_total += conf
    acc = sum(outcomes) / trials
    lo, hi = bootstrap_ci(outcomes, rng)
    return {
        "condition": "sealed" if sealed else "open",
        "n": n,
        "p": p,
        "lead": lead,
        "trials": trials,
        "seed": seed,
        "protocol": protocol,
        "accuracy": acc,
        "ci95": [lo, hi],
        "conformity_rate": conformed_total / (trials * n),
        "seconds": round(time.time() - t0, 1),
    }


def bootstrap_ci(outcomes: List[int], rng: random.Random) -> Tuple[float, float]:
    """95% Wilson score interval for a Bernoulli proportion (exact enough at
    these sample sizes; cheaper and more honest than a resampling loop)."""
    n = len(outcomes)
    k = sum(outcomes)
    if n == 0:
        return 0.0, 0.0
    z = 1.959964
    ph = k / n
    denom = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / denom
    half = z * ((ph * (1 - ph) + z * z / (4 * n)) / n) ** 0.5 / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def sweep(p_fixed: float, n_values: List[int], p_values: List[float], n_fixed: int, lead: int, trials: int, seed: int) -> Dict:
    """Each point gets its own seed so that sampling errors are independent
    across points (a shared seed makes neighbouring points move together)."""
    out = {"by_n": [], "by_p": []}
    i = 0
    for n in n_values:
        for sealed in (True, False):
            i += 1
            out["by_n"].append(with_exact(run_condition(n, p_fixed, lead, sealed, trials, seed * 1000 + i, protocol=False)))
    for p in p_values:
        for sealed in (True, False):
            i += 1
            out["by_p"].append(with_exact(run_condition(n_fixed, p, lead, sealed, trials, seed * 1000 + i, protocol=False)))
    return out


def with_exact(row: Dict) -> Dict:
    """Attach the exact probability from pol2_agent_ballot.theory."""
    if row["condition"] == "sealed":
        row["exact_accuracy"] = condorcet(row["n"], row["p"])
        row["exact_conformity_rate"] = 0.0
    else:
        c = cascade(row["n"], row["p"], row["lead"])
        row["exact_accuracy"] = c["accuracy"]
        row["exact_conformity_rate"] = c["conformity_rate"]
    row["exact_inside_ci95"] = row["ci95"][0] <= row["exact_accuracy"] <= row["ci95"][1]
    return row


# --------------------------------------------------------------------------
# figures
# --------------------------------------------------------------------------
SEALED_COLOR = "#2E6FD6"  # blue
OPEN_COLOR = "#D9822B"  # orange — the pair is distinguishable under all CVD types
INK = "#1F2937"
MUTED = "#6B7280"
GRID = "#E5E7EB"


def _style(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, loc="left", fontsize=12, color=INK, pad=12)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED)


def plot_headline(headline: List[Dict], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    names = [r["condition"] for r in headline]
    colors = [SEALED_COLOR if r["condition"] == "sealed" else OPEN_COLOR for r in headline]

    ax = axes[0]
    accs = [r["accuracy"] for r in headline]
    err = [[r["accuracy"] - r["ci95"][0] for r in headline], [r["ci95"][1] - r["accuracy"] for r in headline]]
    bars = ax.bar(names, accs, color=colors, width=0.55, yerr=err, capsize=4, ecolor=INK, error_kw={"linewidth": 1})
    for b, r in zip(bars, headline):
        ax.text(b.get_x() + b.get_width() / 2, r["accuracy"] + 0.012, f"{r['accuracy']:.3f}", ha="center", color=INK, fontsize=10)
    ax.set_ylim(0, 1.0)
    r0 = headline[0]
    _style(ax, f"P(correct collective decision)\nN={r0['n']}, p={r0['p']}, lead={r0['lead']}, {r0['trials']:,} trials each", "", "")

    ax = axes[1]
    conf = [r["conformity_rate"] for r in headline]
    bars = ax.bar(names, conf, color=colors, width=0.55)
    for b, v in zip(bars, conf):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.004, f"{v:.3f}", ha="center", color=INK, fontsize=10)
    ax.set_ylim(0, max(conf) * 1.3 + 0.01)
    _style(ax, "Share of agents voting against their own private signal", "", "")

    fig.text(0.01, 0.01, "Scripted conformist agents; simulation only — no claim about LLM agents or humans. Error bars: Wilson 95% CI.", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_sweep(sw: Dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))

    def series(rows: List[Dict], key: str):
        for sealed, color in ((True, SEALED_COLOR), (False, OPEN_COLOR)):
            rs = [r for r in rows if r["condition"] == ("sealed" if sealed else "open")]
            xs = [r[key] for r in rs]
            ys = [r["accuracy"] for r in rs]
            lo = [r["ci95"][0] for r in rs]
            hi = [r["ci95"][1] for r in rs]
            yield rs[0]["condition"], color, xs, ys, lo, hi

    for ax, rows, key, xlabel, fixed in (
        (axes[0], sw["by_n"], "n", "number of agents N", f"p={sw['by_n'][0]['p']}"),
        (axes[1], sw["by_p"], "p", "private signal accuracy p", f"N={sw['by_p'][0]['n']}"),
    ):
        for name, color, xs, ys, lo, hi in series(rows, key):
            ax.fill_between(xs, lo, hi, color=color, alpha=0.15, linewidth=0)
            ax.plot(xs, ys, color=color, linewidth=2, marker="o", markersize=5)
            ax.text(xs[-1], ys[-1] + (0.015 if name == "sealed" else -0.015), f"  {name}", color=color, va="bottom" if name == "sealed" else "top", fontsize=10)
        if key == "p":
            ax.plot(xs, xs, color=GRID, linewidth=1, linestyle="--")
            ax.text(xs[-1], xs[-1], "  single agent", color=MUTED, va="center", fontsize=8)
        ax.set_ylim(0.4, 1.02)
        _style(ax, f"Collective accuracy vs {'N' if key == 'n' else 'p'}\n{fixed}, lead={rows[0]['lead']}, {rows[0]['trials']:,} trials/point", xlabel, "P(correct)")
        ax.margins(x=0.12)

    fig.text(0.01, 0.01, "Decision logic only (no cryptography); identical to the protocol path. Bands: Wilson 95% CI.", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=400)
    ap.add_argument("--n", type=int, default=9)
    ap.add_argument("--p", type=float, default=0.7)
    ap.add_argument("--lead", type=int, default=2)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--fast", action="store_true", help="headline run without cryptography")
    ap.add_argument("--sweep", action="store_true", help="also sweep N and p (fast path)")
    ap.add_argument("--sweep-trials", type=int, default=3000)
    ap.add_argument("--plot", action="store_true", help="write PNG figures")
    ap.add_argument("--reuse-headline", action="store_true", help="keep results/headline.json, rerun only sweeps/plots")
    a = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)

    if a.reuse_headline and (RESULTS / "headline.json").exists():
        headline = [with_exact(r) for r in json.loads((RESULTS / "headline.json").read_text())]
    else:
        headline = [with_exact(run_condition(a.n, a.p, a.lead, sealed, a.trials, a.seed, protocol=not a.fast)) for sealed in (True, False)]
    print(f"N={a.n} agents, private accuracy p={a.p}, conformity lead={a.lead}, trials={a.trials:,}, path={'fast' if a.fast else 'protocol'}")
    print(f"{'condition':<10}{'P(correct)':>12}{'95% CI':>20}{'conformity':>12}{'seconds':>9}")
    for r in headline:
        print(f"{r['condition']:<10}{r['accuracy']:>12.4f}{r['ci95'][0]:>10.4f}–{r['ci95'][1]:<9.4f}{r['conformity_rate']:>12.4f}{r['seconds']:>9}   exact {r['exact_accuracy']:.4f}")
    (RESULTS / "headline.json").write_text(json.dumps(headline, indent=1))

    sw = None
    if a.sweep:
        sw = sweep(a.p, [3, 5, 7, 9, 13, 17, 21, 25], [0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9], a.n, a.lead, a.sweep_trials, a.seed)
        (RESULTS / "sweep.json").write_text(json.dumps(sw, indent=1))
        pts = sw["by_n"] + sw["by_p"]
        print(f"exact value inside the 95% CI at {sum(r['exact_inside_ci95'] for r in pts)} of {len(pts)} sweep points")
        print("\nsweep written to", RESULTS / "sweep.json")

    if a.plot:
        plot_headline(headline, FIGURES / "headline.png")
        print("figure:", FIGURES / "headline.png")
        if sw:
            plot_sweep(sw, FIGURES / "sweep.png")
            print("figure:", FIGURES / "sweep.png")

    print("\nHonesty clause: scripted agents, hand-set conformity rule; no claim about real LLM agents or humans.")


if __name__ == "__main__":
    main()
