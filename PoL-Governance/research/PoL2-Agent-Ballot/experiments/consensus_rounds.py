"""Experiment 2 — consensus through repeated sealed rounds.

Question. Can deliberative consensus (EAP 5.3.3, "all parties agree") be
implemented with the same sealed-ballot protocol, and what does it cost?

Setup. N = 9 DeliberativeAgents with private accuracy p = 0.7. Round 1 is a
sealed ballot; at each close all choices and rationales are disclosed; later
rounds update on the round-1 record (see agents.DeliberativeAgent). Rule:
`unanimous`, max 5 rounds. We vary the number of agents that never update
("stubborn", s = 0..4) and record: share of events that reach consensus,
accuracy of the consensus when reached, and rounds used. Every trial runs
through the full protocol and every round is audited.

Honesty clause. Scripted agents with an idealised Bayesian update; the
experiment shows that the protocol can carry a consensus procedure and how a
persistent dissenter is surfaced, not how LLM agents deliberate.

Run:  python experiments/consensus_rounds.py --trials 1000 --plot
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pol2_agent_ballot.agents import DeliberativeAgent, Proposal
from pol2_agent_ballot.consensus import run_consensus
from pol2_agent_ballot.event import Event
from pol2_agent_ballot.identity import AgentIdentity

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FIGURES = HERE / "figures"


def wilson(k: int, n: int):
    if n == 0:
        return 0.0, 0.0
    z = 1.959964
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * ((ph * (1 - ph) + z * z / (4 * n)) / n) ** 0.5 / d
    return max(0.0, c - h), min(1.0, c + h)


def trial(n: int, p: float, stubborn: int, max_rounds: int, rng: random.Random, org: AgentIdentity):
    agents = [DeliberativeAgent(AgentIdentity.generate(f"a{i}"), truth="advance", accuracy=p, rng=random.Random(rng.random()), stubborn=i < stubborn) for i in range(n)]
    rng.shuffle(agents)
    ev = Event("CONS", "consensus test")
    res = run_consensus(ev, Proposal("P", "advance?", "", ["advance", "hold"]), org, agents, rule="unanimous", max_rounds=max_rounds)
    if not all(t.audit["ok"] for t in ev.transitions):
        raise RuntimeError("audit failed")
    return res.reached, (res.reached and res.rounds[-1].winner == "advance"), res.n_rounds


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=1000)
    ap.add_argument("--n", type=int, default=9)
    ap.add_argument("--p", type=float, default=0.7)
    ap.add_argument("--max-rounds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    rng = random.Random(a.seed)
    org = AgentIdentity.generate("organiser")
    rows = []
    print(f"N={a.n}, p={a.p}, rule=unanimous, max_rounds={a.max_rounds}, trials/point={a.trials:,}")
    print(f"{'stubborn':>8}{'reached':>10}{'correct|reached':>17}{'mean rounds':>13}")
    for s in range(0, 5):
        reached = correct = 0
        rounds_hist = {}
        for _ in range(a.trials):
            r, c, k = trial(a.n, a.p, s, a.max_rounds, rng, org)
            reached += r
            correct += c
            rounds_hist[k] = rounds_hist.get(k, 0) + 1
        row = {
            "stubborn": s,
            "n": a.n,
            "p": a.p,
            "trials": a.trials,
            "reached": reached / a.trials,
            "reached_ci95": wilson(reached, a.trials),
            "correct_given_reached": correct / reached if reached else None,
            "correct_given_reached_ci95": wilson(correct, reached) if reached else None,
            "rounds_hist": {str(k): v for k, v in sorted(rounds_hist.items())},
            "mean_rounds": sum(k * v for k, v in rounds_hist.items()) / a.trials,
        }
        rows.append(row)
        cg = f"{row['correct_given_reached']:.3f}" if reached else "—"
        print(f"{s:>8}{row['reached']:>10.3f}{cg:>17}{row['mean_rounds']:>13.2f}")
    (RESULTS / "consensus.json").write_text(json.dumps(rows, indent=1))
    if a.plot:
        plot(rows, FIGURES / "consensus.png")
        print("figure:", FIGURES / "consensus.png")
    print("\nHonesty clause: scripted agents with an idealised update rule; no claim about LLM agents or humans.")


def plot(rows, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    INK, MUTED, GRID = "#1F2937", "#6B7280", "#E5E7EB"
    BLUE, GREEN = "#2E6FD6", "#2A9D6F"
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    xs = [r["stubborn"] for r in rows]

    ax = axes[0]
    ys = [r["reached"] for r in rows]
    ax.bar(xs, ys, color=BLUE, width=0.55)
    for x, y in zip(xs, ys):
        ax.text(x, y + 0.02, f"{y:.2f}", ha="center", color=INK, fontsize=10)
    ax.set_ylim(0, 1.12)
    ax.set_title(f"Share of events reaching unanimity\nN={rows[0]['n']}, p={rows[0]['p']}, ≤5 sealed rounds, {rows[0]['trials']:,} trials/bar", loc="left", fontsize=12, color=INK)
    ax.set_xlabel("agents that never update (stubborn)", color=MUTED)

    ax = axes[1]
    hist_keys = sorted({k for r in rows for k in r["rounds_hist"]}, key=int)
    bottom = [0.0] * len(rows)
    shades = ["#BFD4F5", "#7FA8EA", "#2E6FD6", "#1E4E9C", "#11305F"]
    for i, k in enumerate(hist_keys):
        vals = [r["rounds_hist"].get(k, 0) / r["trials"] for r in rows]
        ax.bar(xs, vals, bottom=bottom, color=shades[i % len(shades)], width=0.55, edgecolor="white", linewidth=1.5, label=f"{k} round{'s' if k != '1' else ''}")
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(1, 1))
    ax.set_title("Rounds used (5 = stopped without consensus)", loc="left", fontsize=12, color=INK)
    ax.set_xlabel("agents that never update (stubborn)", color=MUTED)
    for ax in axes:
        ax.set_axisbelow(True)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=MUTED)
        ax.set_xticks(xs)
    acc = [r["correct_given_reached"] for r in rows if r["correct_given_reached"] is not None]
    fig.text(0.01, 0.01, f"Accuracy of the consensus when reached: {min(acc):.3f}–{max(acc):.3f}. Scripted agents; simulation only.", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
