# Round 1 — fidelity-B (§4 G4–G7 + tab:negative, §2, §5)

Reviewer: independent fidelity lens B. Sources: local full texts (scratchpad/fulltext), arXiv HTML (v as in corpus.bib), grey URLs in grey.bib, Zenodo record descriptions only (‡), and the primary legal texts for the regulatory paragraph. Date of checks: 2026-10-04.

## Claims verified as correct

G4 (04_evidence.tex)
- l.188 Grazian: 3,066 WiC pairs, ECE 0.027, nearly all bins within sampling error.
- l.189 arx26550: error-detection AUROC 0.875 (Jev) vs 0.894 (GPT-6) on RewardBench.
- l.190 arx37647: 346,009 requests, 37 datasets; Jev > Qwen3.8-27B on 27 datasets; pooled Choice ECE 0.028; ANLI 73.9% → 86.9% at 50% coverage.
- l.191 arx24881: AUROC 0.666 [0.638, 0.691] on 1,718 text responses; baselines 0.532–0.649 on 1,953; PINOCCHIO 0.868 on identical rows; 32,419 training responses.
- l.194 arx24052: n = 2,416 blind labels; slope 1.63; Spiegelhalter z = −5.3; ECE 0.0231 → 0.0069 (factor 3.3).
- l.195 arx27607: isotonic recalibration on hold-out, ECE 0.1235 → 0.0077.
- l.198 arx37647: mean P(yes) 0.209 vs observed 0.041; UNFAIR-ToS micro-F1 0.499 → 0.748.
- l.199 arx33843: independent, preregistered; Laya under-confident, gap −0.214; ECE 0.204 → 0.037; gate 0.140 vs 0.10; 120-claim probe 0.617.
- l.200 zen23032384‡: ECE 0.076 → 0.339; mean confidence 0.807 (but see fidB-24).
- l.201 Molas: calibration need not transfer to production distribution; treat as scores, recalibrate.
- l.205–207 arx33209: 480 pairs; MAD 0.064 [0.055, 0.072]; Qwen3.8-27B first-token 0.293; noise floor 0.013 (≈5×); single-label sum 1.14; 0.142 vs 0.018 by confidence group.
- l.208 typesafe_jaggedness: 0.72 / 0.47 example (archived 2026-09-20 version only; see fidB-20).
- l.209 arx37470: 1,000 worlds; 32.8% at c = 0.10; Jev loss 0.1336 vs always-defer 0.10; 745/1,000 repeats within 0.02 (see fidB-7 for scope).
- l.210 arx33971: 36,000 questions per system / 72,000 total; TV 0.219–0.349; CLINC150 −22.9 (Jev) / +21.3 (Laya).
- l.211 yurin: 738,164 answers; formula reconstruction; 10 identical calls 0.84–0.88 same label; 9 calls split 7:2 (see fidB-5 for the 0.20→0.58 figure).
- l.214–216 arx35342: Sys1Cal-v1, three primitives; suppressed-P(U) hypothesis; median soft accuracy 0.771 → 0.903 (calibrated) and 0.978 (T/U/F).
- l.219–220 arx34024: 17/162 = 10.5% (CI 6.7–16.2); GPT-6 Sol 8.6%; 17 of 18 correct; 52 of 100 fictional-organ items substantive.
- l.221 zen22848952‡: conflict 0.50–0.57 vs ignorance 0.46–0.48; Choice separated both in completed cases (but see fidB-23).
- l.222 arx38850: Qwen3-1.7B; 81.1% vs 19.4% (GRPO+KL+TS) at ≤5% error, similar accuracy; cannot beat CE on annotator disagreement (ChaosNLI).
- l.223 alphaRAG: five-way conflict classification; wrong-answer confidence flat 0.56–0.58 across prompts.

G5
- l.253–254 Willison: justification caveat, "floating point number", spam-signal example, bias "front and center", job-applicant ranking.
- l.255 zen22847531‡ (no abstract), zen22866847‡ (AI-assisted dialogue; schema/option-set relocation, hedged "can").
- l.256 zen22846597‡: "no … una autorización de uso decisorio" (translation; see fidB-29).
- l.259–260 arx24965: Jev + 5 configurations fully correct; 7 wrong selections by 3 comparators; all reference labels "inconsistent".
- l.261 arx27678: 10 models; all-12 correctness (4 conditions × 3 repeats); Jev lowest hosted baseline 77.38%; 5 stably wrong; "agreement does not establish correctness".
- l.266 zen23064668‡: marginal calibration not preserved under latent regime shift; permutation-invariant audits have zero power.
- l.270–272 arx32160: 28 papers 19–24 Sep; no independent readout accuracy advantage; latency/cost clearest; 14 items, nine scored; B1 5/26, T3 1/27, C4 3/20, T2 17/26, R2 15/27, C1 13/17.

G6
- l.289–294 arx26550: 16 judges (14 generative + 2 RMs); within 3 points at 0.36% fee, 0.15 s; +0.93 [0.24, 1.66] at 41.4% on 1,610 pairs; 83% RewardBench; JudgeBench −0.74 [−2.22, 0.74]; earlier "99.4% at 56.8%" on 510 pairs, change attributed to composition; live runs matched GPT-6 at 75.5% fee; AUROC 0.76 / 0.498.
- l.297–300 arx29769 v2: 7 benchmarks, 9 panels; AUROC 0.57–0.70 on six ordinal panels, 0.49 on ELLIPSE; 84 items, 242/252 = 96.0% vs 50.3%; ≤1.5 (2.0 oracle); below best single judge on 6/9 (main setup; see fidB-13).
- l.303–304 arx26532: 0.95 success, 72.7% fewer strong calls, 100 frozen tasks (vs B0 0.88, McNemar p = 0.039); BFCL 98.4% / 52.0% (see fidB-15 on 0.778).
- l.305 arx26532: τ²-style, Flash self-escalation cascade cheaper and numerically more successful (unresolved).
- l.309–310 arx33401: symmetric policies automate nothing on WAInjectBench, 7.63% on R-Judge; independent thresholds 47.03% (110 blocks, 1 allow); judges catch ≤5 of 130 misses at ≥0.95; AgentHarm NLL 0.481 → 2.163.
- l.311 arx33689: ≤0.143 (Jev); Laya-FT 0.801 act-and-wrong; 19 labels (see fidB-14).
- l.313 zen22952571‡: Brier 0.0263 vs 0.0555; 6 false allows removed, 29 correct allows withheld; no human adjudication.
- l.314 zen22922769‡: 60.8% avoidance; 181/204 vs 180/204; 8 accepted errors bypassed escalation.
- l.315 arx30706: ≤0.5 questions per conversation, +14.1 points; wrong on 19% of ABCD cases at confidence ≥0.99.

G7
- l.342–344 arx27535: once per unique state; 1M agents × 20 steps in 0.9 s; 9,070 participants; 1.7% anchors; 0.0305 → 0.0180 (−41%); coverage 0.93/0.96 vs 0.29/0.36 on 37 unseen studies; primary policy value 0.0027 [−0.0118, 0.0169]; raw effect MAE worsened on SocSci210.
- l.348 arx36399: no-persona answers resemble American personas; Saudi–US gap 87% (English) vs 62% (Arabic).
- l.353–354 arx24052: "no rule says how much output a human must check"; median 0.26 κ understatement.
- l.357–359 arx28919: 13.4% / 20.8%; 10,000 seats; 46 synthetic conversations; ~10,000 public sessions; 21 harnesses; Jev weights not published, not offered for self-hosting; classifier-agnostic, self-hosted encoder fallback.
- l.362–363 arx30216: 2,170 projects by 22 Sep; 175 (8.1%) safety/governance, ~3.5% stars (2.6% + 0.9%); routing/automation 41.4% of stars; LLM-agent labelling.

tab:negative
- l.387 arx26758: Laya AUC 93.8% → 23.2%; Jev 81.5% → 58.1%; 0% type errors.
- l.388 arx30243: 61.4% (312/508); 229 at p ≥ 0.7 (hosted Jev 1.13.0) (see fidB-17 on hedge).
- l.389 arx31142: 12.1% [8.5, 15.5]; authority impersonation 10.1% (statistically tied).
- l.390 arx33401: 130 no-EI misses, unsafe p < 0.1; ≤5 of 130 at ≥0.95.
- l.393 simmons: "White" 51.12% of first picks (Jev).
- l.394 arx24574: 78% of items at ≥0.9, accuracy 0.383, three classes of 166 each.
- l.395–397 arx33209, arx35342, arx34024 as above.
- l.399 arx36399; l.400 arx38827 (hosted JEV 1.13: 38.8% predictions, 51.3% of 1,603 errors); l.401 arx37470; l.402 arx29769; l.403 arx24965; l.404 arx32160; l.405 arx28919.

§2 (02_background.tex)
- l.9 typed output, exact option set, no free text (arx23886, arx26758, arx32160).
- l.10–13 TypeSafe docs: Choice up to 255 options with probabilities + confidence; Score ordered levels; Noul P(yes).
- l.14 many questions per call (arx29429 "in a single call"; arx28919 "all answers in a single query").
- l.15 arx30216: Choice 81.0%, Noul 72.2%, Score 45.4% of 2,170 projects.
- l.19 launch post "parallel sampler" + RLCD; primer's output contract; architecture/reward/data/weights unpublished (arx24574 l.133, arx28919).
- l.22–24 readout families (arx32160 §3.3: decoders / Laya marker token / Open-Jev pooled name+definition; this-that-model, JevLite, Visual Jev).
- l.28 masking before normalisation (arx26758 §1).
- l.30 non-determinism (4/510; ≤1.33%) and two-decimal grid (arx32160 §3.1).
- l.31 nine failure modes (live page still lists nine incl. the seven named).
- l.34 $0.042/Mtok input, output free; 70–500 ms.
- l.35 client-side medians ≈150–500 ms: 26550 0.15 s; 27535 213 ms; 28919 250/420 ms; 22753 0.27–0.42 s (single requests); 23136 356–409 ms; 27331 0.42–0.50 s.
- l.37 arx23136: DeepSeek billed less than Jev.
- l.38 arx32160 audit conclusions.

§5 (05_synthesis.tex)
- l.13 arx24574 empathy failure (see fidB-21 for hedge).
- l.19–20 arx35342, arx33209, arx26758, arx34024 (one in ten), arx38827.
- l.26 closed hosted model; l.27 arx22753 (SemIf ≤16 options, Laya rejects 254-option catalogue; replicas less accurate), arx26758 (Laya most severe inversion), arx33401 (Laya R-Judge AUROC 0.533 vs Jev 0.961).
- l.28 arx36965 (initialised from Laya Multilingual; +1.24% on general domain, own benchmark), arx38850.
- l.33 arx29769, arx33401 (≤5 of 130), arx31142 (gate at 0.8 passes 12.6% of flips), zen22922769‡.
- l.42 arx36399, arx31142 (observer opinion).
- l.47 AI Act Art. 5(1)(f) (emotion inference in workplace/education) and Art. 14 (effective human oversight of high-risk systems): accurate.
- l.49 Santa Clara Principles 2.0 (Notice incl. reasons; Appeal): accurate.

## Findings

### NEW-fidB-1 [major]
- Location: sections/04_evidence.tex:211
- Claim in paper: "found that adding zero-probability dummy options raised reported confidence from 0.20 to 0.58"
- Source says: bernoulli.app (Yurin): "At fixed top probability of 0.60, confidence runs from 0.20 at two options to 0.58 at twenty." (derived from the reconstructed formula, not an observed manipulation)
- Problem: A value computed from the reconstructed formula is presented as an observed experimental effect of adding dummy options. The source does not report an experiment in which dummy options were added and confidence measured.
- Suggested fix: "An analysis of 738,164 Choice answers reconstructed the vendor's confidence formula, which implies that at a fixed top probability of 0.60 reported confidence rises from 0.20 with two options to 0.58 with twenty, so padding the option set inflates confidence; it also found that ten identical requests …"

### NEW-fidB-2 [major]
- Location: sections/04_evidence.tex:229 (polbox), also 05_synthesis.tex:20
- Claim in paper: "a model that cannot separate conflict from ignorance~\cite{zen22848952}" (and §5: "'absent' must be kept distinct from 'contested', which a single probability cannot do~\cite{zen22848952}")
- Source says (record description, Zenodo 22848952): Choice schema "separates both cases with probability 1.0 in all four completed cases"; a third experiment found "an unanticipated directional bias"; "The central finding is therefore not that Jev collapses per se".
- Problem: The polbox states that Jev cannot separate conflict from ignorance. The record says the opposite for Choice and explicitly disclaims "collapse per se". Only the binary Noul probabilities share a band. The §5 phrasing ("must be kept distinct … which a single probability cannot do") is a normative conclusion that the description does not state. Combined with the ‡ status (description-level only), this is an overstatement.
- Suggested fix (polbox): "a single yes/no probability that does not separate conflict from ignorance (although a Choice question naming both states did, in four completed cases)~\cite{zen22848952}\zmark{}". (§5): "… and a single yes/no probability placed 'conflict' and 'ignorance' in the same band, whereas a Choice question naming both separated them~\cite{zen22848952}\zmark{}; 'absent' should therefore be kept distinct from 'contested'." Add to l.221 that the record itself reports a directional bias and does not claim a collapse per se.

### NEW-fidB-3 [minor]
- Location: sections/04_evidence.tex:190
- Claim in paper: "The largest benchmark so far, 346,009 requests over 37 datasets, found Jev more accurate than an open 27B model on 27 datasets and well calibrated for Choice questions (pooled ECE 0.028)"
- Source says: arx37647 §4.2: "Jev scores higher than Qwen3.8-27B on 27 datasets and lower on 9, with one tie"; "11 of Jev's leads have non-overlapping 95% bootstrap intervals, none of Qwen's does"; §4.3 pooled ECE 0.028 over 22 Choice datasets / 279,925 answers, three datasets supply 63% of answers, unweighted per-dataset mean ECE 0.061. The paper never calls itself the largest.
- Problem: "largest benchmark so far" is the survey's own, uncited and undated claim. The 27-dataset lead omits that only 11 leads are clearly separated. The pooled ECE is dominated by three datasets, and the unweighted mean is twice as large.
- Suggested fix: "The largest benchmark in our corpus, 346,009 requests over 37 datasets, found Jev more accurate than an open 27B model on 27 datasets (11 with non-overlapping intervals) and well calibrated for Choice questions when pooled (ECE 0.028; unweighted mean over datasets 0.061) …"

### NEW-fidB-4 [minor]
- Location: sections/04_evidence.tex:191
- Claim in paper: zero-shot correctness estimation paragraph placed under "Evidence of usable calibration"; "its authors conclude that it is not a usable correctness signal on its own"
- Source says: arx24881 §4: Jev "does not provide a usable correctness signal off the shelf"; Table: Jev ECE 0.133 (vs 0.009–0.034 for recalibrated baselines).
- Problem: The paragraph heading presents this as evidence of usable calibration, but the source reports poor calibration (ECE 0.133) and a negative conclusion. "On its own" also shifts the meaning of "off the shelf" (without training).
- Suggested fix: Move the sentence to "Calibration is local" (or a new "Limits" sentence) and write "… its authors conclude that it does not provide a usable correctness signal off the shelf, and its ECE (0.133) was worse than that of recalibrated baselines~\cite{arx24881}."

### NEW-fidB-5 [minor]
- Location: sections/04_evidence.tex:194
- Claim in paper: "pooled recalibration on the same labels reduced ECE from 0.0231 to 0.0069"
- Source says: arx24052 §4.2: "Out of fold, the pooled calibration error falls from 0.0231 to 0.0069 under Platt scaling" (split by narrative, 50 repeats; CI [0.0045, 0.0112]); "The pooled map is a demonstration and the per-variable maps are the deployment evidence." Slope 1.63 is read as under-extreme ("hedges toward the middle").
- Problem: "on the same labels" reads as in-sample, which understates the evidence. l.197 then tells readers that ECEs differ in in/out-of-sample status without saying which this one is. The source's own caveat that the pooled map is only a demonstration is dropped. Also, the direction of the miscalibration (under-extreme, not over-confident) is not given, which matters for the G4/G7 over-confidence narrative.
- Suggested fix: "raw Jev was not well calibrated (calibration slope 1.63, Spiegelhalter z = −5.3: probabilities too close to the middle rather than over-confident); out-of-fold Platt recalibration on the same label set reduced pooled ECE from 0.0231 to 0.0069, a factor of 3.3, which the authors present as a demonstration, with per-variable maps as the deployment evidence~\cite{arx24052}."

### NEW-fidB-6 [minor]
- Location: sections/04_evidence.tex:196
- Claim in paper: "Both studies conclude that probabilities must be recalibrated on the target data, and \cite{arx24052} adds that each model must be audited separately."
- Source says: arx27607: "Probability thresholds benefit from calibration on the intended data"; "These results support task-specific calibration before using probability thresholds." arx24052 abstract: "Calibration varies by model rather than by paradigm, so each model must be audited." arx27607 also shows the open NLI baseline improving the same way (0.1072 → 0.0063).
- Problem: "Must" overstates arx27607. "Separately" is the survey's addition. The radiology improvement is not specific to Jev.
- Suggested fix: "Both studies recommend calibrating probabilities on the intended data before thresholding (in the radiology study the open NLI baseline improved similarly), and \cite{arx24052} adds that calibration varies by model, so each model must be audited."

### NEW-fidB-7 [minor]
- Location: sections/04_evidence.tex:209
- Claim in paper: "Jev's yes/no and Choice interfaces led to different act-or-defer decisions on 32.8% of cases at a deferral cost of 0.10, its decision loss (0.134) was worse than always deferring (0.10)"
- Source says: arx37470 §6: "For binary Event/Choice at c = 0.10, actions change on 14.9% of roots for Kev, 34.2% for posttrained, and 32.8% for Jev"; "On the canonical task at c = 0.10, oracle loss is 0.0897: only 0.0103 average improvement is available below always defer … Jev's loss is 0.1336"; Kev's loss (0.1090) also exceeds always-defer.
- Problem: The loss figure belongs to the canonical multiclass task, not to the yes/no-vs-Choice comparison it is attached to. The benchmark leaves almost no headroom over always-deferring (0.0103), and other configurations also exceed always-defer or show similar or higher interface gaps (posttrained 34.2%). Without this, the result reads as Jev-specific.
- Suggested fix: "… on 32.8% of cases at a deferral cost of 0.10 (a post-trained open model: 34.2%); on the canonical multiclass task, where always deferring is nearly optimal (oracle 0.090), Jev's decision loss (0.134) exceeded that of always deferring (0.10) …"

### NEW-fidB-8 [minor]
- Location: sections/04_evidence.tex:210 and 265
- Claim in paper: l.210 "\jev{}'s fine-grained answers and the answers reconstructed from its coarse and conditional questions differed by a mean total variation of 0.22--0.35 … while the same procedure raised Laya's accuracy by 21.3 points"; l.265 "disagree with the direct fine-grained answer in a large share of cases"
- Source says: arx33971 abstract: "mean category-level total variation ranges from 0.219 to 0.349 for Jev and from 0.424 to 0.689 for Laya"; CLINC150 Laya 23.1% → 44.4%, Jev 91.0% → 68.1%.
- Problem: (a) TV is measured at the category (parent) level, not between fine-grained answers. (b) The contrast with Laya omits that Laya is even less coherent (TV 0.42–0.69) and starts from 23.1% accuracy, so readers may infer that Laya composes better. (c) l.265 "in a large share of cases" turns a mean TV into a case-share that the paper does not report.
- Suggested fix: l.210: "… the category-level probabilities asked directly and those reconstructed from its fine-grained answers differed by a mean total variation of 0.22–0.35 (Laya: 0.42–0.69), and reconstruction lowered Jev's accuracy on CLINC150 by 22.9 points (91.0% to 68.1%), while raising the much weaker Laya's by 21.3 points (23.1% to 44.4%)". l.265: "… disagree substantially with the direct answers (mean category-level total variation 0.22–0.35)".

### NEW-fidB-9 [minor]
- Location: sections/04_evidence.tex:200 and table l.398
- Claim in paper: "ECE rising from 0.076 on items where human annotators agree to 0.339 where they disagree"
- Source says (Zenodo 23032384 description): calibration error rose from 0.076 to 0.339 between the lowest and highest quartiles of annotator entropy; figures are for Choice probabilities, and Noul "degraded less (verdict inconclusive)".
- Problem: "agree / disagree" is a binarisation of entropy quartiles. Restricting the result to Choice and the inconclusive Noul result are omitted, which overgeneralises a ‡ source.
- Suggested fix: "… found the ECE of \jev{}'s Choice probabilities rising from 0.076 on the quarter of items with the most annotator agreement to 0.339 on the quarter with the least (mean confidence 0.807 there; the Noul result was inconclusive)~\cite{zen23032384}\zmark{}". Table: "Choice ECE rises from 0.076 to 0.339 from most- to least-agreed items".

### NEW-fidB-10 [minor]
- Location: sections/04_evidence.tex:261
- Claim in paper: "\jev{} had the lowest baseline accuracy among the hosted models (77.38\%) and five stably wrong answers"
- Source says: arx27678 §4.2: "Sonnet keeps 24 of 30 anchors correct across all twelve responses, followed by Jev with 23"; Jev's mean correctness on the stability panel 79.44%.
- Problem: In a paragraph arguing that rankings change, the paper reports only Jev's weak side. On the persistent-correctness criterion Jev ranked second of ten. This omission is precisely the point of the source.
- Suggested fix: "… gave different orders: \jev{} had the lowest baseline accuracy among the hosted models (77.38\%) but ranked second in all-condition correctness (23 of 30 targets), with five targets stably wrong; the authors caution …"

### NEW-fidB-11 [minor]
- Location: sections/02_background.tex:36
- Claim in paper: "studies report cost reductions of one to two orders of magnitude, for example 63$\times$ for alignment-failure detection~\cite{arx29429} and 312--455$\times$ for population simulation~\cite{arx27535}"
- Source says: arx29429 App. H: pooled 62.9× at list prices, "per-benchmark median 16.2×"; with judges repriced to GPT-4o-mini and a single generic question "12.1×, the median 3.3×"; with repriced judges and the full battery "6.0× and the median 1.5×", where the judge is cheaper on 5 benchmarks. arx27535: "approximately 8 times Jev for Luna (A3), 455 times for Astra … and 312 times for Astra on Arechar".
- Problem: Both examples are the most favourable figures. The same sources report a conservative 3.3–12× and an 8× ratio against a cheaper generative model. "One to two orders of magnitude" is not the typical finding.
- Suggested fix: "Relative to generative judges, studies report cost reductions from a few-fold to two orders of magnitude depending on the comparator and pricing, for example 63× pooled at list prices but 12× under conservative repricing for alignment-failure detection~\cite{arx29429}, and 8× against a mid-tier and 312–455× against a flagship model for population simulation~\cite{arx27535}."

### NEW-fidB-12 [minor]
- Location: sections/05_synthesis.tex:42
- Claim in paper: "The same models … degrade on lower-resource languages~\cite{typesafe_models,arx37647}, and can be steered by a third party's opinion inserted into the context~\cite{arx31142,arx30243}"
- Source says: arx37647 abstract: "All three models degrade on low-resource languages, fine-grained or noisy labels…" (Jev and two open generative comparators); typesafe_models: "Other languages, including CJK scripts, are handled but not equally well"; arx30243 adds background/procedural context, not opinions attributed to anyone (opinions are arx31142).
- Problem: (a) The language degradation is not specific to typed models, and the vendor page speaks of non-English/CJK languages, not lower-resource ones. (b) arx30243 does not test third-party opinions.
- Suggested fix: "… perform worse outside English, as the vendor acknowledges and as a 37-dataset benchmark found for typed and generative models alike~\cite{typesafe_models,arx37647}, can be steered by a third party's opinion inserted into the state~\cite{arx31142}, and can be flipped by optimised, innocuous-looking context~\cite{arx30243}".

### NEW-fidB-13 [minor]
- Location: sections/04_evidence.tex:298–300; table l.402
- Claim in paper: "AUROC 0.57--0.70 on six graded panels, chance on one"; "on \jev{}'s 12 most confident errors per graded panel"; "the best cross-fitted cascade beat the best single judge by at most 1.5 points (2.0 with an oracle threshold)"; table "cascades gain $\leq$1.5 points"
- Source says: arx29769 v2: "two binary panels … and seven ordinal panels"; §6.2 "no cascade's average gain over the best single judge exceeds 1.5 points (HealthBench)"; 2.0 and 1.3 "not significant"; across conditions incl. high reasoning effort the abstract gives at most 2.5 (cross-fitted) / 2.7 (oracle).
- Problem: "graded" is not the paper's term and is ambiguous, since all nine panels are graded; the analyses use the seven ordinal panels. The 1.5-point bound holds only for the main setup and is an average gain.
- Suggested fix: Replace "graded" with "ordinal" (three times). "… the best cross-fitted cascade's average gain over the best single judge was at most 1.5 points in the main setup (2.0 with an oracle threshold, neither significant; at most 2.5 across all reasoning-effort conditions) …"; table "cascades gain ≤1.5 points (≤2.5 across conditions)".

### NEW-fidB-14 [minor]
- Location: sections/04_evidence.tex:311
- Claim in paper: "certifying action on a new question type required at least 19 labels~\cite{arx33689}"
- Source says: arx33689: "The gate can act … only if n ≥ ⌈1/α⌉ − 1, i.e., 19 labels" (α = 0.05); labels from simulator rules; Open5GS/UERANSIM testbed without real RAN; Jev "hosted and 11–29 times slower".
- Problem: The bound depends on α, which is not stated. The simulator-label and testbed limitations are omitted.
- Suggested fix: "… certifying action on a new question type at a 5\% error level required at least 19 labels, in a simulated 5G testbed with rule-derived labels~\cite{arx33689}."

### NEW-fidB-15 [minor]
- Location: sections/04_evidence.tex:304
- Claim in paper: "on BFCL, \jev{} chose the right function 98.4\% of the time but decided correctly \emph{whether} to call one only 52.0\% of the time, with mean confidence 0.778 on wrong calls"
- Source says: arx26532 §5.4: the 0.778 refers to the 29 incorrect calls in the candidate-set expansion test (K = 2 → 64; accuracy 99.0% → 98.7%): "Incorrect calls nevertheless have a mean confidence of 0.778".
- Problem: As written, 0.778 reads as the confidence of the wrong whether-to-call decisions, which the source does not report.
- Suggested fix: "… only 52.0\% of the time (100 relevance cases); when distractor functions were added, its wrong function calls still carried a mean confidence of 0.778."

### NEW-fidB-16 [minor]
- Location: sections/04_evidence.tex:392 (table)
- Claim in paper: "F1 0.158 at threshold 0.5 vs 0.947 at a fitted threshold" — \cite{jkf87_2026replication}
- Source says: README (commit c11dbd0): "TensorTrust-hijack | 0.158 | 0.947 | 0.35" (columns F1@0.5 / after calibration / fitted threshold); threshold fitted on 10 labels; hosted jev-latest; median gain across 5 legs +0.254, max +0.789; AUROC 0.9476 with recall 8.8% at t = 0.5.
- Problem: The row gives no task, model or label budget, and cites the most extreme of five legs as if it were general.
- Suggested fix: "Prompt-injection detection (TensorTrust-hijack, hosted \jev{}): AUROC 0.95 but F1 0.158 at threshold 0.5, 0.947 with a threshold fitted on 10 labels (largest of five re-run benchmarks; median gain +0.25)".

### NEW-fidB-17 [minor]
- Location: sections/04_evidence.tex:388 (table)
- Claim in paper: "Fluent context additions flip 61.4\% of \jev{}'s correct decisions, 229 at $p \geq 0.7$"
- Source says: arx30243 abstract: "redirects Jev on 312 of 508 initially correct decisions within 64 accepted target evaluations, yielding a TFR of 61.4%"; "229 of the 508 decisions reach at least 0.7"; rate varies 40.0–85.7% by dataset.
- Problem: The flips come from a probability-guided search with up to 64 queries, not from arbitrary fluent additions. Without this, the row overstates how easily decisions flip.
- Suggested fix: "Optimised, fluent context additions (≤64 queries) flip 61.4\% of \jev{}'s correct decisions; 229 of 508 end at $p \geq 0.7$ on the wrong option".

### NEW-fidB-18 [minor]
- Location: sections/04_evidence.tex:391 (table)
- Claim in paper: "Multi-turn adaptive attacks succeed 25/27; ``untrusted'' labels barely help"
- Source says: Check Point blog: 25/27 is the strongest of three attackers ("typically needed four" turns of ten available); marking content untrusted made "no meaningful difference" (16/27 marked vs 16/27 single message; 13/27 unmarked separate message).
- Problem: The strongest-attacker result is presented as the general rate. "Barely help" suggests a small benefit, but the source found none, and marking was in one comparison worse.
- Suggested fix: "The strongest multi-turn adaptive attacker succeeds 25/27; marking content ``untrusted'' made no meaningful difference".

### NEW-fidB-19 [minor]
- Location: sections/05_synthesis.tex:42; table l.393
- Claim in paper: "The same models show group bias under forced choice~\cite{simmons2026saidno}"
- Source says: Simmons blog tests one model (Jev via Vercel AI Gateway): "White goes from ninth place on the direct question to 51 percent of all first picks"; the author speculates but does not measure that other evaluators share it.
- Problem: The plural "models" generalises a single-model blog test.
- Suggested fix: "\jev{} showed group bias under forced choice in one informal test~\cite{simmons2026saidno}$^\dagger$, …"

### NEW-fidB-20 [minor]
- Location: sections/02_background.tex:31; 04_evidence.tex:208
- Claim in paper: "gives an example in which a statement and its negation receive probabilities 0.72 and 0.47~\cite{typesafe_jaggedness}"
- Source says: The live page (checked 2026-10-04) still lists nine failure modes but no longer contains "refund", 0.72 or 0.47; the "Common-sense structural invariants" section was replaced. The Wayback capture of 2026-09-20 has "refund / not_refund Sum 0.72 0.47 1.19" (two Nouls on the ticket "I was charged twice…").
- Problem: The cited URL (urldate 2026-10-01) no longer supports the example. The citation is not reproducible.
- Suggested fix: Cite the archived version (web.archive.org/web/20260920205110/https://docs.typesafe.ai/model-jaggedness/jev-1.13) in grey.bib's note, and add "(in the 20 September version of the page; the example has since been removed)".

### NEW-fidB-21 [minor]
- Location: sections/05_synthesis.tex:13; 04_evidence.tex:394 and fig:honesty(d) caption l.241
- Claim in paper: "the clearest failure in the annotation study was on empathy, where \jev{} was confident on most items yet barely more accurate than a majority guess"
- Source says: arx24574 App.: "both Jev and Gemini 3.8 Flash collapse onto the no-exploration class, so the empathy failure is shared across model classes rather than specific to the decision model."
- Problem: The source's hedge that the failure is shared with a frontier generative model is omitted. This matters for T1, which argues from it about typed models specifically.
- Suggested fix: Append "; the authors note that a frontier generative model failed the same way, so the problem is the task, not only the typed model~\cite{arx24574}".

### NEW-fidB-22 [minor]
- Location: sections/05_synthesis.tex:48–49
- Claim in paper: "it requires effective human oversight of high-risk systems (Art.~14) and gives affected persons a right to an explanation of individual decisions taken on the basis of a high-risk system's output (Art.~86)"; "the Digital Services Act requires a statement of reasons for each restriction and an internal complaint-handling system (Arts.~17 and~20)"; "The GDPR restricts decisions based solely on automated processing that significantly affect a person (Art.~22)"
- Source says: AI Act Art. 86(1): right for a person subject to a decision taken by the deployer on the basis of output from a high-risk AI system listed in Annex III (except point 2) that produces legal effects or similarly significantly affects them adversely, to obtain "clear and meaningful explanations of the role of the AI system in the decision-making procedure and the main elements of the decision taken". DSA Art. 17 applies to providers of hosting services; Art. 20 applies to providers of online platforms (micro and small enterprises are exempt under Art. 19). GDPR Art. 22(1) covers decisions producing "legal effects … or similarly significantly" affecting the person; Art. 22(3) requires at least the right to obtain human intervention, express a view and contest the decision.
- Problem: Art. 86 is narrower than stated (Annex III systems, adverse legal or similarly significant effects; an explanation of the AI system's role and main elements, not of the decision in general). The DSA obligations have different addressees. The GDPR summary omits Art. 22(3), whose right to human intervention is the provision most relevant to T4.
- Suggested fix: "… and gives persons affected by decisions based on certain (Annex III) high-risk systems with legal or similarly significant effects a right to an explanation of the system's role and the main elements of the decision (Art. 86) …. The GDPR restricts decisions based solely on automated processing that produce legal or similarly significant effects and, where permitted, requires a right to human intervention and to contest the decision (Art. 22(1), (3)). For content moderation, the Digital Services Act requires hosting providers to give a statement of reasons for each restriction (Art. 17) and online platforms to run an internal complaint-handling system (Art. 20) …"

### NEW-fidB-23 [nit]
- Location: sections/05_synthesis.tex:47
- Claim in paper: "social scoring that leads to detrimental treatment (Art.~5(1)(c))"
- Source says: AI Act Art. 5(1)(c): evaluation or classification of natural persons over a certain period based on social behaviour or personal characteristics, where the score leads to detrimental treatment in unrelated social contexts and/or treatment that is unjustified or disproportionate.
- Problem: The cumulative conditions (evaluation over time; unrelated contexts or unjustified/disproportionate treatment) are dropped. They bear directly on whether T5's per-person aggregates would be caught.
- Suggested fix: "social scoring, that is, evaluating persons over time on their social behaviour or personal characteristics where the score leads to detrimental treatment in unrelated contexts or to unjustified or disproportionate treatment (Art.~5(1)(c))".

### NEW-fidB-24 [nit]
- Location: sections/04_evidence.tex:200
- Claim in paper: "the model is most over-confident precisely where people are divided"
- Source says: (description) mean confidence 0.807 vs mean annotator agreement 0.468 on hard items.
- Problem: This is an interpretation; the record compares quartiles only, so "most … precisely" is stronger than the evidence.
- Suggested fix: "the model is markedly over-confident where people are divided."

### NEW-fidB-25 [minor]
- Location: sections/02_background.tex:25
- Claim in paper: "Open approximations of RLCD combine cross-entropy with a Brier-score term, or use a REINFORCE loop … ~\cite{arx23886,arx24574}"
- Source says: arx23886 §3.3 presents this-that-model-1.0's own training loss (a convex combination of cross-entropy and Brier) and does not describe it as an RLCD approximation; arx24574 l.136 describes the 0.6B model's "own reading of the objective, a REINFORCE loop whose reward is the outcome minus the probability placed on the chosen option".
- Problem: arx23886 is attributed a framing ("approximation of RLCD") that it does not use.
- Suggested fix: "Open models train with cross-entropy plus a Brier-score term~\cite{arx23886,arx23959}, and one open implementation of RLCD uses a REINFORCE loop rewarding the outcome minus the probability placed on the chosen option~\cite{arx24574}."

### NEW-fidB-26 [nit]
- Location: sections/02_background.tex:29
- Claim in paper: "This guarantees \emph{form}, not \emph{correctness} or calibration~\cite{arx23886,arx26758}."
- Source says: arx26758: "output-type correctness alone does not ensure that decisions follow explicit option definitions"; arx23886: support is the declared set "by construction … no parser and no retry path".
- Problem: Neither source mentions calibration in this context. This is a fair inference but not a source statement.
- Suggested fix: "This guarantees \emph{form}, not \emph{correctness}~\cite{arx26758}; calibration is a separate empirical property (\cref{sec:g4})."

### NEW-fidB-27 [nit]
- Location: sections/02_background.tex:19
- Claim in paper: "publishes the training objective (that among answers given probability $p$, a fraction close to $p$ should be correct)"
- Source says: typesafe_primer: "Outcomes assigned a probability of 0.8 should occur about 80% of the time", presented as RLCD's output contract.
- Problem: The vendor states an output property, not a training objective. arx38850 notes that TypeSafe has not disclosed a training algorithm.
- Suggested fix: "… and publishes the calibration property its training targets (…)".

### NEW-fidB-28 [nit]
- Location: sections/04_evidence.tex:270
- Claim in paper: "and that confidence was mainly used to route items to stronger models or people"
- Source says: arx32160 abstract: "confidence is often used to decide when to defer to a stronger model or a human".
- Problem: "mainly" vs "often".
- Suggested fix: "… and that confidence was often used to defer items to stronger models or people".

### NEW-fidB-29 [nit]
- Location: sections/04_evidence.tex:255–256
- Claim in paper: "an essay critiquing …"; "arguing that typed inference relocates governance problems to whoever writes the schema and the option set"; "states explicitly that it is ``not an authorisation for decision use''"
- Source says: Zenodo 22847531 typed "Thesis/dissertation"; 22866847 "can relocate the relevant commitments into types, schemas, rubrics, probability thresholds…"; 22846597 "no un benchmark jurídico general ni una autorización de uso decisorio".
- Problem: There are small fidelity slips: the record type differs, the "can" hedge and the wider list are dropped, and a translation is shown in quotation marks as if verbatim.
- Suggested fix: "a document critiquing …"; "arguing that typed inference can relocate governance commitments into the schema, option set, rubrics and thresholds"; "states that it is not an authorisation for decision use (our translation)".

### NEW-fidB-30 [nit]
- Location: sections/04_evidence.tex:313
- Claim in paper: "also withheld 29 additional correct decisions"
- Source says: Zenodo 22952571: "withholding 29 additional correct allows".
- Problem: The source says "correct allows", which is more specific than "correct decisions".
- Suggested fix: "also withheld 29 additional correct allows".

### NEW-fidB-31 [nit]
- Location: sections/04_evidence.tex:358
- Claim in paper: "and the gateway was not run live"
- Source says: arx28919: the case study is an "emulation", and the classifier was called live ("live classifier labels, cached"; "We verified the interface live").
- Problem: The paper does not say this in these words, and the classifier was in fact live.
- Suggested fix: "the enterprise was emulated rather than deployed, although the \jev{} classifier was called live."

### NEW-fidB-32 [nit]
- Location: sections/04_evidence.tex:362–363; 02_background.tex:15
- Claim in paper: "2,170 projects using \jev{} by 22~September"; "in its first week"; "the labels were assigned by LLM agents without a reported human check"
- Source says: arx30216: "1,865 were created in the following week" plus 305 existing repositories that integrated Jev; labelling "independently reviewed by a second GPT-6 Luna Max agent, and disagreements are resolved by inspecting the original repository materials".
- Problem: "first week" covers integrations into older repos too. The labelling process included a second-agent review, which should be mentioned.
- Suggested fix: §2 "in a census of 2,170 public projects using \jev{} by 22 September"; G7 "… labels were assigned and cross-checked by two LLM agents, with no reported human validation."

### NEW-fidB-33 [nit]
- Location: sections/04_evidence.tex:259
- Claim in paper: "seven wrong intermediate choices by three comparator models changed downstream counts without changing the final labels"
- Source says: arx24965 abstract: "seven wrong selections on one culture-history question".
- Problem: All seven errors concern a single question, and that should be stated.
- Suggested fix: "… seven wrong intermediate choices by three comparator models, all on one culture-history question, changed downstream counts …"

### NEW-fidB-34 [nit]
- Location: sections/05_synthesis.tex:28
- Claim in paper: "a Chinese model initialised from Laya matched \jev{} on general Chinese decisions~\cite{arx36965}"
- Source says: arx36965 abstract: "exceeds the accuracy of the closed-source Jev model by 1.24% on general-domain tasks" on the authors' own CJ-Bench; it "retains 92% of Jev's average accuracy across specialized domains".
- Problem: The benchmark is the authors' own, and the specialised-domain shortfall is omitted.
- Suggested fix: "… matched \jev{} on general Chinese decisions in its authors' benchmark, though not across specialised domains (92\% of \jev{}'s accuracy)~\cite{arx36965}".

### NEW-fidB-35 [nit]
- Location: sections/04_evidence.tex:389 (table)
- Claim in paper: "as much as impersonating an authority"
- Source says: arx31142 §4.2: observer 12.1% vs authority impersonation 10.1%, "statistically tied" (+2.0 pp [−2.1, 5.9]).
- Problem: "as much as" is acceptable but less precise than the source's wording.
- Suggested fix: "statistically tied with impersonating an authority (10.1\%)".

### NEW-fidB-36 [nit]
- Location: sections/04_evidence.tex:223
- Claim in paper: "A study published only on alphaXiv, which we could verify only at the abstract level"
- Source says: The alphaXiv abstract field is empty, but the full text is shown on the page and supports the numbers (jev-1.13.0, CONFLICTS benchmark, 0.56–0.58).
- Problem: The verification-level statement is inaccurate.
- Suggested fix: "A study published only on alphaXiv (not peer-reviewed or on arXiv) reports …".

## Uncited claims needing a citation
- 04_evidence.tex:190 "The largest benchmark so far" (see fidB-3); state the scope ("in our corpus").
- 05_synthesis.tex:26 "and cannot be self-hosted": supported by arx28919 ("nor is it offered for self-hosting") but none of the cited TypeSafe pages say so; add \cite{arx28919}.

## Summary

I checked about 200 source-attributed statements in G4–G7, tab:negative, §2 and §5 against full texts (41 local, the rest via arXiv HTML), the grey URLs and the Zenodo record descriptions. Most numbers are reproduced exactly: model, dataset and condition match in nearly all cases, and the frequent hedges the authors already added (secondary endpoints, upper-bound caveats, version changes) are faithful. There are two major problems. First, a formula-derived confidence figure (0.20→0.58, Bernoulli) is presented as an observed effect. Second, the G4 polbox and §5 T2 say Jev "cannot separate conflict from ignorance", but the cited Zenodo record reports that Choice did separate them and explicitly disclaims a collapse. Twenty-one further minor issues are mostly selective reporting or dropped hedges:
- the most favourable cost ratios in §2;
- Jev's second-place persistent-correctness rank omitted;
- a loss figure attached to the wrong task;
- Laya presented as composing better when it is less coherent;
- the strongest-attacker and best-leg grey results shown as general;
- "graded" vs "ordinal" panels, with the main-setup-only cascade bound;
- the α condition on the 19-label bound;
- a 0.778 confidence attached to the wrong BFCL test;
- language degradation and opinion steering misattributed in §5 T5;
- the jaggedness example now gone from the live page;
- "must recalibrate" overstated;
- over-broad readings of Art. 86, DSA Arts. 17/20 and GDPR Art. 22 (Art. 5(1)(f), Art. 14 and the Santa Clara Principles are accurate).

The remaining 13 items are nits. None of the findings overturns the survey's conditional thesis, but fidB-1 and fidB-2 should be fixed before submission, and the minor items would make the negative-results table and §5 measurably more balanced.
