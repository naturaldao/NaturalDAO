# Iterative review protocol (v0.3)

Adapted from the `/fix-paper` loop of HuangPuStar/MetaInfer (`.claude/skills/fix-paper/SKILL.md`, branch `arxiv-paper`):
independent reviewer agents → numbered findings → one class of fix at a time → independent re-check → audit log.

## Files

| File | Role |
|------|------|
| `PROTOCOL.md` | this file |
| `round<N>_<lens>.md` | raw findings of one reviewer in round N (never edited after the round) |
| `REVIEW.md` | consolidated issue list; each fixed item gets `<!-- FIXED: date, how -->`, rejected items `<!-- REJECTED: reason -->` |
| `AUDIT.md` | one entry per fix: issue, before, rationale, after, re-check verdict, residual risk |
| `../bib_verification_log.tsv` | provenance of bibliographic entries |
| `../../data/evidence_coding.csv` | provenance of S/Q/N codes |

## Reviewer lenses

1. **fidelity-A** — §4 G1–G3: every number and claim checked against the cited full text.
2. **fidelity-B** — §4 G4–G7, §2, §5: same.
3. **consistency** — the same quantity everywhere (abstract, intro, §4, §5, §8, figures, tables, CSV, metadata); counts; clause numbers vs Appendix A; acronyms defined at first use; cross-references.
4. **argument** — over-claiming, balance, survey-method reporting (PRISMA 2020 / rapid-review items), whether the conditional thesis follows from the evidence, positionality.
5. **arxiv-pol2** — arXiv moderation risk (Oct 2025 CS review/position-paper rule, cs.CY), academic tone, presentation, and fidelity of every PoL2 clause quotation to NaturalDAO commit 5791ae3.

## Finding format

`NEW-<lens>-<n>` · location (`file:line`) · severity (major / minor / nit) · problem · evidence (quote source) · suggested fix.

## Exit condition

Two consecutive review rounds with no new major or minor findings. Then the build, `make_arxiv.py` clean-room compile and `make_metadata.py` must pass.

## Principle

Honesty over polish: when a source does not support a sentence, weaken or delete the sentence; never smooth a number.
