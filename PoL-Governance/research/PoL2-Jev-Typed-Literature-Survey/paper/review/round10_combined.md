# Round 10: combined review (fidelity, consistency, balance, argument/arXiv)

**Scope**

- Paper and data: main.pdf, main.log, main.bbl, arxiv-submission.zip (all 5 Oct 06:20); sections/*.tex (04_evidence.tex and 05_synthesis.tex at 06:20); data/evidence_coding.csv.
- Local full texts (scratchpad): g1/22885291.txt, fulltext/2609.34024.txt, g4/2610.00381.txt, g4/2609.39496.txt, graz.txt.
- Focus:
  - the round-9 fixes;
  - every sentence added or changed in round 9;
  - whether the abstract, §1, §5, §6, §8 and Table 2 agree with the revised G4 box;
  - a fresh pass that does not re-raise items resolved in earlier rounds.
- Edits: this file is the only one I edited.

## Status of round-9 findings

| ID | Status | Current text / note |
|---|---|---|
| R9-1 | FIXED | The G4 box now reads: "an explicit ``I don't know'' option is rarely chosen when it is correct, and ``none'' is chosen inconsistently". T2 (05_synthesis.tex:19) reads: "``none'' only inconsistently (54\% of the time on a medical benchmark, 7\% when recognising it needed arithmetic)". The Table 2 finding reads: "Explicit ``I don't know'' rarely chosen when correct; ``none'' inconsistently". None of these now conflicts with §4.4's 53.9%. |
| R9-2 | FIXED | The box now reads "usually better than generative models' stated confidence and mixed against frontier models". §4.4 (l.141) adds arx34024 (ECE 0.063 against 0.146), zen22885291 (raw Brier lowest; a frontier model matched it after recalibration) and arx00381 (lower calibration error than a matched baseline). All three S codes for G4 are now shown. Wording nits remain; see R10-1 and R10-2. |
| R9-3 | FIXED | The sentence has moved to "Escalation among peers" (l.218): "escalating \jev{}'s uncertain band to a low-cost LLM never helped significantly; only a frontier model, at 42--97 times the cost, helped, on 2 of 30 cascades, so within the low-cost tier its author recommends routing that band to a person". The monotone risk–coverage result is added under "Thresholds and gates" (l.223). |
| R9-4 | FIXED | Table 2 row 1 Codes = "S/Q/N". |
| R9-5 | FIXED | "ECE 0.025 on 612 two-way $\alpha$NLI items from ChaosNLI, scored against the crowd's share over all items". |
| R9-6 | FIXED | "beat it on two of the seven"; and arx27678 is now "below the point estimates of all seven hosted LLMs, though not significantly below every one". |
| R9-7 | FIXED | arx00381's AURC is now "lower than a matched generative baseline's on three of four task families". |

## Verification of round-9 sentences against the sources

| Citation | Claim in text | Source | Result |
|---|---|---|---|
| arx34024 (§4.4) | Better calibrated than a frontier reasoning model, ECE 0.063 against 0.146 | §3.3: "best calibrated (ECE 0.063 vs 0.146 with medium reasoning; difference −0.083, 95% CI −0.100 to −0.064)"; abstract | Correct. This holds on MetaMedQA only. See R10-2. |
| arx34024 (§4.4, T2) | "None of the above" 53.9% (T2: 54%) against 73.9%; "I don't know" 10.5% against 8.6% | §3.4: "53.9% (62/115)", "10.5% (17/162…)", "missing-answer recall (73.9%)", "8.6% with medium reasoning" | Correct |
| zen22885291 (§4.4) | Raw Brier lowest of all systems tested; a frontier model matched it after recalibration | §4: "lowest mean Brier score of any system (0.103 vs. 0.122 for Haiku…)"; "0.071 for Sonnet, which is lower than Jev's [0.076]"; abstract: "the gap … closes against Sonnet" | Substantively correct. See R10-1: the figures cover six tasks, and Sonnet was slightly lower after recalibration rather than equal. |
| zen22885291 (§4.6) | Risk–coverage curves monotone on seven public tasks | §4: "its risk-coverage curves are monotone"; Table 10 covers the six binary tasks | See R10-1, same scope point |
| zen22885291 (§4.6) | Low-cost escalation never significant; frontier helped on 2 of 30; within the low-cost tier the author recommends routing to a person | §5: "only 2 are significant … (HaluEval-QA via Sonnet-4.6 …; HaluEval-Dial. via Sonnet-4.6 …)"; "Within the cheap tier, the operational recommendation is therefore to route Jev's uncertain band to a human" | Correct (GPT-5.4, also non-cheap, had no significant gain either, consistent with "only a frontier model") |
| zen22885291 (§4.1) | Frontier model at 42–97× cost beat it on two of the seven | Abstract; §6 | Correct |
| arx00381 (§4.4) | Lower calibration error than a matched generative baseline | Table 2/Table 7 (ECE 0.0806 vs 0.2589 class.; 0.0114 vs 0.2981 multi-label; 0.0408 vs 0.4204 counting); CSV: regression 0.0913 vs 0.1267 | Correct |
| arx00381 (§4.6) | AURC lower on 3 of 4 families | Table 7; CSV (regression 0.2272/0.2280 unchanged) | Correct |
| arx39496 (§4.4, T2) | "None" 7% while 99% answer-present; threshold raises to 79% | Abstract; Fig. 1 | Correct |
| grazian2026calibrated (§4.4) | ECE 0.025 on 612 two-way αNLI items, against crowd's share | Blog: "αNLI part of ChaosNLI … two hypotheses"; "test set of 612 stories"; "The ECE against the crowd is 0.025" | Correct |
| arx24574, arx27678 (§4.1) | Re-worded qualifiers | As verified in round 9 | Correct |

## Consistency of other sections with the revised G4 box

**Abstract (l.6), §1 (l.32) and §8 (l.6, l.10).** All say an explicit "insufficient" option "is rarely chosen". This matches the box's "I don't know" clause, and none of these sentences mentions "none". Consistent.

**§5 T2.** Matches the box exactly (see R9-1).

**§6.** No frontier-calibration claim. Criterion 5's "recall of insufficient at least 0.5" is unaffected. Consistent.

**Table 2.**
- The "I don't know / none" row and row 1 are consistent with the text.
- The row "Well calibrated on familiar closed-choice tasks; calibration is local" still cites only arx37647, arx01006, arx24052 and arx27607. The box's new frontier clause therefore has no Table 2 row or source (nit R10-3).

**Build.**
- main.pdf contains the revised wording: "mixed against frontier", "two of the seven", "within the low-cost tier" and "inconsistently". It has no "??".
- main.log has no undefined references and no "may have changed" warnings. The overfull boxes are at most 3.1pt, and the "Infinite glue shrinkage" notes are the known ones from earlier rounds.
- The zip's 04_evidence.tex differs from the source only in figure paths and stripped comment rules, which are expected clean-room transformations.

---

### R10-1 [nit] zen22885291 scope: "seven public tasks" for Brier and risk–coverage results that cover the six binary tasks; "matched" understates Sonnet's post-recalibration edge

**Location:** 04_evidence.tex l.141 ("on seven public tasks its raw Brier score was the lowest … though a frontier model matched it after recalibration") and l.223 ("monotone on seven public tasks").

**Evidence.**
- Table 8a is the "Mean over the six binary tasks". Table 10 lists six tasks.
- After Platt scaling, Sonnet's Brier is 0.071 against Jev's 0.076: "lower than Jev's".

**Fix.**
- Write "on six public binary tasks".
- Write "though a frontier model matched or slightly bettered it after recalibration".

### R10-2 [nit] "Other frontier comparisons favour \jev{}" generalises arx34024 from one of its three benchmarks

**Location:** l.141.

**Evidence.** The calibration advantage is on MetaMedQA only. On DiagnosisArena the ECE "did not differ significantly" (0.105 vs 0.084). On PubMedQA the "three models behaved similarly (ECE 0.140-0.141)". The study is coded G4 Q, mixed in the CSV.

**Fix.** Add "(similar on two other medical benchmarks)" after the ECE figures, or write "Two other frontier comparisons partly favour \jev{}".

### R10-3 [nit] Table 2's calibration row does not carry the box's new frontier clause

**Location:** Table 2, row "Well calibrated on familiar closed-choice tasks; calibration is local" (comparator "better or mixed").

**Problem.** The comparator wording is compatible with the box. However, the frontier studies that now underpin "mixed against frontier models" (arx24574, arx34024, zen22885291) are not among the row's sources.

**Fix (optional).** Add them to the Sources cell. If so, update the Codes cell to "S/Q" (zen22885291 is coded G4 S).

## Fresh pass

Beyond the three nits above, I found no new fidelity, balance, consistency or arXiv-compliance problems:
- The new §4.4 sentence is balanced by the adjacent arx24574 caveat, and §4.6 keeps the arx34024 selective-prediction counterweight.
- The G4 box's code tallies (S 3, Q 29, N 13) and the G1 box were not changed and still match the earlier verification.

## Counts

0 major, 0 minor, 3 nits (R10-1 to R10-3). All seven round-9 findings are FIXED.

New major or minor problems remain: **no**
