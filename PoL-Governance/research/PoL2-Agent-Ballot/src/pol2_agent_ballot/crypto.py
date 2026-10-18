"""Cryptographic primitives.

IVXV encrypts each ballot with ElGamal under the election's public key, and
the private key is held by the election organiser's key application, split
with threshold secret sharing among several key holders. Decryption happens
only after anonymisation, and the key application emits proofs of correct
decryption that the auditor checks.

This prototype keeps the *shape* and simplifies the primitives:

* ballots are encrypted with a libsodium **sealed box** (X25519 + XSalsa20-
  Poly1305) to the election public key, so no single collector can read them
  before the close;
* the election private key is split with **Shamir secret sharing** over
  GF(2^255-19) among `n` custodians, `k` of whom must cooperate to reconstruct
  it;
* there is **no mix-net and no zero-knowledge proof**. Correct decryption is
  made checkable by a different route: after the close, the reconstructed key
  is published, so anyone can re-decrypt every sealed ballot themselves.
  This is acceptable only because agent ballots in PoL2 are *sealed until
  close, then public* (see docs/design.md §4). Do not use this module where
  ballot secrecy must survive the tally.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from nacl.public import PrivateKey, PublicKey, SealedBox

# 2^255 - 19, a prime; Shamir shares live in this field. X25519 private keys
# are 32 bytes, i.e. integers < 2^256; we reduce the key to the field by
# splitting it into two 128-bit halves (each < p), sharing each half.
_P = (1 << 255) - 19


# --------------------------------------------------------------------------
# Shamir secret sharing
# --------------------------------------------------------------------------
def _eval_poly(coeffs: Sequence[int], x: int) -> int:
    acc = 0
    for c in reversed(coeffs):
        acc = (acc * x + c) % _P
    return acc


def _split_int(secret: int, k: int, n: int) -> List[Tuple[int, int]]:
    if not (1 <= k <= n):
        raise ValueError("need 1 <= k <= n")
    if not (0 <= secret < _P):
        raise ValueError("secret out of field")
    coeffs = [secret] + [secrets.randbelow(_P) for _ in range(k - 1)]
    return [(x, _eval_poly(coeffs, x)) for x in range(1, n + 1)]


def _recover_int(shares: Sequence[Tuple[int, int]]) -> int:
    """Lagrange interpolation at x = 0."""
    total = 0
    for i, (xi, yi) in enumerate(shares):
        num, den = 1, 1
        for j, (xj, _) in enumerate(shares):
            if i == j:
                continue
            num = (num * (-xj)) % _P
            den = (den * (xi - xj)) % _P
        total = (total + yi * num * pow(den, _P - 2, _P)) % _P
    return total


@dataclass(frozen=True)
class KeyShare:
    """One custodian's share of the election private key."""

    index: int
    hi: int  # share of the high 128 bits
    lo: int  # share of the low 128 bits

    def to_dict(self) -> dict:
        return {"index": self.index, "hi": hex(self.hi), "lo": hex(self.lo)}

    @classmethod
    def from_dict(cls, d: dict) -> "KeyShare":
        return cls(int(d["index"]), int(d["hi"], 16), int(d["lo"], 16))


def split_private_key(key: PrivateKey, k: int, n: int) -> List[KeyShare]:
    raw = int.from_bytes(bytes(key), "big")
    hi, lo = raw >> 128, raw & ((1 << 128) - 1)
    hi_shares = _split_int(hi, k, n)
    lo_shares = _split_int(lo, k, n)
    return [KeyShare(x, h, l) for (x, h), (_, l) in zip(hi_shares, lo_shares)]


def recover_private_key(shares: Sequence[KeyShare], k: int) -> PrivateKey:
    if len(shares) < k:
        raise ValueError(f"need at least {k} shares, got {len(shares)}")
    use = list(shares)[:k]
    hi = _recover_int([(s.index, s.hi) for s in use])
    lo = _recover_int([(s.index, s.lo) for s in use])
    if hi >= (1 << 128) or lo >= (1 << 128):
        raise ValueError("shares are inconsistent (wrong key or corrupted share)")
    raw = (hi << 128) | lo
    return PrivateKey(raw.to_bytes(32, "big"))


# --------------------------------------------------------------------------
# Sealed ballots
# --------------------------------------------------------------------------
def generate_election_keypair() -> Tuple[PrivateKey, PublicKey]:
    sk = PrivateKey.generate()
    return sk, sk.public_key


def seal(plaintext: bytes, election_pk: PublicKey) -> bytes:
    return SealedBox(election_pk).encrypt(plaintext)


def unseal(ciphertext: bytes, election_sk: PrivateKey) -> bytes:
    return SealedBox(election_sk).decrypt(ciphertext)
