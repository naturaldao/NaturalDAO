# Round 11: combined review (fidelity, consistency, balance, argument/arXiv)

**Scope**

- Paper and data: main.pdf (65 pp.), main.log, arxiv-submission.zip (all 5 Oct 06:23); sections/*.tex (04_evidence.tex 06:23, 05_synthesis.tex 06:20); counts.tex; data/evidence_coding.csv.
- Local full texts (scratchpad):
  - for the round-10 nits: g1/22885291.txt, fulltext/2609.34024.txt, fulltext/2609.24574.txt;
  - for fresh spot-checks: fulltext/2609.36965.txt, fulltext/2609.24881.txt, fulltext/2609.26550.txt, g4/2610.02046.txt, 33843.html, zen/23041163.txt, fulltext/2609.27535.txt, fulltext/2609.28919.txt, g3/z22848952.txt, g4/2610.02076.txt, zh.md, bern.txt, cp.html, g3/simmons.txt and r2/jkf.md.
- Focus:
  - the round-10 nits;
  - the sentences changed in response to them;
  - a fresh whole-paper pass that does not re-raise items resolved in rounds 1–10.
- Edits: this file is the only one I edited.

## Status of round-10 findings

| ID | Status | Current text / note |
|---|---|---|
| R10-1 | FIXED | l.141: "on six public binary tasks its raw Brier score was the lowest of all systems tested, though after recalibration a frontier model's was slightly lower (0.071 against 0.076)". l.223: "monotone on six public binary tasks". |
| R10-2 | FIXED | l.141: "on one of three medical benchmarks its probabilities were better calibrated than a frontier reasoning model's (ECE 0.063 against 0.146), with similar error on the other two". |
| R10-3 | PARTLY FIXED | The Table 2 row now reads "Well calibrated on familiar closed-choice tasks, mixed against frontier models; calibration is local", and its sources add arx24574, arx34024 and zen22885291. The Codes cell still reads "Q" (see R11-1). |

## Verification of the changed sentences against the sources

| Citation | Claim in text | Source | Result |
|---|---|---|---|
| zen22885291 (§4.4 l.141) | Raw Brier lowest of all systems on six public binary tasks | §4: "lowest mean Brier score of any system (0.103 vs. 0.122 for Haiku…)"; Table 8a is the "Mean over the six binary tasks" | Correct |
| zen22885291 (§4.4 l.141) | After recalibration a frontier model's Brier was slightly lower (0.071 against 0.076) | §4: "Jev's mean Brier is 0.076 … but 0.071 for Sonnet, which is lower than Jev's"; abstract: "closes against Sonnet" | Correct |
| zen22885291 (§4.6 l.223) | Risk–coverage curves monotone on six public binary tasks | §4: "its risk-coverage curves are monotone", referring to Table 10, which covers the six binary tasks | Correct |
| zen22885291 (§4.6 l.218) | Only a frontier model helped, on 2 of 30 cascades | §5: "only 2 are significant … via Sonnet-4.6" | Correct (unchanged) |
| arx34024 (§4.4 l.141) | Better calibrated on one of three benchmarks (ECE 0.063 against 0.146), similar on the other two | §3.3: MetaMedQA 0.063 against 0.146; DiagnosisArena "ECE did not differ significantly"; PubMedQA "three models behaved similarly (ECE 0.140-0.141)"; calibration not computed on the 34 NEJM cases | Correct. "Three" correctly excludes NEJM. |
| arx34024 (§4.6 l.223) | Selective prediction worse than the frontier model on two of three | AURC 0.087 against 0.070 (MetaMedQA); 0.303 against 0.080 (DiagnosisArena); 0.109 against 0.126 (PubMedQA, Jev better) | Correct |
| arx24574 (§4.4 l.141) | Better than 16 of 19 LLMs; three frontier models lower, overlapping intervals (0.066 against 0.157) | Abstract and §4: "16 of the 19 LLMs … three frontier Claude models (median ECE 0.157 against 0.066 for the best baseline)" | Correct |

## Fresh pass

### Fidelity spot-checks (claims not checked in rounds 8–10)

| # | Citation / location | Claim | Source | Result |
|---|---|---|---|---|
| 1 | arx36965, §4.3 l.120 and T3 | ECE 11.45% against 3.78%; general model slightly more accurate; specialists beat Jev in medicine, reach 92% of its average accuracy and are worse calibrated (12.08% against 5.57%); initialised from Laya | Table: 68.35 against 69.20; "reduces ECE … from 11.45% to 3.78%"; "+4.0% … in medicine"; "92.0% of Jev's average accuracy"; "12.08% versus 5.57%"; "initialize … from Laya Multi-" | Correct |
| 2 | arx24881, §4.4 l.146 | Zero-shot ECE 0.133 | Table 3: "TypeSafe Jev (zero-shot) … 0.133" | Correct |
| 3 | arx26550, §4.6 l.210 | Within three points; 0.36% of fee; +0.93 (0.24–1.66) at 41.4% on 1,610 pairs, 83% RewardBench; −0.74 on JudgeBench; live test matched GPT-6 with thresholds on 100 local labels | Abstract and §8 match each figure; live test: "matched GPT-6's accuracy exactly … saving a quarter" | Correct |
| 4 | arx02046, §4.1 l.37 and §4.6 l.212 | Fixed 0.5: mean F1 63–66%, range 24–89% by predicate; escalation raises it to 96–98% | "Mean F1 is 66.3%, 64.0%, and 63.2%"; Q4 "23.8–30.4%", Q1 "85.3–88.9%"; "97.5%, 96.1%, and 95.7%" | Correct (95.7 rounds to 96) |
| 5 | arx33843, §4.6 l.225 | Frozen Laya gate missed its target (0.140 against 0.10) | HTML: "0.0916→0.1399" against "≤0.10" | Correct |
| 6 | zen23041163, §4.6 l.225 | Conformal gate risk 0.585 at nominal 0.05 | Abstract: "returns risk .585 at a nominal α=.05" | Correct |
| 7 | arx27535, §4.7 l.252 and §2 l.37 | Coverage 0.93/0.96 at 80/90% on 37 unseen studies; primary endpoint not shown; 312–455× against flagship | "retrospective coverage is 0.93/0.96"; "preregistered primary policy-value gain was not shown"; "455 times … 312 times" | Correct |
| 8 | arx28919, §4.7 l.255 | Closed weights led to a classifier-agnostic interface with a self-hosted fallback | "That is why the interface is classifier-agnostic and a self-hosted encoder is the stated fallback" | Correct |
| 9 | zen22848952, §4.4 l.158 and T2 | Noul probabilities for conflict and ignorance in the same band; Choice separated them in all four cases | "conflict cases (probability 0.50-0.57) and ignorance cases (0.46-…)"; "separates both cases … in all four completed cases" | Correct |
| 10 | arx02076, §4.4 l.159 | Narrow fine-tuning suppressed "none of the above" and biased the readout towards "yes" while validation loss improved | "confirmation bias toward 'yes' … severe suppression"; "even as in-distribution validation loss continues to improve" | Correct |
| 11 | qin2026zhdecisionbench, §4.3 l.119 | Jev 1.9% (voice) and 2.9% (CS) order flips, 1.7% script flips (n = 323), no refit; Laya multilingual 10.8% and 20.6% | README results table and finding 5: "Jev needs no refit at all" | Correct |
| 12 | yurin2026confident, §4.4 l.152 | 738,164 answers; padding the option set inflates confidence | "over 738,164 live choice answers …"; "Adding options that are never chosen raises the reported confidence" | Correct |
| 13 | checkpoint2026jev, §4.2 l.73 | 25 of 27 runs, fourth turn on average; untrusted marking no meaningful difference; directional study of one application | "broke through in 25 of 27 runs, succeeding on the fourth turn on average"; "focused, directional study … single application" | Correct |
| 14 | simmons2026saidno, §4.3 l.113 | "White" took 51% of first picks across eight traits; direct claims about 3% "yes" | "White goes … to 51 percent of all first picks"; "3% Typical chance Jev calls a direct racial superiority claim [true]" | Correct |
| 15 | jkf87_2026replication, §4.1 l.36 | Median absolute difference 0.0036; TensorTrust AUROC 0.95, F1 0.158 at 0.5 and 0.947 at 0.35; no fitted threshold equals 0.5 | "절대차 중앙값 0.0036"; table "0.158 \| 0.947 \| 0.35"; AUROC 0.9476; "5개 적합 문턱값에 0.5가 하나도 없습니다" | Correct |
| 16 | arx24574, T1 l.12 | Empathy 0.383 on confident items against 0.371 on all items; shared with a low-cost generative model | §4.4 and App. Table 20 ("both Jev and Gemini 3.8 Flash collapse") | Consistent with the R3-fc-7 resolution; not re-raised |

### Internal consistency

**Code tallies (recomputed from evidence_coding.csv, in_tally = yes).**
- 161 pairs: S 16, Q 99, N 46.
- Per requirement: G1 2/20/5, G2 1/0/9, G3 2/12/10, G4 3/29/13, G5 2/3/3, G6 1/23/4, G7 5/12/2. All seven answer boxes match.
- G1 comparators: 1 better + 5 similar = 6 of 21; 10 mixed; 5 worse. G4: 9 better of 18; 2 worse.
- Across requirements: 76 pairs with a comparator (23 better, 17 similar, 28 mixed, 8 worse). Of the 14 negative codes with a comparator, 6 worse, 4 similar, 3 mixed and 1 better; 32 of 46 negative codes have no comparator.
- By source: Zenodo 19 N of 44, arXiv 23 of 107. Stronger-design pairs: 7/45/27 of 79. Without Zenodo: 13/77/27 of 117. 85 documents in the tally.
- All of these match counts.tex, §4.8 and Fig. 2(b)'s "44 Zenodo and 2 alphaXiv pairs".

**Other counts.**
- §3: 85 coded + 7 non-empirical = 92 appraised (37 stronger, 17 moderate, 38 weaker). Adding the 22 background-tier papers gives 114 = 107 + 7.

**Statements across sections.**
- Abstract, §1, §8 and the metadata abstract are identical in substance and use the same counts.
- The G4 box, T2, Table 2 and §8's "rarely chosen when correct" agree.
- §6 has seven elements, as stated. Element 3's "about a third" matches §4.6's 34.5–38%.

**Figures.**
- There are seven figures, matching "7 figures" in the Comments field.
- The captions of Figs. 3–5 match the text (versions, counts, the Wilson intervals and the 1,800/1,200 split).

**arXiv compliance.**
- Build:
  - main.log reports 65 pages, no undefined references and no errors.
  - The overfull boxes are at most 3.1pt. The "Infinite glue shrinkage" note and the typeout line ("get arXiv to do 4 passes") are the known, intended ones.
  - main.pdf contains the round-10 wording and has no "??".
- Bundle:
  - The zip holds main.tex, all sections, counts.tex, main.bbl, the 7 figure PDFs and 00README.json (pdflatex, toplevel main.tex).
  - Section files match the sources line for line, apart from the expected input/graphics paths and stripped comment rules.
- Metadata:
  - The abstract is 1,917 of 1,920 characters, with counts filled from counts.tex.
  - Primary category cs.CY, cross-list cs.AI, CC BY 4.0. The Comments field states "Policy analysis with a documented evidence assessment".
  - Positionality, AI-use and data statements are present.
- Open author-only items from earlier rounds (public data push, affiliation) remain as logged in REVIEW.md; they are not re-raised here.

**Balance.**
- The revised §4.4 paragraph now gives the favourable frontier comparisons with their scope limits: one of three benchmarks, six binary tasks, and Sonnet ahead after recalibration.
- §4.6 keeps the arx34024 selective-prediction counterweight. I found no new over-claiming.

---

### R11-1 [nit] Table 2 calibration row: Codes cell "Q" although one newly added source is coded S

**Location:** 04_evidence.tex l.290, Table 2 ("Well calibrated on familiar closed-choice tasks, mixed against frontier models; calibration is local"), Codes = "Q".

**Problem.** The caption defines Codes as "the cited studies' codes for the finding stated". The row now cites zen22885291, whose G4 code in evidence_coding.csv is S ("lowest mean Brier of all systems … stayed better than the cheap tier and GPT-5.4"). It also cites arx37647, arx01006, arx24052, arx27607, arx24574 and arx34024, all coded G4 Q. R10-3 noted that the cell should become "S/Q" if zen22885291 were added.

**Fix.** Change the Codes cell to "S/Q". The certainty ("low") is unaffected.

## Counts

0 major, 0 minor, 1 nit (R11-1). R10-1 and R10-2 are FIXED. R10-3 is PARTLY FIXED; its residue is R11-1.

New major or minor problems remain: **no**
