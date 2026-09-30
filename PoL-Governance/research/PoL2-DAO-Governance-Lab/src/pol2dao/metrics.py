"""Equality and influence metrics used across the lab."""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence


def gini(values: Iterable[float]) -> float:
    """Gini coefficient of non-negative values (0 = perfectly equal)."""
    xs = sorted(float(v) for v in values)
    if any(x < 0 for x in xs):
        raise ValueError("gini needs non-negative values")
    n, total = len(xs), sum(xs)
    if n == 0 or total == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * cum) / (n * total) - (n + 1) / n


def nakamoto(influence: Mapping[str, float] | Sequence[float], threshold: float = 0.5) -> int:
    """Smallest number of participants whose combined influence exceeds ``threshold``."""
    vals = sorted(influence.values() if isinstance(influence, Mapping) else influence, reverse=True)
    total = sum(vals)
    if total <= 0:
        return 0
    acc = 0.0
    for k, v in enumerate(vals, start=1):
        acc += v
        if acc / total > threshold:
            return k
    return len(vals)


def normalized_regret(utilities: Sequence[Sequence[float]], chosen: int) -> float:
    """Equal-weight welfare loss of ``chosen``: 0 = best option, 1 = worst.

    ``utilities[i][j]`` is person i's utility for option j. Everyone counts
    once, whatever their token budget -- the Equal Connection yardstick.
    """
    k = len(utilities[0])
    totals = [sum(u[j] for u in utilities) for j in range(k)]
    best, worst = max(totals), min(totals)
    if best == worst:
        return 0.0
    return (best - totals[chosen]) / (best - worst)
