# Round 32: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R31-1..R31-3 against arx04985 (§IV-B, Table V, §VI-A, App. C1–C2); grep of every section and the architecture figure for label withholding, rate or query limits, data minimisation and task restriction; fresh whole-paper pass (abstract, §6, §7.1, lessons, §7.2 limitations/open problems, §8, metadata, arXiv bundle). Items resolved in REVIEW.md, AUDIT.md and rounds 12–31 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/06_design.tex, 07_discussion.tex, 08_conclusion.tex (23:30); main.pdf 23:30; main.log: "Output written on main.pdf (96 pages, 2037743 bytes).", no `!` lines, no undefined or multiply defined references.
- `python scripts/rate_certainty.py --check` (repository root): CHECK PASSED ("tab:keyfindings and tab:certchanges agree with the computed ratings").
- scratchpad/update/arx2610.04985.txt: §IV-B1 threat model ("a malicious user authorized to submit requests"), §IV-B2 attack settings ("two queries per state", six for ethnicity), Table V and its discussion, Takeaway 4 ("mask sensitive information in application state"), §VI-A, App. C1–C2.
- figures/fig_architecture.pdf (text extracted with PyMuPDF); identical to arxiv/fig_architecture.pdf and to the copy in arxiv-submission.zip. Zip copies of 06/07/08 match sections/ except the expected figure-path rewrites.
- arxiv_metadata.txt: 96 pages, abstract 1916/1920 characters.

## Task 1: re-check of round 31

| Item | Status | Evidence |
|---|---|---|
| R31-1 oracle sentence split | FIXED | 07 l.93: planted-instruction precondition now governs only the attribute result ("with conditional instructions planted in the input, … revealed hidden gender, age-group, health and ethnicity attributes in every tested case, with two to six queries per state (an open model's labels revealed none); separately, its verdicts raised … and its labels trained a surrogate to 92% agreement from 200 labels"). Matches §IV-B2/Table V (official Jev 100% coverage and accepted accuracy, label access; NanoJev zero coverage under label access) and App. C1–C2 (49% → 92%, 200 labels). |
| R31-2 element 4 / §7.1 / §8 / item 7 | FIXED in substance; residual on task restriction (R32-1) | 06 element 4 now adds data minimisation ("fields a decision does not need, sensitive attributes above all, are kept out of the detector's input") and "restricted to authorised tasks and logged", following §VI-A; 07 l.93 adds "a query-rate limit alone would not bound attribute inference"; lesson 7 (07 l.105), §8 l.11 and checklist item 7 ("under the deployed input and query restrictions") agree. |
| R31-3 figure box 4 | FIXED (partially; R32-3) | PDF box 4 reads "probabilities withheld; untrusted / queries restricted, logged (G2)"; regenerated 23:30 and copied to arxiv/ and the zip. |

**Grep** (`label quer|untrusted|rate.limit|query limit|withh|oracle|04985|sensitive field|minimi|authori[sz]ed task`): 04 l.403–404, 06 element 4 (title and clause), 06 element 7 ("without becoming an oracle"), tab:checklist item 7, 07 l.93, l.105, l.153, 08 l.11, plot_architecture.py box 4. No remaining mention of a "query limit" or "rate-limited" requirement in the design. Residues: 04 l.404 still frames the extension as "to labels and query volume" (R32-3); the open-problems item at 07 l.153 lists rate limiting but not the two measures the design now recommends (R32-2); "health" at 07 l.93 vs "heart-disease" at 04 l.403 (R32-3).

## Task 2: fresh pass

Abstract, §8 and metadata abstract are verbatim-consistent; "four are contested" (07 l.90, l.124; §8) matches the script; lesson-to-element pointers (elements 3, 4, 5, 6, 7; items 2, 3, 4, 10, 11, 16) resolve; checklist item 7 Basis includes arx04985; arXiv bundle matches the build. The one substantive problem found is in the justification chain of element 4 (R32-1).

## Findings

**R32-1 [minor] Element 4 justifies restricting queries to authorised tasks by the attribute-inference result, but that attack was run by an authorised user inside the authorised task.**
- **Location:** 06_design.tex element 4, final clause ("queries from untrusted callers are restricted to authorised tasks and logged, since with conditional instructions planted in the input labels alone revealed hidden attributes with two to six queries per state, and labels also trained a surrogate"); 07 l.93 ("This argues for … restricting untrusted callers' queries to authorised tasks and logging them …; a query-rate limit alone would not bound attribute inference").
- **Evidence:** arx04985 §IV-B1: "a malicious user authorized to submit requests can exploit this dependence by crafting conditional inputs"; §IV-B2: a fixed support-routing task and "fixed conditional template", two queries per state. Takeaway 4: "These results highlight the need to mask sensitive information in application state." §VI-A pairs minimisation and task restriction but does not claim the latter stops attribute inference; the valve itself is an authorised fixed-question task whose users see its outcome.
- **Problem:** As written, the "since" clause presents both task restriction and logging as answers to attribute inference. Neither bounds it in the valve setting (the attacker is a legitimate user of the authorised task, and two queries look like normal use); only keeping the attribute out of the input does. R31-2's logic (a rate limit cannot bound a two-query probe) applies equally to task restriction, and 07 l.93 now singles out the rate limit only.
- **Fix:** tie each measure to the result it addresses, e.g. element 4: "fields a decision does not need, sensitive attributes above all, are kept out of the detector's input, because conditional instructions planted by an ordinary user of the task made labels alone reveal hidden attributes in two to six queries per state~\cite{arx04985}; queries from untrusted callers are restricted to authorised tasks and logged, which limits plan refinement with attacker-chosen questions and makes surrogate extraction visible~\cite{arx04985}." In 07 l.93 replace the last clause by "neither a query-rate limit nor restriction to authorised tasks would bound attribute inference, which ran inside an authorised task; only keeping the attribute out of the input does."

**R32-2 [nit] The open problem on queryable safeguards omits the measures the design now recommends.**
- **Location:** 07 l.153 ("Whether hiding or coarsening probabilities, adding noise or rate-limiting reduces attack success … has not been measured").
- **Evidence:** arx04985 §VI-A: "The effectiveness of these defenses and their impact on utility remain to be evaluated for Jev."
- **Fix:** "Whether keeping sensitive fields out of the input, restricting queries to authorised tasks, hiding or coarsening probabilities, adding noise or rate-limiting reduces attack success …".

**R32-3 [nit] Small residues of the earlier framing.**
- 04 l.404 "extends the case for keeping probabilities from untrusted callers (§6) to labels and query volume" → "… to labels, and for keeping sensitive fields out of the input" (query volume is no longer the design's answer).
- 07 l.93 "health" → "heart-disease status" (as 04 l.403 and the source; only heart disease was tested).
- fig:architecture box 4 does not show data minimisation, now the first measure of element 4: e.g. "probabilities withheld; unneeded / sensitive fields kept out; untrusted / queries restricted, logged (G2)"; regenerate and copy to arxiv/.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 1 | R32-1 |
| Nit | 2 new, plus 5 carried | R32-2, R32-3; R17-2, R17-3, R21-1, R21-2, R21-3 |

R31-1, R31-3: FIXED. R31-2: FIXED in substance; justification residue raised as R32-1.

New major or minor problems remain: yes
