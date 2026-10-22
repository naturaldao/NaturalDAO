# Round 26: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R25-1 and R25-2; source check of every CAC and \pol{} claim in the rewritten 02b "What the comparison implies", l.66 and tab:paradigms rows (a) and (f); coding check of the other rows against (a) and (f); fresh whole-paper pass (balance of §2.3, verdict traceability §7.1/§8, consistency abstract ↔ §1 ↔ §2.3 ↔ boxes ↔ §7 ↔ §8 ↔ metadata, layout). Items resolved in REVIEW.md, AUDIT.md and rounds 12–25 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/*.tex (01, 07 at 23:03:23; 02b at 23:05:04; A_concordance touched 23:24:22, content identical to the zip copy apart from line endings); main.pdf, main.log, arxiv_metadata.txt, arxiv-submission.zip at 23:05:14.
- main.log: "Output written on main.pdf (94 pages)", no `!` lines, no undefined references, 17 overfull boxes (all ≤ 5.98pt, none in 02b), as in round 25.
- arxiv-submission.zip extracted to scratchpad/r26/zip: every section equals sections/*.tex up to CRLF and the flattened `\input`/figure paths.
- arxiv_metadata.txt: abstract 1,916 ≤ 1,920; "94 pages, 7 figures" agrees with the log.
- `python scripts/rate_certainty.py --check`: CHECK PASSED.
- PDF pp. 8–11 via pdftotext -layout.
- CAC 生成式人工智能服务管理暂行办法, https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm, fetched 2026-10-08: Art. 2, 4, 14, 15, 17 read verbatim.
- \pol{}: scratchpad/pol/zh_5.md (§5.4 "我们将该工程称之为 NaturalDAO（自然道）", §5.4.1, §5.5, §5.6), zh_7.md (Preface, Art. 1–11, Conclusion), zh_4.md (§4.3.2 不在场的"非爱非恨"状态), zh_1.md (§1.5 "服务于结构性分析而非道德标签"); en_5.md, en_7.md for the official translation.

## Task 1: re-check of round 25

| Item | Status | Evidence |
|---|---|---|
| R25-1 "only paradigm" claim | FIXED (one new asymmetry in the gap sentence: R26-1) | 02b l.120 "\pol{} and China's 2023 Interim Measures … are the two texts compared that join …"; "This conjunction" and the "only" claim are gone (grep: no "the only paradigm", no "uniq" claim in sections/ or metadata other than "not uniqueness" in 02b l.129 and 01 l.14); l.66 now "a duty stated without a mechanism, as \pol{}'s safety valve is (row (f))"; row (a) carries CN Art. 14(1), 14(2), 15, 17; row (f) "mechanism, thresholds and appeal unspecified"; 07 l.115 "gives at most in part (… Art. 14(2) and 15)"; §1 l.14 names the CAC Measures and says the case is "chosen not for uniqueness" |
| R25-2 anomaly-detection qualifier | FIXED | 01 l.36 "anomaly detection on text (not on numeric or structured signals without a trained model)" = 07 l.86, 08 l.6, tab:verdict row 4 |

**CAC claims (official text).**

| Paper claim | Source | Verdict |
|---|---|---|
| duty to stop generating or transmitting unlawful content once found (Art. 14(1)) | 第十四条第一款 提供者发现违法内容的，应当及时采取停止生成、停止传输、消除等处置措施 … 并向有关主管部门报告 | accurate |
| warnings, restriction or suspension of users with records kept and reported (Art. 14(2)) | 第十四条第二款 … 警示、限制功能、暂停或者终止 … 保存有关记录，并向有关主管部门报告 | accurate; note these records concern measures against users engaged in unlawful activity, not the content stops of 14(1) (the paper's row (a) wording "measures against users … recorded" is exact; 02b l.121 "over the measures taken" is acceptable) |
| complaint channel that publishes its procedure and time limits and feeds back results (Art. 15) | 第十五条 建立健全投诉、举报机制 … 公布处理流程和反馈时限 … 反馈处理结果 | accurate |
| legality- and content-based standard (Art. 4); "binary, lawful or unlawful, and set by the state" | 第四条 chapeau 遵守法律、行政法规，尊重社会公德和伦理道德; (一) 坚持社会主义核心价值观，不得生成 … 法律、行政法规禁止的内容; (二) non-discrimination | trigger of the intercept (违法内容) is binary and state-set: accurate; Art. 4 itself also invokes social morality, ethics and core socialist values: R26-3 (nit) |
| filing and security assessment (Art. 17) in row (a) | 第十七条 applies only to services 具有舆论属性或者社会动员能力 | scope qualifier missing: R26-3 (nit) |
| providers of generative services to the public (Art. 2) | 第二条 向中华人民共和国境内公众提供 … | accurate |

**\pol{} claims.**

| Paper claim | Source | Verdict |
|---|---|---|
| §5.4 names the whole engineering project, governance layer included, NaturalDAO | zh_5 l.127 我们将该工程称之为 NaturalDAO（自然道）(after the Layer-1/Layer-2 diagram), l.138 | accurate; but this passage is not in tab:concordance (R26-4) |
| safety valve audits and intercepts input and output, "where necessary" (5.4.1) | zh_5 l.134 | accurate |
| any LLM "may accept" (5.5) | zh_5 任何大语言模型都可以纳入 / en "may accept" | accurate (official translation) |
| three-valued, not moral labels (1.5, 4.3.2) | zh_1 §1.5 服务于结构性分析而非道德标签; zh_4 §4.3.2 不在场的"非爱非恨"状态 | accurate |
| Art. 4(1) "all NaturalDAO technologies" fully open | zh_7 第四条(1) 所有NaturalDAO技术的运行逻辑、决策过程和输出结果必须完全公开透明 | accurate |
| duties to explain, keep a decision chain and adjudicate disputes (5(5), 9(2), 10) "framed within the welfare protocol"; "no clause states reasons, a record or an appeal for an individual block" | zh_7 第四条(3) 人类可随时 … 质询任何决策，NaturalDAO对质询必须提供可理解的解释 (same article as 4(1)); 第五条(4)–(5) 所有NaturalDAO的运行逻辑 … / NaturalDAO必须提供可验证的决策链路; 第十条 所有争议由NaturalDAO自主裁决; 第九条(6) 问题报告 | partly inaccurate as reasoned: R26-1 |
| population-level aims (5.6, Ch. 7) the Measures lack | zh_5 §5.6 量化每个人的爱语与恨语特征 … 公共决策中提供"爱2证明"的评估维度 | accurate; the Measures contain no per-person quantification |

**Are the four differences accurate and fair?** (1) Multi-valued, non-moral construct vs binary state-set standard: accurate for the intercept trigger; incomplete for Art. 4 (R26-3, nit). (2) Model-agnostic layer inside LLMs vs provider duty without mechanism: accurate, and symmetric with l.66 and row (f) ("mechanism … unspecified"). It omits the one intercept difference that is textual and testable: the valve screens every input and output (输入输出 … 审计与拦截), whereas Art. 14(1) acts on content once found (发现违法内容); see R26-2. (3) Open CC0 text any LLM may accept vs binding regulation: accurate. (4) Population-level aims: accurate.

**Other rows of tab:paradigms against (a) and (f).** (b) "Procedure around the decision" with no intercept: consistent with DSA Art. 16, 17(3)(c), 20(6). (c) "None": consistent. (d) "Yes, as code … no duty to give reasons or to keep records": consistent with (a)/(f) coding of duties. (e) "no content layer": consistent. Within (a) and (f) the intercept cells are now symmetric ("yes, as a duty … mechanism unspecified"). No other row is miscoded. The only residual coding asymmetry is in the prose gap sentence, not in the table (R26-1).

## Task 2: fresh pass

**Balance of §2.3.** The "only" claim is gone and costs (i)–(v) are intact. The new gap sentence (l.127) now errs the other way: it extends Art. 4(1) to the valve because §5.4 names the whole project NaturalDAO, but withholds Art. 4(3) (questioning of "any decision" with a duty to explain, in the same article), Art. 5(4)–(5) (stated of "NaturalDAO" generally) and Art. 10 ("all disputes"), and then contrasts \pol{} with the CAC's complaint channel, although \pol{} has questioning and problem reporting (Art. 4(3), 9(1), 9(6)) and the CAC likewise states no reasons or record for an individual content stop under Art. 14(1). §2.2 l.42 itself cites Art. 4 for the explanation duty. A referee would read this as an inconsistent scope rule, not as tilt in \pol{}'s favour; it is still a fidelity error in a comparison written by a contributor (R26-1).

**Case-selection rationale.** 02b l.129 and §1 l.14 justify the case because "its construct and intercept are stated precisely enough to be tested", while (i), row (f) and l.128 say the mechanism, thresholds and "where necessary" are unspecified and guardrails specify the intercept more precisely; and row (a) is now coded identically on the intercept. What is precise and testable is the valve's object (every input and output) and the construct (R26-2).

**Verdict traceability (§7.1, §8, tab:verdict ↔ tab:keyfindings).** Unchanged since round 25; certainties and "four contested" match the script output (CHECK PASSED). No break.

**Consistency chain.** Abstract and §8 contain no uniqueness claim; §1 l.14, 02b l.120–129 and 07 l.115 agree on the CAC Measures joining intercept, standard and decision duties and on "at most in part" (records, complaint channel). §1 l.14 introduces "the case" and "its construct" one sentence before \pol{} is named (l.15): R26-5. Metadata abstract = 00_abstract.tex.

**Layout.** tab:paradigms pp. 8–9 with repeated header; "What the comparison implies" runs pp. 10–11, gap sentence breaks across the page in running text; no new overfull box. Accepted.

## Findings

**R26-1 [minor] The gap sentence applies Art. 4(1) to the safety valve but not Art. 4(3), 5(5) or 10, and contrasts \pol{} with the CAC complaint channel asymmetrically.**
- **Location:** 02b_pol2.tex l.127; secondarily 07_discussion.tex l.115 (unchanged wording is fine).
- **Source:** zh_7 第四条 (1) 所有NaturalDAO技术的运行逻辑、决策过程和输出结果必须完全公开透明; (3) 人类可随时提供建议、质询任何决策，NaturalDAO对质询必须提供可理解的解释; 第五条(5) NaturalDAO必须提供可验证的决策链路; 第九条(6) 问题报告; 第十条 所有争议由NaturalDAO自主裁决. CAC 第十四条第一款 (content stop: no record or notice to the person), 第十五条 (general complaint channel). 02b l.42 cites \art{4} for explanation when questioned.
- **Problem:** If §5.4's naming makes Art. 4(1) plausibly reach the valve, the same reasoning reaches Art. 4(3) (explanation of any decision questioned), Art. 5(5) (decision chain of NaturalDAO) and Art. 10 (all disputes); singling out 5(5), 9(2), 10 as "framed within the welfare protocol" while Art. 4 is in the same protocol is not textually grounded. Conversely the CAC states no reasons or record for an individual content stop either; its records (14(2)) concern measures against users, and Art. 15 is a general complaint channel. The contrast "whereas the Measures provide a complaint channel" thus compares \pol{}'s weakest reading with the CAC's strongest.
- **Fix:** e.g. "The join has a gap in \pol{}: \clause{5.4} names the whole project NaturalDAO, so its duties of openness, explanation on questioning and a verifiable decision chain (\art{4}(1), (3), \art{5}(5)) and its dispute procedure (\art{10}) plausibly reach the safety valve, but no clause addresses a block as such: none requires the blocked person to be told, and questioning and disputes are resolved by NaturalDAO itself (\art{9}(7), \art{10}); the Measures likewise state no notice for a content stop (Art.~14(1)) but give users a complaint channel with time limits and feedback (Art.~15) and require records of measures against users (Art.~14(2)). This is a gap that the design … fills …". Add \art{4}(3) where §2.3 lists \pol{}'s explanation duty if desired.

**R26-2 [minor] The case-selection rationale says the intercept is "stated precisely enough to be tested", which (i), row (f) and l.128 contradict, and the four differences omit the intercept difference that is precise.**
- **Location:** 02b_pol2.tex l.124 (second difference) and l.129; 01_introduction.tex l.14.
- **Source:** zh_5 §5.4.1 对输入输出进行严格的动态审计与拦截 … 在必要情况下; CAC 第十四条第一款 提供者发现违法内容的 …; 02b (i) "the text does not say how the valve is built, what 'where necessary' means"; row (f) "mechanism, thresholds and appeal unspecified"; l.128 guardrails "specify the intercept … more precisely".
- **Problem:** With rows (a) and (f) now coded identically on the intercept, the claim that \pol{}'s intercept is precise enough to test is unsupported as worded; what the text does fix is the valve's object (every input and output, in both directions) and the three-valued construct, which is also what separates it from the CAC's on-discovery duty.
- **Fix:** Add to the second difference: "and the valve screens every input and output (\clause{5.4.1}), whereas Art.~14(1) applies once unlawful content is found". In l.129 and §1 l.14 replace "its construct and intercept are stated precisely enough to be tested" with "what its valve must screen (every input and output) and the construct it applies are stated precisely enough to be tested".

**R26-3 [nit] CAC Art. 4 and Art. 17 summarised without qualifiers.**
- **Location:** 02b l.123 ("the Measures' standard is binary, lawful or unlawful, and set by the state"); row (a) intercept cell "with filing and security assessment (Art. 17)".
- **Source:** 第四条 chapeau 尊重社会公德和伦理道德, (一) 坚持社会主义核心价值观; 第十七条 提供具有舆论属性或者社会动员能力的生成式人工智能服务的.
- **Fix:** l.123 "the standard that triggers the Measures' intercept is binary, lawful or unlawful content, set by the state (Art.~14(1)), within an Art.~4 that also invokes social morality and core socialist values"; row (a) "(Art.~17, for services with public-opinion or mobilisation capacity)".

**R26-4 [nit] The §5.4 naming passage that the gap argument rests on is not quoted in tab:concordance.**
- **Location:** 02b l.127 "\clause{5.4} names the whole engineering project … NaturalDAO"; A_concordance.tex l.40 (\clause{5.4} row quotes only the governance-layer sentence).
- **Fix:** add to the \clause{5.4} row "……我们将该工程称之为 NaturalDAO（自然道）" / "… We call this project NaturalDAO (the Natural Way)." (en_5).

**R26-5 [nit] §1 l.14 refers to "the case" and "its construct" before \pol{} is named.**
- **Location:** 01_introduction.tex l.13–15.
- **Fix:** move the l.14 sentence after l.15 (after "Proof of Love2 (\pol{}) is an open, versioned governance text …").

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 2 | R26-1, R26-2 |
| Nit | 3 new, plus 5 carried | R26-3, R26-4, R26-5; R17-2, R17-3, R21-1, R21-2, R21-3 |

R25-1: FIXED (the "only" claim and its asymmetric coding are gone; the new gap sentence raises R26-1). R25-2: FIXED.

New major or minor problems remain: yes
