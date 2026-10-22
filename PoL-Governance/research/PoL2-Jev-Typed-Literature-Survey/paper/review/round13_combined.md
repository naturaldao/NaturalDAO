# Round 13: combined review (fidelity, consistency, argument, arXiv moderator)

Date: 2026-10-08. Scope: the round-12 fix pass (AUDIT.md, last two sections), the new symmetric certainty rule, and a fresh consistency pass. Items resolved in REVIEW.md are not re-raised.

**Inputs**

- Paper: main.tex, sections/*.tex, main.pdf (81 pp.), main.log, main.aux, arxiv-submission.zip (unpacked and compared with the working sources after stripping comments and paths; all identical), arxiv_metadata.txt.
- Data: evidence_coding.csv, quality_appraisal.csv, evidence_coding_update_2026-10-08.csv, quality_appraisal_update_2026-10-08.csv, coder_agreement.csv, excluded_records_update_2026-10-08.csv, search_rerun_2026-10-08.csv, counts.tex, counts_update.tex.
- Review files: CODEBOOK_v3.md, coding/adjudication_update.md, coding/docs_update_U4.md.
- Full texts (scratchpad): update/arx2610.03324, 03387, 06425, 07177; zen23179064.pdf; r2/jkf.md.
- Figures: fig_framework.pdf, fig_corpus.pdf, fig_prisma.pdf (text extracted).
- Recomputation was done with Python. This file is the only one edited.

## Status of round-12 findings

| ID | Status | Note |
|---|---|---|
| R12A-1 | FIXED, with residuals | The rule is in §3 l.118–120 and the table caption. It is applied to four rows. Coverage of the other rows is incomplete; see R13-1 to R13-4. |
| R12A-2 | FIXED | The "update:" list is arx03387, arx02267 and arx04985. §4.9 l.321 names jkf87 as a partial re-run of 5 of 44 benchmarks; jkf.md confirms 5 legs. The rows were not merged; this was optional. |
| R12A-3 | FIXED | §1 l.42, §8 l.6 and the G4 box agree. The abstract uses a merged variant ("chosen inconsistently"), which no longer overreaches; see nit R13-10. |
| R12A-4 | FIXED | arx00831 G3 and arx35865 G3 are N in the CSV, App. B and fig_framework (G3 2/10/12). The main tally is 16/97/48. The main κ sample contains neither row, so κ 0.72 and the marginals are unaffected. §3 l.76–79 reworded. |
| R12A-5 | FIXED | Disclosed in §3 l.76. CODEBOOK_v3.md now contains rule (iv) and the independence condition. |
| R12A-6 | FIXED | §3 l.55 softened. "18 of the 103 (17%)" is in §3 and §7 (85 + 18 = 103; 17.5% rounds to 17%). The check is stated as direction-only, and the caveat on the label is given. |
| R12A-7 | FIXED | §3 l.73–74 and §7 l.84. 10 of 118 is 8%. |
| R12A-8 | FIXED | Text added. The figure "91" cannot be checked from released files; see nit R13-11. |
| R12A-9 | FIXED | §3 l.68 and App. E. |
| R12A-10 | FIXED | main.aux places tab:keyfindings on p. 24 and §4.9 on p. 25. |
| R12A-11 | FIXED | Item 16 is reworded. The ° marks still match the sentence in §6 l.41. |
| R12A-12 | NOT FIXED (accepted) | Optional; the author decides on length. |
| R12F-1 | FIXED | Same fix as R12A-1. |
| R12F-2 | FIXED | §4.9 l.396–397. zen22935043 is removed from the transfer row. |
| R12F-3 | FIXED | l.359. |
| R12F-4 | FIXED | l.364. |
| R12F-5 | FIXED | §3 l.67 and App. E l.73–76. 46 = 10+4+32; 32 = 1+31; 44 = 7+3+5+29; 29 = 4+25; +1 gives 26; 62 read, 57 retained. zen23187206 is now in the excluded-records file. |
| R12F-6 | FIXED | The App. C update table has 57 rows: 48 Coded, 6 Context, 2 Non-emp., 1 Excluded. |
| R12F-7 | FIXED | — |
| R12F-8 | FIXED | Checked against arx03324 App. I, l.2049: Sol .658→.729, .696→.721 and .730→.763, against Sol alone at .897/.682/.776. "Not to the frontier model's own level on two of three" is correct, and Luna gives .714. |
| R12F-9 | FIXED | — |
| R12F-10 | FIXED | — |
| R12F-11 | PARTLY | A reason is now given, but the source does not support it; see R13-6. |
| R12F-12 | FIXED | adjudication_update.md now says six S. The excluded-records file uses "re-screened" for every Zenodo row. AUDIT.md still lists this item as not harmonised; see R13-13. |

## Recomputed (no finding)

- **Main tallies.** 16/97/48 of 161. Stronger-design studies only: 7/45/27 of 79. Without Zenodo: 13/75/29 of 117. Zenodo is negative in 19 of 44 pairs and arXiv in 25 of 107. Dropping either set moves each share by 6 points or less.
- **Main comparators.** 76 pairs with a comparator: 23 better, 17 similar, 28 mixed, 8 worse. Of the negative codes, 14 have a comparator (6 worse, 4 similar, 3 mixed, 1 better) and 34 of 48 have none.
- **Box code counts G1–G7.** All match the CSV and fig_framework: 2/20/5, 1/0/9, 2/10/12, 3/29/13, 2/3/3, 1/23/4, 5/12/2. The G1 comparator figures (6 of 21, 10 mixed, 5 worse) and the G4 figures (9 better and 2 worse of 18) are correct.
- **tab:update.** Every cell matches:
  - update 12/92/14;
  - stronger-design 5/45/9 of 59;
  - in-window 5/28/3 (36 pairs, 18 sources);
  - main + in-window 21/125/51;
  - comparator column 15/10/27/7 with 59 none, per requirement as printed.
- **Sensitivity check.** G3 goes from N 12 / Q 10 to Q 14 / N 13, and G5 from a 3–3 tie to Q 4 / N 3. No other requirement's modal code changes.
- **§4.9 shares.** 14/118 = 12% against 48/161 = 30%. 9 of the 14 negative update codes have a comparator; the typed model is worse in 6, and 4 of those 6 are open-only (arx06744, arx07177, arx02586 G4, arx07327 G4). Across both sets, 39 of 62 negative codes lack a comparator.
- **counts_update.tex.** Sets 30/5/13; 27 arXiv and 21 Zenodo. κ, CI and 97 of 118 as in round 12.
- **fig_corpus (b).** The arXiv column is 107, Zenodo/alphaXiv 46 (44 + 2), grey 8. fig_prisma is unchanged and consistent.
- **Rule outcomes that recompute correctly from the appraisal files:**
  - Threshold-transfer row: the moderate^u rating holds. arx29429, arx00346, arx03387 and arx02267 are all independent, held-out, n+CI and stronger, and arx29429 is replicated by jkf87.
  - Sub-type row: low^u, not moderate. arx33401, arx07953, arx03324 and arx08675 are stronger, and none is preregistered.
  - Escalation fall: arx07177 is preregistered and stronger, equal to arx24574; the result is at the "preregistered 0.97 retention bar" (l.48–49).
  - Injection row: arx04985 is moderate, below arx28613 (preregistered), so the row is contested only.
  - Steering row stays low: the three independent stronger studies (arx31142, arx01834, arx01006) include none that is preregistered, and arx02048 is moderate.
- **"Often less accurate than the best LLMs" unchanged.** Correct.
  - arx03324 Table 4: Jev .826/.691/.738/.960 against Sol .897/.682/.776/.976. On MHS, Luna is .691, a tie. So Jev is below the best generative model on 3 of 4 datasets, and significantly on Dynamic only.
  - arx03935: 84.54 against 85.57.
- **arx03387.** 63.7% (artificial omission, k = 5) and 82.4% (DBpedia). Out-of-scope detection falls from 84.0 to 75.0 as k rises from 2 to 10.
- **Metadata and build.**
  - 81 pages and 7 figures, matching main.log.
  - The metadata abstract matches 00_abstract.tex.
  - The zip is newer than main.pdf and its sources match the working files.
- **Checklist.** 16 items. The ° marks are on items 5–8, 10–13 and 16.

## Findings

**R13-1 [minor] The "contested" half of the rule is not applied to the calibration row, and §4.9 misstates the rule.**
- **Location:** 04_evidence.tex l.328; tab:keyfindings, row "Well calibrated on familiar closed-choice tasks … calibration is local" (low).
- **Quote:** "The remaining findings gain no new preregistered or replicated stronger-design study in the same direction, and no opposing study of the required strength."
- **Problem:**
  - Under §3 l.118, an opposing study of *any* strength marks a finding contested, so "of the required strength" does not match the rule.
  - The calibration row has candidate opposing update studies on hosted Jev:
    - arx07953 (stronger, independent): ECE 14.9% on OLID and 33.2% on HateXplain without precedents; on held-out PluRule, overconfident by 12.2 points;
    - zen23221456 (stronger): Brier 0.283, against 0.250 for a constant predictor;
    - arx02267 (stronger): pooled ECE 0.143, and 0.477 on routing.
  - Their strongest is below arx24574, which is preregistered. Each therefore either marks the row contested^u or must be shown to be out of scope. No reason is given.
- **Fix:**
  - Reword l.328 to "… and no opposing study within the claim's scope".
  - Add one sentence giving the scope reason, e.g. "poor calibration on offensive-language, self-generated or routing tasks falls under 'calibration is local'".
  - Alternatively, mark the row "low; contested^u".

**R13-2 [minor] The upward rule is checked only at the moderate threshold, not for the three very-low rows.**
- **Location:** l.328, same sentence; tab:keyfindings, rows "Acceptance on agreement with an independently built rule …" (very low, arx02048 only, moderate) and "A separate sufficiency question …" (very low, arx01006).
- **Problem:**
  - Under §3 l.117, a very-low finding rises to low when a second study agrees and at least one of the studies is stronger. "No new preregistered or replicated stronger-design study" is the moderate test.
  - For the acceptance row, zen22904595 (stronger, independent; G6) points the same way: it accepted Laya at p ≥ 0.4 when a word match agreed, otherwise used a lexical fallback, and matched ReAct (−3.2 pp [−7.7, +1.2]) with 83.6% fewer input tokens.
  - zen23088660 (stronger; a fixed gate with a rule-based fallback) and arx07327 also bear on this row.
  - The escalation row counted an open-model study (arx07177), so excluding zen22904595 because it uses an open model would apply the scope test inconsistently.
  - For the sufficiency row, arx05107 (moderate) had hosted Jev reach 79.8% on evidence sufficiency. This is a partial match: it does not compare against confidence.
- **Fix:** State for each of these rows whether it rises to low^u. If it does not, give the reason, e.g. the disguised-attack clause is untested, or a lexical fallback is not "agreement with an independently built rule".

**R13-3 [minor] The injection row's "contested^u" is attributed to the update, but by the test used for arx04985 the main window already contests it.**
- **Location:** 03_method.tex l.120 ("Applied to the main-window evidence alone, this rule changes no rating"); tab:keyfindings row 5; 04_evidence.tex l.373.
- **Problem:**
  - arx04985 is counted as opposing although, in the paper's own words, it "used a different attack and benchmark" (l.373), namely a Jev-specific injection and a universal suffix.
  - Main-window sources report attacker success against hosted Jev under other attacks:
    - checkpoint2026jev (grey, weaker): "succeeded … in 25 of 27 runs", and marking content as untrusted made no difference (l.74);
    - arx30243 (weaker): 61.4% of decisions redirected to an attacker-chosen option by optimised additions;
    - arx31142 (stronger): an injected authority command flipped about 12%.
  - Each is below arx28613, which is preregistered, so under the same test they would already mark the row contested. "Changes no rating" is literally true, because a mark is not a rating, but "contested^u" credits the update with something the main evidence already shows.
- **Fix:** Do one of the following:
  - state the scope criterion that admits arx04985 and excludes these sources (e.g. single-call instruction injection on a fixed benchmark versus optimised context, which belongs to row 4);
  - mark the main-window cell "very low, contested" and change §3 l.120 to "changes no rating; it marks one finding contested".

**R13-4 [minor] The G6 box is unchanged although its claim's certainty fell, and the G2 box likewise for the contested clause.**
- **Location:** 04_evidence.tex l.206 (G6 box: "saved a quarter to over half of the cost without loss of accuracy in several studies"); l.401 ("The box stands"); l.61 (G2 box: "the one study coded as supporting found that injection rarely selected the attacker's target"); 05_synthesis.tex l.39 ("escalation can also work, when the next stage is a stronger reasoner").
- **Problem:**
  - §3 l.71 makes a box change depend on a change of direction *or rating* under the rules.
  - The escalation rating fell and the finding is now contested, yet the box reads as unqualified. The G5 box, by contrast, carries a pointer to §4.9 for a lesser change.
  - A reader of the boxes or §5 alone would not learn that this finding is now very low and contested.
- **Fix:** Add "(contested by later studies; \cref{sec:update})" to the escalation sentence in the G6 box, to the injection clause in the G2 box, and to §5 l.39. Alternatively, explain in §4.9 why a fall in rating leaves the box unchanged.

**R13-5 [minor] The range for "none" is incomplete, and the hosted-Jev statement overlooks one study.**
- **Location:** l.327 ("widens the range (7–82% across studies)"; "no new study of hosted Jev found 'I don't know' chosen reliably"); l.387 ("for 7–82% of the items without an answer across studies~\cite{arx39496,arx03387}").
- **Source:** arx06425, l.1247 (hosted jev-1.13.0, weaker): "Jev requests new contract candidates in 45/48 absent-candidate cases. It escalates only 4/120 infeasible forwarding instances."
- **Problem:**
  - For hosted Jev, the explicit no-valid-answer option was chosen in 3% to 94% of cases across studies. arx07327 (open) gives 28/30.
  - "7–82% across studies" cites two studies and understates the spread.
  - tab:keyfindings row 9 does not say "hosted", although §4.9 limits the row to hosted Jev.
- **Fix:**
  - Write "3–94% across studies \cite{arx39496,arx03387,arx06425}", or limit the range explicitly to "the two studies of an explicit NONE option".
  - Add "hosted \jev{}" to row 9, or to the reasoning in §4.9.

**R13-6 [minor] The reason given for not raising the option-names row is not supported by the source.**
- **Location:** l.329: "this analysis was not among its preregistered tests, so the rating stays low".
- **Source:** zen23179064 App. B.
  - "Every pre-registration is a dated note written before the corresponding calls."
  - The post-hoc analyses are listed under deviation 6, and the Table 1 label-set decomposition is not among them.
  - Deviation 4 says only that the zero-evidence-prior *framing* "failed its pre-declared kill criterion and was demoted".
  - §4.1: one 55% witness cuts the pull from +0.354 to +0.063.
- **Problem:**
  - The source does not say the label-set analysis was unregistered.
  - Without a valid exclusion, the rule as written gives moderate. arx26758, arx00346 and arx02586 (stronger, independent, same direction, and not mentioned in §4.9) plus zen23179064 (preregistered, stronger) make four independent stronger studies, at least one preregistered.
- **Fix:**
  - Give the source-supported scope reason. The pull is a prior under no evidence, toward an option word whose description was present; it is not a bound definition being overridden. The author's framing was demoted after failing its kill criterion.
  - Mention arx02586 in the same sentence.

**R13-7 [nit] arx09188 is cited as opposing the "stronger reasoner" claim, but the coding reads it as escalation to a peer.**
- **Location:** l.323, tab:keyfindings row 11 ("update, opposing: … arx09188"); coding/docs_update_U4.md ("G6 **confirms** 'escalating to peer models' gives little").
- **Problem:**
  - Qwen3-32B was less order-consistent and worse calibrated than Jev in the same study, so it is not clearly a "stronger reasoner".
  - The fall rests on arx07177 alone. Its own explanation of the failure ("confidence about a near-chance judge cannot gate", l.88) concerns a near-chance base evaluator, and §4.9 does not say why that is within the scope of "on readable judgements".
- **Fix:**
  - Cite arx09188 under the peer row, or justify "stronger".
  - Add one clause on why arx07177 is within the claim's scope.

**R13-8 [nit] The strength ranking leaves preregistered studies rated moderate unplaced.**
- **Location:** §3 l.118: "ranking preregistered above other stronger designs, then moderate, then weaker".
- **Problem:**
  - arx02048 (the sole source of row 12) and zen23225893 are preregistered but rated moderate, and the ranking does not say where they sit.
  - Two agreeing moderate studies fall into no level (neither very low nor low).
- **Fix:** Write "ranked by rating (stronger > moderate > weaker), with a preregistered study above a non-preregistered one of the same rating". Say that two moderate studies give very low.

**R13-9 [nit] The certainty cell formats differ between rows.**
- **Location:** tab:keyfindings: row 5 "very low; contested^u"; row 11 "low; very low, contested^u".
- **Fix:** Use "very low; very low, contested^u" for row 5.

**R13-10 [nit] The abstract and AUDIT.md differ on the "I don't know" wording.**
- **Location:** 00_abstract.tex l.6 ("'I don't know' or 'none' options are chosen inconsistently"). AUDIT.md says the abstract now reads "rarely chosen when correct".
- **Problem:** The abstract is acceptable, and plausibly shortened for the length limit, but the log is inaccurate.
- **Fix:** Correct the AUDIT entry.

**R13-11 [nit] "The largest returned 91" cannot be checked from the released files.**
- **Location:** §3 l.65; App. E l.73.
- **Problem:** rerun_arxiv_search_web.py prints the per-query counts (l.72) but does not save them. search_rerun_2026-10-08.csv holds only the 46 new records.
- **Fix:** Release the per-query count log.

**R13-12 [nit] The jkf87 replication is described two ways.**
- **Location:** l.36 ("re-ran five sub-experiments"); l.321 ("on 5 of its 44 benchmarks").
- **Problem:** The README calls these 5 legs, i.e. benchmarks.
- **Fix:** Use "five of its 44 benchmarks" in both places.

**R13-13 [nit] AUDIT.md residual notes are stale.**
- **Problem:**
  - The App. C caption now says "lists the 57 sources retained after full-text reading", so that residual is fixed.
  - The set label in excluded_records_update is now harmonised; only arXiv 2610.02516 is "late-indexed", which is correct.
- **Fix:** Update AUDIT.md.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | — |
| Minor | 6 | R13-1 to R13-6 |
| Nit | 7 | R13-7 to R13-13 |

New major or minor problems remain: yes
