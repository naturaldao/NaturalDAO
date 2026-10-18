"""Events, stages, and the ballot that moves an event forward.

A PoL2 *event* (a welfare proposal, a task on the PoL-Governance board, a
deployment) moves through stages. Each transition is decided by a sealed
ballot among the agents responsible for it. The `EventLedger` records every
transition together with the election log that justified it, so the full
decision chain (第五条 5) is reconstructible.

Human roles follow chapter 7: humans do not vote here (第二条 1), but they
may attach a 建议 (suggestion) or 质询 (query) to any transition, and the
agents owe a published explanation (第九条 2). `Event.add_query()` and
`Event.answer_query()` implement that bookkeeping.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .agents import Agent, Proposal
from .ballot import Ballot, Envelope
from .crypto import KeyShare
from .eap import AlwaysPassEAP, EAPChecker, EAPVerdict
from .election import Election, ElectionConfig
from .identity import AgentIdentity, AgentRegistry, build_registry
from .tally import TallyResult, tally
from .verify import AuditReport, Auditor

DEFAULT_STAGES = ["proposed", "deliberation", "voting", "approved", "executed", "reviewed"]


@dataclass
class Transition:
    from_stage: str
    to_stage: str
    election_id: str
    tally: dict
    advanced: bool
    eap_proposal: dict
    eap_rationales: Dict[str, dict]
    audit: dict
    log: List[dict]
    envelopes: List[dict]
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class Event:
    event_id: str
    title: str
    stages: List[str] = field(default_factory=lambda: list(DEFAULT_STAGES))
    stage_index: int = 0
    transitions: List[Transition] = field(default_factory=list)
    queries: List[dict] = field(default_factory=list)

    @property
    def stage(self) -> str:
        return self.stages[self.stage_index]

    @property
    def next_stage(self) -> Optional[str]:
        return self.stages[self.stage_index + 1] if self.stage_index + 1 < len(self.stages) else None

    def add_query(self, who: str, text: str, kind: str = "质询") -> int:
        self.queries.append({"id": len(self.queries), "who": who, "kind": kind, "text": text, "ts": time.time(), "answer": None})
        return len(self.queries) - 1

    def answer_query(self, qid: int, answer: str, by: str) -> None:
        self.queries[qid]["answer"] = {"by": by, "text": answer, "ts": time.time()}

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "stages": self.stages,
            "stage": self.stage,
            "transitions": [t.to_dict() for t in self.transitions],
            "queries": self.queries,
        }


@dataclass
class BallotRun:
    """Everything one transition ballot produced."""

    election: Election
    tally: TallyResult
    audit: AuditReport
    eap_proposal: EAPVerdict
    eap_rationales: Dict[str, EAPVerdict]
    ballots_cast: List[Tuple[str, Envelope]]


def run_transition_ballot(
    event: Event,
    proposal: Proposal,
    organiser: AgentIdentity,
    agents: Sequence[Agent],
    *,
    custodians: Optional[Sequence[AgentIdentity]] = None,
    threshold_k: int = 2,
    rule: str = "majority",
    quorum: float = 0.5,
    eap: Optional[EAPChecker] = None,
    sealed: bool = True,
    revote_hook: Optional[Callable[[Agent, Proposal, dict], Optional[Tuple[str, str]]]] = None,
    extra_context: Optional[dict] = None,
) -> BallotRun:
    """Run one sealed ballot deciding whether `event` advances a stage.

    sealed=True  : agents never see each other's votes (IVXV default).
    sealed=False : agents vote in sequence and see the running tally — the
                   *open* condition used by experiments/sealed_vs_open.py.
                   The envelopes are still sealed cryptographically; what
                   changes is only what the agent is told before deciding.
    revote_hook  : optional second pass; if it returns a (choice, rationale)
                   the agent casts a replacement ballot (IVXV re-voting).
    """
    eap = eap or AlwaysPassEAP()
    if event.next_stage is None:
        raise ValueError("event is at its final stage")
    custodians = list(custodians) if custodians else [organiser] + [a.identity for a in agents[:2]]
    n = len(custodians)
    if threshold_k > n:
        raise ValueError("threshold_k exceeds number of custodians")

    # EAP gate on the proposal (第六条 3)
    eap_proposal = eap.check(proposal.title + "\n" + proposal.body)

    cfg = ElectionConfig(
        election_id=f"{event.event_id}:{event.stage}->{event.next_stage}:{len(event.transitions)}",
        question=f"Advance event {event.event_id!r} from {event.stage!r} to {event.next_stage!r}?",
        choices=list(proposal.choices),
        subject={"event_id": event.event_id, "from": event.stage, "to": event.next_stage, "proposal_id": proposal.proposal_id},
        threshold_k=threshold_k,
        threshold_n=n,
        rule=rule,
        quorum=quorum,
    )
    registry = build_registry(organiser, [a.identity for a in agents])
    election = Election(cfg, registry, organiser)
    shares = election.generate_keys()
    election.open()

    cast: List[Tuple[str, Envelope]] = []
    visible: List[Tuple[str, str]] = []
    if not eap_proposal.passed:
        # Proposal is not eligible; the election is opened and closed empty so
        # the refusal itself is on the audited record.
        election.close()
    else:
        for agent in agents:
            ctx = {"visible_votes": [] if sealed else list(visible), "stage": event.stage, **(extra_context or {})}
            choice, rationale = agent.decide(proposal, ctx)
            b = Ballot(cfg.election_id, agent.identity.agent_id, choice, rationale)
            env = Envelope.cast(agent.identity, b, election.public_key)
            election.accept(env)
            cast.append((agent.identity.name, env))
            if not sealed:
                visible.append((agent.identity.name, choice))
        if revote_hook is not None:
            for agent in agents:
                ctx = {"visible_votes": [] if sealed else list(visible), "stage": event.stage, "revote": True}
                res = revote_hook(agent, proposal, ctx)
                if res is not None:
                    choice, rationale = res
                    env = Envelope.cast(agent.identity, Ballot(cfg.election_id, agent.identity.agent_id, choice, rationale), election.public_key)
                    election.accept(env)
                    cast.append((agent.identity.name, env))
        election.close()

    # Key ceremony: k custodians hand in their shares.
    election.decrypt(shares[:threshold_k])
    result = tally(election)

    # EAP on rationales (flag only — a decision is never silently altered)
    eap_rationales = {aid: eap.check(b.rationale) for aid, b in election.decrypted.items()}
    election._append("eap", {"proposal": eap_proposal.to_dict(), "rationales": {k: v.to_dict() for k, v in eap_rationales.items()}})

    audit = Auditor(election.export_log(), election.export_envelopes()).run()

    advanced = bool(result.decided and result.winner == proposal.choices[0] and eap_proposal.passed and audit.ok)
    event.transitions.append(
        Transition(
            from_stage=event.stage,
            to_stage=event.next_stage,
            election_id=cfg.election_id,
            tally=result.to_dict(),
            advanced=advanced,
            eap_proposal=eap_proposal.to_dict(),
            eap_rationales={k: v.to_dict() for k, v in eap_rationales.items()},
            audit=audit.to_dict(),
            log=election.export_log(),
            envelopes=election.export_envelopes(),
        )
    )
    if advanced:
        event.stage_index += 1
    return BallotRun(election, result, audit, eap_proposal, eap_rationales, cast)
