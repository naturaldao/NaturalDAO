"""The election: configuration, the collector's ballot box, and lifecycle.

IVXV lifecycle (simplified): trust-root config → election config → voter
list → voting period (collector accepts double envelopes, registers each with
a registration service, issues receipts) → close → processor strips outer
envelopes, applies re-vote and paper-vote rules → key application decrypts
→ tally → auditor verifies everything.

Here the collector, processor and key application are methods on one
`Election` object, but every step leaves a record in a hash-chained log so
that an independent `Auditor` (verify.py) can re-check the whole chain.
"""
from __future__ import annotations

import enum
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from nacl.encoding import HexEncoder
from nacl.public import PrivateKey, PublicKey

from .ballot import Ballot, Envelope, canonical, sha256
from .crypto import KeyShare, generate_election_keypair, recover_private_key, split_private_key, unseal
from .identity import AgentIdentity, AgentRegistry


class Stage(enum.Enum):
    SETUP = "setup"
    OPEN = "open"
    CLOSED = "closed"
    DECRYPTED = "decrypted"


@dataclass
class ElectionConfig:
    """Signed election configuration (IVXV: election.json + choices list)."""

    election_id: str
    question: str
    choices: List[str]
    #: what the election decides: usually "advance event <id> from stage X to Y"
    subject: Dict[str, str] = field(default_factory=dict)
    #: threshold k of n custodians needed to reconstruct the decryption key
    threshold_k: int = 2
    threshold_n: int = 3
    #: decision rule: "majority" (strict > 1/2 of valid ballots),
    #: "supermajority" (>= 2/3), "unanimous", or "plurality"
    rule: str = "majority"
    #: minimum fraction of eligible agents that must cast a valid ballot
    quorum: float = 0.5
    #: how long after acceptance an agent may run individual verification (s)
    verification_window_s: float = 30 * 60
    created_at: float = field(default_factory=time.time)

    def canonical(self) -> bytes:
        d = dict(self.__dict__)
        return canonical(d)


@dataclass
class LogEntry:
    """One link in the collector's append-only, hash-chained log."""

    seq: int
    kind: str
    payload: dict
    prev_hash: str
    ts: float
    hash: str = ""

    def compute_hash(self) -> str:
        body = canonical({"seq": self.seq, "kind": self.kind, "payload": self.payload, "prev_hash": self.prev_hash, "ts": self.ts})
        return sha256(body)

    def to_dict(self) -> dict:
        return {"seq": self.seq, "kind": self.kind, "payload": self.payload, "prev_hash": self.prev_hash, "ts": self.ts, "hash": self.hash}


class RejectedBallot(Exception):
    pass


class Election:
    """Collector + processor + key application for one decision."""

    def __init__(self, config: ElectionConfig, registry: AgentRegistry, organiser: AgentIdentity):
        if not registry.is_sealed():
            raise ValueError("registry must be sealed by the organiser")
        self.config = config
        self.registry = registry
        self.organiser = organiser
        self.config_signature = organiser.sign(config.canonical())
        self.stage = Stage.SETUP
        self.log: List[LogEntry] = []
        self._sk: Optional[PrivateKey] = None  # only during setup, then split and discarded
        self.public_key: Optional[PublicKey] = None
        self.shares: List[KeyShare] = []
        #: agent_id -> list of accepted envelopes in arrival order (re-votes)
        self.envelopes: Dict[str, List[Envelope]] = {}
        self.decrypted: Dict[str, Ballot] = {}  # agent_id -> final ballot
        self.invalid: Dict[str, str] = {}  # agent_id -> reason, after decrypt
        self.recovered_sk: Optional[PrivateKey] = None
        self._append("config", {"config": json.loads(config.canonical()), "signature": self.config_signature.hex(), "organiser": organiser.agent_id})
        self._append("registry", registry.to_dict())

    # ------------------------------------------------------------------ log
    def _append(self, kind: str, payload: dict) -> LogEntry:
        prev = self.log[-1].hash if self.log else "0" * 64
        e = LogEntry(seq=len(self.log), kind=kind, payload=payload, prev_hash=prev, ts=time.time())
        e.hash = e.compute_hash()
        self.log.append(e)
        return e

    # ---------------------------------------------------------------- setup
    def generate_keys(self) -> List[KeyShare]:
        """Key ceremony: create the election key pair, split the private key
        among custodians, forget the whole key (IVXV key application)."""
        if self.stage is not Stage.SETUP:
            raise RuntimeError("keys already generated")
        self._sk, self.public_key = generate_election_keypair()
        self.shares = split_private_key(self._sk, self.config.threshold_k, self.config.threshold_n)
        self._append("key_ceremony", {"public_key": self.public_key.encode(encoder=HexEncoder).decode(), "k": self.config.threshold_k, "n": self.config.threshold_n})
        self._sk = None
        return self.shares

    def open(self) -> None:
        if self.public_key is None:
            raise RuntimeError("run generate_keys() first")
        self.stage = Stage.OPEN
        self._append("open", {})

    # ------------------------------------------------------------ collector
    def accept(self, env: Envelope) -> dict:
        """Collector: check eligibility and signature, register, issue receipt."""
        if self.stage is not Stage.OPEN:
            raise RejectedBallot(f"election not open (stage={self.stage.value})")
        if env.election_id != self.config.election_id:
            raise RejectedBallot("wrong election id")
        if not self.registry.is_eligible(env.agent_id):
            raise RejectedBallot("agent not on roster")
        vk = self.registry.verify_key_of(env.agent_id)
        try:
            vk.verify(env.signed_bytes(), env.signature)
        except Exception:
            raise RejectedBallot("bad signature")
        prior = self.envelopes.setdefault(env.agent_id, [])
        entry = self._append(
            "ballot",
            {"agent_id": env.agent_id, "envelope_hash": env.envelope_hash, "sealed_sha256": sha256(env.sealed), "revote_index": len(prior)},
        )
        receipt = {
            "election_id": self.config.election_id,
            "envelope_hash": env.envelope_hash,
            "log_seq": entry.seq,
            "log_hash": entry.hash,
            "accepted_at": entry.ts,
            "verify_until": entry.ts + self.config.verification_window_s,
            "collector_signature": self.organiser.sign(canonical({"envelope_hash": env.envelope_hash, "log_seq": entry.seq, "log_hash": entry.hash})).hex(),
        }
        env.receipt = receipt
        prior.append(env)
        return receipt

    def individual_verify(self, agent_id: str, envelope_hash: str, now: Optional[float] = None) -> dict:
        """IVXV individual verification: within the window after casting, the
        voter's verification app confirms that the ballot the collector holds
        is the one that was cast. In IVXV this reveals the *choice* via the
        randomness in the QR code; here the sealed box is non-malleable, so
        confirming the exact ciphertext is in the log is equivalent."""
        now = time.time() if now is None else now
        for env in self.envelopes.get(agent_id, []):
            if env.envelope_hash == envelope_hash:
                r = env.receipt or {}
                ok_window = now <= r.get("verify_until", 0)
                ok_log = self.log[r["log_seq"]].payload["envelope_hash"] == envelope_hash
                return {"found": True, "in_window": ok_window, "in_log": ok_log, "log_seq": r["log_seq"]}
        return {"found": False, "in_window": False, "in_log": False}

    # ------------------------------------------------------------ processor
    def close(self) -> None:
        if self.stage is not Stage.OPEN:
            raise RuntimeError("not open")
        self.stage = Stage.CLOSED
        self._append("close", {"accepted_envelopes": sum(len(v) for v in self.envelopes.values()), "distinct_agents": len(self.envelopes)})

    def final_envelopes(self) -> Dict[str, Envelope]:
        """Re-vote rule (IVXV): the latest accepted envelope per voter counts."""
        return {aid: envs[-1] for aid, envs in self.envelopes.items() if envs}

    # ------------------------------------------------------ key application
    def decrypt(self, shares: Sequence[KeyShare]) -> Dict[str, Ballot]:
        if self.stage is not Stage.CLOSED:
            raise RuntimeError("close the election first")
        sk = recover_private_key(shares, self.config.threshold_k)
        if sk.public_key != self.public_key:
            raise RuntimeError("recovered key does not match election public key")
        self.recovered_sk = sk
        for aid, env in self.final_envelopes().items():
            try:
                b = Ballot.from_bytes(unseal(env.sealed, sk))
            except Exception as e:  # undecryptable or malformed
                self.invalid[aid] = f"undecryptable: {e}"
                continue
            if b.agent_id != aid or b.election_id != self.config.election_id:
                self.invalid[aid] = "inner/outer envelope mismatch"
                continue
            if b.choice not in self.config.choices:
                self.invalid[aid] = f"choice not in list: {b.choice!r}"
                continue
            self.decrypted[aid] = b
        self.stage = Stage.DECRYPTED
        # PoL2 transparency: publish the key so anyone can re-decrypt.
        self._append(
            "decrypt",
            {
                "published_private_key": bytes(sk).hex(),
                "shares_used": [s.index for s in shares[: self.config.threshold_k]],
                "valid": {aid: {"choice": b.choice, "rationale": b.rationale, "nonce": b.nonce} for aid, b in self.decrypted.items()},
                "invalid": dict(self.invalid),
            },
        )
        return self.decrypted

    # --------------------------------------------------------------- export
    def export_log(self) -> List[dict]:
        return [e.to_dict() for e in self.log]

    def export_envelopes(self) -> List[dict]:
        return [env.to_dict() for envs in self.envelopes.values() for env in envs]
