# Round 21: combined review (fidelity, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: the two nits fixed after round 20, plus an independent whole-paper pass that concentrates on the areas rounds 12–20 looked at least:
- §2 background;
- §5 tensions and regulatory parallels;
- §6 reference design and tab:checklist;
- Appendix A concordance;
- §9 statements;
- bibliography (update keys, Hatevolution);
- metadata and bundle.

Items resolved in REVIEW.md, AUDIT.md or rounds 12–20 are not re-raised.

**Inputs**
- Paper:
  - sections/*.tex (04_evidence.tex 17:58:56);
  - main.pdf and main.log from 17:59:06: 84 pages, no `!` lines, no undefined or multiply defined references;
  - main.bbl and main.blg: one known warning, naeini2015obtaining volume+number, recorded in update_text_changes.md.
- arxiv_metadata.txt: abstract 1,909 ≤ 1,920.
- arxiv-submission.zip (17:59:07), extracted to a fresh directory:
  - 28 entries, with 00README.json (pdflatex) and main.bbl byte-identical to paper/main.bbl;
  - once comments are stripped and `sections/` and `figures/` paths are flattened, every section file and counts file matches the source.
- PoL2 sources (scratchpad/pol): zh_1/4/5/7.md and en_1/4/5/7.md.
- Full texts:
  - scratchpad/fulltext: 2609.29429, 27535, 24574, 33209, 34024, 33401, 36965, 37647v1;
  - scratchpad/hatevolution.txt.

## Status of round-20 and carried findings

| ID | Status | Note |
|---|---|---|
| R20-1 | FIXED | 04_evidence l.354 now reads "against 35.6--58.9\% recall for three fixed encoder conditions" (source abstract l.13–14). It is present in the bundle. |
| R20-2 | FIXED | Row 14 Sources cell (l.299) now reads "update: \cite{arx03387,arx02267}; update, opposing: \cite{zen22935043,zen23075657}", the same form as rows 5 and 11. It is present in the bundle. |
| R17-2 | NOT FIXED (nit) | Unchanged: data/certainty_evidence.csv was last changed at 17:52. No rating effect. |
| R17-3 | NOT FIXED (nit) | Unchanged. No rating effect. |

## Script check (task 2)

`python scripts/rate_certainty.py --check` gives CHECK PASSED (exit 0). The output is identical to rounds 19–20:

| Set | Moderate | Low | Very low | Contested |
|---|---|---|---|---|
| Now | 0 | 11 | 4 | 2, 5, 11, 14 |
| Main only | 0 | 10 | 5 | 2, 5, 14 |
| Given 4 Oct | 1 | 9 | 5 | |
| 4 Oct recomputed | 0 | 9 | 6 | |

The 4 Oct recomputed set differs from the given set on row 14 only.

## Fresh pass (task 3)

### Appendix A concordance
- Every \zh{} excerpt was split at "……" and checked by script against zh_1/4/5/7.md, after whitespace and quote normalisation. All 52 fragments are verbatim.
- English excerpts were checked against en_1/4/5/7.md in the same way. The script's four apparent misses are artefacts:
  - a source comma inside a closing quote, before an ellipsis (§1.4);
  - Markdown escapes `\-` and `\.` (§5.4);
  - list-item numbers dropped where items are joined (Art. 8, Art. 10).
- Two convention problems remain: R21-2 and R21-3.

### §2 background and §2.2
- l.37: 63× pooled at list prices and 12× under repricing match arx29429 l.594–595. 8× and 312–455× match arx27535 l.576–578.
- Interface, readout and "type-safe" paragraphs are consistent with §4.
- l.57, "the EU AI Act prohibits it in workplaces and education", is a compressed restatement. §5 l.55 gives the medical/safety exception, so it is not raised.

### §5 tensions
- T1: 0.383 against 0.371 matches arx24574 l.95 and l.678–679.
- T2: "54%" matches arx34024 l.395 (53.9%, 62/115). "7%" matches §4.4 and arx39496.
- T2: "complementary probabilities do not sum to one where the model is unsure" matches arx33209 l.31 and l.95 ("Jev's violations concentrate where its answer is uncertain").
- T3: 92% matches arx36965 l.29 and l.518.
- T4: "at most 5 of 130" matches arx33401 l.1257.

### §5 regulatory parallels
Each provision was checked against the regulation text:

| Provision | Paper's statement | Assessment |
|---|---|---|
| AI Act Art. 5(1)(f) | Emotion inference in workplace and education, with the medical/safety exception | Correct |
| AI Act Art. 5(1)(c) | Social scoring, giving both limbs (unrelated contexts; unjustified or disproportionate) | Correct |
| AI Act Art. 14 | Human oversight for high-risk systems | Correct |
| AI Act Art. 86 | Explanation right for Annex III high-risk systems with legal or similarly significant effects | Correct; the omitted point-2 exclusion and the "adverse impact" qualifier are acceptable in a paraphrase |
| GDPR Art. 22(1) and (3) | Safeguards limited to the contract and explicit-consent bases | Correct |
| DSA Art. 17 | Statement of reasons from hosting providers | Correct |
| DSA Art. 20 | Internal complaint handling by online platforms | Correct |

### §6 design and tab:checklist
- The seven enumerated elements match the figure caption numbering (3)–(7).
- Item mapping: B1–B2, C1, C3–C4, R1–R2 and T2–T3 make 9 items. With the 5 not adopted (B3, T1, T4, R3, C2), the total is the 14 items of arx32160 (l.643ff).
- Item 16:
  - its criterion refers to item 11 (languages) and item 2 (re-certification), both of which exist and fit;
  - §6 element 4 cites "item~16";
  - the basis honestly says "English only; no typed model tested".
- Pass criteria are coherent and declared provisional.
- The Hatevolution sentence (l.36) was checked against hatevolution.txt l.17, l.829–845 and Table 5:
  - 20 models and four static benchmarks: correct;
  - ρ from −0.3053 to 0.1909, so "−0.31 to 0.19": correct;
  - all 90% intervals include 0: correct;
  - static–static mean 0.36: correct.

### §4.3–4.4 spot-checks
| Study | Claim checked | Source location |
|---|---|---|
| arx36965 | 11.45 vs 3.78; 12.08 vs 5.57 | l.113, l.526 |
| arx37647 | 346,009 requests; pooled ECE 0.028 | Matches source |
| arx24574 | 0.063, lowest of 22; 0.066 vs 0.157 | l.97–98, l.22 |
| arx33209 | 480 pairs; 0.064; about five times repeat noise | l.21–27 |
| arx34024 | 17/162 = 10.5% vs 8.6%; 53.9% vs 73.9% | l.395–408 |

All correct. In total, 16 numeric claims across §§2, 4.3–4.4, 5 and 6 were checked, and none is wrong.

### Bibliography
- corpus_update.bib has 57 entries, generated. Every entry has title, author and year, every arx key has an eprint, and every zen key has a DOI.
- dibonaventura2025hatevolution is well-formed: four authors with escaped ñ, arXiv 2506.12148, DOI and URL. It renders correctly in main.bbl l.980–984.

### §9 statements
- Positionality, AI-assistance statement and acknowledgements are adequate.
- The data statement is incomplete (R21-1).

### Metadata and moderation
- Title, abstract (1,909) and comments (84 pages, 7 figures) agree with the PDF.
- cs.CY primary with cs.AI cross-list is appropriate.
- The "[Author Name]" placeholder is known and author-only.
- There is no moderation risk.

## Findings

**R21-1 [nit] The §9 data statement does not name every released file.**
- **Location:** 09_statements.tex l.21.
- **What is missing:**
  - data/search_rerun_2026-10-08_query_hits.csv, which is cited in §3 l.65 and App. E l.73 but not listed in §9;
  - data/search_rerun_2026-10-04.csv;
  - data/pol2_mapping.csv;
  - data/pol2_axes.json;
  - data/papers.json;
  - data/sources/arxiv_meta.csv.
- **Scripts not covered:** scripts/merge_coding.py, merge_update.py, build_catalog.py, check.py and fetch_papers.ps1 are covered by neither "the search scripts" nor "the figure scripts".
- **Why nit rather than minor:** the whole directory is released under CC0, so nothing is unavailable.
- **Fix:** add the six data files. Either add "and the merge, catalogue-build and check scripts", or say "all files in data/ and scripts/, including …".

**R21-2 [nit] Two English concordance cells break Appendix A's ellipsis convention.**
- **Location:** A_concordance.tex l.50 (Art. 8(1)–(2)) and l.54 (Art. 10 lead-in, 1, 4).
- **The convention:** A l.4 says "…" marks omitted text "including where separate list items are joined", and the Chinese cells follow it ("……讨论义务", "：……AI进行").
- **What is wrong:** the English cells join the items directly, with no \ldots:
  - "…at any time. Obligation to discuss…";
  - "…by NaturalDAO: AI conducts…".
- **Fix:** insert "\ldots\ " at both joins, as in the Art. 4 and Art. 7 rows.

**R21-3 [nit] Two PoL2 phrases quoted in §2.1 are absent from tab:concordance.**
- **Location:** 02b_pol2.tex l.19 ("feeling-nothing state", §4.3.2) and l.35 ("the wisdom of love and hate", the wisdom navigator, §5.4.1).
- **Why it matters:** Appendix A l.4 claims to quote "every \pol{} passage that this paper cites or paraphrases".
- **History:** this was raised in R2-cons-18. Its other items were fixed and these two were never closed, so the item is not resolved and is raised again.
- **Source text:** en_4.md l.65 and en_5.md l.107. The corresponding Chinese text is in zh_4 and zh_5.
- **Fix:** extend the §4.3.2 "state of absence" row and the §5.4.1 row with these excerpts in both languages. Alternatively, qualify the claim in A l.4.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 0 | |
| Nit | 3 new, plus 2 carried | R21-1, R21-2, R21-3; R17-2, R17-3 |

New major or minor problems remain: no
