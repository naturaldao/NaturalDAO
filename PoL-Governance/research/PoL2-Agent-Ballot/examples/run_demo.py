"""End-to-end demo: five agents decide whether a welfare proposal advances
from `deliberation` to `voting`, one agent re-votes, a human files a 质询,
and the auditor re-checks everything from the exported record.

Run:  python examples/run_demo.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pol2_agent_ballot.agents import Proposal, ScriptedAgent
from pol2_agent_ballot.eap import KeywordEAP
from pol2_agent_ballot.event import Event, run_transition_ballot
from pol2_agent_ballot.identity import AgentIdentity


def main() -> None:
    rng = random.Random(7)
    organiser = AgentIdentity.generate("organiser", role="NaturalDAO election organiser")
    agents = [
        ScriptedAgent(AgentIdentity.generate(f"agent-{i}", model="scripted"), truth="advance", accuracy=0.75, rng=random.Random(rng.random()))
        for i in range(5)
    ]
    custodians = [organiser, agents[0].identity, agents[1].identity]

    event = Event("WELFARE-042", "Community kitchen pilot in district 3")
    event.stage_index = 1  # start at 'deliberation'
    proposal = Proposal(
        "P-042-1",
        "Move the kitchen pilot to a formal vote",
        "Deliberation has produced a costed plan, a site, and a staffing roster. "
        "Two residents' suggestions were incorporated; one open question about opening hours remains.",
        choices=["advance", "hold"],
        evidence={"plan_cost": "within envelope", "residents_consulted": "14", "open_questions": "1"},
    )

    def revote(agent, proposal, ctx):
        # agent-3 receives late evidence and changes its mind: IVXV re-voting.
        if agent.identity.name == "agent-3":
            return "advance", "late evidence resolved the opening-hours question; replacing my earlier ballot"
        return None

    run = run_transition_ballot(
        event,
        proposal,
        organiser,
        agents,
        custodians=custodians,
        threshold_k=2,
        rule="majority",
        quorum=0.6,
        eap=KeywordEAP(blocklist=["humiliat", "punish"]),
        revote_hook=revote,
    )

    qid = event.add_query("resident-Li", "Why was the opening-hours question not resolved before voting?")
    event.answer_query(qid, "It was resolved during the voting period; agent-3 re-voted after the evidence arrived — see election log seq of its second ballot.", by="organiser")

    print(f"Event {event.event_id}: now at stage {event.stage!r}")
    print(f"Tally: {run.tally.counts}  decided={run.tally.decided} winner={run.tally.winner}")
    print(f"Reason: {run.tally.reason}")
    print(f"Envelopes accepted: {len(run.ballots_cast)} (one re-vote)")
    print("Audit:", "PASS" if run.audit.ok else "FAIL")
    for c in run.audit.checks:
        print("  ✓", c)
    for f in run.audit.failures:
        print("  ✗", f)
    # individual verification by agent-3 for its final ballot
    last_env = [e for n, e in run.ballots_cast if n == "agent-3"][-1]
    print("agent-3 individual verification:", run.election.individual_verify(agents[3].identity.agent_id, last_env.envelope_hash))

    out = Path(__file__).resolve().parent / "demo_output.json"
    out.write_text(json.dumps(event.to_dict(), indent=1, ensure_ascii=False))
    print(f"Full decision chain written to {out}")


if __name__ == "__main__":
    main()
