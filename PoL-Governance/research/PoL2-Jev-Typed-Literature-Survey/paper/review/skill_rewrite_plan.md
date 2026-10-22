# Full rewrite with the sci-paper-writing skill (2026-10-11)

Method: Glasman-Deal distillation (Desktop/SKILL.md), Steps 0–5. Target articles: COMPL-AI (arXiv 2410.07959) and Policy-as-Prompt (arXiv 2502.18695, FAccT 2025). Audit: `review/check_invariants.py` against `Downloads/PoL2-Jev-v0.5.1-pre-skill-snapshot` — numbers, citation keys, clause numbers, macros, quotes and floats must not change unless listed below.

## Step 0. Intake
- Genre: research paper (policy and engineering analysis with a structured evidence assessment); arXiv cs.CY primary, cs.AI cross-list.
- Readers: interdisciplinary — AI-governance and FAccT readers, PoL2/NaturalDAO implementers, ML evaluators. Assume a reader who jumps to the Abstract, §5 answers, the verdict table or the Conclusion.

## Step 2. Magnetic south (judgement calls; the author can overrule)
- **Achievement (one verb: *assess*).** We assess whether typed decision models can perform the judgements the PoL2 safety valve and public-welfare protocol require, by deriving seven testable requirements from the clauses and assessing 163 studies and 7 grey sources against them.
- **Contribution.** (1) To knowledge: on the first weeks of evidence, typed models are supported as detectors under added conditions and not as judges; the failures are not shown to be specific to typed models. (2) To practice: a clause-to-requirement reading of a governance text, and a scripted, auditable certainty apparatus with a corrections table. (3) To PoL2: five tensions, a reference design and a function-by-function verdict.
- **Impact (as modest as the evidence allows).** Implementers should use hosted Jev only as a recorded, three-valued, locally calibrated detector; specification writers should make five choices explicit; the next study is a Chinese three-valued construct benchmark.
- **Paper type.** *New application* (an evidence assessment applied to a governance specification) with a policy recommendation. The Abstract, Discussion and Conclusion lead with the verdict and its certainty, then the transferable practices.
- Ranking of achievements: verdict > requirements reading > certainty apparatus > design.

## Step 3. Paragraph-function outline (one function per paragraph, entry sentence signals it)
**§1 Introduction (wide → narrow).** P1 importance: automated restriction is spreading; cost was the obstacle (present/present perfect). P2 the new technology: typed models remove the cost obstacle; define terms (past for release, present for definition). P3 the specification: PoL governance; what PoL2 asks of a machine (present). P4 gap: governance judgement depends on the judgement's definition; most texts do not state it; evidence is scattered (present). P5 the key distinction: detector vs judge, by who checks the output (present, definitional). P6 the present paper: RQ and three steps (present). P7 main results with value words and hedges (present for what the paper finds, past for studies). P8 contributions (numbered). P9 scope and delta to closest work (present).
**§2 Background.** 2.1 the technology (present facts). 2.2 related work mapped by problem: precursors, threats, bias, aggregation, calibration/abstention, evaluator bias, oversight failure, accountability (present perfect/past). 2.3 PoL2 among paradigms: comparison, five properties each with a cost, why studied (present).
**§3 Requirements.** 3.1 specification facts (present; quotes kept); why typed models are relevant (present). 3.2 how requirements were derived (past), two reading choices (present), table invitation.
**§4 Method.** Overview restating aim (present) → eligibility and search (past) → coding (past; rules present) → second coding and its limits (past) → appraisal and certainty (past; rules present) → who did what (past). Active "we" as in both targets.
**§5 Results.** Opening: revisit aim, how to read subsections, invite figure and table. Each G: one-line answer + tally → strongest supporting evidence with value words → limiting evidence → comparison with generative evaluators → "so what" for a safeguard. Across requirements: pooled answer → sensitivity → comparison → implication for design.
**§6 Implications.** Announce structure → tensions (each: text → evidence → options) → regulatory parallels → design (invite figure, elements, costs) → verdict (table, verdict paragraph separating evidence and precaution, what transfers).
**§7 Discussion.** Restate achievement → generality → certainty → interface not isolated → limitations → what would change it → open problems leading to the next study.
**§8 Conclusion.** Self-contained: what we did, what we found (evaluative), verdict, limits, what the text must decide, next step (present perfect for achievement).
**Abstract.** Background + problem → what we do → method → results (detector yes, judge no, comparison) → verdict with certainty → design/tensions → release. ≤1,920 chars.

## Step 5 checks to run
Terminology fixed: *typed decision models / typed models*, *generative evaluators*, *detector*, *judge*, *state of absence*, *insufficient information*, *safety valve*, *requirement* (G1–G7), *tension* (T1–T5), *added condition*. No synonym rotation. Style guide items 1–10 (no semicolon chains, formulaic contrasts, aphorisms, signposting, banned words).

## Outcome (2026-10-11)
- Step 1 profile of the two targets obtained (paragraphs 90–130 words, mean sentence 22–29 words, inline contributions, signposted section openers, abstract ~200 words). Adopted: inline First/Second/Finally contributions with a hedged novelty claim ("To our knowledge, the first assessment of typed decision models against the requirements of a governance specification" — author to confirm), section signposts in §2, §3, §6, §7, paragraph splits at function boundaries, a "so what for a safeguard" closing sentence per requirement in §5, a self-contained Conclusion with a present-perfect recap, a Method split into Eligibility/Corpus/Coding/Second coding/Appraisal/Certainty/Who did what.
- Not adopted (judgement calls): title kept as a question (options offered to the author); limitations kept in §7 Discussion rather than moved into the Conclusion; abstract kept at ~1,784 characters (longer than the targets) to keep every certainty and extrapolation hedge.
- AI statement revised to arXiv's policy (disclosure, AI not an author, full author responsibility; May 2026 one-strike rule on unchecked LLM output): names what was verified and how. Acknowledgements: Zhaohui Zhou (Derek.DAism) first.
- Checks: check_invariants against Downloads/PoL2-Jev-v0.5.1-pre-skill-snapshot shows no lost number or citation key; rate_certainty --check passed; build main 35 pp. / OA 27 pp., 0 errors / 0 undefined; arXiv clean-room compile 35 pp.; no placeholder strings in any section.

## Expanded target set (2026-10-11, user: "more targets, high level only")
Verified venues: BetterBench (Reuel et al., NeurIPS 2024 D&B, arXiv 2411.12990); Leakage and the reproducibility crisis in ML-based science (Kapoor & Narayanan, Patterns 4(9) 2023, arXiv 2207.07048); The Fallacy of AI Functionality (Raji et al., FAccT 2022, arXiv 2206.09511); Black-Box Access is Insufficient for Rigorous AI Audits (Casper et al., FAccT 2024, arXiv 2401.14446); AI auditing: The Broken Bus on the Road to AI Accountability (Birhane et al., SaTML 2024, arXiv 2401.14462); REFORMS (Kapoor et al., Science Advances 10(18) 2024, arXiv 2308.07832). Plus COMPL-AI and Policy-as-Prompt.
Applied where the six disagree with the two-paper model:
- separate Limitations section before the Conclusion (sec:limitations), opening with "Scope of the claims" (preprints only; reported, not reproduced; corpus a lower bound; one reading of PoL2);
- novelty stated as an absence ("no structured assessment … exists"), not "first";
- "What this assessment cannot establish" paragraph in the Discussion (necessary but not sufficient);
- regulatory analysis as its own subsection (sec:regulatory) with one run-in per instrument (AI Act, GDPR, DSA), each ending with a recommendation to a named actor using should/could;
- abstract ends with the released artefacts and their users.
Not applied: abstract cut to ≤200 words (would drop certainty and extrapolation hedges); claim-sentence subsection titles (the one-line italic answers already serve that function).

## Reference audit (2026-10-11, against arXiv's May 2026 one-strike rule)
All 178 cited keys checked against a registry: 91 arXiv entries (export API; every cited version exists, titles and author lists match), 23 Zenodo records (REST API), 40 DOIs (Crossref; arXiv DataCite DOIs checked on arXiv), 28 URL-only sources (laws on EUR-Lex/CAC, vendor docs, blogs, GitHub repos, PoL2 commit 5791ae3; ISO page blocks bots, standard exists). No fabricated reference. Fixed: arx03387 and arx06625 first-submitted dates (v2 date had been used; now 2026-10-02 and 2026-10-05); zen23032384 title (bib carried a shortened title; now the record's full title, also in data/zenodo_preprints.csv). PDFs scanned for placeholders, model meta-comments and "??": none.
Verification log moved out of the release; acknowledgement now "Derek.DAism (DD)" (EN and ZH).
