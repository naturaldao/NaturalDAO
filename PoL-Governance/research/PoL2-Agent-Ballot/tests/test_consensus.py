import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pol2_agent_ballot.agents import DeliberativeAgent, Proposal
from pol2_agent_ballot.consensus import run_consensus
from pol2_agent_ballot.event import Event
from pol2_agent_ballot.identity import AgentIdentity


def _agents(signals, stubborn=()):
    out = []
    for i, s in enumerate(signals):
        a = DeliberativeAgent(AgentIdentity.generate(f"a{i}"), truth=s, accuracy=1.0, rng=random.Random(i), stubborn=i in stubborn)
        out.append(a)
    return out


def test_consensus_reached_in_round_two_with_full_record():
    org = AgentIdentity.generate("org")
    ev = Event("C1", "t")
    res = run_consensus(ev, Proposal("P", "t", "", ["advance", "hold"]), org, _agents(["advance"] * 4 + ["hold"] * 1))
    assert res.reached and res.n_rounds == 2
    assert res.rounds[0].counts == {"advance": 4, "hold": 1}
    assert res.rounds[1].counts == {"advance": 5, "hold": 0}
    assert res.rounds[1].changed_minds == ["a4"]
    assert ev.stage == "deliberation"
    assert len(ev.transitions) == 2 and not ev.transitions[0].advanced and ev.transitions[1].advanced
    assert all(t.audit["ok"] for t in ev.transitions)


def test_unanimous_first_round():
    org = AgentIdentity.generate("org")
    ev = Event("C2", "t")
    res = run_consensus(ev, Proposal("P", "t", "", ["advance", "hold"]), org, _agents(["advance"] * 3))
    assert res.reached and res.n_rounds == 1


def test_stubborn_dissent_blocks_and_event_stays():
    org = AgentIdentity.generate("org")
    ev = Event("C3", "t")
    res = run_consensus(ev, Proposal("P", "t", "", ["advance", "hold"]), org, _agents(["advance"] * 4 + ["hold"], stubborn={4}), max_rounds=3)
    assert not res.reached and res.n_rounds == 3
    assert ev.stage == "proposed"
