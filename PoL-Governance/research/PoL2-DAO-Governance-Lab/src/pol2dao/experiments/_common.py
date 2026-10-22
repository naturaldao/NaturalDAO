"""Shared helpers for the experiment modules: simulation cells, CSV output.

All plotting style (colours, fonts, export) lives in :mod:`pol2dao.plotstyle`.
"""

from __future__ import annotations

import csv
import random
import zlib
from pathlib import Path
from statistics import mean
from typing import Sequence

from .. import simulate
from ..simulate import Condition, Scenario, _ci

COND = {c.name: c for c in simulate.CONDITIONS}
HOSTILE = Scenario("hostile", hate_rate=0.3)
BASELINE = Scenario("baseline")
_LEX = simulate.lexicon_flagger()


def seed(*parts: object) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


def cell(sc: Scenario, cond: Condition, reps: int, behavior: str = "strategic",
         flagger=None, key: Sequence[object] = ()) -> dict:
    """Mean and 95 % CI half-width (``<metric>_ci``) of every metric over ``reps`` pods.

    ``key`` seeds the RNG; reuse the same key across conditions for common random numbers.
    """
    rng = random.Random(seed(*key) if key else seed(sc, behavior))
    flagger = flagger or _LEX
    runs = [simulate.run_once(sc, cond, behavior, rng, flagger) for _ in range(reps)]
    out: dict = {}
    for k in runs[0]:
        xs = [r[k] for r in runs]
        out[k] = mean(xs)
        out[f"{k}_ci"] = _ci(xs)
    for num, den, name in (("hostile_missed", "hostile_msgs", "hostile_miss_rate"),
                           ("benign_flagged", "benign_msgs", "benign_flag_rate"),
                           ("critical_flagged", "critical_msgs", "critical_flag_rate")):
        d = sum(r[den] for r in runs)
        out[name] = sum(r[num] for r in runs) / d if d else float("nan")
    return out


def write_csv(rows: list[dict], out: Path, name: str) -> Path:
    path = out / "tables" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})
    return path


def fig_path(out: Path, stem: str) -> Path:
    return out / "figures" / stem


def frange(a: float, b: float, n: int) -> list[float]:
    return [a + (b - a) * i / (n - 1) for i in range(n)]
