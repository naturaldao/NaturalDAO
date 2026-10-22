# Round 4: fidelity and consistency review

Scope: the current sources (sections/*.tex, counts.tex, main.bbl, arxiv/ bundle, arxiv_metadata.txt, figures/src) and main.pdf (65 pp., built 4 Oct 23:37, newer than every section file). The only file I edited is this one.

**Recomputed from `data/`; all match the paper:**

- **Tallies.** 161 tallied pairs are S 16 / Q 99 / N 46, from 85 documents. All seven answer-box tallies match.
- **Comparator splits.**
  - G1: 6 of 21 better or similar, 10 mixed, 5 worse.
  - G4: 9 better and 2 worse, of 18.
  - All comparisons: 76 compared pairs, 23 better / 17 similar / 28 mixed / 8 worse.
  - Negative codes: 14 have a comparator (6 worse / 4 similar / 3 mixed / 1 better); 32 have none.
- **Sensitivity analyses.**
  - Stronger-design studies only: 7/45/27 of 79.
  - Without Zenodo: 13/77/27 of 117.
  - Negative share, Zenodo vs arXiv: 19/44 vs 23/107.
- **Appraisal.** Design ratings are 37 stronger / 17 moderate / 38 weaker of 92. The quality column in evidence_coding.csv agrees with quality_appraisal.csv for every row.
- **Corpus reconciliation.** 85 tallied + 7 non-empirical + 22 uncoded background arXiv papers = 114 = 107 + 7, which reconciles the §3.3 sentence. papers.csv has 25 background papers, 3 of them coded.
- **Agreement.** κ = 0.717 on 26 of 30 pairs, with first-coder marginals S 3 / Q 23 / N 4. The 10,000-resample bootstrap lower bound is 0.40–0.42 depending on seed; the script fixes the seed.
- **App. E PRISMA arithmetic.** 89 = 63 + 1 + 25 → 15 new, giving 79 arXiv papers. Zenodo: 62 → 41 → 28 → 27.
- **tab:keyfindings.** Every certainty rating now satisfies the stated rule, checked against quality_appraisal.csv:
  - Only "Thresholds set in advance" is moderate. arx00346, arx33843, zen23041163 and arx33401 are all independent and stronger, and arx33843 is preregistered.
  - Every "low" row has two or more studies, at least one of stronger design.
  - Every "very low" row is single-study.
- **Certainty count.** 1 moderate / 9 low / 5 very low. §7 ("One reaches moderate certainty") matches.

**Bibliography:**

- main.bbl has 134 URLs and 47 DOIs, all well formed.
- No `abs/v1` remains in main.bbl or arxiv/main.bbl.
- All 80 arXiv URLs are valid IDs.
- Every `arxNNNNN` key resolves to the matching 2609/2610 ID.
- main.log has no undefined references.
- Apart from the `sections/` and `figures/` path prefixes, the arxiv/ bundle sources match `sections/`.

**Claims spot-checked against full texts, with no problem found:**

- arx24574: 0.383 vs 0.371, where 0.371 is Jev's all-item accuracy (App. table); 166 per class; Gemini 3.8 Flash; 16 of 19; 0.066 vs 0.157; "a quarter to half" of cost.
- arx29429: 0.886 [0.821, 0.952]; 31 benchmarks; 25 of them; $0.30 vs $18.96; +0.006 [−0.004, +0.015]; F1 0.706 → 0.822; 0.721 vs 0.694.
- arx00346: 0.921; 0.940–0.948 vs 0.913; 50.5 flips per hundred; Laya 91.3; 4.2–6.5; 0.310 → 0.195; 0.0079 per thousand; 138 ms.
- arx34862: 77.8 vs 74.1.
- arx02046: 63–66% (Q4 23.8, Q1 88.9); 95.7–97.5% with escalation.
- arx33671: 35.71 → 0.42; 60.33 → 56.81.
- arx00213: 14 of 42.
- arx00376: 9.80 vs 22.79; 150 examples.
- arx28613: 1.8%; 3.5%; 18/510; [0, 10]%.
- arx36399: 87% vs 62%.
- arx37647: 346,009; ECE 0.028 / 0.061; 27 datasets (11 non-overlapping).
- arx24052: 2,416; about 80%; 0.0231 → 0.0069; slope 1.63.
- arx27607: 0.1235 → 0.0077.
- arx24881: ECE 0.133.
- zen23032384: 0.076 → 0.339; preregistered.
- arx33209: 480 pairs; 0.064; about five times.
- arx34024: 17/162 = 10.5% vs 8.6%.
- arx33689: 0.143 vs 0.801; ⌈1/α⌉−1 = 19.
- arx33843: 0.1399 vs 0.10.
- zen23041163: 0.585.
- arx01834: 36% / 56%; 33 → 94%; 24 of 26.
- arx26550: within three points; 0.36%; 1,610.
- arx00831: 0.33 → 0.14 / 0.18.
- arx38827: 74.4% (but see R4-fc-1).
- fig_fragility data: 0.706/0.822, 0.158/0.947, 238/328, Laya 0.7692 / Open-Jev 0.1950 / Jev 0.3250, AUROC 0.938 → 0.232 and 0.815 → 0.581.
- fig_framework reads evidence_coding.csv directly.

---

## Status of round-3 findings

| ID | Status | Note |
|---|---|---|
| R3-fc-1 | FIXED | Steering row is now *low*; §7 says "One reaches moderate certainty". |
| R3-fc-2 | PARTLY | §3 now says "reported neither sample sizes nor uncertainty", matching the code. App. E "Design appraisal" still says "or no uncertainty reported" (R4-fc-2). |
| R3-fc-3 | FIXED | "9 of the 14 items". |
| R3-fc-4 | FIXED | Both boxes say "the typed models". |
| R3-fc-5 | FIXED | "better or mixed", "similar", "similar". |
| R3-fc-6 | FIXED | §6 now says "most elements rest on evidence of low or very low certainty". Summaries ("mostly low", "most findings … low") are accurate for 9 of 15 low. Wording still varies slightly (nit, not re-raised). |
| R3-fc-7 | FIXED | "0.383 against 0.371 … low-cost generative model"; verified against the source. |
| R3-fc-8 | FIXED | "close to what data-protection law requires where it applies". |
| R3-fc-9 | FIXED | "17 of the 162 items for which it was the correct answer". |
| R3-fc-10 | FIXED | §3.3 now separates 85 tallied, 7 non-empirical and 22 background papers. |
| R3-fc-11 | FIXED | App. E says "the earlier dataset release". |
| R3-fc-12 | FIXED | 10,000 resamples with a fixed seed; reports 0.42–0.94. |
| R3-fc-13 | FIXED | §8 no longer lists transparency as a commitment. |
| R3-fc-14 | PARTLY | §1 still says "28 passages" while tab:concordance has 33 rows over 28 clause labels. \clause{4.3.3.2} is still cited nowhere in the body (R4-fc-5). |
| R3-fc-15 | PARTLY | Column renamed "Design". §4.8 says "at most about five points", but the largest shift is 5.6 points (R4-fc-4). |
| R3-arg-1 | PARTLY | §4.8 bridge paragraph added and the abstract says "under added conditions". The Thesis still presents steering and "insufficient" failures only as reasons against judge use; it does not state that G2 failures are detector failures. |
| R3-arg-2 | FIXED | §1 treats automatic allow as a deliberate, audited exception; element 5 repeats it. |
| R3-arg-3 | NOT | Author action. Disclosure unchanged; no human check reported. |
| R3-arg-4 | PARTLY | The rating is fixed. The "rising to moderate is our adaptation" note is not added to §3.5. |
| R3-arg-5 | PARTLY | Element 6 title and Figure 6 box 6 fixed ("every chain that could block"). The Figure 6 caption is unchanged (R4-fc-3). |
| R3-arg-6 | FIXED | §3.3 reconciles 85 + 7 + 22; 92 appraised = 85 + 7. |
| R3-arg-7 | FIXED | No `abs/v1` left; all arXiv URLs valid. |
| R3-arg-8 | NOT | Author action. The Data statement still points to an unpinned `main` path (public repository not re-checked this round). |
| R3-arg-9 | NOT | Author action. Comments still ends in "…/PoL2-Jev-Typed-Literature-Survey". |
| R3-arg-10 | FIXED | "a plausible role". |
| R3-arg-11 | FIXED | "AI review passes"; "Changes from the earlier release"; "separate review passes". |
| R3-arg-12 | FIXED | "on simulated data" is in the abstract. |
| R3-arg-13 | FIXED | Same edit as R3-fc-13. |

---

### R4-fc-1 [minor]
**Location:** §4 G3, "Order, wording and culture": "On ANLI, \jev{} placed 38.8\% of its predictions and 51.3\% of its errors on the middle option".

**Problem:** This is a regression. Round 2 had "on Neutral". "The middle option" presents the result as a position (order) effect, which the source explicitly rules out.

**Evidence:** arx38827 says Jev "assigns 38.8% of all predictions and 51.3% of errors to Neutral despite … nearly balanced gold labels, and balanced candidate positions". It concludes that the bias "is not a renamed Neutral, middle, or low-score preference" and that a "purely first-, middle-, or last-position mechanism should therefore weaken sharply". evidence_coding.csv also says "on Neutral".

**Fix:** Write "placed 38.8\% of its predictions and 51.3\% of its errors on Neutral, although the option's position was balanced".

### R4-fc-2 [minor]
**Location:** App. E, "Design appraisal": "*weaker design*: single run, case study, non-empirical, or no uncertainty reported".

**Problem:** §3 sec:appraisal now reads "or reported neither sample sizes nor uncertainty". That matches the data, but App. E still has the old rule, so the two definitions contradict each other.

**Evidence:** Under App. E's wording, arx24965, arx35293, arx36965 and zen23065532 would be weaker; they are held-out, report sizes only and are rated moderate in quality_appraisal.csv and tab:evidence. The comment in scripts/merge_coding.py (l. 79–80) carries the same stale wording.

**Fix:** In App. E, write "or reported neither sample sizes nor uncertainty". Optionally update the script comment.

### R4-fc-3 [minor]
**Location:** Figure 6 (fig:architecture) caption: "disagreements, insufficient information and a random sample of confident decisions go to people (6)".

**Problem:** Element 5 and the regenerated Figure 6 box 5 send disagreements and \texttt{insufficient} verdicts first to clarification or to a stronger reasoning model. Element 6 and box 6 send to people only escalations that would end in a block, unresolved escalations and a random audit sample. The caption contradicts both. This is the part of R3-arg-5 that was not applied.

**Fix:** Write "disagreements and insufficient verdicts are clarified or escalated (5); any that would end in a block or remain unresolved, and a random sample of confident automatic decisions, go to people (6)".

### R4-fc-4 [nit]
**Location:** §4.8 "The shares change by at most about five points"; §7 "changes the overall shares little".

**Problem:** The largest shift is in the negative share. It is 28.6% overall, 34.2% on stronger-design studies only (+5.6) and 23.1% without Zenodo (−5.5).

**Fix:** Write "by at most about six percentage points", or give 28.6% / 34.2% / 23.1%.

### R4-fc-5 [nit]
**Location:** §1 Contributions, "(\nPolClauses{} passages, \cref{app:concordance})"; App. A, "quotes every \pol{} passage that this paper cites or paraphrases".

**Problem:**
- tab:concordance has 33 rows over 28 clause labels. \clause{4.3.2} alone has five rows and \clause{4.3.3.1} has two.
- \nPolClauses{} is hard-coded as 28 in merge_coding.py, so it counts clauses, not passages.
- \clause{4.3.3.2} is still not cited or paraphrased anywhere in the body.

**Fix:** Write "28 clauses, 33 passages". Drop the 4.3.3.2 row, or say that App. A also includes related passages.

### R4-fc-6 [nit]
**Location:** tab:keyfindings, row "Peer evaluators repeat \jev{}'s most confident errors", column "vs. generative" = "similar".

**Problem:** The cited G6 rows are arx29769 = similar and arx33401 = mixed.

**Fix:** Write "similar or mixed".

### R4-fc-7 [nit]
**Location:** §4 G7 / G1 (arx00213): "finding residual personal identifiers in 37--43\% of audited narratives after two redaction passes".

**Problem:** Only the 37% figure is from the audited sample (152 of 407 adjudication narratives). The 43% is 25 of the 58 documented fetal-harm narratives.

**Fix:** Write "in 37\% of audited narratives and 43\% of documented fetal-harm narratives".

### R4-fc-8 [nit]
**Location:** §4 G1, "Where the evidence is not text": "stayed far below small tree models with 150 examples in context".

**Problem:** The sentence reads as if the tree models had 150 examples. In the source, Jev had 150 in-context examples (34.5%), while the tree models were trained on 8,000 records (66.8–70.0%).

**Fix:** Write "and, even with 150 examples in context, stayed far below tree models trained on 8,000 records".

---

**Counts:** 0 major, 3 minor (R4-fc-1, -2, -3), 5 nits (R4-fc-4 to -8). New major or minor problems: yes, three minor ones. R4-fc-1 is a new regression; R4-fc-2 and R4-fc-3 are round-3 fixes applied in one place but not in another. No new major problem.
