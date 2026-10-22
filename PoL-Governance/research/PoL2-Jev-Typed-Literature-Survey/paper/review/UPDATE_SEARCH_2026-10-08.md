# Update search, 8 October 2026: protocol

Decision (user, 2026-10-08): run a supplementary search. The main analysis window (first public version dated 15 September to 1 October 2026) and every count, figure and certainty rating built on it stay unchanged. New records are screened, read and coded with the same rules and reported separately. An answer box or a certainty rating changes only when the update evidence changes its direction or its rating under the rules in §3.

## Searches (same queries as Appendix E)
- arXiv: the 18 queries via `scripts/rerun_arxiv_search.py`. Output: `data/search_rerun_2026-10-08.csv`. Supplementary source: the arXiv search page for "Jev", saved 8 October.
- Zenodo: the 11 queries via `scripts/rerun_zenodo_search.py`. Output: `data/search_rerun_zenodo_2026-10-08.csv`. Exclusions from the 1 October Zenodo screening were recorded only as counts, so records dated up to 1 October in this file are re-screened.
- Grey literature: the two community trackers (hanxiao.io/all-about-jev, pozapas/awesome-system-one-models) are checked for items added after 1 October.

## Sets
- **Post-window**: first public version dated 2 to 8 October 2026.
- **Late-indexed**: dated in the main window but not retrieved by the 1 or 4 October searches. These are flagged as such. They are reported with the update set, not added to the main tallies, and the paper states how many there were.

## Eligibility and coding
- Eligibility is the same as in §3 (typed decision model as object, component or direct comparator). Non-empirical items are recorded but not tallied.
- Each included source is read in full: arXiv HTML or PDF, and for Zenodo the main file via the records API.
- Coding uses `CODEBOOK_v3.md` (symmetric S/Q/N for detector use, rule (iv), comparator field, design rating). The rationale must give numbers and a locator.
- Every update pair is double-coded blind by a second AI coder. Disagreements are resolved by a third pass that has read both rationales. Agreement is reported separately from the main κ.
- Output: `data/evidence_coding_update_2026-10-08.csv` (same columns as `evidence_coding.csv`, plus `set` = post-window | late-indexed) and `data/excluded_records_update_2026-10-08.csv`.

## Reporting
- §3 gains a short "Update search" paragraph with counts.
- §4 gains a subsection "Update search (2 to 8 October)": per requirement, whether the new evidence confirms, qualifies or reverses the answer box, with the key numbers.
- Abstract, §1 and §8 change only if an answer box changes.
- Review loop: as in PROTOCOL.md, with exit after two consecutive rounds that have no new major or minor findings. The Chinese version is updated afterwards.
