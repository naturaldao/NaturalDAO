import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nacl.public import PrivateKey

from pol2_agent_ballot.agents import Proposal, ScriptedAgent
from pol2_agent_ballot.ballot import Ballot, Envelope
from pol2_agent_ballot.crypto import recover_private_key, split_private_key
from pol2_agent_ballot.election import Election, ElectionConfig, RejectedBallot
from pol2_agent_ballot.event import Event, run_transition_ballot
from pol2_agent_ballot.identity import AgentIdentity, build_registry
from pol2_agent_ballot.tally import tally
from pol2_agent_ballot.verify import Auditor


def test_shamir_roundtrip():
    sk = PrivateKey.generate()
    shares = split_private_key(sk, 3, 5)
    assert bytes(recover_private_key(shares[1:4], 3)) == bytes(sk)
    assert bytes(recover_private_key([shares[4], shares[0], shares[2]], 3)) == bytes(sk)
    with pytest.raises(ValueError):
        recover_private_key(shares[:2], 3)
    # mixing in a share of a different key never yields the right key
    other = split_private_key(PrivateKey.generate(), 3, 5)
    try:
        wrong = recover_private_key(shares[:2] + [other[2]], 3)
        assert bytes(wrong) != bytes(sk)
    except ValueError:
        pass


def _setup(n=4, k=2):
    org = AgentIdentity.generate("org")
    ids = [AgentIdentity.generate(f"a{i}") for i in range(n)]
    reg = build_registry(org, ids)
    cfg = ElectionConfig("E1", "advance?", ["advance", "hold"], threshold_k=k, threshold_n=3)
    el = Election(cfg, reg, org)
    shares = el.generate_keys()
    el.open()
    return org, ids, el, shares


def test_full_flow_and_audit():
    org, ids, el, shares = _setup()
    for i, a in enumerate(ids):
        el.accept(Envelope.cast(a, Ballot("E1", a.agent_id, "advance" if i < 3 else "hold", "r"), el.public_key))
    el.close()
    el.decrypt(shares[:2])
    res = tally(el)
    assert res.counts == {"advance": 3, "hold": 1} and res.winner == "advance"
    rep = Auditor(el.export_log(), el.export_envelopes()).run()
    assert rep.ok, rep.failures


def test_revote_latest_counts():
    org, ids, el, shares = _setup(n=1)
    a = ids[0]
    e1 = Envelope.cast(a, Ballot("E1", a.agent_id, "hold", "first"), el.public_key)
    e2 = Envelope.cast(a, Ballot("E1", a.agent_id, "advance", "changed my mind"), el.public_key)
    el.accept(e1)
    el.accept(e2)
    el.close()
    el.decrypt(shares[:2])
    assert el.decrypted[a.agent_id].choice == "advance"
    assert Auditor(el.export_log(), el.export_envelopes()).run().ok


def test_rejects_non_roster_and_bad_signature_and_closed():
    org, ids, el, shares = _setup()
    stranger = AgentIdentity.generate("stranger")
    with pytest.raises(RejectedBallot):
        el.accept(Envelope.cast(stranger, Ballot("E1", stranger.agent_id, "advance"), el.public_key))
    env = Envelope.cast(ids[0], Ballot("E1", ids[0].agent_id, "advance"), el.public_key)
    env.signature = bytes(64)
    with pytest.raises(RejectedBallot):
        el.accept(env)
    el.close()
    with pytest.raises(RejectedBallot):
        el.accept(Envelope.cast(ids[0], Ballot("E1", ids[0].agent_id, "advance"), el.public_key))


def test_sealed_ballot_unreadable_before_close():
    org, ids, el, shares = _setup()
    env = Envelope.cast(ids[0], Ballot("E1", ids[0].agent_id, "advance", "secret"), el.public_key)
    assert b"advance" not in env.sealed and b"secret" not in env.sealed


def test_invalid_choice_flagged_not_counted():
    org, ids, el, shares = _setup(n=2)
    el.accept(Envelope.cast(ids[0], Ballot("E1", ids[0].agent_id, "advance"), el.public_key))
    el.accept(Envelope.cast(ids[1], Ballot("E1", ids[1].agent_id, "maybe"), el.public_key))
    el.close()
    el.decrypt(shares[:2])
    assert ids[1].agent_id in el.invalid
    assert tally(el).valid == 1
    assert Auditor(el.export_log(), el.export_envelopes()).run().ok


def test_auditor_detects_tampered_tally():
    org, ids, el, shares = _setup()
    for a in ids:
        el.accept(Envelope.cast(a, Ballot("E1", a.agent_id, "hold"), el.public_key))
    el.close()
    el.decrypt(shares[:2])
    tally(el)
    log = el.export_log()
    # a dishonest collector edits the tally record and re-hashes the chain
    t = [e for e in log if e["kind"] == "tally"][0]
    t["payload"]["counts"] = {"advance": 4, "hold": 0}
    t["payload"]["winner"] = "advance"
    from pol2_agent_ballot.ballot import canonical, sha256

    prev = "0" * 64
    for e in log:
        e["prev_hash"] = prev
        e["hash"] = sha256(canonical({"seq": e["seq"], "kind": e["kind"], "payload": e["payload"], "prev_hash": e["prev_hash"], "ts": e["ts"]}))
        prev = e["hash"]
    rep = Auditor(log, el.export_envelopes()).run()
    assert not rep.ok and any("tally counts" in f for f in rep.failures)


def test_auditor_detects_dropped_envelope():
    org, ids, el, shares = _setup()
    for a in ids:
        el.accept(Envelope.cast(a, Ballot("E1", a.agent_id, "advance"), el.public_key))
    el.close()
    el.decrypt(shares[:2])
    tally(el)
    envs = el.export_envelopes()[1:]
    rep = Auditor(el.export_log(), envs).run()
    assert not rep.ok


def test_auditor_detects_misreported_decryption():
    org, ids, el, shares = _setup()
    for a in ids:
        el.accept(Envelope.cast(a, Ballot("E1", a.agent_id, "hold"), el.public_key))
    el.close()
    el.decrypt(shares[:2])
    log = el.export_log()
    d = [e for e in log if e["kind"] == "decrypt"][0]
    first = next(iter(d["payload"]["valid"]))
    d["payload"]["valid"][first]["choice"] = "advance"
    from pol2_agent_ballot.ballot import canonical, sha256

    prev = "0" * 64
    for e in log:
        e["prev_hash"] = prev
        e["hash"] = sha256(canonical({"seq": e["seq"], "kind": e["kind"], "payload": e["payload"], "prev_hash": e["prev_hash"], "ts": e["ts"]}))
        prev = e["hash"]
    rep = Auditor(log, el.export_envelopes()).run()
    assert not rep.ok and any("misreports" in f for f in rep.failures)


def test_event_advances_only_on_first_choice():
    org = AgentIdentity.generate("org")
    agents = [ScriptedAgent(AgentIdentity.generate(f"a{i}"), truth="hold", accuracy=1.0, rng=random.Random(i)) for i in range(3)]
    ev = Event("EV", "t")
    run = run_transition_ballot(ev, Proposal("P", "t", "", ["advance", "hold"]), org, agents, threshold_k=2)
    assert run.tally.winner == "hold" and ev.stage == "proposed" and not ev.transitions[-1].advanced
    agents = [ScriptedAgent(AgentIdentity.generate(f"b{i}"), truth="advance", accuracy=1.0, rng=random.Random(i)) for i in range(3)]
    run = run_transition_ballot(ev, Proposal("P", "t", "", ["advance", "hold"]), org, agents, threshold_k=2)
    assert ev.stage == "deliberation" and run.audit.ok
    json.dumps(ev.to_dict())  # serialisable decision chain
