"""PAI-autonomous decisions (PoLEn ch. 7 Art. 2) as an alternative to human voting.

Art. 2: "Autonomy means that no human voting or additional decision-making
mechanism is required"; humans keep the rights to suggest and to question.
Here the PAI collects each person's *reported* utilities, rescales every report
to [0, 1] so that each person counts once (Equal Connection), and picks the
option with the largest total. Humans can then question the result through the
same questioning period as in :mod:`pol2dao.protocol`.

The weakness this makes visible: the PAI only sees reports. If some people
exaggerate (favourite = 1, everything else = 0), the equal-weight sum is
distorted -- the same incentive problem that quadratic voting tries to price.
"""

from __future__ import annotations

import random
from typing import Sequence


def normalize(u: Sequence[float]) -> list[float]:
    lo, hi = min(u), max(u)
    if hi == lo:
        return [0.0] * len(u)
    return [(x - lo) / (hi - lo) for x in u]


def exaggerate(u: Sequence[float]) -> list[float]:
    best = max(range(len(u)), key=lambda j: u[j])
    return [1.0 if j == best else 0.0 for j in range(len(u))]


def report(u: Sequence[float], noise: float, rng: random.Random, strategic: bool = False) -> list[float]:
    """What a person tells the PAI: exaggerated if strategic, plus elicitation noise."""
    base = exaggerate(u) if strategic else list(u)
    return [x + rng.gauss(0, noise) for x in base] if noise > 0 else base


def pai_decide(reports: Sequence[Sequence[float]], method: str = "utilitarian") -> int:
    """0-based winner from reports.

    ``raw``: sum of reports as given (intensity-sensitive, fully exploitable);
    ``utilitarian``: sum of reports rescaled to [0, 1] per person (one person,
    one unit of weight); ``borda``: sum of ranks (blind to intensity).
    """
    k = len(reports[0])
    if method == "raw":
        scores = [sum(r[j] for r in reports) for j in range(k)]
    elif method == "utilitarian":
        scores = [0.0] * k
        for r in reports:
            for j, x in enumerate(normalize(r)):
                scores[j] += x
    elif method == "borda":
        scores = [0.0] * k
        for r in reports:
            order = sorted(range(k), key=lambda j: r[j])
            for rank, j in enumerate(order):
                scores[j] += rank
    else:
        raise ValueError(f"unknown method {method!r}")
    return max(range(k), key=lambda j: scores[j])
