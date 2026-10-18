# Changelog

## 0.4.0 — 2026-10-18

- Experiment 3 run: Claude Haiku 5.5, 40 proposals × 7 agents × 2 conditions
  (560 ballots, all audited). Sealed and open both 37/40, equal to the
  evidence ceiling; 2/280 open ballots against own evidence, only at visible
  leads of 5–6; 8 invalid open ballots, all under a visible lead of 2–5
  against the agent, none able to change a decision. Logs, analysis and
  figure committed.
- `experiments/analyze_llm_herding.py`: conformity curve by visible lead,
  evidence ceiling, paired bootstrap, invalid-ballot sensitivity.
- `agents.parse_choice`: tolerant reply parsing (the strict parser of 0.3
  is the likely cause of the invalid ballots); raw replies of invalid
  ballots are now logged.
- `llm_herding.py`: Anthropic personal keys (`LLM_WORKSPACE_ID`), automatic
  fallback when a model rejects `temperature`, retries for flaky networks,
  preflight checks, progress output.
- Demo site: language-model results section.

## 0.3.0 — 2026-10-18

- `theory.py`: exact results for every experiment (Condorcet sum, dynamic
  programme for the sequential cascade, closed form for consensus rounds);
  tests check them against brute-force enumeration and the simulator.
- Experiment 1 sweeps rerun with 10,000 runs per point and an independent
  seed per point (0.2.0 reused one seed across points, which correlated
  their sampling errors). Exact values shown in every figure.
- Experiment 3 (`experiments/llm_herding.py`): runnable test of herding among
  language-model agents against any OpenAI-compatible endpoint, paired design
  with bootstrap interval; mock backend for offline checks.
- `docs/related-work.md` (42 references, `docs/references.bib`) and
  `docs/related-repos.md` (25 projects).
- New README with protocol diagram (`docs/assets/protocol.svg`); figures
  redrawn in one style by `experiments/make_figures.py`.

## 0.2.0 — 2026-10-18

- Consensus mode: `consensus.run_consensus` runs repeated sealed rounds with
  full disclosure between rounds until the decision rule is met.
  `DeliberativeAgent` added.
- Experiment 2 (`experiments/consensus_rounds.py`), 3,000 runs per setting.
- Experiment 1 rerun with 30,000 runs per condition through the full
  protocol; Wilson intervals; parameter sweeps over N and p; figures.
  The 300-run figures in 0.1.0 (0.937 vs 0.820) were within sampling noise of
  the 30,000-run estimates (0.903 vs 0.843), which supersede them.
- Live demo (`site/app.html`, built to `docs/index.html` for GitHub Pages):
  step-through visualisation of the protocol in the browser, with sealed,
  open and consensus modes and a dishonest-collector mode.
- README rewritten; Chinese README split out; CITATION.cff.

## 0.1.0 — 2026-10-18

- Initial protocol: identities and signed roster, sealed double envelope,
  Shamir k-of-n election key, hash-chained ledger with receipts, individual
  verification, re-voting, decision rules, independent auditor, EAP hook,
  event stages and human queries, sealed-vs-open experiment.
