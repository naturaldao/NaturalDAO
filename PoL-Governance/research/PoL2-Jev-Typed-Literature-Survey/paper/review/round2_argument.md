# Round 2 — argument / method / arXiv-moderation lens (v0.3)

Reviewer: independent senior reviewer (FAccT/AIES standard) and, separately, acting arXiv moderator. Date 2026-10-04. I did not edit any file except this one.

Inputs I read:
- `main.pdf`, read in order via `pdftotext -layout` (64 pp.). Pages 8, 22 and 29 were also rendered to check the tables.
- `main.tex` and all `sections/*.tex`.
- `arxiv_metadata.txt`.
- `review/round1_argument.md` and `review/round1_arxiv-pol2.md` (Part 1).
- `data/evidence_coding.csv`, `data/quality_appraisal.csv` and `data/coder_agreement.csv`, used to recompute the tallies and κ.
- The arXiv blog post of 31 Oct 2025, fetched today. Relevant wording:
  - review/survey articles or position papers without documented peer review "will be likely to be rejected";
  - the FAQ answers "I have a scientific paper studying the impact of science and technology in society. Can I submit this to arXiv without peer review?" with "Yes, arXiv has always released these types of scientific papers, for example in cs.CY or physics.soc-ph";
  - the problem it targets is submissions that are "little more than annotated bibliographies, with no substantial discussion of open research issues".

Numbers I recomputed from the data (all match the paper unless noted):
- **Tallied pairs.** 161 pairs from 85 documents: S 17, Q 98, N 46.
- **N rate by source.** arXiv 23/107 (21%); Zenodo 19/44 (43%); grey 3/8; alphaXiv 1/2.
- **Sensitivity without Zenodo** (not reported in the paper): S 14, Q 76, N 27 of 117 (N 23%, against 29% overall).
- **κ.** First coder Q 23 / N 4 / S 3, second coder Q 19 / N 6 / S 5. Agreement 26/30 gives p_o 0.867, p_e 0.529, κ 0.717, which matches the reported 0.72. All 4 disagreements are first-coder Q. With n = 30 the 95% CI for κ is roughly ±0.25 and is not reported.
- **Quality appraisal (96 studies).** higher 50, lower 42, moderate 4. Independence was recorded as "author-built system" for 26 studies, and none were vendor-affiliated. Independence plays no part in the rating rule: author-built studies split 13 higher / 11 lower / 2 moderate.
- **Public repository.** `naturaldao/NaturalDAO@main …/data` still lists only 6 entries. `evidence_coding.csv`, `quality_appraisal.csv`, `coder_agreement.csv` and `zenodo_preprints.csv` are not public.

---

## Resolution checklist — round-1 MAJOR issues

### round1_argument.md

| ID | Issue | Status | Note |
|---|---|---|---|
| NEW-arg-1 | "Not a judge" framed as typed-specific | RESOLVED | Thesis is now comparative (abstract, §1 Thesis, §4.8, §8). It now overshoots in the other direction (R2-arg-5). |
| NEW-arg-2 | Direction-based weighting | RESOLVED | The rule was removed. Synthesis is by requirement, with a quality subset and a certainty rating. |
| NEW-arg-3 | Emotion "least reliable" superlative | RESOLVED | T1 now says "thin and mixed", cites the sentiment counter-evidence and gives the charitable reading. |
| NEW-arg-4 | 96% caveat dropped in headline places | PARTLY | Caveat is in §4.6, T4 and Table 2. Abstract and §1 Thesis still say "peer evaluators repeat their most confident errors" without the selection or rubric-grading qualifier (R2-arg-15). |
| NEW-arg-5 | Human end-point asserted as better | RESOLVED | T4 says it is untested. The design still treats it as settled, and no revision condition exists for it (R2-arg-10). |
| NEW-arg-6 | Single-study generalisations | RESOLVED | Two studies now support the option-name claim, and Table 4 rates certainty. The "over-confident where people disagree" claim is no longer in the abstract or conclusion. |
| NEW-arg-7 | Omitted positive evidence (rotation robustness, Chinese routing) | RESOLVED | Both are now in §4.3. |
| NEW-arg-12 | No quality appraisal / certainty | RESOLVED (with method concerns) | §3.6, Table 2 and Table 4 added. The rule ignores independence and the GRADE starting point is non-standard (R2-arg-6). |
| NEW-arg-13 | Asymmetric codebook | PARTLY | Codebook v3 is more symmetric and coded for detector use. "Added condition" still pushes successes to Q, while attack or perturbation conditions push failures straight to N; S remains rare (17/161) (R2-arg-9). |
| NEW-arg-14 | Who did what (human vs AI) | RESOLVED in body; NOT in abstract | §3.7 is candid. The abstract's "blind second coder" implies a human (R2-arg-3). |
| NEW-arg-15 | Eligibility and flow | RESOLVED | Window, operational definition, grey-literature status and reconciled counts (79 + 27 + 1 = 107) are all present. Willison has been moved to context. |
| NEW-arg-18 | Detector/judge definition applied inconsistently | PARTLY | §1 definition and element 5 are now aligned. T4 option (a) and the conclusion's wording reopen the gap, and "repair" is undefined (R2-arg-2). |
| NEW-arg-19 | Falsification asymmetric / non-operational | PARTLY | Now quantified (5%, 0.75, 80%, 64 queries). The evidence standard is still asymmetric, and there is no condition for the human-end recommendation (R2-arg-10). |
| NEW-arg-23 | Scope statement inaccurate | RESOLVED | §1 Scope now says §5 identifies tensions and offers options, including at least one that preserves the text. |
| NEW-arg-27 | Missing literatures | RESOLVED | §2.3 is now organised by theme, with moderation, emotion recognition, annotator disagreement, Chinese resources, deferral, due process, DAOs and social scoring. Each §4 subsection has a "Relation to prior work" paragraph. |
| NEW-arg-28 | §4 structure and length | PARTLY | Answer boxes and the Appendix B evidence table were added. §4 is still about 5,800 words, against the ≤4,500 requested (R2-arg-14). |

### round1_arxiv-pol2.md (Part 1)

| ID | Issue | Status | Note |
|---|---|---|---|
| NEW-arx-1 | Self-described survey | PARTLY | "Survey" is gone from the title, abstract and headings, and the research question leads. The PRISMA flow, PRISMA checklist, vote-count bars and a 5,800-word evidence section still signal "systematic review" to a moderator (R2-arg-4). |
| NEW-arx-2 | Abstract lacks societal and policy content | RESOLVED | Abstract opens with speech, welfare and per-person assessment, and names the EU AI Act, GDPR and DSA. |
| NEW-arx-6 | Author-name syntax | RESOLVED | "Shentao Yan" is used in the metadata, the PDF and pdfinfo. |
| (minor) NEW-arx-3 | Project-memo voice | RESOLVED, with residue | No ★ or "team" device remains. A few promotional sentences about PoL2 and the version-history apparatus remain (R2-arg-12, R2-arg-16). |
| (minor) NEW-arx-7 | Data not public | NOT | Still not pushed (R2-arg-13). |
| (nit) NEW-arx-10/11 | `\typeout` placement, PDF metadata | RESOLVED | — |

---

## Findings

### R2-arg-1 [major]
- **Location:** sections/00_abstract.tex ("a preregistered study accepted their low-risk verdicts safely when an independently built rule agreed"); 01_introduction.tex Thesis ("can be accepted safely"); 06_design.tex element 3 ("a differently built rule made acceptance safe"); 04_evidence.tex G6 answer box ("saved most of the cost without loss").
- **Problem:** This is the single positive headline result for detector use, and it is stated without qualification. The paper's own evidence and rating say otherwise:
  - §4.2 reports that on the look-alike set "21 of the 76 windows that an agreement gate accepted as benign were attacks".
  - §4.6 says "look-alike attacks still passed".
  - The data are a simulated water network.
  - Table 4 rates the claim "Acceptance on agreement with an independently built judge is safe" as **very low** ("disguised attacks leaked").

  A very-low-certainty claim is presented in the abstract as an established fact ("safely"), and the word "safe" is contradicted by the study's own adversarial result.
- **Why it matters:** This breaks "every conclusion follows with the stated certainty". It is also the claim most likely to be quoted.
- **Suggested fix:**
  - Abstract: "…and in one preregistered study on simulated network data, accepting their low-risk verdicts only when an independently built rule agreed was non-inferior to a frontier LLM, although disguised attacks still passed."
  - §1 Thesis: replace "can be accepted safely" with "were accepted without loss of accuracy relative to a frontier LLM on simulated data, though disguised attacks still passed".
  - Element 3: replace "made acceptance safe" with "made acceptance non-inferior on benign drift".
  - Table 4 claim text: "…is non-inferior on benign data", not "is safe".

### R2-arg-2 [major]
- **Location:**
  - 05_synthesis.tex T4 option (a);
  - 06_design.tex elements 5–6 and Figure 7;
  - 00_abstract.tex ("consequential decisions end with a person");
  - 08_conclusion.tex ¶1 ("human review of confident decisions") and ¶2 ("whether non-intervention should yield … the text has yet to make");
  - 01_introduction.tex definition.
- **Problem:** The detector/judge definition from §1 is now applied correctly in element 5. Three places still disagree with it:
  1. **T4 option (a) keeps an automated judge.** It keeps non-intervention and escalates to "independently built judges rather than peers", with only a random audit afterwards. Under the §1 definition, consequential outcomes would then be decided without contemporaneous human confirmation, which is exactly what the thesis says the evidence does not support. Yet option (a) is offered as a legitimate, text-preserving choice, while §6 silently adopts option (b) and the abstract states (b) as the design. The reader cannot tell whether the paper's own evidence rules option (a) out.
  2. **"Repair" is undefined.** Element 5 permits automatic *repair*. If repair edits or truncates a person's message, it restricts speech without a time bound and cannot be "fully reversed", so under §1 it is a judge act. If it only means truncating PAI's own output (§4.3.3.1), say so.
  3. **Conclusion ¶1 says "human review of confident decisions",** but the design has humans review a *random sample* of confident decisions plus unresolved escalations. Element 6 also says reviewers see "all unresolved escalations": escalations that the stronger reasoning model "resolves" into a block are covered by element 5's person-confirmation rule, but this should be stated.
- **Why it matters:** The thesis is defined by this distinction. Offering a text-preserving option that the thesis itself argues against, without saying so, is the most visible remaining inconsistency.
- **Suggested fix:**
  - Add to T4 after the options: "Option (a) leaves consequential decisions with automated components and so falls outside the detector role defined in Section 1; the reference design in Section 6 implements option (b). We list (a) because it preserves the text, not because the evidence supports it."
  - Element 5: "…automatic allow, automatic repair of the AI system's own output (truncation under §4.3.3.1, never editing a person's message), and a hold…". Alternatively, make any repair of a person's content subject to the same 24-hour and person-confirmation rule.
  - Conclusion ¶1: replace "human review of confident decisions" with "person-confirmed blocks, and a random human audit of confident automatic decisions".
  - Element 6: "Reviewers see every escalation that would end in a block, every unresolved escalation, and a random sample…".

### R2-arg-3 [major]
- **Location:** 00_abstract.tex ("blind second coder on a sample, κ = 0.72"); 01_introduction.tex contribution 2 ("a sample is double-coded blind"); 03_method.tex §3.5 Agreement and §3.7; D_corrections.tex ("five independent review passes").
- **Problem:** The disclosure in §3.7 and the Limitations section is honest. The abstract and contributions list are not:
  - A reader of the abstract will assume a human second coder. In fact both coders were AI agents. §3.7 says "two independent AI coders", and the AI-use statement names the same vendor (Claude), so the coders were very likely the same model family. Shared priors inflate agreement, so κ = 0.72 is an upper bound on codebook reproducibility, not a measure of inter-human reliability.
  - κ is reported without a CI. With n = 30 it is roughly ±0.25.
  - The sample is Q-heavy: the first coder gave Q to 23/30. It therefore says little about the S/N boundary, which is the one that matters.
  - §3.7 says AI agents "proposed and applied the codes" and that the author "is responsible for every judgement". It does not say whether the author read or checked any codes, quality ratings or certainty ratings, or what share. FAccT reviewers will ask exactly this.
  - "Independent review passes" in Appendix D does not say that these passes were AI agents.
- **Why it matters:** Under FAccT/AIES norms on AI-assisted research, the human-vs-AI split must be visible wherever reliability is claimed. The abstract claims reliability.
- **Suggested fix:**
  - Abstract: "…coded with a symmetric codebook by AI agents under the author's direction (a second, blind AI coder agreed on 26 of 30 sampled pairs, κ = 0.72)…".
  - Contribution 2: "…a random sample is double-coded blind by a second AI coder".
  - §3.5: add the κ 95% CI, the marginal distributions of the sample, and the model and version of each coder (and whether they were the same).
  - §3.7: add one sentence such as "The author read every S and N code and every certainty rating and changed k of them; Q codes and quality ratings were spot-checked (m of n)". Use whatever is true; if the author checked none, say so.
  - Appendix D: "five review passes by AI agents".
  - Ideally, have one human code the same 30 pairs and report human–AI κ. This is a few hours' work and would remove the main reliability objection.

### R2-arg-4 [major — arXiv]
- **Location:** Overall structure; 03_method.tex ¶1 ("We follow PRISMA 2020 … Cochrane rapid-review guidance"); Figure 2; Appendix E PRISMA table (item "Title, abstract (1–2): Title; abstract"); §4 (about 5,800 words, about 36% of the body).
- **Problem:** A moderator reading v0.3 will see a real research question and genuinely original components:
  - the clause-to-requirement derivation;
  - the coded and certainty-rated assessment with released data;
  - the five-tension analysis mapped to specific Articles of the EU AI Act, GDPR and DSA;
  - a reference design with falsifiable pass criteria.

  This is far from the "annotated bibliography" the policy targets, and cs.CY primary is defensible: the question is about automated speech restriction, welfare adjudication and social scoring. However, the paper's most visible apparatus is that of a systematic review: a PRISMA flow figure on p. 10, a PRISMA 2020 checklist, vote-count bars, and an evidence section longer than the policy and design sections combined (about 5,800 words against about 3,400). The PRISMA checklist also claims item 1 is met ("Title"), but PRISMA item 1 requires the title to identify the report as a systematic review, which this title deliberately does not. That is both inaccurate and a pointer for a moderator. A moderator who skims the method and section headings could still classify the paper as a review in research-paper form.
- **Why it matters:** The blog FAQ exempts "scientific paper[s] studying the impact of science and technology in society", but moderators judge content and proportion. The safest reading is a policy-analysis paper whose evidence assessment is its method.
- **Suggested fix** (no new work needed):
  1. Add one framing sentence at the end of §1 Contributions: "The evidence assessment (contribution 2) is the method by which the policy questions are answered; we do not attempt a general review of typed decision models, and studies are discussed only insofar as they bear on G1–G7."
  2. Move Figure 2 (the PRISMA flow) and the selection details to Appendix E, and keep a 4–5 sentence selection summary plus Figure 1 in §3.
  3. Shorten §4 to ≤4,500 words (see R2-arg-14), so that §5–§6 together are at least as long as §4.
  4. Fix the PRISMA item-1 row: "Not followed by design: the paper is a policy analysis; its evidence component is identified as a structured rapid evidence assessment in Section 3."
  5. Consider cs.AI as the only cross-list (drop cs.CL). The content is not computational linguistics, and each cross-list puts the paper in front of another CS moderator applying the review rule.
  6. In the arXiv Comments field, add a short neutral descriptor, e.g. "Policy analysis with a documented evidence assessment."
- **Moderator verdict on framing honesty:** The title is honest: it is a question answered by a clause-level analysis. The abstract is honest about the corpus and certainty, apart from R2-arg-1 and R2-arg-3. The tone is mostly neutral (see R2-arg-12).

### R2-arg-5 [major]
- **Location:** 00_abstract.tex ("so the conclusion concerns automated judges generally"); 01_introduction.tex Thesis ("speaks against automated judges in general"); 08_conclusion.tex ("no automated component tested so far should serve as the judge"); 07 "What would change" ("until then it applies to automated judges generally").
- **Problem:** The round-1 fix overshoots in the other direction.
  - Only 14 of the 46 N pairs had a generative comparator (32/46 had none, §4.8).
  - The comparators were mostly low-cost or flash-tier evaluators, small open models, or the generative evaluators in the injection and option-swap studies.
  - The two stronger automated end-points in the corpus are a GPT-6 reasoning cascade and an independently built rule tree. These are exactly the ones the paper reports as working (G6), and neither was tested against judge-grade criteria such as option swaps, inserted opinions or the PoL2 construct.
  - The evidence therefore supports "the failures are not specific to typed models; the generative evaluators tested alongside them shared most of them". It does not support "automated judges generally", nor "no automated component tested so far": a GPT-6 judge was tested and was not shown to fail the judge criteria. The certainty for this claim is "low" in Table 4, while the abstract states it as an implication.
- **Why it matters:** This is a cross-system generalisation that the comparator set cannot carry. A reader from the LLM-evaluation community will object.
- **Suggested fix:**
  - Abstract: "Where generative evaluators were tested alongside, they shared most of these failures, so the evidence does not single out typed models; certainty is low throughout."
  - Conclusion: "…why none of the typed models, and none of the low-cost generative evaluators tested alongside them, should serve as the judge…".
  - §7: "…until then it is not specific to typed models."

### R2-arg-6 [major — method]
- **Location:** 03_method.tex §3.6; E_codebook.tex "Quality appraisal"; Table 2 (04) and Table 4 (07).
- **Problem:**
  1. **Independence is recorded but unused.** The rating rule uses only design and reporting. "Author-built system" studies (26 of 96) are rated higher as often as independent ones (13/26 against 37/70). "What we read" is constant (all full text) and therefore not an appraisal item.
  2. **The rule is effectively binary.** Only 4 of 96 studies are "moderate", so labelling day-old, single-author, unrefereed preprints "higher quality" in 50 of 96 cases overstates what the label means.
  3. **The GRADE starting point is non-standard.** "Unrefereed preprints start at low" is not GRADE: GRADE starts from study design, and publication status belongs under risk of bias or publication bias. This adaptation needs a citation or a justification.
  4. **The rules are applied unevenly.**
     - The G2 claim (nine N codes, seven from higher-quality, independent studies, consistent direction) meets the paper's own criterion for raising to moderate but is held at low without explanation.
     - Table 2 rates "Escalation … or acceptance on agreement with an independent rule … without loss" as **low**, while Table 4 rates the component claim "Acceptance on agreement … is safe" as **very low** from the same sources.
     - Table 2 rates "Errors concentrate in sub-types" very low from two higher-quality studies, without stating which downgrade rule applied.
- **Why it matters:** The certainty ratings carry the sentence "certainty is low throughout". A methods reviewer will check whether they were assigned by a rule or by impression.
- **Suggested fix:**
  - Make independence a rating input, e.g. "higher requires preregistered/held-out design, sizes with intervals, *and* evaluation of a system the authors did not build". Report the counts that result.
  - Rename the levels "stronger / weaker design" rather than "higher / lower quality".
  - Justify the starting point with one sentence and a citation to a preprint-adapted GRADE approach, or start from design as GRADE does and downgrade one level for lack of peer review.
  - Merge Tables 2 and 4 into one table (see R2-arg-14) with a column "rule applied" (e.g. "single study → very low"; "consistent ≥3 independent higher → could rise to moderate; held at low because …"). That makes every rating reproducible.

### R2-arg-7 [minor]
- **Location:** 00_abstract.tex ("assess them against 107 studies and 7 grey sources"); 01 contribution 2.
- **Problem:** Only 85 sources (including grey) enter the tallies. The 25 "background" arXiv papers are, by §3.5, "not coded", and 11 further items are context. "Assess against 107 studies" overstates the evidence base by roughly a quarter.
- **Suggested fix:** "…against a corpus of 107 studies and 7 grey sources from its first seventeen days, of which 85 bear on the requirements and are coded…". Make the same change in contribution 2.

### R2-arg-8 [minor]
- **Location:** 07_discussion.tex Limitations; 04 §4.8.
- **Problem:** The paper reports that Zenodo pairs are negative twice as often as arXiv pairs (19/44 against 23/107). It then reassures the reader with the "higher-quality" subset, which is a different sensitivity analysis. Round-1 NEW-arg-17 asked for the without-Zenodo analysis, which is trivial to compute: S 14, Q 76, N 27 of 117 (N 23% against 29%).
- **Suggested fix:** Add to §4.8: "Excluding Zenodo records, the codes are 14 S, 76 Q and 27 N of 117 pairs; no requirement changes direction (check G3, where 8 of 24 pairs are Zenodo)." Verify the per-requirement claim before writing it.

### R2-arg-9 [minor]
- **Location:** 03_method.tex §3.5; E_codebook.tex S/Q/N definitions.
- **Problem:** The codebook is more symmetric than v0.2 but still not fully symmetric. A success that needed an "added condition" (local threshold, recalibration, language restriction) becomes Q. A failure that needed an added condition (an optimised adaptive attack, an adversarially selected item set such as the 96% study, a definition swap) is coded N. The codebook does not say which conditions count as the *test* of a requirement (attack for G2, perturbation for G3) and which are *added* to it. Result: S = 17/161.

  The synthesis is also a vote count of direction codes. If used, it should follow SWiM guidance (Campbell et al. 2020, BMJ) and say why effect-direction counting was chosen.
- **Suggested fix:**
  - Add a decision rule: "(iv) conditions that constitute the requirement's test (adversarial content for G2, name/order/language perturbation for G3, adversarially selected items for G6) are not added conditions; a failure that occurs only under an added condition not part of the test is coded Q."
  - Cite SWiM in §3.5 and in PRISMA items 12–13.

### R2-arg-10 [minor]
- **Location:** 07_discussion.tex "What would change the conclusion".
- **Problem:** The criteria are now operational, but two asymmetries remain:
  - **Evidence standard.** Revising "not a judge" requires a preregistered study plus independent replication, or two independent studies. Revising "detector" has no stated evidence standard, so a single study appears to suffice. That may be a defensible precaution, but it should be stated and justified.
  - **No revision condition for the recommendation that consequential decisions end with a person.** Per T4 that recommendation is untested, and criterion (iv) uses human reviewers as the benchmark without testing them.
- **Suggested fix:**
  - Add: "We apply the same evidence standard to both halves." If you do not, add: "We require more evidence to relax a safeguard than to add one, because the costs of error are asymmetric."
  - Add: "We would revise the recommendation that consequential decisions end with a person if, on the same benchmark, trained reviewers agreed with the independent panel less well than the gated detector ensemble, or changed their verdict toward the model's displayed verdict in more than a pre-set share of audited cases."

### R2-arg-11 [minor]
- **Location:** 01_introduction.tex ("We use *judge* in this sense only … we write LLM evaluators"); 04 G6 answer box ("an independently built judge confirms"); 05 T4 ("escalate to independently built judges"); Table 4 ("independently built judge"); Figure 5 axis labels ("LLM judges repeating Jev's…", "best single judge").
- **Problem:** The paper declares a technical meaning for "judge", namely an automated component that determines consequential outcomes without human confirmation. It then uses the same word for a rule tree, for escalation targets and in a figure. A careful reader will read "independently built judge" as endorsing an automated judge, which the thesis rejects.
- **Suggested fix:**
  - Replace with "independently built rule" or "independently built checker" in the G6 box, T4 and Table 4.
  - Relabel Figure 5: "LLM evaluators repeating Jev's most confident errors" and "best single evaluator". Regenerate the figure from its script.

### R2-arg-12 [minor — tone]
- **Location:** 07_discussion.tex ¶1 ("the answers here transfer"; "exactly the safeguards the evidence calls for"); 08_conclusion.tex ¶2 ("several of the framework's own commitments are exactly the safeguards the evidence calls for").
- **Problem:** The paper's tone is now largely neutral. These two sentences praise the case object in strong terms, and the author is a contributor to that object. The evidence is low or very low certainty and does not show that PoL2's concepts (the state of absence, the not-moral-labels warning) *are* the right safeguards. It shows that three-valued questions and neutral option names help. "The answers here transfer" generalises beyond the case without evidence.
- **Suggested fix:**
  - §7: "…and, with the caveats on certainty above, the same design conclusions are likely to apply." Also: "…the state of absence, the warning that love and hate are not moral labels, and the distinction between persons and behaviours are consistent with what the evidence recommends."
  - §8 ¶2: "…several of the framework's own commitments are consistent with what the evidence recommends: …".

### R2-arg-13 [minor — submission blocker]
- **Location:** 09_statements.tex Data and code availability; arxiv_metadata.txt Comments.
- **Problem:**
  - **Data statement is currently false.** The statement lists `evidence_coding.csv`, `quality_appraisal.csv`, `coder_agreement.csv`, `zenodo_preprints.csv`, scripts, logs and LaTeX sources as released. On `naturaldao/NaturalDAO@main` (checked today) the data directory still has only 6 entries, and none of these files are there. The statement is false until pushed.
  - **Unpinned link.** The Comments field links to `main` rather than a commit or tag.
  - **Table count is wrong.** "4 tables" is incorrect: the PDF has Tables 1–11 (4 in the body, 7 in the appendices).
- **Suggested fix:** Push the files. Pin the link to a tag such as `v0.3-arxiv` or a commit SHA in both the statement and the Comments field. Change the Comments to "64 pages, 7 figures, 11 tables (4 in the main text)" or simply "64 pages, 7 figures".

### R2-arg-14 [minor — readability]
- **Location:** §4 (about 5,800 words), §5, §6, §7 ¶1, §8; Tables 2 and 4.
- **Problem:** The answer boxes help a great deal: each requirement can now be read in 60 words, and they are the best change in v0.3. Redundancy remains:
  - The G4 evidence list (option names, non-additive probabilities, rare "none", conflict/ignorance band, sufficiency question) appears in §4.3, §4.4, T2, element 3, checklist items 4–6 and the conclusion.
  - The 96% result appears in §4.6, Table 2, T4, element 3, element 6, checklist item 10 and Table 4.
  - Tables 2 and 4 are two certainty tables with overlapping, slightly differently worded claims and, in one case, different ratings (R2-arg-6).
  - §7 "Beyond one specification" restates the conclusion.
  - §4 still narrates many secondary numbers (CIs, n's) that are already in Appendix B and the CSV.
- **Suggested fix:**
  - Merge Tables 2 and 4 into one "Key findings and certainty" table at the end of §4, and have §7 and §8 point to it.
  - In T1–T5, cite the evidence by pointer ("Section 4.4; Table 2 rows 9–11") rather than re-listing it.
  - Cut §4 by about 1,300 words, mainly by:
    - (a) dropping secondary numbers where the answer box and figure carry the point (e.g. the KITE coverage details, the census percentages, the TF-IDF comparison);
    - (b) shortening "Where the evidence is not text" to two sentences;
    - (c) folding §4.7 "Cost, adoption and dependence" into §2.1.
  - Delete the first two sentences of §7 ¶1, or move the "where the text already contains the remedy" point there and out of §8.

### R2-arg-15 [minor]
- **Location:** 00_abstract.tex; 01_introduction.tex Thesis ("peer evaluators repeat their most confident errors").
- **Problem:** The upper-bound and selection caveat, and the fact that the setting is rubric grading by three flash-tier evaluators, are missing in the two places most readers see. This is the residual of round-1 NEW-arg-4.
- **Suggested fix:** "…and, on rubric grading, low-cost peer evaluators repeated almost all of Jev's most confident errors."

### R2-arg-16 [minor — arXiv tone]
- **Location:** main.tex date line ("Version 0.3"); 01_introduction.tex "Version 0.2 of this analysis … is superseded"; §3.8; Appendix D (two correction tables against v0.1 and v0.2); D_corrections.tex ("174 findings").
- **Problem:** For an arXiv v1, a visible version history and corrections log against versions that readers cannot see (v0.2 was not published) reads as project documentation. It also invites the question of what v0.1 and v0.2 were. Transparency is good, but the place for it is the repository.
- **Suggested fix:**
  - Remove "Version 0.3" from `\date`; use the date only.
  - In §1, replace the v0.2 sentence with "An earlier dataset release [survey01] summarised studies from abstracts; this paper supersedes it."
  - Keep §3.8 as "Deviations from protocol", without the version narrative.
  - Move Appendix D to the repository, or keep only the v0.1 table, since v0.1 is public.

### R2-arg-17 [minor — method]
- **Location:** E_codebook.tex PRISMA table.
- **Problem:**
  - The checklist groups items and omits sub-items that reviewers check: 13a–f (synthesis preparation, heterogeneity, sensitivity), 16b (excluded studies that look eligible, which are cited only as "in the data release"), 20a–d, 23a–d and 24b–c.
  - Item 1 is claimed as met but is not (R2-arg-4).
  - Item 14/21 (reporting bias) points to a single Limitations sentence.
  - For a 17-day, AI-screened, single-human-author review, PRISMA-RR, the rapid-review extension, or at least the Cochrane rapid-review minimum standards are the more appropriate checklist. They would also justify the single-human design explicitly.
- **Suggested fix:**
  - Expand to sub-item granularity with "not done" where true. Item 13d/f: "sensitivity analysis excluding Zenodo, Section 4.8" (once added).
  - List the 16b near-misses (e.g. the unrelated "Jev" paper and the PDF-mismatch paper) in a footnote.
  - Add one sentence stating that the Cochrane rapid-review recommendation of dual human screening of at least 20% was not met.

### R2-arg-18 [nit]
- **Location:** 01_introduction.tex Scope ("The author contributes to PoL2 (Section 8)"); main.tex `\author`.
- **Problem:** The positionality statement is an unnumbered section after §8, so "Section 8" points to the Conclusion. The author block has no affiliation or contact address. arXiv does not require one, but cs.CY moderators and readers expect at least "Independent researcher" and an email.
- **Suggested fix:** Use `\label{sec:positionality}` with a `\hyperref` to "the Positionality statement". Add an affiliation line and an email.

### R2-arg-19 [nit]
- **Location:** Figure 1(b) column header "Zenodo / alphaXiv"; Limitations ("19 of 44 coded pairs").
- **Problem:** Figure 1(b) counts 46 Zenodo/alphaXiv pairs and the text counts 44 Zenodo pairs. The 2 alphaXiv pairs explain the difference, but the reader has to infer this.
- **Suggested fix:** Add "(44 Zenodo, 2 alphaXiv)" to the Figure 1 caption.

### R2-arg-20 [nit]
- **Location:** 03_method.tex §3.7; 09 Use of AI assistance.
- **Problem:** "Claude, Anthropic" gives no model versions, dates or prompts. Reproducibility of AI screening and coding depends on all three.
- **Suggested fix:** Name the model and version for each role (screening, extraction, coder 1, coder 2, verification). State that the prompts and agent instructions are in the data release, and release them.

### R2-arg-21 [nit]
- **Location:** 04 §4.2 answer box ("Codes: S 1, Q 0, N 9; this is the most consistently negative requirement") and the box's first sentence ("Every study that attacked a typed model … found some success").
- **Problem:** The one S study (InjecAgent, 1.8%) also "found some success", so the first sentence is literally true. Read together, though, "every study found success" and "S 1" look contradictory.
- **Suggested fix:** "…found some success; the one study coded as supporting found that raw injection rarely selected the attacker's target."

---

## Answers to the four questions in brief

**A. arXiv moderation.**
- **Classification:** v0.3 now reads as a research paper. It poses a societal and policy question, and its original components are the clause-to-requirement derivation, a documented and coded assessment with released data, a clause-level comparison with the EU AI Act, GDPR and DSA, and a reference design with falsifiable criteria. That is not an annotated bibliography, and cs.CY primary is defensible.
- **Residual risk:** the review apparatus (PRISMA flow and checklist, a long evidence section) is still prominent, and the PRISMA item-1 row is inaccurate (R2-arg-4).
- **Tone:** neutral apart from two promotional sentences (R2-arg-12) and the version-history apparatus (R2-arg-16).
- **Other reasons for rejection or reclassification:** none of substance. Reclassification to cs.CL or cs.AI is unlikely given the abstract, and dropping the cs.CL cross-list reduces the exposure.
- **Before submitting:** fix R2-arg-13 (data not public, wrong table count).

**B. Argument.**
- **Thesis:** now two-sided and comparative. It overshoots to "automated judges generally" (R2-arg-5).
- **Certainty of conclusions:** the main positive headline is overstated relative to its own very-low rating (R2-arg-1).
- **Detector/judge definition:** consistent in §1 and element 5. It is undercut by T4 option (a), "repair" and the conclusion's wording (R2-arg-2), and by "judge" being used loosely elsewhere (R2-arg-11).
- **Falsification:** operational, but the evidence standard is asymmetric and there is no condition for the human end-point (R2-arg-10).
- **Treatment of PoL2:** charitable. §2.2 is neutral and each tension gives a charitable reading and a text-preserving option.
- **Human-vs-AI disclosure:** honest in the body, misleading in the abstract (R2-arg-3).

**C. Method.**
- **Complete and consistent:** eligibility, flow and counts reconcile, and κ recomputes exactly.
- **Gaps:**
  - quality appraisal ignores independence, and certainty rules are applied unevenly (R2-arg-6);
  - no sensitivity analysis without Zenodo (R2-arg-8);
  - residual codebook asymmetry and no SWiM justification (R2-arg-9);
  - AI-only double coding with no CI (R2-arg-3);
  - PRISMA checklist incomplete and item 1 inaccurate (R2-arg-17).

**D. Readability.** The answer boxes clearly help. §4 is still about 30% too long. The same evidence is re-listed across §4, §5, §6 and §8, and there are two overlapping certainty tables (R2-arg-14).

---

## Overall recommendation

**Minor revision** (FAccT/AIES standard; borderline major only because of R2-arg-1 to -3).

v0.3 is a substantial improvement. Of the 16 round-1 argument majors, 10 are resolved and 6 partly resolved; none is unaddressed. The paper is now comparative, appraised, certainty-rated, reproducibly counted, connected to prior literature, and charitable to its case. The remaining majors are about calibration of wording and disclosure, not about missing analyses:
- a headline "safely" that the paper rates very low;
- a text-preserving option that contradicts the thesis;
- an abstract that hides that the second coder was an AI;
- an overgeneralisation to all automated judges;
- an appraisal rule that ignores independence.

All can be fixed in text and tables in a day. The single most valuable addition is one human coding the 30-pair κ sample.

## arXiv acceptance-risk verdict

**Medium**, falling to **low** once R2-arg-4 (move PRISMA apparatus to the appendix, add the framing sentence, fix PRISMA item 1, shorten §4), R2-arg-12, R2-arg-13 and R2-arg-16 are done.

Reasons:
1. The paper now presents and largely is a cs.CY research paper on the societal impact of automated safeguards, which the 31 Oct 2025 FAQ exempts. Its policy and design contributions are original.
2. The residual risk is perception. A moderator skimming the method sees PRISMA 2020, a flow diagram, a PRISMA checklist and an evidence section longer than the analysis. Moderators judge proportion and content, not labels.
3. The data-availability statement is currently false on the public repository. A reader or moderator who follows the link finds the files missing.
4. There is no remaining advocacy or project-memo voice serious enough to trigger "not scholarly" on its own, and the author metadata is now correct.

**Counts:** 21 findings, made up of 6 major (R2-arg-1, -2, -3, -4, -5, -6), 11 minor (R2-arg-7 to -17) and 4 nit (R2-arg-18 to -21).
