"""Voting agents.

An agent is anything with `decide(proposal, context) -> (choice, rationale)`.
`context["visible_votes"]` is the list of (agent_name, choice) pairs the
agent is allowed to see at decision time: empty under sealed voting, the
running tally under open sequential voting. The experiments compare the two.

`LLMAgent` wraps any `complete(prompt: str) -> str` callable (Anthropic,
OpenAI, a local Ollama model, ...) so that the library has no provider
dependency. The default agents are scripted so the demo runs offline.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol, Sequence, Tuple

from .identity import AgentIdentity


@dataclass
class Proposal:
    proposal_id: str
    title: str
    body: str
    choices: List[str]
    #: optional private evidence given to each agent (e.g. a test result)
    evidence: Dict[str, str] = field(default_factory=dict)

    def prompt(self) -> str:
        return f"Proposal {self.proposal_id}: {self.title}\n\n{self.body}\n\nChoices: {', '.join(self.choices)}"


class Agent(Protocol):
    identity: AgentIdentity

    def decide(self, proposal: Proposal, context: dict) -> Tuple[str, str]: ...


@dataclass
class ScriptedAgent:
    """Votes according to a private signal with fixed accuracy.

    `truth` is the choice a perfectly informed agent would make; the agent's
    private signal equals `truth` with probability `accuracy`. This is the
    standard Condorcet-jury setup, which only works when votes are
    independent — exactly what sealed ballots protect.
    """

    identity: AgentIdentity
    truth: str
    accuracy: float = 0.7
    rng: random.Random = field(default_factory=random.Random)

    def private_signal(self, proposal: Proposal) -> str:
        if self.rng.random() < self.accuracy:
            return self.truth
        others = [c for c in proposal.choices if c != self.truth]
        return self.rng.choice(others) if others else self.truth

    def decide(self, proposal: Proposal, context: dict) -> Tuple[str, str]:
        sig = self.private_signal(proposal)
        return sig, f"private signal suggests {sig!r} (accuracy {self.accuracy})"


@dataclass
class ConformistAgent(ScriptedAgent):
    """Same private signal, but follows a visible majority when the lead is
    at least `lead` votes. Under sealed voting no votes are visible and the
    agent reduces to ScriptedAgent; under open sequential voting it can start
    an information cascade."""

    lead: int = 2

    def decide(self, proposal: Proposal, context: dict) -> Tuple[str, str]:
        sig = self.private_signal(proposal)
        visible: Sequence[Tuple[str, str]] = context.get("visible_votes", [])
        if visible:
            counts: Dict[str, int] = {}
            for _, c in visible:
                counts[c] = counts.get(c, 0) + 1
            ranked = sorted(counts.items(), key=lambda kv: -kv[1])
            top, n = ranked[0]
            second = ranked[1][1] if len(ranked) > 1 else 0
            if n - second >= self.lead and top != sig:
                return top, f"private signal said {sig!r} but {n} visible votes favour {top!r}; following the majority"
        return sig, f"private signal suggests {sig!r}; no decisive visible majority"


def parse_choice(raw: str, choices: Sequence[str]) -> Tuple[str, str]:
    """Extract (choice, rationale) from a model reply, tolerating the usual
    deviations from strict JSON: a leading <think> block, code fences, prose
    around the object, \\' escapes, raw newlines inside strings. If no JSON
    object parses, fall back to a `"choice": "<option>"` pattern. Returns
    ("", reason) when no valid choice can be found, which the election records
    as an invalid ballot."""
    if not isinstance(raw, str):
        return "", f"unparseable model output: {raw!r}"
    visible = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)
    for cand in reversed(re.findall(r"\{[^{}]*\}", visible)):
        for text in (cand, cand.replace("\\'", "'")):
            try:
                d = json.loads(text, strict=False)
            except Exception:
                continue
            choice = str(d.get("choice", "")).strip().lower()
            if choice in choices:
                return choice, str(d.get("rationale", ""))
    m = re.search(r'"choice"\s*:\s*"(' + "|".join(map(re.escape, choices)) + r')"', visible, re.I)
    if m:
        r = re.search(r'"rationale"\s*:\s*"(.*?)"\s*[},]', visible, re.S)
        return m.group(1).lower(), (r.group(1) if r else "")
    return "", f"unparseable model output: {raw[:300]!r}"


@dataclass
class LLMAgent:
    """Wraps a completion function. The prompt asks for JSON so the choice can
    be parsed; if parsing fails the agent abstains (choice=None is rejected
    by the election, which is the honest outcome)."""

    identity: AgentIdentity
    complete: Callable[[str], str]
    system: str = (
        "You are one agent in a NaturalDAO council governed by the PoL2 Ethical "
        "Alignment Protocol. Decide on the proposal using only the evidence given. "
        "Answer with JSON: {\"choice\": <one of the choices>, \"rationale\": <2-4 sentences "
        "naming the evidence and the ethical ground for your choice>}"
    )

    def decide(self, proposal: Proposal, context: dict) -> Tuple[str, str]:
        parts = [self.system, proposal.prompt()]
        if proposal.evidence:
            parts.append("Evidence:\n" + "\n".join(f"- {k}: {v}" for k, v in proposal.evidence.items()))
        if context.get("visible_votes"):
            parts.append("Votes already cast: " + ", ".join(f"{n}->{c}" for n, c in context["visible_votes"]))
        raw = self.complete("\n\n".join(parts))
        return parse_choice(raw, proposal.choices)


@dataclass
class DeliberativeAgent(ScriptedAgent):
    """Agent for multi-round consensus (consensus.py).

    Round 1: votes its private signal, like ScriptedAgent.
    Later rounds: treats every round-1 ballot as an independent signal of the
    same accuracy and votes for the posterior majority (ties keep its own
    signal). Only round-1 ballots are counted as evidence: later ballots are
    already conditioned on round 1 and would double-count it.

    `stubborn=True` never updates; used to show a deliberation that fails to
    reach unanimity and leaves the event where it is.
    """

    stubborn: bool = False
    _signal: Optional[str] = None
    _round1: Optional[List[str]] = None

    def decide(self, proposal: Proposal, context: dict) -> Tuple[str, str]:
        rnd = context.get("round", 1)
        if self._signal is None:
            self._signal = self.private_signal(proposal)
        if rnd == 1 or self.stubborn:
            if rnd > 1:
                return self._signal, f"round {rnd}: keeping my private signal {self._signal!r} regardless of the record"
            return self._signal, f"round 1: private signal suggests {self._signal!r}"
        prior = context.get("prior_round", [])
        if self._round1 is None:
            self._round1 = [d["choice"] for d in prior]
        counts: Dict[str, int] = {}
        for c in self._round1:
            counts[c] = counts.get(c, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: -kv[1])
        if not ranked or (len(ranked) > 1 and ranked[0][1] == ranked[1][1]):
            return self._signal, f"round {rnd}: round-1 evidence is tied; keeping my signal {self._signal!r}"
        top, n = ranked[0]
        if top == self._signal:
            return top, f"round {rnd}: round-1 record ({n}/{len(self._round1)} for {top!r}) agrees with my signal"
        return top, f"round {rnd}: my signal said {self._signal!r}, but {n}/{len(self._round1)} independent round-1 signals favour {top!r}; updating"
