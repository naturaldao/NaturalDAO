# Round 24: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R23-1..R23-6, then a fresh whole-paper pass with attention to §2.3 `sec:paradigms` / `tab:paradigms`, §7.1 `sec:verdict` / `tab:verdict`, §7.2, §8, abstract, §1 thesis, answer boxes and metadata. Items resolved in REVIEW.md, AUDIT.md and rounds 12–23 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/*.tex (01, 07, 08 at 22:46; 02b at 22:48:15); main.pdf and main.log 22:48:30 (94 pages, no `!` lines, 17 overfull boxes, none in 02b_pol2.tex or 07_discussion.tex; largest 5.98pt in an appendix alignment).
- arxiv-submission.zip 22:48:31, extracted to scratchpad/r24/zip: 00_abstract, 01, 02b_pol2, 07, 08 identical to the comment-stripped source.
- arxiv_metadata.txt: abstract 1,916 ≤ 1,920, identical to 00_abstract.tex; "94 pages, 7 figures" agrees with the PDF (7 `figure` environments).
- `python scripts/rate_certainty.py --check`: CHECK PASSED (0 moderate, 11 low, 4 very low; contested 2, 5, 11, 14).
- PDF pp. 7–9 (tab:paradigms) and 40–42 (tab:verdict, "The verdict") rendered at 60 dpi.
- PoL2: scratchpad/pol/en_7.md and zh_7.md (Preface, Art. 2–11, Conclusion).
- OpenAI Model Spec, https://model-spec.openai.com/ (redirects to 2026-08-18.html), downloaded 2026-10-08.

## Task 1: re-check of round 23

| Item | Status | Evidence |
|---|---|---|
| R23-1 generative evaluators in the "decides" verdict | FIXED | 07 l.84 "no low-cost generative evaluator tested beside one has been shown to [escape] … applies to automated judges of this cost tier as a precaution"; 08 l.5 "on precaution the low-cost generative evaluators … (not shown to escape these failures, most of which were never compared)"; consistent with §7.2 "What would change the conclusion", last sentence, and with abstract/§1 ("most failures lack a comparison") |
| R23-2 "inherits the same requirements" | FIXED in §2.3 | 02b l.121 "inherits G1--G5 … and, where it automates oversight, the escalation question of G6; the non-intervention … and the per-person and public assessment of G7 … follow from \pol{}'s own institutional choices (v)"; G1–G5 names match tab:clauses (03 l.26–30). The same overreach survives in §7.2 (R24-2) |
| R23-3 "the record" scoped to NaturalDAO | FIXED | 02b l.120 "for NaturalDAO's decisions (Chapter~7), the record and the decision-maker"; row (f) last cell "For NaturalDAO (Chapter~7):"; en_7 Art. 4(1) "all NaturalDAO technologies", Art. 5(5) "NaturalDAO must provide a verifiable decision chain", Art. 9(3) "data and logs of the welfare system" |
| R23-4 Model Spec customisation | FIXED | 02b l.68. Verified on model-spec.openai.com (2026-08-18): "user- and guideline-level defaults, where the latter can be overridden by users or developers"; chain of command "enabling them to adjust the model's behavior to their needs while staying within clear boundaries"; root rules "cannot be overridden by system messages, developers or users"; "We are training our models to align to the principles in the Model Spec"; "dedicated to the public domain and marked with the Creative Commons CC0 1.0 deed"; "See all versions" links CHANGELOG.md. Licence and changelog claims of row (c) and (iii) correct. Residual nit on the system level: R24-5 |
| R23-5 tab:paradigms layout | FIXED | p. 7 full text ending with "What the alternatives specify"; table on p. 8 (caption, rows (a)–(d)) and p. 9 (rows (e)–(f), repeated header), then (i)–(v) on p. 9; no overfull in 02b; "Institu-tional" hyphenates; "(Art. 11(2) and (5))" stays inside its column |
| R23-6 row-8 verdict in §1 and §7.1 | FIXED | 01 l.36 and 07 l.86 "the public-decision assessment of \clause{5.6} … only as an audited aggregate measurement with its measured error carried into every conclusion"; matches tab:verdict row 8, §8 l.6 and the G7 box |

## Task 2: fresh pass

**Balance and positionality of §2.3.** The section still reads as comparative analysis: each of (i)–(v) carries a cost, the conflict with EU law is stated in (v), and positionality is declared in §2.2 l.6 and §1 Scope. Descriptions of the other paradigms are accurate (risk-based regulation, DSA articles, Santa Clara, Model Spec, guardrails, DAO/polycentric rows checked in round 22; Model Spec re-checked above). Two residual tilts in PoL2's favour remain. (1) After the R23-3 scoping, the superlative of l.120 rests for the inference-time safeguard only on naming "the intercept and the construct", which paradigm (d) names more precisely (R24-4). (2) Property (iii) and row (f) credit the whole PoL2 text with an amendment and archiving procedure that Chapter 7 states only for the welfare protocol (R24-1).

**Fidelity of PoL2 Chapter 7 claims.** Checked against en_7/zh_7: Art. 2(1) (no human voting), 4(1)–(3), 5(4)–(5), 6(3), 7(1)–(3), 8(2), 9(2), 9(3), 9(7), 10, 11(1)–(5) are quoted and cited correctly in §2.2, row (f) and (i)–(v), with one scope error: Art. 11 is headed 【协议修订】 "Protocol Amendment" and amends "the Protocol", i.e. the Governance Protocol for Human Public Welfare, which the Chapter 7 conclusion calls "an open protocol developed and managed by the autonomous NaturalDAO" (zh l.100 由自治的NaturalDAO开发与管理的开放协议). It is not an amendment procedure for the PoL2 text, which is versioned by its originator on GitHub; §2.2 l.11 itself reports a renumbering of three chapters by the originator with no questioning period (R24-1).

**Verdict traceability (§7.1, §8, tab:verdict ↔ tab:keyfindings).** Every certainty in "The verdict" and in tab:verdict matches tab:keyfindings and the script: thresholds low^c (rows 2, 14), steering low (row 4), option names low (row 6), "I don't know" low (row 9), peer errors low (row 13), ranking low (row 1), calibration low (row 8), agreement gating very low (row 12), comparator statement low^j (row 15), culture very low (row 7). NS/DC/NT are used as defined in l.9 and the caption; "precautionary" appears only in row 7 and, for generative evaluators, in l.84 and §8 l.5, each with the absence-of-measurement basis stated. One function's verdict is reported more favourably in the prose than in the table: anomaly detection (R24-3).

**Consistency chain.** Abstract ↔ §1 l.32–37 ↔ answer boxes ↔ §7.1 ↔ §8 ↔ metadata agree on: detector under added conditions; not a judge; not suitable for any function that decides; per-person quantification on steering plus precaution; §5.6 public-decision assessment as audited aggregate measurement; extrapolation from English benchmarks; low/very low, four contested, none moderate; update reversed nothing; comparator caveat. Two breaks: §7.2 "Beyond one specification" restates the pre-R23-2 claim that every interception layer needs an answer to all of G1–G7 (R24-2); anomaly detection (R24-3).

**Layout.** 17 overfull boxes, all ≤ 6pt and outside 02b/07 (as accepted in earlier rounds). tab:paradigms (pp. 8–9) and tab:verdict (pp. 40–41) break cleanly with repeated headers; no cell collisions visible at 60 dpi.

## Findings

**R24-1 [minor] Art. 11 is the welfare protocol's amendment procedure, not the PoL2 text's.**
- **Location:** 02b_pol2.tex l.108 "(iii) The text is versioned and citable: it is CC0, pinned to a commit, and its own amendment procedure archives every version (\art{11}(5)), which is what makes \cref{tab:concordance} and the requirements of \cref{tab:clauses} possible"; l.110 cost "… and lets NaturalDAO propose amendments and verify them itself (\art{11}(1),~(3), with \art{6}(3))"; tab:paradigms row (f), column "Who sets the norms", "amendments pass a universal questioning period and all versions are archived (\art{11}(2) and~(5))". Secondary: 05_synthesis.tex l.41 option (b) uses "the amendment procedure of \art{11}" to define decisions including "blocking a person's speech", which is a §5.4.1 safety-valve function outside Chapter 7.
- **Source:** en_7 Art. 11 "[Protocol Amendment]" (zh 第十一条【协议修订】); Conclusion: the protocol is "developed and managed by the autonomous NaturalDAO". The PoL2 text as a whole is changed by its originator by commit (§2.2 l.11: three chapters renumbered between 27 and 30 September with no questioning period).
- **Problem:** (iii) credits the PoL2 text with a self-imposed archiving duty it does not have and attributes the concordance to it (what makes tab:concordance possible is commit pinning on GitHub); the cost sentence then sets "controlled by its originator" beside "lets NaturalDAO propose amendments", which reads as contradictory unless the reader knows Art. 11 governs only Chapter 7. With the author a PoL2 contributor, a favourable mis-scoping in the distinguishing-properties list is a balance issue.
- **Fix:** l.108 "it is CC0 and pinned to a commit, which is what makes … possible; its welfare protocol (Chapter~7) also archives every amended version (\art{11}(5))"; l.110 "… has not been peer reviewed, and lets NaturalDAO propose amendments to the welfare protocol and verify them itself (…)"; row (f) "Originator and listed contributors; open CC0 text pinned to a commit, changed by commit; for the welfare protocol, amendments pass … (\art{11}(2) and~(5)); not peer reviewed". In 05 l.41 (b), drop "blocking a person's speech or" or say "and, by the corresponding change to \clause{5.4.1}, blocking a person's speech".

**R24-2 [minor] §7.2 restates the overreach that R23-2 removed from §2.3.**
- **Location:** 07_discussion.tex l.115: "constitutional classifiers, the Chinese duty to stop unlawful generation and the DSA's provisions on automated means each move toward an inference-time interception layer, and each then needs an answer to G1--G7 that its own text does not yet give."
- **Conflict:** 02b l.121 (post-R23-2): such a layer "inherits G1--G5 … and, where it automates oversight, the escalation question of G6; the non-intervention (\art{9}(7)) and AI-only adjudication (\art{10}) in G6 and the per-person and public assessment of G7 … follow from \pol{}'s own institutional choices (v)". l.114 is correctly conditional ("gives disputes to AI, or scores people's behaviour"), l.115 is not.
- **Fix:** "… and each then needs an answer to G1--G5 and, where it automates oversight, to the escalation question of G6, which its own text does not yet give; G7 and the rest of G6 arise only where a proposal also gives disputes to AI or scores people."

**R24-3 [minor] The anomaly-detection verdict in §1, §7.1 and §8 omits the table's NS for non-text signals.**
- **Location:** 01 l.36 "for the functions that detect, the safety valve, output truncation and anomaly detection, it is usable only as a recorded detector"; 07 l.86 "the anomaly detection of \art{7}, hosted \jev{} is usable, but only inside the design"; 08 l.6 same list.
- **Conflict:** tab:verdict row 4 (07 l.49): "DC on text; NS on numeric or structured signals without a trained model", on arx00376 (9.8% vs 22.8% majority class) and arx09937 (57–94% false flags; no better than flagging every window under shift). Art. 7(1)–(2) asks NaturalDAO to monitor "all welfare operations in real time" and identify "anomalous patterns", which are largely operational, non-text signals; a reader of §1, §7.1 or §8 alone takes the function as supported.
- **Fix:** 01 l.36 and 08 l.6 "… and anomaly detection on text (not on numeric or structured operational signals without a trained model)"; 07 l.86 "the anomaly detection of \art{7} on text signals".

**R24-4 [minor] After R23-3, the basis of "most specification-like … for an inference-time safeguard" is matched by paradigm (d).**
- **Location:** 02b l.120 "\pol{} is the most specification-like of these paradigms for an inference-time safeguard, in the limited sense that it names the intercept and the construct and, for NaturalDAO's decisions (Chapter~7), the record and the decision-maker".
- **Problem:** for the inference-time safeguard the remaining basis is "names the intercept and the construct"; l.69 and row (d) say guardrails "specify the intercept precisely, as code with a harm taxonomy and a threshold", while (i) and row (f) say PoL2 leaves thresholds, "where necessary", the operator and appeal unspecified. The record and decision-maker are now scoped to NaturalDAO, not to the safeguard. What actually distinguishes PoL2 is that it states the intercept and construct as governance duties in citable clauses rather than as discretionary vendor or deployer code. Given the author's positionality, the superlative should rest on that.
- **Fix:** "\pol{} is the only text in this comparison that states an inference-time intercept and its construct as governance duties in clauses that can be cited (guardrails (d) specify both more precisely, but as vendor or deployer code with no duty), and that names, for NaturalDAO's decisions (Chapter~7), the record and the decision-maker; this is why …".

**R24-5 [nit] Model Spec: not every change of the vendor's norms requires retraining.**
- **Location:** 02b l.68 "so a change of the vendor's norms requires retraining under vendor control".
- **Source:** model-spec.openai.com (2026-08-18), levels of authority: "System: Rules set by OpenAI that can be transmitted or overridden through system messages"; implementation: "We are training our models to align to the principles in the Model Spec".
- **Fix:** "so a change of the vendor's norms is implemented mainly by retraining under vendor control (the vendor can also adjust system-level rules through system messages; developers and users …)".

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 4 | R24-1, R24-2, R24-3, R24-4 |
| Nit | 1 new, plus 5 carried | R24-5; R17-2, R17-3, R21-1, R21-2, R21-3 |

R23-1..R23-6: all FIXED (R23-2's overreach survives in §7.2, raised as R24-2).

New major or minor problems remain: yes
