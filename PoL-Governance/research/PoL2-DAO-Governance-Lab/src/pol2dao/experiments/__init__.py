"""Experiment registry: ``pol2dao experiments [--only E1,E4] [--reps N]``."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from . import allocation_exp, autonomy_exp, data_exp, judge_eval, mechanisms, screening

Experiment = Callable[[Path, int, Callable[[str], None]], list[Path]]

REGISTRY: dict[str, tuple[str, Experiment, float]] = {
    # id: (title, function, reps multiplier relative to --reps)
    "E0": ("mechanism decomposition", mechanisms.e0_decomposition, 1.0),
    "E1": ("sensitivity heatmaps", mechanisms.e1_sensitivity, 0.4),
    "E2": ("preference intensity", mechanisms.e2_intensity, 1.0),
    "E3": ("pod size and minority share", mechanisms.e3_scale, 0.6),
    "E4": ("judge operating point", screening.e4_operating_point, 0.6),
    "E5": ("judge bias against dissent", screening.e5_judge_bias, 1.0),
    "E6": ("sybil attack", mechanisms.e6_sybil, 0.6),
    "E7": ("PAI autonomy vs voting", autonomy_exp.e7_autonomy, 1.0),
    "E8": ("voice dynamics", screening.e8_dynamics, 0.6),
    "E9": ("NaturalDAO pilot benchmark", judge_eval.e9_pilot, 1.0),
    "E10": ("bilingual stress corpus", judge_eval.e10_stress, 1.0),
    "E11": ("published data overview", data_exp.e11_published, 1.0),
    "E12": ("decision chain cost", data_exp.e12_ledger, 1.0),
    "E13": ("literature map", data_exp.e13_literature, 1.0),
    "E14": ("needs reporting (ch. 6)", allocation_exp.e14_needs_report, 0.4),
    "E15": ("correlated reviewers and escalation", allocation_exp.e15_reviewer_correlation, 1.0),
}


def run(out: Path, reps: int = 1000, only: list[str] | None = None,
        log: Callable[[str], None] = print) -> dict[str, list[Path]]:
    ids = only or list(REGISTRY)
    results = {}
    for eid in ids:
        title, fn, mult = REGISTRY[eid]
        log(f"== {eid} {title}")
        results[eid] = fn(out, max(2, int(reps * mult)), log)
    return results
