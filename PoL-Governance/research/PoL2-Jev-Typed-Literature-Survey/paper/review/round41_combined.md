# Round 41: combined review (consistency, cross-reference integrity, arXiv moderator, fidelity)

Date: 2026-10-09. Scope: the split of the appendices into a separate supplementary PDF (main.tex / supplement.tex, label exchange by build.py), the retitling around PoL governance, the supplement URL and arXiv ancillary file, and the Chinese split. Items resolved in REVIEW.md, AUDIT.md and rounds 12–40 are not re-raised; author-only items (author placeholder) are not findings.

**Inputs**
- main.pdf 9 Oct 00:23, supplement.pdf 00:24, arxiv-submission.zip 00:24, zh/main_zh.pdf and zh/supplement_zh.pdf 00:25.
- Logs: main.log "Output written on main.pdf (67 pages)", supplement.log "(40 pages)", main_zh.log "(64 pages)", supplement_zh.log "(41 pages)"; 0 `!` lines, 0 undefined or multiply-defined references or citations in all four.
- pdftotext of all four PDFs: 0 occurrences of "??". The Chinese PDFs yield no extractable CJK text (font without ToUnicode), so the Chinese check was done on the sources and logs.
- main_labels.tex (81 lines), supplement_labels.tex (39 lines): generated, anchors empty; supplement labels S1–S5, tables S1–S9, figure S1, sec:certainty-detail = S4.1.
- Zip: 24 flat files plus anc/supplement.pdf (md5 identical to supplement.pdf); supplement_labels.tex is shipped, so arXiv's compile resolves the cross-references; no supplement sources, no .bib.
- `python scripts\rate_certainty.py --check`: CHECK PASSED.
- URLs (curl, 9 Oct): …/blob/main/…/paper/supplement.pdf returns 404; …/tree/main/PoL-Governance/research/PoL2-Jev-Typed-Literature-Survey returns 200.
- arXiv help "Ancillary files" (info.arxiv.org/help/ancillary_files.html): files go in `anc/` at the package root; supported for TeX submissions only; examples are data, code, extra images; PDFs are not excluded (only PDFs with embedded JavaScript fail); TeX files must not go in anc; full text in anc is not indexed.

## Checks

**(1) Cross-references paper → supplement.** Every reference renders: "Supplement S1" (concordance, Table S1), S2 (evidence tables), S4 and S4.1 (corrections; certainty detail, Table S8), S5, S5.3 (queries), S5.4 (flow diagram, checklist). Table captions in the paper (Table 2 "quoted in Table S1", Table 3 "Supplement S4.1", "Table S8") render. Supplement S3 (catalogue) is referred to only in the statements list; acceptable. No "Appendix", "appendices", "at the end" or "below" pointing at former appendix content remains in the English or Chinese body (the only "appendix" hit is "appendix E.10 of the source" in Table S7, which refers to a cited study and is correct; the Chinese "原文附录 E.10" likewise).

**(2) Cross-references supplement → paper.** "Section 3", "Section 3.5", "Section 4.8", "Section 4.9", "Section 7", "Table 3", "Figure 2" all match main_labels.tex (sec:appraisal 3.5, sec:across 4.8, sec:update 4.9, tab:keyfindings 3, fig:framework 2). The supplement's opening note states that S-prefixed items are its own and that unprefixed numbers are the paper's. One ambiguity, R41-5.

**(3) Figures and tables moved.** The paper keeps six figures (corpus, framework, fragility, honesty, escalation, architecture = Figures 1–6) and six tables (paradigms, clauses, key findings, update, checklist, verdict = Tables 1–6). Moved: the PRISMA flow diagram (now Figure S1) and Tables S1–S9 (concordance, evidence, update evidence, catalogue, Zenodo, update catalogue, corrections, certainty changes, PRISMA checklist). Metadata "67 pages, 6 figures; supplementary material (40 pages)" matches. No residual "7 figures" in the body, metadata or make_arxiv.py output.

**(4) Self-containedness.** The verdict (Table 6), key findings and certainty (Table 3), requirements (Table 2), every number used in §4–§7 and the method rules (§3.5) remain in the paper; the supplement holds tabulations and audit trails. The one essential reporting item that now lives only in the supplement is the selection flow (R41-1).

**(5) Title and naming.** See R41-2, R41-3, R41-4.

**(6) arXiv ancillary file and URL.** A PDF in anc/ is permitted and the bundle layout is correct; the supplement is not indexed or rendered by arXiv, so the in-paper pointer matters. See R41-6.

## Findings

**R41-1 [minor] §3 no longer reports the selection flow; PRISMA item 16a now rests on the supplement only.**
- Location: 03_method.tex l.5, l.59 ("flow diagram and counts in Supplement S5.4"); Table S9 maps 16a to "Figure S1".
- Evidence: the paper gives only the end totals (79 arXiv, 27 Zenodo, 1 alphaXiv, 7 grey; 85 coded). Records identified (arXiv 955, 606 unique; Zenodo about 330), screened, dated in the window (89), full-text assessed and excluded with reasons appear only in Supplement S5.4 / Figure S1. For the update search §3 does report the flow (62 read in full, 5 excluded, 57 appraised), so the main search is reported less fully than the update. PRISMA 2020 allows the diagram in a supplement, but a referee reading only the paper cannot see how 955 records became 107.
- Fix: one sentence in §3 l.59, e.g. "The 4 October arXiv search returned 955 records (606 unique), of which 89 were dated on or after 15 September; with about 330 Zenodo records and the tracker items, N were read in full and M excluded at that stage (Figure S1)."

**R41-2 [minor] "PoL" is introduced in §1 without its relation to PoL2, and the abstract never introduces it.**
- Location: title ("in PoL Governance"), 01_introduction.tex l.12 ("Centred on the governance of PoL (Proof of Love)…"), l.14 and 02b l.5 ("Proof of Love2 (PoL2)"); abstract and arxiv_metadata.txt.
- Evidence: the reader meets "PoL" in the title, does not find it in the abstract (which names only "Proof-of-Love2 (PoL2)"), and in §1 gets "PoL (Proof of Love)" followed two sentences later by "Proof of Love2 (PoL2)" with no statement of how they relate (PoL as the framework/project, PoL2 as its current governance specification? a version?). §2.2 likewise defines only PoL2. A moderator or referee cannot tell whether "PoL governance" is broader than the PoL2 text the paper actually analyses.
- Fix: one clause in §1 l.12 or §2.2 l.5, e.g. "PoL (Proof of Love) is the framework; PoL2 is its current, versioned governance specification", and use "PoL" once in the abstract (e.g. "…taking as a case Proof-of-Love2 (PoL2), the governance specification of the Proof of Love (PoL) framework, …"; mind the 1920-character limit, currently 1919).

**R41-3 [minor] The new framing ("centred on the governance of PoL") conflicts with the case-selection language kept in §1 and §2.2; the title slightly overstates scope.**
- Location: 01_introduction.tex l.12–15 vs l.15 ("PoL2 is chosen not for uniqueness but because…"), l.13 ("We study the question through one governance specification that makes it unusually concrete"), 02b l.9 ("We use PoL2 as a case because…"), l.56 ("we do not evaluate PoL2's broader normative or political commitments"), 02b l.8 ("We do not assess these commitments").
- Evidence: if the paper is centred on PoL governance, PoL2 is its object, not a case "chosen" among governance texts for its concreteness; if PoL2 is a case for a general question, "centred on the governance of PoL" and the title misdescribe the paper. The title "Automated Safeguards in PoL Governance" also reads as an assessment of PoL governance generally, whereas the paper assesses only the clauses that require or constrain machine judgement (safety valve, anomaly detection, adjudication, per-person assessment) and explicitly does not evaluate PoL2's normative or political commitments. The subtitle ("Clause-Level Analysis") narrows it, so the overstatement is mild. Given the author's disclosed contributor status, a title foregrounding the project also invites a moderator's "promotional" reading.
- Fix: choose one framing. Either keep the PoL-centred title and change l.15 / 02b l.9 to say why PoL2 is the right text for this question (it is PoL's governance specification; it also makes the general question concrete), or revert §1 l.12 to the general question with PoL2 as the case. Optionally "…Safeguards for PoL Governance Clauses?" or add to §1 l.12 "in the clauses of that governance that require machine judgement".

**R41-4 [minor] "Proof-of-Love2" vs "Proof of Love2", and the Chinese gloss of "PoL".**
- Location: hyphenated in the title, 00_abstract l.3, 02b section heading, preamble pdftitle, supplement title, arxiv_metadata.txt; unhyphenated in 01 l.14 and 02b l.5 ("Proof of Love2 (PoL2)") and §1 l.12 ("Proof of Love"). Chinese: zh/sections/00_abstract.tex l.3 and 01_introduction.tex l.12 "PoL（爱2证明）", while 02b defines 爱2证明 as PoL2 and the English says "PoL (Proof of Love)".
- Evidence: the Chinese gloss equates PoL with "Proof of Love 2", i.e. PoL2, contradicting the English and the zh §2.2 definition; the English uses two spellings of the specification's name in the title, abstract and the defining sentence.
- Fix: one spelling throughout (the specification's own English translation decides; "Proof of Love2" is used in the defining sentences); in Chinese "PoL（爱的证明）" or the term the PoL text itself uses for PoL, consistent with the English gloss.

**R41-5 [nit] "Figure 2 and Tables S2 and 3" in Table S9 (item 13c).**
- Location: E_codebook.tex, PRISMA checklist row 13c.
- Evidence: in a supplement where tables are S-prefixed, "Tables S2 and 3" reads as S2 and S3 (Table S3 is the update evidence table, also plausible), though Table 3 of the paper is meant.
- Fix: "Figure 2, Table S2 and Table 3 of the paper".

**R41-6 [minor] The title-page supplement URL is a dead link until the branch is merged, and the title page does not mention the arXiv ancillary copy.**
- Location: main.tex \date (title page), 09_statements.tex l.21, zh/main_zh.tex l.15 (…/paper/zh/supplement_zh.pdf).
- Evidence: curl returns 404 for …/blob/main/…/paper/supplement.pdf on 9 Oct (the repository directory itself returns 200). arXiv does not render or index anc/ files, so a reader of the arXiv PDF depends on the pointer; the title page gives only the GitHub URL, while the statements section also names the ancillary file. A URL that may change (branch path) and is unreachable at submission time is a moderator's and referee's first click. The arXiv-side copy is correct (anc/supplement.pdf, md5-identical to supplement.pdf, PDF permitted in anc/, no JavaScript).
- Fix: merge before submission and re-check the URL (author item); add "and as an ancillary file of the arXiv record (anc/supplement.pdf)" to the title-page note; consider a tagged or commit-pinned URL (…/blob/<tag>/…) so later edits do not silently change the cited supplement.

## Carried

R17-2, R17-3, R21-1, R21-2, R21-3, R37-1, R38-2, R40-1: not applied, carried (nits).

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 5 | R41-1, R41-2, R41-3, R41-4, R41-6 |
| Nit | 1 new, plus 8 carried | R41-5; R17-2, R17-3, R21-1, R21-2, R21-3, R37-1, R38-2, R40-1 |

Cross-references in all four PDFs: no "??", no undefined references, no residual appendix wording; figure/table counts and metadata consistent; rate_certainty --check passed.

New major or minor problems remain: yes
