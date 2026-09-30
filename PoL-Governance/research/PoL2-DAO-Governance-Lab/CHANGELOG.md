# Changelog

## 0.3.0 — 2026-09-29

House figure style.

- `plotstyle.py`: one module for palette, typography, export and plot helpers, following the rules of ChenLiu-1996/figures4papers (restated, not copied; CC BY-NC 4.0).
- All 17 figures migrated: semantic colours (blue = PoL2, red / grey = Sharma et al. baselines, green = variants), dashes + hatching for 20/80 power, 95 % CI bands and error bars, ↑/↓ metric direction, no in-figure footnotes, PNG 300 dpi + vector PDF.
- CI columns (`*_ci`) added to all simulation tables; point estimates unchanged.
- `CLAUDE.md` (project memory with the figure rules), `docs/figure-style.md`, `tests/test_figure_style.py`.
- 54 tests.

## 0.2.0 — 2026-09-29

Experiment suite and richer data.

- `pol2dao experiments`: 14 experiments E0–E13 with 14 new figures and 15 new tables, documented in `docs/results.md`.
- Simulation: pluggable flaggers (`lexicon_flagger`, synthetic `noisy_flagger` with chosen AUROC / false-flag rate / bias against dissent), sybil attacks, message traces; round-robin order is now shuffled per pod (was by group), ~2× faster.
- `autonomy.py`: PAI-autonomous decisions (PoLEn ch. 7 Art. 2) for comparison with voting.
- `LexiconJudge.v1()`: three PoL2-anchored categories (dignity ranking, conditional love, isolation).
- Data: 96-sentence bilingual EAP stress corpus; NaturalDAO PoL-Governance pilot and literature-survey data (CC0); rule-based winners added to the published token totals.
- Fonts: CJK fallback in figures when a CJK font is installed.
- 49 tests.

## 0.1.0 — 2026-09-29

First version.

- EAP screening (`eap.py`): love / hate / absence typed decisions, transparent lexicon baseline, pluggable judge, human-review band, local threshold fitting.
- Deliberation with round-robin moderation and voice-equality metrics.
- Linear / quadratic / plurality tallies; equal and 20/80 power; equal-budget counterfactual.
- Hash-chained decision chain with verification.
- End-to-end PoL2 governance session with questioning period and escalation.
- Agent-based simulation of the four Sharma et al. conditions, PoL2 and two ablations.
- Equal-budget counterfactual from published numbers and a per-ballot OSF replay.
