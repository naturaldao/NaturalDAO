# Round 31: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R30-1..R30-3 against arx04985; consistency of every mention of element 4, label withholding, label queries and checklist item 7 across sections; fresh whole-paper pass prioritising cross-references between §5 tensions, §6 elements/checklist, §7.1 verdict and lessons, and §8. Items resolved in REVIEW.md, AUDIT.md and rounds 12–30 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/06_design.tex, 07_discussion.tex, 08_conclusion.tex (23:27); main.pdf 23:27; main.log: "Output written on main.pdf (95 pages, 2036426 bytes).", no `!` lines, no undefined references.
- `python scripts/rate_certainty.py --check` (repository root): CHECK PASSED ("tab:keyfindings and tab:certchanges agree with the computed ratings").
- Full text: scratchpad/update/arx2610.04985.txt (§IV-B attribute inference, Table V, §VI-A mitigations, App. C1–C2).
- figures/fig_architecture.pdf (4 Oct 23:33) and figures/src/plot_architecture.py.

## Task 1: re-check of round 30

| Item | Status | Evidence |
|---|---|---|
| R30-1 §8 label lesson | FIXED | 08 l.11 "probabilities kept from untrusted callers and their label queries limited and logged"; matches 06 element 4 and 07 l.93, l.105. |
| R30-2 checklist item 7 / element 4 title | FIXED | tab:checklist item 7 adds "label-only oracle attacks (attribute inference, surrogate extraction) under the deployed query limit", Basis adds arx04985; element 4 title "Calibrate locally, keep probabilities from untrusted callers and limit their label queries". |
| R30-3 oracle sentence scope | FIXED for the attribute result, but over-scoped (R31-1) | 07 l.93 now "with conditional instructions planted in the input, hosted \jev{}'s labels alone revealed … (an open model's labels revealed none)". Table V text supports this: official Jev 100% coverage and accepted accuracy under label access; NanoJev zero coverage under label access. But the opening clause also governs the plan-harmfulness and surrogate results, which used no planted instructions. |

**Grep for consistency** (`label quer|untrusted caller|element 4|item 7|oracle|04985`): 04 l.403–404 (attribute result with "conditional instructions in user input"; "extends the case … to labels and query volume"), 06 element 4 title and clause, 06 element 7 ("without becoming an oracle"), tab:checklist item 7, 07 l.93, l.105, 08 l.11. All text mentions agree on "keep probabilities, limit and log label queries". Two residues: fig:architecture box 4 still reads only "probabilities not returned to untrusted callers (G2)" (R31-3); and the design's justification for the rate limit rests on the attribute attack, which a rate limit cannot plausibly stop (R31-2).

## Task 2: fresh pass

Cross-references checked: §5 T2 options ↔ element 3, checklist 4–5, lesson 1–2; T3 ↔ element 7 (delayed, coarsened publication), 07 l.94; T4 option (b) ↔ elements 5–6 ("the reference design … implements it") and lesson 6 ("T4, option (b)"); T5 ↔ lesson 8, tab:verdict row 6, checklist 12; T1 ↔ §8 open choice. Lesson-to-element/checklist pointers in 07 l.99–107 (elements 3, 4, 5, 6, 7; items 2, 3, 4, 10, 11, 16) all resolve to the matching content. tab:verdict certainty entries match tab:keyfindings; "four are contested" (07 l.90, l.124; §8) matches the script. No new inconsistency found outside the label-query thread.

## Findings

**R31-1 [minor] The R30-3 precondition now also governs the plan-harmfulness and surrogate results, which needed no planted instructions.**
- **Location:** 07_discussion.tex l.93.
- **Evidence:** arx04985 App. C1: the attacker submits its own state ("Harmful goal + Proposed action") and question and refines the plan from Jev's yes/no answers (harmfulness 2.3 → 4.5). App. C2: the attacker generates 200 states, "queries Jev with a fixed question and the same four candidate answers" and trains NanoJev on the answers (49% → 92%). Neither uses conditional instructions; only §IV-B attribute inference does.
- **Problem:** The sentence "with conditional instructions planted in the input, hosted Jev's labels alone revealed …, raised …, and trained …" makes all three results conditional on injection, understating the two misuse results (and the plan-refinement attack also required the attacker to choose the question, which a fixed-question valve does not allow).
- **Fix:** split: "With conditional instructions planted in the input, hosted \jev{}'s labels alone revealed hidden gender, age-group, health and ethnicity attributes in every tested case (an open model's labels revealed none); queried directly, its yes/no answers raised the judged harmfulness of harmful plans, and 200 of its labels trained a surrogate to 92\% agreement~\cite{arx04985}, …".

**R31-2 [minor] Element 4 answers the label-leak finding with a rate limit that cannot bound it, and omits the source's own mitigation.**
- **Location:** 06_design.tex element 4, last clause ("label queries from untrusted callers are therefore rate-limited and logged, since labels alone revealed hidden attributes and trained a surrogate"); echoed in 07 l.105 and 04 l.404.
- **Evidence:** arx04985 §IV-B3: attribute inference needed "two queries per state" (six for ethnicity). §VI-A: "Privacy risks can be reduced by minimizing the sensitive fields exposed to Jev and restricting queries to authorized tasks. Hiding probabilities removes one source of inference signal, but observable decisions may still reveal private attributes."
- **Problem:** A per-caller rate limit plausibly bounds surrogate extraction (hundreds of labels) and iterative plan refinement, but not a two-query attribute probe, which is the result the clause cites first. The design's response to the privacy leak is therefore not the one the evidence supports; and element 1 ("the content under review is always paired with that context") increases what hidden state the detector sees. 07 l.153 lists rate-limiting as unmeasured, so the paper has no evidence that it helps.
- **Fix:** in element 4 (or element 1) add data minimisation: "The detector's state holds only the fields its question needs; protected or sensitive attributes of persons are kept out of it, because conditional instructions made hosted \jev{}'s labels reveal such attributes in two queries~\cite{arx04985}; label queries from untrusted callers are rate-limited and logged, which bounds surrogate extraction and plan refinement~\cite{arx04985}." Mirror in 07 l.105 ("keep sensitive fields out of the detector's state, keep probabilities from untrusted callers, limit and log their label queries") and §8 l.11; optionally add to checklist item 7's Requirement "with sensitive fields removed from the state".

**R31-3 [nit] fig:architecture box 4 does not show the label-query limit now in element 4's title.**
- **Location:** figures/src/plot_architecture.py box 4 ("probabilities not returned\nto untrusted callers (G2)"); figures/fig_architecture.pdf dated 4 Oct, before R29-2/R30-2.
- **Fix:** "probabilities withheld, label\nqueries limited and logged (G2)" (and the data-minimisation item if R31-2 is adopted); regenerate the PDF and copy to paper/arxiv/.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 2 | R31-1, R31-2 |
| Nit | 1 new, plus 5 carried | R31-3; R17-2, R17-3, R21-1, R21-2, R21-3 |

R30-1, R30-2: FIXED. R30-3: FIXED for the attribute result; over-scope raised as R31-1.

New major or minor problems remain: yes
