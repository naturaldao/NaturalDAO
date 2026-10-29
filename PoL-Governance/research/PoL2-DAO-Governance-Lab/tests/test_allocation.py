"""E14 (needs reporting) and E15 (correlated reviewers): invariants and closed-form checks."""

import random

import pytest

from pol2dao.experiments import allocation_exp as a


def test_water_fill_conserves_supply_and_caps():
    rep = [1.0, 2.0, 3.0, 10.0]
    x = a.water_fill(rep, 8.0)
    assert sum(x) == pytest.approx(8.0)
    assert all(xi <= ri + 1e-12 for xi, ri in zip(x, rep))
    assert x == pytest.approx([1.0, 2.0, 2.5, 2.5])


def test_water_fill_serves_everyone_when_supply_suffices():
    assert a.water_fill([1.0, 2.0], 10.0) == [1.0, 2.0]


def test_proportional_rule_shifts_harm_to_honest_agents():
    honest = {f: a.needs_cell(f, 2.0, 0.5, 60) for f in (0.0, 0.4)}
    # R1: honest agents lose a lot as inflation spreads, yet no supply is "wasted"
    assert honest[0.4]["R1"]["honest_fill"] < honest[0.0]["R1"]["honest_fill"] - 0.1
    assert honest[0.4]["R1"]["efficiency"] > 0.99
    # R2: honest agents are nearly unaffected, the cost shows up as lower efficiency
    assert honest[0.4]["R2"]["honest_fill"] > honest[0.0]["R2"]["honest_fill"] - 0.06
    assert honest[0.4]["R2"]["efficiency"] < 0.97
    # R3: auditing helps on both metrics
    assert honest[0.4]["R3"]["efficiency"] > honest[0.4]["R2"]["efficiency"]


def test_no_inflation_means_no_gap_between_r2_and_r3():
    c = a.needs_cell(0.0, 2.0, 0.5, 20)
    assert c["R2"]["honest_fill"] == pytest.approx(c["R3"]["honest_fill"])


def test_single_reviewer_is_independent_of_correlation():
    assert a.fa_mean(1, 0.0) == pytest.approx(a.fa_mean(1, 0.9))
    assert a.fa_any(1, 0.0) == pytest.approx(a.fa_mean(1, 0.0), abs=2e-3)
    assert a.fa_mean(1, 0.0) == pytest.approx(0.2363, abs=1e-3)


def test_more_reviewers_help_less_when_errors_are_correlated():
    for fn in (a.fa_mean, a.fa_any):
        gain = {rho: fn(1, rho) - fn(7, rho) for rho in (0.0, 0.5, 0.9)}
        assert gain[0.0] > gain[0.5] > gain[0.9] > 0
    assert a.fa_mean(7, 0.9) > 0.85 * a.fa_mean(1, 0.9)      # seven clones ~ one reviewer


def test_any_veto_is_not_safer_than_mean_at_equal_false_rejection():
    assert a.fa_any(5, 0.5) > a.fa_mean(5, 0.5)


def test_escalation_frontier_is_monotone_and_respects_false_rejection():
    f = a.escalation_frontier([0.0, 0.1, 0.2, 0.3])
    assert [x["fa"] for x in f] == sorted((x["fa"] for x in f), reverse=True)
    assert all(x["benign_rejected"] <= a.FR_TARGET + 1e-9 for x in f)
    assert all(x["escalated"] <= x["escalation_budget"] + 1e-9 for x in f)
    # 20 % escalation to an independent reviewer ~ seven same-base reviewers at rho = 0.5
    assert f[2]["fa"] == pytest.approx(a.fa_mean(7, 0.5), abs=0.01)


def test_needs_once_is_seeded_reproducible():
    r1 = a.needs_once(random.Random(3), 0.3, 2.0, 0.5)
    r2 = a.needs_once(random.Random(3), 0.3, 2.0, 0.5)
    assert r1 == r2


def test_nonmarket_allocator_respects_claim_caps_and_supply():
    needs = [2, 2, 2, 2]
    claims = [2, 2, 2, 2]
    tiers = [0, 0, 1, 2]
    pointers = [0, 0, 0]
    alloc, _ = a._allocate_e16(needs, claims, tiers, 3, True, pointers)
    assert sum(alloc) == 3
    assert all(x <= c for x, c in zip(alloc, claims))
    assert alloc[0] + alloc[1] == 3  # critical tier is served before lower tiers


def test_equal_priority_rotation_does_not_depend_on_need_tier():
    needs = [3, 3, 3]
    claims = [3, 3, 3]
    tiers = [0, 1, 2]
    pointers = [0, 0, 0]
    alloc, _ = a._allocate_e16(needs, claims, tiers, 3, False, pointers)
    assert alloc == [1, 1, 1]


def test_basic_floor_then_priority_gives_one_before_extra_units():
    needs = [4, 4, 4]
    claims = [4, 4, 4]
    tiers = [0, 1, 2]
    alloc, _ = a._allocate_e16(needs, claims, tiers, 5, True, [0, 0, 0], basic_floor=True)
    assert all(x >= 1 for x in alloc)
    assert alloc[0] > alloc[1] >= alloc[2]


def test_basic_floor_defers_to_urgent_needs_when_supply_cannot_cover_everyone():
    needs = [3, 3, 3, 3]
    claims = [3, 3, 3, 3]
    tiers = [0, 0, 1, 2]
    alloc, _ = a._allocate_e16(needs, claims, tiers, 2, True, [0, 0, 0], basic_floor=True)
    assert alloc[:2] == [1, 1]
    assert sum(alloc) == 2


def test_e16_seeded_reproducible_and_bounded():
    r1 = a.needs_priority_simulation(random.Random(19), 0.3, reps=3, n=30, rounds=8)
    r2 = a.needs_priority_simulation(random.Random(19), 0.3, reps=3, n=30, rounds=8)
    assert r1 == r2
    assert all(0 <= v <= 1 for rule in r1.values() for v in rule.values())
