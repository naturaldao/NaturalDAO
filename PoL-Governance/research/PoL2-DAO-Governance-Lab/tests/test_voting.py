import math

import pytest

from pol2dao.metrics import gini, nakamoto, normalized_regret
from pol2dao.voting import Ballot, allocate, budgets, equalize, tally


def test_quadratic_uses_sqrt():
    t = tally([Ballot("a", (100, 0), 100), Ballot("b", (0, 25), 100), Ballot("c", (0, 25), 100)],
              "quadratic")
    assert t.scores == (10.0, 10.0) and t.tied


def test_linear_and_plurality():
    bs = [Ballot("a", (60, 40), 100), Ballot("b", (0, 100), 100)]
    assert tally(bs, "linear").winner == 1
    assert tally(bs, "plurality").scores == (1.0, 1.0)


def test_twenty_eighty_budgets():
    b = budgets(25, "20/80", holders=range(5))
    assert b.count(400) == 5 and b.count(25) == 20
    assert sum(b[:5]) / sum(b) == pytest.approx(0.8)


def test_equalize_keeps_split():
    e = equalize(Ballot("a", (200, 100, 0, 0), 400))
    assert e.budget == 100 and e.tokens == (50, 25, 0, 0)


def test_equal_power_can_flip_outcome():
    # One rich voter against three poorer ones.
    bs = [Ballot("rich", (400, 0), 400)] + [Ballot(f"p{i}", (0, 25), 25) for i in range(3)]
    assert tally(bs, "linear").winner == 0
    assert tally([equalize(b) for b in bs], "linear").winner == 1


def test_allocate_is_exact():
    a = allocate([0.2, 0.3, 0.5], 7)
    assert sum(a) == 7 and all(x >= 0 for x in a)


def test_metrics():
    assert gini([1, 1, 1]) == 0
    assert gini([0, 0, 1]) == pytest.approx(2 / 3)
    assert nakamoto({"a": 80, "b": 10, "c": 10}) == 1
    assert nakamoto([1, 1, 1, 1]) == 3
    assert normalized_regret([[0, 1], [0, 1]], 1) == 0
    assert normalized_regret([[0, 1], [0, 1]], 0) == 1


def test_ballot_validation():
    with pytest.raises(ValueError):
        Ballot("a", (-1, 0), 100)
    assert not math.isnan(tally([Ballot("a", (0, 0), 100)], "plurality").scores[0])
