# Round 12: fidelity review of the update-search text (8 October)

**Scope**

- Text: new and changed text listed in `update_text_changes.md`: §3 "Update search"; §4 G1 Hatevolution sentence (04_evidence.tex l.52); G5 answer box (l.183); "Across requirements" (l.273); §4.9 `sec:update` with `tab:update` (l.276–364); `tab:keyfindings` rows marked $^{u}$ (l.378–379); §6 l.36 and checklist item 16 (l.67); §7 l.11, l.19, l.36; abstract; §1 l.35; §8 l.8; §9 l.21; Appendix B `tab:evidence-update`; Appendix C `tab:catalogue-update`; Appendix E "Update search of 8 October".
- Sources:
  - full texts in `scratchpad/update/` (arx2610.02267, 02293, 03324, 03387, 03935, 04985, 06625, 07177, 07327, 07730, 07953, 08829, 09188, 09683, 09896, 10321; zen22935043, 23075657, 23179064, 23221456, 23225893);
  - `scratchpad/hatevolution.txt`;
  - the data files: `evidence_coding_update_2026-10-08.csv`, `quality_appraisal_update_2026-10-08.csv`, `coder_agreement_update_2026-10-08.csv`, `papers_update_2026-10-08.csv`, `excluded_records_update_2026-10-08.csv`, `counts_update.tex`, `counts.tex`, `evidence_coding.csv`, `review/coding/adjudication_update.md`.
- Recomputation: I recomputed every tally with Python from the CSVs (in_tally = yes).
- Edits: this file is the only one I edited.

## Verified claims

### Counts and tables (all recomputed)

| Claim | Location | Result |
|---|---|---|
| 57 read (31 arXiv, 26 Zenodo); 48 coded (27/21); 6 context, 2 non-empirical, 1 excluded | §3, App. E | Correct against `papers_update` (31 arXiv) and `quality_appraisal_update` (57 rows: 49 in the coding file, 48 of them tallied; 6 context; zen23138396 and arx08089 non-empirical; zen23187206 excluded). See R12F-6 for the App. C mismatch. |
| Sets 30 / 5 / 13 | §3, §4.9 | Correct (distinct tallied docs by `set`) |
| 118 pairs, S 12 / Q 92 / N 14; stronger-design 5 / 45 / 9 of 59 | §4.9 | Correct |
| κ = 0.55 on 97 of 118 pairs; bootstrap CI 0.36–0.70; 21 disagreements, 11 resolved for the first coder and 10 for the second | §3 | Correct. I recomputed κ = 0.546; my bootstrap gave 0.37–0.70; all 118 resolved codes equal the final codes in the coding file. |
| `tab:update`, all cells: main window per requirement; update; in-window; main + in-window; comparator splits better/similar/mixed/worse; none; the All row (5/28/3, 21/127/49, 15/10/27/7; 59) | §4.9 | All match. The main per-axis values match `evidence_coding.csv` and `counts.tex` (16/99/46). |
| 18 in-window records, 36 pairs (S 5, Q 28, N 3); no requirement changes direction | §4.9 | Correct |
| Share negative: 12% against 29% | §4.9 | Correct (14/118; 46/161) |
| 14 negative codes: 9 with a comparator, 6 worse, 4 of them open-only | §4.9 | Correct. The open-only four are arx06744, arx07177 and arx02586/arx07327 on G4. |
| Across both sets, 37 of 60 negative codes lack a comparator | §4.9 | Correct (main 32 of 46 + update 5 of 14) |
| App. E search arithmetic: arXiv 10 + 4 + 1 + 31 = 46; Zenodo 9 + 7 + 3 + 25 = 44, plus 1 found through a companion link = 26 | App. E | Correct against `excluded_records_update` (4 arXiv excluded at title/abstract, 1 at full text; Zenodo 2 at title, 3 at abstract, 4 at full text) |
| Data statement: seven update files | §9 | All seven exist |

### Study claims (against the full texts)

**arx03324**

| Claim | Source | Result |
|---|---|---|
| Binary macro-F1 .826/.691/.738/.960 against Sol .897/.682/.776/.976 | Table 4 | Correct |
| LLMs significantly ahead on only one dataset | §6: "significantly outperformed all decision models only on Dynamic" | Correct |
| Three-class: Jev .532, Sol .604, TF-IDF .639 | — | Correct |
| Definitions change 2.8–27.9% of predictions; 8 gains and 8 losses of 28 comparisons; Jev least sensitive; CoPE loses on 3 of 4 datasets | §4.2, Table 7 | Correct |
| Decomposition: 6 gains and 11 losses of 30; Jev's gain matched by a tuned threshold | Key finding; App. G: "for Jev on Dynamic, both reach .845" | Correct |
| Cost $0.033 per 1K texts and 336 ms, against $1.177 and 1,426 ms for Sol; 1.6 points below Sol | — | Correct |
| Referral to Sol: .658→.729 and other values; below Sol alone on 2 of 3 datasets | — | Correct |

**arx07953**

| Claim | Source | Result |
|---|---|---|
| OLID F1 66.1 against Detoxify 65.7; accuracy 74.4 against 81.0 | Table 5 | Correct |
| AUROC .893/.902 | Table 7 | Correct |
| PluRule EMA 48.4 against the always-"no rules broken" baseline of 50.0 | Table 3 | Correct |
| Semantic policy labels −5.06 (CI 3.91–6.21) | — | Correct |
| ECE 14.9/33.2 without precedents and 9.7/20.2 with them | Table 16 | Correct |
| Confidence ≥0.8 gate: 71.9%/94.3%, 75.8%, 67.6% | Table 8 | Correct |

**zen23075657**

| Claim | Source | Result |
|---|---|---|
| 90.52% recall at 3.24% FPR; encoders 35.63–58.91%; human-subset FPR 5.39% above the 5% tolerance | abstract; Table R1a | Correct |

**arx04985**

| Claim | Source | Result |
|---|---|---|
| AUROC 0.95–1.0 on eight benchmarks; AI-text accuracy 78%→89% with a fitted threshold | l.909 | Correct |
| Attack success 100/100/97.2 and 100/100/97.0 | Table I | Correct |
| Poisoning 5–10% | — | Correct |
| 100% coverage of the private attributes | Table V | Correct |
| Surrogate agreement 49%→92% from 200 labels | App. C2 | Correct |

**arx02267**

| Claim | Source | Result |
|---|---|---|
| Injection AUROC .98; 25.5% of harmful requests passed; PII FPR 66→63% | — | Correct |
| Option reversal changes 1.8% of Jev's decisions against 30.3% of Laya's | — | Correct |
| Pre-screen saves only 4.3% | — | Correct |
| Held-out thresholds: extra misses in 47% of splits | — | Correct |

**arx03935**

| Claim | Source | Result |
|---|---|---|
| AgentHarm 84.54% against at most 85.57% (single run) | — | Correct |
| ECE 0.0532 against 0.0784–0.2526 on 10,938 questions of a bilingual benchmark | — | Correct |
| 89.35% of the mass on the mode, against a true 35.60% | — | Correct |

**arx10321**

| Claim | Source | Result |
|---|---|---|
| 96–100% against 15% for unbelted occupants | Table B.2 | Correct |
| 229,510 narratives | — | Correct |
| Same authors and reused data as arx24052 | appraisal | Correct |

**arx08829**

| Claim | Source | Result |
|---|---|---|
| 62.93% average, above 5 of 10 configurations; best 67.28%; cost 96.41% lower | — | Correct |
| CMMA: Jev 21.06 against 19.82–23.31 | Table 2 | Correct |
| Decomposition 62.93→57.31; appended judgements 61.61 | Table 3 | Correct |
| "Single-run" | appraisal | Correct |

**arx03387**

| Claim | Source | Result |
|---|---|---|
| Neutral identifiers cut Qwen2.5-7B's detection by 20.0 and 30.6 points | — | Correct |
| NONE option: 63.7%/3.3% for Jev against 45.0% for Qwen | — | Correct |
| 82.4% on DBpedia | — | Correct |
| OOS detection 84→75 as k rises 2→10 | — | Correct |
| 6 of 12 transfers above 5% | — | Correct |

**Other studies**

| Study | Claim | Result |
|---|---|---|
| arx02586 | Accuracy 0.1357 against a 0.5690 control | Correct |
| arx02293 | 0.039 against 0.366–0.590 | Correct |
| arx09188 | 94.8/90.6 and 86.7/72.0; escalation never helped | Correct |
| arx06625 | Lower ECE than Luna on 8 categorical tasks; Qwen 27B better on pairwise; Luna cheaper on 6 of 7 | Correct |
| arx09896 | ECE 0.0271 against 0.0307–0.0607 for three flagship LLMs; 678 of 5,000 failed | Correct (Gemma3's 0.0225 is a small local model, so it is correctly excluded) |
| zen23221456 | Brier 0.283 against 0.250; Qwen3.5-4B 0.232 against 0.249 | Correct |
| arx07730 | 62.8% against 17.5% of 382 | Correct |
| arx07327 | 28/30, 17/30; 90→113 of 120 | Correct |
| arx06425 | 29→84 of 120 | Correct |
| zen23189584 | Two live calls inside an author-built shell; no reasons | Correct |
| arx09683 | Matches the reasoner at 30% of its calls | Correct |
| arx07177 | Escalates 0.923–1.000 at the preregistered bar | Correct |
| zen23088660 | Gate fixed on 1,000 names and tested on 4,000 | Correct |
| zen23225893 | 94.6% against 62.4%; Danish risk 14.3% at a 5% target; Austria 1.3% at a 2% target | Correct |
| zen23179064 | 0.88 on 55/45 DICES items; worse than uniform | Correct |

**Hatevolution and other text**

| Claim | Source | Result |
|---|---|---|
| 6 of 20 models flip more than 10% | l.375 | Correct |
| Most models decline on hateful instances over 2017–2022 | l.331 | Correct |
| ρ from −0.3053 to 0.1909, all 90% intervals include 0 | Table 5 | Correct |
| Static benchmarks: mean ρ 0.36 | l.845 | Correct |

- Abstract (48 more sources), §1, §7 and §8: consistent with §4.9.
- Balance check: every requirement except G2, which has a single pair, is reported with both favourable and unfavourable update results.
- "Confirmed" or "qualified" labels against the coded rows: consistent. The G5 qualification is supported by arx03324 and arx08829 (decomposition did not raise accuracy) against arx07327 and arx06425.

## Findings

### R12F-1 [minor] Certainty rules applied asymmetrically to the escalation finding

- **Location:** 04_evidence.tex l.288, "No rating falls, and no other changes … or, like the calibration finding, combine results that point in different directions"; l.348–350, "The box stands, but the evidence that escalation saves cost without loss of accuracy is less consistent".
- **Rule (tab:keyfindings caption):** *low* requires "at least two studies with a consistent direction".
- **Evidence:**
  - With the update studies added, the escalation finding ("saves cost without loss of accuracy", main: arx26550, arx24574, arx02046) gains stronger-design results in the opposite direction:
    - arx07177 (preregistered, stronger): "escalates between 0.923 and 1.000 of items", l.48–49;
    - arx09188 (stronger): gated labels "lost 0.047 NDCG@10" (coding file);
    - arx02267 (stronger): the pre-screen saves only 4.3% (Table 2, l.251).
  - The paper uses inconsistency of direction to explain why the calibration finding does not rise. It does not apply the same test to whether the escalation finding falls.
- **Fix:** Do one of the following:
  - mark the escalation row "low; very low$^{u}$" and revise "No rating falls";
  - state why the new negatives are outside the finding's scope ("on readable judgements": a near-chance open evaluator, offline label allocation, a cost-only result), so that its direction remains consistent.

### R12F-2 [minor] A certification result is described as a threshold missing its target

- **Location:** 04_evidence.tex l.344, "Thresholds fixed in advance again missed their targets on new data: … a 5\% automatic tier was certified for \jev{} in none of 2{,}000 splits on one dataset~\cite{zen22935043}". The same study is an update source for "Fixed thresholds do not transfer" (tab:keyfindings l.378).
- **Source:** zen22935043 §4.5, l.456: "over 2,000 random splits of AG News, a 5% tier certifies for Jev" in none. This is a valid-bound procedure that declined to certify any threshold. No threshold was fixed in advance and then missed its target on new data. On SST-2 it certified in 191 of 2,000 splits (l.465). The study's actual miss is that "conformal single-label answers are wrong 5.93% of the time at a nominal 5%" (abstract, l.22).
- **Fix:** Use the 5.93%-at-nominal-5% result, or rephrase: "no 5% automatic tier could be certified for Jev on AG News (0 of 2,000 splits; 191 on SST-2)". Then move the sentence out of the "missed their targets" list. Re-check that zen22935043 still counts as a same-direction source for the moderate$^{u}$ rating. If it does not, three independent stronger-design studies remain: arx29429, arx00346, arx03387, plus zen23075657 and arx02267. The rating survives, but the source list should change.

### R12F-3 [minor] Exact-match accuracy is described as exact policy selection

- **Location:** 04_evidence.tex l.322, "it picked exactly the violated Facebook hate-speech policy in 29.4\% of cases without retrieved precedents (51.6\% with them)".
- **Source:** arx07953 l.224: EMA "requires the model either to identify the annotated violated rule or to correctly select No rules broken". l.498: on HateModerate "VRR from 27.6% to 54.3%"; 29.4% and 51.6% are EMA (Table 4).
- **Fix:** Use "exact-match accuracy on Facebook hate-speech policy selection was 29.4% … (51.6% with them)". Alternatively, give violated-policy recall: 27.6% → 54.3%.

### R12F-4 [minor] The only negative G1 code on hosted Jev is not reported

- **Location:** 04_evidence.tex l.326, "Two open typed models scored below the generative comparators on the same benchmarks~\cite{arx06744,arx07177}". This is the paragraph's only negative G1 sentence, and it concerns open models.
- **Source:**
  - arx09937 (G1, N, hosted, stronger): Jev's fault question "flagged 75–99% of fault windows but also 57–94% of fault-free ones (AUROC 0.65)", and "under the nine shift tests no model beat flagging every window (detection F1 0.71; Jev 0.67–0.70)" (coding file; Sec. 4.1–4.2).
  - It is the only G1 N code on hosted Jev, and the G1 row of `tab:update` counts it.
- **Fix:** Add one clause: "and in industrial fault detection hosted \jev{} flagged most fault-free windows and, under shift, did no better than flagging every window~\cite{arx09937}".

### R12F-5 [minor] The count of sources read in full omits the full-text exclusions; one exclusion is missing from the data file

- **Location:** 03_method.tex l.66, "We read \nUDocs{} sources in full … one reports no evaluation and was excluded"; E_codebook.tex l.76, "Of the 57 sources read in full, …".
- **Evidence:**
  - App. E l.73–75 itself reports 1 arXiv and 4 Zenodo exclusions "at full text". `excluded_records_update_2026-10-08.csv` lists them with stage = "full text": 2610.02516, 23019391, 23024634, 23048160, 23167634, plus the grey page trio-spark-v1.0. So at least 62 sources were read in full, not 57.
  - The one read-and-excluded source that is counted (zen23187206, `quality_appraisal_update` row 54: "Excluded: no evaluation") is absent from `excluded_records_update_2026-10-08.csv`. App. E says that file holds "records and reasons".
- **Fix:** Say "57 sources were read in full and retained for appraisal (a further 5 were excluded at full text)", or count all of them. Add zen23187206 to the excluded-records file.

### R12F-6 [minor] Appendix C counts context and non-empirical sources differently from §3 and Appendix E

- **Location:** C_catalogue.tex, `tab:catalogue-update`. Tier column: 48 Coded, 7 Context, 1 Non-emp., 1 Excluded.
- **Text:** §3 l.66 and App. E l.76 say "6 are context, two are non-empirical". `quality_appraisal_update` gives zen23138396 the design "non-empirical", and the paper counts it as non-empirical.
- **Evidence:** The table lists `\cite{zen23138396} & Continuous Cheat Detection … & Context`.
- **Fix:** Set zen23138396's tier to "Non-emp." in `tab:catalogue-update`, or change the text counts to 7 context and 1 non-empirical.

### R12F-7 [nit] An offensive-language dataset is called a hate-speech task

- **Location:** l.336, "On hate-speech tasks its probabilities were poorly calibrated … (ECE 14.9\% on OLID …)".
- **Source:** arx07953 Table 16 is "Detailed Direct and semantic-RAD Noul offensiveness results". OLID labels offensive language.
- **Fix:** "On offensive-language and hate-speech tasks".

### R12F-8 [nit] The escalation example omits a referral that lowered macro-F1

- **Location:** l.348, "raising hate-speech macro-F1 when a frontier model reviewed Laya's least certain fifth".
- **Source:** arx03324 App. I, l.2049: "referring the same fraction to Luna lowers HateXplain to .714" (from .730).
- **Fix:** Add "(GPT-6 Sol; referral to GPT-5.6 Luna lowered it on one dataset)".

### R12F-9 [nit] Security-benchmark accuracies also used a fitted threshold

- **Location:** l.324, "reached AUROC 0.95--1.0 on eight benchmarks, but accuracy on AI-generated text rose from 78\% to 89\% only with a threshold fitted on held-out examples".
- **Source:** arx04985 l.909: "On the six security benchmarks, its calibrated accuracy ranges from 87% to 99%". These accuracies also use the fitted threshold (coding file: "at a threshold fitted on 20–100 held-out calibration examples").
- **Fix:** Optionally add "(87–99% on the security benchmarks, also with fitted thresholds)".

### R12F-10 [nit] The thresholds were not themselves preregistered

- **Location:** l.344, "preregistered abstention thresholds held their target on the training registers".
- **Source:** zen23225893 Table 7. The hypotheses (H18, H22) were preregistered. The thresholds were fitted on validation ("Learn-then-Test abstention thresholds fitted on Norwegian and Austrian validation"). Only Austria was reported at 1.3% against a 2% target.
- **Fix:** "abstention thresholds fitted on the training registers held a preregistered 2\% target on Austria but gave 14.3\% risk against a 5\% target on an unseen register".

### R12F-11 [nit] A preregistered study is not considered for the "option names" rating

- **Location:** l.288, "the remaining findings gain no new preregistered or replicated stronger-design study in the same direction".
- **Source:** zen23179064 (preregistered, stronger) finds Choice's pull carried "almost all" by the option word "heads" (+0.354) rather than the key or position, with descriptions present (§4.1). It bears on "Option names can override definitions". However, the zero-evidence prior was its demoted framing (deviation 4), and the label-set analysis is not clearly among the preregistered tests.
- **Fix:** One clause in the change log or in §4.9 stating why zen23179064 does not raise that rating.

### R12F-12 [nit] Data-file inconsistencies outside the paper text

- `adjudication_update.md` l.6: "Five decisions are S and three are N". The decision table has six S: arx03324 G7, arx03935 G1, arx07177 G3, arx09188 G3, zen22941164 G4 and zen23005202 G1.
- `excluded_records_update_2026-10-08.csv` labels Zenodo records with `set` = "late-indexed", while the coding files use "re-screened" for the same category.
- **Fix:** Correct the count to six. Harmonise the set label.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | — |
| Minor | 6 | R12F-1 to R12F-6 |
| Nit | 6 | R12F-7 to R12F-12 |

New major or minor problems remain: yes
