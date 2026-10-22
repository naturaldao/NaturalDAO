# Round 22: combined review (balance/positionality, verdict fidelity, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: the two additions since round 21 (A: new §2.2 `sec:paradigms` / `tab:paradigms` and its §1/§7 insertions; B: new §7.1 `sec:verdict` / `tab:verdict`, rewritten §8, abstract and §1 thesis), plus layout, metadata and bundle. Items resolved in rounds 12–21 are not re-raised; R17-2, R17-3 and R21-1..3 are carried unchanged.

**Inputs**
- Paper: sections/*.tex as of 22:29 (02b_pol2.tex was edited at 22:29:20, after the 22:27 bundle; see R22-2). main.pdf and main.log from 22:29:31: 92 pages, no `!` lines, no undefined or multiply defined references; 21 overfull boxes, of which four are new and large (R22-1). Known warnings only otherwise (tab:keyfindings float 29.9pt too large; "Infinite glue shrinkage" ignored errors from longtables).
- arxiv_metadata.txt: abstract 1,916 ≤ 1,920; comments "92 pages, 7 figures" agree with the PDF.
- arxiv-submission.zip (22:27:17), extracted and compiled in a clean scratchpad directory: 92 pages, 0 errors; 00_abstract, 01, 07, 08 byte-identical to the source after comment stripping; 02b_pol2.tex differs from the source (R22-2).
- Coding: data/evidence_coding.csv, data/evidence_coding_update_2026-10-08.csv, data/certainty_evidence.csv (962 rows); every study cited in tab:verdict and in "The verdict" / "What transfers" was looked up.
- Full texts: scratchpad/fulltext/2609.29429, 2609.33401; scratchpad/update/*.
- PoL2: sections/A_concordance.tex, scratchpad/pol/en_5.md, en_7.md, zh_7.md (Art. 2, 4–11; §5.4.1, §5.5, §5.6).
- External sources fetched: Santa Clara Principles 2.0 (santaclaraprinciples.org); CAC Interim Measures (cac.gov.cn, Chinese text of Art. 2, 4, 14, 17); OpenAI Model Spec 2025-02-12 page (CC0 statement, changelog link) and the model-spec.openai.com redirect to 2026-08-18.html; Crossref records for dong2025safeguarding (AI Review 58(12):382, 17 Oct 2025) and makridis2025polycentric (Rev. Austrian Econ., online 22 Oct 2025); arXiv 2406.07814 for huang2024collective (FAccT '24, pp. 1395–1417, DOI as given). DSA, AI Act, GDPR and Klonick checked from the instruments' texts as known.

## Task 1: balance and positionality of §2.2

**Overall reading.** §2.2 reads as comparative policy analysis, not advocacy. Each of the five "distinctive properties" is paired with a cost that is specific and, for (i), (iii), (iv) and (v), damaging to PoL2 (no appeal route, originator control, privacy conflict, conflict with AI Act Art. 14 / GDPR Art. 22 / Art. 5(1)(c)). The scope sentence of §1 ("we do not evaluate PoL2's broader normative or political commitments") is respected: (v) describes the legal tension and refers it to T4/T5 rather than judging the aims. The one sentence that tips toward advocacy is in §1, not §2.2 (R22-3).

**tab:paradigms, cell by cell.**

| Row | Checked against | Assessment |
|---|---|---|
| (a) Risk-based | AI Act Art. 11, 12, 13, 14, 86; GDPR Art. 22; CAC Art. 2, 4, 14, 17 | Correct. CAC Art. 14(1) "停止生成、停止传输、消除 … 并向有关主管部门报告"; Art. 14(2) "警示、限制功能、暂停或者终止" (the cell's "warn or suspend" is a fair compression); Art. 17 security assessment and algorithm filing; Art. 2 services to the public; Art. 4 lawfulness and non-discrimination. GDPR is cited inline though not in the row's source list (nit, not raised). |
| (b) Platform | DSA Art. 14, 15, 16, 17(3)(c), 20(6), 24(5); Santa Clara 2.0; Klonick | Correct. Santa Clara 2.0 wording verified: "sufficiently high confidence in the quality and accuracy of those processes"; appeal "by a person or panel of persons who were not involved in the initial decision"; numbers "in an openly licensed, machine-readable format". DSA Art. 20(6) "not … solely on the basis of automated means"; Art. 24(5) database. Board decisions binding on the case: correct. |
| (c) Training-time | Bai 2022; Huang 2024; Model Spec; Guan 2024 | Correct. Model Spec 2025-02-12 "dedicated to the public domain" (CC0 1.0) with a changelog link; latest version 2026-08-18 confirmed by redirect. "no per-output record" is a fair statement of what the texts specify. |
| (d) Guardrails | Llama Guard; Markov 2023; NeMo; Sharma 2025; Dong 2025 | Correct as a statement of the texts; "no duty to give reasons or to keep records" is accurate (these are vendor papers, not duties). |
| (e) DAO / polycentric | Buterin; Hassan 2021; Santana 2022; Ostrom 1990; Makridis 2025 | Correct. "monitoring and graduated sanctions by members" are Ostrom's design principles 4–5. |
| (f) PoL2 | §5.4, §5.4.1, §5.5, §5.6, §1.5, §4.3.2, §4.3.3.1; Art. 2(1), 4, 5(5), 9(2), 9(3), 9(7), 10, 11(2), 11(5) | All clause references verified against en_5/en_7 and the concordance. Art. 11(2) "universal questioning period", 11(5) "permanently archived": correct. "thresholds and appeal unspecified": correct, the text says nothing on either. |

No cell misdescribes a paradigm. Superlatives and scope words are examined in R22-3, R22-5, R22-7, R22-8, R22-9.

**"Most specification-like for an inference-time safeguard."** Defensible as hedged ("in the limited sense that it names the intercept, the construct, the record and the decision-maker in clauses that can be cited"), with one correction: the decision-maker is named only for welfare decisions (NaturalDAO, Art. 2, 10), not for the safety valve, as (i) itself says (R22-5). Paradigm (d) also names the intercept and the construct precisely; what PoL2 adds is the record and the decision-maker, and the sentence should say so.

**Costs.** One cost is understated: (i) says PoL2 "avoids the … vendor dependence of (c)", but a valve implemented on hosted Jev reintroduces vendor dependence (T3; G7 box "deployment depends on one closed vendor"). This is covered later in the paper, so it is a nit only, folded into R22-5.

## Task 2: verdict fidelity

**tab:verdict numbers.** Every number was traced to a coding row or full text:

| Row | Numbers | Source | Result |
|---|---|---|---|
| 1 Safety valve | 0.886; $0.30 vs $18.96; 1.6 F1, 97% cost; F1 0.158 vs 0.947; 97–100%; 12.1%; 32.5–50.5% | arx29429 (fulltext l.593); arx03324 G7; jkf87; arx04985 G2 (100/100/97.2, 100/100/97.0); arx31142; arx26758, arx00346 | All correct |
| 2 Truncation | 0.532/0.604/0.639; 29.4%; 130 of 167 at ≥0.95 | arx03324 G1; arx07953 G1; arx33401 G2 and fulltext l.772, l.1253 | Correct |
| 3 Correction support | 21.06; 19.82–23.31 | arx08829 G1 | Correct |
| 4 Anomaly | 9.8 vs 22.8; 57–94%; no better than flagging every window; recall 0.34; 21 of 76 | arx00376; arx09937 G1; arx02048 G2 | Correct |
| 5 Ethical verification | 87% / 62%; rewording; 0.339; 0.88 on 55/45 | arx36399; zen23023694; zen23032384; zen23179064 G7 | Correct |
| 6 Adjudication | 96.0%; ≤5 of 130; 10.5%; 7–54%; 32.8%; 8 of 14; contested by arx33689 | arx29769 G6 (242/252); arx33401 G6; arx34024; arx39496; arx37470 G5; arx24574 G6 (cleared 6 of 14) | Correct |
| 7 Per-person | 51%; low-resource degradation; 12.1% | simmons (51.12%); arx37647 G3; arx31142 | Correct |
| 8 Assessment dimension | 0.93 / 0.96 at 80/90%; corrected statewide counts after per-factor recalibration | §4 G7 text (arx27535); arx00213, arx10321 G7 | Correct |

**Certainty cells.** Each matches tab:keyfindings: ranking low; thresholds low^c; sub-types low; steering low (arx04985 is counted under finding 4 in certainty_evidence.csv l.240, so citing its 97–100% under "steering (low)" is consistent); option names low; culture very low; calibration low; "I don't know" low; agreement gating very low; peer errors low; thresholds in advance low^c; "not rated" used only for non-key single-study results. "none is moderate" and "four are contested" agree with the script output of rounds 19–21.

**"The verdict" and "What transfers".** Every sentence traced: attribute leakage, harmfulness oracle and 92%-from-200-labels surrogate (arx04985 G7); most severe name inversion in an open model (arx26758, Laya 76.9%); deferral in-distribution (arx00381, zen22885291); sufficiency question AUROC 0.95 vs 0.85 (arx01006 G6, very low); digit identifiers near the floor (arx00346 G3); probability feedback (arx30243); planted note (zen23038928); Hatevolution (round 21). "Typed models were not generally worse (low, by judgement)" matches the tab:keyfindings row. The verdict for the "decides" functions is not stronger than the boxes: G2 "Yes", G3 "Not by default", G4 "Partly", G6 "It depends", and the §7.2 "What would change the conclusion" conditions are referenced as the test. The detector verdict is not weaker than the boxes: G1 "Yes as a ranking", G6 agreement-gating positives are carried with their conditions. Two verdict cells are labelled more strongly than the table's own definition allows (R22-6).

**Consistency chain.** Abstract ↔ §1 l.36 ↔ boxes ↔ §7.1 ↔ §8 agree on: not suitable for any function that decides (adjudication, ethical verification, per-person quantification, final block); detector only inside §6 for safety valve, truncation, anomaly detection; public-decision dimension as audited aggregate; extrapolation from English binary benchmarks; low/very low, four contested; update reversed nothing. The abstract says "Jev" where the body says "hosted Jev"; acceptable in 1,916 characters.

## Task 3: layout, metadata, bundle, bibliography

- tab:verdict (pp. 39–40): legible at \scriptsize, no overfull boxes, continuation header present.
- tab:paradigms: see R22-1 and R22-2. The version in the bundle (table[t] + tabularx, \footnotesize) fits the text width with six overfull boxes ≤ 13.4pt and sits on p. 7 as a full-page float; the version now in the source (longtable, \scriptsize) overflows the text width by 65pt on pp. 7–8.
- New bib entries: all eight well-formed and verified (see Inputs). cac2023genai: the Chinese title renders correctly on p. 49 inside \zh{}. Bibtex lower-cases the bracketed English gloss ("[interim measures …]") and "OpenAI model spec", in line with the file's existing style for other instruments; not raised.
- Metadata: title, abstract length, page count, categories unchanged and correct. No moderation risk: §2.2 and §7.1 are analytical, cite primary texts, and carry the positionality statement.

## Findings

**R22-1 [major] tab:paradigms overflows the text width by 65pt on every row.**
- **Location:** sections/02b_pol2.tex l.64–66 (current longtable); main.log l.1443–1459, "Overfull \hbox (65.20573pt too wide) in alignment at lines 66--71 / 71--75 / 75--77 / 77--89"; visible on pp. 7–8 of main.pdf, where the last column runs about 23 mm into the right margin.
- **Cause:** the eight fixed p-widths sum to 0.96\linewidth and the 14 inter-column \tabcolsep gaps (default 6pt) add 84pt.
- **Fix:** either (a) restore the tabularx version that is in the bundle (it fits), or (b) keep the longtable and set `\setlength{\tabcolsep}{3pt}` with widths summing to at most 0.90\linewidth (for example 0.08, 0.10, 0.11, 0.13, 0.14, 0.10, 0.12, 0.12). Rebuild and confirm no "in alignment" overfull line remains for 02b_pol2.tex.

**R22-2 [minor] The bundle no longer matches the source for 02b_pol2.tex.**
- **Location:** arxiv-submission.zip and paper/arxiv/02b_pol2.tex (22:27:17) contain the table[t]/tabularx version; sections/02b_pol2.tex (22:29:20) and main.pdf (22:29:31) contain the longtable version. Cell text is identical; only l.64–77 and l.89–90 differ.
- **Why it matters:** the protocol's exit condition requires the clean-room bundle to match the reviewed PDF; verdict_changes.md reports the clean-room result for the older version.
- **Fix:** after R22-1, re-run make_arxiv.py and make_metadata.py and re-check that every bundled section equals the comment-stripped source (as in round 21).

**R22-3 [minor] "unlike theirs" in contribution 1 overclaims and reads as advocacy.**
- **Location:** 01_introduction.tex l.41: "place the specification among five other governance paradigms to show why its clauses, unlike theirs, can be tested against evidence".
- **Problem:** the paper itself tests clauses of the other paradigms (§5 against AI Act Art. 5, 14, 86; GDPR Art. 22; DSA Art. 17, 20), §2.2 says paradigm (d) "specif[ies] the intercept precisely, as code with a harm taxonomy and a threshold", and the Model Spec "shares the licence and the changelog". What distinguishes PoL2 is that it states intercept, construct, record and (for welfare) decision-maker together, not that other texts are untestable.
- **Fix:** "…to show which of its properties make its clauses readable as testable requirements for an inference-time safeguard, and what each costs (\cref{sec:paradigms})."

**R22-4 [minor] "no annotated data exists in any language" contradicts §6 and §7.2.**
- **Location:** 02b_pol2.tex l.102 (property (ii)): "the construct has never been operationalised, no annotated data exists in any language".
- **Conflict:** 06_design.tex l.6 says the workstream's pilot protocol "already distinguishes conforming, violating and insufficient verdicts"; 07_discussion.tex l.150 refers to "the workstream's 20 public pilot items" (polgov); checklist item 5 cites polgov. That is an operationalisation and a small labelled set.
- **Fix:** "the construct has not been operationalised beyond the workstream's 20 pilot items~\cite{polgov}, no annotated benchmark exists in any language (\cref{sec:evidence}), …"

**R22-5 [minor] "names … the decision-maker" is true for Chapter 7 only, and property (i) omits the vendor-dependence cost it reintroduces.**
- **Location:** 02b_pol2.tex l.115: "it names the intercept, the construct, the record and the decision-maker in clauses that can be cited"; l.99–100 (property (i)): "avoids the retraining and vendor dependence of (c); the cost is that the text does not say how the valve is built, … who operates it".
- **Problem:** l.100 concedes that the text does not say who operates the valve, so l.115 cannot claim the decision-maker is named for the safeguard; it is named only for welfare decisions (Art. 2(1), Art. 10). And a valve built on a hosted model reintroduces vendor dependence (T3; G7 box).
- **Fix:** l.115: "names the intercept, the construct, the record and, for welfare decisions, the decision-maker"; l.100: add "and, if the valve is built on a hosted model, the vendor dependence returns (T3, \cref{sec:synthesis})".

**R22-6 [minor] Two "not supported" cells rest on absence of evidence, which the table's own definition reserves for "not tested".**
- **Location:** 07_discussion.tex l.9 defines NS as "where the coded evidence shows the function failing or depends on a property the evidence contradicts" and NT as "where no coded study measures what the clause asks for". Row 7 (l.65–69, per-person quantification) says "no study measures differential error by speaker group on behavioural judgements" and cites one informal, non-counterbalanced test ("not rated"), language degradation on African languages (arx37647, not a behavioural or hate-language task) and steering (low), yet gives NS. Row 5 (l.53–57, ethical verification) says "no coded study tests the EAP construct" in the verdict cell itself, yet gives NS.
- **Also:** "The verdict" l.80–82 lists per-person quantification among the functions whose "decisive findings are negative and … consistent", but the five findings then listed concern thresholds, steering, option names, abstention and peer errors; only steering bears on quantification.
- **Why it matters:** the task is to ensure NS is not stronger than the evidence and certainty allow; here NS is a precautionary verdict (the §7.2 rule "we ask for more evidence to relax a safeguard than to add one"), which is legitimate but must be labelled as such.
- **Fix:** Row 7 verdict: "NS as a decision input (steering, low); NT on error by group: score events and behaviours, never persons, until error by group and language is published (precautionary, \cref{sec:scope-certainty})". Row 5 verdict: "NS as an automatic verifier, because it depends on a neutral default and on calibration where people disagree, both contradicted; the EAP construct itself NT". In "The verdict" l.81–82 add after "per-person quantification of §5.6": "(on steering and on the absence of any group-error measurement)".

**R22-7 [nit] "the risk-based instruments state their opposite" overstates.**
- **Location:** 02b_pol2.tex l.110.
- **Problem:** AI Act Art. 14 applies to high-risk systems and Art. 5(1)(c) prohibits social scoring only under its two limbs (as §5 correctly states); NIST and ISO state no such thing. "Opposite" is stronger than the texts.
- **Fix:** "the EU instruments impose contrary requirements on the systems they cover".

**R22-8 [nit] Art. 9(3) is scoped to the welfare system.**
- **Location:** 02b_pol2.tex l.106–107: "unimpeded access to all data and logs (Art. 9(3))"; "Art. 9(3) opens all logs to anyone".
- **Source:** en_7.md Art. 9(3): "Humans may access all data and logs *of the welfare system* without obstruction."
- **Fix:** add "of the welfare system" in both places; the privacy cost in l.108 then applies to welfare decisions directly and to the valve only if its logs are placed in that system.

**R22-9 [nit] "assigns the amendment procedure itself to NaturalDAO (Art. 11(1), (3))" is indirect.**
- **Location:** 02b_pol2.tex l.105.
- **Source:** Art. 11(1) lets NaturalDAO propose amendments; 11(3) requires EAP ethical verification, which Art. 6(3) assigns to NaturalDAO; 11(2) and 11(4) give people a questioning period and a right to question.
- **Fix:** "lets NaturalDAO propose amendments and verify them itself (Art. 11(1), (3), with Art. 6(3))".

**R22-10 [nit] "routing and engineering" under-describes the Chinese benchmarks.**
- **Location:** 07_discussion.tex l.89: "the only Chinese decision benchmarks concern routing and engineering rather than hate language~\cite{qin2026zhdecisionbench,arx09896}".
- **Source:** qin2026zhdecisionbench coding rows cover customer-service and voice routing *and scam detection*; arx09896 is ship-design (NL2Hull).
- **Fix:** "concern service routing, scam detection and ship-design engineering rather than hate language".

**R22-11 [nit] Row 7 certainty cell leaves one cited result unattributed.**
- **Location:** 07_discussion.tex l.68: "very low (culture); low (steering); not rated (group bias, single informal test)".
- **Problem:** the low-resource-language degradation (arx37647) cited in the evidence cell is attributed to no finding.
- **Fix:** "not rated (group bias, single informal test; language degradation, one benchmark)".

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 1 | R22-1 |
| Minor | 5 | R22-2, R22-3, R22-4, R22-5, R22-6 |
| Nit | 5 new, plus 5 carried | R22-7, R22-8, R22-9, R22-10, R22-11; R17-2, R17-3, R21-1, R21-2, R21-3 |

New major or minor problems remain: yes
