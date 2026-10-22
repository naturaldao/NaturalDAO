# Round 23: combined review (balance/positionality, fidelity, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R22-1..R22-11, then a fresh pass on §2.3 `sec:paradigms` / `tab:paradigms`, §7.1 `sec:verdict` / `tab:verdict`, §8, abstract, §1 thesis and metadata. Items resolved in REVIEW.md, AUDIT.md and rounds 12–22 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/*.tex as of 22:40:37; main.pdf and main.log 22:40:46 (93 pages, no `!` lines, 19 overfull boxes, none in 07_discussion.tex; in 02b_pol2.tex only two paragraph overfulls of 1.66pt and 3.34pt, no "in alignment" line).
- arxiv-submission.zip 22:40:47, extracted to scratchpad/r23/zip: 00_abstract, 01, 02b_pol2, 07, 08 and A_concordance identical to the comment-stripped source (CR-insensitive diff).
- arxiv_metadata.txt: abstract 1,916 ≤ 1,920, identical to 00_abstract.tex; "93 pages, 7 figures" agrees with the PDF.
- `python scripts/rate_certainty.py --check`: CHECK PASSED; now 0 moderate, 11 low, 4 very low; contested 2, 5, 11, 14.
- PDF pages 7–9 (tab:paradigms) and 40–41 (tab:verdict) rendered at 70 dpi.
- PoL2: scratchpad/pol/en_5.md (§5.4.1, §5.5, §5.6), en_7.md (Art. 2, 4–11).
- Coding: data/evidence_coding*.csv rows for arx31142, arx37647, simmons2026saidno, arx08829 (spot check of the rows whose verdict cells changed in round 22; all other numbers were traced in round 22 and are unchanged).
- External sources: as verified in round 22 (DSA, AI Act, GDPR, CAC 2023 Measures, Santa Clara 2.0, Model Spec, Klonick, Llama Guard, NeMo, Ostrom, Makridis); no cell text about them changed since.

## Task 1: re-check of round 22

| Item | Status | Evidence |
|---|---|---|
| R22-1 tab:paradigms overflow | FIXED | longtable with tabcolsep 3pt, widths sum 0.88; no "in alignment" overfull for 02b; residual 1.7pt/3.3pt paragraph overfulls on "Institutional:" and "(Art. 11(2), (5));" (R23-5) |
| R22-2 bundle vs source | FIXED | zip 22:40:47 after the last source edit; six files identical |
| R22-3 "unlike theirs" | FIXED | 01 l.41 "which of its properties make its clauses readable as testable requirements … and what each costs" |
| R22-4 "no annotated data" | FIXED | 02b l.107 "not been operationalised beyond the workstream's 20 pilot items … no annotated benchmark exists" |
| R22-5 decision-maker; vendor dependence | FIXED | l.120 "for welfare decisions, the decision-maker"; l.105 "the vendor dependence returns (T3)" (see R23-3 for "the record") |
| R22-6 NS on absence of evidence | FIXED | row 5 "NS as an automatic verifier … the EAP construct itself NT"; row 7 "NS as a decision input (steering, low); NT on error by group … (precautionary)"; caption defines combined cells and "precautionary"; §7.1 l.81, §1 l.36, §8 l.5 state the basis |
| R22-7 "state their opposite" | FIXED | l.115 |
| R22-8 Art. 9(3) scope | FIXED | l.111, l.112 "of the welfare system" |
| R22-9 Art. 11 amendment | FIXED | l.110 |
| R22-10 Chinese benchmarks | FIXED | 07 l.89 |
| R22-11 row 7 certainty | FIXED | 07 l.68 |

## Task 2: fresh pass

**Balance and positionality of §2.3.** Still reads as comparative analysis; every distinguishing property carries a specific cost, and the superlative in "What the comparison implies" is hedged. Two residual overreaches remain: the final sentence generalises all seven requirements to any interception layer although (v) says PoL2's institutional aims are unique (R23-2), and "the record" is, like the decision-maker, stated in Chapter 7 for NaturalDAO rather than for the safety valve (R23-3). The DAO and guardrail rows describe their sources fairly; the Model Spec sentence omits inference-time customisation (R23-4).

**Fidelity of PoL2 claims.** All clause references in row (f) and (i)–(v) checked against en_5/en_7: Art. 2(1), 4, 5(5), 6(3), 9(2), 9(3), 9(7), 10, 11(1)–(5), §5.4, §5.4.1, §5.5, §5.6 correct. Note for R23-3: Art. 4(1) covers "all NaturalDAO technologies", Art. 5(5) "NaturalDAO must provide a verifiable decision chain", Art. 9(3) "data and logs of the welfare system"; §5.4.1 says of the governance layer only that it uses "the tamper-proof and auditable properties of blockchain to enhance security guarantees".

**Verdict table.** Definitions of NS/DC/NT and "precautionary" are given in the §7.1 lead paragraph and the caption; "precautionary" is used in row 7 only, and its basis (the §7.2 asymmetry rule, 07 l.144) is the cross-referenced section. Row 5 and row 7 now match the definitions. Changed cells traced: arx31142 12.1% (G2 N row), arx37647 degradation "both open LLM references degrade likewise" (supports "typed and generative models degraded"), simmons 51.12% with non-counterbalanced order (supports "informal"), arx08829 21.06 vs 19.82–23.31. Certainty cells match tab:keyfindings and the script.

**Overreach in the comparative clause of the verdict.** See R23-1.

## Task 3: consistency chain

Abstract ↔ §1 l.36 ↔ §7.1 ↔ §8 ↔ metadata agree on: not suitable for any function that decides (adjudication, ethical verification, per-person quantification, final block); detector only inside §6 for safety valve, truncation, anomaly detection; extrapolation from English benchmarks; low/very low, four contested, none moderate; update reversed nothing. Per-person quantification: "precautionary grounds" (§1), "absence of any group-error measurement" (§7.1), "rests on precaution" (§8), "(precautionary)" (row 7): consistent. The public-decision assessment dimension (row 8, DC) is stated in §8 l.6 but not in §1 l.36 or in §7.1 "The verdict" (R23-6). Comparative scope: abstract and §1 l.10 say "most failures lack a comparison"; §7.1 l.84 and §8 l.5 extend the verdict to every low-cost generative evaluator tested (R23-1).

## Findings

**R23-1 [minor] §7.1 and §8 extend the "decides" verdict to generative evaluators on evidence the paper says was mostly not compared.**
- **Location:** 07_discussion.tex l.84: "No typed model tested, and no low-cost generative evaluator tested beside one, escapes this verdict … so the verdict is against automated judges of this cost tier, not against typed models in particular"; 08_conclusion.tex l.5: "Hosted \jev{}, and the typed models and low-cost generative evaluators tested beside it, should not adjudicate …, because thresholds do not transfer, …".
- **Conflict:** 01 l.10 "most of the failures were never compared, so the evidence neither singles out typed models nor shows that their failures are shared"; abstract "most failures lack a comparison"; REVIEW.md l.50 resolved the same overreach ("Automated judges generally … failures shared"; typed worse in 6 of 14 compared negative codes, so generative evaluators did better in some). "Not generally worse" does not establish that every generative evaluator fails each listed property.
- **Fix:** l.84: "No typed model tested escapes this verdict, and no low-cost generative evaluator tested beside one has been shown to: where the comparison was made, typed models were not generally worse (low, by judgement), but most failures were never compared, so the verdict is not specific to typed models and, until generative evaluators are tested under the same protocol, applies to automated judges of this cost tier as a precaution (\cref{sec:scope-certainty})." §8 l.5: "Hosted \jev{}, and on precaution the low-cost generative evaluators tested beside it, should not …".

**R23-2 [minor] "any paradigm that does so inherits the same requirements" contradicts property (v).**
- **Location:** 02b_pol2.tex l.121.
- **Problem:** G6 is anchored in Art. 9(7) non-intervention and Art. 10 AI-only adjudication, and G7 in Art. 2(1) autonomy and §5.6 per-person assessment (tab:clauses); l.115 says "No other paradigm in the table states such aims". An interception layer under constitutional classifiers, the CAC Measures or the DSA inherits G1–G5 and the escalation question of G6, not the non-intervention and per-person-scoring requirements.
- **Fix:** "… all move toward an inference-time interception layer, and any paradigm that does so inherits G1–G5 and the escalation question of G6; the rest of G6 and G7 follow from \pol{}'s own institutional choices (v)."

**R23-3 [nit] "the record" is, like the decision-maker, stated for NaturalDAO, not for the safety valve.**
- **Location:** 02b_pol2.tex l.120 ("names the intercept, the construct, the record and, for welfare decisions, the decision-maker"); tab:paradigms row (f), last column (Art. 4, 5(5), 9(2), 9(3) unscoped).
- **Source:** en_7 Art. 4(1) "all NaturalDAO technologies", Art. 5(5) "NaturalDAO must provide a verifiable decision chain"; for the valve, en_5 §5.4.1 states only blockchain's "tamper-proof and auditable properties" in general.
- **Fix:** l.120 "… the intercept and the construct and, for NaturalDAO's decisions, the record and the decision-maker"; row (f) last cell prefix "For NaturalDAO (Chapter 7):".

**R23-4 [nit] "a change of norms requires retraining" omits the Model Spec's inference-time customisation.**
- **Location:** 02b_pol2.tex l.97; tab:paradigms row (c) itself lists "a chain of command among instructions".
- **Problem:** under the Model Spec, developers and users adjust defaults by instructions at inference within the vendor's limits; only the vendor's own norms require retraining.
- **Fix:** "so a change of the vendor's norms requires retraining under vendor control (deployers adjust only the defaults the spec leaves open)".

**R23-5 [nit] tab:paradigms layout.**
- **Location:** PDF pp. 7–9; main.log l.1443, l.1448.
- **Problem:** p. 7 carries the caption, header and row (a) with about 40% of the page blank (row (b) cannot break); row (f) stands alone on p. 9; two small overfulls (1.66pt "Institutional:", 3.34pt "(Art. 11(2), (5));" which touches the next column on p. 9).
- **Fix:** allow hyphenation in the narrow columns (e.g. `\hspace{0pt}` before long tokens or "Institu\-tional"), write "(\art{11}(2) and (5))" with a break point, and consider placing the table at the start of p. 8 (e.g. move the `longtable` after the "What the alternatives specify" paragraph) so that rows (a)–(e) share one page.

**R23-6 [nit] The row-8 verdict is missing from §1 and from "The verdict".**
- **Location:** 01 l.36; 07 l.79–90.
- **Problem:** §8 l.6 and tab:verdict row 8 give the public-decision assessment dimension (§5.6) a DC verdict ("audited aggregate measurement"); §1's explicit verdict and §7.1's prose list only the safety valve, truncation and anomaly detection, so a reader of §1 or §7.1 alone does not learn that this §5.6 function is partly supported.
- **Fix:** add to l.86 of 07 and l.36 of 01: "; the public-decision assessment of \clause{5.6} only as an audited aggregate measurement with its error carried into every conclusion".

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 2 | R23-1, R23-2 |
| Nit | 4 new, plus 5 carried | R23-3, R23-4, R23-5, R23-6; R17-2, R17-3, R21-1, R21-2, R21-3 |

R22-1..R22-11: all FIXED.

New major or minor problems remain: yes
