import csv
import random

from pol2dao import replay, simulate
from pol2dao.cli import main


def test_run_once_fields():
    r = simulate.run_once(simulate.Scenario(), simulate.CONDITIONS[0], "sincere", random.Random(1))
    assert 0 <= r["regret"] <= 1 and r["winner"] in range(4)


def test_round_robin_keeps_minority_voice_under_hostility():
    sc = simulate.Scenario("hostile", hate_rate=0.5, intimidation=0.9)
    rows = simulate.run_grid(reps=40, scenarios=[sc], behaviors=["sincere"], holders=["random"],
                             conditions=[simulate.CONDITIONS[0], simulate.CONDITIONS[4]])
    free, pol2 = rows
    assert pol2["minority_voice_share"] == 0.2
    assert free["minority_voice_share"] < pol2["minority_voice_share"]


def test_grid_is_deterministic():
    kw = dict(reps=5, behaviors=["sincere"], holders=["random"])
    assert str(simulate.run_grid(**kw)) == str(simulate.run_grid(**kw))  # str: NaN != NaN


def test_published_counterfactual():
    rows = {(r["round"], r["cond"]): r for r in replay.from_published()}
    r = rows[(1, "ranked-early")]
    assert (r["actual_winner"], r["equal_budget_winner"], r["flipped"]) == (2, 3, True)
    assert rows[(2, "ranked-early")]["flipped"] is False
    assert rows[(1, "quadratic-early")]["note"].startswith("needs")


def _fake_osf(d):
    with (d / "anonymous_round1_vote.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["user", "pod", "pod-categorical", "votes_given",
                    "choice_1", "choice_2", "choice_3", "choice_4"])
        w.writerow([1, 0, "ranked-early", 400, 400, 0, 0, 0])
        for i in range(3):
            w.writerow([i + 2, 0, "ranked-early", 25, 0, 25, 0, 0])
        w.writerow([9, 1, "quadratic-equal", 100, 50, 50, 0, 0])
    with (d / "anonymous_round3_vote.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pod", "phase", "votes_given", "choice_1", "choice_2", "choice_3", "choice_4"])
        w.writerow(["ranked-equal", "pilots", 100, 10, 90, 0, 0])
        w.writerow(["ranked-equal", "round-3", 100, 0, 0, 100, 0])


def test_replay_osf_format(tmp_path):
    _fake_osf(tmp_path)
    rows = replay.replay_osf(replay.read_osf_votes(tmp_path), boot=50)
    r = next(x for x in rows if x["cond"] == "ranked-early")
    assert (r["actual_winner"], r["equal_budget_winner"], r["flipped"]) == (1, 2, True)
    no_pilots = replay.replay_osf(replay.read_osf_votes(tmp_path), boot=10, include_pilots=False)
    assert next(x for x in no_pilots if x["round"] == 2)["n"] == 1


def test_cli_smoke(tmp_path):
    _fake_osf(tmp_path)
    out = tmp_path / "out"
    assert main(["demo", "--out", str(out)]) == 0
    assert main(["verify", str(out / "demo_decision_chain.jsonl")]) == 0
    assert main(["simulate", "--reps", "3", "--out", str(out), "--no-figures"]) == 0
    assert main(["published", "--out", str(out), "--no-figures"]) == 0
    assert main(["replay", "--data-dir", str(tmp_path), "--boot", "5", "--out", str(out)]) == 0
