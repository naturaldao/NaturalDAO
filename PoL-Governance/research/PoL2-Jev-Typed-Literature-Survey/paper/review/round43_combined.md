# Round 43: combined review (consistency, cross-reference integrity, fidelity, arXiv moderator)

Date: 2026-10-09. Scope: the round-42 fixes (AUDIT.md, last line); a first-time reader's pass over the front matter (title page, abstract, §1) of main.pdf and zh/main_zh.pdf, with attention to how PoL / PoL2 are introduced and how the supplement is signposted; cross-references between paper and supplement in all four PDFs; factual accuracy of the repository documents to be published (README.md, CHANGELOG.md 0.4.0, CITATION.cff, paper/README.md) against the paper and data, including the existence of every path they mention. Items resolved in REVIEW.md, AUDIT.md and rounds 12–42 are not re-raised; author-only items (author placeholder, merging the branch so the supplement URL resolves) are not findings.

**Inputs**
- main.pdf 9 Oct 00:37:14, supplement.pdf 00:37:16, zh/main_zh.pdf 00:38:05, zh/supplement_zh.pdf 00:38:13, arxiv-submission.zip 00:38:14; no source in paper/sections, paper/zh/sections, main.tex, supplement.tex or *.bib is newer than its PDF (files newer than the PDFs are build outputs only: logs, aux, paper/arxiv/*).
- Logs: main.log "(67 pages)", supplement.log "(40 pages)", main_zh.log "(64 pages)", supplement_zh.log "(41 pages)"; 0 `!` lines, 0 undefined or multiply-defined references in all four.
- pdftotext of main.pdf and supplement.pdf: 0 "??". Chinese PDFs: no extractable CJK text (as in rounds 41–42); checked on sources, logs and rendered page images.
- Cross-document labels: all 78 labels in main_labels.tex and zh/main_labels.tex and all 36 in supplement_labels.tex and zh/supplement_labels.tex carry the same number as in the corresponding .aux (main.aux, supplement.aux, zh/main_zh.aux, zh/supplement_zh.aux): 0 mismatches, so every "Section x" in the supplements and every "Supplement Sx / Table Sx" in the papers is current.
- paper/arxiv/*.tex identical to paper/sections/*.tex except flattened figure paths and stripped comment lines; zip anc/supplement.pdf byte-identical to supplement.pdf (1254045 bytes).
- arxiv_metadata.txt: abstract 1917 characters; "67 pages, 6 figures; supplementary material (40 pages)" matches the logs and the six figure PDFs in the zip.
- `python scripts\rate_certainty.py --check`: CHECK PASSED. Now: 0 moderate, 11 low, 4 very low; contested 2, 5, 11, 14.
- Paths: every path named in README.md, paper/README.md, CHANGELOG.md 0.4.0 and the data statement (09_statements l.21–22) exists in the directory (paper/build.py, make_arxiv.py, make_metadata.py, zh/GLOSSARY.md, zh/QA_LOG.md, figures/src/f4p_style.py, review/PROTOCOL.md, review/coding/, all data/*.csv and *_update_2026-10-08.csv files, data/pol2_axes.json, data/sources/arxiv_meta.csv, scripts/merge_coding.py, merge_update.py, rate_certainty.py, rerun_arxiv_search.py, rerun_arxiv_search_web.py, rerun_zenodo_search.py, build_catalog.py, fetch_papers.ps1, docs/survey.zh.md, papers/LICENSES.md; `.gitignore` ignores papers/_local/). Links outside the directory, checked on GitHub main 9 Oct: PoL-Governance/README.md, tasks/LIT-01-shenton.md, TASKS.md, models/CATALOG.md, benchmark/README.md, tree/main/PoL all 200; …/paper/supplement.pdf still 404 (author item, R41-6).

## Verification of round-42 findings

| Finding | Status | Evidence |
|---|---|---|
| R42-1 §1 leftover sentence, double expansion | Resolved | 01_introduction.tex l.12 defines "PoL governance, that is, governance under the Proof of Love2 (\pol{}) specification"; l.13 now begins "\pol{} is an open, versioned governance text"; "Proof of Love2 (" occurs once in §1 (EN) and "爱2证明（" once (ZH). ZH l.12–14 now match EN sentence for sentence. The optional abstract comma was not applied (R43-4). |
| R42-2 CHANGELOG update flow and adjudication | Resolved | CHANGELOG 0.4.0 l.5: 62 read in full, 5 excluded, 57 kept (31/26), 48 coded, 118 pairs, κ = 0.55, "分歧由第三轮 AI 裁定"; matches 03_method l.67–68, l.74 and counts_update.tex (nUDocs 57, nUCoded 48, nURows 118, nUKappa 0.55). |
| R42-3 paper/README appendix references | Resolved | paper/README.md l.46 "补充材料 S1 为中英逐字摘录与旧编号", l.48 "规则见补充材料 S5". |
| R42-4 README ninth lesson | Resolved | README 主要发现 5 now lists nine lessons, including "对事件评分而不对人评分", matching §7.1 l.97–107. |
| R42-5 two "62"s in §3 | Resolved | l.59 "the Zenodo queries of 1~October about 330 records, of which 62 …" (ZH "10 月 1 日的 Zenodo 检索") versus l.67 under "Update search"; the two quantities are now distinguishable by date and paragraph. |
| R42-6 round counts | Resolved for round 42, stale again | README tree "（42 轮）", CHANGELOG "审稿第 12–42 轮"; this round makes both stale (R43-5). |

## Checks

**(1) Front matter, first-time reader (EN and ZH PDFs).** Title page names "PoL Governance" and "the Proof of Love2 (PoL2) Specification"; the abstract (sentence 2) and §1 l.12 tie the two together ("PoL governance … under Proof of Love2 (PoL2)"), and §1 l.13 says what PoL2 is (open, versioned text; inner governance layer; safety valve, cl. 5.4.1). PoL2 is expanded once in each of title, abstract and §1, consistently, and the ZH front matter mirrors it ("PoL 治理，即依据爱2证明（PoL2）规范进行的治理"). "PoL" alone is not expanded; with the stated equation this remains acceptable (as in round 42). The research question, the detector/judge distinction, the thesis and the verdict in §1 agree with the abstract, §7.1 and Table 6 (verdict functions, precautionary ground for per-person quantification, extrapolation from English benchmarks, update search reversing no answer). Problems: R43-2 (supplement signposting in §1), R43-3 (title and URL line breaks), R43-4 (abstract comma).

**(2) Paper ↔ supplement.** main.pdf points to Supplement S1, S2, S4, S4.1, S5, S5.3, S5.4 and Tables S1, S8; supplement.pdf points back to main sections, tables and figures; all resolve (label check above), and no "Appendix" wording for moved material remains in either PDF (the one "appendix" in supplement.pdf is "appendix E.10 of the source", a study's appendix). Title pages: EN "Supplementary material (Supplements S1–S5): ancillary file anc/supplement.pdf … and <URL>"; ZH names the Chinese supplement URL and the English ancillary file; both supplements open with a paragraph explaining the S-prefix and that section references use the paper's numbering. §9 l.21 lists the contents of S1–S5.

**(3) Repository documents against the paper and data.** README 主要发现 1–3, 5 and 6 match the abstract, §1, §2.3 l.65–75, §4.9 l.366, §6 (16 checklist items, item 7 label-only oracle attacks, item 16 temporal re-validation), §7.1 and Table 6. CHANGELOG 0.4.0 matches the paper on the title, the split (S1–S5, anc/, build.py), update-search counts, §2.3, §7.1 and nine lessons, rating output (0/11/4, confirmed by the script), checklist items 7 and 16, and the EU-law scoping (Art. 5(1)(f) biometric; Art. 14 and 86 Annex III; 05_synthesis l.55–56). CITATION.cff title, version 0.4.0 and date 2026-10-09 match paper/README.md and CHANGELOG. Exceptions: R43-1, R43-6, R43-7. Not verified: the count "8 篇治理范式文献" in CHANGELOG l.11 (no list of the added entries in the repository).

## Findings

**R43-1 [minor] README 主要发现 4 asserts what the paper says the evidence does not show.**
- Location: README.md l.27: "**多数失效并非类型化模型独有**，但大多数失效从未与生成式评估器对比过，所以这一判断对低成本生成式评估器同样适用（出于审慎）。"
- Evidence: 04_evidence.tex l.269 "The evidence therefore does not show that typed models are generally worse than generative evaluators, nor that their failures are shared with them; for most failures the comparison has not been made"; §1 l.33 "the evidence neither singles out typed models nor shows that their failures are shared"; §7.1 l.84 "the verdict is not specific to typed models". The bold heading states as a finding ("most failures are not unique to typed models") the very claim the paper declines to make, and the following clause ("most were never compared") contradicts it. This is a published summary of the paper's comparative hedge, the point rounds 22–23 tightened in the paper itself.
- Fix: "**结论并非专门针对类型化模型。** 在做过对比之处，类型化模型总体上并不比生成式评估器差；但大多数失效从未对比，证据既不表明失效为类型化模型独有，也不表明二者共有，所以这一结论出于审慎同样适用于低成本生成式评估器。"

**R43-2 [nit] §1 uses "Supplement S1" without saying what or where the supplement is.**
- Location: 01_introduction.tex contribution 1 ("passages from 28 clauses, Supplement S1"); the only explanations are the title-page line and §9 l.21 at the end of the paper; §1 has no organisation paragraph.
- Evidence: a reader who skipped the small-print title-page line meets "Supplement S1" (and later S2–S5) with no in-text explanation until the statements section.
- Fix (optional): at the end of §1 "Scope", one sentence: "Supplements S1–S5 (clause concordance, evidence tables, catalogue, corrections and certainty ratings, codebook and search) are a separate PDF, provided as an ancillary file." ZH likewise. The ZH title-page wording "补充材料（补充材料 S1–S5）" could read "补充材料 S1–S5".

**R43-3 [nit] Title-page line breaks in main.pdf.**
- Location: main.tex l.11 (`…Automated Safeguards\\ in PoL Governance?`) and l.19 (URL).
- Evidence: the title wraps naturally after "Automated" and then breaks again at the forced `\\`, leaving "Safeguards" alone on line 2 of a three-line title (rendered page 1); the supplement URL breaks inside a word ("PoL2-Jev-T / yped-Literature-Survey"). Cosmetic, but it is the first thing a moderator sees.
- Fix: `Can Typed Decision Models Serve as\\ Automated Safeguards in PoL Governance?` (check that it fits on two lines); for the URL, allow breaks only at "/" (e.g. `\def\UrlBreaks{\do\/}` locally) or put the URL on its own line.

**R43-4 [nit] Stray comma in the abstract (carried from the optional part of R42-1).**
- Location: 00_abstract.tex l.3 and arxiv_metadata.txt: "We ask whether they can serve as safeguards, for PoL governance under Proof of Love2 (PoL2), an open text …".
- Fix: drop the comma after "safeguards" (−1 character; 1916 ≤ 1920); regenerate the metadata.

**R43-5 [nit] Review-round counts are stale again.**
- Location: README.md l.46 "审稿与修订记录（42 轮）"; CHANGELOG.md l.11 "审稿第 12–42 轮".
- Evidence: round 43 now exists in paper/review/. Each round makes a fixed number stale.
- Fix: write "多轮" / "第 12 轮起", or set the number once at release after the last round.

**R43-6 [nit] paper/README.md uses Chinese terms that differ from the glossary and the Chinese paper.**
- Location: paper/README.md l.44 "“judge”只用于文中定义的“裁判”含义"; l.48 "针对“探测器”用途".
- Evidence: zh/GLOSSARY.md l.68–69 and every ZH section use 检测器 (detector) and 裁决者 (judge); "裁判" and "探测器" occur in no ZH section.
- Fix: "裁决者"; "检测器".

**R43-7 [nit] README 主要发现 3 drops the scope of the 97–100% figure.**
- Location: README.md l.26 "针对 Jev 的注入攻击成功率达 97–100%".
- Evidence: 04_evidence.tex l.366: one update-search study, a Jev-specific injection and a universal suffix, "on three tasks". The README states it as a general rate.
- Fix: "一项研究中，针对 Jev 的注入攻击在三项任务上成功率达 97–100%".

## Carried

R17-2, R17-3, R21-1, R21-2, R21-3, R37-1, R38-2, R40-1: not applied, carried (nits). R41-6 URL: author item (404 until merge; consider a tag- or commit-pinned URL).

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 1 | R43-1 |
| Nit | 6 new, plus 8 carried | R43-2, R43-3, R43-4, R43-5, R43-6, R43-7; R17-2, R17-3, R21-1, R21-2, R21-3, R37-1, R38-2, R40-1 |

R42-1 to R42-5 verified as resolved in EN and ZH sources, PDFs and repository documents; R42-6 resolved for round 42 but stale again (R43-5). Four PDFs current, no "??", no undefined references, cross-document labels consistent, every mentioned path exists; metadata 1917 characters; rate_certainty --check passed.

New major or minor problems remain: yes
