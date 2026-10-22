# Round 42: combined review (consistency, cross-reference integrity, fidelity, arXiv moderator)

Date: 2026-10-09. Scope: the round-41 fixes (AUDIT.md, last line), the naming chain "PoL governance / Proof of Love2 (PoL2)" across paper, metadata and repository documents, a fresh pass on the paper/supplement split, and factual accuracy of README.md, paper/README.md and the CHANGELOG 0.4.0 entry, which will be published. Items resolved in REVIEW.md, AUDIT.md and rounds 12–41 are not re-raised; author-only items (author placeholder, merging the branch) are not findings.

**Inputs**
- main.pdf 9 Oct 00:30, supplement.pdf 00:30, zh/main_zh.pdf 00:31, zh/supplement_zh.pdf 00:32, arxiv-submission.zip 00:32; all later than every edited source (latest source edit 00:30:36).
- Logs: main.log "(67 pages)", supplement.log "(40 pages)", main_zh.log "(64 pages)", supplement_zh.log "(41 pages)"; 0 `!` lines, 0 undefined or multiply-defined references or citations in all four.
- pdftotext of main.pdf and supplement.pdf: 0 occurrences of "??". The Chinese PDFs yield no extractable CJK text (as in round 41); checked on sources and logs.
- paper/arxiv/*.tex identical to paper/sections/*.tex except the flattened paths (\input, figure paths); zip anc/supplement.pdf 1254045 bytes, equal to supplement.pdf.
- arxiv_metadata.txt abstract: 1917 characters (recounted), limit 1920.
- `python scripts\rate_certainty.py --check`: CHECK PASSED. Now: 0 moderate, 11 low, 4 very low; contested 2, 5, 11, 14.
- curl, 9 Oct: …/blob/main/…/paper/supplement.pdf still returns 404 (author item: merge before submission; see R41-6).

## Verification of round-41 findings

| Finding | Status | Evidence |
|---|---|---|
| R41-1 screening counts in §3 | Resolved | 03_method.tex l.59 (EN) and zh l.59: 955 records (606 unique), 89 in window; Zenodo about 330, 62 meeting keyword and date criteria; matches E_codebook.tex l.65/l.69 (S5.4). |
| R41-2 PoL introduced, relation to PoL2 | Resolved | Abstract l.3 "for PoL governance under Proof of Love2 (PoL2)"; §1 l.12 "PoL governance, that is, governance under the Proof of Love2 (PoL2) specification"; ZH abstract and §1 "PoL 治理，即依据爱2证明（PoL2）规范进行的治理". The incorrect ZH gloss "PoL（爱2证明）" is gone. Residual wording issue in R42-1. |
| R41-3 framing vs case language | Resolved | §1 l.15 "what makes PoL2 a useful object of study is not uniqueness but…"; §2.3 l.58–62 "Why a specification is needed" (EN) / "为何需要一份规范" (ZH) explains why the question needs a specification; §2.2 "We use PoL2 as a case" is compatible with a PoL-centred paper that studies PoL2 as its case. |
| R41-4 spelling | Resolved | No "Proof-of-Love" or bare "Proof of Love" remains in sections, main.tex, supplement.tex, preamble (pdftitle), arxiv_metadata.txt, CITATION.cff, README.md, paper/README.md, CHANGELOG.md. |
| R41-5 Table S9 13c | Resolved | E_codebook.tex l.114 "Figure 2, Table 3 and Table S2" via separate \cref (EN and ZH). |
| R41-6 title page names ancillary copy | Resolved in sources and PDF | main.tex \date: "ancillary file anc/supplement.pdf of the arXiv submission and <URL>"; zh/main_zh.tex names the English ancillary copy. URL still 404 (author item). |

## Checks

**(1) Naming chain.** Title (main.tex, preamble pdftitle, supplement.tex, zh), abstract (EN/ZH, metadata), §1 l.12, §2.2 heading "The case: the Proof of Love2 governance specification", §2.3 heading "PoL2 among AI-governance paradigms", §8 (uses PoL2 and "the specification" only), arxiv_metadata.txt title and abstract, CITATION.cff title and keywords, README.md H1, paper/README.md H1, CHANGELOG 0.4.0: one title, one spelling, one definition of PoL governance. "PoL" itself is never expanded; with "PoL governance = governance under PoL2" stated, this is acceptable. Wording issue in §1 only (R42-1).

**(2) Split.** References from paper to supplement render as "Supplement S1–S5", "Table S1", "Table S8"; every one is a pointer to tabulation, quotation or audit trail, and the paper states the content it relies on (requirements, verdict, key findings, coding categories at §3.4 l.95–96, update flow, now also the main search's identification counts). Rule (iv) is cited as "rule (iv) of Supplement S5" (03_method l.76–78) but its content is also stated in §3.4 l.96, so a reader of the paper alone can follow; acceptable. No "??", no "Appendix" wording for moved material, page and figure counts match the metadata.

**(3) Repository documents against the paper.** README "主要发现" 1–4 and 6 match §7.1, Table 6, §8, abstract and §2.3 (verdict scope, detector conditions, English-binary extrapolation, 97–100% injection success, "not generally worse" with precaution, PoL2 and the Interim Measures as the two texts joining intercept, construct and decision duties, "not uniqueness"). §6 checklist has 16 items (item 16 temporal re-validation), §7.1 has nine lessons, ratings 0/11/4, κ 0.55 on 118 pairs, 48 coded (27 arXiv, 21 Zenodo): all consistent. Exceptions in R42-2 to R42-4, R42-6.

## Findings

**R42-1 [minor] §1 l.12–14: a leftover sentence repeats the l.12 rationale, re-introduces the specification as if unnamed, and the acronym is defined twice; the Chinese l.13 says something different.**
- Location: 01_introduction.tex l.12 ("…because the specification makes machine judgement unusually concrete…"), l.13 ("We study the question through one governance specification that makes it unusually concrete."), l.14 ("Proof of Love2 (PoL2) is an open, versioned governance text…"); l.15 again "which of PoL2's properties make the question concrete". zh/sections/01_introduction.tex l.13 "PoL2 规范使这一问题异常具体，因而是本文的研究对象。"
- Evidence: after l.12 has named and defined PoL2 and given the "unusually concrete" rationale, l.13 reads as the old pre-round-41 introduction of an unnamed case ("one governance specification"), l.14 defines "Proof of Love2 (PoL2)" a second time, and "concrete" occurs three times in four sentences. The ZH l.13 was rewritten ("is therefore the object of study") while the EN was not, so the two versions now differ in this sentence. This is the paper's first paragraph on the object of study, which a moderator reads.
- Fix: delete EN l.13 and start l.14 "\pol{} is an open, versioned governance text…" (no second expansion); delete ZH l.13 likewise and start "\pol{} 是一份开放的…". Optionally, in the abstract, "We ask whether they can serve as safeguards for PoL governance, that is, governance under Proof of Love2 (PoL2), an open text…" (drops the stray comma; +3 net characters after removing ", " → check ≤1920; currently 1917).

**R42-2 [minor] CHANGELOG 0.4.0 misstates the update flow and the adjudication.**
- Location: CHANGELOG.md 0.4.0, third bullet: "新增 57 项全文阅读来源（arXiv 31、Zenodo 26）…全部配对盲法第二编码（κ = 0.55）并由第三方裁定".
- Evidence: §3.3 l.67 and S5.4 l.76: 62 sources were read in full and 5 excluded at that stage; 57 (31 arXiv, 26 Zenodo) were retained and appraised. §3.4 (main.pdf text): disagreements "were resolved by a third AI pass that had read both rationales"; "第三方" (third party) suggests an independent, presumably human, adjudicator, which overstates the independence; the paper discloses that all coding was by author-directed AI agents.
- Fix: "补充检索全文阅读 62 项、排除 5 项，保留 57 项（arXiv 31、Zenodo 26）……全部配对盲法第二编码（κ = 0.55），分歧由第三次 AI 裁定（读过双方理由）".

**R42-3 [minor] paper/README.md still refers to appendices that no longer exist.**
- Location: paper/README.md, "写作约定": "附录 A 为中英逐字摘录与旧编号"; "规则见附录 E".
- Evidence: after the split, the concordance is Supplement S1 (Table S1) and the codebook Supplement S5; the same README's file table already says "原附录 A–E，编号 S1–S5". A reader of the published README looking for "Appendix A/E" in main.pdf finds none.
- Fix: "补充材料 S1（表 S1）为中英逐字摘录与旧编号"; "规则见补充材料 S5".

**R42-4 [nit] README "主要发现" 5 lists eight of the paper's nine lessons and drops "score events and behaviours, never persons".**
- Location: README.md, 主要发现 item 5; paper §7.1 l.97–107 (nine bullets), §8 l.10; CHANGELOG says "九条".
- Evidence: the omitted lesson is the one tied to PoL2's per-person quantification (§5.6, T5), which README item 1 names as a function Jev should not perform; "中性的选项标识" also omits "tested by renaming".
- Fix: add "评分对象是事件与行为而非个人（在公布按群体和语言的误差之前）"; optionally "并通过换名测试".

**R42-5 [nit] Two different "62"s eight lines apart in §3.**
- Location: 03_method.tex l.59 ("Zenodo queries about 330 records, of which 62 met the keyword and date criteria") and l.67 ("We read 62 sources in full" in the update search).
- Evidence: unrelated quantities with the same value in adjacent paragraphs invite conflation (and S5.4 l.74 has a third: the 11 Zenodo queries "returned 62 records dated on or after the release").
- Fix: none required; optionally "62 Zenodo records" at l.59 and "In the update search we read 62 sources in full" at l.67.

**R42-6 [nit] Review-round counts in published documents are stale.**
- Location: README.md tree "审稿与修订记录（40 轮）"; CHANGELOG 0.4.0 "审稿第 12–40 轮".
- Evidence: rounds 41 and 42 exist in paper/review/ and round 41 is in AUDIT.md.
- Fix: update to the final round at release, or drop the number ("多轮").

## Carried

R17-2, R17-3, R21-1, R21-2, R21-3, R37-1, R38-2, R40-1: not applied, carried (nits). R41-6 URL: author item (404 until merge; consider a tag- or commit-pinned URL).

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 3 | R42-1, R42-2, R42-3 |
| Nit | 3 new, plus 8 carried | R42-4, R42-5, R42-6; R17-2, R17-3, R21-1, R21-2, R21-3, R37-1, R38-2, R40-1 |

R41-1 to R41-6 verified as resolved in EN and ZH sources and PDFs; four PDFs current, no "??", no undefined references; metadata 1917 characters; rate_certainty --check passed.

New major or minor problems remain: yes
