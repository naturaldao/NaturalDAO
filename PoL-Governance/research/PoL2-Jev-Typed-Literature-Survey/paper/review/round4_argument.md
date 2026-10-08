# Round 4: argument, method and arXiv-moderation review (build of 4 Oct 2026 23:37, 65 pp.)

Reviewer: independent senior reviewer (FAccT/AIES standard) and, separately, acting arXiv moderator. Date 2026-10-04. The only file I edited is this one.

## Inputs

- `main.pdf` (65 pp.), read in order with `pdftotext -layout`.
- `sections/*.tex`, `counts.tex`, `arxiv_metadata.txt`, and the `arxiv/` bundle. I compared the bundle with `sections/` and found only the expected path-flattening and comment-stripping differences. Both `main.bbl` files contain zero `abs/v1` strings.
- `review/round3_argument.md` and `review/round3_fidelity-consistency.md`.
- `data/evidence_coding.csv`, `data/quality_appraisal.csv`, `data/grey_literature.csv` and `data/zenodo_preprints.csv` (local copies), which I used to recheck counts. Recomputed: 161 pairs, S 16 / Q 99 / N 46, from 85 documents. There are 92 appraised sources (37 / 17 / 38), which is the 85 tallied documents plus 7 non-empirical ones. A further 4 records were read and then excluded: arx22664, Molas, Willison and zen22953637. Seven grey sources count once the excluded ones are removed. All of these match the text.

---

## 1. Status of the round-3 argument findings

| ID | Status | One line |
|---|---|---|
| R3-arg-1 | FIXED | Abstract now says "under added conditions". The §4.8 bridge paragraph says G2 and G4 failures "are failures of the detector itself" and that the recommendation concerns containment, not reliability. The Thesis keeps "disguised attacks still passed" and "even the detector claim is an extrapolation". Residual nit: R4-arg-3. |
| R3-arg-2 | PARTLY | The §1 judge definition is narrowed to restrictive outcomes, and automatic allow is now an explicit, audited exception; the body of element 5 repeats this. The element-5 title and the §8 summary still describe all automatic action as "brief and reversible" (R4-arg-2). |
| R3-arg-3 | AUTHOR-ONLY | The disclosure is honest and consistent across §3.4, §3.6, Limitations and the AI-use statement. Only the author can do the human re-check (hand-code the κ sample and read the N codes) and report it. |
| R3-arg-4 | FIXED | The steering row is now rated *low*, and §7 says "One reaches moderate certainty". The remaining moderate row (thresholds) meets the stated rule: arx00346, arx33401 and arx33843 are stronger-design and independent, and arx33843 is preregistered. The sentence naming "rises to moderate" as the paper's own adaptation of GRADE was not added (nit, R4-arg-6). |
| R3-arg-5 | PARTLY | The element-6 title ("End every chain that could block with a person") and Figure 6 box 6 ("end of every chain that could block") are fixed. The Figure 6 caption is unchanged (R4-arg-1). |
| R3-arg-6 | FIXED | §3.3 now reconciles 85 tallied + 7 non-empirical + 22 background = 114, which matches the data. |
| R3-arg-7 | FIXED | No `abs/v1` remains in the PDF, `main.bbl` or `arxiv/main.bbl`. Refs [22], [23], [24], [30], [31] and [121] now resolve to correct IDs. |
| R3-arg-8 | AUTHOR-ONLY | All the named files now exist in the local `data/` folder. Pushing them, tagging the release and pinning the tag or commit in the Data statement and the Comments field remain author actions. |
| R3-arg-9 | AUTHOR-ONLY | The Comments line still ends in "PoL2-Jev-Typed-Literature-Survey". Whether to rename the path or mint a DOI is the author's decision. |
| R3-arg-10 | FIXED | "a plausible role". |
| R3-arg-11 | FIXED | Appendix D now says "AI review passes", §3.7 is retitled "Changes from the earlier release", and §3.6 and §9 say "separate". A small leftover is in PRISMA item 24 (R4-arg-6). |
| R3-arg-12 | FIXED | The abstract now has "in one preregistered study on simulated data". |
| R3-arg-13 | FIXED | "demand for transparency" has been removed from the list of §8 commitments. |

**Tally:** 9 FIXED, 2 PARTLY, 0 NOT, 3 AUTHOR-ONLY (R3-arg-3, -8, -9). The affiliation and contact email also remain author actions.

---

## 2. New and remaining findings

### R4-arg-1 [minor] Figure 6 caption still sends all disagreements to people

**Location:** 06_design.tex, `\caption` of `fig:architecture`: "...disagreements, insufficient information and a random sample of confident decisions go to people (6)".

**Problem:**
- Element 5 sends disagreement and "insufficient" verdicts first to clarification or to a stronger reasoning model.
- Element 6, as now titled, and the redrawn box 6 send to people only escalations that could end in a block, unresolved escalations and the random audit.

So the caption, which most readers see before the elements, still contradicts the design and overstates the human end-point. This is the one piece of R3-arg-5 left undone.

**Fix:** Change the caption to: "...disagreements and insufficient verdicts are clarified or escalated (5); any that would end in a block, any left unresolved, and a random sample of confident decisions go to people (6)...".

### R4-arg-2 [minor] Element-5 title and the §8 summary drop the automatic-allow exception

**Location:**
- 06_design.tex element 5 title: "Act automatically only on agreement, only reversibly, and only briefly".
- 08_conclusion.tex ¶1: "brief and reversible automatic action only on agreement".

**Problem:** §1 now defines automatic allow as neither bounded in time nor reversible for anyone the content harms. It is admitted to the detector role only as a "deliberate, audited exception". The body of element 5 permits it and governs its miss rate. The title and the conclusion's one-line summary, however, say all automatic action is brief and reversible.

A reader of the conclusion alone is told the design never takes an irreversible automatic action. In fact it does, for allow, and the G2 evidence (disguised attacks passed the agreement gate) bears directly on that action. This is the last inconsistency on the detector/judge line. It is small, but it sits in the conclusion.

**Fix:**
- Element 5 title: "Act automatically only on agreement; restrict only reversibly and briefly".
- §8: "...automatic allow only on agreement with an audited miss rate, brief and reversible holds, person-confirmed blocks...".

### R4-arg-3 [nit] The Thesis lacks the "under added conditions" qualifier that the abstract now has

**Location:** 01_introduction.tex Thesis ("supports typed decision models as detectors: they rank...").

**Fix:** "supports typed decision models as detectors under added conditions (local thresholds, an independently built second check, human review of blocks):".

### R4-arg-4 [nit] "At most about five points" understates the sensitivity shift

**Location:** 04_evidence.tex §4.8.

**Problem:** The negative share moves from 28.6% (46/161) to 34.2% (27/79) for stronger-design studies only, and to 23.1% (27/117) without Zenodo. Both shifts are about 5.5 points.

**Fix:** Write "by about six percentage points at most", or give the three negative shares.

### R4-arg-5 [nit] An excluded source is still marked as grey evidence

**Location:** 04_evidence.tex §4.5, "[147]†" (Willison).

**Problem:** `quality_appraisal.csv` excludes this record ("commentary without original measurements"). It is not among the 7 grey sources, and App. B lists it as not tallied. §3.2 admits grey literature only "when they report original measurements". The † mark therefore implies it is counted evidence.

**Fix:** Drop the † and cite it as context.

### R4-arg-6 [nit] Small method-reporting leftovers

**Location and fix:**
- E_codebook.tex, PRISMA 24a–c: "deviations in Section 3". Write "changes from the earlier release in Section 3.7".
- 03_method.tex §3.7: "The protocol was not registered" implies that an unregistered protocol exists. Write "No protocol was registered or published."
- 03_method.tex §3.5: after the moderate rule, add "Raising a rating on consistency across studies is our adaptation; GRADE's own upgrading criteria do not apply to benchmark evaluations."

### R4-arg-7 [nit] "Shows why" is stronger than the certainty supports

**Location:** 08_conclusion.tex ¶1 ("The same evidence shows why none of the typed models tested... should serve as the judge").

**Problem:** The supporting findings are rated low or very low. The judge conclusion actually rests on the stated asymmetric evidence standard (§7) as much as on the evidence.

**Fix:** "The same evidence, read under the asymmetric standard of Section 7, indicates why...".

---

## 3. Fresh-review summary by question

- **Claims against certainty:** Calibrated throughout. Exactly one moderate finding remains, and it meets the stated rule. The abstract, §6, §7 and §8 word certainty consistently. Only the R4-arg-7 nit remains.
- **Detector/judge consistency:** The §1 definition, §4.8 bridge, T4 option (a), elements 3, 5 and 6, and Figure 6 box 6 are now consistent. Two places are left: the Figure 6 caption (R4-arg-1) and the element-5 title and §8 summary (R4-arg-2). Both are wording, not substance.
- **Fairness to PoL2:** Charitable and neutral. Every tension offers a text-preserving option. Option (a) of T4 is honestly flagged as outside the evidence. Positionality is complete, and coincidences with the pilot protocol are flagged. I found no new issue.
- **Disclosure honesty:** The AI-agent roles, same-family coders, the absence of a human re-check, and the unmet Cochrane dual-screening recommendation are all stated, and stated consistently. I found no new issue.
- **Method reporting:** The counts reconcile against the data. The certainty rule is applied correctly. The references are fixed. The arXiv bundle is in sync with the sources and compiles from a flat directory. Only nits remain (R4-arg-4, -5, -6).
- **Tone:** Neutral and scholarly. There is no advocacy or project-memo voice.
- **arXiv classification:** This is a cs.CY policy analysis with original contributions: the clause-to-requirement derivation, the regulatory tension analysis and a falsifiable reference design. The PRISMA apparatus sits in an appendix, and the Comments line says "Policy analysis with a documented evidence assessment". cs.CY primary with a cs.AI cross-list is appropriate.

## 4. Overall recommendation

**Accept with minor revisions** (FAccT/AIES standard). R4-arg-1 and R4-arg-2 are a few minutes of wording, plus regenerating nothing beyond the caption. The nits are optional. No major problem remains in the argument.

## 5. arXiv acceptance-risk verdict

**Low**, provided the author-only items are done:
- push the data and sources;
- tag the release and pin it in the Data statement and Comments;
- add an affiliation (e.g. "Independent researcher") and a contact email;
- settle the repository path or DOI in Comments.

If the author also does the R3-arg-3 human check and reports it in §3.4, §3.6 and the AI-use statement, the remaining main moderation signal goes away. That signal is a sole author with no affiliation whose evidence base was produced and drafted by AI agents with no human verification.

If the human check is *not* done but the other author items are, I rate the risk **low to medium**. The paper is clearly within the cs.CY exemption and is scholarly in form. The open question is whether a moderator reads the AI-production profile as insufficient author contribution. Honest disclosure mitigates this but does not remove it.

If the data are not pushed before submission, I rate the risk **medium**. The Data statement would then be verifiably false.

## Counts

7 findings: 0 major, 2 minor (R4-arg-1, R4-arg-2), 5 nit (R4-arg-3 to R4-arg-7). Both minor findings are residuals of round-3 items (R3-arg-5, R3-arg-2), not new problems of substance.
