# Round 8: combined review (fidelity, consistency, balance, argument/arXiv)

**Scope**

- Paper and data:
  - main.pdf (65 pp., built 5 Oct 06:06);
  - sections/*.tex, counts.tex, main.bbl, arxiv_metadata.txt and arxiv-submission.zip;
  - data/evidence_coding.csv.
- Local full texts: scratchpad fulltext/, g1/, g3/, g4/, sc2/ and root copies.
- Edits: this file is the only one I edited.
- Build check: I made a scratch copy of the build in scratchpad/r8build and compiled it there.

## Status of round-7 findings

| ID | Status | Note |
|---|---|---|
| R7-1 | FIXED | §4.6 now opens "Escalation among peers" with the favourable half: "differed significantly … in at most 8 of 27 paired comparisons, at 1/16 to 1/325 of their cost". This is correct against the source ("16 to 325 times as much"). |
| R7-2 | FIXED | §4.1 now reports Jev-IDS: F1 0.856 against 0.880, and about 43 against about 764 false alarms. These are the body-table values, not the abstract's 0.859. See the nit R8-5. |
| R7-3 | FIXED | §2.1 now reads "about 140 to 500 ms". |
| R7-4 | PARTLY | The WiC result is added (ECE 0.027, tuned prompt). The same blog's ChaosNLI result (ECE 0.025 against the crowd share) is still omitted next to the unfavourable ChaosNLI study. See R8-4. |

## Build and numbers

**Shipped build**

- main.log has no undefined references or citations, and the PDF contains no "??".
- The final lines of the shipped main.log still carry a genuine `LaTeX Warning: Label(s) may have changed`. This is separate from the intentional `\typeout` line, and suggests the shipped log comes from a pass that had not converged.
- I recompiled a copy in scratch. Two further passes give zero rerun warnings and the same 65 pages, and the pdftotext output is identical to the shipped main.pdf. No content effect.

**arXiv bundle**

- arxiv-submission.zip matches the sources apart from flattened figure paths and stripped comment lines.
- It contains the round-7 fixes.
- The metadata abstract matches the PDF abstract (1,917 characters).

**Counts recomputed from evidence_coding.csv** (in_tally = yes). All match counts.tex, the answer boxes, §4.8 and §3.

| Check | Result |
|---|---|
| Codes per requirement | G1 2/20/5, G2 1/0/9, G3 2/12/10, G4 3/29/13, G5 2/3/3, G6 1/23/4, G7 5/12/2 |
| Totals | S 16, Q 99, N 46 (161 pairs) |
| Coded documents | 85 |
| G1 comparators | better 1, similar 5, mixed 10, worse 5 ("6 of 21 better or similar") |
| G4 comparators | better 9, worse 2 |
| Corpus arithmetic | 85 + 7 non-empirical + 22 background = 114 = 107 + 7 |

## Systematic S/N balance pass over evidence_coding.csv

**Method.** For every in-tally S or N pair I checked two things:
- whether the body (§§1–8) reports that study's coded finding for that requirement;
- if it does, whether the report matches the coded rationale.

**Reports of cited studies match their rationales.** I checked each of the following:
- arx00376, arx01006, arx01834, arx02048, arx30243, arx31142 and arx33401;
- arx26758, arx00346, arx36399, arx38827, simmons and zen23023694;
- arx33209, arx33971, arx37470 and arx39496;
- arx29769, arx28613, arx24965 and zen22849329.

The exceptions are listed below.

**Omission rates are roughly symmetric overall.**
- About 6 of 16 S pairs and about 15 of 46 N pairs are not reported in the body.
- Most of the omitted N pairs are weaker-design Zenodo items or open-model items: zen22846597, zen22864020, zen22957049, zen22980293, zen22922769 and alphaRAG.
- The two exceptions are arx36154 (stronger) and zen23065532 (moderate). Omitting them does not bias any answer box against typed models.

**The specific omissions below do change how particular answers read.**

---

### R8-1 [minor] Three S-coded, stronger or moderate design results never reach the body; one is the only S code for G6

**Location:** §4.1 (G1), §4.3 (G3), §4.4 (G4) and §4.6 (G6) of 04_evidence.tex, and Table 2 (tab:keyfindings).

**Problem.** Three studies coded S appear only in Appendix B and are never described in the body.

- **zen22885291** (G1 S "better"; G4 S "better"; G6 Q; stronger; hosted jev-1.13-20260917).
  - **G1:** on identical 500–600-item samples of seven moderation, hallucination, NLI and injection tasks, Jev had the highest AUROC of the cheap-tier LLMs on all six binary tasks (0.90–0.99). It was never significantly worse than a cheap-tier model, but frontier Sonnet 4.6 beat it.
  - **G4:** Jev had the lowest raw Brier score of all systems.
  - **G6:** escalating Jev's uncertain band to an LLM helped in only 2 of 30 cascades, and the author recommends routing that band to a human. This directly supports the paper's own G6 and T4 line, yet it is not cited there.
  - **Effect on G1:** this study is the only "better" pair behind G1's "6 of 21 better or similar". Table 2's row "Ranks harmful or misaligned content well… vs generative: similar or mixed" cites three other studies and does not reflect it.
- **arx24574, G3 S "better"** (stronger, preregistered).
  - The preregistered hypothesis that calibration degrades on Indian-English dialect text was rejected in the opposite direction. Jev's dialect ECE was 0.063, the lowest of 22 models (next 0.181).
  - The same source is cited eight times elsewhere, but the G3 box ("lean towards one culture's values") and the "Language" paragraph never mention this, the one preregistered fairness result in Jev's favour.
- **arx00381** (G4 S, G6 S; moderate; open medical LVLM readout).
  - It is the **only** S code for G6, so the G6 box's "S 1" refers to a study the reader never meets.
  - It reports lower ECE and lower AURC than a matched generative SFT baseline in distribution.
  - It also has a G4-relevant caveat: with the true candidate removed, it picks a runner-up (0.88) instead of signalling absence.

**Why minor.** None of these reverses an answer. Together, though, they are most of the favourable head-to-head evidence. A reviewer checking the paper's claim of a symmetric assessment against Appendix B would find that the favourable comparisons are less visible than the unfavourable ones.

**Fix.** Add one clause or sentence each:

- **§4.1 "Zero-shot ranking":** "On matched samples of seven moderation, hallucination, NLI and injection tasks, \jev{} had the highest AUROC of the low-cost LLM evaluators on all six binary tasks, though a frontier model beat it~\cite{zen22885291}\zmark{}."
- **§4.3 "Language":** "In a preregistered test, its calibration on Indian-English dialect text was the best of 22 models (ECE 0.063)~\cite{arx24574}."
- **§4.6 "Escalation among peers":** "Escalating \jev{}'s uncertain band to an LLM helped in 2 of 30 cascades~\cite{zen22885291}\zmark{}."
- **§4.6 "Thresholds and gates":** "In distribution, a typed readout trained on a medical vision-language model gave lower selective-prediction risk than a matched generative baseline~\cite{arx00381}."
- **Table 2:** change the G1 comparator cell to "similar to better (low-cost); worse (frontier)", or add zen22885291 to its sources.

### R8-2 [minor] The clearest "worse than generative" results for hosted Jev are omitted from G1 and G6

**Location:** §4.1 (G1), §4.6 (G6) and Table 2.

**Problem.** Of the 8 "worse" comparator pairs, the body reports five (arx01079, arx02048, zen22901853, arx39496, plus zen22901853 under G1). It does not report the three largest deficits for hosted Jev.

- **arx24574, G1 N "worse"** (stronger, preregistered).
  - On 15 annotation tasks (7,977 items), Jev trails the per-task best LLM on 14 of 15, with a median deficit of 11.6 macro-F1 points. The deficit is significant after FDR correction on 12 tasks.
  - Source: abstract and §4.1 ("trails the per-task best LLM on 14 of 15 evaluation tasks, with a median deficit of 11.6 macro-F1 points").
  - The body cites this paper for favourable calibration (16 of 19 LLMs) and for the cheap cascade, but never for this result. That is a one-sided report of a single source against its coded rationale.
- **arx27678, G1 N "worse"** (stronger).
  - On ContractNLI (2,091 judgments), Jev 1.13.0 reached 77.38% (CI 75.99–78.81), below all seven hosted LLMs (78.96–83.21%), at the lowest cost.
  - Source: §4, Table "Jev 1.13.0 77.38 [75.99, 78.81]". The body cites it only in checklist item 9.
- **arx34024, G6 N "worse"** (weaker).
  - Selective prediction was worse than GPT-6 Sol on two of three benchmarks (AURC 0.087 against 0.070, and 0.303 against 0.080). The authors conclude that better calibration gave no selective-prediction advantage.
  - The body cites the paper only for the "I don't know" rate.

**Why minor.**
- The G1 box says "worse in 5", but the G1 text shows the reader only comparisons in which Jev is ahead, on a par or slightly behind.
- §4.8's conclusion ("not generally worse") is still supported by the tallies.
- However, the text gives the reader no means to see the strongest counter-instances, and arx24574 is the largest preregistered head-to-head comparison in the corpus.

**Fix.**
- **§4.1:** after the arx34862 sentence, add: "On 15 preregistered annotation tasks, however, \jev{} trailed the best LLM on 14 by a median 11.6 macro-F1 points at about 1/44 of the cost~\cite{arx24574}, and on contract NLI it was below all seven hosted LLMs (77.4\% against 79.0--83.2\%)~\cite{arx27678}."
- **§4.6:** add one clause for arx34024.
- **Table 2:** the ranking row's comparator cell can then read "mixed; worse on annotation".

### R8-3 [minor] Explicit "None of the above" in the medical benchmark is omitted, and that half is neither rare nor on a par with the frontier model

**Location:**
- §4.4 "The missing 'insufficient'";
- T2 in 05_synthesis.tex;
- Table 2 row "Explicit 'none'/'I don't know' rarely chosen when correct — similar (frontier); worse (reasoning)".

**Problem.**
- **What the paper reports from arx34024.** Only the "I don't know" half: 17 of 162 items (10.5%), against 8.6% for GPT-6 Sol.
- **What the same benchmark also offers.** MetaMedQA also has a "None of the above" option, correct for 115 items. Source §3.4: Jev "selected 'None of the above' for 53.9% (62/115) of the questions for which that option was correct". GPT-6 Sol "had a higher missing-answer recall (73.9%)".
- **What this changes, in two directions:**
  1. **Not always "rare".** An explicit "none" option was chosen on more than half of the items where it was correct, which qualifies the generalisation "rarely chosen" in the abstract, §4.4, T2 and §8. As it stands, that generalisation rests on arx39496 (7% on arithmetic).
  2. **Worse than the frontier model.** On "none", Jev was clearly worse than the frontier comparator (54% against 74%), so "similar (frontier)" in Table 2 is true only for "I don't know".

**Fix.**
- **§4.4:** add "; it chose an explicit 'None of the above' for 54\% of the items where that was correct, against 74\% for the frontier model~\cite{arx34024}".
- **Table 2:** change the comparator cell to "similar (frontier, 'I don't know'); worse (frontier, 'none'; reasoning)".
- **Wording elsewhere:** "an explicit 'insufficient' option is rarely chosen" can stay. "Insufficient" or "I don't know" is the construct at issue, and both IDK results (10.5%) and arx39496 (7%) support it. But §4.4 should not let "none" and "I don't know" read as one finding.

### R8-4 [nit] ChaosNLI is reported only for its unfavourable side (carries R7-4)

**Location:** §4.4 "Calibration is local" and §4.7 G7 ("stayed confident where annotators were split").

**Problem.** Two facts are missing next to zen23032384's ECE of 0.339 on the most-disagreed quarter:
1. **The study's own comparator result.** It is coded "better" (the only N code with a "better" comparator). Jev was far better calibrated than the local generative baseline, and its confidence still ranked contested items (AUROC 0.744).
2. **grazian2026calibrated (grey, coded G4 Q, stronger).** On 612 held-out αNLI ChaosNLI stories, after per-dataset prompt tuning, it reported an ECE against the crowd's share of 0.025. Source: "The ECE against the crowd is 0.025".

**Why only a nit.** The subsets (αNLI against SNLI/MNLI) and the prompting (tuned against untuned) differ, so this does not contradict "calibration is local". It does bear on the G7 claim that probabilities do not estimate how many people would agree.

**Fix.** Add one clause: "…against 0.076 on the most agreed quarter (still better than a small generative baseline); with a prompt tuned to αNLI, one blog reported an ECE of 0.025 against the crowd's share~\cite{grazian2026calibrated}\gmark{}".

### R8-5 [nit] The Jev-IDS random-forest contrast needs its label budget

**Location:** §4.1, line 47.

**Problem.**
- **What the paper says.** "With about 43 false alarms per run against about 764 for a random forest".
- **What the source says.** The 764 figure is for the random forest at k = 1 ("approximately 764 false alarms among the 874 normal Flows in each seed"). At k = 8 the forest reached F1 0.865, above Jev's 0.854.

**Fix.** Write "…against about 764 for a random forest given the same single example per class".

### R8-6 [nit] The arx27607 rationale in the released data mislabels a value

**Location:** data/evidence_coding.csv, row arx27607 G4.

**Problem.**
- **What the row says.** "Raw sentence-level ECE is 0.1192 (Brier 0.1235)".
- **What the source says.** §5.6 and App. G Table: 0.1192 is the full-set ECE, and 0.1235 is the **holdout ECE** (Brier on the holdout is 0.1269). The G6 row of the same study correctly says "ECE 0.1235->0.0077".
- **Effect.** The paper text and the Fig. 3c caption are correct. Only the public data file is affected.

**Fix.** Correct the rationale string.

### R8-7 [nit] The shipped main.log ends with a real "Label(s) may have changed" warning

**Problem.** See "Build and numbers" above. One more pdflatex pass clears it, and the output is unchanged.

**Fix.** Rebuild once before packaging, so the submitted log is clean.

## Source claims spot-checked this round (not in rounds 4–7)

All were checked against local full texts, and all are correct unless noted.

| # | Source | Claim | Result |
|---|---|---|---|
| 1 | arx34862 | F1 77.8 against 74.1 (GLM-5.2); wins on 2 of 4 benchmarks with higher recall and lower precision | Correct ("JEV's F1 advantage accompanies higher recall despite lower precision") |
| 2 | arx33671 | Benign FPR 35.71% → 0.42%; general Chinese safety 60.33% → 56.81% unless replay | Correct |
| 3 | arx01834 | ALFWorld misleading steps: 36% right, lure 56%; written prediction 33% → 94%; 24 of 26 follow a wrong premise | Correct |
| 4 | arx01006 | HotpotQA 0.84 → 0.75 with confidence 0.83; up to 0.80 on a salient option; enough AUROC 0.95 against 0.85; 2–6 points worse as a filter; SmoothECE 0.015–0.033 on familiar tasks; 575,442 calls | Correct |
| 5 | arx00831 | Reversal changes about a third; rotation averaging 14–18% on 20-option tasks | Correct (0.33 → 0.14 and 0.18) |
| 6 | arx24052 | 2,416 blind labels; prevalence overstated by about 80%; too close to the middle; ECE 0.0231 → 0.0069 out of fold | Correct. The source adds that one frontier arm failed the same way, which is coded "mixed" and is acceptable as written. |
| 7 | arx27607 | Holdout ECE 0.1235 → 0.0077; open baseline improved similarly (0.1072 → 0.0063) | Correct (but see R8-6 for the data file) |
| 8 | arx37470 | 32.8% interface disagreement against 34.2% post-trained | Correct |
| 9 | arx34024 | 17/162 (10.5%) against 8.6% | Correct, but incomplete; see R8-3 |
| 10 | arx39496 | None chosen on 7%; 99% answer-present; threshold to 79% | Correct |
| 11 | arx01079 | F1 0.856 against 0.880; about 43 against about 764 false alarms | Correct values; see the qualifier in R8-5 |
| 12 | arx36399 | 87% English and 62% Arabic of the human Saudi–US difference | Correct |
| 13 | arx33971 | Total variation 0.22–0.35 | Correct (0.219–0.349) |
| 14 | arx33689 | Act-and-wrong ≤ 0.143 against 0.801; 19 labels at α = 0.05 | Correct |
| 15 | arx38827 | 38.8% of predictions and 51.3% of errors on neutral with balanced positions; six datasets, 74.4% agreement across orders | Correct (Table 2: 74.43; six ordinal datasets) |
| 16 | grazian2026calibrated | WiC ECE 0.027 on 3,066 pairs after tuning | Correct |
| 17 | arx29769 (new sentence) | At most 8 of 27; 1/16 to 1/325 of the cost | Correct |

## arXiv

- Tone remains neutral.
- cs.CY primary with a cs.AI cross-list is still appropriate.
- The bundle matches the build.
- No new moderation concern.

---

## Counts

0 major, 3 minor (R8-1, R8-2, R8-3), 4 nits (R8-4 to R8-7).

New major or minor problems remain: **yes**. All three minor findings are balance or fidelity omissions found in the systematic S/N pass. Each can be fixed with one added sentence or clause plus a Table 2 cell edit:
- **R8-1:** favourable S-coded results are omitted, including the only G6 S.
- **R8-2:** the strongest "worse than generative" results for hosted Jev are omitted.
- **R8-3:** the "None of the above" half of arx34024 is omitted.

R7-1 to R7-3 are fixed. R7-4 is partly fixed (nit).
