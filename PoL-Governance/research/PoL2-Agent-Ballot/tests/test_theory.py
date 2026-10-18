"""Exact results in theory.py against brute force and against the simulator."""
import itertools
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from pol2_agent_ballot.theory import cascade, condorcet, consensus


def _enumerate(n, p):
    for signals in itertools.product([1, 0], repeat=n):  # 1 = correct signal
        w = 1.0
        for s in signals:
            w *= p if s else 1 - p
        yield signals, w


@pytest.mark.parametrize("n,p", [(3, 0.7), (5, 0.6), (7, 0.8), (6, 0.7)])
def test_condorcet_matches_enumeration(n, p):
    brute = sum(w for s, w in _enumerate(n, p) if 2 * sum(s) > n)
    assert condorcet(n, p) == pytest.approx(brute, abs=1e-12)


@pytest.mark.parametrize("n,p,lead", [(5, 0.7, 2), (7, 0.65, 2), (6, 0.8, 3)])
def test_cascade_matches_enumeration(n, p, lead):
    acc = conf = 0.0
    for sig, w in _enumerate(n, p):
        d, c = 0, 0
        for s in sig:
            vote = 1 if d >= lead else 0 if d <= -lead else s
            c += vote != s
            d += 1 if vote else -1
        acc += w * (d > 0)
        conf += w * c / n
    r = cascade(n, p, lead)
    assert r["accuracy"] == pytest.approx(acc, abs=1e-12)
    assert r["conformity_rate"] == pytest.approx(conf, abs=1e-12)


def test_condorcet_increases_with_n_and_cascade_plateaus():
    assert condorcet(25, 0.7) > condorcet(9, 0.7) > condorcet(3, 0.7)
    assert abs(cascade(25, 0.7)["accuracy"] - cascade(13, 0.7)["accuracy"]) < 0.002


def test_simulator_agrees_with_theory():
    from sealed_vs_open import run_condition

    for sealed in (True, False):
        r = run_condition(9, 0.7, 2, sealed, 4000, seed=11, protocol=False)
        exact = condorcet(9, 0.7) if sealed else cascade(9, 0.7, 2)["accuracy"]
        assert abs(r["accuracy"] - exact) < 4 * (exact * (1 - exact) / 4000) ** 0.5


def test_consensus_no_stubborn_equals_condorcet():
    r = consensus(9, 0.7, 0)
    assert r["reached"] == pytest.approx(1.0)
    assert r["correct_given_reached"] == pytest.approx(condorcet(9, 0.7))
