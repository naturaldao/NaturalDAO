# PoL2 × DAO: a lab for love-aligned, equal and verifiable AI governance

[简体中文](README.md) · **English**

This repository connects two things:

- **Proof of Love2 (PoL2)**, the foundational theory of [NaturalDAO](https://github.com/naturaldao/NaturalDAO): *what* good governance should be — Equal Connection, "promote love and restrain hate", the "neither love nor hate" state of absence, a verifiable decision chain, and people's rights to suggest and to question.
- **The DAO experiment of Sharma et al. (2026)**, *Scientific Reports* 16, 11792 ([independent re-analysis](https://github.com/shentonyan/dao-governance-replication)): *how* people actually voted with tokens on AI-model behaviour under quadratic vs ranked voting and equal vs 20/80 power.

Each relevant PoL2 clause is turned into a piece of code, a measurable quantity and a test (see [docs/concept-mapping.md](docs/concept-mapping.md), in Chinese). The question asked is:

> What changes about whose voice is heard, and whose choice wins, when an AI-governance DAO adds PoL2's Equal Connection and "promote love, restrain hate"?

The core is pure Python standard library; matplotlib is optional for figures.

## A PoL2 governance session

1. **Proposal** — every option is screened by the Ethical Alignment Protocol (EAP).
2. **Deliberation** — PAI enforces turn-taking; each message gets a typed *love / hate / absence* decision. Flagged messages receive a repair prompt and stay on record; the speaker keeps every right (persons are equal, behaviour is judged). Criticism and anger are not hate.
3. **Vote** — equal token budgets, quadratic voting (configurable).
4. **Questioning period** — anyone may question; every question needs an explanation.
5. **Decision** — with data sources, reasoning steps and ethical checks; **escalated to a human** instead if a question is unanswered, the winning option failed screening, or there is a tie.

Every step is appended to a SHA-256 hash chain; `pol2dao verify` detects any edit.

## Quick start

```bash
pip install -e ".[dev]"
pol2dao demo                 # one full session, writes results/demo_decision_chain.jsonl
pol2dao verify results/demo_decision_chain.jsonl
pol2dao published            # equal-budget counterfactual from published numbers
pol2dao simulate --reps 1000 # agent-based comparison (~1 min)
pol2dao replay --data-dir path/to/osf-files   # per-ballot replay (OSF data not included)
pol2dao experiments --reps 1000   # E0–E13, all figures (~3 min)
pytest                         # 49 tests
```

Plug in any model (LLM, Jev-style typed-decision model, safety classifier) with `CallableJudge`; see [examples/custom_judge.py](examples/custom_judge.py).

## Results

**Real data.** Using only numbers published with the article, if everyone in the ranked 20/80 conditions had the same budget but split it the same way, the round-1 winner changes from option 2 to option 3 (exact for linear tallies); round 2 does not change. The margin is 0.021 with n = 25 — within sampling noise — and people might have split differently under equal budgets.

**Simulation** (a model, not evidence about people; assumptions in [docs/experiment-design.md](docs/experiment-design.md)). With an intense 20 % minority and a mildly opposed majority, strategic voters:

- Equal power is the largest lever when power sits with the majority (ranked 0.40 → 0.14, quadratic 0.66 → 0.21 probability that the minority's option wins).
- Quadratic beats ranked for intense preferences (0.66 vs 0.42).
- Under hostile talk, turn-taking restores the minority's share of the floor (0.12 → 0.20) and its win rate (0.34–0.40 → 0.67–0.68); EAP screening adds to it (→ 0.74–0.76) while missing ~20 % of hostile messages.
- **Without hostility, screening hurts the minority** (0.67–0.70 → 0.60–0.62): the baseline's false alarms land on the minority's criticisms. A safety valve's false alarms are paid by the people it is meant to protect — hence human review and local calibration.

**Fourteen further experiments (E0–E13)** with 14 new figures are documented in [docs/results.md](docs/results.md) (in Chinese; figures in English): mechanism decomposition, sensitivity heatmaps, preference intensity, pod size, judge operating point (AUROC × false-flag rate), judge bias against dissent, sybil attacks on quadratic voting, PAI-autonomous decisions vs voting (PoL2 ch. 7 Art. 2), voice dynamics, the NaturalDAO PoL-Governance pilot benchmark, a 96-sentence bilingual stress corpus, the published data, decision-chain cost, and the PoL2-Jev literature map. Run them all with `pol2dao experiments --reps 1000`.

Headline cross-experiment findings (model-based): equal power is the foundation; turn-taking is the strongest defence against hostility; screening pays only with hostility present, a judge with AUROC ≳ 0.85, and no bias against dissent; equality needs proof of personhood (sybils break quadratic voting); PAI autonomy is only as good as people's honesty in reporting.

## Limitations

- `LexiconJudge` is a transparent placeholder, not a validated classifier.
- "PAI" here is a deterministic procedure, not an AI. PoL2 ch. 7 Art. 2 envisages decisions without human voting; this lab keeps human votes as an input and compares the two in E7.
- `LexiconJudge.v1()` was written after reading the NaturalDAO pilot, so its pilot results are not blind.
- No proof-of-personhood; E6 shows equality depends on it.
- Ballots are recorded under pseudonyms; a real deployment needs a privacy design.

## Credits

PoL2: NaturalDAO (CC0-1.0). DAO experiment: Sharma, T. et al., *Sci. Rep.* 16, 11792 (2026), https://doi.org/10.1038/s41598-026-40180-8; data https://osf.io/q6snh/. Not affiliated with these authors. Code: MIT.
