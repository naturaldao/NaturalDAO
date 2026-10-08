# Round 7: combined review (fidelity, consistency, argument, arXiv moderation)

Scope: main.pdf (65 pp., built 5 Oct 00:02, the same time as the newest section files, grey.bib, main.bbl, arxiv_metadata.txt and arxiv-submission.zip), sections/*.tex, data/*.csv, the PoL2 local copies and the local full texts (scratchpad fulltext/, g4/, root-level copies, zf/, papers/_local/). Web fetching was unavailable this round (session limit), so every check below was made against local copies. The only file I edited is this one.

## Status of round-6 findings

| ID | Status | Note |
|---|---|---|
| R6-1 | FIXED | The calibration counter-finding is now reported. §4.3 says the "domain-fine-tuned specialists beat Jev in medicine but reached 92% … and were worse calibrated there (12.08% against 5.57%)". The medicine result is attributed to the specialists, not the general model. T3 says "Chinese models initialised from Laya … after domain fine-tuning, in medicine". |
| R6-2 | FIXED | The grey.bib note now reads "v0.1 released 2026-09-26 (did not test Jev); cited figures from v0.2.0, released 2026-09-28, commit 7cd0164". The same text is in main.bbl, in the PDF reference [134] and in the bbl inside arxiv-submission.zip. §4.3 now reports like with like: voice routing 1.9% against 10.8%, and customer service 2.9% against 20.6%. |

## Consistency checks (all pass)

- **Metadata abstract.** arxiv_metadata.txt matches the PDF abstract word for word. The only difference is that pdftotext drops the κ glyph. The Comments line says 65 pages and 7 figures, which matches pdfinfo and the figure count.
- **Fig. 1b.** Columns sum to arXiv 107, Zenodo/alphaXiv 46 (44 + 2) and grey 8, for 161 in total. Every per-requirement n matches Fig. 2 and the answer boxes.
- **Fig. 2 and §4.8.** S 16, Q 99, N 46. I recomputed the subsets from evidence_coding.csv:
  - stronger design only: 7 / 45 / 27;
  - without Zenodo: 13 / 77 / 27;
  - Zenodo N 19 of 44, arXiv N 23 of 107.
- **Comparators.** Overall: 23 better, 17 similar, 28 mixed, 8 worse. Within N codes: 1 / 4 / 3 / 6, with 32 none. G1: 6 of 21 better or similar, 10 mixed, 5 worse. G4: 9 of 18 better, 2 worse. All match.
- **Quality appraisal.** 92 appraised sources (96 rows minus 4 excluded): 37 stronger, 17 moderate, 38 weaker. Matches §3.5.
- **Coder agreement.** 26 of 30 agree, κ = 0.717, and a bootstrap 95% CI of about 0.41–0.94. The first coder's codes are S 3 / Q 23 / N 4. Matches §3.4.
- **Fig. 3b.** 238/328 = 72.6%, 240/328 = 73.2% and 185/285 = 64.9%. Consistent with the text ("64.9–73.2%").
- **Fig. 5c.** Six panels are negative, from −0.1 to −7.3, and the maximum is +1.5. Consistent with arx29769 ("trail it on six of nine panels, by 0.1 to 7.3 points").

## Source claims spot-checked this round (not in the round-4, round-5 or round-6 lists)

| # | Source | Claim in paper | Result |
|---|---|---|---|
| 1 | arx26550 | Cascade +0.93 pt (CI 0.24–1.66) at 41.4% of the fee on 1,610 held-out pairs; 83% from RewardBench (1,340/1,610); JudgeBench −0.74; live test on 570 pairs with 100 local labels per workload matched GPT-6 exactly at 75.5% of the fee | Correct |
| 2 | arx27535 (KITE) | Cost ratios 8× (Luna) and 312–455× (Astra); a million agents in under a second (20 steps in 0.9 s); coverage 0.93/0.96; preregistered primary gain not shown | Correct |
| 3 | arx29429 | 63× cheaper pooled at list prices, about 12× (12.1×) under conservative repricing | Correct |
| 4 | arx00437 (JevSpawn) | Hosted Jev variant took 1.4–2.1× as long end to end, including API calls, as local Qwen scoring | Correct (verbatim "1.4 to 2.1 times as long … including API communication") |
| 5 | arx23136 | A hosted low-cost generative model was billed less than Jev (DeepSeek US$0.001262 against Jev US$0.002125) | Correct |
| 6 | arx31142 (JevAdvBench) | Opinion flips 12.1% [8.5, 15.5], tied with authority impersonation (10.1%, the strongest command, spliced into the question); rewording within 1.2 pp of noise; 0.8 gate passes 12.6% of flips; 38.0% of confident answers pushed below 0.8 | Correct |
| 7 | arx29769 | 242/252 (96.0%) against 50.3%; 12 errors × 7 panels; cascade gain at most 1.5 pt; below best single judge on 6 of 9 panels | Correct; but see R7-1 (balance) |
| 8 | arx37647 | Option rotation leaves accuracy unchanged (calculation-heavy MMLU, 94.3% → 94.3%); all three models degrade on low-resource languages | Correct |
| 9 | arx30216 | 2,170 projects as of 22 Sep; Choice 81.0%, Noul 72.2%, Score 45.4% | Correct |
| 10 | arx23886 / arx23959 | Training uses cross-entropy plus a Brier term | Correct: a "convex combination" in arx23886 and "CE+Brier" in arx23959 |
| 11 | arx24574 (for the REINFORCE sentence) | An open RLCD implementation uses a REINFORCE loop rewarding outcome minus probability; the vendor publishes the objective, not the reward | Correct as a secondary description, l.133–136 |
| 12 | arx26758 / arx32160 | Laya is ModernBERT with a marker token; Open-Jev is DeBERTa-v3; up to 255 options | Correct |
| 13 | Vendor jaggedness page | Nine failure modes, including literal reading, math, dates, indirection, large state, adversarial content and contradictory instructions | Correct (the other two are option order and generation) |
| 14 | arx00213 | Residual identifiers after two redaction passes in 25/58 = 43% of fetal-harm narratives and 152/407 = 37% of the adjudication sample | Correct |
| 15 | arx35286 (Loi) | Jev scored on a different (native 0–4) rubric; small interactions; the author declines to rank it | Correct |
| 16 | arx01231 (Hill) | A conceptual Jevons argument that cheap evaluation may increase total evaluation and exception handling | Correct |
| 17 | arx35293 | With a supervised layer, Jev matched the best systems on valence-arousal | Correct, and conservative: the source reports the lowest aggregate RMSE (1.0645) of any participating system |
| 18 | zen23038928 / zen22959854 | Attacks reinforcing an existing mistake could pass a gate (38 boosted mistakes at a threshold of 50; 0.47 → 0.89) | Correct |
| 19 | PoL2 en_7 / en_4 / en_5 | Art. 7(2)–(3) anomaly detection and risk warning; Art. 8 "must immediately discuss"; Art. 11 questioning period and archive; the weapons ban is under §4.3.2; the §5.5 "hate attack on humanity's core ethic"; §5.6 per-person quantification | Correct |
| 20 | §5 regulatory paragraph | AI Act Art. 5(1)(c) and (f), Art. 14, Art. 86 (Annex III, legal or similarly significant effects); GDPR Art. 22(1) and (3) (contract or explicit consent); DSA Art. 17 (hosting providers) and Art. 20 (online platforms); OJ references and dates | Correct paraphrases |

### Figures against captions

- **Figs. 1–5.** Each was checked against its caption and the text (see the consistency checks above).
- **Fig. 6.** Its elements and labels match §6, elements 1–7.

### arXiv

- Tone is neutral.
- cs.CY primary with a cs.AI cross-list remains appropriate.
- The submission bundle matches the build.
- No moderation concern beyond the low residual risk noted in earlier rounds.

---

### R7-1 [minor] The rubric-judge study is reported only for its negative half

**Location:**
- §4.6 "Escalation among peers" (04_evidence.tex);
- the abstract, §1 Thesis and §8, which all carry "peer evaluators repeated almost all of them";
- §6 elements 3 and 6.

**Problem:**
- **What the paper reports from arx29769.** It reports only correlated errors and the cascade's lack of gain.
- **What the same study also finds.** The headline result of its abstract and §4 is "Jev can often stand in for them". The three flash-tier LLM evaluators "cost 16 to 325 times as much and take 28 to 350 times as long, yet … Jev's accuracy differs significantly from theirs in at most 8 of 27 paired comparisons, ahead mostly on binary checklist criteria and behind only on ordinal ones".
- **Where it is missing.** This favourable result is coded (G1, Q, "mixed") in evidence_coding.csv and counted in the tallies. It appears nowhere in the body text.
- **Why it matters.** The study enters the abstract and the conclusion as an argument against typed judges. A reviewer checking the paper's claim of a symmetric assessment would ask for the other half, especially since the source's own conclusion is that both kinds of judge "err alike", which supports the paper's "not generally worse" line.

**Fix:** In §4.6, before "On Jev's 12 most confident errors…", add: "In the same study, Jev's accuracy differed significantly from three flash-tier LLM evaluators in at most 8 of 27 paired comparisons, ahead mostly on binary and behind only on ordinal criteria, at 16–325 times lower cost; but [continue]". Optionally cite arx29769 in §4.1 "Zero-shot ranking" as well.

### R7-2 [minor] Non-text detection reports only the unfavourable network-traffic study

**Location:** §4.1, paragraph "Where the evidence is not text" (04_evidence.tex).

**Problem:**
- **What the paragraph says.** On numeric network-flow features it cites only arx00376: zero-shot Jev scored below the majority class and stayed far below tree models even with 150 examples.
- **The omitted study.** Jev-IDS (arx01079, ref. [164]) also tests hosted Jev on numeric flow records. It is coded G1 Q in evidence_coding.csv but cited in the body only for cost (§6).
- **What Jev-IDS finds.** On a 300-flow NSL-KDD pilot (Table 2, three seeds), Jev with one labelled example per class in context reached F1 0.856 (precision 0.953). That is:
  - slightly below Gemini 3.6 Flash (0.880);
  - on a par with a random forest given eight examples per class (0.865);
  - with about 43 false alarms against about 764 for a random forest given one example per class;
  - with novel-attack recall of 0.747 against 0.713 for the generative model.
- **Effect on the reader.** The tasks differ (application classification against intrusion detection), but as written the reader learns only that Jev failed on numeric flows.

**Fix:** Append: "On intrusion detection from flow records with one labelled example per class in its context, it reached F1 0.856, slightly below a low-cost generative model (0.880) but with far fewer false alarms than a random forest given the same labels~\cite{arx01079}." Use the body-table figures, not the abstract's (0.859, which disagrees with the body).

### R7-3 [nit] The latency range in §2.1 excludes a figure the paper cites inside it

**Location:** §2.1 "Cost and latency", and §4.7.

**Problem:** §2.1 says independent client-side medians "range from about 150 to 500 ms" and cites [30] (arx00346) among the sources. §4.7 reports from the same [30] "a median latency of 138 ms".

**Fix:** Write "about 140 to 500 ms", or "from under 150 to about 500 ms".

### R7-4 [nit] The one favourable calibration grey source is coded but not mentioned

**Location:** §4.4 "Calibration is local".

**Problem:**
- **What the source finds.** grazian2026calibrated (grey, G4 Q, stronger design) found held-out ECE of 0.027 on 3,066 WiC pairs and 0.025 on 612 ChaosNLI items. This was after the Jev prompt was tuned separately for each dataset, and the author stresses that tuning is critical.
- **What the paragraph reports instead.** It reports only the unfavourable ChaosNLI result (0.339 on the most-disagreed quarter, zen23032384).
- **Why it is only a nit.** The source supports, rather than contradicts, the "calibration is local" reading.

**Fix:** Optionally add: "after per-dataset prompt tuning, one blog reported ECE near 0.03 on WiC and pooled ChaosNLI~\cite{grazian2026calibrated}\gmark{}".

---

## Counts

0 major, 2 minor (R7-1, R7-2), 2 nits (R7-3, R7-4).

New major or minor problems: **yes**, two minor balance problems:
- R7-1: a favourable result in the same source is omitted while its unfavourable result reaches the abstract.
- R7-2: a favourable non-text study is omitted from the paragraph that reports the unfavourable one.

Both are fixable with one added sentence each. No major problem remains, and both round-6 findings are fixed.
