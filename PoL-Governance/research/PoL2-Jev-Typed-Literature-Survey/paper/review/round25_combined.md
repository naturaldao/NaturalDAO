# Round 25: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R24-1..R24-5; test of the lead author's reframed distinctiveness claim (02b "What the comparison implies") against every row of `tab:paradigms`; fresh whole-paper pass on §2.3, §7.1, §7.2, §8, abstract, §1, answer boxes, metadata and layout. Items resolved in REVIEW.md, AUDIT.md and rounds 12–24 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/*.tex (01, 05, 07, 08 at 22:56:19; 02b at 22:56:26); main.pdf and main.log 22:56:42 (94 pages, no `!` lines, no undefined references, 17 overfull boxes, all ≤ 5.98pt and none in 02b/07, as in round 24).
- arxiv-submission.zip 22:56:47, extracted to scratchpad/r25/zip: 01, 02b, 05, 07, 08 contain the round-24 fixes.
- arxiv_metadata.txt 22:56:47: abstract 1,916 ≤ 1,920, identical to 00_abstract.tex; "94 pages, 7 figures" agrees with the PDF.
- `python scripts/rate_certainty.py --check`: CHECK PASSED (now 0 moderate, 11 low, 4 very low; contested 2, 5, 11, 14).
- PDF pp. 7–10 via pdftotext -layout (§2.2 end, tab:paradigms, (i)–(v)).
- PoL2: scratchpad/pol/en_7.md (Preface, Art. 1–11), en_5.md (§5.4.1).
- CAC, 生成式人工智能服务管理暂行办法, https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm, fetched 2026-10-08 (Art. 4, 9, 10, 14, 15, 17).
- OpenAI Model Spec 2026-08-18 (as verified in round 24 and in AUDIT R24-5).

## Task 1: re-check of round 24

| Item | Status | Evidence |
|---|---|---|
| R24-1 Art. 11 scope | FIXED | 02b l.108 "CC0 and kept in a versioned repository whose commits can be cited … its welfare protocol (Chapter~7) also has its own amendment procedure, which archives every amended version (\art{11}(5))"; l.110 "propose amendments to the welfare protocol"; row (f) "changed by commit; for the welfare protocol (Chapter~7), amendments pass …"; §2.2 summary (PDF p. 7) "amendments to the protocol … (Art. 11)"; 05 l.41 (b) "(and, by the corresponding change to \clause{5.4.1}, blocking a person's speech)". Matches en_7 "Article 11 [Protocol Amendment]" |
| R24-2 §7.2 overreach | FIXED | 07 l.115 "needs an answer to G1--G5 and, where it automates oversight, to the escalation question of G6 …; G7 and the rest of G6 arise only where a proposal also gives disputes to AI or scores people", consistent with 02b l.123 |
| R24-3 anomaly detection | FIXED | 01 l.36, 07 l.86 (with \cref{tab:verdict}), 08 l.6 qualify "on text (not on numeric or structured … signals …)", matching tab:verdict row 4. Residual wording difference: R25-2 (nit) |
| R24-4 superlative | PARTLY | "most specification-like" removed everywhere (grep: no occurrence in sections/ or metadata). The replacement "only paradigm compared whose single public, versioned text joins an intercept, its construct and institutional duties over the resulting decisions" is not true as stated of row (a) (CAC Measures) and overstates the join inside \pol{}: R25-1 |
| R24-5 Model Spec | FIXED | 02b l.68 "behaviour can be changed without retraining only within the spec's chain of command (the vendor through system messages, developers and users by instruction within the defaults the spec lets them override), while a change of the norms trained into the model requires retraining under vendor control"; matches the Model Spec levels of authority and "We are training our models to align to the principles in the Model Spec" |

## Task 2: does any comparator satisfy the reframed claim?

Claim (02b l.120–121): \pol{} is "the only paradigm compared whose single public, versioned text joins an inference-time intercept (\clause{5.4.1}), the construct it applies (\clause{1.5}, \clause{4.3.2}) and institutional duties over the resulting decisions … (\art{5}(5), \art{9}(2)--(3))".

| Comparator | Intercept | Construct | Duties over resulting decisions | Verdict |
|---|---|---|---|---|
| EU AI Act (a) | none prescribed (Art. 12 logging, 14 oversight, 50 marking are not an intercept) | risk tiers, not a content construct | yes (Art. 11–14, 86) | does not satisfy |
| CAC Interim Measures (a) | Art. 14(1) 提供者发现违法内容的，应当及时采取停止生成、停止传输、消除等处置措施 (a duty to stop generation and transmission, i.e. to intercept outputs, stated as an outcome) | Art. 4(1) enumerated prohibited content (煽动颠覆国家政权 … 宣扬民族仇恨、民族歧视，暴力、淫秽色情，以及虚假有害信息), Art. 4(2) discrimination | Art. 14(2) warnings, function limits, suspension or termination of users, 保存有关记录, report to authorities; Art. 15 complaint and reporting mechanism, 公布处理流程和反馈时限 … 反馈处理结果; Art. 17 assessment and filing | **satisfies all three elements in one public, citable instrument**, except that its intercept is an outcome duty rather than a named component (see R25-1) |
| DSA (b) | none: notice-and-action (Art. 16) and automated means (Art. 15(1)(e), 17(3)(c)) govern moderation of hosted content, not an inference-time intercept on model I/O | illegal content (Art. 3(h)) or T&C | yes (Art. 17, 20, 24(5)) | fails only on "inference-time"; holds |
| Santa Clara (b) | automated detection conditioned, not prescribed | — | notice, appeal, numbers | does not satisfy |
| Model Spec / constitutions (c) | none (training-time) | yes | none stated | does not satisfy |
| Guardrails (d) | yes, as code | yes | none (row (d) "no duty to give reasons or to keep records") | does not satisfy (stated in l.121) |
| DAO / polycentric (e) | none | — | ledger, votes | does not satisfy |

Within \pol{} itself, the join is looser than the sentence implies: the Chapter 7 duties (Art. 4, 5(5), 9(2)–(3)) attach to NaturalDAO's welfare decisions and "all NaturalDAO technologies" (en_7 Art. 4(1)), whereas \clause{5.4.1} speaks of "the safety valve of the large model" and nowhere assigns it to NaturalDAO; row (f) and (i) themselves say that for the valve "thresholds and appeal [are] unspecified" and "who operates it or how a blocked person appeals" is not said. Since R24-1, Chapter 7 is also a separately amended protocol. So the duties are not, in the text, "over the resulting decisions" of the intercept; in the CAC Measures the record, report and complaint duties do attach to the actions taken on the content and users the intercept duty concerns.

## Task 3: fresh pass

**Balance of §2.3.** Every distinguishing property (i)–(v) carries a cost; the EU conflict is stated in (v); positionality is in §1 Scope and §2.2 l.6. The remaining tilt is the asymmetry in how outcome-level duties are credited: \pol{}'s \clause{5.4.1} is coded "Yes, as a duty" although (i) concedes the text "does not say how the valve is built", while CAC Art. 14 is coded "None prescribed" and described as "an outcome, not a mechanism" (l.66), and row (a) omits the CAC record-keeping (Art. 14(2)) and complaint (Art. 15) duties that answer the "Human role"/"Transparency" columns. Together with the claim of l.120 this is R25-1.

**Verdict traceability (§7.1, §8, tab:verdict ↔ tab:keyfindings).** Certainties in "The verdict" and tab:verdict match tab:keyfindings and the script (thresholds low^c, steering low, option names low, "I don't know" low, peer errors low, ranking low, calibration low, agreement gating very low, comparator low^j, culture very low); contested count four in §7.2 and §8 matches the script (2, 5, 11, 14). NS/DC/NT used as defined. No new break.

**Consistency chain.** Abstract ↔ §1 l.32–37 ↔ §7.1 ↔ §8 ↔ metadata agree on detector/judge verdict, per-person quantification basis, row-8 aggregate measurement, extrapolation, certainty, update and comparator caveat. §7.2 l.115 now matches §2.3 l.123 on G1–G5/G6/G7. One wording difference on anomaly detection (R25-2). The §7.2 sentence that the Chinese duty "needs an answer to G1--G5 … which its own text does not yet give" is partly answered for G5 by Art. 14(2) records (folded into R25-1's fix).

**Layout.** pp. 7–10: §2.2 and "What the alternatives specify" on p. 7; tab:paradigms pp. 8–9 with repeated header; (iii) breaks across pp. 9–10 in running text. 17 overfull boxes, unchanged and accepted.

## Findings

**R25-1 [major] The reframed distinctiveness claim is also substantially true of the CAC Interim Measures, and overstates the join inside \pol{}.**
- **Location:** 02b_pol2.tex l.120–122 ("the only paradigm compared whose single public, versioned text joins an inference-time intercept …, the construct it applies … and institutional duties over the resulting decisions"; "This conjunction is why …"); l.66 ("which states an outcome, not a mechanism"); tab:paradigms row (a) "Human role" and "Transparency" cells; secondarily 07_discussion.tex l.115.
- **Source:** CAC Measures (cac.gov.cn, fetched 2026-10-08): Art. 14(1) 停止生成、停止传输、消除; Art. 4(1)–(2) enumerated prohibited content and discrimination; Art. 14(2) 警示、限制功能、暂停或者终止 … 保存有关记录，并向有关主管部门报告; Art. 15 投诉、举报机制 … 公布处理流程和反馈时限 … 反馈处理结果. en_7 Art. 4(1) "all NaturalDAO technologies", Art. 9(3) "all data and logs of the welfare system"; en_5 §5.4.1 safety valve "of the large model"; 02b row (f) "thresholds and appeal unspecified", (i) "who operates it or how a blocked person appeals".
- **Problem:** One public, versioned instrument in the comparison joins a duty to stop generating and transmitting content (an inference-time intercept stated as an outcome), the construct it applies, and record, report and complaint duties over the resulting actions on content and users. The only difference left is that \pol{} names an intercept component that screens every input and output, while the CAC states an outcome on discovery, and \pol{}'s own intercept is equally unspecified as a mechanism (cost (i)). Conversely, \pol{}'s decision duties are Chapter 7 duties over NaturalDAO's welfare decisions, not over the valve's blocks, for which the text states no reasons, record or appeal. With the author a \pol{} contributor, an "only" claim that a comparator meets, coded with an asymmetry in the comparator's disfavour, is the kind of tilt an arXiv cs.CY referee would cite.
- **Fix:** Replace l.120–121 with a claim that is true and states the difference: "\pol{} is the only text compared that names an intercept component screening every input and output of a model (\clause{5.4.1}) and the three-valued construct it applies (\clause{1.5}, \clause{4.3.2}); the Chinese Interim Measures come closest, joining a duty to stop generating and transmitting unlawful content once found (Art.~14) with an enumerated content construct (Art.~4) and record, report and complaint duties over the resulting actions (Art.~14, 15), but name no screening component; guardrails (d) specify the component and taxonomy more precisely, as code, but state no duties. \pol{}'s own decision duties (\art{5}(5), \art{9}(2)--(3)) attach to NaturalDAO's welfare decisions (Chapter~7); for the valve's blocks the text states no reasons, record or appeal (i)." Adjust l.122 "This conjunction" accordingly (e.g. "This specificity at the intercept is why …"). In row (a), add to "Human role" or "Transparency": "CN: records of measures against users kept and reported (Art.~14); complaint procedure with published time limits and feedback of results (Art.~15)". Either change l.66 "states an outcome, not a mechanism" to "states an outcome on discovery, not a screening component" or code \pol{}'s cell symmetrically. In 07 l.115, "which its own text does not yet give" → "which its own text gives only in part (the Chinese Measures require records of measures taken, Art.~14)".

**R25-2 [nit] Anomaly-detection qualifier differs between §1 and §7.1/§8.**
- **Location:** 01 l.36 "anomaly detection on text (not on numeric or structured signals)"; 07 l.86 and 08 l.6 "… signals without a trained model"; tab:verdict row 4 "NS on numeric or structured signals without a trained model".
- **Fix:** add "without a trained model" in 01 l.36.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 1 | R25-1 |
| Minor | 0 | |
| Nit | 1 new, plus 5 carried | R25-2; R17-2, R17-3, R21-1, R21-2, R21-3 |

R24-1, R24-2, R24-3, R24-5: FIXED. R24-4: PARTLY (superlative removed; its replacement raises R25-1).

New major or minor problems remain: yes
