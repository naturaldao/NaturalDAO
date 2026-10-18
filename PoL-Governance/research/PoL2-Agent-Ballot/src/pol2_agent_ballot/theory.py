"""Closed-form and exact dynamic-programming results for the experiments.

The Monte Carlo experiments in ``experiments/`` run scripted agents through
the full cryptographic protocol. Because those agents follow fixed decision
rules, the probabilities they estimate can also be computed exactly. This
module does that, so every simulated number in the README has a theoretical
counterpart it can be checked against (``tests/test_theory.py``).

Notation: ``n`` agents, each holding an independent private signal that
points to the correct choice with probability ``p``.
"""
from __future__ import annotations

from functools import lru_cache
from math import comb
from typing import Dict


def condorcet(n: int, p: float) -> float:
    """P(strict majority of n independent votes is correct).

    Condorcet (1785) jury theorem: for p > 1/2 this increases in n and tends
    to 1. Ties (even n) count as no decision, matching ``tally.py``.
    """
    return sum(comb(n, k) * p**k * (1 - p) ** (n - k) for k in range(n // 2 + 1, n + 1))


def cascade(n: int, p: float, lead: int = 2) -> Dict[str, float]:
    """Exact outcome of open sequential voting with conformist agents.

    Agent i sees the running tally d = (#advance - #hold). If |d| >= lead it
    votes with the leader regardless of its own signal; otherwise it votes its
    signal. This is the rule of ``agents.ConformistAgent`` and the
    deterministic version of the cascade in Bikhchandani, Hirshleifer & Welch
    (1992), where lead = 2 is exactly the point at which a Bayesian agent's
    posterior is overturned by public history.

    Returns P(correct decision) and the expected share of agents voting
    against their own signal ("conformity rate").
    """

    @lru_cache(maxsize=None)
    def go(i: int, d: int) -> tuple:
        # returns (P(final majority correct), expected number of conforming votes)
        if i == n:
            return (1.0 if d > 0 else 0.0, 0.0)
        if d >= lead:  # everyone remaining follows "advance"
            pc, ec = go(i + 1, d + 1)
            return (pc, ec + (1 - p))  # conforms when its signal said hold
        if d <= -lead:
            pc, ec = go(i + 1, d - 1)
            return (pc, ec + p)  # conforms when its signal said advance
        a, b = go(i + 1, d + 1), go(i + 1, d - 1)
        return (p * a[0] + (1 - p) * b[0], p * a[1] + (1 - p) * b[1])

    pc, ec = go(0, 0)
    return {"accuracy": pc, "conformity_rate": ec / n}


def consensus(n: int, p: float, stubborn: int, max_rounds: int = 5) -> Dict[str, float]:
    """Exact outcome of ``consensus.run_consensus`` with DeliberativeAgents.

    Round 1 ballots equal the private signals. From round 2 on, every
    non-stubborn agent votes the round-1 majority (keeping its own signal on
    a tie) and stubborn agents keep their signal, so the ballots no longer
    change after round 2. Unanimity is therefore reached in round 1 (all
    signals agree), in round 2 (all stubborn agents' signals agree with the
    round-1 majority), or never.
    """
    s, m = stubborn, n - stubborn
    reached = correct = r1 = 0.0
    for j in range(s + 1):  # stubborn agents with the correct signal
        pj = comb(s, j) * p**j * (1 - p) ** (s - j)
        for k in range(m + 1):  # other agents with the correct signal
            pk = comb(m, k) * p**k * (1 - p) ** (m - k)
            w, c = pj * pk, j + k
            if c in (0, n):  # all signals agree: unanimous in round 1
                reached += w
                r1 += w
                correct += w if c == n else 0.0
                continue
            if 2 * c == n:  # tie in round 1: nobody updates, no unanimity
                continue
            maj_correct = 2 * c > n
            if (maj_correct and j == s) or (not maj_correct and j == 0):
                reached += w
                correct += w if maj_correct else 0.0
    r2 = reached - r1
    mean_rounds = 1 * r1 + 2 * r2 + max_rounds * (1 - reached)
    return {
        "reached": reached,
        "correct_given_reached": correct / reached if reached else float("nan"),
        "mean_rounds": mean_rounds,
    }
