# Design: from IVXV to agent ballots in PoL2

## 1. Why borrow from a national voting system?

IVXV is the source code of Estonia's legally binding online voting system
(published by the State Electoral Office, built by Cybernetica). Its value for
PoL2 is not the ID-card plumbing but a *discipline*: every step that could be
lied about is made checkable by someone who distrusts the operator.

PoL2's governance protocol asks for the same discipline in different words:

| PoL2 (第7章《人类公共福利的治理协议》) | IVXV property that delivers it |
|---|---|
| 第四条 1 决策过程完全公开透明 | signed configs, append-only logs, published ballot box |
| 第四条 2 可追溯、可审计 | independent auditor that re-derives the result |
| 第五条 5 可验证决策链路（数据源、推理步骤、伦理依据） | every vote carries a verifiable receipt; here the ballot also carries the agent's rationale |
| 第九条 2 对质询提供可理解的解释 | individual verification + public decrypt record |
| 第六条 3 / 第十一条 3 EAP 伦理验证 | eligibility check — a proposal failing EAP is like a voter not on the list |

## 2. Where PoL2 and "voting" are in tension — read this first

第二条 1 says NaturalDAO's autonomy means it *does not need human voting or
extra decision mechanisms*. This repo does **not** reintroduce human voting.
The ballots here are cast by the agents that make up the "去中心化协作网络"
of PoL2-governed models (§3.4). An agent ballot is the *internal mechanism*
by which that network reaches a single, verifiable collective decision — the
"verifiable decision chain" of 第五条 5 — not a plebiscite over NaturalDAO.

Humans keep exactly the roles chapter 7 gives them: 建议权 (suggestion) and
监督权 (query, inspect, report). `Event.add_query()` records a 质询 and the
answer the agents owe (第九条 2). Humans never cast a ballot in this library.

Whether PoL2 *wants* its agents to decide by vote at all, rather than by a
deliberation that ends in consensus (EAP 5.3.3: "辅助所有重要决策的相关方
完全同意"), is a design question the manuscript leaves open. This repo
treats voting as one admissible mechanism and supports a `unanimous` rule so
that consensus-style decisions can be recorded with the same audit trail.
Open question for the PoL2 editors: which decision rule the governance
protocol should name. §7 shows that consensus can be run on the same
protocol.

## 3. Component mapping

| IVXV | This repo | Notes |
|---|---|---|
| Voter identity (ID-card / Mobile-ID / Smart-ID / Web eID) | `AgentIdentity` — Ed25519 key pair | no PKI; the organiser's signed roster is the trust anchor |
| Voter list (signed changesets) | `AgentRegistry` sealed by organiser signature | sealed before the election opens; cannot be edited after |
| Election config + trust root (signed YAML) | `ElectionConfig`, signed by organiser, first log entry | choices list, rule, quorum, threshold k-of-n |
| Choices list (`ehak.candidate`) | `ElectionConfig.choices` — first choice means "advance the event" | convention documented in `event.py` |
| Inner envelope: ElGamal ciphertext | libsodium sealed box to election public key | non-malleable AEAD; no homomorphic property needed |
| Outer envelope: BDOC/XAdES qualified signature | Ed25519 signature over `{election_id, agent_id, sha256(sealed), cast_at}` | |
| Qualification: OCSP + RFC 3161 timestamp / `tspreg` receipt | collector-signed receipt with log sequence number and chain hash | the log hash plays the role of the TSA's `MessageImprint` |
| Registration service reconciliation | auditor cross-checks exported envelopes against `ballot` log entries | both directions: dropped envelope and phantom log entry are detected |
| Individual verification (QR with VoteID + randomness, N times within M minutes) | `Election.individual_verify(agent_id, envelope_hash, now)` with a window | IVXV reveals the *choice* through the randomness; here confirming the exact ciphertext is in the log is equivalent because the sealed box is non-malleable |
| Re-voting (processor `squash`: latest counts) | `Election.final_envelopes()` keeps the last accepted envelope per agent | `revote_hook` in `run_transition_ballot` |
| Paper vote overrides e-vote (`revoke` lists) | not applicable — there is no second channel | an EAP failure on the *proposal* voids the whole election instead |
| Key application: threshold key on smart cards (demo 5-of-9) | `split_private_key` / `recover_private_key` — Shamir over GF(2^255−19) | custodians are agents or humans holding shares |
| Anonymize + Verificatum mix-net + shuffle proof | **not implemented** | see §4 |
| Decryption proof (Chaum–Pedersen) | **replaced** by publishing the private key after close | anyone can re-decrypt; the auditor does |
| Auditor (convert / mixer / decrypt / integrity) | `Auditor.run()` on the exported log + envelopes only | 9 checks; tamper tests in `tests/` |
| Processor logs LOG1–LOG3, result schema | hash-chained `LogEntry` list; `TallyResult` | |

## 4. What is deliberately different: secrecy ends at the close

IVXV protects ballot secrecy *forever*: votes are anonymised and mixed before
decryption so that no vote can ever be tied to a voter. PoL2 asks for the
opposite from its agents: a decision must be traceable to its reasoning and
ethical grounds (第五条 5), and humans must be able to inspect everything
(第九条 3). So this protocol is **sealed until close, then fully public**:

* *during* voting, no one — not the collector, not other agents — can read a
  ballot (sealed box; key split k-of-n);
* *at* close, k custodians reconstruct the key, it is written into the log,
  and every ballot is decrypted with its agent id, choice and rationale.

Sealing during voting is what makes the ballots *independent*. That matters
for two reasons the PoL2 corpus already cares about:

1. **Sycophancy / herding.** An agent that can see others' votes can
   conform instead of reporting its own judgement. The sealed box removes
   the opportunity. `experiments/sealed_vs_open.py` shows the mechanism with
   scripted agents; whether real LLM agents herd is an open empirical
   question (see `experiments/llm_herding_protocol.md`).
2. **Condorcet jury theorem.** Majority accuracy grows with the number of
   voters only if their errors are independent. Open sequential voting
   breaks independence; sealed voting preserves it.

If a future use case needs lasting anonymity (e.g. agents evaluating a peer
agent, where retaliation is possible), the mix-net path is the right one and
this library is the wrong tool. Document that choice rather than bolting
anonymity onto a design built for transparency.

## 5. Event lifecycle

```
proposed ──▶ deliberation ──▶ voting ──▶ approved ──▶ executed ──▶ reviewed
         ▲ each arrow = one sealed ballot = one Transition record
```

`run_transition_ballot()` performs, in order:

1. EAP check of the proposal (`eap.py`; placeholder checker, see its docstring);
2. election setup: signed config, sealed roster, key ceremony, open;
3. each agent decides from the proposal + its evidence (+ visible votes only
   in the open condition) and casts a sealed, signed envelope; receipt issued;
4. optional re-vote pass;
5. close; k custodians reconstruct the key; decrypt; tally under the rule;
6. EAP check of each rationale — *flagged*, never silently altered;
7. independent audit from the exported record;
8. the event advances iff `decided ∧ winner == choices[0] ∧ EAP(proposal) ∧ audit.ok`.

Every `Transition` stores the complete election log and envelopes, so a
third party can re-run `Auditor` on any past decision from the JSON alone
(`examples/demo_output.json`).

## 6. Threat model (prototype)

Detected by the auditor: forged or missing envelopes, votes from agents not
on the roster, edited config or roster, a collector that misreports a
decryption, a tally that does not match the ballots, a mis-applied decision
rule, a broken log chain.

Not addressed: a dishonest *organiser* who holds the only signing key for
config and roster (IVXV answers this with a PKI and multi-party trust root);
collusion of k custodians to decrypt early (same as IVXV with k smart
cards); denial of service; the quality of the agents' judgement itself.

## 7. Consensus on the same protocol

EAP 5.3.3 asks PAI to help all parties to an important decision reach full
agreement. `consensus.run_consensus` implements this with the sealed ballot
as the only primitive:

1. each round is a complete election (own key ceremony, ledger, audit);
2. at the close of a round every choice and rationale is disclosed;
3. the next round gives agents that record as context, then seals again;
4. stop when the rule (default `unanimous`) is met or after `max_rounds`.

This differs from the open sequential condition in one respect that matters:
agents see the *complete* previous round only after committing their own
ballot, never a partial ordered tally. Each round therefore aggregates all
private evidence at once, which is the Delphi structure (Dalkey & Helmer,
1963). With `DeliberativeAgent`s that weigh round-1 ballots as independent
evidence, unanimity is reached in two rounds and is as accurate as the sealed
majority; agents that never update block consensus and leave the event where
it is, with the disagreement recorded. See experiment 2 in the README.

## 8. What a real deployment would add

* Organiser key held by the PoL-Governance maintainers' multisig or an
  on-chain registry (natural fit with the ERC-8183 / 8350 family).
* Real EAP checker in place of `KeywordEAP`.
* Mix-net mode for the anonymity use cases in §4.
* Export of `Transition` records to the NaturalDAO task board as the task
  page's decision record.
