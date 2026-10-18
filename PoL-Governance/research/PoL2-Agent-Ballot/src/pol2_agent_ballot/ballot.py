"""The double envelope.

IVXV ballot = inner envelope (the encrypted choice) wrapped in an outer
envelope (the voter's qualified digital signature over the inner envelope).
The outer envelope lets the collector check eligibility and detect
re-votes without learning the choice; the inner envelope is what the key
application eventually decrypts.

Here the inner envelope also carries the agent's **rationale**: PoL2's
"verifiable decision chain" (第五条 5) requires that a decision can be
traced to data sources, reasoning steps and ethical grounds, so an agent's
vote without its reasons is not a decision in the PoL2 sense. The rationale
stays sealed with the choice until the close, so that other agents cannot
read it during the voting period.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

from nacl.public import PublicKey

from .crypto import seal
from .identity import AgentIdentity


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@dataclass
class Ballot:
    """The *plaintext* inner envelope. Never leaves the agent unsealed."""

    election_id: str
    agent_id: str
    choice: str
    rationale: str = ""
    #: random nonce so two agents choosing the same option never seal to the
    #: same bytes, and so a sealed ballot cannot be matched by guessing.
    nonce: str = field(default_factory=lambda: secrets.token_hex(16))

    def to_bytes(self) -> bytes:
        return canonical(
            {
                "election_id": self.election_id,
                "agent_id": self.agent_id,
                "choice": self.choice,
                "rationale": self.rationale,
                "nonce": self.nonce,
            }
        )

    @classmethod
    def from_bytes(cls, b: bytes) -> "Ballot":
        d = json.loads(b.decode())
        return cls(**d)


@dataclass
class Envelope:
    """Outer envelope: sealed inner envelope + agent signature."""

    election_id: str
    agent_id: str
    sealed: bytes
    cast_at: float
    signature: bytes
    #: filled in by the collector on acceptance (IVXV: registration receipt)
    receipt: Optional[dict] = None

    # ---- construction -----------------------------------------------------
    @classmethod
    def cast(cls, identity: AgentIdentity, ballot: Ballot, election_pk: PublicKey) -> "Envelope":
        if ballot.agent_id != identity.agent_id:
            raise ValueError("ballot.agent_id must match the signing identity")
        sealed = seal(ballot.to_bytes(), election_pk)
        cast_at = time.time()
        sig = identity.sign(cls._signed_bytes(ballot.election_id, identity.agent_id, sealed, cast_at))
        return cls(ballot.election_id, identity.agent_id, sealed, cast_at, sig)

    @staticmethod
    def _signed_bytes(election_id: str, agent_id: str, sealed: bytes, cast_at: float) -> bytes:
        return canonical(
            {
                "election_id": election_id,
                "agent_id": agent_id,
                "sealed_sha256": sha256(sealed),
                "cast_at": cast_at,
            }
        )

    def signed_bytes(self) -> bytes:
        return self._signed_bytes(self.election_id, self.agent_id, self.sealed, self.cast_at)

    @property
    def envelope_hash(self) -> str:
        """Hash that identifies this envelope in receipts and the audit log."""
        return sha256(self.signed_bytes() + self.signature)

    # ---- serialisation ----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "election_id": self.election_id,
            "agent_id": self.agent_id,
            "sealed": self.sealed.hex(),
            "cast_at": self.cast_at,
            "signature": self.signature.hex(),
            "receipt": self.receipt,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Envelope":
        return cls(
            d["election_id"],
            d["agent_id"],
            bytes.fromhex(d["sealed"]),
            float(d["cast_at"]),
            bytes.fromhex(d["signature"]),
            d.get("receipt"),
        )
