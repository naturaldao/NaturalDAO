import random
from dataclasses import replace
from statistics import NormalDist

import pytest

from pol2dao import simulate
from pol2dao.autonomy import exaggerate, normalize, pai_decide
from pol2dao.eap import LexiconJudge, Route, ScreeningPolicy
from pol2dao.simulate import CONDITIONS, Scenario

COND = {c.name: c for c in CONDITIONS}


def test_autonomy_methods():
    reports = [[0, 1, 0.9], [0, 1, 0.9], [1, 0, 0]]
    assert pai_decide(reports, "raw") == 1
    assert pai_decide(reports, "borda") == 1
    assert normalize([2, 4, 3]) == [0, 1, 0.5]
    assert exaggerate([0.2, 0.9, 0.5]) == [0, 1, 0]
    with pytest.raises(ValueError):
        pai_decide(reports, "nope")


def test_exaggeration_flips_pai_decision():
    # two mild supporters of option 1, one intense supporter of option 0
    honest = [[0.45, 0.55], [0.45, 0.55], [1.0, 0.0]]
    assert pai_decide(honest, "raw") == 0
    assert pai_decide([exaggerate(u) for u in honest], "raw") == 1


def test_noisy_flagger_matches_requested_rates():
    fl = simulate.noisy_flagger(0.9, 0.1, seed=1)
    benign = sum(fl("x", False) for _ in range(20000)) / 20000
    hostile = sum(fl("x", True) for _ in range(20000)) / 20000
    d = 2 ** 0.5 * NormalDist().inv_cdf(0.9)
    expected_hit = 1 - NormalDist().cdf(NormalDist().inv_cdf(0.9) - d)
    assert benign == pytest.approx(0.1, abs=0.01)
    assert hostile == pytest.approx(expected_hit, abs=0.01)
    with pytest.raises(ValueError):
        simulate.noisy_flagger(0.4, 0.1)


def test_critic_bias_only_hits_critical_texts():
    crit = simulate.CRITICAL_BANK[0][0]
    fl = simulate.noisy_flagger(0.9, 0.05, critic_bias=3.0, seed=2)
    assert sum(fl(crit, False) for _ in range(2000)) / 2000 > 0.5
    assert sum(fl("neutral", False) for _ in range(2000)) / 2000 < 0.1


def test_split_sybils_hurt_quadratic_not_linear():
    def win(cond, s):
        sc = replace(Scenario(), sybil_attackers=5, sybil_ids=s, sybil_mode="split")
        rng = random.Random(3)
        return sum(simulate.run_once(sc, COND[cond], "strategic", rng)["minority_win"] for _ in range(300)) / 300
    assert win("quadratic-equal", 8) < win("quadratic-equal", 1) - 0.08
    assert abs(win("ranked-equal", 8) - win("ranked-equal", 1)) < 0.08


def test_round_robin_order_is_not_by_group():
    tr = []
    simulate.run_once(Scenario(), COND["pol2"], "sincere", random.Random(5), trace=tr)
    assert sum(tr) / len(tr) == pytest.approx(0.2)
    assert tr[:5] != [True] * 5 or tr[5:10] != [False] * 5


def test_lexicon_v1_adds_pol2_categories_without_touching_criticism():
    v1, pol = LexiconJudge.v1(), ScreeningPolicy()
    assert pol.route(v1.judge("这种人天生低人一等，以后任何事情都不值得听他说。")) is Route.FLAG
    assert pol.route(v1.judge("如果你不立刻原谅我，就是你没有爱、不配当我们的同事。")) is Route.FLAG
    assert pol.route(v1.judge("我很生气，我反对这个方案。")) is Route.PASS
    assert pol.route(LexiconJudge().judge("这种人天生低人一等")) is Route.PASS


@pytest.mark.parametrize("eid", ["E9", "E10", "E11", "E12", "E13", "E0"])
def test_experiments_smoke(tmp_path, eid):
    pytest.importorskip("matplotlib")
    from pol2dao import experiments

    res = experiments.run(tmp_path, reps=4, only=[eid], log=lambda m: None)
    assert all(p.exists() for p in res[eid])
    assert {p.suffix for p in res[eid]} == {".png", ".pdf"}   # house style: raster + vector
    assert list((tmp_path / "tables").glob("*.csv"))
