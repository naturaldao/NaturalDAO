# Round 29: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R28-1; fresh whole-paper pass prioritising what rounds 22–28 examined least: the "What transfers" lessons of §7.1 (each tied to a finding and a design element), T1–T5 (§5) against tab:verdict and §2.3, tab:checklist against the verdict's "What would be needed" column, Appendix D.1 against tab:keyfindings, the data statement against data/ and scripts/, the bibliography and the metadata; spot-check of numbers in §7.1 against the full texts. Items resolved in REVIEW.md, AUDIT.md and rounds 12–28 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/01_introduction.tex (23:18:02); main.pdf, arxiv_metadata.txt, arxiv-submission.zip (23:18:12).
- main.log: "Output written on main.pdf (95 pages, 2035455 bytes)", no `!` lines, no undefined references; overfull set unchanged.
- main.blg: one warning (naeini2015obtaining volume+number), pre-existing. No duplicate keys across pol2, corpus, corpus_update, grey, background.bib.
- arxiv-submission.zip extracted to scratchpad/r29z: all sections equal sections/*.tex up to CRLF and the expected make_arxiv.py rewrites (figure paths, `\input{02b_pol2}`, generator header comments); 01 l.15 carries `\cite{cac2023genai}`.
- `python scripts/rate_certainty.py --check` (repository root): CHECK PASSED (changed vs given 4 Oct: 2, 3, 5, 11, 14); `--verbose`: now contested 2, 5, 11, 14; main only contested 2, 5, 14.
- Full texts (scratchpad/fulltext, scratchpad/update): arx2610.03324, arx2610.07953, arx2610.09937, arx2610.08829.

## Task 1: re-check of round 28

| Item | Status | Evidence |
|---|---|---|
| R28-1 uncited first mention of the Interim Measures | FIXED | 01 l.15 "China's 2023 Interim Measures on generative AI~\cite{cac2023genai} also join …"; same in the zip. Entry background.bib l.794 well formed (title in Chinese with translation, Decree No. 15, issued 10 July 2023, effective 15 August 2023, CAC URL). |

## Task 2: fresh pass

**"What transfers" (07 l.96–108).** Nine lessons checked against tab:keyfindings, §6 elements and tab:checklist. Three-valued + sufficiency (element 3, T2, checklist 5 implicitly), neutral identifiers (element 3, item 4), records (element 7), local calibration with re-validation (element 4, items 2, 3, 11, 16), human end-point and audit (elements 5–6, T4(b)), events not persons (T5, \clause{4.3.1}), construct benchmark: correctly tied. Two are not: the agreement-gating lesson states a result the finding does not contain (R29-1), and the label-withholding lesson points to a design element that withholds only probabilities (R29-2).

**T1–T5 vs tab:verdict and §2.3.** T2 ↔ safety-valve and truncation rows and lesson 1; T3 ↔ 07 l.94 and element 3 ("self-hostable preferred"); T4 options (a)/(b) ↔ adjudication row NS and element 5 (design implements (b) and goes further, confirmation before any final block, as 05 says); T5 ↔ per-person row (NS on steering, NT on group error, precautionary) and its "What would be needed" (consent, access, appeal, error by group and language) matches T5's second option. §2.3 l.105, 107, 116 route the vendor-dependence, construct and institutional points to T3, T2, T4/T5 consistently. No break.

**Checklist ↔ "What would be needed".** Safety valve: thresholds certified and re-certified (items 2, 16), red-team per attack type below a target set in advance (item 7, same wording), renaming test (item 4). Truncation: sub-type recall floors (item 8). Ethical verification: default position without persona, contested items routed (item 13). Per-person: error by group and language (items 11, 12). Anomaly: independent second check (element 3, item 10). Consistent.

**Appendix D.1 ↔ tab:keyfindings.** Ratings and contested flags agree with the script and with tab:certchanges; source lists in D.1 are supersets of the table's "principal" sources (e.g. arx26532, zen22952571 named only in D.1), as the caption allows. One counting sentence undercounts (R29-4).

**Data statement (§9) ↔ files.** Every `\nolinkurl` path in the paper exists in data/ or scripts/; figure scripts exist in paper/figures/src (plot_*.py); review/audit logs and bib_verification_log.tsv exist. Unlisted files (papers.json, pol2_axes.json, pol2_mapping.csv, search_rerun_2026-10-04.csv, data/sources/arxiv_meta.csv) are covered by "the catalogue … the search scripts" only loosely, but the statement does not claim to be exhaustive; not raised.

**Bibliography and metadata.** New entries (cac2023genai, dibonaventura2025hatevolution) well formed; no duplicate keys. Metadata abstract = 00_abstract.tex with macros expanded (1916 characters), 95 pages agree with log; "[Author Name]" is the known author-only item.

**Spot-check of §7.1 numbers.**

| Number (07) | Source | Result |
|---|---|---|
| three-class macro-F1 \jev{} 0.532, frontier 0.604, TF-IDF 0.639 (l.36) | arx2610.03324 l.612, table l.1748 | Correct |
| 1.6 macro-F1 points at 97% lower cost (l.30, l.87) | arx2610.03324 l.71, contribution (iv) and §5: "on HateCheck, Jev scored 1.6 points below Sol at 97% lower cost" | Number correct, attribution wrong (R29-3) |
| 29.4% exact policy selection (l.36) | arx2610.07953 tables (29.4) | Correct |
| 57–94% of fault-free windows flagged (l.48) | arx2610.09937 l.1254 "flagged 57–94% of fault-free windows" | Correct |
| Chinese emotion macro-F1 \jev{} 21.06, generative 19.82–23.31 (l.42) | arx2610.08829 l.627, 682, 775 | Correct |
| 21 of 76 windows accepted as benign were attacks (l.48) | 04 l.75, keyfindings row | Consistent within the paper (full text not in scratchpad) |

## Findings

**R29-1 [minor] Agreement-gating lesson claims a result the finding does not contain.**
- **Location:** 07_discussion.tex l.103 ("Peer models repeated confident errors (low), an independently built rule did not (very low)").
- **Problem:** The very-low finding (tab:keyfindings; 04 l.212, l.297) is that accepting \jev{}'s benign verdict on agreement with an independently built rule lost no macro-F1, while fewer disguised attacks were flagged; the study did not measure repetition of confident errors, and tab:verdict (07 l.48) reports that 21 of 76 windows the gate accepted as benign were attacks, i.e. the rule did share errors there. The lesson's contrast overstates the evidence for independence.
- **Fix:** e.g. "Peer models repeated confident errors (low); accepting a verdict only when an independently built rule agreed lost no macro-F1, though disguised attacks still passed (very low), so independence must be built, not assumed, and its miss rate measured (element~3; checklist item~10)."

**R29-2 [minor] Label-withholding lesson points to a design element that withholds only probabilities.**
- **Location:** 07_discussion.tex l.105 ("Keep labels and probabilities from untrusted callers … (elements 3 and 4)") and l.93 ("argues against exposing the valve's labels, as well as its probabilities, to untrusted callers (\cref{sec:design}, element~4)"); 06_design.tex element 4 ("Raw probabilities are not returned to untrusted callers … although attacks also succeed with labels alone") and element 7 (public, delayed record).
- **Problem:** No element of §6 restricts labels; element 4 only notes that labels alone suffice for attacks, and T3 (05) and element 7 frame the conflict as one about probabilities. A reader following the cross-reference finds the recommendation absent from the design.
- **Fix:** either add to element 4 a clause such as "labels are returned to untrusted callers only where the caller needs them, rate-limited and logged", or reword l.93/l.105 to "keep probabilities from untrusted callers and limit label queries" and point to element 4's caveat.

**R29-3 [minor] The 1.6-point result is attributed to four standard hate-speech sets; the source reports it on HateCheck.**
- **Location:** 07_discussion.tex l.30 ("on four English hate-speech sets is within 1.6 macro-F1 points of a frontier LLM at 97\% lower cost") and l.87 ("on standard English hate-speech data it came within 1.6 macro-F1 points").
- **Evidence:** arx2610.03324 contribution (iv) and results: "on HateCheck, Jev scored 1.6 points below Sol at 97% lower cost"; HateCheck is the evaluation-only diagnostic set of functional test cases; on the four datasets commercial LLMs significantly outperformed all decision models on one by 4.1–5.9 points, and \jev{} was below the best generative evaluator on three of four (D.1). 04 l.400 states it correctly ("On HateCheck, …").
- **Fix:** l.30 "on the HateCheck diagnostic set is within 1.6 macro-F1 points … and was significantly outperformed on only one of four English hate-speech sets"; l.87 "on the HateCheck diagnostic set it came within 1.6 …".

**R29-4 [nit] D.1 "Effect of the update studies" undercounts the added opposing studies.**
- **Location:** D_corrections.tex, paragraph "Effect of the update studies" ("add an opposing study to one that the main window already contests").
- **Problem:** The update adds an opposing study to the injection finding (arx04985) and two to "thresholds set in advance" (zen22935043, zen23075657; tab:keyfindings "update, opposing"), which the main window also contests. The sentence reads as if only one finding gained opposition.
- **Fix:** "… and add opposing studies to the two findings that the main window already contests (one and two respectively)".

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 3 | R29-1, R29-2, R29-3 |
| Nit | 1 new, plus 5 carried | R29-4; R17-2, R17-3, R21-1, R21-2, R21-3 |

R28-1: FIXED.

New major or minor problems remain: yes
