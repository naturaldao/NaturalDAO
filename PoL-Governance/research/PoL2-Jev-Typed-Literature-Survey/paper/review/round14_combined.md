# Round 14: combined review (fidelity, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: the round-13 fix pass, in particular the rewritten §3 certainty rule (03_method.tex l.115–123) and the re-rating of every row of tab:keyfindings (04_evidence.tex l.275–303; derivations in certainty_audit_2026-10-08.md). Items resolved in REVIEW.md or closed in round 13 are not re-raised.

**Inputs**

- Paper: main.tex, sections/*.tex, main.log (81 pages, 0 errors), arxiv_metadata.txt, arxiv-submission.zip (newer than main.pdf, which is newer than the edited sections).
- Data: evidence_coding.csv, quality_appraisal.csv, evidence_coding_update_2026-10-08.csv, quality_appraisal_update_2026-10-08.csv, grey_literature.csv, zenodo_preprints.csv (authors), search_rerun_2026-10-08_query_hits.csv.
- Review files: PROTOCOL.md, UPDATE_SEARCH_2026-10-08.md, round13_combined.md, certainty_audit_2026-10-08.md, AUDIT.md.
- Full texts (scratchpad): 33689.txt (arXiv 2609.33689 HTML), 2609.31142.txt, r2/jkf.md (jkf87 README).
- Every row was re-derived with Python from the CSVs. This file is the only one edited.

## Status of round-13 findings

| ID | Status | Note |
|---|---|---|
| R13-1 | FIXED | "of the required strength" is gone. §4.9 l.331 gives a scope reason for the calibration row. One new problem with that reason is raised in R14-4. |
| R13-2 | FIXED | §4.9 l.333–334 deal with the sufficiency row (arx05107 bears on clause 1 only) and the acceptance row (zen22904595 raises clause 1; the disguised-attack clause stays single-study). |
| R13-3 | FIXED | Row 5 now reads "very low, contested" in the main window. §4.9 l.324 and l.378 agree. |
| R13-4 | FIXED | The G2 box (l.61), the G6 box (l.206) and §5 l.39 now carry the contested qualifier. |
| R13-5 | FIXED | "3–94%" is correct: arx06425 gives 45/48 = 94% and 4/120 = 3%. Row 9 says "hosted \jev{}". |
| R13-6 | FIXED | §4.9 l.328 now gives a scope reason the source supports and names arx02586. |
| R13-7 | FIXED | arx09188 is out of the row. Its numbers are correct: order consistency 94.8 vs 90.6, ECE 0.081 vs 0.260. A residual is raised in R14-6. |
| R13-8 | FIXED | §3 l.117 and l.119. |
| R13-9 | FIXED | All cells use one format. Readability is raised in R14-7. |
| R13-10 | FIXED | The AUDIT.md round-13 entry corrects the round-12 entry. |
| R13-11 | FIXED | search_rerun_2026-10-08_query_hits.csv has 18 query rows plus a total row, with a maximum of 91 and 125 unique. |
| R13-12 | FIXED | G1 l.36 and §4.9 l.326 both say "five of its 44 benchmarks". |
| R13-13 | FIXED | — |

## Recomputed (no finding)

The rule as written in §3 (l.117–121) was re-applied to every row using all coded main-window and update studies.

| Row | Result |
|---|---|
| 3 | Low (main) and low^u. arx33401 is S; alphaRAG and arx02046 are W. |
| 5 | Very low, contested. Single supporting study, arx28613 (S\*). Opposing: arx31142 (S; command 10.1%, 88.8% of targeted flips on the target, checked in the full text) and checkpoint2026jev (W). Neither outranks S\*. |
| 6 | Low. Four S studies; none is preregistered. |
| 7 | Very low. |
| 9 | Low. |
| 10 | Very low. |
| 12 | Very low. |
| 13 | Low. See nit R14-8. |
| 11 | Moderate in the main window. arx26550 (S), arx24574 (S\*) and zen22922769 (S\*) are independent. With the update, low, contested: arx07177 (S\*) equals the strongest supporting study. |

These rows reproduce.

**Counts.** The main window has 4 moderate, 7 low and 4 very low ratings, with 2 contested. With the update: 3 moderate, 8 low, 4 very low. These match §3 l.122, §4.8 l.273, §4.9 l.319–320, §7 l.12–14 and the AUDIT line ("8 low, 4 very low, 3 moderate").

**Downstream text.** §1 l.34 ("low or very low"), §1 l.35, §5 l.39, §6 l.38 and §8 l.7 are consistent with the table. The abstract is unchanged and matches the metadata. On "mostly low", see nit R14-9.

**Spot-check of changed sentences.** 10 of 12 are correct:

1. arx07177 escalated 92–100% of items, on RewardBench, JudgeBench and HaluEval.
2. arx02267 cut cost by 4.3%.
3. arx03324 left the cascade below Sol on Dynamic and HateXplain, and above it on MHS: 2 of 3.
4. arx09188: order consistency and ECE as above.
5. arx31142: 10.1% and 88.8%.
6. arx06425: 45/48 and 4/120.
7. zen22904595: −3.2 [−7.7, +1.2] and 83.6% fewer tokens.
8. arx05107: 79.8%.
9. zen22922769: 60.8% of calls avoided, +0.5 [−2.5, +3.9].
10. §3 l.122: the before/after counts agree with the audit's "Change vs. 4 Oct" column.

The two that are not correct are §4.9 l.329 / §7 l.13 on arx33689 (R14-1) and §4.9 l.331, "none reports …" (R14-4).

## Findings

**R14-1 [major] arx33689 is not an opposing study for "thresholds set in advance miss error targets", so the row-14 fall and the contested mark do not reproduce.**
- **Location:**
  - tab:keyfindings row 14 ("opposing: arx33689 … low, contested");
  - 04_evidence.tex l.329: "the preregistered study that found a fixed gate held on changed question types";
  - 07_discussion.tex l.13;
  - G6 box l.206 ("(contested …)");
  - 03_method.tex l.122 ("lowers one from moderate to low");
  - certainty_audit row 14.
- **Source:** 2609.33689.
  - Abstract: "the fine-tuned typed encoder returned its training answer for 98–99.5% of changed questions, and its calibrated gate then acted wrongly on up to 80% of them, whereas the question-reading frameworks acted wrongly on at most 0.143 (Jev)…"
  - §VI-C: "The pre-registered outcome counts (safe / within the Proposition 2 bound / violating) at α = 0.05 were 6/1/0 for Jev, 4/3/0 for AnyJev L0 and 1/6/0 for Laya FT." Here "within bound" means the gate was above α but within α + d_TV.
  - Under the shift split, AnyJev's SLA gate reached 0.199, "about four times α".
  - §VI-B: "certifying action on any new decision type … requires ≥ 19 labels" of that type (CSV rationale).
- **Problem:**
  1. **Primary-result clause.** §3 l.118 says a study with results in both directions "counts on the side of its primary result". The paper's own headline result is that a gate set in advance failed on new question types: Laya FT exceeded α on 6 of 7, and certification needs labels of the new type. Even for Jev the gate exceeded α on 1 of 7 (0.143, nearly three times α). Read whole, the study supports the finding. At most it is mixed. It is not opposing.
  2. **Inconsistent scope.** The same row counts open-model studies as support (arx33843 S\* and zen23041163 on open Laya; arx07177 and zen23225893 in the update), so it is treated as a claim about typed models in general. The audit then takes only the hosted-Jev arm of arx33689 as opposing and leaves out its open-Laya arm, which points the other way. That applies judgement (b) in one direction only.
  3. **Wording.** "found a fixed gate held on changed question types" overstates the source. Jev's gate held on 6 of 7, and the fine-tuned Laya gate held on 1 of 7.
  4. **Secondary.** arx00346, cited as support, reports a held-out threshold that met its target (realized risk 0.049 against 5%). Only the one-sided bound exceeded 5%, so this is "cannot be certified", not "missed".
- **Fix:** Choose one of the following and apply it consistently:
  - (a) Keep the row general. Count arx33689 on its primary result (supporting) or as mixed, not opposing. The row then returns to **moderate**, not contested: arx33401 (S), zen23041163 (S) and arx33843 (S\*), plus arx33689 and arx07177 (S\*). Restore l.122 ("lowers one …" → none), l.206, l.329, §7 l.13 ("Two findings are contested" → one), §4.8 l.273 and the audit.
  - (b) Restrict row 14 to hosted Jev. Then drop the open-only supporters. The hosted supporters are arx33401 and arx00346 in the main window, and arx03387, zen22935043 and arx02267 in the update, none of them S\*. arx33689's Jev arm (S\*) outranks them, so the row becomes very low, contested.

  In both cases:
  - describe arx33689 accurately, e.g. "Jev's gate stayed within α on 6 of 7 changed templates, while a fine-tuned open model's gate exceeded it on 6 of 7";
  - say why arx00346 counts as support.

**R14-2 [major] Two of the four main-window "moderate" ratings rest only on jkf87, a weaker-design reproduction using the original authors' code and data. The rule neither defines "independently replicated" nor reconciles this with its very-low clause.**
- **Location:**
  - 03_method.tex l.117 ("preregistered or independently replicated");
  - l.119;
  - tab:keyfindings rows 1 and 2;
  - 04_evidence.tex l.36 ("An independent replication …");
  - l.326;
  - 07_discussion.tex l.12;
  - certainty_audit rows 1 and 2.
- **Source:**
  - jkf.md: "re-ran with the code and data the authors released" (translated from Korean). It covers 5 legs and 1,155 items, plus a recomputation of the published CSVs.
  - quality_appraisal.csv: jkf87_2026replication is single-run, n only, weaker, grey.
- **Problem:**
  - Without jkf87, no study supporting row 1 clause (a) ("ranks well") or row 2 is preregistered or replicated. arx29429, zen22885291, arx33401, arx00346, arx01006 and arx26550 are all held-out S. Both rows would be **low**, as they were on 4 October.
  - The very-low clause holds that studies "none of which is of stronger design" cannot support even a low rating. Yet a weaker-design re-run of the same harness on the same data, covering 11% of the benchmarks, lifts three stronger studies to moderate.
  - This is a computational reproduction. It shows that the numbers can be regenerated. It is not an independent replication of the finding on new data or in a new setting, which is what an upgrade in the GRADE spirit would need.
  - The dependence is stated for row 2 (l.326), but not for row 1 or in §7 l.12.
- **Fix:** Either option will do:
  - Define "independently replicated" in §3: a different team, new data or a new setting, and a design at least moderate. jkf87 then does not qualify, and rows 1 and 2 return to low. §3 l.122 ("four … low to moderate" → two), §4.8 l.273, §7 l.12 and the audit change accordingly.
  - Keep jkf87 as qualifying, but say in §3 that a same-code reproduction counts as replication. State in §4.9 and §7 that rows 1 and 2 are moderate only through jkf87 and would be low without it.

  In both cases, call jkf87 a "reproduction with the authors' code and data", not an "independent replication", in G1 l.36.

**R14-3 [minor] The scope of each row (hosted Jev or typed models generally) is not stated, although judgement (b) depends on it.**
- **Location:** tab:keyfindings and its caption; §3 l.117 ("open models only when the claim concerns hosted \jev{}"); certainty_audit rows 1, 2, 4, 8, 11 and 14.
- **Problem:**
  - Judgement (b) agrees with the letter of the very-low clause only if each row says which system it concerns. Only rows 5, 9 and 13 do.
  - Row 4 is moderate only because of two preregistered open-model studies, zen22959854 and zen23038928. Both are by the same author (Yousif Alkhubaizi, zenodo_preprints.csv) and both use Kev-0.8B. The audit's "two preregistered" reads as two independent studies.
  - Row 11's main-window moderate rating also uses an open-model study, zen22922769.
  - The abstract, §1 and §8 phrase these findings about typed models generally, which is consistent. However, a reader cannot tell from the table that, for hosted Jev alone, row 4 would be low.
  - R14-1 shows that the absence of a stated scope already produced one inconsistent rating.
- **Fix:**
  - Add the scope to each finding, e.g. "(typed models)" or "(hosted \jev{})", or add a scope column.
  - Add one sentence to the caption: "for findings about typed models generally, open-model studies count; for findings about hosted \jev{}, only studies of hosted \jev{} count".
  - Note in the audit that the two preregistered steering studies share an author. The rating is unaffected: arx31142, arx01834, arx01006 and one zen study still make three or more independent S.

**R14-4 [minor] The calibration scope sentence says no study reports poor calibration on topic or sentiment tasks, but one of the row's own supporting studies does.**
- **Location:** 04_evidence.tex l.331: "none reports poor calibration on the intent, topic, sentiment or factual-question tasks on which the finding says \jev{} is well calibrated, so none opposes it"; certainty_audit row 8, which lists zen22935043 under clause (a).
- **Source:** evidence_coding_update, zen22935043 G4 (hosted, S): "Top-label ECE depended on question form and task (SST-2 yes/no 0.091 underconfident, choice 0.020, AG News 0.089 with the middle of the scale overconfident: stated 0.750 vs observed 0.612 on 258 items)".
- **Problem:**
  - SST-2 is a sentiment task and AG News a topic task. An ECE of about 0.09 is three to six times the 0.015–0.033 that clause (a) rests on (arx01006).
  - The study is mixed on clause (a) and supports clause (c). It should be counted on its primary result, not cited as plain support for (a) under a sentence saying "none".
  - arx10321 (hosted, S, update) reports that raw probabilities failed held-out unbiasedness for 14 of 15 crash-narrative factors, and is not mentioned. This is arguably clause (c) too, but the scope reason should cover it.
  - The rating (low) does not change, because clause (a) has no S\*.
- **Fix:** Reword along the lines of "zen22935043 found \jev{} well calibrated on sentiment in choice form (ECE 0.020) but not in yes/no form or on AG News (0.09); we count it under 'calibration is local'". Add arx10321 to the scope sentence.

**R14-5 [minor] The change in main-window ratings during the update round is disclosed, but not as a deviation from the update protocol, and l.71 still states the frozen-rating rule.**
- **Location:**
  - 03_method.tex l.71: "an answer box or certainty rating was to change only if the update evidence changed its direction or its rating";
  - l.122;
  - §7 Certainty paragraph;
  - App. D (corrections).
- **Protocol:** UPDATE_SEARCH_2026-10-08.md: "The main analysis window … and every count, figure and certainty rating built on it stay unchanged … A certainty rating changes only when the update evidence changes its direction or its rating."
- **Problem:**
  - Six main-window ratings changed in this round: rows 1, 2, 3, 4, 11 and 14, with row 5 newly contested.
  - None of these changes came from update evidence. They came from a rule rewritten and re-applied during review rounds 12–13, after the update studies had been coded.
  - Correcting the method is legitimate, and l.122 states the arithmetic. But l.71 still reads as if the protocol's freeze held. Nowhere does the paper say the rule was revised after the update evidence was known, which is the information a reader needs to judge post-hoc risk. App. D does not list the change.
- **Fix:**
  - Change l.71 to: "… the main-window counts, figures and tallies are unchanged; the main-window certainty ratings were re-derived during review (below), a deviation from the update protocol".
  - In l.122, add "the rule was reworded and re-applied during review, after the update studies had been coded".
  - Add a line to App. D listing the 4-October and current rating for each changed row.
  - Add a half-sentence to §7.

**R14-6 [nit] "Stronger reasoner" is judged differently for the same model.**
- **Location:** 04_evidence.tex l.321 and l.323; l.406.
- **Problem:**
  - arx07177 escalates to Qwen3-32B and is counted as escalation to a stronger reasoner.
  - arx09188 escalates to the same Qwen3-32B but is excluded as "closer to a peer", although in that study Qwen's labels added +16.7 Elo against +2.8 for Jev's (arx09188 G7).
  - The criterion is apparently "stronger than the first stage in the same study". That is defensible, but it is not stated.
  - The rating is unaffected: arx09188 is S, below S\*.
- **Fix:** State the criterion once, or count arx09188 as a further opposing study.

**R14-7 [nit] The certainty cells are hard to read, and the caption does not fit row 5.**
- **Location:** tab:keyfindings.
- **Problem:**
  - "moderate; low, contested$^{u}$" can be read as only "contested" being from the update.
  - The caption says "update:" marks studies that change the certainty cell, but row 5's "update, opposing: arx04985" changes nothing.
- **Fix:**
  - Write the cell as "moderate; low$^{u}$, contested$^{u}$" or "main: moderate / with update: low, contested".
  - Change the caption to "'update:' marks update-search studies that bear on the cell".

**R14-8 [nit] Row 15 and row 13 are rated or counted outside the rule as stated.**
- **Location:** tab:keyfindings rows 13 and 15; certainty_audit rows 13 and 15.
- **Problem:**
  - Row 15 is "kept at low" for a reason the §3 rule does not provide: the comparator field was coded once, which is a count of codes, not a set of studies. Neither the caption nor §3 says that this row is rated by judgement.
  - Row 13 counts zen22885291, which measured LLM accuracy inside Jev's *uncertain* band, as support. Yet it excludes arx09188 because it "measures uncertain, not confident, items".
  - The rating is unaffected: arx29769 and arx33401 still give low.
- **Fix:**
  - Add "(rated by judgement; see audit)" to row 15 or the caption.
  - Drop zen22885291 from row-13 support in the audit.

**R14-9 [nit] The abstract's "Certainty is mostly low" is looser than §1 and §8.**
- **Location:** 00_abstract.tex l.7.
- **Problem:** In the main window the ratings are 7 low, 4 very low and 4 moderate. The abstract's wording is defensible, since low is the most common rating, and §1 and §8 say "low or very low for most findings". The abstract has 1,916 characters, so the arXiv limit of 1,920 leaves no room to add words.
- **Fix:** Harmonise only if R14-1 or R14-2 frees characters, e.g. "Certainty is low or very low for most findings".

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 2 | R14-1, R14-2 |
| Minor | 3 | R14-3, R14-4, R14-5 |
| Nit | 4 | R14-6 to R14-9 |

New major or minor problems remain: yes
