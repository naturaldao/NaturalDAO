# Rounds 50–51: content review, response and rewrite (applied 2026-10-11)

The round-50/51 report (content review by eleven reviewers, response map R50-01…R51-14, deferred items D-01…D-08) was supplied by the author on 2026-10-11. On inspection the working tree did **not** contain any of the changes the report listed as applied (counts still S 28/Q 189/N 62; no "22 Choice", Recital 61, `raji2020closing`, Liberation Sans fallback). This round applies them, re-verifies each source-level claim against the PDFs, and rewrites the main text with the sci-paper-writing method (function per paragraph, one term per concept, evaluative words on numbers, ownership in the Conclusion). Pre-round snapshot: `Downloads/PoL2-Jev-v0.5-pre-r50-snapshot/`.

## Where the report was wrong or could not be reproduced

| Report item | Report said | Verified | Action |
|---|---|---|---|
| A6 / R50-06 | comparator agreement 119/144, κ = 0.75 | **120/148, κ = 0.72** (bootstrap 0.63–0.81) on the same 148 pairs as the S/Q/N κ; first coder's raw comparator vs blind second coder | printed the reproducible value, computed by `scripts/merge_all.py` (`\nCompKappa*`) |
| A4 / R50-04 | favourable endpoint is "the 83%-RewardBench pool" read as accuracy | 83% is the pool's **composition**; favourable figure is +0.93 pp pooled at 41.4% of the frontier fee; JudgeBench −0.74 pp [−2.22, 0.74], saves a third (arx26550 §8, p.14) | §5.6 rewritten accordingly |
| E-4 | arx01834's 94% depends on an *externally supplied* prediction | the prediction is **Jev's own**, from a separate call, written into the state by code (§4.3, p.6) | recode to Q kept (rule (i): separate step + 24/26 wrong-premise result both primary); reason corrected |
| M1 / R51-07 | three open-arm rows relabelled | **four** rows point against their finding: 1/arx06744, 1/arx07177, 11/arx03324, 11/arx07177 | all four set to `contradict-open`; finding 1 now also lists "open, against" |
| R50-16 | prior window "19–25 Sep" | arx32160 searched on 24 and 25 Sep 2026 (§5) | worded as "a search run on 24 and 25 September" |
| R50-16 | delta includes renaming tests | arx32160's checklist already has an option-name invariance item (T3) | delta stated as three-valued answers + sufficiency question, attack/leakage tests, re-validation over time |
| Stage 12 | `scripts/check.py` passes | fails only on README links into the parent NaturalDAO repo (`../../TASKS.md` etc.), which resolve in the published repo; README unchanged | not changed; noted |
| Stage 13 | stale dumps removed | `main_check.txt`, `main_r22.txt` still present | left for the author (not deleted) |

All other source claims (A1, A2, A3, A5, R51-09, R51-10, R51-11, R51-12) were confirmed against the PDFs by an independent agent: arx37647 p.9; arx00213 §3.1 p.9; arx33689 §VI-C p.7; zen22885291 §3.1; arx31142 Table 2; arx30243 §4.2; arx00346 §5.2 p.17 (values are per hundred; 97.2 is Jev's worst case); arx22664 §IV-D (scope checked at action admission); arx24881 App. A ("32,419 training responses").

## Applied

**Data and scripts**
- 8 recodes via `OVERRIDE` (`merge_coding.py` ×7, `merge_update.py` ×1, applied after agreement is computed so κ is unchanged): qin2026zhdecisionbench G3 Q→S; zen23032384 G4 N→Q; zen23047544 G4 S→Q; arx01834 G5 S→Q; arx00346, arx01079, arx02046, arx02048 G7 S→Q (adjudicated rule 7).
- Pooled: S 23 / Q 195 / N 61 of 279; G1 4/37/8, G2 1/0/10, G3 8/24/15, G4 5/57/15, G5 1/10/3, G6 2/42/7, G7 2/25/3. Per-requirement tallies now come from macros (`\nTallyOne`…`\nTallySeven`), so text and data cannot drift.
- New macros: comparator κ; G1 negative share 16.3% → 26.1% under stronger-design-only; rule-(iv) bound (G2 S1/Q10/N0, G3 S8/Q39/N0).
- `rate_certainty.py`: new direction `contradict-open` (never enters the rating). `--check` passes; ratings unchanged (0 moderate, 11 low, 4 very low; contested 2, 5, 11, 14).
- Six references added after Crossref check, provenance kept in a private verification log; `green2019principles` now cited.

**Text** (main): §1 detector/judge drawn by who checks the output, allow held to the same standard, terminology fixed (typed models; generative evaluators), prior-work delta corrected, artefacts named in contribution 2. §2 Interim Measures Art. 14(1) corrected; accountability literature paragraph; "three-valued construct" marked as our term. §3 state of absence ≠ insufficient information; calibration/abstention marked as our requirements; §5.4 paraphrase removed. §4 32 sampled / 30 comparable; denominators; comparator κ; moving codebook; same-author rule scoped to ratings. §5 A1–A5, A7, R51-05, R51-09/10, G7 cost-only rows, Q as residual category. §6 T2 distinction and carve-out scoping; Annex III 8(a), Recital 61, Art. 5(1)(c) input element, Annex III 1(c) + Art. 50(3), GDPR Arts. 2–3, DSA Art. 17(2) limits; design element 2 (action admission) and published hold period; verdict framed as evidential status, 96% figure moved out of the decisive list, precaution labelled. §7 new "typed interface is not isolated" paragraph crediting arx32160; κ "may misstate in either direction"; criteria of "what would change" stated as each necessary, 64-query budget justified, generative-comparator outcomes spelled out. §8 ownership sentence; precaution labelled. Abstract 1807/1920 chars.

**Online appendix**: denominators; 32/30 sample; comparator κ; moving-codebook and rule-(iv) notes; list of round-51 recodes; `contradict-open` convention; judgement row re-justified; verdict-table definition-swap range (to 97.2 per 100); 12.1% noise floor; "training responses".

**Figures** (figures4papers house style kept): Liberation Sans fallback in `f4p_style.py`; all seven figures regenerated; fig_fragility panel labels use the source's model names, AUROC, a neutral panel-(a) label and the 64-evaluation budget; fig_framework names segments too narrow for their number after the bar.

## Verification
- `merge_coding.py`, `merge_update.py`, `merge_all.py` → counts above.
- `rate_certainty.py --check` → CHECK PASSED.
- `paper/build.py` → main 34 pp., online appendix 27 pp., 0 errors / 0 undefined / 0 multiply-defined.
- `paper/make_arxiv.py` → 20 flat files, clean-room compile 0 errors, 34 pp.
- `review/check_invariants.py` against the snapshot: every changed number, citation and clause reference is one listed above.

## Still deferred (author decisions)
D-01 same-author tallies (stated, not collapsed); D-02 arx36965 "both"; D-03 arx08675 row wording; D-04 Chinese translation is two revisions behind; D-05 no human-verified codes; D-06 no version pin; D-07 oa:E earlier-release column unverifiable; D-08 original Chinese three-valued measurement. Also not done: B3–B5 minor fidelity items (G1–G7 omit some articles; T1 does not use §4.3.3.3; T3 charitable reading), Commission Feb 2025 guidelines not cited.
