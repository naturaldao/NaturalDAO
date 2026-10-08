# Round 37: combined review (fidelity, balance/positionality, method, consistency, legal precision, arXiv moderator)

Date: 2026-10-08. Scope: check of R36-1 and R36-2 against Regulation (EU) 2024/1689 (EUR-Lex OJ L 2024/1689: Recital 61; Art. 6(2)–(3), 11–14 incl. 14(4)(e), 86(1); Annex III point 8(a)); whether the §7.1 adjudication row and §8 must now mention direct application; fresh pass of abstract, §1, §5 (all of T1–T5 and the regulatory paragraph), §6, §7.1 table and verdict, §8, statements, metadata. Items resolved in REVIEW.md, AUDIT.md and rounds 12–36 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged; author-only items (author name placeholder in main.tex l.29, l.62 and metadata, etc.; REVIEW.md l.94) are not findings.

**Inputs**
- sections/02b_pol2.tex, 05_synthesis.tex (23:49); main.pdf, main.log, arxiv-submission.zip, arxiv_metadata.txt (23:49:17), so the build follows the edits. main.log: "Output written on main.pdf (96 pages, 2039643 bytes).", no `!` lines, no undefined or multiply defined references, 17 overfull boxes (unchanged from round 36, so the longer tab:paradigms cells added none). The zip's 05_synthesis.tex contains "Recital~61" and its 02b_pol2.tex contains "persons affected by Annex~III".
- `python scripts/rate_certainty.py --check` (repository root): CHECK PASSED ("tab:keyfindings and tab:certchanges agree with the computed ratings"); now 0 moderate, 11 low, 4 very low; contested 2, 5, 11, 14, as stated in the paper.
- arxiv_metadata.txt: abstract 1914/1920 characters, same as 00_abstract.tex.

## Task 1: R36-1, R36-2

| Item | Status | Evidence |
|---|---|---|
| R36-1 Annex III point 8(a), Recital 61 (05 l.56) | FIXED | Text: "point 8(a) does list AI used in alternative dispute resolution, which may reach the adjudication of disputes under \art{10} where its outcomes bind the parties (Recital~61). So for the safety valve and welfare decisions they bear on T4 … by analogy". Annex III 8(a) covers systems assisting a judicial authority in researching and interpreting facts and law and applying the law to facts, "or to be used in a similar way in alternative dispute resolution". Recital 61 (EUR-Lex): systems used by ADR bodies "for those purposes" are high-risk when the outcomes of the proceedings produce legal effects for the parties; it also excludes purely ancillary administrative activities. "may reach" is properly hedged (whether NaturalDAO is an ADR body applying "law", Art. 6(3) derogation, Art. 2 scope all open). "bind the parties" is a slightly narrower paraphrase of "produce legal effects for the parties" (R37-2, nit). Art. 86(1) excludes only Annex III point 2, so 8(a) systems are within Art. 86; the sentence is consistent. Analogy now limited to safety valve and welfare decisions, as intended. |
| R36-2 tab:paradigms row (a) | FIXED | 02b l.87: "EU: none prescribed; for high-risk systems, automatic logging (Art.~12) and human oversight (Art.~14)"; "For high-risk systems, technical documentation and instructions (EU Art.~11, 13) and explanation to persons affected by Annex~III systems (Art.~86)". Matches Art. 11–14 (high-risk) and Art. 86(1) (Annex III except point 2). No new overfull box. |
| Consistency elsewhere | Consistent | 02b l.116 "by analogy where the system is not listed as high-risk" is conditional and so covers the 8(a) case; §1 l.53 and abstract l.8 ("set against EU law") neutral. |

**Do §7.1 and §8 need a mention that the AI Act may apply directly to adjudication?** §7.1: no. The adjudication row and the verdict are evidence verdicts (NS as judge on G4–G6 evidence) and make no legal claim; the per-person row's "legal reading" entry is a research need, not a pattern the adjudication row must copy. §8: not required for correctness ("close to what data-protection law requires where it applies" remains true), but now incomplete, because if 8(a) reaches \art{10}, Art. 14(4)(e) (ability to intervene or interrupt via a "stop" button) is a closer and possibly directly applicable counterpart of "a human who can suspend them" than GDPR Art. 22; and T4 option (a) is presented as text-preserving without noting it could then conflict with Art. 14. Raised as R37-1 (nit, optional).

## Task 2: fresh pass

Read in full: abstract, §1, §5, §6 (design, human review, trade-offs, tab:checklist), §7.1 table and verdict, "Beyond one specification", §8, statements; legal sentences in §2, §2b. Verdict wording (decide/detect; adjudication, ethical verification, per-person quantification, final blocks; detector functions incl. text-only anomaly detection; Chinese-construct extrapolation; low/very low; four contested; 8 October update reversed none) agrees across abstract, §1, §7.1, §8 and the certainty script output. Positionality, AI-use and pilot-protocol coincidence statements are present and consistent with §6 l.6–7. Tone and framing are appropriate for cs.CY; no arXiv moderation risk found beyond the known author-only items. No new major or minor problem found.

## Findings

**R37-1 [nit] Where \art{10} adjudication falls under Annex III point 8(a), T4 option (a) and §8 do not say that the AI Act's own oversight requirement would apply directly.**
- **Location:** 05_synthesis.tex l.41–42 (option (a) "keep non-intervention … preserves the text"); 08_conclusion.tex, "whether non-intervention should yield … close to what data-protection law requires where it applies".
- **Evidence:** Art. 14(4)(e) requires that natural persons overseeing a high-risk system be enabled to intervene in its operation or interrupt it; \art{9}(7) says human supervision "does not directly intervene". After R36-1, §5 l.56 concedes 8(a) "may reach" \art{10}.
- **Fix (optional):** 05 l.42 after "falls outside the detector role defined in \cref{sec:intro}": ", and if \art{10} adjudication is a high-risk system under Annex~III point 8(a) it would not meet Art.~14(4)(e)"; 08: "close to what data-protection law, and for adjudication possibly the AI Act, requires where it applies".

**R37-2 [nit] Recital 61 paraphrase.**
- **Location:** 05_synthesis.tex l.56 "where its outcomes bind the parties (Recital~61)".
- **Evidence:** Recital 61: high-risk "when the outcomes of the alternative dispute resolution proceedings produce legal effects for the parties"; "bind" is narrower than "produce legal effects".
- **Fix (optional):** "where its outcomes produce legal effects for the parties (Recital~61)".

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 0 | |
| Nit | 2 new, plus 5 carried | R37-1, R37-2; R17-2, R17-3, R21-1, R21-2, R21-3 |

R36-1: FIXED. R36-2: FIXED.

New major or minor problems remain: no
