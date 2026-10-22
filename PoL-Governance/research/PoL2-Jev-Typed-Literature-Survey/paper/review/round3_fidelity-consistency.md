# Round 3 — fidelity and consistency review

Scope: text as it stands after round 2 (abstract, §1 thesis, §3 appraisal/agreement/certainty, §4 incl. answer boxes, §4.8 and tab:keyfindings, §5–§8, App. A/D/E, fig_escalation/fig_fragility/fig_framework).

Recomputed from `data/` and confirmed correct (no action): 161 tallied pairs S 16 / Q 99 / N 46 over 85 studies; per-requirement tallies in all seven answer boxes; stronger-design sensitivity 7/45/27 of 79; no-Zenodo 13/77/27 of 117; Zenodo vs arXiv negatives 19/44 vs 23/107; 76 compared pairs = 23 better / 17 similar / 28 mixed / 8 worse; negative codes with comparator 14 = 6 worse / 4 similar / 3 mixed / 1 better, 32 of 46 without; G1 split 6/10/5 of 21; G4 9 better / 2 worse of 18; kappa 0.72 on 26 of 30, first-coder marginals S 3 / Q 23 / N 4; design ratings 37/17/38 of 92 (as the script computes them); corpus counts 79+27+1 = 107, 7 grey; App. E selection arithmetic (arXiv 89→64+25→15 new; Zenodo 62→41→28→27). Spot-checked against full texts with no problem found: arx02048 (34.5–38%, 21 of 76, recall 0.34, 0.63 vs 0.59), arx29769 (242/252, 50.3%, 1.5 points, 6 of 9), arx33401 (130/167, 47.03%, at most 5 of 130), arx26550 (+0.93 [0.24,1.66], 41.4%, −0.74, 75.5%, 100 local labels), arx30243 (312/508, 64.9–73.2%, 63.6 vs 56.4), arx31142 (12.1 [8.5,15.5], 12.6, 38.0), arx26758 (76.9%, 32.5%, 81.5→58.1, 24×, n), arx01006 (0.95 vs 0.85, 2–6 points, 0.80, 0.84→0.75), arx39496 (7%, 99%, 79%), arx27535 (retrospective 0.93/0.96), arx35286 (no ranking), arx33971 (TV 0.219–0.349), arx36965 (92%), arx37470 (32.8/34.2), zen23038928/zen22959854 (Kev scope), jkf87 replication (0.0036, 0.158→0.947 at 0.35, none of five thresholds 0.5), arx32160 framing, new concordance rows (4.3.2 fiction/robots, 4.3.3, Art. 6(3), 8, 9(3), 11(2), 11(5)) against the English text.

---

### R3-fc-1 [major]
**Location:** tab:keyfindings row "Inserted opinions, optimised context and lexical lures steer decisions" (certainty *moderate*); repeated in §7 "Certainty" ("Two reach moderate certainty, that content under review can steer typed decisions …").
**Problem:** The rating breaks its own rule. §3 (sec:appraisal) says a finding rises to moderate only if "at least three independent stronger-design studies agree in direction and at least one *of them* is preregistered or replicated". The table caption has the same rule.
**Evidence:** The cited studies are arx31142, arx01834 and arx01006, all stronger and independent but held-out, not preregistered, and none independently replicated. The other two are arx30243 (weaker, single run) and arx02048 (moderate design, author-built). arx02048 is preregistered but is not one of the three independent stronger-design studies. "3 replicates per cell" (arx01006) and the "identical re-run noise floor" (arx31142) are repeat runs, not replications. The only preregistered stronger-design G2 study, arx28613, is coded S, and the table lists it as a separate finding pointing the other way on injection.
**Fix:** Downgrade the row to *low*. Then change §7 to "One finding reaches moderate certainty …" and recheck the abstract, intro and conclusion wording on certainty. Alternatively, change the rule (e.g. "at least one preregistered or replicated study among those cited") in §3 and the caption. Applying that looser rule only to this row would be post hoc, so say so if you take this route.

### R3-fc-2 [minor]
**Location:** §3 sec:appraisal ("*weaker design* if it was a single run, a case study or non-empirical, or reported no uncertainty") and App. E "Design appraisal" (same wording).
**Problem:** The stated rule and the data disagree. `scripts/merge_coding.py` marks a study weaker only when `size == "none"`. A held-out study that reports sample sizes but no uncertainty ("n only") therefore comes out moderate, but the text says it should be weaker.
**Evidence:** In `quality_appraisal.csv`, arx24965, arx35293, arx36965 and zen23065532 are held-out with "n only" and rated moderate. Their notes say "no intervals" or "intervals only on dev ablations". Under the text's rule they would be weaker, and the counts would be 37 stronger / 13 moderate / 42 weaker of 92, not 37/17/38. arx24965 and arx36965 carry their "moderate" into tab:evidence.
**Fix:** Either reword both places to "or reported neither sample sizes nor uncertainty", which matches the code, or change the code to `size in ("none", "n only")` and regenerate counts.tex, tab:evidence and the quality column of evidence_coding.csv.

### R3-fc-3 [minor]
**Location:** §6, paragraph before tab:checklist: "Items 1--4, 9, 14 and 15 draw on 8 of the 14 items of~\cite{arx32160} (its B1--B2, C1, C3--C4, R1--R2 and T2--T3)".
**Problem:** The list names 9 items, not 8.
**Evidence:** B1, B2, C1, C3, C4, R1, R2, T2 and T3 are 9 items. The five listed as not adopted (B3, T1, T4, R3, C2) bring the total to 14. arx32160's checklist (Table 6) has exactly B1–B3, T1–T4, R1–R3 and C1–C4.
**Fix:** Change "8 of the 14" to "9 of the 14".

### R3-fc-4 [minor]
**Location:** G1 answer box ("against generative comparators \jev{} was better or similar in 6 of 21 pairs, mixed in 10 and worse in 5") and G4 answer box ("\jev{} was better in 9 of 18 pairs and worse in 2").
**Problem:** §4 defines "\jev{}" as the hosted model. These splits include rows where only an open model was measured.
**Evidence:** In G1, arx23959 (open JevLite, "similar") and zen22901853 (open Laya, "worse") are counted. In G4, arx00381 and arx38850 (both open, "better") and zen22901853 (open, "worse") are counted. With hosted-only or both-system rows, G4 would be 7 better / 1 worse of 15.
**Fix:** Write "typed models" instead of "\jev{}" in both boxes, matching §4.8 ("the typed model did better in 23 …"). Alternatively, restrict the counts to rows with system H or H+O.

### R3-fc-5 [minor]
**Location:** tab:keyfindings, column "vs. generative".
**Problem:** The column is meant to come from the cited rows of evidence_coding.csv, but three entries do not.
**Evidence:**
- "Well calibrated on familiar closed-choice tasks …": shows "similar or better". The cited G4 rows are arx37647 better, arx24052 mixed, arx01006 none and arx27607 none. No cited row is "similar", and the "mixed" row is not shown.
- "Escalation to a stronger reasoner …": shows "--". The G6 rows are arx26550 similar and arx24574 similar (arx02046 none).
- "Acceptance on agreement with an independently built rule …": shows "--". arx02048 G6 is "similar", and the thesis itself says "lost no accuracy relative to a frontier LLM".

**Fix:** Change these entries to "better or mixed", "similar" and "similar (G6)".

### R3-fc-6 [minor]
**Location:** §6 "Trade-offs and known limits": "Finally, every element rests on evidence of low or very low certainty (\cref{tab:keyfindings})". Certainty summaries in the abstract ("certainty is mainly low"), §1 thesis ("the certainty of most findings is low"), §8 ("certainty is low for most findings") and §7 ("the rest are low or very low").
**Problem:** The §6 sentence contradicts the table. Element 4 (local calibration, re-certification) rests on "Thresholds set in advance miss error targets", which the table rates *moderate*. Element 3 cites the steering evidence, also rated moderate as the text stands. The summaries also word the same claim in four different ways. The table has 2 moderate, 8 low and 5 very low findings, so "mainly/most … low" understates the share that is very low.
**Fix:** In §6, write "on evidence of at most moderate, and mostly low or very low, certainty". Use one phrasing everywhere, e.g. "certainty is low or very low for most findings".

### R3-fc-7 [minor]
**Location:** §5 T1: "\jev{} was confident on most empathy items yet barely above chance (accuracy 0.38 against 0.33 for three balanced classes), a failure the authors found in a frontier generative model as well~\cite{arx24574}".
**Problem:** Both the comparison and the comparator are misstated.
**Evidence:** In arx24574 (Sec. 4.4, l. 677–679), 0.383 is the accuracy on the 78% of items with confidence ≥ 0.9, and it is compared against "a full-task base rate of 0.371", not 1/3. fig_honesty(d) itself plots it "against the majority base rate". The shared failure (App., Table 20) is with Gemini 3.8 Flash, a flash-tier model, not a frontier one. The authors' frontier models are the Claude arms.
**Fix:** Write "(accuracy 0.38 on the items it answered with confidence ≥ 0.9, against a 0.37 majority base rate), a collapse the authors found in a low-cost generative model as well".

### R3-fc-8 [minor]
**Location:** §8, second paragraph: "whether non-intervention should yield, for consequential decisions, to a human who can suspend them, as data-protection law already requires in its domain".
**Problem:** This overstates GDPR Art. 22, and the round-2 fix in §5 was not carried into the conclusion.
**Evidence:** §5 correctly says Art. 22(3) requires "at least the right to obtain human intervention, to express one's view and to contest the decision" only where a solely automated decision rests on contract or explicit consent, and calls this "close to option (b)". The GDPR does not require a human who can suspend decisions.
**Fix:** Write "… to a human who can suspend them, close to what data-protection law already requires for solely automated decisions".

### R3-fc-9 [nit]
**Location:** §4 G4, "The missing 'insufficient'": "\jev{} chose it for 17 of the 162 items where it was correct (10.5\%)".
**Problem:** "it" reads as items where \jev{} was correct, but the source means items where the "I don't know" option was the correct answer.
**Evidence:** arx34024 l. 397: "for only 10.5% (17/162 …) of the questions for which that [option was correct]". evidence_coding.csv says "17/162 (10.5%) unanswerable items".
**Fix:** Write "for 17 of the 162 items on which that option was the correct answer".

### R3-fc-10 [nit]
**Location:** §3 "Information sources": "Of these, \nCoded{} bear on at least one requirement and are coded below (\cref{fig:corpus}); the rest are background-tier engineering papers."
**Problem:** Not all of the remaining 29 sources are background-tier engineering papers, and tiers are assigned only to arXiv and alphaXiv papers.
**Evidence:** The remainder includes seven records that were read, coded and not tallied because they are non-empirical or measure no typed model: arx01231, arx32160, zen22847531, zen22858286, zen22866847, zen22887464 and zen23064668 (App. B lists them).
**Fix:** Write "the rest are non-empirical items (listed in \cref{app:evidence}) or background-tier engineering papers".

### R3-fc-11 [nit]
**Location:** App. E, arXiv queries: "(version~0.1 relied on the two trackers and web searches on 28--29~September)".
**Problem:** A version label is left over. Everywhere else the paper calls this "the earlier dataset release"~\cite{survey01}.
**Fix:** Write "(the earlier dataset release~\cite{survey01} relied on …)".

### R3-fc-12 [nit]
**Location:** counts.tex `\nKappaLo` = 0.43, used in §3 and §7.
**Problem:** With 2,000 resamples the 2.5% bootstrap quantile is not stable to two decimals.
**Evidence:** Re-running the same percentile bootstrap on coder_agreement.csv with 10,000 resamples gives 0.40, 0.40, 0.42 and 0.42 for four seeds. The upper bound, 0.93–0.94, is stable.
**Fix:** Use 10,000 or more resamples in `merge_coding.py` (or an analytic or BCa interval) and regenerate. The interval will probably read 0.41–0.94.

### R3-fc-13 [nit]
**Location:** §8, second paragraph vs §7 "Beyond one specification".
**Problem:** The two sections list different commitments, and §8 contradicts itself. §7 names three commitments consistent with the evidence: the state of absence, not-moral-labels, and persons vs behaviours. §8 adds "the demand for transparency". The next sentence of §8 then lists "how to reconcile transparency with closed models" as an unresolved tension, and §5 T3 treats transparency as a tension.
**Fix:** Drop "and the demand for transparency" from §8, or add it to §7 with a qualifier such as "as a goal".

### R3-fc-14 [nit]
**Location:** App. A introduction ("quotes every \pol{} passage that this paper cites or paraphrases") and §1 Contributions ("\nPolClauses{} passages", hard-coded 28 in merge_coding.py).
**Problem:** The table has 32 rows over 28 distinct clause labels, so "28 passages" counts clauses, not passages. Two rows are not cited or paraphrased anywhere in the body: \clause{4.3.3.2} ("Real-time correction support") and \clause{4.3.2} ("Thoroughly clear the toxins of hate language").
**Fix:** Say "28 clauses (32 passages)" in §1, or derive the number from the table. Drop the two uncited rows, or say the table also includes "related passages".

### R3-fc-15 [nit]
**Location:** tab:evidence header "Quality" (App. B, generated by gen_evidence_table.py); §4.8 "The shares hardly change …" and §7 "changes the overall shares little".
**Problem:**
- The column holds stronger/moderate/weaker *design* ratings, so "Quality" goes against the round-2 terminology change.
- "Hardly change" understates the shift. The negative share moves from 28.6% overall to 34.2% (stronger design only) and to 23.1% (without Zenodo), about ±5.5 points.

**Fix:** Rename the column "Design". Write "change by at most about six percentage points", or give the percentages.
