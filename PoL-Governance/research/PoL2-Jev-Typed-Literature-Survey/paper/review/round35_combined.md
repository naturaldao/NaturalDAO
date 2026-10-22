# Round 35: combined review (fidelity, balance/positionality, method, consistency, legal precision, arXiv moderator)

Date: 2026-10-08. Scope: re-check of R34-1 against Regulation (EU) 2024/1689 (EUR-Lex OJ L 2024/1689: Art. 3(34), 3(39), 5(1)(c), 5(1)(f), Recital 44; Art. 14, 50(3), 86 and Annex III checked against the consolidated text); every other legal statement in the paper (AI Act Art. 5(1)(c), 11–14, 86, Annex III; GDPR Art. 22(1)–(4); DSA Art. 14–17, 20, 24; CAC Interim Measures Art. 2, 4, 14, 15, 17) read for paraphrase accuracy **and** for whether the paper applies a provision beyond its scope (the R34-1 class); fresh whole-paper pass of abstract, §1, §2b, §5, §6, §8, statements. Items resolved in REVIEW.md, AUDIT.md and rounds 12–34 are not re-raised; R17-2, R17-3, R21-1..3 are carried unchanged.

**Inputs**
- sections/02_background.tex, 05_synthesis.tex (23:40:45), main.pdf, main.log, arxiv-submission.zip, arxiv_metadata.txt (23:40:54–55). main.log: "Output written on main.pdf (96 pages, 2039056 bytes).", no `!` lines, no undefined or multiply defined references, 17 overfull boxes (unchanged).
- `python scripts/rate_certainty.py --check` (repository root): CHECK PASSED ("tab:keyfindings and tab:certchanges agree with the computed ratings").
- arxiv_metadata.txt abstract 1916/1920 characters.

## Task 1: R34-1 and the other legal statements

| Item | Status | Evidence |
|---|---|---|
| R34-1 Art. 5(1)(f) scope | FIXED (substance); basis stated too narrowly (R35-3, nit) | 05 l.55 and 02 l.57 now say the prohibition does not reach inference from text alone and that it bears on T1 "by analogy rather than application". Art. 3(39): emotion recognition system = "identifying or inferring emotions or intentions of natural persons on the basis of their biometric data"; Art. 3(34): biometric data = data from "specific technical processing" of physical, physiological or behavioural characteristics (facial images, dactyloscopic data) — message text is not such data. The conclusion is correct. But Art. 5(1)(f) itself reads "AI systems to infer emotions of a natural person in the areas of workplace and education institutions"; it does not use the defined term, so the limitation to biometric data follows from reading it with Art. 3(39), Recital 44 and the Commission's guidelines on prohibited practices (C(2025) 884), not from the definition alone as "because the Act defines…" implies. |
| Art. 50(3) | No mention needed | Art. 50(3) (deployers must inform persons exposed to an emotion recognition or biometric categorisation system) uses the defined term and so is also limited to biometric data; likewise Annex III point 1(c). Neither reaches text-only inference; adding them would only repeat the R34-1 point. |
| AI Act Art. 5(1)(c) (05 l.55, 02b l.116, 07 table) | Correct | Both limbs (unrelated contexts; unjustified or disproportionate) stated; 02b says per-person quantification "resembles" social scoring; 07 asks for "a legal reading", not a conclusion. |
| AI Act Art. 11, 12, 13, 14, 86, Annex III | Paraphrases correct; applicability over-stated (R35-1) | Paraphrases match the text (Art. 86: Annex III systems, legal or similarly significant effects, role of the system and main elements; point-2 exclusion and "adverse impact" qualifier omitted acceptably, as in round 21). But see R35-1 on whether a PoL2 deployment is high-risk at all. |
| GDPR Art. 22(1), (3) | Correct and applicable | "restricts" consistent with CJEU C-634/21 (prohibition in principle); 22(2)(a),(c) → 22(3) safeguards correctly stated. Art. 22(4) (special categories) not mentioned; not needed. |
| DSA Art. 14, 15, 16, 17, 17(3)(c), 20, 20(6), 24(5) | Correct | Addressees right (17 hosting; 20, 24(5) online platforms; 15 intermediaries). §5 calls them "close analogues", not applicable law — appropriate, since whether a standalone LLM safety valve is a hosting service is unsettled. |
| CAC Interim Measures Art. 2, 4, 4(1), 14(1), 14(2), 15, 17 | Correct | 14(1): stop generation/transmission, eliminate, rectify, report; 14(2): warning, restricting functions, suspension (termination omitted acceptably), records, report; 15: complaint mechanism, published procedure and time limits, feedback; 17: security assessment and algorithm filing for public-opinion/social-mobilisation services. "No article requires notice to the user, reasons or a record" for a 14(1) stop is correctly confined to "In the Measures". |

## Task 2: fresh pass

§1, §2b (table row (a)/(b), properties (i)–(v), comparison), §5 T1–T5, §6 elements 1–7 and trade-offs, §8 and the statements read in full. Thesis, verdict and abstract agree on detector/judge, the 8 October update and certainty; §8's "close to what data-protection law requires where it applies" is correctly hedged. Two consistency/legal-precision problems found (R35-1, R35-2), both of the R34-1 class (a legal parallel stated more strongly than its scope supports).

## Findings

**R35-1 [minor] §5 says the cited law "would apply to a deployment in the EU", but AI Act Arts. 14 and 86 reach only Annex III high-risk systems, and neither the safety valve nor NaturalDAO's welfare decisions is plainly such a system.**
- **Location:** 05_synthesis.tex l.54 ("law that would apply to a deployment in the EU already takes positions on several"), l.56 (Art. 14, Art. 86 "bearing on T4 and on the explanation duty of \art{9}(2)"); 02b_pol2.tex l.116 ("AI-only adjudication with non-intervention sits against the human-oversight … provisions of the AI Act (Art. 14)").
- **Evidence:** Art. 14 applies to high-risk systems; Art. 86(1) to decisions based on "a high-risk AI system listed in Annex III". Annex III lists no content-moderation or speech-filtering use, and its welfare entry, point 5(a), covers systems used "by public authorities or on behalf of public authorities" to evaluate eligibility for essential public assistance benefits — not a private DAO's welfare protocol. The paragraph states the "for high-risk systems" condition but not that a PoL2 deployment would usually not meet it, while its lead sentence asserts application. 02b l.115 ("on the systems they cover") partly scopes l.116, but §5 does not. GDPR Art. 22 is the one cited provision that would apply directly; DSA and Santa Clara are already called analogues. After R34-1 made T1 explicitly an analogy, T4's AI Act parallel is now the stronger-sounding claim with the weaker basis.
- **Fix:** 05 l.54: "law in the EU already takes positions on several, directly or by analogy"; l.56 add after Art. 86: "; these apply only to high-risk systems, and neither a speech filter nor a private organisation's welfare decisions is listed in Annex III (whose point 5(a) covers public-assistance decisions by or for public authorities), so they bear on T4 by analogy, whereas the GDPR applies wherever personal data are processed". Optionally 02b l.116 "the human-oversight provisions the AI Act sets for high-risk systems (Art. 14)".

**R35-2 [minor] The abstract calls all five tensions "tensions with EU AI, data and platform law", but §5 links law to only three of them, and T1 only by analogy.**
- **Location:** 00_abstract.tex l.8 and arxiv_metadata.txt ("Five tensions with EU AI, data and platform law follow: emotion recognition, binary verdicts, closed-model transparency, AI-only adjudication and per-person scoring.").
- **Evidence:** §1 contribution 3 says correctly "five tensions within the specification … which we compare with the EU AI Act, the GDPR, the DSA and content-moderation norms"; §5 defines T1–T5 as tensions *in the specification* and its regulatory paragraph cites law for T1 (by analogy, Art. 5(1)(f) not applicable), T4 and T5 (and the safety valve generally), none for T2 (binary verdicts) or T3 (closed-model transparency). The abstract therefore states a legal tension the body does not claim for T2 and T3 and that R34-1 withdrew for T1.
- **Fix (fits the 1920-character limit; −2 characters):** "Five tensions in the text follow, set against EU law: emotion recognition, …". Rebuild metadata.

**R35-3 [nit] The Art. 5(1)(f) scoping is attributed to Art. 3(39) alone.**
- **Location:** 05 l.55 ("because the Act defines an emotion recognition system as one that infers emotions from biometric data (Art.~3(39)), inference from text alone … falls outside the prohibition"); 02 l.57 ("a definition that does not reach inference from text alone").
- **Evidence:** Art. 5(1)(f) prohibits "AI systems to infer emotions of a natural person" in workplace and education; it does not use the defined term. The biometric limitation comes from reading it with Art. 3(39) and Recital 44, as the Commission's guidelines on prohibited practices (Feb. 2025, non-binding) do.
- **Fix:** "(Art.~5(1)(f), read with Art.~3(39) and Recital~44, as the Commission's guidelines on prohibited practices read it)".

## Counts

| Severity | Number | Findings |
|---|---|---|
| Major | 0 | |
| Minor | 2 | R35-1, R35-2 |
| Nit | 1 new, plus 5 carried | R35-3; R17-2, R17-3, R21-1, R21-2, R21-3 |

R34-1: FIXED.

New major or minor problems remain: yes
