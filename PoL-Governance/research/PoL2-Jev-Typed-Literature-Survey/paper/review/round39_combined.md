# Round 39: combined review (fidelity, balance/positionality, method, consistency, legal precision, arXiv moderator)

Date: 2026-10-09. Scope: verification of R38-1 (abstract) and an independent whole-paper pass. Priorities: abstract, §1 contributions/thesis and §8 as stand-alone claims; §2.3 balance; §7.1 verdict traceability; legal statements; PoL2 quotations; build, bundle and metadata. Items resolved in REVIEW.md, AUDIT.md and rounds 12–38 are not re-raised; author-only items (author placeholder) are not findings.

**Inputs**
- 00_abstract.tex 23:58; main.pdf, main.log, arxiv_metadata.txt, arxiv-submission.zip 23:59. main.log: "Output written on main.pdf (96 pages, 2039666 bytes)", 0 `!` lines, 0 undefined/multiply-defined, 17 overfull boxes (unchanged).
- Zip unpacked to scratch: every .tex, counts.tex, counts_update.tex differs from the working copy only by the flattening done by make_arxiv.py (`sections/` and `figures/` prefixes removed, generator comments stripped, CRLF); 00_abstract.tex, 01, 02b, 05, 07, 08, 09, D and main.bbl are byte-identical. 7 figure PDFs; 00README.json names pdflatex.
- `python scripts\rate_certainty.py --check`: CHECK PASSED. Now 0 moderate, 11 low, 4 very low; contested 2, 5, 11, 14. Main only: contested 2, 5, 14; the update changed only 11 (now contested) and 14 (very low^c → low^c), matching §1 l.37 ("raised one certainty rating… added a study that contests another finding"). Finding 3's rise (very low → low) is between "4 Oct recomputed" and "main only", i.e. not attributed to the update, consistent with §1.
- arxiv_metadata.txt abstract: 1919 of 1920 characters (recounted); text matches 00_abstract.tex with macros expanded (107, 7, Jev, 85, kappa = 0.72, PoL2, PoL2's).

## R38 status

| Item | Status | Evidence |
|---|---|---|
| R38-1 abstract coding claim | FIXED | Abstract now "…in its first 17 days; author-directed AI agents read in full, appraised and coded the \nCoded{} that bear on them (blind second coding: $\kappa = \nKappa{}$)". \nCoded = 85 (counts.tex) = 03_method l.59 "\nCoded{} report results that bear on at least one requirement and are coded"; "them" resolves to the seven requirements; κ = 0.72 on the 30-source blind sample (\nKappaN). Claim no longer exceeds §3 (the 7 non-empirical appraised sources and 22 background papers are simply not mentioned, which is not an overstatement). Same text in arxiv_metadata.txt and in the zip. |
| R38-1 trims | No meaning change | (1) "prescribing an AI ``safety valve''" → "prescribing a ``safety valve''": the abstract's next clauses ("AI-only adjudication", "whether they can serve as safeguards") and §1 l.14/02b l.33–35 keep the valve automated; no claim is altered. (2) "the specification's construct" → "\pol{}'s construct": same referent. |
| R38-2, R37-1 and carried nits | not applied, carried | 02b l.45, l.110 and A_concordance unchanged. |

## Fresh pass

**(1) Abstract, §1, §8 as stand-alone claims.** Sentence by sentence against the body: "107 studies and 7 grey sources", "first 17 days" (15 Sep–1 Oct, §3), "85 that bear on them", κ, detector claim (finding 1, low; arx29429, arx03324), gated study (finding 12, very low), judge failures (findings 2, 6, 4, 9, 13), "not generally worse… most failures lack a comparison" (finding 15, §7.1), "update to 8 October reversed no answer" (§1, §7.2), five tensions (§5), verdict and "low or very low" (script), "four contested" in §8 and §7.1 (script: 2, 5, 11, 14), Chinese-construct extrapolation (§7.1). All consistent except two nits (R39-1, R39-3). §1 contributions 1–4 match §2.3/A (28 clauses), §3, §5 and §6/§7.1. §8's practice list vs §7.1 "What transfers": one omission (R39-2).

**(2) §2.3 balance.** Each property (i)–(v) carries its cost; the points against PoL2 (originator control, renumbering, no peer review, self-verification of amendments, "may accept", privacy conflict, contrary EU requirements, social-scoring resemblance) are stated; the CAC Measures are described neutrally with a gap identified in both texts (l.127–130), and "the Interim Measures would be the natural second case". No promotional framing. No finding.

**(3) §7.1 verdict traceability.** Each certainty cell names a finding whose rating equals the script's "now" column (1, 3, 4, 6, 8, 9, 13 low; 2, 14 low^c; 7, 12 very low); finding 15 "low, by judgement" in the verdict paragraph matches low^j. Decisive numbers unchanged since round 38's full check. "four are contested" matches. No finding.

**(4) Legal statements.** Re-read 05 "Regulatory parallels", 02b tab:paradigms and l.116–129: AI Act Art. 3(39)/Recital 44, 5(1)(c), 5(1)(f) with medical/safety exception, 14, 86 (Annex III, legal or similarly significant effects), Annex III 5(a) and 8(a) with Recital 61; GDPR Art. 22(1), (3) limited to contract/explicit consent; DSA Art. 14–17, 17(3)(c), 20, 20(6), 24(5); CAC Measures Art. 2, 4, 4(1), 14(1)–(2), 15, 17. All accurate and hedged ("may reach", "by analogy", "where it applies"). No finding.

**(5) PoL2 quotations.** 19 quoted strings from §1, §2.2, §2.3 and §5 searched in scratchpad/pol/en_*.md: all present verbatim (three only after removing Markdown escapes or curly apostrophes: 5.4 "within the existing large-language-model architecture…", 5.6 "each person's Love Language…", 5.5 "hate attack on humanity's core ethic"); "All disputes" (Art. 10) verbatim. No new finding beyond carried R21-3/R38-2.

**(6) Build, bundle, metadata.** Consistent (see Inputs). Title, categories (cs.CY, cs.AI), CC BY 4.0, Comments ("96 pages, 7 figures") raise no moderation issue.

## Findings

**R39-1 [nit] The abstract again omits "on simulated data" for the gated study (regression of R3-arg-12).**
- Location: 00_abstract.tex l.5 and arxiv_metadata.txt: "in one preregistered study accepting low-risk verdicts only when an independently built rule agreed lost no accuracy, though disguised attacks passed."
- Evidence: §1 l.32 "in one preregistered study on simulated data … relative to a frontier LLM"; 04_evidence l.212 "on simulated network data". round4_argument.md records R3-arg-12 as FIXED with "on simulated data" in the abstract; the R38-1 version of the abstract no longer has it.
- Fix: if space can be found (18 characters; the abstract is at 1919/1920), "in one preregistered study on simulated data"; for example, shorten "Five tensions in the text follow, set against EU law:" to "Five tensions with EU law follow:" (−20). Otherwise leave, as round 3 judged the existing hedges sufficient.

**R39-2 [nit] §8's list of practices that transfer omits one practice from §7.1's list.**
- Location: 08_conclusion.tex l.11.
- Evidence: §7.1 "What transfers" bullet 7 ends "and separate independent flags into separate calls" (supported by zen23038928); §8 lists "probabilities kept from untrusted callers, unneeded sensitive fields kept out of the input and untrusted queries restricted and logged" without it. Round 38 recorded the two lists as matching item by item.
- Fix: add ", independent flags asked in separate calls" after "restricted and logged", or accept the omission as a summary.

**R39-3 [nit] "its confident errors" in the abstract has no clear antecedent.**
- Location: 00_abstract.tex l.6: "It does not support them as judges: … and peer evaluators repeated almost all of its confident errors."
- Evidence: the sentence's subject "It" is the evidence and "them" the typed models; finding 13 is "Peer evaluators repeat Jev's most confident errors" and §1 l.33 says "a typed model".
- Fix: "of \jev{}'s confident errors" (+2 characters; combine with the trim proposed in R39-1).

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 0 | |
| Nit | 3 new, plus 7 carried | R39-1, R39-2, R39-3; R17-2, R17-3, R21-1, R21-2, R21-3, R37-1, R38-2 |

R38-1: FIXED.

New major or minor problems remain: no
