"""Deliberative consensus on top of sealed ballots.

PoL2's EAP (5.3.3) asks PAI to help "所有重要决策的相关方完全同意" — consensus,
not a bare majority. Consensus is reached here by **repeated sealed rounds
with full disclosure between rounds**, the structure of the Delphi method
(Dalkey & Helmer 1963): in every round each agent decides privately and
casts a sealed ballot; at the close all choices and rationales are
published; the next round starts with that record as shared context. The
process stops when the decision rule (default `unanimous`) is met, or after
`max_rounds`, in which case the event does not advance and the full record
of disagreement is preserved.

Why this is not the cascade of experiments/sealed_vs_open.py: in a cascade
each agent sees a *partial, ordered* tally before deciding and may discard
its own signal; here every agent sees the *complete* previous round only
after committing its own ballot, so each round aggregates all private
information at once. For independent signals of accuracy p > 1/2 the
Bayesian update on the full round converges to the majority signal, which
is the Condorcet-optimal decision; the record shows who changed their mind
and on what evidence (第五条 5).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .agents import Agent, Proposal
from .eap import EAPChecker
from .event import BallotRun, Event, run_transition_ballot
from .identity import AgentIdentity


@dataclass
class RoundRecord:
    round_no: int
    counts: Dict[str, int]
    decided: bool
    winner: Optional[str]
    #: agent name -> (choice, rationale), published at the round's close
    disclosed: Dict[str, tuple]
    changed_minds: List[str] = field(default_factory=list)


@dataclass
class ConsensusResult:
    reached: bool
    rounds: List[RoundRecord]
    final: Optional[BallotRun]
    rule: str

    @property
    def n_rounds(self) -> int:
        return len(self.rounds)

    def to_dict(self) -> dict:
        return {
            "reached": self.reached,
            "rule": self.rule,
            "rounds": [
                {"round": r.round_no, "counts": r.counts, "decided": r.decided, "winner": r.winner, "changed_minds": r.changed_minds, "disclosed": {k: {"choice": v[0], "rationale": v[1]} for k, v in r.disclosed.items()}}
                for r in self.rounds
            ],
        }


def run_consensus(
    event: Event,
    proposal: Proposal,
    organiser: AgentIdentity,
    agents: Sequence[Agent],
    *,
    rule: str = "unanimous",
    max_rounds: int = 5,
    custodians: Optional[Sequence[AgentIdentity]] = None,
    threshold_k: int = 2,
    quorum: float = 1.0,
    eap: Optional[EAPChecker] = None,
) -> ConsensusResult:
    """Run sealed rounds until `rule` is met or `max_rounds` is exhausted.

    Only the round that meets the rule advances the event; earlier rounds are
    recorded as transitions with `advanced=False`, so the audit trail shows
    the whole deliberation. If consensus is never reached the event stays
    where it is.
    """
    rounds: List[RoundRecord] = []
    prior: List[dict] = []  # disclosed record of the previous round
    final: Optional[BallotRun] = None
    names = {a.identity.agent_id: a.identity.name for a in agents}
    last_choice: Dict[str, str] = {}

    for r in range(1, max_rounds + 1):
        extra = {"round": r, "prior_round": list(prior)}
        run = run_transition_ballot(
            event,
            proposal,
            organiser,
            agents,
            custodians=custodians,
            threshold_k=threshold_k,
            rule=rule,
            quorum=quorum,
            eap=eap,
            sealed=True,
            extra_context=extra,
        )
        disclosed = {names[aid]: (b.choice, b.rationale) for aid, b in run.election.decrypted.items()}
        changed = [n for n, (c, _) in disclosed.items() if n in last_choice and last_choice[n] != c]
        last_choice = {n: c for n, (c, _) in disclosed.items()}
        rounds.append(RoundRecord(r, run.tally.counts, run.tally.decided, run.tally.winner, disclosed, changed))
        final = run
        if run.tally.decided:
            return ConsensusResult(True, rounds, final, rule)
        prior = [{"agent": n, "choice": c, "rationale": txt} for n, (c, txt) in disclosed.items()]
    return ConsensusResult(False, rounds, final, rule)
