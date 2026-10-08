# Round 2: fidelity-B (G4 to the end of §4, §5, §6, §7, App. D tab:corrections3, PoL2 quotations, App. A)

Scope note: this round-2 pass covers four things: the tallies (recomputed from data/evidence_coding.csv, rows with in_tally=yes), all PoL2 quotations against the local copies of commit 5791ae3, the regulatory paragraph, and follow-up on the round-1 findings. Four parallel source-verification passes were launched for G4, G5–G6, G7 with tab:keyfindings and tab:corrections3, and §5–§7 cite-backed claims. They had not reported back when this file was written. The per-number re-checks of the new v0.3 sources are therefore NOT included here and should be merged in a supplement. These sources are arx01006, arx39496, arx02076, arx01834, arx02048, arx02046, arx00346, arx00213, arx01079, arx01231, zen22849329, zen23041163, zen22959854 and zen23038928.

## Verified

Tallies (evidence_coding.csv, 161 in-tally rows)
- Overall S 17, Q 98, N 46; higher-quality 13 / 65 / 28 of 106 (04:284).
- G4 S 3, Q 29, N 13. There are 18 comparator pairs: better 9, worse 2 (04:142).
- G5 S 2, Q 3, N 3; G6 S 1, Q 23, N 4; G7 S 5, Q 12, N 2.
- Comparator results: better 24, similar 17, mixed 27, worse 8 (total 76) (04:285; 07 tab:certainty).
- 32 of 46 N rows have no comparator (04:286).
- Zenodo 19 of 44 N against arXiv 23 of 107 N (07:107).

PoL2 / Appendix A
- Every Chinese excerpt in tab:concordance is a verbatim substring of zh_1/4/5/7.md (checked by script, after quote normalisation as the appendix declares).
- Every English excerpt is verbatim in en_1/4/5/7.md, apart from the joins noted under R2-fidB-6.
- Body paraphrases faithful:
  - 02b: 1.4, 1.5, 4.3, 4.3.1, 4.3.2 (graded/hierarchical management, security-robot warnings, fabricated intimacy), 4.3.3, 4.3.3.1, 4.3.3.3.
  - 02b: 5.4 ("within"), 5.4.1 ("where necessary"), 5.5 ("may accept", covenant of publicization), 5.6 ("can").
  - 02b: Arts. 2(1) (with the collaboration premise), 4, 5(4)–(5), 6(3), 7, 8, 9(2), 9(3), 9(7), 10, 11.
  - 02b: seven contributors (Readme).
- T1, T2, T3, T4 and T5 clause quotations in 05_synthesis are faithful.

Regulatory paragraph (05:55–58)
- AI Act Art. 5(1)(f), Art. 5(1)(c) (now with the cumulative conditions), Art. 14 and Art. 86 (Annex III, legal or similarly significant effects, role of the system and main elements) are acceptable.
- GDPR Art. 22(1),(3) is acceptable, with the nit in R2-fidB-8.
- DSA Art. 17 (hosting providers) and Art. 20 (online platforms) are accurate.
- Santa Clara Principles (notice, reasons, appeal) are accurate.

Round-1 fixes confirmed

fidelity-B:
- Fixed: fidB-1, 2, 3, 4, 5, 6, 7, 8 (in G4), 9, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 32, 33, 34, 35.
- Fixed by removing the passage: fidB-10, 15, 28, 30, 31 and 36 (no longer in the body), and the uncited "cannot be self-hosted" claim (now cites arx28919).

arxiv-pol2 Part 2:
- Fixed: NEW-arx-14 (concordance now verbatim), 15, 16, 17, 18, 19, 20, 21, 22 and 23.
- Fixed in 02b and tab:corrections3: NEW-arx-25.

Not fully fixed: see R2-fidB-1, R2-fidB-2, R2-fidB-6 and R2-fidB-7.

## Findings

### R2-fidB-1 [minor]
- Location: 04_evidence.tex:205 (G5, "Chains that do and do not compose")
- Claim: "Asked through two interfaces, or through a hierarchy of coarse and fine questions, the same decision diverged in about a third of cases~\cite{arx37470,arx33971}"
- Source says: arx37470 reports 32.8% of cases with different actions. arx33971 reports a *mean category-level total variation* of 0.219–0.349 (as 04:163 now correctly states). It does not report a share of cases.
- Problem: This reintroduces the round-1 fidB-8(c) error (mean TV turned into a case share) in the G5 section.
- Suggested fix: "...diverged on 32.8% of act-or-defer decisions across two interfaces~\cite{arx37470}, and coarse probabilities reconstructed from fine answers differed from directly asked ones by a mean total variation of 0.22–0.35~\cite{arx33971}".

### R2-fidB-2 [minor]
- Location: 04_evidence.tex:200
- Claim: "two Zenodo documents argue that typed inference relocates accountability into whoever writes the schema and option set~\cite{zen22847531,zen22866847}"
- Source says (round 1, zen22866847): typed inference "can relocate the relevant commitments into types, schemas, rubrics, probability thresholds…".
- Problem: Round-1 fidB-29 was not applied. The hedge "can" is dropped, and so are rubrics and thresholds.
- Suggested fix: "...argue that typed inference can relocate governance commitments into the schema, option set, rubrics and thresholds".

### R2-fidB-3 [minor]
- Location: 04_evidence.tex:286 ("where comparators were run, the failures in G2 and G3 were mostly shared")
- Data says: G3 has 10 N rows, and none of them has a generative comparator. The G3 rows that do have a comparator are better 4, similar 2, mixed 2, and all are coded S or Q. G2 has 2 N rows with a comparator (similar, mixed).
- Problem: For G3 the statement has no basis in the coding. No G3 failure was compared, and where G3 comparisons exist the typed model was more often better.
- Suggested fix: "...where comparators were run, the G2 failures were shared (two studies); no G3 failure had a generative comparator."

### R2-fidB-4 [minor]
- Location: 04_evidence.tex:287 (typed-specific list) vs tab:keyfindings row "Explicit 'none'/'I don't know' rarely chosen when correct | N | similar"
- Data says:
  - arx34024 (G4): Jev 10.5% vs GPT-6 Sol 8.6%, so similar.
  - arx39496 (G4) is coded "worse": "reasoning Qwen3.5-9B reaches 100% in both conditions".
- Problem: There are two inconsistencies.
  1. §4.10 lists failing to "signal missing information" as specific to the typed interface, while the key-findings table codes the same finding as "similar" to generative models.
  2. The table's "similar" ignores arx39496's own comparator, where a reasoning generative model did far better. The G4 text (04:168) also omits that comparator.
- Suggested fix:
  - Table: change the comparator cell to "similar (frontier) / worse (reasoning model)".
  - 04:168: add "a reasoning generative model rejected correctly in both conditions".
  - 04:287: restrict the typed-specific claim to confidence inflation by option padding and the lack of reasons, or say "not signalled by confidence (no comparator)".

### R2-fidB-5 [minor]
- Location: tab:keyfindings (04:303, 311, 314); the codes and comparator columns compared with the coding of the cited sources
- Data says:
  - "Errors concentrate in sub-types… | N | worse/mixed | arx33401, arx00213". arx00213 is coded Q/none in every axis and arx33401 G1 is Q/mixed. No cited row is "worse".
  - "Separate 'is the evidence enough?' question… | S | arx01006". arx01006 is coded Q in all four axes. Its G6 rationale notes the sufficiency question "is 2–6 points less accurate as an acceptance filter".
  - "Thresholds set in advance miss… | N | arx00346, arx33843, zen23041163". Two of the three are coded Q for G6.
- Problem: The table's codes and comparator results do not follow from the study coding that the caption says they summarise. The S code for arx01006 also drops the source's caveat. The same caveat is missing from the G4 answerbox ("works much better") and from T2 ("far better than confidence").
- Suggested fix:
  - Align the codes with the coding, or state in the caption that table codes are synthesis judgements.
  - Change "worse/mixed" to "mixed".
  - Add "but less accurate as an acceptance filter" to the sufficiency row and to T2/04:141.

### R2-fidB-6 [nit]
- Location: A_concordance.tex: rows for Art. 4, Art. 8(1)–(2) and Art. 10
- Source says: Art. 4 has items 1–3 (the row quotes all three). Art. 10 quotes the lead-in plus items 1 and 4. For Art. 8, the Chinese column quotes only item 1 (随时建议…) followed by "……", while the English column gives items 1 and 2.
- Problem: The appendix's own rule ("Where a clause has numbered items, the item is given in parentheses") is not applied to Art. 4 and Art. 10; this is round-1 NEW-arx-24 item 2, partly unfixed. In the Art. 8 row the two language columns quote different extents: the Chinese omits 讨论义务：NaturalDAO在收到人类的建议时，必须马上与人类进行讨论, which is the item the body cites ("must discuss immediately").
- Suggested fix: Label the rows Art. 4(1)–(3) and Art. 10 (lead-in, 1, 4). Add item 2 to the Chinese Art. 8 cell.

### R2-fidB-7 [minor]
- Location: D_corrections.tex:83 (tab:corrections, the version 0.1→0.2 table)
- Claim: "Renumbered in commit \texttt{5791ae3} to 5.4.1, 4.3.x, 5.6"
- Source says: 5791ae3 is "Create sync-wiki.yml". The renumbering was made in 7750ceb–526da3d (round-1 NEW-arx-25), and tab:corrections3 (line 42) itself now records this as a correction.
- Problem: The older table still asserts the statement that tab:corrections3 retracts. Round 1 asked for this row to be changed too.
- Suggested fix: "Renumbered before commit 5791ae3 (commits 7750ceb–526da3d) to …".

### R2-fidB-8 [minor]
- Location: 02b_pol2.tex:7
- Claim: the framework "treats a model's refusal of its governance as a 'hate attack on humanity's core ethic' (§5.5)"
- Source says (en_5.md:150–151; zh_5.md:166):
  - "Any large language model may accept governance under 'Proof of Love2.'"
  - "...Accepting governance under the Proof of Love2 consensus mechanism therefore entails accepting a covenant of publicization. Otherwise, its behavior constitutes a hate attack on humanity's core ethic." (否则，其行为就是对人类核心伦理的仇恨攻击)
- Problem:
  1. "Otherwise" follows the publicization-covenant sentence, and the preceding bullet makes acceptance voluntary ("may accept"). The text therefore most naturally calls *non-public behaviour*, or failing the covenant, a hate attack, not refusal of governance as such. The paper's reading is the harsher one and is presented without the ambiguity.
  2. The quoted phrase is missing from tab:concordance (the §5.5 row stops at "covenant of publicization."), although Appendix A claims to quote every passage cited.
- Suggested fix: "...and describes behaviour outside the 'covenant of publicization' that governance entails as a 'hate attack on humanity's core ethic' (§5.5)". Add "Otherwise, its behavior constitutes a hate attack on humanity's core ethic." / 否则，其行为就是对人类核心伦理的仇恨攻击。 to the §5.5 row.

### R2-fidB-9 [nit]
- Location: 02b_pol2.tex:19
- Claim: the state of absence covers "numbness, distraction and misunderstanding"
- Source says (en_4.md:65): failing to produce emotional experience because of external factors (noise) or internal factors (illness), "the so-called 'feeling-nothing state'", plus "the confusion of failing to understand, or the misunderstanding caused by deviation in understanding".
- Problem: The source does not mention "distraction".
- Suggested fix: "covering the 'feeling-nothing state' (from noise or illness), confusion and misunderstanding".

### R2-fidB-10 [nit]
- Location: 02b_pol2.tex:40 ("NaturalDAO, an AI system 'presented in the form of a DAO'") and 7 ("banning the possession of weapons")
- Problem: Both are quoted or paraphrased from the text (Art. 5(5) lead-in / closing section; §4.3.2 second bullet) but are not in tab:concordance. The Art. 5(5) row starts with "\ldots", which omits exactly the quoted words.
- Suggested fix: Include "Presented in the form of a DAO" / 以DAO的形式呈现 in the Art. 5(5) row, and add the §4.3.2 weapons bullet, or drop the quotation marks.

### R2-fidB-11 [nit]
- Location: 05_synthesis.tex:57
- Claim: "where such decisions are permitted, [GDPR] requires at least the right to obtain human intervention… (Art. 22(1), (3))"
- Source says: Art. 22(3) applies to the exceptions in Art. 22(2)(a) and (c) (contract, explicit consent). For (b) (authorised by law) the law must lay down "suitable measures" (Art. 22(2)(b)).
- Problem: The sentence slightly overstates the scope of 22(3).
- Suggested fix: "where such decisions rest on contract or explicit consent, requires at least…".

### R2-fidB-12 [nit]
- Location: 05_synthesis.tex:55 (AI Act Art. 5(1)(f))
- Problem: The paragraph omits the exception for medical or safety reasons. It is relevant to T1 because §4.3.2's own example concerns security robots.
- Suggested fix: Add "(except for medical or safety reasons)".

## G4 source re-check (completed after the first draft)

The G4 pass re-checked lines 135–187 against the sources, using the local full texts and live fetches of Grazian and of Zenodo records 23032384 and 22848952. Every number matched its source. Verified:
- grazian 3,066 pairs, ECE 0.027, prompt tuned per dataset.
- arx37647: 27 datasets, 11 with non-overlapping intervals, pooled ECE 0.028 against an unweighted mean of 0.061, ANLI 73.9% → 86.9%.
- arx01006: 575,442 calls, SmoothECE 0.015–0.033, 8,132 of 9,960 questions kept with 20 errors, up to 0.80 on a salient option, AUROC 0.95 vs 0.85, 0.83 → 0.10.
- arx24052 and arx27607 recalibration figures, with the NLI baseline (0.1072 → 0.0063).
- arx24881: 0.666 and ECE 0.133.
- zen23032384 (preregistered): 0.076 → 0.339.
- arx33209, arx37470 (32.8% and 34.2%), arx33971 (0.219–0.349 and 0.424–0.689), yurin (738,164 answers; 0.20 → 0.58).
- arx34024: 17/162 answers, CI 6.7–16.2, 8.6%, 17 of 18.
- arx39496: 7%, 99%, 99%, 79%.
- zen22848952: conflict and ignorance in one band, separated in 4 of 4 cases.
- arx35342 (0.771 → 0.903; Noul and Score well calibrated) and arx02076.
- Captions (a)–(d).

### R2-fidB-13 [minor]
- Location: 04_evidence.tex:147
- Claim: "The largest benchmark in our corpus, 346,009 requests over 37 datasets"
- Source says: arx01006 reports "575,442 paid calls" (cited in the next sentence), and arx24052 reports about 2.4 million answers.
- Problem: It is not the largest benchmark by number of requests.
- Suggested fix: "The broadest benchmark in our corpus (37 datasets, 346,009 requests)".

### R2-fidB-14 [minor]
- Location: 04_evidence.tex:140 (answerbox) and 149
- Claim: "better calibrated than generative models' stated confidence"; "better calibrated than the stated confidence of 16 of 19 LLMs~\cite{arx24574}"
- Source says:
  - arx24574: "…16 of the 19 LLMs, yet three frontier models show lower median calibration error (0.157 against 0.066)".
  - arx24052: elicited GPT confidence had ECE 0.0027 against Jev's 0.0231, and "Calibration varies by model rather than by paradigm".
- Problem: The paper states this as a general fact but drops the authors' own qualifier. The frontier generative models were better calibrated in two corpus studies.
- Suggested fix: Answerbox: "usually better calibrated than generative models' stated confidence, though not than the best frontier models". Line 149: append ", though three frontier models were better calibrated (median error 0.066 vs 0.157)".

### R2-fidB-15 [minor]
- Location: 04_evidence.tex:152
- Claim: "(slope 1.63, Spiegelhalter z = −5.3: probabilities too close to the middle rather than over-confident)"
- Source says: arx24052: "the failure is a level shift rather than over-confidence … The probabilities also sit too high overall, with a mean of 4.8% against a weighted base rate of 2.7% … an over-statement of about 80%". Highlight: "overstate prevalence until recalibrated".
- Problem: The authors' headline diagnosis, a level shift that overstates prevalence, is dropped.
- Suggested fix: "(slope 1.63, z = −5.3: probabilities too high overall, overstating prevalence by about 80%, and too close to the middle, rather than over-confident)".

### R2-fidB-16 [nit]
- Location: 04_evidence.tex:141 and 169
- Claim: The sufficiency question "works much better"; "separated complete from incomplete evidence with AUROC 0.95, against 0.85 …, and dropped from 0.83 to 0.10 when a deciding fact was deleted".
- Source says: arx01006 reports "+0.10 [0.09, 0.11]" on HotpotQA. The 0.83 → 0.10 drop is from a separate policy case.
- Problem: "Much better" overstates a single-study gain of 0.10 AUROC, and the sentence merges two experimental settings into one. See also R2-fidB-5 on the acceptance-filter caveat.
- Suggested fix: Answerbox: "works better (AUROC 0.95 vs 0.85 in one study)". Line 169: "…on HotpotQA, and in a policy case fell from 0.83 to 0.10 …".

### R2-fidB-17 [nit]
- Location: 04_evidence.tex:168
- Claim: "relabelling the option or moving it recovered almost nothing"
- Source says: arx39496 tested relabelling on the 100 arithmetic cases, but tested moving the option on "40 selected inventory failures" (5, 0, 2 and 0 recovered).
- Problem: The scope of the two tests differs slightly. The substance is accurate.
- Suggested fix: "…or moving it (on inventory cases) recovered almost nothing".

## Summary
Severity counts: 0 major, 10 minor, 7 nit (including the G4 source re-check, R2-fidB-13 to 17).
- All tallies quoted in the text match evidence_coding.csv.
- All Chinese and English concordance excerpts are verbatim at 5791ae3.
- Nearly all round-1 findings were fixed. fidB-29 (the "can" hedge) and the 0.1→0.2 corrections row of NEW-arx-25 were not, and the fidB-8 case-share error reappears in G5.
- Remaining issues:
  - one unsupported synthesis claim about G3 failures being shared;
  - an internal contradiction over whether failing to signal missing information is typed-specific;
  - tab:keyfindings codes and comparator cells that do not follow from the coding;
  - a harsher-than-text reading of §5.5's "hate attack" sentence, which is also missing from the concordance;
  - small concordance and legal-precision nits.
- The G4 per-number check is complete: every number matches its source, and the three minor and two nit issues are R2-fidB-13 to 17.
- The per-number checks for G5–G7, tab:keyfindings, tab:corrections3 and the cite-backed claims in §5–§7 are still pending from the parallel passes and are not reflected here.
