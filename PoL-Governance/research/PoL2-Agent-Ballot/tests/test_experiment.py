"""The sweep uses the decision logic without cryptography; this checks that
it yields exactly the same decisions as the full-protocol path for the same
random seed, so sweep figures are faithful to the protocol."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from sealed_vs_open import _agents, decide_fast, decide_protocol

from pol2_agent_ballot.identity import AgentIdentity


def test_fast_and_protocol_paths_agree():
    org = AgentIdentity.generate("org")
    for seed in range(12):
        for sealed in (True, False):
            a1 = _agents(7, 0.7, 2, random.Random(seed), with_keys=True)
            a2 = _agents(7, 0.7, 2, random.Random(seed), with_keys=True)
            assert decide_protocol(a1, sealed, org) == decide_fast(a2, sealed)
