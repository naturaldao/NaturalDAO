# Round 9: combined review (fidelity, consistency, balance, argument/arXiv)

**Scope**

- Paper and data: main.pdf, main.log, arxiv-submission.zip (all 5 Oct 06:15); sections/*.tex; data/evidence_coding.csv.
- Local full texts: scratchpad g1/22885291.txt, fulltext/2609.24574.txt, 2609.27678.txt, 2609.34024.txt, g4/2610.00381.txt, graz.txt, g1/23032384.txt.
- Focus: the sentences added in round 8, the remaining S/N pairs not reported in the text, and §§1, 5, 6 and 8 against the revised §4.
- Edits: this file is the only one I edited.

## Status of round-8 findings

| ID | Status | Note |
|---|---|---|
| R8-1 | FIXED | All four suggested sentences are present: zen22885291 in §4.1 and §4.6, arx24574 in §4.3, arx00381 in §4.6. Table 2 row 1 now cites zen22885291 and reads "better (low-cost); worse (best)". Wording issues in the new text are listed under R9-3, R9-6 and R9-7. |
| R8-2 | FIXED | §4.1 now reports arx24574 (14 of 15, median 11.6 macro-F1) and arx27678 (77.38%, below all seven hosted LLMs). §4.6 reports the arx34024 selective-prediction result. The G1 box now says "often below the best ones". |
| R8-3 | PARTLY | §4.4 now gives "None of the above" at 53.9% against 73.9%, and the Table 2 comparator cell is updated. However, the G4 box, Table 2's finding text and T2 still say that an explicit "none" is rarely chosen, citing arx34024. See R9-1. |
| R8-4 | FIXED | §4.4 now adds the "far better calibrated than a local generative baseline" and AUROC 0.744 results, and grazian's ChaosNLI ECE of 0.025. A wording nit remains (R9-5). |
| R8-5 | FIXED | "given the same single example per class (with eight examples the forest's F1 was slightly higher)". |
| R8-6 | FIXED | The arx27607 G4 rationale now reads "(holdout ECE 0.1235)". |
| R8-7 | FIXED | main.log now has no genuine "Label(s) may have changed" warning (only the intentional `\typeout`) and no undefined references. The PDF contains no "??". The zip contains the round-8 text. |

## Verification of the round-8 additions against the sources

All of the following are correct unless a finding is noted.

| Citation | Claim in text | Source | Result |
|---|---|---|---|
| zen22885291 (§4.1) | Highest AUROC of low-cost evaluators on all six binary tasks; a frontier model at 42–97× the cost beat it on two | Abstract; §6 ("Sonnet 4.6 beats Jev on … ANLI-R3 (−0.060 accuracy) and dialogue-grounded hallucination (−0.029 AUROC)") | Correct. Nit R9-6: one of the "two" is the three-way ANLI accuracy task, not one of the six binary tasks. |
| arx24574 (§4.1) | Trailed the best LLM on 14 of 15 preregistered annotation tasks by a median 11.6 macro-F1 | Abstract; §4.1 | Correct |
| arx27678 (§4.1) | Below all seven hosted LLMs (77.38%), at the lowest cost | Table 1 | Correct as point estimates. Nit R9-6: the gap against GPT-5.6 Luna is not significant. |
| arx24574 (§4.3) | Best calibrated of 22 models on Indian-English dialect text (ECE 0.063), single task | §4.3 ("lowest of all 22 models … next lowest is 0.181") | Correct |
| arx34024 (§4.4) | "None of the above" 53.9% against 73.9% | §3.4 | Correct |
| arx34024 (§4.6) | Selective prediction worse than a frontier model on two of three benchmarks | §3.3 (AURC 0.087 against 0.070, 0.303 against 0.080; PubMedQA favours Jev) | Correct |
| arx00381 (§4.6) | In distribution, risk–coverage curves beat a matched generative baseline | Table 2 AURC | Broadly correct. See nit R9-7. |
| zen22885291 (§4.6) | Escalation to an LLM helped in 2 of 30 cascades, "so its author recommends routing that band to a person" | §5 and §12 | Recommendation's scope dropped; see **R9-3**. |
| zen23032384 (§4.4) | Preregistered; far better calibrated than local generative baseline; AUROC 0.744 | Abstract; §7 | Correct |
| grazian2026calibrated (§4.4) | Tuned prompt, ECE 0.025 on 612 ChaosNLI items | Blog ("The ECE against the crowd is 0.025"; 612 αNLI stories) | Correct values. Subset and target are not stated; see nit R9-5. |
| arx01079 (§4.1) | Qualifier for k = 1 and k = 8 | §5 | Correct |

## Remaining S/N pairs not reported in §4

This round's check left 13 in-tally S/N pairs whose study is not cited in §4:
- arx23959 G1 S and arx38850 G4 S are cited elsewhere in the body.
- The rest are zen22846597 G1/G4 N, zen22864020 G3 N, zen22957049 G3/G4 N, zen22980293 G3 N, zen23065532 G3 N, alphaRAG G4 N, arx36154 G4 N, zen22922769 G4 N and zen22995519 G7 S.

Adding any of these pairs would not change how any answer box reads:
- The G3 N items add to the box's existing negatives: order, renaming and rewording effects, and open models.
- arx36154 (hosted Jev, poorly calibrated on accelerometer windows) fits "calibration is local" and §4.1's "not text" paragraph.
- zen22995519 is a weaker-design study by its own author.

Some pairs whose study **is** cited in §4 are still not reported for the requirement they are coded under. These do affect the reading of the G4 box; see R9-2.

---

### R9-1 [minor] "Explicit 'none' … rarely chosen" now contradicts the §4.4 sentence it cites (R8-3 carried)

**Location:**
- G4 answer box: "an explicit ``none'' or ``I don't know'' option is rarely chosen when it is correct";
- Table 2 row "Explicit ``none''/``I don't know'' rarely chosen when correct" (sources arx34024, arx39496, arx01006);
- 05_synthesis.tex T2: "explicit ``none'' or ``I don't know'' options are rarely chosen when correct~\cite{arx34024,arx39496}".

**Problem.**
- §4.4 now reports from arx34024 that Jev chose "None of the above" on 53.9% of the items where it was correct (source §3.4: "53.9% (62/115)").
- The one study cited for "none" being rare in a natural setting therefore shows it chosen more often than not.
- What remains for "rarely" is:
  - "I don't know" at 10.5% (arx34024);
  - "None" at 7% when recognising it required arithmetic (arx39496).
- A reader checking the box against §4.4 will see the contradiction.
- The abstract, introduction and conclusion say "insufficient" and are fine.

**Fix.** In the G4 box, T2 and the Table 2 finding, write "an explicit ``I don't know'' or ``insufficient'' option is rarely chosen when it is correct, and ``none'' only inconsistently (54\% on a medical benchmark, 7\% when arithmetic was needed)", or restrict the claim to "I don't know"/"insufficient". Alternatively, keep "none" but move arx34024's "none" result out of the support for "rarely".

### R9-2 [minor] The G4 box's "though not than the best frontier models" is one-sided, and two of G4's three S codes do not appear in §4.4

**Location:** G4 answer box ("usually better than generative models' stated confidence though not than the best frontier models"); §4.4 "Calibrated where the task is familiar"; Table 2 row "Well calibrated … better or mixed".

**Problem.** Three studies in the corpus compare Jev's calibration with a frontier model. Only the unfavourable one is reported.
- **arx24574 (reported).** Three frontier Claude models had lower median ECE (0.066 against 0.157). The coded rationale notes that the intervals overlap.
- **arx34024 (not reported for G4).** On MetaMedQA, Jev's probabilities were "the best calibrated (ECE 0.063 vs 0.146 …; difference −0.083, 95% CI −0.100 to −0.064)" and discriminated better (AUROC 0.845 against 0.801) than frontier GPT-6 Sol (§3.3). Discrimination was worse on DiagnosisArena (coded Q, mixed).
- **zen22885291 (G4 S, stronger; not reported for G4).**
  - Raw probabilities: the "lowest mean Brier score of any system". Jev was significantly lower than Sonnet 4.6 on 4 of 6 tasks and significantly higher in only 1 of 30 pairings.
  - After recalibration, Sonnet was lower (0.071 against 0.076) (§4, Table 9).
- **arx00381 (G4 S; not reported in §4.4).** It reports lower ECE than a matched generative baseline. Of G4's three S codes, only arx00381's G6 result (AURC, under "Thresholds and gates") appears anywhere in §4, and zen22885291's G4 Brier result appears nowhere.

**Effect.**
- On the evidence the paper itself codes, the frontier comparison of calibration is mixed:
  - one frontier model was better, with overlapping intervals;
  - in one study Jev was significantly better than the frontier model;
  - in one study Jev was better on raw probabilities and roughly equal after recalibration.
- So "not than the best frontier models" overstates one study.
- §4.4 shows the reader none of G4's S-coded results.

**Fix.**
- **Box:** write "usually better than generative models' stated confidence, and mixed against frontier models".
- **§4.4:** add one sentence: "On a medical examination benchmark its probabilities were better calibrated than a frontier reasoning model's (ECE 0.063 against 0.146)~\cite{arx34024}, and on seven public tasks its raw Brier score was the lowest of six systems, though a frontier model matched it after recalibration~\cite{zen22885291}\zmark{}."

### R9-3 [minor] zen22885291's escalation result is reported without its scope and placed as a counterweight it does not provide

**Location:** §4.6 "Thresholds and gates": "…but on medical benchmarks \jev{}'s selective prediction was worse … and in another study escalating \jev{}'s uncertain band to an LLM helped in only 2 of 30 cascades, so its author recommends routing that band to a person~\cite{zen22885291}".

**What the source says (§5 and §12).**
- The two significant cascades were both escalations to the frontier model: "HaluEval-QA via Sonnet-4.6 … HaluEval-Dial. via Sonnet-4.6".
- The recommendation is explicitly scoped: "**Within the cheap tier**, the operational recommendation is therefore to route Jev's uncertain band to a human rather than to a larger model; frontier second stages help on the two inference-heavy tasks at 42–97× the per-item cost".
- The same study finds Jev's own risk–coverage curves monotone, at 98.6% accuracy on 80% coverage on ToxicChat, and concludes that this "makes selective prediction practical".

**Problem.**
- Placed after "but", the sentence reads as evidence against confidence-based deferral and as an unqualified recommendation for human routing.
- The study actually supports Jev's confidence-based deferral. Its negative result concerns cheap peer escalation, which matches the G6 box's "escalating to peer models preserved confident errors".
- Its exception (a frontier second stage helped where inference was needed) matches the box's "stronger reasoning model".

**Fix.** Move the sentence to "Escalation among peers" and qualify it: "Escalating \jev{}'s uncertain band to a low-cost LLM never helped significantly; only a frontier model, at 42--97 times the cost, helped, on 2 of 30 cascades, so within the low-cost tier the author recommends routing that band to a person~\cite{zen22885291}\zmark{}". Optionally, add its monotone risk–coverage result to the arx00381 sentence.

### R9-4 [nit] Table 2 row 1 "Codes" cell says Q but the cited studies are coded S, Q, Q, N and N

**Problem.**
- The caption defines *Codes* as "the cited studies' codes for the finding stated".
- For G1, the sources are coded:
  - arx29429 Q and arx00346 Q;
  - zen22885291 S;
  - arx24574 N and arx27678 N.
- The cell should therefore read "S/Q/N", matching the style of the "Q/N" rows.

### R9-5 [nit] The grazian ChaosNLI figure is set beside zen23032384 without noting that subset and target differ

**Problem.**
- "with a prompt tuned to the dataset, a blog test found ECE 0.025 on 612 ChaosNLI items" reads as the same data as zen23032384. That study used the 3,113 SNLI/MNLI items, three-way.
- The blog used the two-way αNLI subset and scored against the crowd's share over all items, not on the most-disagreed quarter.

**Fix.** Write "on 612 two-way αNLI items, scored against the crowd's share".

### R9-6 [nit] Two point-estimate phrasings in §4.1

- **zen22885291.** "beat it on two": one of the two is ANLI-R3 accuracy, the three-way seventh task, not one of the six binary tasks named just before. "on two of the seven" would be exact.
- **arx27678.** "below all seven hosted LLMs" is true of the point estimates. The paired gap is not significant against GPT-5.6 Luna (CI −0.05 to 3.11). Consider "below all seven hosted LLMs, significantly so against some".

### R9-7 [nit] arx00381 "risk–coverage curves beat" a matched baseline

**Problem.**
- AURC is lower on three of four task families and unchanged on regression (0.2272 against 0.2280).
- The baseline's probabilities are reconstructed. For counting, its curve is flat at error 1.0 by construction, which the authors call "a failure of the reconstruction".

**Fix.** "were lower on three of four task families" would be exact.

## Sections 1, 5, 6 and 8 against the revised §4

**Consistent with the revised §4:**
- Abstract and introduction ("rank risky content well … at a fraction of the cost"; "an explicit ``insufficient'' option is rarely chosen"; "not generally worse").
- T4 ("escalation can also work, when the next stage is a stronger reasoner").
- Design element 3 (escalation to a stronger reasoning model).
- §8.

The new §4.1 caveat ("often less accurate than the best LLMs") appears in the G1 box and Table 2 but not in the abstract or thesis. It is acceptable, because those sentences claim ranking at low cost, not parity with the best models.

**Inconsistent:** the only inconsistencies are the "none" wording in the G4 box, T2 and Table 2 (R9-1), and the G4 box's frontier clause (R9-2).

## Counts

0 major, 3 minor (R9-1, R9-2, R9-3), 4 nits (R9-4 to R9-7).

New major or minor problems remain: **yes** (three minor; no major).
- **R9-1:** "none rarely chosen" is contradicted by the arx34024 figure now in §4.4.
- **R9-2:** the G4 box's frontier clause is one-sided, and G4's S-coded results are not shown.
- **R9-3:** zen22885291's escalation result is reported without its "within the cheap tier" scope and with the wrong valence.

Each can be fixed with a clause-level edit.
