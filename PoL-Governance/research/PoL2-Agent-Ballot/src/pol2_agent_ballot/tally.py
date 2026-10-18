"""Tally and decision rule."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Optional

from .election import Election, Stage


@dataclass
class TallyResult:
    counts: Dict[str, int]
    eligible: int
    valid: int
    invalid: int
    quorum_met: bool
    rule: str
    winner: Optional[str]
    decided: bool
    reason: str
    #: rationales grouped by choice, published with the result (PoL2 第四条)
    rationales: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def tally(election: Election) -> TallyResult:
    if election.stage is not Stage.DECRYPTED:
        raise RuntimeError("decrypt first")
    cfg = election.config
    counts = Counter({c: 0 for c in cfg.choices})
    rationales: Dict[str, Dict[str, str]] = {c: {} for c in cfg.choices}
    for aid, b in election.decrypted.items():
        counts[b.choice] += 1
        rationales[b.choice][aid] = b.rationale
    eligible = len(election.registry.ids())
    valid = sum(counts.values())
    invalid = len(election.invalid)
    quorum_met = eligible > 0 and valid / eligible >= cfg.quorum

    winner: Optional[str] = None
    decided = False
    reason = ""
    if not quorum_met:
        reason = f"quorum not met: {valid}/{eligible} < {cfg.quorum}"
    elif valid == 0:
        reason = "no valid ballots"
    else:
        top, top_n = counts.most_common(1)[0]
        ties = [c for c, n in counts.items() if n == top_n]
        if len(ties) > 1:
            reason = f"tie between {ties}"
        else:
            frac = top_n / valid
            if cfg.rule == "plurality":
                decided = True
            elif cfg.rule == "majority":
                decided = frac > 0.5
            elif cfg.rule == "supermajority":
                decided = frac >= 2 / 3
            elif cfg.rule == "unanimous":
                decided = top_n == valid
            else:
                raise ValueError(f"unknown rule {cfg.rule}")
            winner = top if decided else None
            reason = f"{top!r} got {top_n}/{valid} under rule {cfg.rule}" + ("" if decided else " — threshold not reached")
    res = TallyResult(dict(counts), eligible, valid, invalid, quorum_met, cfg.rule, winner, decided, reason, rationales)
    election._append("tally", res.to_dict())
    return res
