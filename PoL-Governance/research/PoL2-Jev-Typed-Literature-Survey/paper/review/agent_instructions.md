# Instructions given to AI agents (v0.3, 2026-10-04)

All agents: Claude Opus 5.5 (Anthropic), launched as sub-agents of the drafting session, each with fresh context and read-only access to the paper except for its own output file. The full codebook is `CODEBOOK_v3.md`; the review protocol is `PROTOCOL.md`.

## Round-1 reviewers (five, in parallel)
- **fidelity-A / fidelity-B**: "strict academic reviewer, independent of the authors"; check every quantitative and substantive claim in an assigned part of the paper against the source full text (local PDF text, arXiv HTML, Zenodo files, grey URLs); report value, model/version, condition and hedge mismatches as `NEW-fid*-n [major|minor|nit]` with location, quote, source quote with locator and fix; list verified claims first.
- **consistency**: recompute every repeated number and count from the CSVs and figure scripts; check definitions, clause references against Appendix A, cross-references and the LaTeX log.
- **argument**: FAccT/AIES/ACM CSUR reviewer; assess whether conclusions follow, balance, PRISMA/rapid-review reporting, detector/judge consistency, fairness to PoL2, missing literature and structure; give an overall recommendation.
- **arxiv-pol2**: arXiv-moderation risk against arXiv's public policies (Oct-2025 CS review/position-paper rule), metadata and bundle checks; verify every PoL2 clause and quotation at commit 5791ae3.

## Search and screening
- **new-paper screener**: screen the 25 re-run candidates by title/abstract; read included papers in full from arXiv HTML; extract system, design, results with locators, limitations and proposed codes; write BibTeX.

## Coding
- **primary coders (four groups)**: read the codebook and the round-1 fidelity findings; for each document read the full text (Zenodo: the main file via the records API, not the description); appraise design; recode every axis row under the v3 codebook with system, Jev version, comparator and a one-sentence rationale with numbers and locator; never invent numbers.
- **blind second coder**: must not open the evidence coding, review files or paper sources; code a random sample of 32 document–requirement pairs from the full texts and the codebook alone.

## Round-2 reviewers (four, plus three verification sub-passes)
Same lenses as round 1, applied to v0.3, with an explicit instruction to check that each round-1 finding was fixed and to report unfixed ones; the argument reviewer also acted as an arXiv moderator and recomputed κ and tallies from the data files.
