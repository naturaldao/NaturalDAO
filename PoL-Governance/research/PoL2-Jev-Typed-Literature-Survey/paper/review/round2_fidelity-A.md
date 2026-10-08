# Round 2: Fidelity review A, covering sections/04_evidence.tex G1–G3 (L1–133, incl. Fig. `fig:fragility`) and sections/02_background.tex

Sources were checked against the raw text: scratchpad/fulltext and scratchpad/g4 (arXiv HTML text of the 2610 papers), and the Zenodo texts in scratchpad/zen and scratchpad/g3. Grey sources were re-fetched with curl on 2026-10-04: docs.typesafe.ai /models, /introduction, /introduction/machine-learning-primer, /model-jaggedness/jev-1.13 and its 2026-09-20 web.archive.org copy, the launch blog, and the jkf87 README plus `results/runs/tensor_trust_hijack/.../metrics.md`. arXiv HTML for 2609.23136 and 2609.22753 was fetched with curl. Decisive numbers were grepped in the raw text, not taken from summaries.

## Verified claims

### 02_background.tex
- L9–13: Jev has three question types; Choice capped at 255 options and returns probabilities and confidence; Noul returns P(yes). Sources: docs /introduction; arx32160 §3.1.
- L15: census of 2,170 projects as of 22 Sep; Choice 81.0%, Noul 72.2%, Score 45.4%. Source: arx30216.
- L19: parallel sampler and RLCD named; calibration property published; architecture, reward and data not published. Sources: launch blog; docs primer ("probability of 0.2 should occur about 20% of the time"); arx24574 ("published the objective but not the reward, the training data, or the architecture").
- L21–24: three readout geometries; Laya uses a ModernBERT marker token; Open-Jev pools with DeBERTa. Sources: arx32160 §3.3 and Table 2; arx26758.
- L25: training-free readouts from instruction-tuned LLMs. Sources: arx00831 abstract (AnyJev, "one prefill"); arx02076 abstract (LLM2Jev, "without training").
- L26: REINFORCE loop whose "reward is the outcome minus the probability placed on the chosen option". Source: arx24574 l.136.
- L29–30: options outside the set are masked before normalisation, which guarantees form, not correctness. Source: arx26758 (but see R2-fidA-10).
- L31: not deterministic, two-decimal grid. Sources: arx32160 §3.1 (4/510 labels changed; grid 0.01–1.00); arx01006 ("not deterministic ... quantised to 0.01").
- L32: nine failure modes; literal reading … contradictory instructions are listed; the 0.72/0.47 complement example is in the 2026-09-20 archive and absent from the current page. Source: jaggedness page, both versions.
- L35: $0.042/Mtok input, output free, 70–500 ms. Sources: docs /models; launch blog ("70ms-500ms").
- L36: client-side medians of about 150–500 ms. Sources: arx26550 (0.15 s, 0.27 s); arx27535 (213 ms); arx28919 (250 ms); arx27331 (0.406–0.500 s); arx23136 (408.9 ms). arx00346 reports 138 ms, which is within "about".
- L37: 63× pooled at list prices and 12.1× under GPT-4o-mini repricing. Source: arx29429 §4.5. Luna about 8×; Astra 455× and 312×. Source: arx27535.
- L38: DeepSeek "has the lower billed interpretation fee". Source: arx23136 §VI-C. Jev variant takes "1.4 to 2.1 times as long as Qwen scoring". Source: arx00437 §4.2 (see R2-fidA-9).

### 04_evidence.tex, G1
- L22–24: arx29429 has 10 failure types, 44 benchmarks, 5 targets and 7,193 instances; AUROC 0.886 [0.821, 0.952] over 31 benchmarks; 25/31 against TF-IDF and length baselines; $0.30 vs $18.96 on 19 benchmarks; +0.006 [−0.004, +0.015]. Round-1 items fidA-4 and fidA-5 are fixed.
- L25: relational failures; context fields encode the label. Source: arx29429.
- L26: arx00346, jev-1.13.0; seven open checkpoints; Jev is the most accurate typed model; out-of-scope AUROC 0.921 [0.901, 0.940]; BERT-base 0.940 and BGE-small LR 0.948 vs Jev 0.913 on CLINC-150.
- L27: arx34862 F1 77.8 vs 74.1; lower precision; Jev wins 2/4; version not reported. Round-1 fidA-12 is fixed for this source.
- L30: median F1 0.706→0.822; on validated labels 0.721 vs 0.694. Source: arx29429 §4.4. Round-1 fidA-3 is fixed.
- L31: 5 sub-experiments; 1,155 items; median absolute difference 0.0036; TensorTrust-hijack AUROC 0.9476, F1@0.5 0.158; no fitted threshold equals 0.5. Source: jkf87 README (but see R2-fidA-1).
- L32: JEVDB-Flash uses jev-1.13.0 at a fixed 0.5 threshold; mean F1 66.3/64.0/63.2%; per-predicate range 23.8–88.9%. Source: arx02046 §4.3.
- L33: Laya-322M FPR 35.71%→0.42% on its own split; SafetyBench-ZH 60.33→56.81; replay recovers it. Source: arx33671. Round-1 fidA-10 is fixed.
- L36: R-Judge 0.961 vs Laya 0.533; all 130 no-EI injections missed at p<0.1; 1 benign false flag; 130 of 167 misses at ≥0.95. Source: arx33401. Round-1 fidA-7 is fixed.
- L37: weighted sensitivity 0.999 and specificity 1.000; "zero false positives among twenty-seven adjudicated true negatives"; Stage C "14 of 42" confirmed; jev-1.13.0. Source: arx00213 Table 3 and §Limitations.
- L38: Laya 0.31 vs LLM 1.00, n=220. Source: zen22901853. Round-1 fidA-6 is fixed.
- L41: zero-shot 9.80% vs training-majority 22.79%; 150 examples 34.50% vs RF 72.70% on week 5 ("38.20 points below RF"). Source: arx00376.
- L42: NSL-KDD, k=1: precision 0.953, recall 0.778; Gemini recall 82.6%; 22× lower estimated cost. Source: arx01079 Tables.
- L43: macro-F1 0.63 vs rule tree 0.59 (means over 4 sealed sets); two frontier LLMs significantly better (glm-5.2, deepseek-v4-pro). Source: arx02048 §3.1 and §3.4 (but see R2-fidA-7).

### 04_evidence.tex, G2
- L61–62: 9/510 (1.8%); "ignore previous" reduces the effect; 18/510 = 3.5% [0, 10]; exploratory hedge. Source: arx28613. Round-1 fidA-13 is fixed.
- L65–66: budget 64; median 31 words among successful contexts; checked by a separate model; 312/508 = 61.4% [57.1, 65.5]; 229 at ≥0.7; others 64.9–73.2% on their own items; open Jev-style interface on Qwen3-1.7B. Source: arx30243. Round-1 fidA-20 and fidA-21 are fixed.
- L67: opinion 12.1% [8.5, 15.5], tied with authority 10.1%; command in the question vs opinion in the state; benign rewording within noise. Source: arx31142. Round-1 fidA-19 is fixed.
- L68: misleading S-known steps 36% correct, lure 56%, 89% of errors to the lure (seen games). Source: arx01834 §5.1; jev-1.13.0.
- L69: HotpotQA 0.84→0.75 with confidence at 0.83. Source: arx01006 §4.
- L72–73: three attackers, 25/27, fourth turn on average, one objective, untrusted marking made no difference, "focused, directional study". Source: Check Point blog. Round-1 fidA-23 is fixed (but see R2-fidA-3 on version).
- L74: concealed manipulation cyber recall 0.34 (training-free methods); 21 of 76 accepted E4c ("look-alike family C") windows were attacks. Source: arx02048 §3.5 and §2.
- L75: Kev-0.8B 5/45 and 12/45; multi-answer change. Sources: zen22959854 and zen23038928. Round-1 fidA-15 and fidA-16 are fixed.
- L79: 63.6% vs 56.4% (140 decisions). Source: arx30243 §4.3.

### 04_evidence.tex, G3
- L105–107: Laya 76.9% vs 6.5%; AUC 0.938→0.232; Jev 32.5%; floor at most 1.33% on 300; AUC 0.815→0.581. Source: arx26758. Round-1 fidA-25 and fidA-26 are fixed.
- L108: jev-1.13.0, 50.5 [46.2, 54.7], floor 1.3; 97.2 on conversation derailment; digit and random-string conditions within 2.8; Laya 91.3; Kev-9B, Nimble-9B, decider-2b and this-that-model-1.0 at 4.2–6.5 ("four larger decoder-based checkpoints"). Source: arx00346 §5.2.
- L109: "witness" renaming "raised its probability by up to 0.28"; jev-1.13. Source: zen22980293.
- L112: 38.8% and 51.3% on neutral; 74.4% ordinal agreement on six datasets; nominal agreement ≥95.6%. Source: arx38827. Round-1 fidA-28 is fixed.
- L113: reversal changes 32.8% and 33.4% of answers; 0.138 and 0.183 after rotation averaging. Source: arx00831 §3–4 (but see R2-fidA-8).
- L114: spread at most 0.08 across runs. Source: zen23023694. "Small exploratory study". Source: zen22864020. Round-1 fidA-30 is fixed.
- L115: distractor permutations change accuracy by at most 0.013. Source: arx00346 §5.2.
- L118–119: typical 3%; White 51% of first picks; no counterbalancing. Source: Simmons blog. Round-1 fidA-32 is fixed.
- L120: 24 VSM items, 288,000 answers, 0.08, 87% and 62%; jev-1.13.0. Source: arx36399.
- L121: Sol 0.359 vs 0.639; all Jev interactions below the "contestable absolute reference of 0.05"; distinct rubric. Source: arx35286. Round-1 fidA-39 is fixed.
- L124: "Other languages, including CJK scripts, are handled but not equally well". Source: docs /models. Round-1 fidA-34 is fixed.
- L125: Jev 1.9% (order) and 1.7% (script), n=323; Laya 10.8–20.6%. Source: zh-decision-bench v0.2. Round-1 fidA-35 is fixed.
- L126: CJ-Bench 69.20 vs 68.35; specialists reach 92.0% of Jev's average across domains. Source: arx36965. Round-1 fidA-36 is fixed.
- L127: Polish 0.884 vs 0.780; JevBench 0.861 vs 0.740. Source: zen23022986. Round-1 fidA-37 is fixed.
- L128: all three models degrade on low-resource languages. Source: arx37647 abstract.

### Round-1 items out of scope
Round-1 items fidA-1, 2, 8, 9, 11, 14, 17, 18, 22, 24, 29, 31, 33, 38 and 40 refer to text that has been removed from G1–G3 or moved to G4 or later sections. They were not re-checked here.

---

## Findings

### R2-fidA-1 [minor]
- Location: sections/04_evidence.tex:31
- Claim: "F1 was 0.158 at threshold 0.5 and 0.947 with a threshold fitted on ten labels"
- Source says: jkf87 `results/runs/tensor_trust_hijack/.../metrics.md`, row `naive:noul`: "F1 cv 0.947 | thr cv 0.35/0.35". The legend says: "F1 cv = fixed-denominator F1 with a threshold chosen on the other half (2-fold by item, grid 0.05-0.95)". The README mentions "라벨 10건" (ten labels) only when describing the original paper's claim.
- Problem: in the replication, 0.947 comes from 2-fold cross-validation, so each threshold is fitted on about 150 labelled items, not ten. The ten-label procedure belongs to arx29429. The current wording overstates how little data is needed to repair the threshold.
- Suggested fix: "...and 0.947 with a threshold fitted by two-fold cross-validation (0.35 in both folds)..."

### R2-fidA-2 [minor]
- Location: sections/04_evidence.tex:89 (Figure `fig:fragility` caption)
- Claim: "``Jev (hosted)'' is TypeSafe's API; these studies do not report its version."
- Source says:
  - arx29429 pins `jev-1.13.0` (§3), and arx30243 reports "Jev 1.13.0".
  - The jkf87 replication used `jev-latest` (README l.7).
  - Only arx26758 (panels c–d) names no version.
- Problem: the caption is wrong for panels (a) and (b). It also contradicts the L6 convention, which reads "jev-1.13 unless stated".
- Suggested fix: "``Jev (hosted)'' is TypeSafe's API: jev-1.13.0 in~\cite{arx29429,arx30243}, the jev-latest alias in~\cite{jkf87_2026replication}, and not reported in~\cite{arx26758}."

### R2-fidA-3 [minor] (round-1 fidA-12, only partly fixed)
- Location: sections/04_evidence.tex:6, applied at L31, L72, L118 and L126
- Claim: "where a study reports a version it is \texttt{jev-1.13} unless stated, and where it reports none we say so."
- Source says:
  - Check Point blog: no version.
  - Simmons blog: "typesafe-ai/jev via Vercel AI Gateway", no version.
  - jkf87: `jev-latest`, and the README says "논문이 어느 Jev 버전으로 쟀는지 모릅니다".
  - arx36965: cites "Jev (Almeida, 2026)" with no version string.
- Problem: the convention was added, but the text does not apply it. Only arx34862 (L27) carries "(version not reported)". The four results above silently inherit jev-1.13.
- Suggested fix: add "(version not reported)" after the citations at L72, L118 and L126. At L31 add "(run on the jev-latest alias)".

### R2-fidA-4 [nit]
- Location: sections/02_background.tex:26
- Claim: "Open models train with cross-entropy plus a Brier-score term~\cite{arx23886,arx23959}"
- Source says: arx32160 Table 2 lists cross-entropy + Brier only for this-that-model-1.0 and JevLite. Visual Jev uses "Answer SFT"; SemIf is "frozen"; PixelJev uses "RL for calibrated decisions"; Laya uses "Few-shot LoRA; temperature"; Open-Jev is "n.r.".
- Problem: the training recipe of two models is presented as true of open models in general.
- Suggested fix: "Two open decoders (this-that-model-1.0, JevLite) train with cross-entropy plus a Brier-score term..."

### R2-fidA-5 [nit]
- Location: sections/02_background.tex:38
- Claim: "inside a multi-step agent loop the round trip to the hosted model made it 1.4--2.1 times slower than a local open scorer~\cite{arx00437}"
- Source says: arx00437 §4.2: "The TypeSafe Jev variant takes 1.4 to 2.1 times as long as Qwen scoring across all eight tasks, including API communication". App. B.4: "E2E latency includes network and API service time."
- Problem: the source reports end-to-end time that includes the API round trip. It does not attribute the slowdown to the round trip.
- Suggested fix: "...the hosted model's end-to-end time, including the network round trip, was 1.4–2.1 times that of a local open scorer~\cite{arx00437}."

### R2-fidA-6 [nit]
- Location: sections/04_evidence.tex:43
- Claim: "and beat supervised models on attack sub-types they had not been trained on"
- Source says: arx02048 abstract: "exceeded the supervised classifier by 0.36-0.42 on event subtypes absent from its labels". §3.2: the classifier was "R2 retrained without the evaluated subtype", with subtypes drawn from all four cause classes (cyber, fault, transient, sensor).
- Problem:
  - The held-out subtypes are event subtypes of every class, not only attacks.
  - There is a single supervised classifier (R2), not several "models".
- Suggested fix: "...and beat a supervised classifier by 0.36–0.42 macro-F1 on event sub-types withheld from its training labels..."

### R2-fidA-7 [nit]
- Location: sections/04_evidence.tex:115
- Claim: "a 37-dataset benchmark found its Choice answers robust to option rotation on the subjects tested~\cite{arx37647}"
- Source says: arx37647 §4: "we rotated the answer options so that every option moves to a different letter. If Jev had memorized answer positions, accuracy would drop, but it stays at 94.3%". The test covers only the calculation-heavy MMLU and C-Eval subjects.
- Problem:
  - The source reports that accuracy was unchanged. It does not report that answers were unchanged, and the test was designed as a memorisation probe.
  - Calling the answers "robust" claims answer-level invariance that the source does not measure.
- Suggested fix: "...found its accuracy unchanged when the options were rotated (94.3%, calculation-heavy MMLU subjects)~\cite{arx37647}."

### R2-fidA-8 [nit]
- Location: sections/04_evidence.tex:113
- Claim: "Reversing the option list changed about a third of the answers of typed readouts from open LLMs; averaging over rotations reduced this to 14--18\%"
- Source says: arx00831 abstract: "On a 20-option task, reversing the option list changes the answer on 33% of items, averaged over eleven models". §4.2 gives "0.138 of banking20 items and 0.183 of newsgroups items after the average".
- Problem: the 20-option scope is dropped. With many options, order effects are larger than for the few-option questions the survey has in view.
- Suggested fix: "On two 20-option tasks, reversing the option list changed about a third of the answers..."

### R2-fidA-9 [nit]
- Location: sections/02_background.tex:29
- Claim: "Because the scores of options outside the declared set are masked before normalisation, every answer is a valid member of the option set~\cite{arx26758}."
- Source says: arx26758 §2: "For the open-weight models this holds by construction, since scores of candidates outside O are masked before normalization. For Jev it is the documented behavior".
- Problem: the masking mechanism is stated for all typed models, including the closed hosted model. For hosted Jev the source treats it as a documented property, not an observed mechanism. This sits awkwardly with L18 ("The hosted model is closed").
- Suggested fix: "In open models the scores of options outside the declared set are masked before normalisation, and for hosted Jev the vendor documents the same guarantee, so every answer is a valid member of the option set~\cite{arx26758}."

---

## Summary
I checked about 110 source-attributed claims in G1–G3 and in the Background section against raw source text. Every number transcribed from the 15 new 2610 papers (arx00213, 00346, 00376, 00437, 00831, 01006, 01079, 01834, 02046, 02048, 02076) and from the vendor documentation matched. Of the 25 round-1 findings whose text remains in scope, 24 are fixed. The exception is fidA-12: the "version not reported" convention was added at L6 but is applied only to arx34862 (R2-fidA-3). The new findings are mostly about scope and attribution, not numbers:
- R2-fidA-1: the replication's 0.947 F1 came from a two-fold cross-validated threshold, not a ten-label fit.
- R2-fidA-2: the figure caption says no version is reported, but two of the three sources pin jev-1.13.0.

Counts: 0 major, 3 minor, 6 nit.
