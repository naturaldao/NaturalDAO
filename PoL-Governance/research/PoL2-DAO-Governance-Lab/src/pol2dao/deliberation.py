"""Deliberation with PAI-guaranteed equal speaking rights.

PoL2 grounding (PoLEn 4.3.3, "Core requirements for PAI to implement Equal
Connection"): "PAI ensures strict turn-taking in speaking, not monopolizing the
dialogue", and 4.3.3.2 "real-time hate-language identification and correction
suggestions". Flagged messages stay on record with a repair prompt; the
speaker's right to speak is never removed (persons equal, behaviour judged).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from .eap import Judge, Route, ScreeningPolicy, TypedDecision, repair_prompt
from .metrics import gini

Moderation = Literal["free", "round_robin"]


class TurnError(RuntimeError):
    """Raised when someone speaks out of turn under round-robin moderation."""


@dataclass(frozen=True)
class Message:
    index: int
    speaker: str
    text: str
    decision: TypedDecision | None = None
    route: Route = Route.PASS
    repair: str | None = None

    def to_dict(self) -> dict:
        d = {"index": self.index, "speaker": self.speaker, "text": self.text,
             "route": self.route.value}
        if self.decision is not None:
            d["screening"] = self.decision.to_dict()
        if self.repair:
            d["repair_prompt"] = self.repair
        return d


class Deliberation:
    def __init__(self, participants: Sequence[str], moderation: Moderation = "round_robin",
                 judge: Judge | None = None, policy: ScreeningPolicy | None = None,
                 lang: str = "zh") -> None:
        if len(set(participants)) != len(participants) or not participants:
            raise ValueError("participants must be non-empty and unique")
        self.participants = list(participants)
        self.moderation = moderation
        self.judge = judge
        self.policy = policy or ScreeningPolicy()
        self.lang = lang
        self.messages: list[Message] = []
        self._turn = 0

    @property
    def next_speaker(self) -> str | None:
        if self.moderation != "round_robin":
            return None
        return self.participants[self._turn % len(self.participants)]

    def _check_turn(self, speaker: str) -> None:
        if speaker not in self.participants:
            raise ValueError(f"{speaker!r} is not a participant")
        if self.moderation == "round_robin" and speaker != self.next_speaker:
            raise TurnError(f"it is {self.next_speaker}'s turn, not {speaker}'s")

    def pass_turn(self, speaker: str) -> None:
        self._check_turn(speaker)
        self._turn += 1

    def post(self, speaker: str, text: str) -> Message:
        self._check_turn(speaker)
        decision, route, repair = None, Route.PASS, None
        if self.judge is not None:
            decision = self.judge.judge(text)
            route = self.policy.route(decision)
            if route is Route.FLAG:
                repair = repair_prompt(decision, self.lang)
        msg = Message(len(self.messages), speaker, text, decision, route, repair)
        self.messages.append(msg)
        self._turn += 1
        return msg

    def voice_report(self) -> dict:
        """How equally the floor was shared (message counts and characters)."""
        counts = {p: 0 for p in self.participants}
        chars = {p: 0 for p in self.participants}
        for m in self.messages:
            counts[m.speaker] += 1
            chars[m.speaker] += len(m.text)
        total_chars = sum(chars.values()) or 1
        return {
            "moderation": self.moderation,
            "messages": len(self.messages),
            "gini_messages": round(gini(counts.values()), 4),
            "gini_chars": round(gini(chars.values()), 4),
            "max_char_share": round(max(chars.values()) / total_chars, 4),
            "silent_participants": sum(1 for c in counts.values() if c == 0),
            "routes": {r.value: sum(1 for m in self.messages if m.route is r) for r in Route},
        }
