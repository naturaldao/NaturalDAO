# Round 27: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R26-1..R26-5 against the CAC text and \pol{}; fresh whole-paper pass (balance and accuracy of §2.3, verdict traceability §7.1/§8 ↔ tab:keyfindings, consistency abstract ↔ §1 ↔ §2.3 ↔ boxes ↔ §7 ↔ §8 ↔ metadata, layout). Items resolved in REVIEW.md, AUDIT.md and rounds 12–26 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/01_introduction.tex, A_concordance.tex (23:12:13), 02b_pol2.tex (23:12:22); main.pdf, main.log (23:12:32); arxiv_metadata.txt, arxiv-submission.zip (23:12:38).
- main.log: "Output written on main.pdf (95 pages, 2034997 bytes)", no `!` lines, no undefined references, 17 overfull boxes (all ≤ 5.98pt, none in 02b), as in round 26.
- arxiv-submission.zip extracted to scratchpad/r27z: 00, 01, 02b, 07, 08, A equal sections/*.tex up to CRLF.
- arxiv_metadata.txt: abstract 1,916 ≤ 1,920 and identical in substance to 00_abstract.tex; "95 pages, 7 figures" agrees with the log.
- `python scripts/rate_certainty.py --check`: CHECK PASSED (given 4 Oct 1 moderate/9 low/5 very low; changed vs given: 2, 3, 5, 11, 14).
- PDF pp. 1–3, 10–12 via pdftotext.
- CAC 生成式人工智能服务管理暂行办法, https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm, fetched 2026-10-08: Art. 4 (chapeau and (一)), 9, 10, 14(1), 14(2), 15, 17.
- \pol{}: scratchpad/pol/zh_5.md l.127 我们将该工程称之为 NaturalDAO（自然道）, l.134 (安全阀 … 对输入输出进行严格的动态审计与拦截 … 在必要情况下); en_5.md l.101, l.108; zh_7.md 第四条(1),(3), 第五条(4),(5), 第九条(1),(2),(7), 第十条; en_7.md Art. 4(3), 9, 10.

## Task 1: re-check of round 26

| Item | Status | Evidence |
|---|---|---|
| R26-1 asymmetric gap sentence | FIXED (one omission on the CAC side: R27-2) | 02b l.127–129: gap "in both texts, at the individual block"; Art. 4(1) and 4(3) said to plausibly reach the valve (zh_7 第四条(1) 所有NaturalDAO技术 …; (3) 质询任何决策 … 必须提供可理解的解释: accurate); Art. 5(5) and Art. 10 "unclear" is defensible (Art. 5 is headed 【NaturalDAO作为福利载体】, Art. 10 sits in the welfare protocol's 第四章); "no clause requires that a blocked person be told": accurate. CAC side: Art. 15 complaint channel with 反馈时限 and 反馈处理结果: accurate; "no article requires notice to the user, reasons or a record for a content stop under Art. 14(1)": accurate (records appear only in 14(2), for measures against users). "framed within the welfare protocol" gone. Row (f) transparency cell "For NaturalDAO (Chapter 7): … fully open (Art. 4)" consistent. |
| R26-2 "precisely enough"; every-input screening | FIXED in l.132 and §1 l.15 (construct and point of interception stated in citable clauses; "how the valve works is left open"); the added clause of the second difference is FIXED as to \pol{} but understates the Measures (R27-1) | zh_5 l.134 对输入输出进行 … 审计与拦截; 02b l.124, l.132; 01 l.15 |
| R26-3 Art. 4 / Art. 17 qualifiers | FIXED | l.123 "within an Art. 4 that also invokes social morality and ethics and core socialist values" = 第四条 chapeau 尊重社会公德和伦理道德, (一) 坚持社会主义核心价值观; row (a) taxonomy cell adds both; row (a) intercept cell "for services with public-opinion attributes or social-mobilisation capacity (Art. 17)" = 第十七条 具有舆论属性或者社会动员能力 |
| R26-4 §5.4 naming in tab:concordance | FIXED | A_concordance l.40 "……我们将该工程称之为 NaturalDAO（自然道）。" / "… We call this project NaturalDAO (the Natural Way)." = zh_5 l.127, en_5 l.101 verbatim |
| R26-5 §1 order | FIXED | 01 l.14 names \pol{} first; l.15 comparison sentence follows; PDF p. 2 reads in that order |

## Task 2: fresh pass

**Balance and accuracy of §2.3.** Rows (a) and (f) are coded symmetrically on intercept ("mechanism … unspecified"), standard and decision duties; costs (i)–(v) intact; "not uniqueness" and "natural second case" stated; the gap is now in both texts. Two residual accuracy points on the CAC side, both introduced or exposed by the R26 fixes: the second difference contrasts \pol{}'s every-input-and-output screening with Art. 14(1) "once unlawful content is found" but omits that Art. 4(一) already forbids generating unlawful content at all (不得生成 … 法律、行政法规禁止的内容), an outcome duty over every output (R27-1); and the CAC half of the gap sentence omits that Art. 14(1) itself requires rectification and a report to the competent authorities (R27-2). Neither tilts the verdict; both are fidelity points a reader of Chinese law would catch.

**Verdict traceability (§7.1, §8, tab:verdict ↔ tab:keyfindings).** 07 and 08 unchanged since round 25; §8 l.4–8 functions (Art. 10, 6(3), §5.6, final block; detectors §5.4.1, §4.3.3.1, Art. 7 on text; §5.6 aggregate) match tab:verdict and §1 l.36; "four contested" and "low or very low" match the script output. No break.

**Consistency chain.** Abstract = metadata; abstract and §8 make no uniqueness claim; §1 l.15, 02b l.120–132 and 07 l.115 agree on the CAC Measures joining intercept, standard and decision duties. One wording now jars: 07 l.115 "the Chinese Measures require records of the measures taken" next to 02b l.129 "no … record for a content stop" (R27-3). 95 pages agree across log, metadata and AUDIT.

**Layout.** "What the comparison implies" pp. 10–11, gap sentence continues across the page break in running text; no new overfull box; §1 p. 2 reads correctly. §1 l.15 is now one sentence of about 95 words (R27-4).

## Findings

**R27-1 [minor] The second difference understates the Measures: Art. 4(一) forbids generating unlawful content in any output, not only once it is found.**
- **Location:** 02b_pol2.tex l.124 ("and the valve screens every input and output (\clause{5.4.1}), whereas Art.~14(1) applies once unlawful content is found").
- **Source:** CAC 第四条 提供和使用生成式人工智能服务，应当 … 遵守以下规定：（一）坚持社会主义核心价值观，不得生成 … 法律、行政法规禁止的内容; 第十四条第一款 提供者发现违法内容的 …. \pol{} zh_5 l.134 对输入输出进行严格的动态审计与拦截.
- **Problem:** The sentence reads as if the Measures act only after discovery, while Art. 4 places on provision and use an ex-ante prohibition that covers every output; what the Measures leave open is how the provider meets it (screening, training, filtering), and they say nothing about inputs. As written the difference overstates \pol{}'s distinctiveness in the comparison a contributor-written section draws.
- **Fix:** e.g. "and \pol{} defines the valve as screening every input and output in both directions (\clause{5.4.1}), whereas the Measures state an outcome, that no unlawful content be generated (Art.~4(1)), and a duty to act once it is found (Art.~14(1)), leaving how outputs are screened, and whether inputs are, to the provider."

**R27-2 [nit] The CAC half of the gap sentence omits Art. 14(1)'s rectification and reporting duty.**
- **Location:** 02b l.129.
- **Source:** 第十四条第一款 … 采取模型优化训练等措施进行整改，并向有关主管部门报告.
- **Problem:** "no article requires notice to the user, reasons or a record for a content stop" is accurate, but the stop does carry a report to the authorities, which \pol{}'s valve lacks; the symmetric comparison should say so.
- **Fix:** "… but a content stop under Art.~14(1) is reported to the authorities, not to the user: no article requires notice, reasons or a record for it."

**R27-3 [nit] 07 l.115 "records of the measures taken" sits awkwardly with 02b l.129.**
- **Location:** 07_discussion.tex l.115.
- **Problem:** After the R26-1 fix §2.3 says there is no record for a content stop; §7.2 still says the Measures "require records of the measures taken", which a reader can take to include content stops.
- **Fix:** "require records of measures taken against users and a complaint channel (Art.~14(2) and~15)".

**R27-4 [nit] §1 l.15 is one ~95-word sentence.**
- **Location:** 01_introduction.tex l.15.
- **Fix:** split after "what each costs": "… what each costs. China's 2023 Interim Measures on generative AI also join …; \pol{} is chosen not for uniqueness but because …".

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 1 | R27-1 |
| Nit | 3 new, plus 5 carried | R27-2, R27-3, R27-4; R17-2, R17-3, R21-1, R21-2, R21-3 |

R26-1: FIXED (R27-2 nit on the CAC side). R26-2: FIXED as to the rationale; the added comparison clause raises R27-1. R26-3, R26-4, R26-5: FIXED.

New major or minor problems remain: yes
