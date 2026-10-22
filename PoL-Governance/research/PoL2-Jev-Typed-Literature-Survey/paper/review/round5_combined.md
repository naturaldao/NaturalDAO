# Round 5: combined review (fidelity, consistency, argument, arXiv moderation)

Scope: main.pdf (65 pp., built 4 Oct 23:45, newer than every section file), sections/*.tex, counts.tex, main.bbl, arxiv_metadata.txt and data/*.csv. The only file I edited is this one.

## Recomputed from data/evidence_coding.csv (all match the paper)

- **Tallies.** 161 tallied pairs from 85 documents: S 16 / Q 99 / N 46.
- **Per requirement.** G1 2/20/5, G2 1/0/9, G3 2/12/10, G4 3/29/13, G5 2/3/3, G6 1/23/4, G7 5/12/2. These match the answer boxes, Fig. 1b and Fig. 2.
- **Comparators.**
  - All pairs: 23 better / 17 similar / 28 mixed / 8 worse of 76.
  - Negative codes: 6 worse / 4 similar / 3 mixed / 1 better, and 32 with no comparator.
  - G1: 6 of 21 better or similar. G4: 9 better and 2 worse of 18.
- **Fig. 1b sources.** 107 arXiv + 46 Zenodo/alphaXiv + 8 grey = 161.
- **Table 2.** Certainty is 1 moderate / 9 low / 5 very low. The codes and comparator columns agree with the coded rows of the cited studies (e.g. arx02048 G6 Q similar and G2 N; arx29769 similar; arx33401 mixed).
- **Metadata.** The arxiv_metadata abstract matches the PDF abstract. Page count is 65. main.log has no missing characters.

## Status of round-4 findings

| ID | Status | Note |
|---|---|---|
| R4-fc-1 | FIXED | Now reads "on the ``neutral'' option, although option positions were balanced". |
| R4-fc-2 | FIXED | App. E.2 now reads "or neither sample sizes nor uncertainty reported". The script comment is optional and was not checked. |
| R4-fc-3 | FIXED | The Fig. 6 caption now has "clarified or escalated, any final block is confirmed by a person, and a random sample … audited". |
| R4-fc-4 | FIXED | "by about six points or less". |
| R4-fc-5 | PARTLY | §1 now says "passages from 28 clauses". \clause{4.3.3.2} is still cited or paraphrased nowhere in the body, yet App. A says it quotes passages "this paper cites or paraphrases" (R5-5). |
| R4-fc-6 | FIXED | "similar or mixed". |
| R4-fc-7 | FIXED | "43% of the narratives documenting fetal harm and 37% of the adjudication sample". |
| R4-fc-8 | FIXED | "even with 150 labelled examples in its context, stayed far below small tree models trained on the labels". |
| R4-arg-1 | FIXED | Same edit as R4-fc-3. |
| R4-arg-2 | FIXED | The element-5 title now reads "and restrict people only briefly and reversibly". §8 says "with any restriction of a person brief and reversible and automatic allows audited". |
| R4-arg-3 | FIXED | The Thesis now says "as detectors under added conditions". |
| R4-arg-4 | FIXED | Same edit as R4-fc-4. |
| R4-arg-5 | FIXED | The Willison citation in §4.5 has no † mark. |
| R4-arg-6 | PARTLY | PRISMA 24a–c is fixed, and §3.5 now states that the upgrading rules are the paper's own adaptation. §3.7 still says "The protocol was not registered" (R5-4). |
| R4-arg-7 | FIXED | "The same evidence indicates why". |

**Author-only items (not findings):**
- push the data and pin a tag or commit in the Data statement and Comments (R3-arg-8);
- settle the repository path or DOI (R3-arg-9);
- the human re-check of the codes (R3-arg-3);
- the affiliation and contact email.

## Claims spot-checked against full texts this round (not in the round-4 lists)

Each claim below was checked against the full text (local copy or arxiv.org/html).

- arx33401:
  - AUROC 0.961 against 0.533 on R-Judge.
  - All 130 no-EI injections missed with unsafe probability below 0.1.
  - 130 of 167 misses at confidence ≥0.95; judges detect at most five of them.
  - 47.03% coverage, achieved with 1 allow and 110 blocks.
  - Symmetric coverage of zero on WAInjectBench.
- arx01006:
  - 575,442 calls; SmoothECE 0.015–0.033.
  - 0.84 → 0.75 at confidence 0.83; up to 0.80 on a salient option.
  - AUROC 0.95 against 0.85; filtering 2–6 points less accurate.
  - Not deterministic; probabilities quantised to 0.01.
- arx02048:
  - Macro-F1 0.63 against 0.59; attack recall 0.34.
  - 21 of 76 accepted look-alike windows were attacks.
  - Gate settled 34.5% and 38.0% of windows; within margin on transfer to two networks. See R5-2 for the wording.
- arx37470: 32.8% of 1,000 (Event vs. Choice); 34.2% for the post-trained model.
- arx39496: 7% / 99% / 79%.
- arx24965: ten cases; seven wrong selections on one question.
- arx33971: TV 0.219–0.349 for Jev.
- arx36965: 92% of Jev's average accuracy.
- arx35342: 0.771 / 0.903 / 0.978.
- arx28919: interface classifier-agnostic with a self-hosted fallback.
- arx24574: preregistered (AsPredicted); REINFORCE reward of outcome minus probability.
- arx00213: 6,840 + 499,306 narratives read ("about half a million").
- arx30243 (JevOut):
  - 312/508 = 61.4% within 64 queries.
  - 63.6% against 56.4% with labels only.
  - 72.6 / 73.2 / 64.9% for the other systems.
  - A separate checker model.
- arx31142: 12.1% [8.5, 15.5], tied with the strongest command (10.1%); 12.6% through the 0.8 gate; 38.0% pushed below it; rewording at most +1.2 pp.
- arx29769: 242/252 (96.0%) against 50.3%; at most 1.5 points; 6 of 9 panels below.
- arx27535 (KITE): 8× and 312–455×; 37 held-out studies; primary endpoint not shown. See R5-3 for "near nominal".
- arx30216: 2,170 projects by 22 Sep; 81.0 / 72.2 / 45.4%.
- arx26550:
  - +0.93 [0.24, 1.66] at 41.4% on 1,610 pairs (83% RewardBench); −0.74 on JudgeBench.
  - Live: 100 labels per workload, 75.5% of the fee.
  - Within three points at 0.36% of the fee.
- arx29429: 63× pooled; 12× under conservative repricing.
- arx00437: 1.4–2.1× as long.
- arx37647: 27 datasets, 11 non-overlapping; rotation left accuracy unchanged on MMLU; all three models weakest on low-resource languages.
- arx00346: one-sided upper bound above the 5% target for every model.
- arx35293: lowest aggregate RMSE with a fitted ridge layer.
- arx02076: "none of the above" suppressed and a "yes" bias while validation loss improved.
- arx32160: 28 papers from 19–24 Sep; 14-item checklist.
- arx35286: a different rubric, so not ranked.

---

### R5-1 [minor] "The only Chinese benchmark" is false, and the Chinese calibration result it hides is omitted

**Location:** 04_evidence.tex l.118 (§4.3 Language): "The only Chinese benchmark found that hosted \jev{} needed no recalibration on Chinese voice routing…" [qin2026zhdecisionbench†].

**Problem:**
- The corpus contains a second Chinese benchmark that evaluates hosted Jev: arx36965 introduces CJ-Bench (307,900 held-out Chinese decisions), and the paper cites it in the very next sentence.
- On CJ-Bench, hosted Jev's ECE on general Chinese tasks was 11.45%, against 3.78% for the authors' open model. That is far above the English pooled ECE of 0.028 reported in §4.4.
- This result is coded in data/evidence_coding.csv (arx36965, G4), but it appears nowhere in the text.
- As written, the only Chinese calibration evidence reported is the favourable grey source, which has a weaker design. CJ-Bench is moderate design, although its comparator was built by the same authors.
- This bears directly on G3/G4 for the PoL2 construct, which is in Chinese, and on Table 3 item 11.

**Fix:**
- Write "The one Chinese benchmark of decision stability found…".
- Add: "On its authors' Chinese benchmark, hosted \jev{}'s ECE on general tasks was 11.45\%, against 3.78\% for their open model, though after domain fine-tuning the open specialists were worse calibrated than \jev{}~\cite{arx36965}." This could go in §4.3 Language or §4.4 "Calibration is local".

### R5-2 [minor] The agreement-gate study is described as non-inferior "on benign data"

**Location:**
- Table 2 row: "Acceptance on agreement with an independently built rule is non-inferior on benign data; disguised attacks pass".
- 06_design.tex element 3: "let a reviewer skip about a third of cases without loss of accuracy on benign data".

**Problem:**
- In arx02048, non-inferiority was tested on four-class macro-F1. The sealed sets contain 50 windows per class, including cyberattacks, and the test covered the unseen look-alike family E4c, where it held: +0.016 [0.003, 0.033] with glm-5.2.
- The study did not measure "benign data". The real caveat is different. On E4c the gate reduced the number of true attacks that received any non-benign verdict, from 20 to 15 of 50 (glm-5.2) and from 30 to 23 (deepseek-v4-pro). Macro-F1 hid this because the reviewers rarely recognised these attacks anyway.
- The phrase therefore misstates both what was found and why the success is fragile.
- §4.6 and the abstract ("lost no accuracy … though disguised attacks passed") are accurate.

**Fix:**
- Table 2: "…is non-inferior in macro-F1 on simulated data; disguised attacks pass and fewer attacks are flagged".
- Element 3: "…without loss of macro-F1 on simulated data, although disguised attacks still passed and fewer of them were flagged".

### R5-3 [minor] KITE coverage is called "near the nominal level" when it is well above it

**Location:** §4.7: "on 37 unseen studies this term gave retrospective coverage near the nominal level (0.93 and 0.96 at 80% and 90%)".

**Problem:**
- The source reports coverage of 0.67 / 0.93 / 0.96 at nominal 50 / 80 / 90%. That is over-coverage, and the authors call it possibly conservative.
- 0.93 at a nominal 0.80 is not "near nominal". The intervals are wider than needed.
- This inaccuracy is favourable to the honesty claim of G7.

**Fix:** Write "coverage at or above the nominal level (0.67, 0.93 and 0.96 at 50, 80 and 90%; the authors note it may be conservative)".

### R5-4 [nit] §3.7 still opens "The protocol was not registered"

**Location and problem:** This is left over from R4-arg-6. The wording implies that an unregistered protocol exists, while PRISMA 24a–c now says "no protocol published".

**Fix:** "No protocol was registered or published."

### R5-5 [nit] A clause row in App. A is cited nowhere

**Location and problem:** This is left over from R4-fc-5. App. A quotes \clause{4.3.3.2} (real-time correction support), but no body text cites or paraphrases it. The App. A intro says it quotes passages "this paper cites or paraphrases".

**Fix:** Drop the row, or write "cites, paraphrases or relates to".

### R5-6 [nit] The G2 answer box says other systems were "similarly vulnerable"

**Location and problem:** "Where other systems were attacked in the same studies they were similarly vulnerable". The two G2 rows with a comparator are arx30243, coded similar, and checkpoint2026jev, coded mixed.

**Fix:** "similarly or comparably vulnerable (one similar, one mixed)", or keep the sentence and cite only JevOut.

### R5-7 [nit] The latency figure is attributed to the documentation as well as the launch post

**Location and problem:** §2.1: "its launch post cites 70–500 ms per call [4, 7]". Appendix D itself says the documentation [7] states about 100–150 ms and that 70–500 ms comes from the launch post [4]. The citation pair therefore blurs the correction.

**Fix:** "The vendor lists $0.042 per million input tokens with free output [7], and its launch post cites 70–500 ms per call [4]."

---

## Argument and arXiv-moderation summary

- **Detector/judge line.** All four places that state it are now consistent: the §1 definition, element 5's title and body, the Fig. 6 caption and box 5, and §8.
- **Certainty.** Claims are calibrated, and the GRADE adaptation is now disclosed.
- **Tone.** Neutral and scholarly.
- **Classification.** cs.CY primary with a cs.AI cross-list remains appropriate.
- **Acceptance risk.** Unchanged from round 4: low once the author-only items are done.

## Counts

0 major, 3 minor (R5-1, R5-2, R5-3), 4 nits (R5-4 to R5-7).

New major or minor problems: **yes**, three minor ones, all fidelity issues new in this round. No major problem remains.
