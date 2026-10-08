# Round 34: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R33-1 against arx04985 (§III-A3 Table I, Takeaway 4, §VI-A, §VI-B, App. C1–C2); fresh whole-paper pass with emphasis on parts not read closely in rounds 22–33: §3 method text and its counts, §4.1–4.7 answer boxes against §7.1 and tab:verdict, the §5 regulatory paragraph (and its echo in §2), figure captions against figure text, appendix captions and the PRISMA figure. Items resolved in REVIEW.md, AUDIT.md and rounds 12–33 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/06_design.tex, 07_discussion.tex, main.pdf, main.log, arxiv-submission.zip, arxiv_metadata.txt (all 23:36). main.log: "Output written on main.pdf (96 pages, 2038707 bytes).", no `!` lines, no undefined or multiply defined references, 17 overfull boxes (unchanged).
- `python scripts/rate_certainty.py --check` (repository root): CHECK PASSED ("tab:keyfindings and tab:certchanges agree with the computed ratings").
- arxiv-submission.zip extracted to scratchpad: 05, 07 identical to sections/; 03 and 06 differ only by figure paths. main.pdf contains the new §7.1 wording ("surrogate extraction through the authorised task").
- Figure text extracted with PyMuPDF from fig_corpus, fig_fragility, fig_honesty, fig_escalation, fig_framework, fig_prisma.

## Task 1: re-check of round 33

| Item | Status | Evidence |
|---|---|---|
| R33-1 §7.1 "bounds" overstatements | FIXED | 07 l.93 now: minimisation "for hosted \jev{} is the only one of these measures that would remove the signal, since the attack worked for a user authorised for the task and needed labels alone" (matches Takeaway 4: official Jev 100% coverage and accepted accuracy for all four attributes "under both label and probability access"; NanoJev abstains under label access, consistent with "an open model's labels revealed none"); task restriction "keeps the valve from serving as a general oracle for questions such as the feasibility of harmful plans" (App. C1: attacker asks "whether the proposed action is likely to be effective"); logging "makes surrogate extraction through the authorised task visible, though neither prevents it" (App. C2: fixed question, four answers, 49% → 92% after 200 labels); "None of these measures has been tested" (§VI-A). 06 element 4 now splits the justification: restriction "since labels refined harmful plans", logging "since labels also trained a surrogate"; it no longer claims either bounds extraction. Lesson 7 (l.105), open problem (l.153), §8 l.11 and checklist item 7 are consistent with it. The 97–100% figure of tab:verdict and §7.1 matches Table I (Jev-specific injection 100/100/97.2, universal suffix 100/100/97.0 on hosted Jev). |

## Task 2: fresh pass

**§3 method, arithmetic.** counts.tex / counts_update.tex reproduce every derived number: 79 + 27 + 1 = 107 studies; 85 coded + 7 non-empirical + 22 background = 114 = 107 + 7 grey; 92 appraised = 85 + 7 = 37 + 17 + 38; update 62 read − 5 excluded = 57 = 31 + 26 = 48 coded + 6 context + 2 non-empirical + 1 excluded; 48 = 30 + 5 + 13; 18 / (85 + 18) = 17.5% ("17%"); 118 − 97 = 21 disagreements = 11 + 10; 10/118 = 8.5% ("8%"); κ intervals 0.42–0.94 and 0.36–0.70 overlap as stated. The deviations (late re-screening, ratings unfrozen, rule (iv) gap, no human dual screening) are disclosed.

**§4 answer boxes vs tallies and §7.1.** Box codes sum to S 16, Q 97, N 48 = 161 pairs (= \nRows, = fig_framework and fig_corpus (b) per-requirement n). G1 comparator 6 + 10 + 5 = 21. The verdict's decisive findings (thresholds low contested; steering low; option names low; "I don't know" low; peer errors low, upper bound) and the detector positives (ranking low; agreement gating very low, preregistered, disguised attacks passed) match the G1, G2, G3, G4, G6 boxes and tab:keyfindings; G6 box "in several, including a preregistered one, \jev{}'s threshold met its target" matches tab:verdict's "a finding one preregistered study contests~\cite{arx33689}" (quality_appraisal.csv: arx33689 preregistered, stronger).

**Figures vs captions.** fig_corpus (b): Zenodo/alphaXiv column 8 + 2 + 8 + 13 + 2 + 9 + 4 = 46 = "44 Zenodo and 2 alphaXiv"; (a) arXiv 30 + 24 + 25 = 79, Zenodo/alphaXiv 28. fig_fragility (b): 312/508, 238/328, 240/328, 185/285 match "61.4%" and "64.9–73.2%"; (c)–(d) AUROC 0.938→0.232, 0.815→0.581 match §4.3. fig_escalation (b) 242/252, 96.0% vs 50.3%; (c) nine panels. fig_prisma: 63 + 1 + 15 = 79; 25 − 9 − 1 = 15; ~330 − ~268 = 62 = 61 + 1; 62 − 21 − 13 − 1 = 27; grey 9 − 2 = 7. Appendix table captions accurate.

**§5 regulatory paragraph.** AI Act Art. 5(1)(c), Art. 14, Art. 86, GDPR Art. 22(1),(3), DSA Arts. 17 and 20 and the Santa Clara Principles are paraphrased accurately (as in round 21). The Art. 5(1)(f) sentence is accurate as to workplace/education and the medical/safety exception, but not as to what the prohibition covers (R34-1); this point was not raised in round 1 or round 21.

## Findings

**R34-1 [minor] The paper applies the AI Act's emotion-recognition prohibition to T1 without saying that it covers only inference from biometric data, so it does not reach a typed model that infers emotion from text.**
- **Location:** 05_synthesis.tex l.55 ("The EU AI Act~\cite{euaiact2024} prohibits emotion recognition in workplaces and educational institutions except for medical or safety reasons (Art.~5(1)(f)), bearing on T1"); 02_background.tex l.57 ("the EU AI Act prohibits it in workplaces and education"); by extension l.59 of 05, which lists "no emotional-state inference about persons" among options that "would bring an implementation closer to these norms".
- **Evidence:** AI Act Art. 3(39) defines an "emotion recognition system" as one "for the purpose of identifying or inferring emotions or intentions of natural persons on the basis of their biometric data", and Recitals 18 and 44 frame the Art. 5(1)(f) prohibition in those terms; the Commission's guidelines on prohibited practices (Feb. 2025) read Art. 5(1)(f) as limited to such systems, so inferring emotion from written text alone falls outside it. T1 concerns exactly a typed model attaching emotion scores to messages (05 l.11), and the §8 / abstract list "emotion recognition" as a tension "with EU AI … law". A cs.CY or legal referee would flag the parallel as overstated; the paper's own principle is to weaken a sentence the source does not support.
- **Fix:** e.g. 05 l.55: "… prohibits AI systems that infer emotions from biometric data in workplaces and educational institutions, except for medical or safety reasons (Art.~5(1)(f), with the definition of Art.~3(39)); text-only inference by a typed model falls outside the prohibition, so it bears on T1 only by analogy, as a statement of the same concern about inferring persons' emotional states, …"; 02 l.57: "the EU AI Act prohibits emotion recognition from biometric data in workplaces and education". The abstract's "tensions with EU AI, data and platform law" can stand, since T1 is still compared with the Act.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 1 | R34-1 |
| Nit | 0 new, plus 5 carried | R17-2, R17-3, R21-1, R21-2, R21-3 |

R33-1: FIXED.

New major or minor problems remain: yes
