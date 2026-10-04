"""One PoL2 governance session, end to end, recorded on a decision chain.

Flow (each step is appended to :class:`~pol2dao.ledger.DecisionChain`)::

    proposal --EAP screen--> deliberation (equal turns, EAP screen per message)
      --> vote (token ballots, power scheme, aggregation rule)
      --> questioning period (any participant may question; every question
          needs an explanation -- PoLEn ch. 7 Art. 9 and Art. 11)
      --> decision record (data sources, reasoning steps, ethical checks)

A decision is ``escalated`` to human review instead of ``decided`` when a
question is left unexplained, when the winning option itself was flagged by
EAP screening, or when the tally is tied. "The end of an escalation chain must
be a human" is taken from the PoL2-Jev literature survey.

The "PAI" here is a transparent, deterministic procedure, not an AI model.
PoLEn ch. 7 Art. 2 describes NaturalDAO deciding without human voting; this
lab keeps human voting as an explicit input so the two can be compared (see
docs/concept-mapping.md, "open questions").
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Sequence

from .deliberation import Deliberation, Moderation
from .eap import Judge, LexiconJudge, Route, ScreeningPolicy
from .ledger import DecisionChain
from .voting import Ballot, PowerScheme, Rule, Tally, budgets, tally


@dataclass(frozen=True)
class Proposal:
    id: str
    title: str
    options: tuple[str, ...]
    rationale: str = ""
    author: str = "PAI"


@dataclass(frozen=True)
class GovernanceConfig:
    rule: Rule = "quadratic"
    power: PowerScheme = "equal"
    moderation: Moderation = "round_robin"
    screening: bool = True
    policy: ScreeningPolicy = field(default_factory=ScreeningPolicy)
    lang: str = "zh"

    @classmethod
    def pol2(cls, **kw) -> "GovernanceConfig":
        return cls(rule="quadratic", power="equal", moderation="round_robin", screening=True, **kw)

    @classmethod
    def sharma(cls, rule: Rule, power: PowerScheme, **kw) -> "GovernanceConfig":
        """One of the four conditions of the DAO experiment (no PoL2 additions)."""
        return cls(rule=rule, power=power, moderation="free", screening=False, **kw)

    def to_dict(self) -> dict:
        return {"rule": self.rule, "power": self.power, "moderation": self.moderation,
                "screening": self.screening,
                "policy": {"review_threshold": self.policy.review_threshold,
                           "flag_threshold": self.policy.flag_threshold}}


@dataclass(frozen=True)
class Decision:
    status: str  # "decided" | "escalated"
    winner: int
    tally: Tally
    reasons: tuple[str, ...]
    checks: dict

    def to_dict(self) -> dict:
        return {"status": self.status, "winner": self.winner, "tally": self.tally.to_dict(),
                "escalation_reasons": list(self.reasons), "ethical_checks": self.checks}


class GovernanceSession:
    def __init__(self, proposal: Proposal, participants: Sequence[str],
                 config: GovernanceConfig | None = None, judge: Judge | None = None,
                 chain: DecisionChain | None = None, power_holders: Sequence[str] = (),
                 seed: int = 0) -> None:
        self.proposal = proposal
        self.config = config or GovernanceConfig.pol2()
        self.judge = judge or (LexiconJudge() if self.config.screening else None)
        self.chain = chain if chain is not None else DecisionChain()  # an empty chain is falsy
        self.participants = list(participants)
        holders = [self.participants.index(p) for p in power_holders] or None
        self.budgets = dict(zip(self.participants, budgets(
            len(self.participants), self.config.power, random.Random(seed), holders)))
        self.deliberation = Deliberation(self.participants, self.config.moderation,
                                         self.judge, self.config.policy, self.config.lang)
        self.ballots: dict[str, Ballot] = {}
        self.questions: dict[int, dict] = {}
        self.result: Tally | None = None
        self.stage = "deliberation"

        screened_options = []
        for text in proposal.options:
            item = {"text": text}
            if self.judge is not None:
                d = self.judge.judge(text)
                item["screening"] = d.to_dict()
                item["route"] = self.config.policy.route(d).value
            screened_options.append(item)
        self.option_routes = [o.get("route", Route.PASS.value) for o in screened_options]
        self.chain.append("proposal", {
            "id": proposal.id, "title": proposal.title, "author": proposal.author,
            "rationale": proposal.rationale, "options": screened_options,
            "config": self.config.to_dict(), "participants": self.participants,
            "budgets": self.budgets,
        })

    # -- deliberation ------------------------------------------------------
    def say(self, speaker: str, text: str):
        self._require("deliberation")
        msg = self.deliberation.post(speaker, text)
        self.chain.append("message", msg.to_dict())
        return msg

    def pass_turn(self, speaker: str) -> None:
        self._require("deliberation")
        self.deliberation.pass_turn(speaker)

    # -- voting ------------------------------------------------------------
    def open_vote(self) -> None:
        self._require("deliberation")
        self.chain.append("deliberation_closed", self.deliberation.voice_report())
        self.stage = "voting"

    def cast(self, voter: str, tokens: Sequence[float]) -> Ballot:
        self._require("voting")
        if voter not in self.budgets:
            raise ValueError(f"{voter!r} is not a participant")
        if len(tokens) != len(self.proposal.options):
            raise ValueError("one token count per option is required")
        budget = self.budgets[voter]
        if sum(tokens) > budget + 1e-9:
            raise ValueError(f"{voter} spent {sum(tokens)} > budget {budget}")
        ballot = Ballot(voter, tuple(float(t) for t in tokens), budget)
        self.ballots[voter] = ballot  # re-casting replaces the earlier ballot
        self.chain.append("ballot", {"voter": voter, "tokens": list(ballot.tokens),
                                     "budget": budget})
        return ballot

    def close_vote(self) -> Tally:
        self._require("voting")
        self.result = tally(list(self.ballots.values()), self.config.rule)
        self.chain.append("tally", {**self.result.to_dict(), "n_ballots": len(self.ballots),
                                    "per_voter_influence": self.result.per_voter})
        self.stage = "questioning"
        return self.result

    # -- supervision -------------------------------------------------------
    def question(self, asker: str, text: str) -> int:
        """Right to question (Art. 9). Questions are recorded, never blocked."""
        self._require("questioning")
        qid = len(self.questions)
        payload = {"qid": qid, "asker": asker, "text": text}
        if self.judge is not None:
            payload["screening"] = self.judge.judge(text).to_dict()
        self.questions[qid] = {**payload, "explanation": None}
        self.chain.append("question", payload)
        return qid

    def explain(self, qid: int, text: str, by: str = "PAI") -> None:
        """Obligation to explain (Art. 9.2)."""
        self._require("questioning")
        if qid not in self.questions:
            raise KeyError(qid)
        self.questions[qid]["explanation"] = text
        self.chain.append("explanation", {"qid": qid, "by": by, "text": text})

    def finalize(self) -> Decision:
        self._require("questioning")
        assert self.result is not None
        t = self.result
        voice = self.deliberation.voice_report()
        unanswered = [q for q, v in self.questions.items() if not v["explanation"]]
        checks = {
            "equal_connection.power": self.config.power == "equal",
            "equal_connection.turn_taking": self.config.moderation == "round_robin",
            "equal_connection.voice_gini": voice["gini_chars"],
            "restrain_hate.messages": voice["routes"],
            "restrain_hate.winning_option_route": self.option_routes[t.winner],
            "supervision.questions": len(self.questions),
            "supervision.unanswered": unanswered,
        }
        reasons = []
        if unanswered:
            reasons.append(f"{len(unanswered)} question(s) without explanation")
        if self.option_routes[t.winner] != Route.PASS.value:
            reasons.append("winning option was not cleared by EAP screening")
        if t.tied:
            reasons.append(f"tie between options {t.leaders}")
        decision = Decision("escalated" if reasons else "decided", t.winner, t,
                            tuple(reasons), checks)
        ballot_entries = [e.index for e in self.chain.of_kind("ballot")]
        self.chain.append("decision", {
            **decision.to_dict(),
            "winning_option": self.proposal.options[t.winner],
            "data_sources": {"ballot_entries": ballot_entries,
                             "message_entries": [e.index for e in self.chain.of_kind("message")]},
            "reasoning_steps": [
                f"aggregate {len(self.ballots)} ballots with rule '{self.config.rule}'",
                f"power scheme '{self.config.power}'",
                f"option {t.winner + 1} ('{self.proposal.options[t.winner]}') leads with share "
                f"{t.shares[t.winner]:.3f}",
            ],
            "ethical_foundations": ["PoLEn 4.3.1 Equal Connection",
                                    "PoLEn 4.3.2 Promote love, restrain hate",
                                    "PoLEn 7 Art. 4-5 transparency, verifiable decision chain",
                                    "PoLEn 7 Art. 9 right to question, obligation to explain"],
        })
        self.stage = "closed"
        return decision

    def _require(self, stage: str) -> None:
        if self.stage != stage:
            raise RuntimeError(f"session is in stage '{self.stage}', need '{stage}'")
