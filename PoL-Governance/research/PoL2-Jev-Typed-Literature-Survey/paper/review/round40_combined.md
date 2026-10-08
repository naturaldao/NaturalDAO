# Round 40: combined review (fidelity, balance/positionality, method, consistency, legal precision, arXiv moderator)

Date: 2026-10-09. Scope: verification of the round-39 changes (abstract, §8) and an independent whole-paper pass. Priorities: abstract, §1 and §8 as stand-alone claims; §2.3 balance; §7.1 verdict traceability; legal statements; PoL2 quotations; numbers against sources; build, bundle and metadata. Items resolved in REVIEW.md, AUDIT.md and rounds 12–39 are not re-raised; author-only items (author placeholder) are not findings.

**Inputs**
- 00_abstract.tex and 08_conclusion.tex 9 Oct 00:03; main.pdf, main.log, arxiv_metadata.txt, arxiv-submission.zip 9 Oct 00:03:45 (rebuilt after the edits). main.log: "Output written on main.pdf (96 pages, 2039685 bytes)", 0 `!` lines, 0 undefined/multiply-defined, 17 overfull boxes (unchanged).
- Zip unpacked to scratch (r40zip): 00_abstract.tex and 08_conclusion.tex byte-identical to the working copy; file list unchanged (16 .tex, counts, counts_update, main.bbl, 7 figure PDFs, 00README.json).
- arxiv_metadata.txt abstract recounted: 1919 of 1920 characters; text matches 00_abstract.tex with macros expanded (107, 7, Jev, 85, kappa = 0.72, PoL2, PoL2's).
- `python scripts\rate_certainty.py --check`: CHECK PASSED. Now 0 moderate, 11 low, 4 very low; contested 2, 5, 11, 14; main only contested 2, 5, 14 (unchanged from round 39).

## R39 status

| Item | Status | Evidence |
|---|---|---|
| R39-1 "on simulated data" | FIXED | Abstract: "in one preregistered study on simulated data accepting low-risk verdicts only when an independently built rule agreed lost no accuracy, though disguised attacks passed"; matches §1 l.32 and 04_evidence ("simulated network data"). |
| R39-2 §8 practices | FIXED | 08 l.11 now "…untrusted queries restricted and logged, independent flags asked in separate calls, scoring of events…". §8's list now matches the nine §7.1 "What transfers" bullets item by item (three-valued + sufficiency; neutral identifiers; record; local calibration + re-validation; agreement gating; human-ended chains + blind audit; probabilities/sensitive fields/restricted and logged queries/separate calls; events not persons; construct benchmark), and 06 element 3. |
| R39-3 antecedent | FIXED | "peer evaluators repeated almost all of a typed model's confident errors"; same wording as §1 l.33 ("a typed model was most confident"); the model in arx29769 is Jev, a typed model, so no overstatement. |
| Trim ", adjudication included" | No meaning change | "not a suitable tool for any function that decides" still covers adjudication; §1 l.36, §7.1 l.81 and §8 l.5 name dispute adjudication explicitly. |
| First-sentence rewording | Nit | See R40-1. |
| Carried nits | not applied, carried | R17-2, R17-3, R21-1, R21-2, R21-3, R37-1, R38-2 unchanged. |

## Fresh pass

**(1) Abstract, §1, §8 as stand-alone claims.** Re-read sentence by sentence against the body: corpus counts and window (counts.tex 107/7/85, κ 0.72 on 30), detector claim (finding 1 low; arx29429 median AUROC 0.886, verified in full text; arx03324), gated study (finding 12 very low, simulated data), judge failures (findings 2, 6, 4, 9, 13), "not generally worse… most failures lack a comparison" (finding 15 low^j), update reversed no answer (§1 l.37, script: only 11 and 14 changed by update), five tensions (§5 T1–T5), verdict and "low or very low" (script), "four findings are contested" (§8 l.8; script 2, 5, 11, 14), Chinese-construct extrapolation (§7.1 l.89). §1 contributions 1–4 match §2.3/App. A, §3, §5, §6/§7.1. Consistent apart from R40-1.

**(2) §2.3 balance and positionality.** Properties (i)–(v) each carry their cost; the points against PoL2 (originator control, renumbering within three days, no peer review, NaturalDAO self-verifying its own amendments, "may accept", privacy conflict of Art. 9(3), contrary EU requirements, resemblance to social scoring, "can" not "must" in 5.6) are stated. The CAC Interim Measures are described neutrally, with a gap identified in both texts and named as "the natural second case". The positionality statement discloses contributor status, reputational interest, coincidences with the pilot protocol (flagged again in §6), no originator review, and AI-agent coding without hand re-checks. T4 option (a) is listed while saying the evidence does not support it. No finding.

**(3) §7.1 verdict traceability.** Every certainty cell of tab:verdict names a finding whose rating equals the script's "now" column (1, 3, 4, 6, 8, 9, 13 low; 2, 14 low^c; 7, 12 very low); finding 15 "low, by judgement" in l.84 matches low^j; "not rated" entries are single-study results not in tab:keyfindings. Decisive numbers spot-checked against full texts this round: arx29769 96.0% (242 of 252, against 50.3%), arx33401 130 confident misses, arx34024 10.5% (17/162), arx24574 "Six of 14 tasks cleared" (= 8 of 14 missed), arx29429 median AUROC 0.886. No finding.

**(4) Legal statements.** Re-read 05 "Regulatory parallels", 02b tab:paradigms and l.116–129: AI Act Art. 3(39)/Recital 44 (biometric basis, so text-only inference outside 5(1)(f)), 5(1)(c) elements (over time, social behaviour or characteristics, unrelated-context or unjustified/disproportionate treatment), 14, 86 (Annex III, legal or similarly significant effects), Annex III 5(a) (public authorities) and 8(a) ADR with Recital 61; GDPR Art. 22(1), (3) limited to contract/explicit consent; DSA Art. 14, 16, 17, 17(3)(c), 20, 20(6), 24(5); CAC Measures Art. 2, 4, 4(1), 14(1)–(2), 15, 17. Accurate and hedged ("by analogy", "may reach", "where it applies"). No finding.

**(5) PoL2 quotations.** 02b and 05 unchanged since round 39's verbatim check against scratchpad/pol; no new quotation introduced by the round-39 edits. No finding.

**(6) Method, §6, statements, arXiv moderation.** §7.2 limitations (AI coders of one family, κ as upper bound, incomplete recall 18 of 103, no human-reviewer comparison) and §6 trade-offs are candid; "Use of AI assistance" discloses agent roles and absence of manual re-checking. Title, categories (cs.CY primary, cs.AI), CC BY 4.0, comments ("96 pages, 7 figures", repository path) raise no moderation issue; content is a policy analysis with documented evidence assessment, appropriate for cs.CY. No finding.

## Findings

**R40-1 [nit] The reworded first sentence of the abstract attributes the low cost to the output type.**
- Location: 00_abstract.tex l.2 and arxiv_metadata.txt: "Typed decision models return a probability over declared options, so screening every message is cheap."
- Evidence: §1 l.6–8 attributes the saving to the model "not generating text at all" ("Because the output is a value rather than prose … at a small fraction of the latency and price of a generative call"), and §1 l.49 notes, via arx32160, that typed readout had not shown an advantage over reading label probabilities from a generative model, which also returns a probability over declared options. The round-38 wording ("which return a probability over caller-declared options, make screening every message cheap") was attributive; "so" now states a causal link the body does not make in that form. Meaning for a reader is close, hence nit.
- Fix: e.g. "Typed decision models return a probability over declared options without generating text, so screening every message is cheap" (+24 characters, needs a trim elsewhere), or accept as a summary.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 0 | |
| Nit | 1 new, plus 7 carried | R40-1; R17-2, R17-3, R21-1, R21-2, R21-3, R37-1, R38-2 |

R39-1, R39-2, R39-3: FIXED.

New major or minor problems remain: no
