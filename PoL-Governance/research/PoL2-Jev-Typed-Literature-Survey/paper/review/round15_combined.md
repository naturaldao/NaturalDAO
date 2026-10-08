# Round 15: combined review (fidelity, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: the round-14 fix pass (lead-author decisions D1–D5) and the lead author's later lowering of row 4 (steering) to low under D3. Items resolved in REVIEW.md or closed in earlier rounds are not re-raised.

**Inputs**

- Paper: sections/*.tex, main.log (84 pages, 0 errors), arxiv_metadata.txt, arxiv-submission.zip. The zip, PDF and metadata (16:36:58) are newer than the last section edit (16:36:48). The zip's 04_evidence.tex contains the row-4 "stays low" text.
- Data: evidence_coding.csv, quality_appraisal.csv, evidence_coding_update_2026-10-08.csv, quality_appraisal_update_2026-10-08.csv, papers.csv, papers_update_2026-10-08.csv, zenodo_preprints.csv (authors).
- Review files: round14_combined.md, certainty_audit_2026-10-08.md, AUDIT.md (round-14 fix log).
- Full texts (scratchpad): sc2/2609.33689.txt; update/arx2610.07177.txt, arx2610.09188.txt, arx2610.10321.txt, zen22935043.txt.
- Every row was re-derived with Python from the CSVs: design rating, preregistration, independence, the `system` column and authors. This file is the only one edited.

## Status of round-14 findings

| ID | Status | Note |
|---|---|---|
| R14-1 | FIXED | arx33689 is now counted as supporting on its primary result (D2). §4.9 l.334 describes it accurately; checked in the full text: Laya FT 1/6/0, Jev 6/1/0, 0.143, ≥19 labels, 0.801. arx00346 is excluded with a stated reason (l.335). A residual conflict with D3 is raised in R15-1. |
| R14-2 | FIXED | §3 l.118 defines independent replication (D1). jkf87 is called a reproduction (G1 l.36, §4.9 l.329, §7 l.15 and l.46). Rows 1 and 2 are low. |
| R14-3 | PARTLY | The scope column, the caption sentence and the same-author rule (§3 l.118–119) are in place. The rule that open-model studies "cannot raise" a rating is applied to row 4 but is not stated in §3 and is not applied to rows 11, 12 or 14 (R15-1 to R15-3). |
| R14-4 | FIXED | l.336–337. ECEs 0.020, 0.091 and 0.089 checked in zen22935043. "14 of 15" checked in arx10321: the identity map was ineligible for every factor except vehicle defects. |
| R14-5 | FIXED | §3 l.71 and l.126–127, §4.9 l.320, §7 l.12 and App. D (paragraph and tab:certchanges). The disclosure is clear and not overstated. One stale row in tab:certchanges is raised in R15-4. |
| R14-6 | FIXED | The criterion is stated in §4.9 l.323. It appears there only, not in §3 (see R15-5). |
| R14-7 | FIXED | Separate "4 Oct" and "Now" columns; ^c and ^j are defined. |
| R14-8 | FIXED | §3 l.124 marks row 15 as descriptive. zen22885291 is dropped from row 13. |
| R14-9 | FIXED / no change needed | Now: 1 moderate, 10 low, 4 very low. "Certainty is mostly low" holds, and the metadata matches the abstract (1,916 characters). |

## Recomputed

**Rows that reproduce under §3 as written and as applied to row 4:** 1, 2, 3, 5, 6, 7, 8, 9, 10, 13 and 15. Their 4 Oct, Now and contested marks match the table and the audit.

**Row 4.** The audit table's "Now" is low, which matches tab:keyfindings. Row 4 is "both", but its preregistered support is open-only (the Alkhubaizi pair, one author). The hosted studies arx31142, arx01834 and arx01006 are three S, none of them S\*, which gives low.

**Row 11.**
- Hosted support: arx26550 (S) and arx24574 (S\*), plus arx02046 (W). That is two independent S.
- Moderate depends on the open study zen22922769. With "open studies cannot raise", as applied to row 4, the main-window rating is **low**, not moderate.
- Now: low, contested. Hosted arx02267 (S) opposes and ranks below S\*, so the rating does not fall. This matches the table.

**Row 14.**
- Hosted S: arx33401, arx03387, zen22935043 and arx02267. None is preregistered.
- The only S\* is arx33689. Its support comes from the open fine-tuned Laya arm. The hosted Jev arm was 6 safe / 1 within bound / 0 violating (§VI-C).
- See R15-1.

**Spot-check of 8 changed sentences.** All 8 are correct:
- l.324: 92–100%; Qwen3-32B accuracy 0.615–0.868.
- l.326: 87.2% vs 86.2%; NDCG 0.6295 vs 0.6371.
- l.227 and l.334: arx33689 figures.
- l.335: arx00346 realised risk 0.049, bound 0.066.
- l.336: arx10321, 14 of 15.
- l.337: zen22935043.
- l.325: arx02267, 4.3%.
- l.36 and l.329: jkf87, 5 of 44 benchmarks, the authors' code and data.

One wording nit is raised in R15-5.

## Findings

**R15-1 [major] Row 14's only moderate rating rests on preregistered support that comes from an open-model arm. That is the same kind of support D3 refused for row 4.**
- **Location:** tab:keyfindings row 14; §4.9 l.333–334; §7 l.13 ("One finding reaches moderate certainty … which a preregistered study … supports"); audit row 14.
- **Problem:**
  - The four hosted S studies for row 14 give low, because none is preregistered.
  - Moderate needs arx33689 as S\*. In that study, the gate exceeding α on 6 of 7 changed templates is fine-tuned Laya's. Hosted Jev's preregistered outcome was 6 safe / 1 within bound / 0 violating.
  - Row 4 was lowered because preregistered support existed only for open models. Treating row 14 differently is not uniform. It also turns on whether a "both" study is counted whole (D2) or by arm (D3), and §3 does not say which.
- **Fix:** Choose one of the following:
  - (a) State in §3 that a study testing hosted and open models counts as a hosted-model study on its primary result. Then add to §4.9 l.334 and §7 l.13 that the preregistered support is from the open-model arm, and that Jev's arm held on 6 of 7 with none violating. Explain why this differs from row 4.
  - (b) Rate row 14 low. Then nothing reaches moderate, and §3 l.127, §4.8, §7 l.13, App. D and the audit change accordingly. The abstract's "mostly low" still holds.

**R15-2 [major] Under D3 as applied to row 4, escalation (row 11) is low on the main-window studies, not moderate, so the claim that the update lowered one rating does not reproduce.**
- **Location:**
  - §1 l.35 ("lowered the certainty of one finding below its main-window rating");
  - §4.9 l.321–322;
  - l.415;
  - §7 l.14;
  - keyfindings caption ("on main-window studies alone only escalation differs (moderate)");
  - tab:certchanges ("Main only" moderate);
  - audit row 11 and Summary.
- **Problem:**
  - The main-window moderate needs the open study zen22922769 (S\*), because hosted Jev has only arx26550 and arx24574.
  - Applied uniformly, D3 makes the main-window rating low. The update then changes no rating and only adds the contested mark.
  - l.324 also leans on the open arx07177 S\* as the opposing study "as strong as the strongest". Only the hosted arx02267 is in scope as the primary opposer.
- **Fix:**
  - Change the main-window rating for row 11 to low.
  - Reword §1 l.35, §4.9 l.321–322, l.415 and §7 l.14 to say that the update leaves every rating unchanged and adds the opposing studies that make escalation contested. Fix the caption, App. D and the audit to match.
  - Alternatively, state a principled reason why open S\* raises row 11 but not row 4.

**R15-3 [minor] D3's "open-model studies cannot raise a rating" is not in §3, and two sentences contradict it.**
- **Location:** §3 l.119 and the keyfindings caption say only "count … only as corroboration of a hosted-model study". §4.9 l.330 says "only corroborate a finding about hosted \jev{} and do not raise its rating (§3)". l.341 says zen22904595 (open) "would raise the first clause to low".
- **Problem:**
  - Read literally, l.119 lets row 4's open S\* count, because hosted studies point the same way, and that gives moderate. The rule applied to row 4 is stricter than the rule stated.
  - l.330 also calls row 4 a hosted finding, but its scope is "both".
  - l.341 applies the opposite reading to row 12. The rating is unaffected, because clause (b) is very low.
- **Fix:**
  - Add to §3 l.119: "they cannot by themselves raise a rating above what the hosted-model studies give."
  - Change l.330 to "a finding about typed models generally".
  - Change l.341 to "would corroborate the first clause, but cannot raise it".

**R15-4 [minor] Counts are stale after row 4 was lowered.**
- **Location:**
  - §4.8 l.273: "two findings reach moderate certainty" (now one).
  - certainty_audit Summary: "Now: 2 moderate (rows 4 and 14), 9 low" (now 1 and 10). The "Main only" column gives row 4 as moderate, against D3.
  - tab:certchanges: lists steering (low / moderate / low), although its caption and App. D l.48 say it lists findings whose rating "differs from 4 October", and 4 Oct = Now for row 4.
  - Caption: says only escalation differs on main-window studies, while App. D and the audit also show steering.
  - AUDIT.md round-14 log: still has "Row 4 … -> moderate", "Now 2 moderate, 9 low" and "4 low->moderate". It has no entry for the lead author's lowering.
- **Fix:**
  - Change l.273 to "one finding reaches moderate certainty".
  - Drop the steering row from tab:certchanges, or relabel the table.
  - Correct the audit Summary and the main-only column.
  - Append a log entry for the row-4 decision.

**R15-5 [nit] D5 is stated only in §4.9, and l.413 overstates it.**
- **Location:** §4.9 l.323; l.413: "Qwen3-32B, which was no more accurate than \jev{} on that task".
- **Source:** arx09188 l.355: Jev 86.2%, Qwen 87.2% human agreement; l.364: NDCG 0.6371 vs 0.6295.
- **Problem:**
  - On agreement, Qwen was 1 point more accurate. As written, with no margin, D5 would make it stronger. "Peer" is defensible only with a margin or a test.
  - D1–D4 are in §3, but D5 is not.
- **Fix:**
  - Move D5 to §3 with "materially (beyond sampling error)".
  - Change l.413 to "about as accurate as \jev{} (agreement 87.2% vs 86.2%, NDCG lower)".

**R15-6 [minor] §4.9 is out of proportion, and its certainty bookkeeping belongs in an appendix.**
- **Location:** §4.9 is l.308–422, 114 of the 422 lines of §4 (27%), for a supplementary update. Lines 320–341 are a row-by-row justification of certainty ratings, including the review-round history, that is already in App. D and the audit.
- **Problem:**
  - A cs.CY referee will read §4.9 as process noise in an 84-page paper whose main argument is in §2b–§6.
  - The length also places the rating disputes in the main text, where the certainty table is meant to stand alone.
- **Fix:** Keep 3–4 sentences in §4.9: no box reversed; one box qualified; the deviation, with a pointer to App. D; and contested escalation. Move l.321–341 into App. D next to tab:certchanges. This should save about 1–1.5 pages and leaves the abstract unaffected.

## Consistency check (no further finding)

The following agree with the final ratings and with each other: the abstract ("mostly low"), the metadata, §1 l.34, the G2 box (l.61), the G6 box (l.206), §5 l.39, §6 l.38, §7 l.15 and §8 l.7. The exceptions are those named in R15-2 and R15-4. The protocol deviation is disclosed in §3, §4.9, §7 and App. D without overstating it.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 2 | R15-1, R15-2 |
| Minor | 3 | R15-3, R15-4, R15-6 |
| Nit | 1 | R15-5 |

New major or minor problems remain: yes
