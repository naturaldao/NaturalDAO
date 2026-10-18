# Related open-source projects

Repositories checked on 2026-10-18. Star counts are approximate and will
drift; licences are those shown on each repository page.

## Verifiable electronic voting

| Project | What it is | Use here |
|---|---|---|
| [valimised/ivxv](https://github.com/valimised/ivxv) | Source of the Estonian internet voting system, published for review (not developed in the open). Licence CC BY-NC-ND 3.0. | The design this protocol follows; read alongside [ivxv-notes.md](ivxv-notes.md). No code is reused. |
| [Election-Tech-Initiative/electionguard-python](https://github.com/Election-Tech-Initiative/electionguard-python) | Python implementation of the ElectionGuard specification: threshold ElGamal, guardian key ceremony, decryption proofs. MIT. | The upgrade path if ballots must stay secret after the close. |
| [Election-Tech-Initiative/electionguard](https://github.com/Election-Tech-Initiative/electionguard) | ElectionGuard specification and components. MIT. | Reference for record formats and key ceremonies. |
| [benadida/helios-server](https://github.com/benadida/helios-server) | Helios open-audit voting server. Apache-2.0. | A compact reference for a public bulletin board and homomorphic tally. |
| [glondu/belenios](https://github.com/glondu/belenios) | Mirror of Belenios (canonical home on GitLab). AGPL-3.0. | Credential-based eligibility, close to our signed roster. |
| [verificatum/verificatum-vmn](https://github.com/verificatum/verificatum-vmn) | Verificatum mix-net, as used by IVXV. | What a verifiable shuffle would add. |
| [vocdoni/vocdoni-node](https://github.com/vocdoni/vocdoni-node) | Vocdoni anonymous voting backend. AGPL-3.0. | A production alternative architecture. |

## Private voting for DAOs

| Project | What it is | Use here |
|---|---|---|
| [shutter-network/rolling-shutter](https://github.com/shutter-network/rolling-shutter) | Threshold encryption framework behind Shutter's shielded voting on Snapshot. MIT. | Same policy as this repository: votes sealed under a threshold key, revealed at the close. |
| [privacy-ethereum/maci](https://github.com/privacy-ethereum/maci) | Minimal Anti-Collusion Infrastructure. MIT. Archived in August 2026. | Re-voting by key change; permanent vote privacy. Reference only. |
| [semaphore-protocol/semaphore](https://github.com/semaphore-protocol/semaphore) | Anonymous group membership with nullifiers. MIT. | One agent, one vote without revealing which agent voted. |
| [snapshot-labs/snapshot-v1](https://github.com/snapshot-labs/snapshot-v1) | Snapshot off-chain voting interface. MIT. | The common "votes visible during voting" baseline. |
| [OpenZeppelin/openzeppelin-contracts](https://github.com/OpenZeppelin/openzeppelin-contracts) | Includes the Governor proposal, vote and timelock contracts. MIT. | Mapping event stages onto on-chain governance states. |

## Multi-agent language models: debate, voting, conformity

| Project | What it is | Use here |
|---|---|---|
| [lkaesberg/decision-protocols](https://github.com/lkaesberg/decision-protocols) | Code for Kaesberg et al., *Voting or Consensus?* (Findings of ACL 2025). Apache-2.0. | The closest prior study of which decision rule agents should use. |
| [Zhiyuan-Weng/BenchForm](https://github.com/Zhiyuan-Weng/BenchForm) | Conformity benchmark for LLMs (ICLR 2025). MIT. | Calibrating conformist behaviour; prompts for experiment 3. |
| [composable-models/llm_multiagent_debate](https://github.com/composable-models/llm_multiagent_debate) | Du et al. multiagent debate (ICML 2024). | The open, full-disclosure condition. |
| [Skytliang/Multi-Agents-Debate](https://github.com/Skytliang/Multi-Agents-Debate) | Liang et al. MAD with a judge. GPL-3.0. | Prompt-level remedy for loss of independence. |
| [dinobby/ReConcile](https://github.com/dinobby/ReConcile) | Round-table consensus among different LLMs. MIT. | Open-round analogue of our consensus mode. |
| [zjunlp/MachineSoM](https://github.com/zjunlp/MachineSoM) | Social-psychology study of LLM agent collaboration, with conformity analysis. MIT. | Conformity measurements to compare against. |
| [camel-ai/oasis](https://github.com/camel-ai/oasis) | Large-scale agent social simulation including herd behaviour. Apache-2.0. | Scaling cascade studies to many agents. |

## Social choice libraries

| Project | What it is | Use here |
|---|---|---|
| [voting-tools/pref_voting](https://github.com/voting-tools/pref_voting) | Preferential, graded and cardinal voting methods and axioms. MIT. | Replacing the binary tally with ranked rules for multi-option proposals. |
| [mggg/VoteKit](https://github.com/mggg/VoteKit) | Ballot generators, ranked-choice and STV. | Synthetic voter models alongside agents. |
| [COMSOC-Community/pabutools](https://github.com/COMSOC-Community/pabutools) | Participatory budgeting rules. GPL-3.0. | Budget allocation decisions in PoL2 welfare governance. |

## Cryptography used here

| Project | Licence | Role |
|---|---|---|
| [pyca/pynacl](https://github.com/pyca/pynacl) | Apache-2.0 | Ed25519, sealed boxes (Python library) |
| [jedisct1/libsodium](https://github.com/jedisct1/libsodium) | ISC | The library under PyNaCl |
| [dchest/tweetnacl-js](https://github.com/dchest/tweetnacl-js) | Unlicense | Ed25519 and box in the browser demo |
