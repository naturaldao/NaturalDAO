# Round 28: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R27-1..R27-4 against the CAC text and \pol{}; fresh whole-paper pass (balance and accuracy of §2.3, verdict traceability §7.1/§8, consistency abstract ↔ §1 ↔ §2.3 ↔ boxes ↔ §7 ↔ §8 ↔ metadata, layout). Items resolved in REVIEW.md, AUDIT.md and rounds 12–27 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/01_introduction.tex, 02b_pol2.tex, 07_discussion.tex (23:16:19); main.pdf, main.log (23:16:29); arxiv_metadata.txt, arxiv-submission.zip (23:16:30).
- main.log: "Output written on main.pdf (95 pages, 2035223 bytes)", no `!` lines, no undefined references, 17 overfull boxes (all ≤ 5.98pt, same set as round 27, none in 01, 02b or 07).
- arxiv-submission.zip extracted to scratchpad/r28z: 00, 01, 02b, 07, 08 equal sections/*.tex up to CRLF.
- `python scripts/rate_certainty.py --check` (run from the repository root): CHECK PASSED (changed vs given 4 Oct: 2, 3, 5, 11, 14), as in round 27.
- PDF p. 2 and pp. 10–11 via pdftotext.
- CAC 生成式人工智能服务管理暂行办法 (cac.gov.cn/2023-07/13/c_1690898327029107.htm): 第四条 chapeau 提供和使用 … 应当 … （一）… 不得生成 … 法律、行政法规禁止的内容; 第十四条第一款 提供者发现违法内容的，应当及时采取停止生成、停止传输、消除等处置措施，采取模型优化训练等措施进行整改，并向有关主管部门报告; 第十四条第二款 … 保存有关记录; 第十五条.
- \pol{} zh_5.md l.134 安全阀 … 对输入输出进行严格的动态审计与拦截。通过这种双向的主动防御 … 在必要情况下.

## Task 1: re-check of round 27

| Item | Status | Evidence |
|---|---|---|
| R27-1 Art. 4(1) outcome duty | FIXED | 02b l.124 now: "\pol{} defines the valve as screening every input and output in both directions (§5.4.1), whereas the Measures state an outcome, that no unlawful content be generated (Art. 4(1)), and a duty to act once it is found (Art. 14(1)), leaving how outputs are screened, and whether inputs are, to the provider." Matches 第四条（一）不得生成 … and 第十四条第一款 发现违法内容的; "in both directions" = 双向; the Measures indeed say nothing about screening inputs. PDF p. 10 renders it. |
| R27-2 content stop reported to authorities | FIXED | 02b l.129 "a content stop under Art. 14(1) is reported to the competent authorities, not to the user: no article requires notice to the user, reasons or a record for it" = 并向有关主管部门报告; records only in 14(2). |
| R27-3 07 l.115 records | FIXED | "the Chinese Measures require records of measures taken against users and a complaint channel, Art. 14(2) and 15"; now consistent with 02b l.129. |
| R27-4 §1 l.15 split | FIXED | l.15 split after "what each costs."; PDF p. 2 reads "China's 2023 Interim Measures on generative AI also join …; \pol{} is chosen not for uniqueness but because …". |

## Task 2: fresh pass

**Balance and accuracy of §2.3.** With R27-1 and R27-2 in place the four differences and the two-sided gap are symmetric and each clause is checkable against the source: the Measures are credited with an outcome duty over every output, a duty to act, rectification and reporting, records for measures against users and a complaint channel; \pol{} with every-input-and-output screening, plausible reach of Art. 4(1), 4(3), unclear reach of 5(5) and 10, and no notice to a blocked person. Costs (i)–(v), "not uniqueness" and "natural second case" intact. No new accuracy issue.

**Verdict traceability (§7.1, §8 ↔ tab:verdict ↔ tab:keyfindings).** 07 §7.1 and 08 unchanged since round 25 apart from 07 l.115 (in §7.2); script check passes; no break.

**Consistency chain.** Abstract = metadata (no change); neither makes a uniqueness or CAC claim. §1 l.15, 02b l.120–132 and 07 l.115 now agree on what the Measures join and on records being for measures against users. 95 pages agree across log and metadata. One residual: §1 l.15 names "China's 2023 Interim Measures on generative AI" without a citation, while every other mention (02b l.120, l.134; 07 l.115) carries \cite{cac2023genai} (R28-1).

**Layout.** p. 2 and pp. 10–11 read correctly; no new overfull box.

## Findings

**R28-1 [nit] First mention of the Interim Measures in §1 is uncited.**
- **Location:** 01_introduction.tex l.15 ("China's 2023 Interim Measures on generative AI also join …").
- **Problem:** A reader of §1 meets a named legal instrument with no reference; the citation appears only in §2.3.
- **Fix:** add `~\cite{cac2023genai}` after "generative AI".

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 0 | |
| Nit | 1 new, plus 5 carried | R28-1; R17-2, R17-3, R21-1, R21-2, R21-3 |

R27-1, R27-2, R27-3, R27-4: FIXED.

New major or minor problems remain: no
