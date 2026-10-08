# Round 33: combined review (fidelity, balance/positionality, method, consistency, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R32-1..R32-3 against arx04985 (§IV-B1 threat model, §IV-B2, Takeaway 4, §VI-A, §VI-B, App. C1–C2); grep of every section and the architecture figure for label or probability withholding, query/task restriction, rate limits and data minimisation; fresh whole-paper pass (abstract, §6, §7.1, lessons, open problems, §8, metadata, arXiv bundle). Items resolved in REVIEW.md, AUDIT.md and rounds 12–32 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/04_evidence.tex, 06_design.tex, 07_discussion.tex, figures/src/plot_architecture.py, figures/fig_architecture.pdf, main.pdf, main.log (all 23:34); 08_conclusion.tex 23:30. main.log: "Output written on main.pdf (96 pages, 2038037 bytes).", no `!` lines, no undefined or multiply defined references, 17 overfull boxes (unchanged).
- `python scripts/rate_certainty.py --check` (repository root): CHECK PASSED ("tab:keyfindings and tab:certchanges agree with the computed ratings").
- scratchpad/update/arx2610.04985.txt: §IV-B1 (l.709 "a malicious user authorized to submit requests"), §IV-B2 (l.756, two queries per state, six for ethnicity), Takeaway 4 (l.842: official Jev labels alone suffice; NanoJev requires probability access), §VI-A (l.921), §VI-B (l.927), App. C1 (l.1641) and C2 (l.1647: "queries Jev with a fixed question and the same four candidate answers", 49% → 92% after 200 labels).
- arxiv-submission.zip extracted to scratchpad: 06, 07, 08 identical to sections/; 04 differs only by figure paths and stripped comment rules; fig_architecture.pdf byte-identical to figures/ and arxiv/. Figure text (PyMuPDF) box 4: "probabilities withheld; unneeded sensitive fields kept out; untrusted queries restricted, logged (G2)".
- arxiv_metadata.txt: 96 pages, 7 figures, abstract 1916/1920 characters.

## Task 1: re-check of round 32

| Item | Status | Evidence |
|---|---|---|
| R32-1 element 4 justification | FIXED in element 4; residual in §7.1 (R33-1) | 06 element 4 now ties minimisation to attribute inference ("since a user authorised for the task, by planting conditional instructions in the input, recovered hidden attributes from labels alone with two to six queries per state") and task restriction/logging to surrogate training and harmful-plan refinement. Matches §IV-B1, §IV-B2, §VI-A, §VI-B, App. C1–C2. 07 l.93 rewritten along the same lines, but with two overstatements (R33-1). |
| R32-2 open problem | FIXED | 07 l.153 lists hiding or coarsening probabilities, noise, rate limiting, task restriction and keeping sensitive fields out of the input; matches §VI-A "remain to be evaluated". |
| R32-3 residues | FIXED | 04 l.404 "to the fields placed in the detector's input and to the tasks untrusted callers may query"; 07 l.93 "heart-disease"; figure box 4 shows minimisation, regenerated and copied to arxiv/ and the zip. |

**Grep** (`label quer|label-only|untrusted|rate.limit|query limit|query volume|withh|oracle|04985|sensitive field|minimi|authori[sz]ed|surrogate|probabilit|restricted`) over all sections and plot_architecture.py: 02b l.113 (publication delay/coarsening), 04 l.403–404, 06 element 4 (title and clause), element 7 ("without becoming an oracle"), tab:checklist item 7 ("under the deployed input and query restrictions"), 07 l.93, lesson 7 (l.105), l.153, 08 l.11, figure box 4. No remaining "query limit", "rate-limited" or "query volume" requirement; all mentions now list the same measures as element 4. The only inconsistency with the source and within the paper is the strength of §7.1's two "bounds" claims (R33-1).

## Task 2: fresh pass

Abstract, §8 and the metadata abstract agree; "four are contested" (07, §8) matches the script; lesson-to-element and checklist pointers resolve; checklist item 7 Basis includes arx04985; the trade-offs paragraph and "design is a hypothesis" framing remain appropriately hedged; the arXiv bundle matches the build. Nothing new found outside the queryable-safeguard paragraph.

## Findings

**R33-1 [minor] §7.1 says minimisation is "the only measure that bounds attribute inference" and that task restriction and logging "bound surrogate extraction"; the first contradicts the same sentence's open-model result, the second does not hold for extraction of the valve's own task, and both claim an effect the open problem (l.153) says has not been measured.**
- **Location:** 07_discussion.tex l.93, second sentence ("… keeping sensitive fields a decision does not need out of its input, which is the only measure that bounds attribute inference, since the attack worked for a user authorised for the task; restricting untrusted callers' queries to authorised tasks and logging them bounds surrogate extraction and misuse as an oracle").
- **Evidence:** (a) Takeaway 4: attributes were inferred "from the official Jev's labels alone, but require probability access to infer them from NanoJev"; 07 l.93 itself says "an open model's labels revealed none", and element 3 prefers self-hostable models, so for an open detector withholding probabilities also stopped the tested attack. §VI-A: "Hiding probabilities removes one source of inference signal". (b) App. C2: the extraction attacker "queries Jev with a fixed question and the same four candidate answers" on 200 task-specific states, i.e. exactly an authorised fixed task; a valve user who submits messages and observes outcomes is in that position, so task restriction does not prevent a surrogate of the valve's own task, and logging only makes it visible. Task restriction does exclude the attacker-chosen feasibility questions of App. C1/§VI-B. (c) §VI-A: "The effectiveness of these defenses … remain to be evaluated"; 07 l.153 repeats this.
- **Fix:** e.g. "… out of its input, which for hosted \jev{} is the only one of these measures that would remove the signal, since the attack worked for a user authorised for the task and needed labels alone; restricting untrusted callers' queries to authorised tasks keeps the valve from serving as a general oracle for questions such as the feasibility of harmful plans, and logging makes surrogate extraction through the authorised task visible, though neither prevents it (\cref{sec:design}, element~4)." Optionally adjust element 4's final clause the same way ("restricted to authorised tasks, since labels refined harmful plans, and logged, since labels also trained a surrogate").

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 1 | R33-1 |
| Nit | 0 new, plus 5 carried | R17-2, R17-3, R21-1, R21-2, R21-3 |

R32-2, R32-3: FIXED. R32-1: FIXED in element 4; §7.1 overstatement raised as R33-1.

New major or minor problems remain: yes
