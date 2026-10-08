# Text changes for the 8 October 2026 update search

Date: 2026-10-08. Protocol: `paper/review/UPDATE_SEARCH_2026-10-08.md`. Main-window counts, figures, tallies and `counts.tex` unchanged. Not edited: `B_evidence.tex`, `C_catalogue.tex`, `E_codebook.tex`, `counts.tex`, `counts_update.tex`, data files.

## Files and changes

- `main.tex`: `\input{counts_update}` after `\input{counts}`; `corpus_update` added to `\bibliography{}`; date 4 -> 8 October 2026.
- `background.bib`: added `dibonaventura2025hatevolution` (BibTeX from `hatevolution_assessment.md` §4). Background literature, not corpus.
- `make_metadata.py`: `counts()` now also reads `counts_update.tex` (the abstract uses `\nUCoded{}`); docstring updated. No "15 items" text existed anywhere (grep), so nothing else to renumber.
- `00_abstract.tex`: added "an update search to 8 October (\nUCoded{} more coded sources) reversed no answer". Trimmed to fit, hedges kept: "instead of text" -> ", not text"; "that intercepts hate language" -> "against hate language"; "its open counterparts from" -> "open counterparts in"; "under the author's direction" -> "directed by the author"; "the cost of LLM evaluators" -> "LLM evaluators' cost"; "accepting their low-risk verdicts" -> "accepting low-risk verdicts"; "generative evaluators" -> "LLM evaluators" (certainty sentence); "Read against ... the evidence sharpens" -> "Against ... it sharpens"; "transparency with closed models" -> "closed-model transparency"; "acceptance criteria" -> "pass criteria". Plain-text length 1,918 of 1,920.
- `01_introduction.tex` (Thesis): one sentence: the update reversed no answer, qualified one statement (decomposed chains) and raised the certainty of two findings.
- `03_method.tex`: `\label{sec:search}` on "Information sources, search and selection"; new paragraph "Update search": web-interface arXiv re-run (API rate-limited; `scripts/rerun_arxiv_search_web.py`), Zenodo API re-run, trackers unchanged; 57 read (31 arXiv, 26 Zenodo, no grey), 48 coded (27/21), 6 context, 2 non-empirical, 1 excluded (no evaluation); sets 30 / 5 / 13; the 1 Oct Zenodo counts-only limitation; 118 pairs S12/Q92/N14 reported separately; blind second coder on all pairs, 97 of 118, kappa 0.55 (0.36-0.70), lower than main; 21 disagreements, third pass 11 first / 10 second; `CODEBOOK_v3.md` lacked rule (iv) until 8 Oct, second coders applied the rule as stated in §3.
- `04_evidence.tex`:
  - G1 "Relation to prior work": Hatevolution candidate sentence 2.
  - G5 answer box: "more accurate" -> "can make them more accurate, though in two later studies decomposition did not raise accuracy (\cref{sec:update})". Codes line unchanged (main window).
  - "Across requirements": last sentence notes two ratings rise with the update.
  - New subsection 4.9 `sec:update` "Update search (2--8 October 2026)" with `tab:update` (main / update / in-window / main+in-window per requirement; update comparator splits; stronger-design row) and paragraphs G1, Emotion and Chinese text (T1), G2-G7. Cites all PoL2-central studies requested (arx03324, arx07953, arx08829, arx04985, arx09896, arx03935, arx03387, arx07730, arx07327, zen23075657, zen23225893, zen22935043, arx06625, zen23221456) with favourable and unfavourable results; arx10321 flagged as not independent of arx24052.
  - `tab:keyfindings`: two rows get update sources and a `$^{u}$` rating; caption explains. Table now floats after the update subsection (Table 3).
- `06_design.tex`: element 4 adds re-certification "on a schedule, and whenever a temporal re-validation fails (item 16)"; Trade-offs adds Hatevolution candidate sentence 1 (rho -0.31 to 0.19, all 90% intervals include zero; static benchmarks mean rho 0.36); `tab:checklist` adds item 16° "Temporal re-validation" with the assessment's pass criterion.
- `07_discussion.tex`: Certainty paragraph adds the two update-driven rating changes; Limitations replaces "Zenodo search was not re-run ... after 4 October not included" with the update-search caveats (separate, not pooled, kappa 0.55, 13 re-screened Zenodo records of uncertain status, nothing after 8 October); open problem "A PoL2 benchmark" adds Hatevolution candidate sentence 3.
- `08_conclusion.tex`: one sentence: the update reversed none of the conclusions.
- `09_statements.tex`: data statement lists the seven update data files.

## Answer boxes

- Reversed: none.
- Amended: G5 only. The box said writing intermediate facts into the state makes chains "more accurate" when those facts are right. arx03324 (criterion decomposition: 6 gains, 11 losses of 30) and arx08829 (decomposition 62.93 -> 57.31; appended judgements 61.61) did not find higher accuracy, while arx07327 and arx06425 did. Qualified to "can make them more accurate".
- Unchanged, stated in §4.9: G1 (arx03324 closer to the best LLMs than "often below the best", but same direction), G2, G3, G4, G6 (escalation evidence less consistent: arx09188, arx07177, arx02267 against arx09683), G7 (new privacy/dual-use negative, arx04985).

## Certainty ratings (rules of §3.5 applied with update studies added)

- "Fixed thresholds do not transfer; local fitting is needed": low -> moderate. Stronger-design independent studies in the same direction: arx29429, arx00346 (main) plus arx03387, zen23075657, zen22935043, arx02267 (update); arx29429 replicated by jkf87_2026replication.
- "Errors concentrate in sub-types hidden by aggregates": very low -> low. arx33401 (main) plus arx07953, arx03324, arx08675, arx10321 (update, all stronger); none preregistered or replicated, so not moderate.
- No rating falls. "Injection rarely selects the attacker's target" stays very low and is now contested by arx04985 (97-100% attack success). "Option names can override definitions" gains arx02586 and arx07953 (stronger) but no preregistered or replicated study, so stays low. Escalation finding stays low (main-window support unchanged; new evidence less consistent). Calibration finding stays low (directions differ, as in the main window).

## Build

`pdflatex` / `bibtex` / `pdflatex` x3: no errors, no undefined references or citations; one pre-existing BibTeX warning (naeini2015obtaining volume+number). 80 pages, up from 66. The new §4.9 adds about 2.5 pages; `B_evidence.tex` and `C_catalogue.tex` were regenerated by the other process during this session (10 KB to 18 KB and 16.5 KB to 25 KB), which probably accounts for most of the rest. Remaining overfull boxes are in appendix tables not edited here.
