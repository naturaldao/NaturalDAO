"""Verifiable decision chain: an append-only, hash-linked JSON log.

PoL2 grounding (PoLEn ch. 7): Art. 4 openness and traceability, Art. 5.5
"verifiable decision chain, including data sources, reasoning steps and
ethical foundations", Art. 11.5 "all amended versions are permanently
archived".

Each entry stores the SHA-256 of the previous entry, so editing or removing
any past entry breaks :meth:`DecisionChain.verify`. This is chain-agnostic: the
head hash can be anchored on any public blockchain or timestamping service,
but nothing here talks to a network.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

GENESIS = "0" * 64


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Entry:
    index: int
    time: str
    kind: str
    payload: dict
    prev_hash: str
    hash: str

    def body(self) -> dict:
        return {"index": self.index, "time": self.time, "kind": self.kind,
                "payload": self.payload, "prev_hash": self.prev_hash}

    def to_dict(self) -> dict:
        return {**self.body(), "hash": self.hash}


def _digest(body: dict) -> str:
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


class DecisionChain:
    def __init__(self, clock: Callable[[], str] = _utc_now) -> None:
        self._entries: list[Entry] = []
        self._clock = clock

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[Entry]:
        return iter(self._entries)

    @property
    def head(self) -> str:
        return self._entries[-1].hash if self._entries else GENESIS

    def append(self, kind: str, payload: dict) -> Entry:
        # Round-trip through JSON so the stored payload is exactly what is hashed.
        payload = json.loads(canonical(payload))
        body = {"index": len(self._entries), "time": self._clock(), "kind": kind,
                "payload": payload, "prev_hash": self.head}
        entry = Entry(**body, hash=_digest(body))
        self._entries.append(entry)
        return entry

    def of_kind(self, kind: str) -> list[Entry]:
        return [e for e in self._entries if e.kind == kind]

    def verify(self) -> tuple[bool, int | None]:
        """(True, None) if intact, else (False, index of the first bad entry)."""
        prev = GENESIS
        for i, e in enumerate(self._entries):
            if e.index != i or e.prev_hash != prev or _digest(e.body()) != e.hash:
                return False, i
            prev = e.hash
        return True, None

    def to_jsonl(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for e in self._entries:
                f.write(canonical(e.to_dict()) + "\n")
        return path

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "DecisionChain":
        chain = cls()
        with Path(path).open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    chain._entries.append(Entry(**json.loads(line)))
        return chain
