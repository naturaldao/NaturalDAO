# Round 30: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R29-1..R29-4 against the full texts; whether the new element-4 clause needs a checklist item; fresh whole-paper pass prioritising every sentence in the abstract, §1, §7.1 and §8 that summarises a quantitative finding, checked against §4/§4.9 and the source. Items resolved in REVIEW.md, AUDIT.md and rounds 12–29 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/06_design.tex, 07_discussion.tex, D_corrections.tex (23:23); main.log: "Output written on main.pdf (95 pages, 2035938 bytes)", no `!` lines.
- `python scripts/rate_certainty.py --check` (repository root): CHECK PASSED. `--verbose`: now 0 moderate, 11 low, 4 very low; contested 2, 5, 11, 14; main only contested 2, 5, 14.
- Full texts: scratchpad/update/arx2610.03324.txt, arx2610.04985.txt.

## Task 1: re-check of round 29

| Item | Status | Evidence |
|---|---|---|
| R29-1 agreement-gating lesson | FIXED | 07 l.103 and l.87 now "lost no macro-F1, though disguised attacks (still) passed (very low)"; matches 04 l.212, l.75 and tab:keyfindings row 12. |
| R29-2 label-withholding lesson vs design | FIXED in §6/§7, residue in §8 | 06 element 4 adds "label queries from untrusted callers are therefore rate-limited and logged … labels alone revealed hidden attributes and trained a surrogate~\cite{arx04985}"; 07 l.93, l.105 reworded to "keep probabilities … limit and log their label queries". Source: Table V, official Jev 100% coverage and accepted accuracy for all four attributes under label access; App. C2, NanoJev surrogate 49% → 92% agreement after 200 labels; C1 harmfulness 2.3 → 4.5. Supported. But §8 l.11 was not updated (R30-1), and no checklist item tests the new clause (R30-2). |
| R29-3 1.6-point result | FIXED | 07 l.30, l.87 "on the HateCheck diagnostic set". arx03324 Table: Jev direct .960 vs Sol .976 on HateCheck (= 1.6); l.695 "Jev scores 1.6 macro-F1 points below Sol at ≈97% lower recorded cost" ($0.033 vs $1.177 per 1K). Matches 04 l.400. |
| R29-4 D.1 count | FIXED | D l.74 "add opposing studies to the two findings that the main window already contests, one to the injection finding and two to that on thresholds set in advance"; script: row 14 opposing zen22935043, zen23075657 (update) plus arx33689 (main); row 5 contested in main; row 11 newly contested ("make one finding contested"). |

**Does element 4's new clause need a checklist item?** Yes. Every other clause of element 4 is tied to a checklist item (local fitting: item 2; calibration: 3; re-certification: 16), and §6 says tab:checklist "turns the evidence into a checklist". Item 7 red-teams "adaptive, probability-guided additions, inserted opinions, lures and multi-turn attacks" but not label-only oracle use (attribute inference, plan refinement, surrogate extraction), which is what the rate limit is meant to bound; arx04985 is not in any checklist "Basis". See R30-2.

## Task 2: fresh pass

**Quantitative summaries checked (abstract, §1, §7.1, §8 against §4 and source).** 07 l.30: 0.886 / $0.30 vs $18.96 (04 l.29), F1 0.158 vs 0.947 (04 l.36), 97–100% (arx04985 Table I: Jev-specific injection 100/100/97.2, universal suffix 100/100/97.0; 04 l.366), 12.1% (04 l.69), 32.5–50.5% (04 l.107–108): all agree. l.48: 9.8 vs 22.8% (04 l.46), 57–94% (04 l.358), recall 0.34 and 21 of 76 (04 l.75): agree. l.54: 87%/62% (04 l.115), 0.339 (04 l.147), 0.88 at 55/45 (04 l.402): agree. l.60: 96.0%, 5 of 130, 10.5%, 7–54%, 32.8%, 8 of 14: agree with 04/05. l.72: 0.93/0.96 (04 l.254): agree. l.82 and l.87 certainty labels match tab:keyfindings (rows 2, 4, 6, 9, 12, 13). Abstract/§1/§8 "almost all" (96.0%, upper bound; resolved R2-arg-15, round 7), "lost no accuracy" for the gate (04 l.212, macro-F1), "17 days" (15 Sep–1 Oct inclusive), "update to 8 October reversed no answer" (D.1; script shows no rating falls), §8 "four findings are contested" (script: 2, 5, 11, 14): agree. §1 "raised one certainty rating … from very low to low" (row 14 main very low → now low): agrees.

**One summary sentence over-generalises a source** (R30-3).

## Findings

**R30-1 [minor] §8 still says labels are kept from untrusted callers, contradicting the R29-2 fix.**
- **Location:** 08_conclusion.tex l.11, the "What transfers" sentence: "…human-ended chains with blind audit of confident decisions, labels and probabilities kept from untrusted callers, scoring of events rather than persons…".
- **Problem:** After R29-2, element 4 returns labels to untrusted callers but rate-limits and logs their queries, and 07 l.93/l.105 say "keep probabilities from untrusted callers, limit and log their label queries". The conclusion restates the old, stronger lesson that the design does not implement; the conclusion is the one place many readers take the practices from.
- **Fix:** "…probabilities kept from untrusted callers and their label queries limited and logged, …".

**R30-2 [minor] Element 4's new label-query clause has no checklist item or pass criterion.**
- **Location:** 06_design.tex element 4 (last clause) and tab:checklist item 7.
- **Problem:** See Task 1. The rate limit is a design commitment without a test; item 7 names probability-guided attacks but not label-only ones, and arx04985 (attribute inference and surrogate extraction from labels alone) appears in no item's Basis. 07 l.153 correctly lists the effect of rate-limiting as unmeasured, which is a reason to require it be reported, not to omit it.
- **Fix:** extend item 7: Requirement "… multi-turn attacks, and label-only oracle attacks (attribute inference, surrogate extraction) under the deployed query limit"; Basis add `\cite{arx04985}`; optionally retitle element 4 "Calibrate locally, keep probabilities from untrusted callers and limit their label queries".

**R30-3 [minor] "Labels alone revealed hidden attributes in every tested case" is attributed to the typed interface, but holds for hosted Jev only and required planted instructions.**
- **Location:** 07_discussion.tex l.93 ("The typed interface itself makes a safeguard a queryable oracle: labels alone revealed hidden gender, age-group, health and ethnicity attributes in every tested case, …").
- **Evidence:** arx04985 Table V text: "The official Jev is highly vulnerable, achieving 100% Coverage … under both label and probability access … NanoJev … Under label access, the attack abstains on all attributes, resulting in zero Coverage." The attack uses a conditional instruction template in the input (§4 l.403 says so: "conditional instructions in user input made hosted \jev{}'s labels alone reveal …").
- **Problem:** The sentence makes a property of the interface out of a result that the open typed model with the same interface did not show, and drops the injection precondition that §4 states; it is the premise of the R29-2 lesson.
- **Fix:** "…: with conditional instructions planted in the input, hosted \jev{}'s labels alone revealed hidden gender, age-group, health and ethnicity attributes in every tested case (an open model's labels revealed none), …".

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 3 | R30-1, R30-2, R30-3 |
| Nit | 0 new, plus 5 carried | R17-2, R17-3, R21-1, R21-2, R21-3 |

R29-1, R29-3, R29-4: FIXED. R29-2: FIXED in §6/§7; residue in §8 raised as R30-1.

New major or minor problems remain: yes
