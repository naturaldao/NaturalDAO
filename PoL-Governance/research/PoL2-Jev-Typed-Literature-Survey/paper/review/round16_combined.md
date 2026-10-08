# Round 16: combined review (fidelity, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: the round-15 fix pass (D3′ per-arm counting, D1 and D5 stated in §3, App. D.1 `sec:certainty-detail`, abstract "low or very low") and the lead author's later choice to show the 4 Oct column "as given" (row 14 moderate^a). Items resolved in REVIEW.md or closed in earlier rounds are not re-raised.

**Inputs**

- Paper: sections/*.tex, main.log (84 pages, 0 errors, 0 undefined), arxiv_metadata.txt (abstract 1,909 characters), arxiv-submission.zip. The zip (16:56:44.9) is newer than the last section edit (16:56:34.8) and contains "moderate$^{a}$" and "Certainty is low or very low".
- Data: evidence_coding.csv, quality_appraisal.csv, evidence_coding_update_2026-10-08.csv, quality_appraisal_update_2026-10-08.csv, papers.csv, papers_update_2026-10-08.csv, zenodo_preprints.csv (authors).
- Review files: round15_combined.md, certainty_audit_2026-10-08.md, AUDIT.md (round-15 fix log and the lead-author note after it).
- Full texts: sc2/2609.33689.txt, fulltext/2609.24574.txt, update/arx2610.09188.txt, arx2610.07177.txt, arx2610.02267.txt, zen22904595.txt.
- Every row was re-derived with Python from the CSVs: design rating, preregistration, the `system` column, author overlaps across all coded studies, and the per-arm result. This file is the only one edited.

## Status of round-15 findings

| ID | Status | Note |
|---|---|---|
| R15-1 | FIXED | D3′ is in §3 l.119. Row 14 is rated on the hosted arms. arx33689's hosted arm (6/1/0, 0.143; "question-readers safe or within bound", Sec. VI-C and summary table) is counted as opposing, and this was checked in the full text. Residual problems are raised in R16-1 and R16-3. |
| R15-2 | FIXED | Row 11 is low on the main window, with zen22922769 as corroboration only. Now it is low, contested by arx02267's hosted arm. §1 l.35, §4.9 l.321, §7 l.14, the caption, tab:certchanges and the audit agree. |
| R15-3 | FIXED | §3 l.119 now states the rule. The steering and acceptance sentences in App. D.1 are corrected. A wording nit is raised in R16-5. |
| R15-4 | FIXED | §4.8 l.273 says "no finding reaches moderate certainty, and three are contested". Steering is dropped from tab:certchanges. The audit summary is corrected, and the row-4 decision is logged in AUDIT.md. |
| R15-5 | FIXED | D5 is in §3 l.123, with the sampling-error and opposite-direction clauses. l.394 and App. D.1 give 87.2% vs 86.2% and NDCG 0.630 vs 0.637 (difference 0.008, CI −0.007 to 0.022), checked at arx09188 l.355 and l.364–365. |
| R15-6 | FIXED | §4.9 keeps a three-sentence certainty summary (l.320–322). The row-by-row reasoning is in App. D.1. |

## Recomputed

**Reproduces under §3 as written (4 Oct as given / Main only / Now / contested / scope):** rows 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 and 15 match tab:keyfindings, tab:certchanges, App. D.1 and the audit.

- **D3′ is applied symmetrically on the rows checked.**
  - Open-only opposing studies do not contest. In row 1, arx07177 and arx06744 are not counted. In row 11, arx07177 and arx03324 are counted as corroboration only.
  - The contesting studies in rows 5 and 11 are all hosted or hosted arms: arx31142, checkpoint2026jev, the hosted arm of arx04985, and the hosted arm of arx02267.
  - The open S\* corroborates rows 4, 11 and 12 and does not raise them.
- **Author overlaps.** The only overlaps are those the audit names, plus arx29429/arx31142 (Yi Liu, Leo Yu Zhang), arx26532/arx28613 and arx00213 (Rafe & Das). None of these pairs falls in the same row or clause.
- **Row 14** reproduces as stated, given the studies the audit counts: 4 hosted S support it, and an opposing S\* lowers it to very low^c. Main only is very low^c, and 4 Oct as given is moderate. The study set is incomplete, however (R16-1).
- **Row 2** does not reproduce (R16-1).

**Consistency (task 3).** Each of the following says "low or very low" or "no finding reaches moderate", and none mentions "moderate" or "two findings":
- abstract and metadata;
- §1 l.34–35;
- G2 box l.61 and G6 box l.206;
- §4.8 l.273 and §4.9 l.320–322;
- §6 l.38 ("most elements", which refers to design elements and is acceptable);
- §7 l.12–15 and §8 l.7.

**Spot-check of 6 changed sentences.** All 6 are correct:
- App. D.1 / l.394, arx09188: 86.2% vs 87.2% on 500 pairs; 0.6371 vs 0.6295; +0.008 [−0.007, 0.022].
- App. D.1, arx07177: 0.923–1.000 escalated; Qwen3-32B 0.615–0.868.
- App. D.1 / l.392, arx02267: 4.3%; τ=0.05 costs 4.7% more; reviewer agreement 91.1%.
- App. D.1, zen22904595: −3.2 points, CI −7.7 to +1.2, 83.6% fewer tokens.
- l.227 / App. D.1, arx33689: 6/1/0 for Jev, 1/6/0 for Laya FT, 0.143, 0.801, ≥19 labels.
- App. D.1, arx03324: the cascade stays below Sol on Dynamic (.729 vs .897) and HateXplain (.763 vs .776).

## Findings

**R16-1 [major] The two threshold rows (2 and 14) are not rated on the same evidence. arx33689's hosted arm opposes row 14 but is ignored for row 2, and arx24574's preregistered threshold failure is not assessed for either row.**
- **Location:** tab:keyfindings rows 2 and 14; App. D.1 "Thresholds set in advance" and "Other findings" ("That fixed thresholds do not transfer … stay low: no study supporting the first … is preregistered"); audit rows 2 and 14.
- **Problem:**
  - (a) Row 14 counts arx33689's hosted arm as an opposing S\*. In that arm, Jev's gate was set in advance and carried over to changed question templates: 6 safe / 1 within bound / 0 violating, which the paper summarises as "safe or within bound". That is also a result against row 2's first clause, "fixed thresholds do not transfer". Rows 2 and 14 share their update support (arx03387, arx02267, zen22935043).
    - The audit gives row 2 as opposing "none" and does not mention arx33689.
    - Under §3 as written, clause 1 of row 2 has an opposing S\* that ranks above every supporting S. The row would therefore fall to **very low, contested**.
    - The ≥19-label floor at most supports clause 2 ("local fitting is needed"). The clause rule then takes the lower clause rating, so the row is still very low.
  - (b) arx24574 is a hosted S\* (G6, Sec. 4.4, full text l.580–679). Its preregistered routing hypothesis fixed a confidence threshold of 0.9 in advance, with a target accuracy of ≥0.85. The hypothesis failed: the median task reached 0.815 [0.691, 0.897], and 8 of 14 tasks missed the target. This is a threshold set in advance that missed its target.
    - The audit does not list it under row 14, either as counted or as not counted.
    - If it is counted, row 14 has an S\* behind it. Moderate then falls one level to **low^c** Now; main only stays very low^c.
    - It may also bear on row 2.
- **Fix:**
  - Decide arx33689's hosted arm for row 2, and arx24574's routing hypothesis for rows 2 and 14. Either count them, or state in App. D.1 and the audit why each is out of scope.
  - Re-rate both rows. Then update the table, tab:certchanges, §3 l.128 ("one finding rises … three are newly contested"), §7 l.14 and the audit summary.
  - The abstract's "low or very low" holds in every outcome.

**R16-2 [minor] Three places still say that per-arm counting is applied to the 4 Oct column, but the table shows the rating as given.**
- **Location:** §3 l.128 ("is applied to both columns"); App. D.1 l.50 ("it is applied to the 4~October column as well"); certainty_audit (the "4 Oct" column of row 14 is "very low^a"; the Protocol-deviation bullet says "applied to both columns"; the Summary gives the 4 Oct counts per arm as 0 moderate, 9 low and 6 very low).
- **Problem:** After round 15, the lead author set the 4 Oct column of tab:keyfindings and tab:certchanges to the rating as given (row 14: moderate^a), and the captions say so. The three places above describe the earlier version. A reader of §3 will expect a 4 Oct column with no moderate in it.
- **Fix:**
  - In §3 and App. D.1: "The 4 October column shows the ratings as given that day; counted per system arm, one of them (note a) would have been very low."
  - In the audit: show row 14's 4 Oct as "moderate (very low per arm)", and give both counts in the Summary.

**R16-3 [minor] Note a, §3 and App. D.1 attribute the 4 Oct moderate to arx33689's open arm alone. Two other open-model studies were also needed, and they would have given moderate without arx33689.**
- **Location:** tab:keyfindings and tab:certchanges note a ("rested on the open-model arm of the network-control study"); §3 l.128 ("because a preregistered study was counted on the result of its open-model arm"); App. D.1 l.89.
- **Problem:**
  - The studies cited on 4 Oct were arx33401 (hosted), arx33689, arx33843 (open, preregistered S\*) and zen23041163 (open S).
  - Without arx33689, the earlier rule still gives moderate: three independent S, one of them S\* (arx33843).
  - Per-arm counting gives very low because all of the open evidence drops out, not only arx33689's arm.
- **Fix:** Use "rested on open-model evidence: the open arm of [arx33689] and two open-model studies [arx33843, zen23041163]", or equivalent wording.

**R16-4 [minor] Table row 11 lists two open-model studies as "opposing", which contradicts D3′ and the caption.**
- **Location:** tab:keyfindings row 11, "update, opposing: arx07177, arx02267, arx03324".
- **Problem:**
  - Both arx07177 and arx03324 are open-only (`system` = open). Under D3′ they "cannot … contest", and App. D.1 l.79 calls them "corroboration only".
  - The caption says that Sources lists "supporting studies, then opposing ones", with open-model studies "cited as corroboration". A reader of the table sees three opposing studies, when only arx02267's hosted arm contests.
  - Rows 4, 12 and 14 also mix open corroborating studies (zen22959854/zen23038928, zen22904595, arx33843/zen23041163/arx07177) in with the supporting studies, without a marker.
- **Fix:**
  - Give row 11 "update, opposing: arx02267; open, same direction: arx07177, arx03324".
  - Alternatively, add a marker for open-model studies to the caption and to the cells.

**R16-5 [nit] "Cannot by itself raise" in §3 l.119 reopens the ambiguity behind R15-3.**
- **Problem:** "By itself" suggests that open-model evidence could raise a rating when it is combined with hosted studies, which is the row-4 situation. The previous clause ("computed from hosted-model evidence alone") settles the question, but this one muddies it.
- **Fix:** Delete "by itself".

**R16-6 [nit] The G6 box says "a finding later studies contest" (l.206), plural.**
- **Problem:** Under D3′ only one in-scope study, arx02267's hosted arm, contests the finding. §1 l.35 correctly says "a study that contests one finding".
- **Fix:** Change it to "a finding a later study contests".

## Fresh pass (task 5)

- No new moderation risk. The build, zip and metadata are consistent.
- The disclosure of the protocol deviation is honest and appears in §3, §4.9, §7 and App. D.1.
- The remaining author-only items (author name placeholder) are already known and are not re-raised.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 1 | R16-1 |
| Minor | 3 | R16-2, R16-3, R16-4 |
| Nit | 2 | R16-5, R16-6 |

New major or minor problems remain: yes
