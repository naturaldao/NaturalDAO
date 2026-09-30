"""Token ballots, aggregation rules and power schemes.

The design follows the DAO experiment of Sharma et al. (2026, Sci. Rep. 16,
11792): each participant spreads a token budget over the options.

* ``linear`` ("ranked"/weighted in the article): an option's score is the sum
  of tokens placed on it.
* ``quadratic``: t tokens on an option buy sqrt(t) votes.
* ``plurality``: one vote for each ballot's top option (a reference rule).

Power schemes: ``equal`` gives everyone 100 tokens; ``20/80`` gives 20 % of the
participants 400 tokens and the rest 25, so 20 % hold 80 % of the tokens (the
article's "early" condition; see dao-governance-replication/data/README.md).

PoL2's Equal Connection (PoLEn 5.3.1, "equal access to resources") corresponds
to the ``equal`` scheme; :func:`equalize` rescales any ballot to an equal
budget while keeping how the voter split it -- the counterfactual used by
:mod:`pol2dao.replay`.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Literal, Sequence

Rule = Literal["linear", "quadratic", "plurality"]
PowerScheme = Literal["equal", "20/80"]

RULES: tuple[Rule, ...] = ("linear", "quadratic", "plurality")
EQUAL_BUDGET = 100
HIGH_BUDGET, LOW_BUDGET = 400, 25


@dataclass(frozen=True)
class Ballot:
    voter: str
    tokens: tuple[float, ...]
    budget: float

    def __post_init__(self) -> None:
        if any(t < 0 for t in self.tokens):
            raise ValueError(f"negative tokens on ballot of {self.voter}")
        if self.budget <= 0:
            raise ValueError("budget must be positive")

    @property
    def shares(self) -> tuple[float, ...]:
        """Tokens as a share of the *budget* (unspent tokens stay unspent)."""
        return tuple(t / self.budget for t in self.tokens)


def votes(ballot: Ballot, rule: Rule) -> tuple[float, ...]:
    """Effective votes a single ballot contributes to each option."""
    if rule == "linear":
        return tuple(float(t) for t in ballot.tokens)
    if rule == "quadratic":
        return tuple(math.sqrt(t) for t in ballot.tokens)
    if rule == "plurality":
        top = max(ballot.tokens)
        if top <= 0:
            return tuple(0.0 for _ in ballot.tokens)
        winners = [i for i, t in enumerate(ballot.tokens) if t == top]
        return tuple(1.0 / len(winners) if i in winners else 0.0 for i in range(len(ballot.tokens)))
    raise ValueError(f"unknown rule {rule!r}")


@dataclass(frozen=True)
class Tally:
    rule: Rule
    scores: tuple[float, ...]
    per_voter: dict[str, float]  # total effective votes cast by each voter

    @property
    def shares(self) -> tuple[float, ...]:
        z = sum(self.scores)
        return tuple(s / z if z else 0.0 for s in self.scores)

    @property
    def leaders(self) -> list[int]:
        top = max(self.scores)
        return [i for i, s in enumerate(self.scores) if abs(s - top) <= 1e-9 * max(1.0, top)]

    @property
    def winner(self) -> int:
        """0-based index of the winning option; ties go to the lowest index."""
        return self.leaders[0]

    @property
    def tied(self) -> bool:
        return len(self.leaders) > 1

    def to_dict(self) -> dict:
        return {"rule": self.rule, "scores": [round(s, 6) for s in self.scores],
                "shares": [round(s, 6) for s in self.shares],
                "winner": self.winner, "tied": self.tied}


def tally(ballots: Sequence[Ballot], rule: Rule) -> Tally:
    if not ballots:
        raise ValueError("no ballots")
    k = len(ballots[0].tokens)
    if any(len(b.tokens) != k for b in ballots):
        raise ValueError("ballots have different numbers of options")
    scores = [0.0] * k
    per_voter: dict[str, float] = {}
    for b in ballots:
        v = votes(b, rule)
        for i, x in enumerate(v):
            scores[i] += x
        per_voter[b.voter] = per_voter.get(b.voter, 0.0) + sum(v)
    return Tally(rule=rule, scores=tuple(scores), per_voter=per_voter)


def budgets(n: int, scheme: PowerScheme, rng: random.Random | None = None,
            holders: Sequence[int] | None = None) -> list[float]:
    """Token budgets for ``n`` voters.

    For ``20/80``, ``round(0.2 * n)`` voters get 400 tokens. They are
    ``holders`` if given (indices), otherwise drawn with ``rng``.
    """
    if scheme == "equal":
        return [float(EQUAL_BUDGET)] * n
    if scheme == "20/80":
        k = max(1, round(0.2 * n))
        if holders is None:
            holders = (rng or random.Random(0)).sample(range(n), k)
        chosen = set(holders)
        return [float(HIGH_BUDGET if i in chosen else LOW_BUDGET) for i in range(n)]
    raise ValueError(f"unknown power scheme {scheme!r}")


def equalize(ballot: Ballot, budget: float = EQUAL_BUDGET) -> Ballot:
    """Same split of the budget, but everyone's budget is ``budget``."""
    return Ballot(ballot.voter, tuple(s * budget for s in ballot.shares), budget)


def allocate(weights: Sequence[float], budget: float) -> tuple[int, ...]:
    """Integer token allocation proportional to ``weights`` (largest remainder)."""
    w = [max(x, 0.0) for x in weights]
    z = sum(w)
    if z <= 0:
        w, z = [1.0] * len(w), float(len(w))
    exact = [budget * x / z for x in w]
    base = [math.floor(e) for e in exact]
    rest = int(round(budget)) - sum(base)
    order = sorted(range(len(w)), key=lambda i: exact[i] - base[i], reverse=True)
    for i in order[:rest]:
        base[i] += 1
    return tuple(base)
