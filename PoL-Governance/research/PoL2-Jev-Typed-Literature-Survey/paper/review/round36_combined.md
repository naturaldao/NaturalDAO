# Round 36: combined review (fidelity, balance/positionality, method, consistency, legal precision, arXiv moderator)

Date: 2026-10-08. Scope: check of R35-1..R35-3 against Regulation (EU) 2024/1689 (EUR-Lex OJ L 2024/1689: Recitals 18, 44, 61; Art. 3(39), 5(1)(c), 5(1)(f), 6(1)–(3), 14(1), 86(1)–(3); Annex III points 1–8, in particular 5(a) and 8(a)) and GDPR Art. 22; every other legal statement (§2 l.57, §2b tab:paradigms rows (a), (b), (f) and l.112–129, §5 regulatory paragraph, §6 l.30–31, §7.1 tab:verdict and verdict, §7 l.115, §8) read for over-application; fresh pass of abstract, §1, §5, §7.1, §8. Items resolved in REVIEW.md, AUDIT.md and rounds 12–35 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/00_abstract.tex, 02b_pol2.tex, 05_synthesis.tex (23:45:19); main.pdf, main.log, arxiv-submission.zip, arxiv_metadata.txt (23:45:30), so the build follows the edits. main.log: "Output written on main.pdf (96 pages, 2039293 bytes).", no `!` lines, no undefined or multiply defined references, 17 overfull boxes (unchanged). The zip's 05_synthesis.tex contains the R35-1 text.
- `python scripts/rate_certainty.py --check` (repository root): CHECK PASSED ("tab:keyfindings and tab:certchanges agree with the computed ratings").
- arxiv_metadata.txt abstract 1914/1920 characters (recounted), identical in substance to 00_abstract.tex.

## Task 1: R35-1..R35-3 and the other legal statements

| Item | Status | Evidence |
|---|---|---|
| R35-1 Art. 14/86 limited to high-risk; T4 by analogy | FIXED for the speech filter and welfare decisions; incomplete for dispute adjudication (R36-1) | 05 l.54 "directly or by analogy"; l.56 "These apply only to high-risk systems, and neither a speech filter nor a private organisation's welfare decisions is listed in Annex III, whose point 5(a) covers decisions on public assistance taken by or for public authorities". Art. 6(2): Annex III systems are high-risk; Art. 14(1) addresses high-risk systems; Art. 86(1): Annex III systems except point 2. Annex III point 5(a): systems used "by public authorities or on behalf of public authorities" to evaluate eligibility for essential public assistance benefits — paraphrase acceptable. No Annex III point lists content moderation or speech filtering (point 8(b) is election influence). But T4 also covers \art{10} dispute adjudication (05 l.35), and Annex III point 8(a) lists AI used "in a similar way in alternative dispute resolution" (see R36-1). 02b l.116 "by analogy where the system is not listed as high-risk" is correctly conditional. |
| R35-1 GDPR clause | Acceptable | "the GDPR applies wherever personal data are processed": in the sentence's EU context (l.54 "law in the EU") this is a fair shorthand for Art. 2–3; Art. 22 itself is then stated with its solely-automated and significant-effects conditions. |
| R35-2 abstract | FIXED | 00_abstract.tex l.9 and metadata: "Five tensions in the text follow, set against EU law"; no longer claims a legal tension for T2/T3. 1914 characters. |
| R35-3 Recital 44 | FIXED | 05 l.55 "(Art.~3(39); Recital~44)". Recital 44 itself refers to systems inferring emotions "on the basis of their biometric data" and Recital 18 elaborates the biometric definition, so citing Recital 44 supports the scoping. Art. 5(1)(f) ("AI systems to infer emotions") does not use the defined term; reading it with Art. 3(39) and Recital 44 is the standard reading. 02 l.57 consistent. |
| Art. 5(1)(c) (05 l.55, 02b l.116, 07 per-person row) | Correct | Applies to any AI system, not only high-risk; §5 "bearing on T5", 02b "resembles", 07 "a legal reading" — not over-applied. |
| tab:paradigms row (a) | Minor wording gap (R36-2, nit) | Oversight column scoped ("Human oversight required for high-risk systems (EU Art.~14)"); intercept column "automatic logging (Art.~12), human oversight (Art.~14)" and transparency column "explanation to affected persons (Art.~86)" are unscoped, though Art. 11–14 bind high-risk systems only and Art. 86 Annex III systems only. Row describes the paradigm, not PoL2, so this is a nit. |
| Row (b), 02b l.112, l.121–129, 07 l.115 (DSA, CAC) | Correct | Unchanged since round 35; addressees and paraphrases verified there. |
| §6 l.31, §7.1 tab:verdict and verdict, §8 | Correct | §6 cites DSA/Santa Clara as norms for notice/reasons/appeal, not as applicable law; tab:verdict asks for "a legal reading against social-scoring prohibitions"; §8 "close to what data-protection law requires where it applies" correctly hedged. |

## Task 2: fresh pass

Abstract, §1 contributions, §5 T1–T5 and regulatory paragraph, §7.1 table and verdict, §8 read in full. Verdict wording (decide/detect; dispute adjudication, ethical verification, per-person quantification, final blocks; detector functions; Chinese-construct extrapolation; low/very low certainty; 8 October update) agrees across abstract, §7.1 and §8. The only new problem found is the R35-1 class again (R36-1).

## Findings

**R36-1 [minor] §5 says the AI Act's Art. 14 and 86 bear on T4 only by analogy, but T4 includes AI adjudication of disputes (\art{10}), and Annex III point 8(a) lists AI used in alternative dispute resolution as high-risk.**
- **Location:** 05_synthesis.tex l.56 ("neither a speech filter nor a private organisation's welfare decisions is listed in Annex~III … so they bear on T4 and on the explanation duty of \art{9}(2) by analogy"); T4 defined at l.35 to include \art{10} ("gives disputes to AI fact-finding and ethical assessment").
- **Evidence:** Annex III point 8(a): AI systems intended to assist a judicial authority in researching and interpreting facts and law and applying the law to facts, "or to be used in a similar way in alternative dispute resolution". Recital 61: AI systems used by alternative dispute resolution bodies for these purposes are high-risk "when the outcomes" of the proceedings produce legal effects for the parties. NaturalDAO's adjudication of "all disputes" (\art{10}) is AI fact-finding and assessment whose result decides the dispute; whether it is ADR with legal effects for the parties is open, but it is not plainly outside Annex III, so "by analogy" overstates the distance for the adjudication arm of T4 (the opposite direction from R35-1, now under-applying). The welfare-decision and speech-filter statements remain correct.
- **Fix:** 05 l.56, after "taken by or for public authorities": "; point 8(a) does list AI used in alternative dispute resolution, which may reach the adjudication of disputes under \art{10} where its outcomes bind the parties (Recital~61)", and change "so they bear on T4" to "so for the safety valve and welfare decisions they bear on T4". Optionally 02b l.116 unchanged (already conditional).

**R36-2 [nit] tab:paradigms row (a) lists Art. 12, 14 and 86 as EU features without saying they attach only to high-risk (Art. 86: Annex III) systems in two of three cells.**
- **Location:** 02b_pol2.tex l.87, intercept column ("EU: none prescribed; automatic logging (Art.~12), human oversight (Art.~14)") and transparency column ("Technical documentation and instructions (EU Art.~11, 13); explanation to affected persons (Art.~86)").
- **Evidence:** Art. 11–14 are requirements for high-risk systems; Art. 86(1) is limited to Annex III systems (except point 2). The oversight column of the same row already says "for high-risk systems".
- **Fix:** "EU: none prescribed; for high-risk systems, automatic logging (Art.~12) and human oversight (Art.~14)"; "for high-risk systems, technical documentation and instructions (EU Art.~11, 13) and explanation to persons affected by Annex~III systems (Art.~86)". Check column width / overfull count after rebuild.

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 1 | R36-1 |
| Nit | 1 new, plus 5 carried | R36-2; R17-2, R17-3, R21-1, R21-2, R21-3 |

R35-1: FIXED for speech filter and welfare decisions (adjudication arm: R36-1). R35-2: FIXED. R35-3: FIXED.

New major or minor problems remain: yes
