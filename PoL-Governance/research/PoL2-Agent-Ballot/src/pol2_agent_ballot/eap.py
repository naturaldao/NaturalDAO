"""Ethical Alignment Protocol (EAP) gate — interface and a placeholder.

PoL2 (第六条 3, 第十一条 3) requires that proposals and their execution pass
EAP verification. In IVXV terms this is the *eligibility layer* for
proposals, parallel to the voter-list check for voters: a proposal that
fails EAP is not put to a vote, and a decision whose rationales fail EAP is
flagged in the audit log.

What this module does NOT do: it does not detect 恨语. Reliable 恨语
recognition is the subject of PoL2's own research programme (see the
sycophancy and honesty-probe experiments in the same GitHub account). The
`KeywordEAP` below is a stub that exists so the pipeline has a hook; replace
it with a real checker via the `EAPChecker` protocol. Its verdicts carry a
`placeholder=True` flag so no audit log can mistake them for a real
assessment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Protocol


@dataclass
class EAPVerdict:
    passed: bool
    reasons: List[str] = field(default_factory=list)
    checker: str = "unspecified"
    placeholder: bool = True

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class EAPChecker(Protocol):
    name: str

    def check(self, text: str) -> EAPVerdict: ...


class AlwaysPassEAP:
    """For tests and for runs where EAP is handled outside this library."""

    name = "always-pass"

    def check(self, text: str) -> EAPVerdict:
        return EAPVerdict(True, ["no check performed"], self.name, placeholder=True)


class KeywordEAP:
    """Placeholder: fails only on an explicit blocklist. Not a 恨语 detector."""

    name = "keyword-placeholder"

    def __init__(self, blocklist: Iterable[str] = ()):
        self.blocklist = [w.lower() for w in blocklist]

    def check(self, text: str) -> EAPVerdict:
        low = text.lower()
        hits = [w for w in self.blocklist if w in low]
        if hits:
            return EAPVerdict(False, [f"blocklisted term: {w}" for w in hits], self.name, placeholder=True)
        return EAPVerdict(True, ["no blocklisted terms (placeholder check only)"], self.name, placeholder=True)
