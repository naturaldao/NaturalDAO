# Round 3: argument, method and arXiv-moderation review (v0.3, build of 4 Oct 2026 23:26)

Reviewer: independent senior reviewer (FAccT/AIES standard) and, separately, acting arXiv moderator. Date 2026-10-04. The only file I edited is this one.

## Inputs

- `main.pdf` (64 pp.), read in order with `pdftotext -layout`. I rendered p. 12 to check the source marks and Figure 2.
- `sections/*.tex`, `main.tex`, `arxiv_metadata.txt`, `arxiv/main.bbl` and `corpus.bib`.
- `review/round2_argument.md` and `review/REVIEW.md`.
- `data/evidence_coding.csv` and `data/quality_appraisal.csv`, which I used to recompute the numbers below.
- The public GitHub directory `naturaldao/NaturalDAO@main …/PoL2-Jev-Typed-Literature-Survey/data`, fetched today.

## Recomputed numbers

All of these match the paper unless I say otherwise.

- **Tallied pairs:** 161 pairs from 85 documents, coded S 16, Q 99, N 46. The per-requirement sums match the answer boxes and Figure 2.
- **Appraisal file:** 96 rows. 4 are excluded, leaving 92. Of those 92, 37 are stronger, 17 moderate and 38 weaker. Every "stronger" study is independent.
- **Where 92 comes from:** 85 tallied empirical documents plus 7 non-empirical items. The text never says this (R3-arg-6).
- **Size of §4:** about 3,860 words of source, so the target of 4,500 or less is met. §5 to §7 together run about 3,900 words.
- **Public repository:** the `data/` folder still lists only `sources/`, `grey_literature.csv`, `papers.csv`, `papers.json`, `pol2_axes.json` and `pol2_mapping.csv`. None of the coding, appraisal, agreement or exclusion files is public.

---

## 1. Status of the round-2 findings

| ID | Status | One line |
|---|---|---|
| R2-arg-1 | RESOLVED | Abstract, Thesis, element 3 and Table 2 now say "lost no accuracy… disguised attacks passed", rated very low. Nit: the abstract drops "simulated data" (R3-arg-12). |
| R2-arg-2 | PARTLY | Option (a) is now flagged, repair is limited to the AI's own output, and the conclusion is fixed. Automatic *allow*, and "end every chain" against element 6, remain inconsistent with the §1 definition (R3-arg-2, R3-arg-5). |
| R2-arg-3 | RESOLVED | Abstract and contributions now say "AI coder". §3.4 adds the CI, the marginals and "same model family". §3.6 and §9 state that there was no human re-check. Appendix D still says "independent review passes" (nit, R3-arg-11). |
| R2-arg-4 | RESOLVED | PRISMA flow moved to App. E.4, framing sentence added, item 1 marked "not followed by design", cs.CL dropped, Comments descriptor added, §4 shortened. The repository path in Comments still says "Literature-Survey" (R3-arg-9). |
| R2-arg-5 | RESOLVED | The thesis is now "not generally worse; most failures never compared", supported by the comparator counts in §4.8. |
| R2-arg-6 | PARTLY | Independence is now a rating input, the levels are renamed and the starting point is justified. One "moderate" rating does not meet the paper's own stated rule (R3-arg-4). |
| R2-arg-7 | RESOLVED | Abstract: "the 85 relevant sources were read in full, appraised and coded". |
| R2-arg-8 | RESOLVED | The without-Zenodo sensitivity analysis (13/77/27 of 117) is in §4.8 and Limitations. |
| R2-arg-9 | RESOLVED | Rule (iv) added to §3.4 and App. E; SWiM cited. |
| R2-arg-10 | RESOLVED | Asymmetric evidence standard justified; revision condition for the human end-point added. |
| R2-arg-11 | RESOLVED | "Independently built rule/checker" throughout; Figure 5 relabelled "LLM evaluators". |
| R2-arg-12 | RESOLVED | §7 and §8 now say "consistent with what the evidence recommends". |
| R2-arg-13 | PARTLY | Page count in Comments fixed. The data statement is still false against the public repository, and the link is still unpinned (R3-arg-8). |
| R2-arg-14 | RESOLVED | One merged certainty table, §4 at about 3,860 words, and §7 no longer restates the conclusion. |
| R2-arg-15 | RESOLVED | "On rubric grading, low-cost peer evaluators repeated almost all…" plus the selection caveat. |
| R2-arg-16 | RESOLVED | Version history removed. Residual nit: §3.7 is titled "Deviations from protocol" although no protocol exists (R3-arg-11). |
| R2-arg-17 | RESOLVED | PRISMA expanded to sub-items; 16b examples given; 13e/14/21 marked not done; Cochrane dual-screening shortfall stated in §3.6. |
| R2-arg-18 | PARTLY | Positionality is now cross-referenced by name. There is still no affiliation or contact email (author action). |
| R2-arg-19 | RESOLVED | Figure 1 caption gives "44 Zenodo and 2 alphaXiv pairs". |
| R2-arg-20 | RESOLVED | Model named ("Claude Opus 5.5… for all agent roles"); agent instructions released (`review/agent_instructions.md`). |
| R2-arg-21 | RESOLVED | The G2 answer box now explains the single S code. |

**Tally:** 15 RESOLVED, 6 PARTLY, 0 NOT.

---

## 2. New and remaining findings

### R3-arg-1 [major] The detector claim is not connected to a tally coded for detector use

**Location:**
- 00_abstract.tex ("The evidence supports typed models as detectors")
- 01_introduction.tex Thesis
- 04_evidence.tex §4.8 ("16 support detector use, 99 qualify it and 46 are negative")
- E_codebook.tex ("for *detector* use…; judge use is never coded")
- 08_conclusion.tex ¶1

**Problem:** By the paper's own codebook, every code concerns detector use. So the 46 N codes are 46 failures *of detector use*, against only 16 unconditional supports (10%). The thesis reads them the other way round: the failure list (thresholds do not transfer, option names, inserted opinions, rare "insufficient") is offered as the reason typed models are not *judges*, while the same tally is said to "support" them as *detectors*.

The paper never states the bridge: why a mainly Q/N tally for detector use licenses a positive detector claim, and why the N codes bear on the judge role rather than the detector role. A FAccT reviewer will ask this immediately.

The gap is sharpest for G2. G2 is S 1, Q 0, N 9, "the most consistently negative requirement". Under the §1 definition a miss (an attack that is allowed through) is a governed detector failure, so G2 is evidence against the detector role too. The design's answer (two independently built detectors, a human end-point) is untested; Table 2 rates the gated-acceptance evidence very low.

**Fix:** Add a short paragraph at the end of §4.8, something like:

> "The tallies concern detector use. The detector conclusion rests on the Q codes: the conditions they require (local thresholds, recalibration, human review of uncertain cases) are what the design in Section 6 supplies. The N codes for G3 and G4 are failures that a human end-point is meant to absorb, and they are the reason we do not support judge use. The G2 codes are different: they are failures of the detector itself, because a successful attack is a miss. Whether two independently built detectors and human review contain them is untested."

Then:
- In the abstract, change "The evidence supports typed models as detectors" to "The evidence supports typed models as detectors under added conditions".
- In the Thesis, add "and adversarial content remains an open risk even in that role".
- Make sure the G2 limitation appears in the abstract or Thesis, not only in "Trade-offs".

### R3-arg-2 [major] Automatic allow does not fit the §1 definition of a judge

**Location:**
- 01_introduction.tex "Detector or judge" ("…or that cannot be fully reversed on appeal. Under this definition, an automatic allow is also consequential…")
- 06_design.tex element 5 ("This element is what keeps the typed model a detector")
- Figure 6, box 5

**Problem:** §1 defines a judge as any automated output that, without human confirmation, determines an outcome that "cannot be fully reversed on appeal". It then says an automatic allow is "also consequential". Element 5 permits automatic allow on agreement with no person involved.

When an allowed message harms someone, the harm cannot be reversed on appeal. On a plain reading of the definition, an automatic allow is therefore a judge act, and element 5's claim that it "keeps the typed model a detector" does not hold. The text tries to handle this by governing the miss rate, but the definition does not say that a governed miss rate turns a judge act into a detector act.

This is the last place where the detector/judge distinction, which the whole thesis rests on, is internally inconsistent. Read with R3-arg-1, it also means the G2 evidence bears directly on what the design does automatically.

**Fix:** Do one of the following in §1:
1. Narrow the "cannot be fully reversed" clause to restrictive outcomes ("…an outcome that restricts a person's speech, resources or account beyond a short bounded period or irreversibly").
2. Treat automatic allow explicitly as a bounded, permitted exception: "We treat automatic allow as a detector act provided its miss rate is certified against a target set by those accountable and audited by random sampling; this is a policy choice, not a consequence of the evidence."

Make element 5 and §8 repeat whichever wording is chosen.

### R3-arg-3 [major — method / arXiv] AI drafting and coding without any human verification

**Location:** 03_method.tex §3.6 ("the author did not re-code or re-check individual codes by hand before this release"); 09_statements.tex "Use of AI assistance" ("…coding, quality appraisal, second coding, figure scripting and drafting…").

**Problem:** The disclosure is now honest, which is to its credit. What it discloses is the problem: AI agents of one model family did the searching, screening, extraction, coding, the blind second coding, appraisal, certainty rating, drafting and number checks. No human checked a single code, rating or extraction.

For a FAccT/AIES reviewer, this means κ measures agreement between two AI agents of the same model family, and no measured quantity in the paper has been verified by a human. For an arXiv moderator, a 64-page paper whose evidence base was produced and drafted by AI agents, with no stated human verification, matches the profile of submissions that moderators have increasingly rejected as insufficiently author-produced. That is so even though the author takes responsibility and the material is not an annotated bibliography.

A modest human check would change both readings, and only the author can do it.

**Fix (author action):**
- Before submission, the author codes the 30-pair agreement sample by hand and reports human–AI κ.
- The author reads all 46 N codes, and the codes behind the two "moderate" rows of Table 2, against their locators. Report "the author checked k codes and changed m" in §3.4, §3.6 and the AI-use statement.
- If that is not possible, add one sentence to Limitations stating that no measured quantity was verified by a human, and accept the higher moderation risk.

### R3-arg-4 [minor — method] One "moderate" rating breaks the paper's own rule

**Location:** 04_evidence.tex Table 2, row "Inserted opinions, optimised context and lexical lures steer decisions" (moderate); §3.5 rule; §7 "Certainty".

**Problem:** The rule raises a finding to moderate only if "at least three independent stronger-design studies agree… and at least one *of them* is preregistered or replicated". The row's sources and their appraisal records:

| Source | Appraisal record |
|---|---|
| arx31142 | stronger, held-out |
| arx01834 | stronger, held-out |
| arx01006 | stronger, held-out |
| arx30243 | weaker, single run |
| arx02048 | moderate, preregistered, author-built |

None of the three stronger-design studies is preregistered or replicated, so by the stated rule this row should be **low**, not moderate. The row "Thresholds set in advance miss error targets" does meet the rule (arx33843 is preregistered, stronger and independent).

GRADE also does not upgrade for consistency. Its upgrade domains are large effect, dose–response and plausible confounding. "In the spirit of GRADE" partly covers this, but "rises to moderate" should be named as the paper's own adaptation.

**Fix:**
- Either rate the steering row low (then §7 says "One finding reaches moderate certainty…"), or rewrite the rule (e.g. "…or at least one preregistered study of any design agrees") and re-apply it to every row.
- In §3.5, add: "Raising to moderate is our adaptation; GRADE's own upgrading criteria (large effect, dose–response) do not apply to benchmark evaluations."

### R3-arg-5 [minor] Figure 6 and element 6 say every chain ends with a person; element 5 lets some end without one

**Location:** 06_design.tex element 6 title "End every chain with a person"; Figure 6 box 6 "end of every escalation chain"; Figure 6 caption ("disagreements, insufficient information and a random sample of confident decisions go to people"); element 5 ("Disagreement or insufficient leads to clarification or to escalation to a stronger reasoning model").

**Problem:** The body text of element 6 is now precise: reviewers see escalations that would end in a block, unresolved escalations and a random sample. That means an escalation that the stronger reasoning model resolves to *allow* ends without a person. Three places say otherwise:
- the element 6 title;
- Figure 6 box 6;
- the caption's statement that disagreements "go to people", which element 5 contradicts (they go to clarification or to a model first).

The same automatic-allow gap as R3-arg-2 thus appears in the most-viewed figure.

**Fix:**
- Retitle element 6 "Put a person at the end of every restrictive or unresolved chain".
- Figure 6 box 6: "escalations ending in a block or unresolved".
- Caption: "…disagreements and insufficient verdicts are clarified or escalated; any that would end in a block, any left unresolved, and a random sample of confident decisions go to people".
- Regenerate the figure from its script.

### R3-arg-6 [minor] Corpus, coded and appraised counts do not reconcile in the text

**Location:** 03_method.tex §3.3 ("Of these, 85 bear on at least one requirement and are coded below…; the rest are background-tier engineering papers"); §3.5 ("Each coded study was appraised… Of the 92 appraised sources").

**Problem:**
- The 92 appraised sources are 85 tallied documents plus 7 non-empirical items. A reader sees "85 coded" and then "92 appraised" with no explanation.
- "The rest are background-tier engineering papers" is inaccurate: the remaining 29 of 114 include those 7 non-empirical items (essays and critiques that §4.5 and §4.7 cite), and Figure 1 lists 25 background arXiv papers.

**Fix:**
- §3.3: "…85 report measurements bearing on at least one requirement and enter the tallies; 7 further non-empirical items are coded but not tallied, and the remaining 22 are background engineering papers" (use the true split).
- §3.5: "Each of the 92 coded sources (85 tallied, 7 non-empirical) was appraised".

### R3-arg-7 [minor — scholarly / arXiv] Fifteen references have broken arXiv identifiers

**Location:** `corpus.bib` (15 entries) → `main.bbl` and `arxiv/main.bbl`. In the PDF these include refs [22] AnyJev, [23] LLM2Jev, [24] Beyond Answer Confidence, [30] Rafe & Das (the benchmark behind G1, G3, G6, Table 2 and the checklist) and [31] JevSpawn.

**Problem:** Each of these prints `URL https://arxiv.org/abs/v1` and `arXiv:v1`, i.e. no identifier. The `eprint` fields hold the correct IDs: 2610.00831, 2610.02076, 2610.01006, 2610.00346, 2609.39496, 2609.40241, 2610.02048, and others. The bug is in how `gen_corpus_bib.py` builds the `url` and `note` fields, apparently for IDs announced late in the window.

Several of the paper's most-cited sources (refs [24], [30], [121], [123] and others) are therefore not locatable from the reference list. A moderator or reader who clicks them gets a dead link. This is the most visible non-scholarly defect left in the PDF.

**Fix:**
- Regenerate `url` and `note` from `eprint` (with the version suffix) for all 15 entries.
- Rebuild `main.bbl` and the arXiv bundle.
- Add a check to `make_arxiv.py` that fails on `abs/v1`.

### R3-arg-8 [minor — submission blocker, author action] Data statement still false; link not pinned

**Location:** 09_statements.tex "Data and code availability"; arxiv_metadata.txt Comments.

**Problem:**
- The public `data/` folder (fetched today) still lacks `evidence_coding.csv`, `quality_appraisal.csv`, `coder_agreement.csv`, `excluded_records.csv` and `zenodo_preprints.csv`, as well as the scripts and logs that the statement says are "released".
- §3.4, §3.5 and §3.6 also point readers to these files.
- The link targets `main`, not a tag or commit.

**Fix:**
- Push the data and the `paper/` sources.
- Complete the licence audit of the redistributed PDFs.
- Tag the release (e.g. `pol2-jev-arxiv-v1`) and cite the tag or commit in both the statement and the Comments field.

### R3-arg-9 [minor — arXiv framing] "Survey" is still visible to a moderator

**Location:** arxiv_metadata.txt Comments (".../PoL2-Jev-Typed-Literature-Survey"); Data statement; ref. [12] title "PoL2 × Jev typed decision models: A literature survey"; directory name in the bundle.

**Problem:** The paper itself no longer calls itself a survey. The first thing a moderator reads after the abstract, though, is a Comments line ending in "Literature-Survey". The 31 Oct 2025 policy is applied by moderators on impression. This is a small signal, but it is avoidable.

**Fix:**
- In Comments, give the tagged URL without the long path, e.g. "Data, coding and scripts: https://github.com/naturaldao/NaturalDAO/tree/<tag>/PoL-Governance/research" or a Zenodo DOI for the release.
- Alternatively, rename the directory (e.g. `PoL2-Jev-Safeguard-Analysis`) and keep a redirect note.
- Ref. [12] keeps its real title; that is correct.

### R3-arg-10 [minor — tone/certainty] "A clear role" against low certainty

**Location:** 06_design.tex first sentence ("The evidence suggests a clear role for typed decision models…").

**Problem:** "Clear" sits against "every element rests on evidence of low or very low certainty" in the same section, and against R3-arg-1.

**Fix:** "The evidence, at low certainty, points to a role for typed decision models…".

### R3-arg-11 [nit] Leftover wording from the review process

**Location and fix:**
- D_corrections.tex ("further corrections made during the independent review passes"): write "during review passes by AI agents (Section 3.6)".
- 03_method.tex §3.7 title "Deviations from protocol" when "The protocol was not registered" and PRISMA 24 says no protocol exists: retitle "Changes from the earlier dataset release".
- 09 "checked the text against its sources in independent review passes": "independent" overstates passes run by the same model family. Use "separate".

### R3-arg-12 [nit] Abstract drops "simulated" for the gated study

**Location:** 00_abstract.tex ("in one preregistered study, accepting their low-risk verdicts… lost no accuracy").

**Problem:** The Thesis, element 3 and Table 2 say simulated data and "relative to a frontier LLM"; the abstract omits both. The abstract is at 1,909 of 1,920 characters, so there is little room.

**Fix:** If space allows, "in one preregistered study on simulated data". Otherwise leave it, because "one preregistered study" plus "disguised attacks passed" is already hedged.

### R3-arg-13 [nit] Conclusion praises transparency, which T3 shows in tension

**Location:** 08_conclusion.tex ¶2 ("…and the demand for transparency").

**Problem:** T3 shows the demand for transparency is in tension with closed models, and the same paragraph lists "how to reconcile transparency with closed models" as an open choice. Listing it among commitments that are "consistent with what the evidence recommends" reads slightly as advocacy.

**Fix:** Drop "and the demand for transparency" from the first list, or write "and the demand for a verifiable decision record".

---

## 3. Fresh-review summary by question

- **Claims against certainty:** much improved. The remaining overstatements are:
  - the unconditional "supports as detectors" (R3-arg-1);
  - one moderate rating that fails its own rule (R3-arg-4);
  - "clear role" (R3-arg-10).
- **Detector/judge consistency across §1, §4, T4, elements 3/5/6 and §8:**
  - consistent for blocks, repair, option (a) and the conclusion;
  - inconsistent for automatic allow (R3-arg-2) and for the "every chain" wording in element 6 and Figure 6 (R3-arg-5);
  - the tally-to-thesis bridge is missing (R3-arg-1).
- **Fairness and tone toward PoL2:** charitable and neutral. Each tension gives a charitable reading and a text-preserving option. Option (a) is honestly marked as outside the detector role. The positionality statement is full and coincidences are flagged. Only R3-arg-13 is left (nit).
- **Honesty of AI-use disclosures:** honest and now consistent across the abstract, §3.4, §3.6, Limitations and the statements. The issue is substance (no human verification), not candour (R3-arg-3).
- **Method reporting:** complete and reproducible against the data. The remaining issues are count reconciliation (R3-arg-6), the certainty-rule application (R3-arg-4) and broken references (R3-arg-7).
- **Survey / non-scholarly signals:** the PRISMA apparatus is in the appendix, §4 is shorter than §5–§7, and there is a framing sentence. The remaining signals are:
  - the "Literature-Survey" path (R3-arg-9);
  - 15 dead arXiv references (R3-arg-7);
  - no affiliation or contact;
  - the AI-production profile (R3-arg-3).
- **Readability:** good. The answer boxes, one merged certainty table and §4 at about 3,860 words make the paper navigable. Table 2's layout extracts poorly to text, but renders correctly.

## 4. Overall recommendation

**Minor revision** (FAccT/AIES standard). It becomes accept-ready once R3-arg-1 and R3-arg-2 are fixed in text. R3-arg-3 is an author-time task that would materially strengthen the paper but is not a correctness error, because it is disclosed honestly.

## 5. arXiv acceptance-risk verdict

**Medium.** It falls to **low** once R3-arg-7, R3-arg-8 and R3-arg-9 are done and an affiliation or contact is added. It falls further if R3-arg-3's human check is done and reported.

Reasons:
1. **Category and content are right.** This is a cs.CY research paper on the societal impact of automated speech restriction, welfare adjudication and social scoring, with original contributions: the clause-to-requirement derivation, the regulatory tension analysis and a falsifiable reference design. That falls under the FAQ's cs.CY exemption and is not an annotated bibliography. The review apparatus is no longer prominent.
2. **Verifiable defects a moderator can see in minutes:**
   - 15 references print `arxiv.org/abs/v1`;
   - the data statement points to files that are not in the public repository;
   - the Comments URL ends in "Literature-Survey".
   Any of these can trigger a hold or reclassification query.
3. **AI-production profile.** A sole author with no affiliation, plus the disclosure that AI agents did all searching, coding, appraisal and drafting with no human re-check, is the profile moderators now scrutinise for low author effort. Honest disclosure lowers the risk of a misconduct finding but not the risk of an on-hold or reject decision.
4. **No advocacy or project-memo voice remains** that would trigger "not scholarly" on its own.

## 6. Actions only the human author can take

1. **Push** the coding, appraisal, agreement, excluded-records and Zenodo files, plus the scripts, logs and LaTeX sources. Do the licence audit of redistributed PDFs. **Tag** the release and pin the link in the Data statement and the Comments field (R3-arg-8).
2. **Add an affiliation** (e.g. "Independent researcher") and a contact email to `\author` and the arXiv metadata.
3. **Human check:** code the 30-pair sample by hand (human–AI κ) and read the 46 N codes and the moderate-rated rows. Report what was checked and changed (R3-arg-3).
4. **Decide the repository path or DOI** used in Comments (R3-arg-9). Optionally mint a Zenodo DOI for the data release.
5. **Confirm** that the framework's originator has been told about the tension analysis before posting. This is optional; the paper already discloses that the analysis was not reviewed by the originator.
6. **arXiv endorsement:** a first-time cs.CY submitter may need an endorser.

## Counts

13 findings: 3 major (R3-arg-1, -2, -3), 7 minor (R3-arg-4 to -10), 3 nit (R3-arg-11 to -13).
