import json

import pytest

from pol2dao.deliberation import Deliberation, TurnError
from pol2dao.demo import run_demo
from pol2dao.ledger import DecisionChain
from pol2dao.protocol import GovernanceConfig, GovernanceSession, Proposal

PROP = Proposal("T-1", "test", ("keep", "change"))


def test_round_robin_enforced():
    d = Deliberation(["a", "b"], "round_robin")
    d.post("a", "hi")
    with pytest.raises(TurnError):
        d.post("a", "again")
    d.pass_turn("b")
    d.post("a", "ok")


def test_flagged_speaker_keeps_turns():
    s = GovernanceSession(PROP, ["a", "b"])
    m = s.say("a", "you idiot")
    assert m.route.value == "flag" and m.repair
    s.say("b", "我反对")
    s.say("a", "sorry")  # still a's turn: rights are unchanged


def test_unanswered_question_escalates():
    s = GovernanceSession(PROP, ["a", "b"])
    s.open_vote()
    s.cast("a", (100, 0))
    s.cast("b", (0, 64))
    s.close_vote()
    s.question("b", "why?")
    d = s.finalize()
    assert d.status == "escalated" and "question" in d.reasons[0]


def test_flagged_winning_option_escalates():
    prop = Proposal("T-2", "test", ("kick them out", "include everyone"))
    s = GovernanceSession(prop, ["a", "b"])
    s.open_vote()
    s.cast("a", (100, 0))
    s.cast("b", (100, 0))
    s.close_vote()
    assert s.finalize().status == "escalated"


def test_budget_enforced_and_stages():
    s = GovernanceSession(PROP, ["a", "b"], GovernanceConfig.sharma("linear", "20/80"),
                          power_holders=["a"])
    assert s.budgets == {"a": 400, "b": 25}
    with pytest.raises(RuntimeError):
        s.cast("a", (1, 1))  # vote not open
    s.open_vote()
    with pytest.raises(ValueError):
        s.cast("b", (20, 20))


def test_demo_chain_verifies_and_detects_tampering(tmp_path):
    decision, chain, path = run_demo(tmp_path / "chain.jsonl")
    assert decision.status == "decided" and decision.winner == 2
    assert chain.verify() == (True, None)
    loaded = DecisionChain.from_jsonl(path)
    assert loaded.verify() == (True, None) and loaded.head == chain.head

    lines = path.read_text(encoding="utf-8").splitlines()
    e = json.loads(lines[3])
    e["payload"]["text"] = "edited"
    lines[3] = json.dumps(e, ensure_ascii=False)
    path.write_text("\n".join(lines), encoding="utf-8")
    assert DecisionChain.from_jsonl(path).verify() == (False, 3)


def test_demo_is_reproducible(tmp_path):
    # Regression: an empty DecisionChain is falsy, so the injected clock was once ignored.
    _, a, _ = run_demo(tmp_path / "a.jsonl")
    _, b, _ = run_demo(tmp_path / "b.jsonl")
    assert a.head == b.head
