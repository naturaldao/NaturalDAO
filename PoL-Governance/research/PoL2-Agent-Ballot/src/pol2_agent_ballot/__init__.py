"""pol2-agent-ballot — an IVXV-inspired sealed-ballot protocol for deciding
whether a PoL2 / NaturalDAO event advances to its next stage.

The package is a research prototype. It borrows the *structure* of the
Estonian IVXV online voting system (double envelope, registration receipts,
individual verification, re-voting, threshold-protected tally, independent
audit) and applies it to votes cast by software agents rather than citizens.
It does **not** reproduce IVXV's mix-net or zero-knowledge shuffle proofs;
see docs/design.md for exactly what is and is not implemented.
"""

__version__ = "0.4.0"

from .identity import AgentIdentity, AgentRegistry
from .election import Election, ElectionConfig, Stage
from .ballot import Ballot, Envelope
from .tally import TallyResult
from .verify import Auditor, AuditReport
from .consensus import ConsensusResult, run_consensus
from . import theory

__all__ = [
    "AgentIdentity",
    "AgentRegistry",
    "Election",
    "ElectionConfig",
    "Stage",
    "Ballot",
    "Envelope",
    "TallyResult",
    "Auditor",
    "AuditReport",
    "ConsensusResult",
    "run_consensus",
    "theory",
]
