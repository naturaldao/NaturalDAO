# Round 2: consistency lens (R2-cons)

Reviewer lens: internal consistency, definitions, counts, cross-references, LaTeX log, arXiv bundle; status of round-1 findings (`round1_consistency.md`).
Sources checked: `main.tex`, `counts.tex`, `sections/*.tex`, `main.pdf` (pdftotext -layout), `main.log`, `main.aux`, `main.bbl`, `figures/src/*.py` and rendered PNGs, `../data/*.csv` (tallies recomputed from `evidence_coding.csv`, rows with `in_tally = yes`), `arxiv_metadata.txt`, `arxiv/` and `arxiv-submission.zip`.
Line numbers refer to the source files as of 4 Oct 2026 23:06. Note: `sections/02_background.tex` was modified at 23:06, after `main.pdf`, `main.bbl` and the arXiv bundle were built at 23:03–23:04 (see R2-cons-1).

## Table of repeated quantities

| # | Quantity | Locations | Recomputed from data | Consistent? |
|---|----------|-----------|----------------------|-------------|
| 1 | 79 arXiv papers (\nArxiv) | counts.tex; method:67; fig_prisma (63 + 1 tracker + 15 new); fig_corpus legend (30 core + 24 related + 25 background) | papers.csv has 80 arXiv rows; 80 − arx22664 (context) = 79. Catalogue tiers 31/25/25 = 81 = 80 arXiv + alphaRAG | Y. But arx25498 (Model "--", no typed model) is still counted (R2-cons-12) |
| 2 | 27 Zenodo records (\nZenodo); 28 = 27 + 1 alphaXiv (\nOther) | counts.tex; method:68–70; fig_prisma; fig_corpus legend "Zenodo / alphaXiv (n=28)" | zenodo_preprints.csv 28 rows − zen22953637 (no typed model) = 27 | Y |
| 3 | 107 studies (\nPapers) = 79 + 27 + 1 | abstract; intro contrib. 2; method:71; arxiv_metadata | Y | Y |
| 4 | 7 grey sources (\nGrey) | abstract; intro; method:70–71; fig_prisma ("9 (2 commentary: context)"); fig_corpus legend | grey docs in tally = 7 (checkpoint, simmons, qin, jkf87, grazian, yurin, le2026sev); grey_literature.csv has 11 rows incl. 2 trackers + 2 commentaries | Y (count) |
| 5 | 85 coded documents (\nCoded) | method:71 | 85 distinct docs with in_tally = yes | Y |
| 6 | 161 pairs; S 17, Q 98, N 46 | counts.tex; §4.8:284; fig_framework (sum of bars) | 161; 17/98/46 | Y |
| 7 | Per-requirement tallies | answer boxes §4.1–4.7; fig_framework bars; fig_corpus(b) n | G1 3/19/5 (27); G2 1/0/9 (10); G3 2/12/10 (24); G4 3/29/13 (45); G5 2/3/3 (8); G6 1/23/4 (28); G7 5/12/2 (19) | Y (all three places) |
| 8 | Comparator results: G1 7 of 21 better/similar, 9 mixed, 5 worse; G4 9 of 18 better, 2 worse | answer boxes G1, G4 | G1: better 2 + similar 5 = 7, mixed 9, worse 5 (21); G4: better 9, mixed 6, worse 2, similar 1 (18) | Y |
| 9 | 76 comparisons: better 24, similar 17, mixed 27, worse 8 | §4.8:285; tab:certainty ("76 comparisons") | 24/17/27/8 = 76 | Y |
| 10 | 32 of 46 N codes without comparator | §4.8:286 | 32 | Y |
| 11 | Higher-quality subset 13/65/28 of 106 | §4.8:284 | 13/65/28, 106 | Y |
| 12 | Zenodo 19 of 44 pairs N vs arXiv 23 of 107 | discussion:39 | Zenodo 19/44, arXiv 23/107 | Y |
| 13 | κ = 0.72, 26 of 30, sample 30 | abstract; method:100–101; counts.tex; metadata | coder_agreement.csv: 30 compared, 26 agree, κ = 0.717 | Y |
| 14 | 28 PoL2 clauses (\nPolClauses) | abstract ("derive ... from 28 of its clauses"); intro contrib. 1 ("turn 28 clauses ... into seven requirements"); metadata | Appendix A: 28 distinct labels; Table 1 uses 16 | Count Y; condition N (R2-cons-10) |
| 15 | Time window: 15 Sep – 1 Oct, "seventeen days" | abstract; method:43; discussion:38; conclusion:70 | 17 days inclusive | Y (round-1 NEW-cons-14 fixed) |
| 16 | arXiv PRISMA: 955 / 606 / 517 / 89 = 63 + 1 + 25; 25 − 5 − 4 = 16; 16 − 1 = 15; 63 + 2 + 15 − 1 = 79 | method:64–67; plot_prisma.py | arithmetic | Y |
| 17 | Zenodo PRISMA: ~330 / ~268 / 62 (61 + 1) / 21 (6 + 5 + 9 + 1) / 41 / 13 / 28 / 1 / 27 | method:68–69; plot_prisma.py | arithmetic | Y (wording differs slightly, R2-cons-24) |
| 18 | Trackers: 2,073 records / 52 papers; 213 papers; 27 graded | method:57; discussion:38; plot_prisma | grey_literature.csv notes | Y |
| 19 | Median AUROC 0.886 over 31 of 44 benchmarks; $0.30 vs $18.96 on 19 | §4.1:22–23; tab:keyfindings; background:37 ("63×") | — | Y (round-1 NEW-cons-4 fixed; 63× no longer in abstract) |
| 20 | 130 implicit injections missed; ≤ 5 caught by evaluators | §4.1:36; §4.6:229; T4:38 | — | Y |
| 21 | JevOut 312/508 = 61.4%; others 64.9–73.2% | §4.2:66; plot_fragility | 312/508 = 61.4% | Y |
| 22 | Opinion attack 12.1% vs authority 10.1% | §4.2:67; tab:keyfindings; CSV | CSV rationale now "tied with the strongest injected command (10.1%)"; text says "impersonating an authority (10.1%), the strongest injected command" | Y (round-1 NEW-cons-5 fixed) |
| 23 | 0.8 gate: 12.6% of flips through; 38.0% pushed below | §4.6:234; CSV arx31142 G6; coder_agreement note | — | Y |
| 24 | "I don't know" 17/162 = 10.5% | §4.4:167 | 10.49% | Y |
| 25 | Peer evaluators 242/252 = 96.0% vs 50.3% | §4.6:227; T4:38; tab:keyfindings; tab:certainty; fig_escalation | 96.03% | Value Y; "upper bound" caveat missing in abstract, intro and conclusion (R2-cons-15) |
| 26 | JEV-as-a-Judge +0.93 at 41.4%; −0.74 on JudgeBench; 75.5% live | §4.6:222; D_corrections:129; plot_escalation | — | Y |
| 27 | Census 2,170 projects; 175 (8.1%) | background:15; §4.7:273 | 175/2170 = 8.06% | Y |
| 28 | Negation 0.064 / 0.293 / 0.013; 0.142 vs 0.018 | §4.4:161; fig_honesty(a) | plot_honesty.py has `by_confidence` but panel (a) plots only means | Values Y; figure reference still covers an unplotted number (R2-cons-22) |
| 29 | ECE 0.0231 → 0.0069 out of fold; 0.1235 → 0.0077 hold-out | §4.4:152–153; fig_honesty(c) caption; D_corrections:89 | — | Y (round-1 NEW-cons-18 fixed) |
| 30 | Seven design elements | §6:84–93; fig_architecture boxes 1–7; conclusion:70 | — | Y (round-1 NEW-cons-20 fixed) |
| 31 | 14 items of arx32160 merged into checklist items "1–4, 6, 9 and 13–14" | §6:108; tab:checklist ∘ marks | Unmarked (inherited) items: 1, 2, 3, 4, 6, 7, 9, 14 | N (R2-cons-3) |
| 32 | Five tensions T1–T5 | abstract; intro contrib. 3; §5; fig_framework; conclusion:75 | — | Names/order Y; links partly N (R2-cons-9) |
| 33 | Five review passes on v0.2; 174 findings | method:116; D_corrections:63 | review/round1_*.md = 5 files | Y (174 not verified) |
| 34 | 41 CC PDFs | 09_statements (now says "papers under Creative Commons licences", no number) | papers.csv pdf_in_repo = yes: 41 | Y |
| 35 | 64 pages, 7 figures, 4 tables | arxiv_metadata.txt; main.log ("64 pages") | 7 figures; 4 body tables (+7 appendix longtables) | Y, but stale once the PDF is rebuilt (R2-cons-1) |
| 36 | Abstract 1,881 characters (≤ 1,920) | arxiv_metadata.txt | recounted: 1,881; no LaTeX characters | Y |
| 37 | Clause commit 5791ae3 (30 Sep 2026, UTC); v0.1 snapshot 2e094d3 (27 Sep); renumbering in 7750ceb–526da3d | 02b:86–87; A:4–6; D:100 vs D:141 | — | N (R2-cons-14) |
| 38 | Cite keys: .bbl vs body | main.bbl 210 keys; sources cite 211 | `liang2023holistic` cited (02_background:64) but not in main.bbl, PDF or bundle | N (R2-cons-1) |

---

## Findings

### R2-cons-1 [major]
- Location: `sections/02_background.tex:64`; `main.pdf`, `main.bbl`, `arxiv/02_background.tex`, `arxiv/main.bbl`, `arxiv-submission.zip`.
- Problem: The source was edited after the PDF, the .bbl and the arXiv bundle were built. Line 64 now ends "...which is one reason holistic evaluation reports many scenarios and metrics rather than one score~\cite{liang2023holistic}". The PDF, `arxiv/02_background.tex` and both `main.bbl` files do not contain this sentence or the key. If the bundle is regenerated from the current sources without re-running BibTeX, arXiv will show "[?]" for this citation.
- Evidence: Timestamps: `02_background.tex` 23:06:06; `main.pdf` 23:04:29; `main.bbl` 23:03:28; zip 23:04:29. `liang2023holistic` is in `background.bib:507` but not in `main.bbl`. The other 15 flattened files match their sources once comment lines are stripped and paths are flattened. The 7 figure PDFs and `main.bbl` are byte-identical to the build copies. `00README.json` is correct (pdflatex, main.tex toplevel).
- Suggested fix: Rebuild in this order: pdflatex, bibtex, pdflatex ×2, `make_arxiv.py`, `make_metadata.py`. Then re-check the page count in the metadata.

### R2-cons-2 [major]
- Location: `sections/D_corrections.tex:94` (Table 9 row arx34862). Other locations: `data/evidence_coding.csv:20` (`arx34862,G1,S`); `sections/B_evidence.tex:15` (G1 & arx34862 & S & better); fig_framework G1 bar (S = 3); G1 answer box (S 3).
- Problem: Appendix D states that arx34862 was "Recoded as qualifying: wins on two of four benchmarks with lower precision". The released coding, Appendix B and every tally still code it S. Either the correction table is false or the tallies are stale. This is the round-1 NEW-cons-3 issue: the codebook example was moved to arx23959, but the S code itself remains.
- Evidence: The CSV rationale says that the generative evaluator "leads on 2 of 4 benchmarks and is more precise (91.9 vs 77.1)". By the codebook, mixed-across-tasks is Q.
- Suggested fix: Recode `arx34862,G1` to Q (comparator "mixed"). Regenerate counts.tex, B_evidence, fig_framework and fig_corpus. The figures then become G1 2/20/5, total S 16 / Q 99. Also update the G1 box ("better or similar in 6 of 21", "mixed in 10"), §4.8 (better 23, mixed 28) and the higher-quality subset (arx34862 is "lower", so 13/65/28 is unchanged). Alternatively, delete the Appendix D row.

### R2-cons-3 [minor]
- Location: `sections/06_design.tex:108` and `tab:checklist` (:115–133).
- Problem: The text says the 14 items of arx32160 are merged "into items 1–4, 6, 9 and 13–14". The table contradicts this in two places. Item 13 is marked ∘ (added beyond arx32160), and item 7 (red-teaming) is unmarked, i.e. inherited. The unmarked set is {1, 2, 3, 4, 6, 7, 9, 14}.
- Suggested fix: Either change the text to "items 1–4, 6, 7, 9 and 14", or mark item 7 ∘ and unmark item 13. Whichever is chosen, the set in the text must equal the set of unmarked rows.

### R2-cons-4 [minor]
- Location: `sections/02b_pol2.tex:6` and `sections/01_introduction.tex:168` (`\cref{sec:statements}`). Other location: `sections/09_statements.tex:1–2`.
- Problem: `sec:statements` is a label on an unnumbered `\section*`, so it inherits the counter of the previous section. It renders as "Section 8", which is the Conclusion.
- Evidence: `main.aux`: `\newlabel{sec:statements}{{8}{31}...{section*.80}}`. pdftotext shows "author contributes to PoL2 (Section 8)" and "the author of this paper (Section 8)".
- Suggested fix: Use `\hyperref[sec:statements]{the positionality statement}` or write "(see Positionality and competing interests)".

### R2-cons-5 [minor]
- Location: all `\cref{app:*}`: intro:153,163; method:6,55,91,96; §4:9; fig_framework caption; B_evidence:5; E_codebook:91; and others.
- Problem: Appendix cross-references render as "Section A/B/D/E", not "Appendix A". `app:queries` and `app:prisma` are placed after `\paragraph`, so they resolve to "Section E", the whole appendix. A reader told "the PRISMA checklist is in Section E" looks for a body section E, which does not exist. In addition, D_corrections:132 "Confirmed in Appendix E.10" refers to the *source paper's* appendix but reads as this paper's Appendix E.
- Evidence: pdftotext lines "checklist is in Section E", "18 queries to its API (Section E)", "Section A quotes every passage", "Section D lists the resulting changes".
- Suggested fix: Add `\crefname{appendix}{Appendix}{Appendices}` or `\crefalias{section}{appendix}` after `\appendix` (or load cleveref with the appendix patch). Write "the appendix E.10 of~\cite{arx24881}" in D_corrections.

### R2-cons-6 [minor]
- Location: `sections/04_evidence.tex:304–314` (tab:keyfindings "Code" and "vs. generative" columns).
- Problem: The Code and comparator columns are presented as if they came from the coding, but several rows contradict `evidence_coding.csv` for the cited sources:
  - "Separate 'is the evidence enough?' question detects missing information": S. arx01006 is coded Q on G4, and S on no requirement.
  - "Errors concentrate in sub-types": N, worse/mixed. arx33401 G1 is Q/mixed and arx00213 G1 is Q/none, so no source has N or "worse".
  - "Explicit none/I don't know rarely chosen": comparator "similar". arx34024 G4 is mixed and arx39496 G4 is worse.
  - "Thresholds set in advance miss error targets": N. arx00346 G6 and arx33843 G6 are Q, and only zen23041163 is N.
- Suggested fix: Rename the column "Direction" and define it in the caption as the direction of the finding, not the study code. Alternatively, make it agree with the CSV codes of the cited rows. Align the comparator column with the CSV ("worse/mixed" for the abstention row).

### R2-cons-7 [minor]
- Location: residual uses of *judge* in the generic LLM-as-a-judge or verifier sense, contradicting intro:142 ("We use *judge* in this sense only; ... we write *LLM evaluators*"):
  - `04_evidence.tex:38` "For one open judge (Laya) ... when the judge had to notice"
  - `D_corrections.tex:82` "The collapsing judge was the open Laya model"
  - fig_escalation (`plot_escalation.py:72,88,89,91`): "LLM judges repeating Jev's most confident errors", "Cascade minus best single judge (pp)", "6 of 9 panels below best single judge", "(c) Escalating among peer judges". The caption says "evaluator".
  - "independently built judge(s)" for a rule tree or second-stage verifier: `04_evidence.tex:217` (G6 box), `05_synthesis.tex:39,41`, tab:certainty row "Acceptance on agreement with an independently built judge". In the paper's own definition a judge is a component whose output alone decides an outcome. These verifiers are detectors, and §6 element 3 calls them "detectors".
- Suggested fix: Use "evaluator" (Laya, figure labels) and "independently built detector/rule" or "verifier" in the other places. Regenerate fig_escalation.

### R2-cons-8 [minor]
- Location: `sections/C_catalogue.tex` ("Axes" column; caption "by tier and axis"); `data/papers.csv`, `data/zenodo_preprints.csv` (`pol_axes`).
- Problem: The catalogue's axis column is taken from the old `pol_axes` field and disagrees with the released coding for 32 documents. Examples: alphaRAG catalogue G4 vs coded G1, G4. arx24574 G3, G4 vs G1, G3, G4, G6. arx29429 G1 vs G1, G4. zen22885291 G1, G2 vs G1, G4, G6 (G2 was dropped in coder agreement). zen22846597 G5 vs G1, G3, G4. Non-tallied items (arx32160, arx01231, zen22847531, ...) also show axes. The caption and header also keep "axis/Axes" where the paper now says "requirement".
- Suggested fix: Generate the column from `evidence_coding.csv` (in_tally = yes), and show "--" for non-tallied items. Rename it "Req." and the caption "by tier and requirement".

### R2-cons-9 [minor]
- Location: `figures/src/plot_framework.py:45–51` (TENSIONS) vs `sections/05_synthesis.tex`.
- Problem: The tension links do not follow "the evidence cited for each tension", as the script comment claims:
  - T3 (transparency) rests on Art. 4 and 5(4)–(5), which are the G5 clauses. It is linked to G3 and G7, not G5. Its cited evidence (arx26758 G3; arx33401 G1/G2/G6; arx00346; arx36965 G3/G4; arx38850 G4; arx28919 G6/G7) would give G3, G4 and G6.
  - T5 rests on §5.6, the G7 clause, and cites arx36399, which is coded N on G7. It is linked only to G2 and G3.
  - T4 is linked to G2, but its cited evidence (arx29769, arx33401, arx26550, arx02048) concerns G6 escalation. arx33401's 130 misses are coded under G1/G6.
  - T1's main empirical source arx24574 (empathy) is coded on G1 (N), G3 and G4. T1 is linked to G3 and G4 only.
- Suggested fix: Either derive the links mechanically (the union of the coded requirements of the studies cited in each T paragraph, plus the requirement whose clauses define the tension), or state in the Fig. 6 caption that the links show which requirements a tension mainly draws on. In either case add G5 to T3 and G7 to T5.

### R2-cons-10 [minor] (round-1 NEW-cons-13, not fixed)
- Location: `sections/00_abstract.tex:3` ("derive seven testable requirements from 28 of its clauses"); `sections/01_introduction.tex:153` ("We turn 28 clauses ... that require or constrain machine judgement into seven testable requirements"); arxiv_metadata.txt.
- Problem: Table 1 grounds G1–G7 in 16 clause labels. The other 12 in Appendix A are definitions (§1.1, §1.2, §1.4), context (§4.3, §4.3.3, §5.4) or procedural items (Art. 6(3), 8, 9(3), 11(2), 11(5)), and §4.3.3.2 is cited nowhere in the body. "28" is the number of passages quoted, not the number turned into requirements.
- Suggested fix: Abstract: "derive seven testable requirements from the clauses that require or constrain machine judgement (28 quoted in full)". Intro: "...16 clauses ... into seven requirements, and quote these and 12 related passages (28 in all) in both languages". Alternatively, cite the extra clauses in Table 1.

### R2-cons-11 [minor]
- Location: `sections/03_method.tex:90` (tier rule: background "not coded"); `data/evidence_coding.csv`.
- Problem: Three background-tier arXiv papers are coded and tallied: arx36154 (G4 N), arx00437 and arx40241. This contradicts the stated rule. The alphaXiv paper is also given a tier (Core), although the rule covers only "each arXiv study" (round-1 NEW-cons-40, not fixed).
- Suggested fix: Either re-tier these three as Related, or change the rule to "background: engineering or other domains; coded only where they report a measurement bearing on a requirement". Write "Each arXiv or alphaXiv study".

### R2-cons-12 [minor] (round-1 NEW-cons-12, partly fixed)
- Location: `sections/C_catalogue.tex:78` (arx25498, Model "--", Tier Background, Axes "--"); method:41,45 (inclusion requires a typed model; "Papers that mention typed models without measuring or building one were excluded").
- Problem: arx22664 was moved to context, but arx25498 also has Model "--" ("no typed model measured" by the catalogue legend) and is still counted in the 79. arx01231 (conceptual, Model "--") is counted under the non-empirical rule, but arx25498 is not described as non-empirical.
- Suggested fix: Either mark arx25498 * as context and recount (\nArxiv 78, \nPapers 106, PRISMA box, fig_corpus background n = 24, abstract, metadata), or correct its Model entry if it does build one.

### R2-cons-13 [minor]
- Location: method:106 ("Each study was appraised on four items"); `09_statements.tex:6` ("appraises the quality of every study"); abstract ("107 studies ... quality-appraised").
- Problem: `quality_appraisal.csv` has 96 rows (58 arXiv, 28 Zenodo, 9 grey, 1 alphaXiv). These are exactly the coded documents. The 22 uncoded background-tier arXiv papers in the 107 have no appraisal.
- Suggested fix: Say "each coded study (96 documents)", or appraise the background papers too.

### R2-cons-14 [minor]
- Location: `sections/D_corrections.tex:100` vs `:141`; `sections/02b_pol2.tex:86–87`.
- Problem: The v0.3 table says the renumbering was made "in commits 7750ceb–526da3d before 5791ae3", correcting v0.2's claim that "Commit 5791ae3 renumbered three chapters". The v0.1 table in the same appendix still says "Renumbered in commit 5791ae3 to §5.4.1, §4.3.x, §5.6".
- Suggested fix: Line 141: "Renumbered by commit 5791ae3 (commits 7750ceb–526da3d) to ...".

### R2-cons-15 [minor]
- Location: abstract:5 ("peer evaluators repeat their most confident errors"); intro:147; conclusion:71 ("peer evaluators repeat confident errors"). Other location: `D_corrections.tex:93` ("the caveat is now carried everywhere").
- Problem: The upper-bound/selection caveat for the 96% result appears in §4.6, T4, tab:keyfindings and tab:certainty, but not in the abstract, the thesis or the conclusion. These are exactly the places Appendix D says were fixed. The abstract and thesis also say a preregistered study accepted verdicts "safely", while tab:certainty records "disguised attacks leaked" (21 of 76 accepted look-alike windows were attacks, §4.2:74).
- Suggested fix: "...and peer evaluators repeat many of their most confident errors" (or "...on items selected as confident errors"). "...accepted their low-risk verdicts without loss of accuracy when an independently built rule agreed, though disguised attacks still passed". Alternatively, soften the Appendix D claim.

### R2-cons-16 [minor] (round-1 NEW-cons-19(c), not fixed)
- Location: `figures/src/plot_fragility.py:21,29,91` (panel b "Open-source Jev"; panel c "OpenJev (open)"); text and caption "Open-Jev" (`02_background.tex:24`, `04_evidence.tex:87`).
- Problem: The same DeBERTa model is labelled "OpenJev" in the figure and "Open-Jev" in the text. Panel (b)'s "Open-source Jev" is a different system (the Qwen3-1.7B interface of arx30243) whose name is nearly the same.
- Suggested fix: Panel (c) "Open-Jev (open)". Panel (b) "Qwen3-1.7B typed interface" (as in §4.2:66). Regenerate fig_fragility. The PDF is from 1 Oct.

### R2-cons-17 [minor] (round-1 NEW-cons-11, not fixed)
- Location: `sections/03_method.tex:68` ("13 of the remaining 41 were applications or tools without an evaluation and were excluded"); PRISMA item 16 in `E_codebook.tex:90` ("excluded studies with reasons in the data release").
- Problem: No file in `data/` lists the 21 + 13 + 1 excluded Zenodo records, or the 5 + 4 + 1 excluded arXiv records, with reasons. `search_rerun_2026-10-04.csv` may hold the arXiv screening, but the Data availability statement does not name it.
- Suggested fix: Add `data/excluded_records.csv` (source, id, stage, reason) and list it, together with `search_rerun_2026-10-04.csv`, in the Data and code availability statement.

### R2-cons-18 [minor]
- Location: unquoted attributions in the body, against Appendix A's claim that it "quotes every PoL2 passage that this paper cites or paraphrases":
  - `02b_pol2.tex:83`: §5.5 treats refusal as a "hate attack on humanity's core ethic". This is not in the §5.5 row.
  - `02b_pol2.tex:111`: the wisdom navigator allocates "the wisdom of love and hate" (§5.4.1). Only the safety-valve sentence is quoted.
  - `02b_pol2.tex:116`: NaturalDAO "presented in the form of a DAO" (Chapter 7). No row.
  - `02b_pol2.tex:95`: the state of absence "covering numbness, distraction and misunderstanding". This is elided in the §4.3.2 row.
  - Conversely, the §4.3.3.2 row and the "Thoroughly clear the toxins of hate language" row are never cited in the body.
- Suggested fix: Add the four excerpts to the existing rows (or a Chapter 7 preamble row). Drop the uncited rows, or reword A:4 as "quotes every passage cited, plus related items".

### R2-cons-19 [minor]
- Location: `sections/D_corrections.tex:138` (qin2026zhdecisionbench: first release tested "two Laya models and Qwen3.5-2B"); `data/grey_literature.csv` G-ZhBench note ("v0.1 only tests Laya multilingual 322M"); `04_evidence.tex:125` ("the open Laya multilingual model").
- Problem: The released data note and the correction table describe the benchmark's first release differently (round-1 NEW-cons-28, partly fixed).
- Suggested fix: Re-check the 26 Sep release and align the CSV note with Appendix D.

### R2-cons-20 [minor]
- Location: `main.log` lines 1655–1681 (A_concordance, v0.1 column).
- Problem: There are three overfull hboxes of 5.99pt (> 5pt) where "§5.3.3.1" and "§5.3.3.2" do not fit `p{0.06\linewidth}`. The remaining overfull boxes are ≤ 3.1pt. Seven "ignored error: Infinite glue shrinkage found in box being split" messages remain on pp. 49–61 (the longtables in Appendices A–D). There are no undefined references or citations in this build (but see R2-cons-1) and no font warnings. Round-1 NEW-cons-39's 5.8pt catalogue overflows are fixed.
- Suggested fix: Widen the v0.1 column to `p{0.075\linewidth}` and narrow the English column by the same amount. The glue messages are harmless but come from `\small` plus `\arraystretch` inside breakable longtables; they can be left as they are, or silenced by removing negative skips.

### R2-cons-21 [minor]
- Location: figure order vs first citation (`main.aux`).
- Problem: Fig. 6 (fig_framework) is first cited on p. 11 (§4 opening) and again on p. 21, but is printed on p. 25, after Figs. 3–5. Table 4 (tab:certainty) is cited on pp. 2 and 11 and printed on p. 29, after Tables 2 and 3. Numbering therefore does not follow the order of first citation, and readers who follow the §4 reference must jump 14 pages forward.
- Suggested fix: Move fig_framework to the end of §3 or the start of §4, where it is first used, and keep the §5 reference. Alternatively, drop the §4:9 forward reference.

### R2-cons-22 [nit] (round-1 NEW-cons-17, partly fixed)
- Location: `04_evidence.tex:161`.
- Problem: `\cref{fig:honesty}a` follows a sentence that includes 0.142/0.018, which panel (a) does not plot (`plot_honesty.py:19` defines `by_confidence` but it is unused).
- Suggested fix: Put the reference after "(0.013)", or plot the two values.

### R2-cons-23 [nit]
- Location: grey-literature marks.
- Problem: `willison2026jev` (grey, `04_evidence.tex:200`) has no \gmark. `typesafe_jaggedness` (vendor documentation, which method:50 says is context, not grey evidence) carries \gmark (`02_background.tex:32`).
- Suggested fix: Add \gmark to willison and remove it from typesafe_jaggedness, or define † as "grey or vendor source".

### R2-cons-24 [nit]
- Location: `03_method.tex:68` vs `plot_prisma.py` Zenodo boxes.
- Problem: The text lists the 21 removals as "duplicates, companion deposits and off-topic items", while the figure includes "not a typed model 1" in the 21. "Tool-only" appears both among the 21 ("off-topic/tool-only 9") and as the separate 13 "apps/tools without evaluation", so the two categories overlap.
- Suggested fix: Name the four categories in the text, and rename "off-topic/tool-only" to "off-topic".

### R2-cons-25 [nit]
- Location: acronyms and labels.
- Problem: GDPR (intro:155) and PRISMA (method:5) are never expanded. "CI" is used from §4.1:23 without expansion. fig_corpus(b) labels "G4 Honesty / abstention" and "G6 Oversight / escalation" differ from the Table 1 and Fig. 6 names "Honesty" and "Oversight". The catalogue column header is "Model" while Appendix B's is "System", with slightly different legends ("open-weight or other typed model" vs "open typed model"). `main.tex:47` says counts.tex is "generated by make_counts.py", but counts.tex says `scripts/merge_coding.py`. fig_architecture box 7 says "rule or EAP clause cited as ground", while §6 element 7 says "rule or clause". Element 3 also includes "separate calls for independent flags" and "self-hostable preferred (T3)", which box 3 omits.
- Suggested fix: Expand at first use ("General Data Protection Regulation (GDPR)", "Preferred Reporting Items for Systematic reviews and Meta-Analyses (PRISMA)", "confidence interval (CI)"). Align the figure labels and the generator comment.

### R2-cons-26 [nit] (round-1 NEW-cons-32 a/b, not fixed)
- Location: `data/grey_literature.csv` (ids `G-CheckPoint`, `G-Simmons`, ...) vs `evidence_coding.csv` (`checkpoint2026jev`, `simmons2026saidno`, ...). `papers.csv` tiers are 核心/相关/背景.
- Problem: The released files still use different ID schemes, and the tier labels are in Chinese while the paper uses English. The grey CSV also still lists the trackers and the two commentaries without a column marking which 7 are counted.
- Suggested fix: Add a `bibkey` column and an `in_corpus` flag to grey_literature.csv, and add an English `tier_en` column to papers.csv.

---

## Status of round-1 findings

| Round-1 | Status | Note |
|---|---|---|
| NEW-cons-1 | Fixed | All sources now read in full |
| NEW-cons-2 | Fixed | Tables 2–4 now before references (pp. 22, 28, 29) |
| NEW-cons-3 | **Not fixed** | Example changed, but arx34862 still S and Appendix D claims it was recoded (R2-cons-2) |
| NEW-cons-4 | Fixed | |
| NEW-cons-5 | Fixed | |
| NEW-cons-6 | Fixed for listed items | New unquoted items (R2-cons-18) |
| NEW-cons-7 | Fixed | Art. 4 now quoted with the explanation duty |
| NEW-cons-8 | Fixed | PRISMA restructured |
| NEW-cons-9 | Fixed | "Zenodo records" throughout; data file name `zenodo_preprints.csv` kept |
| NEW-cons-10 | Fixed | Trackers and vendor docs not counted; residual mark issue (R2-cons-23) |
| NEW-cons-11 | **Not fixed** | R2-cons-17 |
| NEW-cons-12 | Partly | arx22664 fixed; arx25498 still counted (R2-cons-12) |
| NEW-cons-13 | Partly | 28-clause condition (R2-cons-10) |
| NEW-cons-14 | Fixed | |
| NEW-cons-15 | Fixed | |
| NEW-cons-16 | Fixed | |
| NEW-cons-17 | Partly | R2-cons-22 |
| NEW-cons-18 | Fixed | |
| NEW-cons-19 | Partly | (a), (b) fixed; (c) names not fixed (R2-cons-16) |
| NEW-cons-20 | Fixed | |
| NEW-cons-21 | Fixed | |
| NEW-cons-22 | Partly | Renumbered and caption fixed; mapping sentence wrong (R2-cons-3) |
| NEW-cons-23 | Fixed for clauses | Tension links still not derived from §5 evidence (R2-cons-9) |
| NEW-cons-24 | Fixed | |
| NEW-cons-25 | Fixed | |
| NEW-cons-26 | Fixed | |
| NEW-cons-27 | Fixed | |
| NEW-cons-28 | Partly | R2-cons-19 |
| NEW-cons-29 | Mostly fixed | \gmark defined; R2-cons-23 |
| NEW-cons-30 | Mostly fixed | AUROC, ECE, F1, LLM, Cohen's κ, Kev defined; GDPR, PRISMA, CI remain (R2-cons-25) |
| NEW-cons-31 | Partly | Defined; residual uses (R2-cons-7) |
| NEW-cons-32 | Partly | (c) arx36154 now coded but background tier (R2-cons-11); (a)/(b) not fixed (R2-cons-26); (d) fixed via Appendix B |
| NEW-cons-33 | Fixed | |
| NEW-cons-34 | Fixed | |
| NEW-cons-35 | Fixed | Verbatim claim stated |
| NEW-cons-36 | Fixed | |
| NEW-cons-37 | Fixed | |
| NEW-cons-38 | Moot | arx34963 no longer cited in text |
| NEW-cons-39 | Partly | New 5.99pt overflows (R2-cons-20) |
| NEW-cons-40 | **Not fixed** | R2-cons-11 |

Leftover check (item 6 of the brief): no "survey" describing this paper (only "values survey", "survey methodology" and the v0.1 bib title), no `\team` or "team" referring to the author, no "Implications for PoL2", and the author block is "Shentao Yan" only. "NaturalDAO contributors" appears only as the corporate author of the repository bib entries, which is appropriate. "axis/Axes" survives only in the catalogue (R2-cons-8), the `\axis` macro name and figure-script docstrings.
