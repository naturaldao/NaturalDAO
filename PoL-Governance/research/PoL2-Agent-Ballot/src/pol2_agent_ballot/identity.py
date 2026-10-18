"""Agent identities and the eligible-voter registry.

IVXV authenticates voters with state-issued credentials (ID-card, Mobile-ID,
Smart-ID, Web eID) and checks them against a signed voter list. Agents have
no state-issued identity, so we use the simplest robust substitute: an
Ed25519 key pair per agent, and a registry (the "voter list") that the
election organiser signs. An agent is eligible for an election iff its public
key is on that election's roster.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from nacl.encoding import HexEncoder
from nacl.signing import SigningKey, VerifyKey


@dataclass
class AgentIdentity:
    """An agent that can sign ballots. Keep `signing_key` private."""

    name: str
    signing_key: SigningKey
    #: free-form description: model, role, operator, etc.
    meta: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def generate(cls, name: str, **meta: str) -> "AgentIdentity":
        return cls(name=name, signing_key=SigningKey.generate(), meta=dict(meta))

    @property
    def verify_key(self) -> VerifyKey:
        return self.signing_key.verify_key

    @property
    def agent_id(self) -> str:
        """Stable identifier = hex public key."""
        return self.verify_key.encode(encoder=HexEncoder).decode()

    def sign(self, message: bytes) -> bytes:
        return self.signing_key.sign(message).signature

    def public_record(self) -> dict:
        return {"agent_id": self.agent_id, "name": self.name, "meta": self.meta}


@dataclass
class AgentRegistry:
    """The signed roster of eligible agents (IVXV: voter list).

    The organiser signs the canonical JSON of the roster so that a collector
    cannot quietly add or remove voters after the fact.
    """

    agents: Dict[str, dict] = field(default_factory=dict)  # agent_id -> public record
    organiser_signature: Optional[bytes] = None
    organiser_key: Optional[VerifyKey] = None

    def add(self, identity: AgentIdentity) -> None:
        if self.organiser_signature is not None:
            raise RuntimeError("registry already sealed; cannot add agents")
        self.agents[identity.agent_id] = identity.public_record()

    def seal(self, organiser: AgentIdentity) -> None:
        self.organiser_key = organiser.verify_key
        self.organiser_signature = organiser.sign(self.canonical())

    def canonical(self) -> bytes:
        return json.dumps(self.agents, sort_keys=True, separators=(",", ":")).encode()

    def is_sealed(self) -> bool:
        return self.organiser_signature is not None

    def verify(self) -> bool:
        if self.organiser_key is None or self.organiser_signature is None:
            return False
        try:
            self.organiser_key.verify(self.canonical(), self.organiser_signature)
            return True
        except Exception:
            return False

    def is_eligible(self, agent_id: str) -> bool:
        return agent_id in self.agents

    def verify_key_of(self, agent_id: str) -> VerifyKey:
        if agent_id not in self.agents:
            raise KeyError(agent_id)
        return VerifyKey(agent_id.encode(), encoder=HexEncoder)

    def ids(self) -> List[str]:
        return sorted(self.agents)

    def to_dict(self) -> dict:
        return {
            "agents": self.agents,
            "organiser_key": self.organiser_key.encode(encoder=HexEncoder).decode()
            if self.organiser_key
            else None,
            "organiser_signature": self.organiser_signature.hex()
            if self.organiser_signature
            else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentRegistry":
        reg = cls(agents=dict(d["agents"]))
        if d.get("organiser_key"):
            reg.organiser_key = VerifyKey(d["organiser_key"].encode(), encoder=HexEncoder)
        if d.get("organiser_signature"):
            reg.organiser_signature = bytes.fromhex(d["organiser_signature"])
        return reg


def build_registry(organiser: AgentIdentity, agents: Iterable[AgentIdentity]) -> AgentRegistry:
    reg = AgentRegistry()
    for a in agents:
        reg.add(a)
    reg.seal(organiser)
    return reg
