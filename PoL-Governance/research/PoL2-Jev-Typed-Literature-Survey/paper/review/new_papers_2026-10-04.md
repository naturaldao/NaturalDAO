# New candidate papers from the 2026-10-04 search re-run

Source list: `data/search_rerun_2026-10-04.csv` (25 rows). Screening and extraction done on 2026-10-04 by a single coder (AI-assisted). Every included paper was read in full from the arXiv HTML rendering (`https://arxiv.org/html/<id>`). Metadata comes from `https://arxiv.org/abs/<id>`. All 15 included papers exist only as **v1**, and v1 is the version that was read.

Conventions:
- Section, table and figure locators refer to the arXiv HTML v1.
- "Derived" marks a figure computed here from numbers the paper reports. The paper does not state such figures itself.
- "Not reported" means the quantity was searched for in the full text and was not found.
- S/Q/N codes: S = supports use for that governance function as-is; Q = supports it only with qualifications or conditions; N = negative evidence. "Empirical" = whether the code rests on a measurement in the paper.

## 1. Screening table

| arxiv_id | decision | reason |
|---|---|---|
| 2609.20587 | exclude-title | Cell-motility spin model (physics). Matched "direct-decision" by accident. |
| 2609.23513 | exclude-title | Temporal entanglement transitions (quantum physics). "System One" is an accidental phrase match. |
| 2610.00213 | include | Hosted Jev (jev-1.13.0) used as the population-scale extractor, audited against blind human adjudication. |
| 2609.28182 | exclude-abstract | Finite-sample safety certification of generic black-box AI controllers for grid-edge devices. "Decision model" is generic; no Jev or typed-decision interface. |
| 2609.32893 | exclude-title | Exoplanet candidate in 61 Cygni ("binary system-one" hyphenation match). |
| 2609.32191 | exclude-title | Harmonic maps (pure mathematics). |
| 2609.33609 | exclude-fulltext | "Jev-LDE" is an RL-fine-tuned small *generative* LLM that edits in-context demonstrations (Keep/Delete/Replace) for Qwen/Llama targets. Zero mentions of TypeSafe or the typed-decision interface; the name is a coincidence. |
| 2609.36093 | exclude-title | Information design in economics ("direct decision value"). |
| 2610.00346 | include | Matched-harness benchmark of hosted Jev 1.13.0 and 7 open Jev-like checkpoints against classifiers and LLMs. |
| 2609.38334 | exclude-abstract | EVOKE post-training for LLM agents. "Direct decision supervision" is unrelated to typed decision models. |
| 2609.37009 | exclude-abstract | Persona-conditioned generative LLM agents for evacuation simulation. No typed decision model. |
| 2609.40241 | include | Controlled empirical study of hosted Jev for recommendation reranking. |
| 2610.00437 | include | JevSpawn (Jev-style finite-scoring agent policy) with a hosted Jev (jev-1.13.0) variant as comparator/component. |
| 2609.39496 | include | Hosted Jev rejection ("None" option) failure on answer-absent menus. |
| 2610.00381 | include | OmniMed-Jev, an authors-built Jev-like typed decision model (Choice/Noul/Score) for medical imaging. |
| 2610.00376 | include | Hosted Jev (typesafe/jev-1.13) for network traffic classification. |
| 2610.00831 | include | AnyJev: open Jev-style readout from frozen LLMs, compared with open Jev replicas (Nimble, Laya, NanoJev). |
| 2609.38861 | exclude-abstract | TRACE literature-QA system. "Typed answers" refers to evaluator answer types, not a typed decision model. |
| 2610.02076 | include | LLM2Jev: open Jev-style readout/fine-tuning, compared with community Jev-style models. |
| 2610.02048 | include | HydroJEV: hosted Jev (jev-1.13.0) as first-tier SCADA triage screen in a gated cascade. |
| 2610.01834 | include | Hosted Jev (jev-1.13.0) as an agent action-selection layer; evaluation vs simulation boundary. |
| 2610.01231 | include | Conceptual perspective whose object is Jev (machine evaluation, thresholds and decision rights). **Non-empirical.** |
| 2610.01079 | include | Jev-IDS: hosted Jev (jev-1.13.0) as a flow-based intrusion detector. |
| 2610.01006 | include | Controlled audit of hosted Jev (jev-1.13.0) confidence and self-knowledge (~575k calls). |
| 2610.02046 | include | JEVDB: hosted Jev (jev-1.13.0) as the fast path of a semantic database, with calibrated LLM escalation. |

**Counts:** 25 screened. 15 included; 10 excluded (5 exclude-title, 4 exclude-abstract, 1 exclude-fulltext). Of the 15 included, 14 are empirical and 1 is conceptual (2610.01231). By model tested:
- 11 test hosted Jev. Two of these also test Jev-like or open models: 2610.00346 (seven open replicas) and 2610.00437 (open Qwen-based JevSpawn as the main arm).
- 3 test only Jev-like or open models: 2610.00381, 2610.00831, 2610.02076.
- 1 tests no model: 2610.01231.

---

## 2. Extraction blocks

### 2610.00213 — Counting the Uncounted: Population-Level Surveillance of Documented Pregnancy and Fetal Harm in Police Crash Narratives with a System One Model (Jev)

- **Authors:** Amir Rafe; Subasish Das (Texas State University). **First version:** 2026-09-21. **Version read:** v1. **Primary category:** stat.AP. **License:** arXiv non-exclusive distribution license 1.0.
- **Model actually tested:** hosted Jev only, "pinned to the single version jev-1.13.0, recorded on every call" (Limitations; Data and code availability). No open replica and no other model comparator.
- **Design:**
  - Task: identify police crash narratives that document a pregnant person, plus role, gestational stage and post-crash condition.
  - Data: all Texas CRIS narratives 2017–2025, 5,018,079 after dropping empty and ≤40-character rows (English) (§3.1).
  - Pipeline:
    - Stage A: a regex screen flags 6,840 narratives.
    - Stage B: Jev answers an 8-question schema (`pregnancy_v1`: presence question + 3 gated choices + 4 further questions) on all 6,840, with threshold τ = 0.5.
    - Stage C: the presence question is asked of 499,306 random non-hit narratives (§3.2).
  - Reference standard: blind human adjudication of a probability-stratified sample.
    - 407 narratives read, 229 of them twice.
    - 174 Stage-A and 218 Stage-C narratives enter the rates.
    - Inverse-probability weighting, Rogan–Gladen correction, and one 2,000-draw bootstrap chain (§3.3).
  - Comparators: regex screen only.
  - Metrics: weighted sensitivity, specificity and PPV; Cohen's κ; adjusted counts; rates per 1,000 drivers; documentation logistic model.
- **Key findings:**
  - G1 (detection, flagged stratum):
    - Weighted sensitivity 0.999 [0.997, 1.000], specificity 1.000 [1.000, 1.000], PPV 1.000, from 174 adjudicated Stage-A narratives (Table 3; §4.1).
    - Weighted decision errors: 5 false negatives and 0 false positives against 5,305 TP and 1,477 TN (§4.1, Fig. 3b).
    - The authors note that specificity 1.000 "reflects zero false positives among twenty-seven adjudicated true negatives" (§5, limitations).
  - G1 (discrimination of screen hits): hits on core terms were confirmed at 97.9%, against 2.1% for hits matched only by everyday-English terms (§4.1).
  - G1 (negative, low-prevalence stratum): among 499,306 unflagged narratives Jev returned 45 positives. Only 14 of 42 adjudicated positives were confirmed true misses (Table 3). Derived: about 0.33 PPV in that stratum, where the paper says the misclassification correction is "not well conditioned" (Fig. 1 caption).
  - G1 (attributes):
    - Driver role confirmed in 284/284 settleable rows; fetal-harm label confirmed in 56/56. Pre-adjudication coder agreement was 96.7% (role) and 96.6% (outcome) (§4.1).
    - "Stage, transport and the remaining outcome categories carry no reference standard … error rates are unknown" (§4.1).
  - G4 (calibration direction): within each decision group the mean model probability is "conservative" (Fig. 3a, §4.1). Narratives called positive are confirmed more often than their mean probability states; narratives called negative are confirmed less often. The probability distribution over hits is strongly bimodal (Fig. 3c).
  - G4 (coherence across related questions): the standalone transport question and the gated post-crash condition disagree in both directions: 192 narratives one way and 105 the other (§4.3). The authors read this as two questions about different subjects.
  - Robustness to call composition (G2-adjacent, not adversarial): on 590 paired narratives, asking the presence question alone vs alongside nine others gave 100.0% binary agreement at τ = 0.5, Pearson 0.998, and mean absolute difference 0.0034 (§3.2).
  - G7 (public-scale use):
    - Jev read 506,146 narratives (derived: 6,840 under the 8-question schema + 499,306 under the presence question), out of a 5.0M-narrative state corpus, "on ordinary research infrastructure without a dedicated computing allocation" (§1). Monetary cost and wall-clock time: not reported.
    - Result: adjusted total 5,467 [5,306, 5,577]; rate 1.13–1.45 per 1,000 female drivers aged 15–49; narratives document 2.56–3.09% of expected pregnant drivers; documentation OR for own recorded injury 21.7 [15.9, 29.6] (Abstract, Table 7).
  - G7 / privacy:
    - After two redaction passes, residual identifiers remained in 25/58 (43%) fetal-harm narratives and 152/407 (37%) adjudication narratives (§3.1).
    - Redaction is applied to "every copy that a human or an external service ever sees".
  - Authors' limitations:
    - Documentation is not prevalence.
    - Validation rests on a few hundred narratives; the screen-miss term rests on 42 Stage-C positives.
    - Closed model; results are "not guaranteed to reproduce against a later version".
    - One state; 2025 only partially reported; no passenger denominator (§5).
- **Proposed axes and codes:**
  - G1 — **Q** (empirical: yes). Near-perfect presence detection inside the regex-flagged stratum, but only 27 adjudicated negatives, PPV about 0.33 (14/42) in the low-prevalence stratum, and finer attributes unvalidated.
  - G4 — **Q** (empirical: yes). Probabilities err on the conservative side for the presence decision. Attribute calibration is unmeasured, and linked questions disagree on 297 narratives.
  - G7 — **Q** (empirical: yes). Demonstrates statewide reading with human audit and misclassification-corrected intervals. Cost is not reported, and 37–43% residual PII constrains sending text to an external service.
  - G5 — **Q** (empirical: no). The audit design is reproducible: released schema, blind adjudication tool and per-equation code map. The decision chain inside the model remains closed and version-pinned.
- **Relevance to a PoL2-style safety valve:** This is the clearest template so far for using a typed model as a population-scale instrument, not as a final judge. It combines a cheap pre-screen, a typed presence question with gated sub-questions forced to `no_pregnancy` below threshold, a blind stratified human audit, and an error-corrected aggregate with intervals. A PoL2 valve could copy three elements: (1) gating sub-decisions on a primary presence decision; (2) auditing by probability strata instead of trusting stated calibration; (3) reporting error rates only for the stratum where they were measured. The 14/42 confirmation rate in the low-prevalence stratum warns that a "violating" verdict on rare events needs a second check. The residual-PII figures bear directly on sending clause evidence to a hosted model.
- **Quality notes:**
  - Very large corpus, but a modest audit (407 read; 174 Stage-A in the rates).
  - One Jev call per narrative per question, except the 590-narrative composition check; no repeat-call variance reported.
  - Two-coder κ = 0.944 over 212 pairs.
  - Not vendor-affiliated. The same authors wrote 2610.00346 and an earlier crash-narrative calibration paper already in the corpus. A competing-interest statement was not found.
  - Code and schema released under MIT (github.com/pozapas/pregnancy-crash-narratives). The narratives themselves cannot be released.

### 2610.00346 — Benchmarking System One decision models against trained classifiers and language models for automated decision gates

- **Authors:** Amir Rafe; Subasish Das (Texas State University). **First version:** 2026-09-29. **Version read:** v1. **Primary category:** cs.LG. **License:** arXiv non-exclusive distribution license 1.0.
- **Model actually tested:** both.
  - Hosted Jev via `typesafe-sdk` pinned to **jev-1.13.0** (§4).
  - Open replicas:
    - Laya (English, ModernBERT-large, 421M)
    - Laya (multilingual, mmBERT-base, 322M)
    - Kev-0.8B and Kev-9B (Qwen3.5 + LoRA + pointer head)
    - decider-2b
    - this-that-model-1.0
    - Nimble-9B
  - Comparators:
    - Generative: Qwen3-14B (verbal JSON); Qwen3.6-27B (verbal JSON and option-key likelihood).
    - Trained classifiers: BERT-base fine-tuned; BGE-small embedding regressions.
    - Zero-shot: DeBERTa-v3 NLI.
    - Untuned Qwen3.5 backbones (Table 3).
- **Design:**
  - Data:
    - D1 typed-decisions: synthetic, 400 states / 2,000 decisions, K = 2–5, teacher-consensus labels.
    - D2 CLINC-150: 600 in-scope + 200 out-of-scope, K = 150.
    - D3: four computational social science tasks (500/500/498/498). All English (Table 4).
  - One harness sends identical semantic requests to every model, with neutral option identifiers o1…oK. Inputs are frozen with SHA-256 digests; seed 20260924 (§3.2).
  - Repeats: Jev answered every condition 3 times (first run analysed), and 5 times on 40 states to obtain a test-retest floor (§3.2).
  - Metrics:
    - Accuracy; ECE (10 equal-mass bins); Brier; NLL.
    - Coverage at 1%/5% risk, with held-out thresholds and one-sided risk bounds.
    - Out-of-scope AUROC.
    - Flip rates under option-name conditions; cardinality sweep.
    - Cost and latency; confidence-gated cascades.
  - Statistics: paired cluster bootstrap with 10,000 replicates and Holm correction (§3.3).
- **Key findings:**
  - G1 (accuracy):
    - Jev: D1 0.732; CLINC-150 0.913; out-of-scope AUROC 0.921; derailment 0.558, power 0.608, emotion 0.504, politeness 0.657; D3 macro-F1 55.0 (Table 5).
    - Trained classifiers beat Jev on CLINC: BERT 0.940, BGE-LR 0.948; Jev is −3.5 points, significant (§5.1).
    - Kev-9B 0.712 on D1 is not distinguishable from Jev (−1.9 points, CI −4.0 to 0.1, Holm p = 0.18) (§5.1).
    - Qwen3.6-27B likelihood readout is level with Jev (0.733 / 0.912).
  - G1/G6 (thresholds):
    - With a threshold chosen on held-out data, Jev accepts 0.93 of CLINC decisions at realized risk 0.049 (one-sided upper bound 0.066), and 0.17 of D1 decisions at realized risk 0.058, which already exceeds the 5% target (§5.1).
    - "The one-sided upper bound on the realized risk lies above the five percent target for every model" (§5.1).
    - On D3 no model holds 5% risk beyond coverage 0.08 (§5.1).
  - G4 (calibration):
    - Jev ECE as shipped: 0.033 (D1), 0.032 (D2), 0.251 pooled over D3; 0.038 after per-task temperature scaling (Table 6).
    - Stored temperatures fitted on few options do not transfer to many: Kev-9B ECE goes from 0.051 (raw) to 0.377 (shipped) on CLINC-150 (§5.1, Table 6).
  - G4/G6 (out-of-scope):
    - At a held-out threshold targeting 5% in-scope risk, Jev accepts 0.310 of out-of-scope requests while routing 0.92 of in-scope ones (risk 0.047). Kev-9B accepts 0.015 and Nimble-9B 0.030, but they route only 0.61 and 0.66 of in-scope requests (§5.1; Table 10).
    - With an explicit "out of scope" option, Jev chooses it for 0.585 of out-of-scope and 0.003 of in-scope requests. False acceptance falls to 0.195 at 0.925 in-scope routing (§5.1). Kev-0.8B, decider-2b and this-that-model-1.0 choose that option for at most 0.165 of out-of-scope requests.
  - G3 (option-name semantics):
    - Swapping yes/no against fixed rubrics flips 50.5 Jev answers per 100 on D1 binary questions (CI 46.2–54.7; test-retest floor 1.3). AUC falls from 0.89 to 0.31 (§5.2).
    - Flips reach 97.2 on derailment and 84.0 on power (floors 0.4 and 0.8).
    - With digits or random strings, Jev stays within 2.8 flips per 100 of the aligned condition.
    - Other models under the swap: Laya 91.3; four larger decoder checkpoints 4.2–6.5; Kev-0.8B 14.3 (§5.2, Fig. 3).
  - G3/robustness (cardinality):
    - Jev accuracy falls from 0.990 (5 options) to 0.913 (150) (Table 7). Laya (English) collapses from 0.852 to 0.020 at 50 options because option text is truncated to its 192-token head budget.
    - Two more distractor permutations move Jev accuracy by at most 0.013 (§5.2).
  - G6 (cascades, held-out thresholds; Table 9, §5.3):
    - Jev → Qwen3-14B on D1: escalates 0.01, gain 0.0.
    - this-that-model-1.0 → Jev on CLINC: escalates 0.25; accuracy 0.927 vs 0.913; gain 1.3 points (CI −0.7 to 2.8, p = 0.16) at 0.43 of the hosted cost.
    - Kev-9B → Jev: escalates 0.56 at 1.08× hosted cost with no gain.
    - Only two cascades show gains whose CI excludes zero, and neither reaches hosted-Jev accuracy.
  - G7 (cost and latency): Jev US$0.0079 per 1,000 D1 decisions; median latency 138 ms (p95 183 ms) (Table 8). this-that-model-1.0 costs US$0.0020 per 1,000 at US$0.48 per GPU-hour.
  - Authors' limitations:
    - Reference labels are teacher consensus, distant hashtags or administrative tags, not human adjudication.
    - Coverages are empirical, not guaranteed.
    - Training data of Jev and Laya are unreleased, so exposure cannot be checked.
    - Models change without notice (§7).
- **Proposed axes and codes:**
  - G1 — **Q** (empirical: yes). Best decision model on workflow/intent items and cheap, but beaten by small trained classifiers where labels exist, and weak on social-science tasks.
  - G3 — **N** (empirical: yes). Jev follows option names over rubrics (50.5–97.2 flips per 100). Only neutral identifiers bring this near the retest floor.
  - G4 — **Q** (empirical: yes). ECE about 0.03 in-domain but 0.251 on the social-science tasks; per-task recalibration is needed.
  - G6 — **Q** (empirical: yes). Held-out thresholds miss their risk bounds, in-scope thresholds do not control out-of-scope acceptance (0.310), and cascade savings depend on the specific model pair.
  - G7 — **Q** (empirical: yes). Lowest hosted cost per decision measured so far; small open checkpoints can be cheaper at full GPU utilization.
- **Relevance to a PoL2-style safety valve:** This is the most directly transferable evidence for a valve built as an automated gate. Four lessons follow. (a) Clause options must use neutral identifiers, with all meaning in the rubric. Naming options "conforming"/"violating" risks the 50–97 per 100 polarity flips measured here. (b) A risk threshold tuned on in-scope cases does not stop out-of-scope inputs. An explicit "insufficient"/out-of-scope option helps (0.310 → 0.195) but does not solve it, so it needs its own validation. (c) Thresholds must be validated per clause family on held-out data and reported with a one-sided risk bound. (d) Escalating from Jev to a generative model adds nothing unless the second stage is more accurate on the escalated cases.
- **Quality notes:**
  - Strong design: matched harness, frozen inputs, Holm-corrected paired bootstrap, triple Jev runs with a test-retest floor, and backbone controls.
  - Modest item counts (≈500–2,000 per dataset).
  - Not vendor-affiliated; same authors as 2610.00213.
  - Harness, inputs, per-request answers and code are stated as released. The repository URL was not found in the HTML text.

### 2609.40241 — Decision-Oriented Recommendation Reranking: An Empirical Study of Jev

- **Authors:** Hanjia Lyu (Singapore Management University); Yinglong Xia (Meta AI). **First version:** 2026-09-30. **Version read:** v1. **Primary category:** cs.IR. **License:** arXiv non-exclusive distribution license 1.0.
- **Model actually tested:** hosted Jev via the TypeSafe API using the alias **jev-latest as of 2026-09-30**. The returned version is not reported (App. B.4).
- **Design:**
  - Task: personalized next-item reranking on controlled hard candidate sets (SASRec negatives).
  - K ∈ {20, 50, 100, 200}.
  - Data: Amazon Reviews 2023, English. Movies & TV (954 users), Video Games (1,000), Books (626) (§4.2).
  - Comparators: SASRec; DCNv2; Qwen2.5-7B-Instruct pointwise and listwise.
  - Metrics: NDCG@10, HR@10, MRR, observed latency.
- **Key findings:**
  - Effectiveness (not a G1 harm-detection task):
    - Jev has the highest MRR and HR@10 in most cells. Books K = 200: Jev MRR 0.140, HR@10 0.251, vs Qwen pointwise 0.074 / 0.161 (Table 2, App. C.1).
    - Movies & TV K = 200: SASRec HR@10 is 0.170 vs Jev 0.150 (Table 2).
  - G7 (latency scaling):
    - Jev median per-user latency is 350–967 ms across K and domains. At K = 200: 627 ms (Movies), 967 ms (Games), 866 ms (Books) (Table 3, App. C.2).
    - Qwen pointwise at K = 200: 6.07–14.87 s. SASRec and DCNv2: under 1.3 ms.
    - The latency comparison is not hardware-normalized (hosted API vs local A800) (§6.3).
  - G4: Jev probabilities are used directly as scores "without additional calibration" (App. B.4). Calibration: not reported.
  - G3: candidate order is randomized deterministically. Order sensitivity: not tested.
  - Authors' limitations: one decision model; one 7B LLM baseline; latency not hardware-normalized (§6.3).
- **Proposed axes and codes:**
  - G7 — **Q** (empirical: yes). Latency grows slowly with candidate-set size (up to 200 options), but it is unnormalized, recorded under a moving alias, and no cost is reported.
  - (No G1–G6 code: the task is preference ranking, not harm detection or oversight.)
- **Relevance to a PoL2-style safety valve:** Low. The only transferable signal is that Jev keeps a usable ranking over up to 200 candidates at sub-second hosted latency. That matters if a valve must choose among many clauses or precedents. It says nothing about correctness, calibration or abstention.
- **Quality notes:**
  - Single run per configuration; no confidence intervals.
  - Main-text results are mostly in figures; exact numbers are in the appendix tables.
  - Model alias, not a pinned version.
  - No vendor affiliation (one author at Meta AI).
  - Code release: not stated.

### 2610.00437 — JevSpawn: Adaptive Agentic Inference through Compositional Action Spaces

- **Authors:** Haoyang Su; Weiran Huang (Fudan University; Shanghai Jiao Tong University; Shanghai Innovation Institute). **First version:** 2026-09-30. **Version read:** v1. **Primary category:** cs.AI. **License:** CC BY 4.0.
- **Model actually tested:** both.
  - Main arm: JevSpawn, a Jev-style finite-scoring policy built on open Qwen3.8-27B.
  - Variant arm: "TypeSafe Jev" replaces finite scoring with hosted **jev-1.13.0**; Qwen still produces declarations and text (§4.1; App. B.4).
- **Design:**
  - 8 tasks: PPNL, Maze, Grid, LightsOut, RushHour, Sokoban, 2048, Nullify.
  - Baselines: 7 agent methods (LATS, LLMCompiler, AgentPrune, HiAgent, FoldAgent, DyFlow, LatentMAS).
  - Settings: 4×H100; temperature 0; seed 42; environment seeds 42–141; 36 rounds; 300 s limit.
  - Metrics: success/reward, end-to-end latency, decoding throughput.
- **Key findings:**
  - Hosted-Jev variant vs Qwen-scored JevSpawn (Table 1):
    - PPNL 0.955 / 0.950
    - Maze 0.960 / 0.960
    - Grid 0.930 / 0.950
    - LightsOut 0.660 / 0.610
    - RushHour 0.290 / 0.390
    - Sokoban 0.250 / 0.150
    - 2048 296.0 / 305.12
    - Nullify 0.170 / 0.210
  - G7 (latency): "The TypeSafe Jev variant takes 1.4 to 2.1 times as long as Qwen scoring across all eight tasks, including API communication" (§4.2). Variant end-to-end latency ranges 43.96–249.05 s (Table 2).
  - Cost: not reported. Calibration, abstention, robustness: not reported.
- **Proposed axes and codes:**
  - G7 — **Q** (empirical: yes). Inside a multi-step agent loop, hosted Jev scoring was slower than local open-weight scoring and gave mixed quality. Speed advantages are deployment-specific.
- **Relevance to a PoL2-style safety valve:** Low. It is an agent-efficiency paper. The only lesson is that round-trip cost to a hosted typed model can dominate in tight multi-step loops. A valve consulted at every agent step may be better served by a local Jev-like scorer.
- **Quality notes:**
  - Single seed for the policy; 100 environment seeds for most tasks; bootstrap intervals in Fig. 3.
  - Authors are not the vendor.
  - Code released (github.com/Hoyant-Su/JevSpawn).

### 2609.39496 — When the Right Answer Is Missing: An Arithmetic-Dependent Rejection Bottleneck in Jev

- **Authors:** Jike Zhong (University of Southern California); Ming Li (University of Florida); Yuxiang Lai (Emory University). **First version:** 2026-09-30. **Version read:** v1. **Primary category:** cs.LG. **License:** CC BY 4.0.
- **Model actually tested:** hosted Jev through its API. The exact version string is not stated in the text; it cites the "Jev 1.13 jaggedness" documentation. Generative control: Qwen3.5-9B with reasoning.
- **Design:**
  - Synthetic paired answer-present / answer-absent menus with exact ground truth.
  - Main sets: 100 problems each for two-operation arithmetic (a+b−c), numeric lookup and purchase totals.
  - Contextual controls: 128 inventory problems, 64 refund-policy, 64 logical-eligibility.
  - Ablations:
    - Operation depth (50 paired cases).
    - Magnitude bands (100 per band × 5).
    - Candidate distance (50).
    - Operators (200).
    - 15 pilot families × 20 paired cases.
    - Rejection-label wording.
  - Three interfaces: Menu Choice with a "None" option; candidate-level T/F Choice; native Boolean.
  - Thresholds selected on 20 development problems; 20,000 bootstrap resamples (§3–4).
- **Key findings:**
  - G4 (abstention failure):
    - Menu Choice answer-present accuracy is 99% but correct rejection only 7% on arithmetic, a 92-point gap. Purchase totals: 94% vs 24% (§4.2, Fig. 3).
    - Contextual inventory: 127/128 correct selections vs 14/128 correct rejections. Refund-policy and eligibility controls: 64/64 in both conditions (§4.2).
  - G4 (mechanism):
    - Supplying the computed result restores 100% rejection (§4.3).
    - On answer-absent arithmetic, native Boolean exact match is 99% vs 27% for T/F Choice: the same questions with only the type field changed (§4.3).
    - Reasoning Qwen3.5-9B reaches 100% present and absent on arithmetic and purchase menus (§4.3, Fig. 5).
  - G4 (onset and scope):
    - Rejection drops from 66% at one operation to 4% at two (present 100% → 98%) (§4.4).
    - Even in the 1–9 band, rejection is only 56%. Other bands: 8%, 14%, 11%, 14% (§4.4).
    - Capacity rounding 18/20 vs 2/20; calendar arithmetic 12/20 vs 0/20 (§4.5).
  - G3-adjacent (label and position):
    - "Other" gives 99%/9% and "None of the above" 99%/6%, vs the "None" baseline 99%/7%.
    - Moving "None" across four positions recovers only 5, 0, 2 and 0 of 40 failures (§4.5).
  - G4/G6 (repair):
    - The scores still carry signal: T/F AUC 0.985 despite only 88/200 exact matches. At the default 0.5 threshold, T/F accepts multiple candidates on 55/200 menus vs 3/200 for Boolean (§5.1).
    - A development-selected threshold τ = 0.03 on p(None) raises arithmetic rejection from 7% to 79%, with present accuracy 99% → 97%. Balanced accuracy goes from 53% to 88% (Table 2, §5.3).
    - Purchase: 24 → 79 rejection, 94 → 86 present. Time: 49/80 → 72/80.
  - Authors' limitation: black-box API only; no access to weights or internals (Limitations).
- **Proposed axes and codes:**
  - G4 — **N** (empirical: yes). An explicit "None/Other" option is almost never chosen when rejecting requires computation (7% correct rejection), and the failure survives relabelling and repositioning.
  - G6 — **Q** (empirical: yes). Thresholding p(None) on development data, or switching to per-candidate Boolean verification, largely repairs it, at a task-specific cost in selection accuracy.
- **Relevance to a PoL2-style safety valve:** Directly relevant to the three-state (conforming / violating / insufficient) protocol. The paper shows that the "insufficient"/"none" option of a Choice question cannot be trusted to fire when no listed option is valid and deciding that requires computation (sums, dates, quantities). A PoL2 valve should do four things: (1) test every clause on paired present/absent cases; (2) prefer per-option Boolean verification over a single Choice-with-None; (3) or threshold p(insufficient) using held-out data; (4) compute numeric facts in code before asking.
- **Quality notes:**
  - Synthetic; 100 cases per main task; pilots of 20.
  - Repeat calls: not reported.
  - Paired bootstrap intervals.
  - No vendor affiliation.
  - Code/data release: not stated.

### 2610.00381 — OmniMed-Jev: Calibrating LVLM Confidence for Trustworthy Medical Multimodal Decisions via System One

- **Authors:** Luyao Tang; Cheng Chen. **First version:** 2026-09-30. **Version read:** v1. **Primary category:** cs.LG. **License:** CC BY 4.0.
- **Model actually tested:** neither hosted Jev nor an existing replica. OmniMed-Jev is the authors' own Jev-like typed decision model: MedGemma-1.5-4B backbone, a candidate-marker scoring head (1,057,410 parameters) and LoRA adapters. It is compared with a generative SFT baseline trained on the same backbone, images and steps (§3–4; App. E).
- **Design:**
  - 4 task families from 15 source datasets:
    - Classification: pooled MedMNIST.
    - Multi-label: chest-radiograph findings, 2,795 decisions.
    - Counting: blood smear, 126/201.
    - Regression: LVEF and retinal score.
  - Test file: 726 rows; n = 200 per family for task metrics.
  - Training: one seed (42) for both models; 3,685 steps (App. E).
  - Metrics: ECE; Murphy reliability/resolution; AURC; task metrics; paired bootstrap; McNemar.
- **Key findings:**
  - G4 (calibration, Table 2; generative → OmniMed-Jev):

    | Family | ECE | Reliability | AURC |
    |---|---|---|---|
    | Classification | 0.2589 → 0.0806 | 0.1002 → 0.0110 | — |
    | Multi-label | 0.2981 → 0.0114 | 0.1294 → 0.0010 | 0.2474 → 0.0126 |
    | Counting | 0.4204 → 0.0408 | — | — |
    | Regression | 0.1267 → 0.0913 | — | AURC unchanged (0.2272 / 0.2280) |

  - G1 (accuracy):
    - No family-level accuracy difference distinguishable from zero except counting MAE, which favours the generative baseline (2.1429 vs 2.5159; CI +0.0952 to +0.6429) (Table 1; App. E).
    - Classification McNemar p = 1.00.
  - G3/robustness (option order): top-1 agreement under candidate permutation is 0.90 (classification), 0.42 (counting) and 0.67 (regression) (§5.4).
  - G4 (no abstention): with the annotated candidate removed, the model picks a plausible runner-up (0.88) instead of signalling absence (§5.4).
  - Authors' limitations:
    - The interface effect cannot be separated from denser supervision and the extra head.
    - Evaluated on held-out data from the same sources only; out-of-distribution and per-class behaviour not measured.
    - "Not evidence of clinical readiness" (Abstract; §6; App. I).
- **Proposed axes and codes:**
  - G4 — **Q** (empirical: yes). Training the decision distribution as the output gives order-of-magnitude in-distribution calibration gains, but only in one controlled study, without OOD tests, and with no abstention option.
  - G6 — **Q** (empirical: yes). Much lower AURC supports confidence-based deferral in-distribution. No deployment test.
- **Relevance to a PoL2-style safety valve:** Indirect but useful. It is controlled evidence that training a model to output a distribution over candidates (Jev-style) rather than text makes reported probabilities usable for thresholds and deferral. That supports the design premise of a typed valve. It also shows that Jev-like models without an explicit "none/insufficient" candidate will confidently pick a runner-up when the true answer is absent. A valve therefore needs the explicit third state.
- **Quality notes:**
  - Single seed and a single matched pair; n = 200 per family.
  - Generative probabilities are reconstructed, by the authors' account a "generous" reconstruction.
  - Academic authors.
  - Code released (github.com/lytang63/OmniMed-Jev).

### 2610.00376 — A First Glance at Jev for Network Traffic Classification: Accuracy, Processing Time, and Cost

- **Authors:** Shenghe Xu (Amazon.com, Inc.; work outside his role there); Lifan Mei (Xi'an Jiaotong-Liverpool University). **First version:** 2026-09-30. **Version read:** v1. **Primary category:** cs.LG. **License:** arXiv non-exclusive distribution license 1.0.
- **Model actually tested:** hosted Jev via OpenRouter, `typesafe/jev-1.13`; returned identifier `typesafe/jev-1.13-20260917` (§3.2).
- **Comparators:** Random Forest and Extra Trees (8,000 training records); training-majority constant; OpenAI GPT-5.6 Sol at high reasoning effort via Azure.
- **Design:**
  - Data: CESNET-QUICEXT-25, 10 application labels, first 10 packets only (sizes, directions, inter-packet times). Numeric input, no text semantics.
  - Test set: 52,000 records from collection weeks 5–30.
  - Jev context sizes: 0, 40 or 150 labelled examples.
  - Paired 100-record subset against Sol.
  - Metrics: accuracy, macro-F1, latency, API cost (§3).
- **Key findings:**
  - G1 (accuracy, Table 1):
    - Jev-0: 9.80%, below the majority constant (22.79%).
    - Jev-40: 28.42% (macro-F1 0.3799).
    - RF: 69.95%; ET: 66.80%.
    - Zero-shot predictions concentrate on two classes: google-www 45,010 and youtube 6,958 (§4.1).
    - RF and ET beat Jev-40 in all 26 weeks (§4.2). Jev-150 reaches 34.50% on week 5 (§4.3).
  - Paired subset (Table 2): Jev-40 29% vs Sol-40 37%; exact McNemar p = 0.2005 (not significant).
  - G7 (latency and cost):
    - Median latency 0.750 s (Jev-40) vs 6.036 s (Sol-40) (Table 2).
    - 52,000 Jev-40 decisions cost US$14.68 (API-reported known cost) (Table 3).
    - Per 100 paired responses: Jev-0/40 US$0.002341 / 0.028234; Sol US$3.927254 / 5.613564 (estimates, not invoices) (§4.5).
  - Reliability: Sol produced 200 valid labels in 211 attempts (§4.5).
  - Calibration: outside the study's scope.
  - Authors' limitations:
    - One network and one fixed context family.
    - No matched-label tree control.
    - Week-5 data reused for extensions.
    - Pretraining overlap unknown (§5).
- **Proposed axes and codes:**
  - G1 — **N** (empirical: yes). On purely numeric evidence, Jev zero-shot is below a majority baseline, and even with 150 examples it stays far below small trained trees.
  - G7 — **Q** (empirical: yes). Cheap and fast at 52k scale, but the accuracy gap removes the practical benefit for this task.
- **Relevance to a PoL2-style safety valve:** Boundary evidence. When the evidence a clause depends on is numeric telemetry, not text, Jev should not be the detector. A valve fed with raw numbers needs code to turn them into stated facts first. This matches 2609.39496 and 2610.01834.
- **Quality notes:**
  - Large N (52,000); one run per arm.
  - Aggregate data and hashes are released, but not every raw response.
  - Not vendor-affiliated.

### 2610.00831 — AnyJev Technical Report

- **Authors:** Jiamu Zhang; Tianze Yang; Yucheng Shi; Evan Chen; Zixiang Nie; Kelly Wan; Liangjie Hong; Ninghao Liu; Liang Wu (Nokia Applied Research; Tencent Hunyuan; The Hong Kong Polytechnic University). **First version:** 2026-09-30. **Version read:** v1. **Primary category:** cs.LG. **License:** CC BY 4.0.
- **Model actually tested:** open Jev-style readout only; no hosted Jev.
  - AnyJev reads typed decisions from one prefill of 13 frozen instruction-tuned LLMs: Qwen3 1.7B–32B, Qwen2.5-7B, Llama-3.2-3B, Mistral-7B, Granite-3.3-8B, Phi-4-mini, SmolLM2-1.7B, OLMo-2-7B, gpt-oss-20b, plus Qwen3.5-9B.
  - Published Jev-like baselines: Bespoke-Nimble-9B, Laya typed-decisions, NanoJev, Qwen3-Reranker-0.6B (§6; App. E).
- **Design:**
  - Corrections tested: label-prior division (batch calibration, α = 0.75) and log-space averaging over K cyclic option rotations, with a Clopper–Pearson stopping rule.
  - Tasks:
    - banking20 and 20 Newsgroups (K = 20) and a binary prompt-injection question, 300 items each.
    - JevBench public subset: 213 of 231 items scored.
    - BEV Decision Mix test: 46,320 decisions.
    - Serving test: 300 decisions of an 18-option MASSIVE routing question.
- **Key findings:**
  - G3 (order dependence):
    - Reversing the option list changes the answer on 32.8% (banking20) and 33.4% (newsgroups) of items, averaged over 11 models (§3).
    - Rotations lower this to 0.138 and 0.183 and raise accuracy on 11/11 models (sign test p = 4.9 × 10⁻⁴) (Table 1, §7.1).
    - Injection-task flips: 0.180 → 0.000.
  - G1/G2 (prompt-injection detection by open readouts):
    - Mean accuracy 0.720 (raw), 0.733 (+rotations), 0.762 (+rotations + prior) across the models passing the answer-mass gate (Table 1).
    - Rotations improve accuracy on only 3 of 7 non-tied rows (p = 0.77).
    - 3 of 11 models fail the answer-mass gate on this task (m = 0.408, 0.710, 0.976) (§3).
  - G4 (calibration):
    - Rotations + prior: ECE 0.251 → 0.223 on banking20. A temperature fitted on labels brings it to 0.088 (Table 1).
    - "We did not measure a label-free procedure that detects this" (§4.3).
    - On JevBench, the temperature raises Granite-3.3-8B ECE from 0.270 to 0.301 (§7.2).
    - On BEV, the label prior lowers accuracy (Qwen3.5-9B: 68.01% → 65.01%) (§7.3).
  - G5 (audit signals):
    - The answer-mass statistic m exposes template faults: gpt-oss harmony gave m = 0.000 while answers "still looked plausible" (§3).
    - The stopping rule certifies agreement with the full-rotation decision at a verified bound of 0.0079 on 2 of 4 cells (§5).
    - In the serving run, the threshold was selected and certified on the same states, and the held-out disagreement was 4/300 = 0.013 (Table 3; §9).
  - G7 (throughput): the rotation budget serves 37.2 vs 16.7 decisions/s on vLLM, a 2.22× speed-up (Table 3).
  - Open baselines on BEV (Table 14): Nimble-9B 70.57%; Laya 56.20%; NanoJev 32.99%.
  - Authors' limitations:
    - One prefill cannot reason.
    - JevBench has few options.
    - 20-option results have no intervals.
    - Serving threshold selected and certified on the same sample (§9).
- **Proposed axes and codes:**
  - G3 — **Q** (empirical: yes). Jev-style readouts from open LLMs carry about 33% order dependence. Rotation averaging cuts it to 14–18% but does not remove it.
  - G4 — **Q** (empirical: yes). Label-free corrections do not deliver calibration; a labelled temperature does on most models.
  - G1 — **Q** (empirical: yes). Binary prompt-injection screening by frozen open readouts reaches only about 0.72–0.76 mean accuracy.
  - G5 — **Q** (empirical: yes). Answer-mass and certified-agreement statistics are useful runtime audit signals for open replicas.
- **Relevance to a PoL2-style safety valve:** If PoL2 runs a self-hosted Jev-like valve instead of hosted Jev, this paper sets the minimum operational checks. Four follow: (1) average over option orders, or sort options canonically; (2) log answer mass and reject low-mass calls; (3) fit a per-question temperature on labelled data before trusting thresholds; (4) certify any shortcut against the full-rotation decision on a separate split.
- **Quality notes:**
  - Self-evaluation by the method's developers (Nokia).
  - 300 items per 20-option cell, without per-item intervals.
  - Not related to TypeSafe.
  - Code open source (github.com/nokia-applied-research/AnyJev).

### 2610.02076 — LLM2Jev: LLMs Are Already Jev-Style Decision Models -- When and How to Fine-Tune Them

- **Authors:** Yinheng Li; Justin Wagle (Microsoft). **First version:** 2026-10-01. **Version read:** v1. **Primary category:** cs.CL. **License:** CC BY 4.0.
- **Model actually tested:** open replicas only.
  - LLM2Jev readout and fine-tuning on Qwen3.5-4B and Qwen3-0.6B.
  - Compared with community Jev-style models: SemIf, reflex 4B, open-alternative-jev, Winnow-12B. Also GPT-5.6 Sol in generation mode.
  - Hosted Jev was not run. Jev 1.13.0 = 86.6% on JevBench appears only as a leaderboard figure in App. I, Table 15.
- **Design:**
  - Evaluation sets:
    - JevBench public: 231 items.
    - External benchmarks: BoolQ, MMLU, MMLU-Pro, ARC-C, WinoGrande, SciQ, Banking77.
    - Multimodal: MMBench, MMStar.
    - General abilities: GSM8K, IFEval, TriviaQA, LAMBADA, WikiText-2.
    - Conversation: Dolly-15k, MT-Bench.
  - Six training mixtures plus anchor and LoRA ablations.
  - Metrics: accuracy, ECE, Brier; exact sign tests (§4.1).
- **Key findings:**
  - G4 (training-free calibration, Table 2):
    - Qwen3.5-4B: 81.4% on JevBench (188/231) with ECE 0.057.
    - SemIf 80.5% (ECE 0.061); reflex 4B 79.7% (0.070); open-alternative-jev 75.8% (0.108); Winnow-12B 86.6% (0.058); GPT-5.6 Sol 94.4%.
    - Qwen3-0.6B: ECE 0.278; Banking77 22.2%.
  - G4 (abstention damage from fine-tuning):
    - Intent-only fine-tuning produced "an aggressive confirmation bias toward 'yes'", "severe suppression of 'none of the above' fallback options", reliance on lexical matches and overconfidence.
    - JevBench fell from 81.4% to 79.2% after 100 steps and 76.2% after one epoch, while in-distribution validation loss kept improving (§4.3.2).
  - G5 (readout and generation consistency): the 4B model selects the same candidate in parallel scoring and greedy generation on all 231 items (§4.2).
  - Fine-tuning stability: without KL anchors, the 4B model runs on after the identifier in 69/231 queries; anchors λ ≥ 0.01 eliminate this (§4.4.1). Best result: LoRA at 84.0% (§4.4.3).
  - Authors' limitations: JevBench used only as an exploratory diagnostic, because training-data choices were informed by JevBench error analysis (§3.5). No separate limitations section.
- **Proposed axes and codes:**
  - G4 — **Q** (empirical: yes). Open 4B readouts are reasonably calibrated out of the box. Narrow fine-tuning can silently create yes-bias and suppress "none of the above" even while validation loss improves.
  - G3 — **Q** (empirical: yes, qualitative error analysis only). Fine-tuned models rely on surface lexical matches.
- **Relevance to a PoL2-style safety valve:** Relevant if PoL2 fine-tunes its own valve model. Training on narrow labelled data can erase the "insufficient" behaviour and shift binary verdicts toward "yes" (i.e., "conforming"). That is the failure a safety valve can least afford. Any fine-tuned valve should be checked out of distribution for yes-rate and fallback-option use, not only on validation loss.
- **Quality notes:**
  - One training run per configuration; sign tests.
  - Evaluated on the public JevBench subset only.
  - Microsoft authors; not TypeSafe.
  - Own code repository: not stated (the URLs given point to other projects).

### 2610.02048 — HydroJEV: A one-second, training-free screen for cyber-attack and fault attribution in water distribution networks

- **Authors:** Tianwei Mu; Shengyan Jiang; Mingzhe Yuan; Qing Luo; Min Xiao; Wenhong Wang; Jun Li; Manhong Huang. **First version:** 2026-10-01. **Version read:** v1. **Primary category:** cs.AI. **License:** CC BY 4.0.
- **Model actually tested:** hosted Jev, "model jev-1.13.0 for every call" (§2.3).
- **Comparators:**
  - R1: hand-written rule tree (and R1b with a physics override).
  - R2: supervised logistic regression, in three forms: full labels, leave-one-subtype-out, and k labels per class.
  - Seven cloud LLMs: deepseek-v4-pro, glm-5.2, gpt-oss:120b, gpt-oss:20b, gemma4, gemma4:31b, minimax-m2.7 (§2.4–2.5).
- **Design:**
  - Data: simulated EPANET C-Town SCADA 6-hour windows.
  - Classes: cyberattack, physical fault, normal transient, sensor fault, plus an "insufficient evidence" option.
  - Evaluation: 1,279 windows in four sealed, pre-registered rounds with hashed designs. Rounds 5–6 transfer the screen unchanged to Net3 and Net1 (4 × 200 windows).
  - Jev correction: label-free prior from 40 unlabelled development windows.
  - Cascades:
    - Rule cascade: accepts every benign Jev verdict.
    - Agreement-gated LLM cascade: accepts a benign Jev verdict only if R1 agrees.
  - Statistics: macro-F1; paired bootstrap; Holm correction; non-inferiority margin 0.03 (§2).
- **Key findings:**
  - G1 (accuracy):
    - In-distribution Jev macro-F1: 0.620, 0.628, 0.628, 0.644 (mean 0.63) vs R1 mean 0.59. No single difference is significant. New event families: 0.51 vs 0.50 (§3.1).
    - Fully supervised R2: 0.887–0.934.
    - Without the prior correction Jev scores 0.41 vs 0.57 with it (rounds 1–3), because raw Jev over-weights physical faults (§3.6).
  - G1 (unseen subtypes): Jev beats leave-one-subtype-out R2 by +0.361 [0.189, 0.523], +0.387, +0.390 and +0.417 [0.344, 0.488], all p < 10⁻⁴ (§3.2). Label crossover k* = 4 on 7 of 8 sets (§3.3).
  - G1 (vs LLMs):
    - glm-5.2: 0.706 / 0.697; deepseek-v4-pro: 0.722 / 0.637; Jev: 0.628 / 0.434 on round 2.
    - 4 of 14 Holm-corrected comparisons are significant, all favouring an LLM (§3.4).
  - G2 (concealed manipulation):
    - Mean cyberattack recall 0.34, vs 0.60–0.71 for other classes; R1 0.32; R2 0.87 (§3.6).
    - On the look-alike family set E4c, the agreement gate's accept precision was 0.58 [0.47, 0.68], vs 0.84 in distribution. 21 of 76 accepted windows were attacks: 12 masked duty swaps and 9 level spoofs (§3.5).
    - True attacks given any non-benign verdict fell from 20 to 15 of 50 (glm-5.2) and from 30 to 23 of 50 (deepseek) (§3.5).
  - G6 (gated cascade):
    - On fresh sealed sets, Jev + R1 agreement gate + glm-5.2 is non-inferior to glm-5.2 alone: +0.011 [−0.011, 0.033] and +0.016 [0.003, 0.033] (p < 10⁻⁴).
    - It settled 69/200 (34.5%) and 76/200 (38.0%) windows. Mean time fell from 43.5 s to 30.6 s (§3.5).
    - Without the gate, burst recall fell from 0.78 to 0.52 (13/50 bursts called benign).
    - The gate lowered the accept rate from 0.45 to 0.29, raised accept precision from 0.75 to 0.83, and cut accepted physical faults per set from 8.4 to 1.9 (§3.5).
    - The gated cascade stayed within the non-inferiority margin on all four transfer sets (§4.3).
  - G7 (latency): Jev median compute 1.22 s (10th–90th percentile 1.15–1.46) over 2,722 calls, vs glm-5.2 30.6–31.7 s and deepseek 39.3–46.4 s per decision (§3.4). Monetary cost: not reported.
  - BATADAL side study: AUROC 0.884; as a veto on rule alarms, FPR fell from 25.6% to 7.0% at TPR 81.2% (§3.6).
  - "Insufficient evidence" option: offered, but usage not reported.
  - Authors' limitations:
    - All windows simulated; one hydraulic model generates both events and twin.
    - LLM timing from one client.
    - The benign gate accepts attacks that both judges miss.
    - Concealed manipulation is the hardest class (§4.4).
- **Proposed axes and codes:**
  - G1 — **Q** (empirical: yes). Matches an expert rule tree and generalises to unlabelled subtypes, but below supervised models and frontier LLMs, and needs a prior correction.
  - G2 — **N** (empirical: yes). Concealed or spoofed telemetry, designed to look benign, is accepted as benign; cyber recall is 0.34.
  - G6 — **Q** (empirical: yes, pre-registered). Agreement with an independent judge is what makes a Jev screen safe to accept, and the gated cascade held on fresh and transferred sets. Leakage of look-alike attacks remains.
  - G7 — **Q** (empirical: yes). 20–40× faster than frontier LLMs; cost not reported.
- **Relevance to a PoL2-style safety valve:** Strongest evidence so far for a specific valve architecture. Let the typed model settle only the low-risk verdict (here "benign"; in PoL2 terms "conforming"), and only when an independent, differently built judge agrees. Send everything else, including every "violating" or "insufficient" outcome, to slower review. The pre-registered sealed rounds are a model for validating such a valve. The look-alike-attack leakage shows why the valve should not be the sole defence against adversarially disguised violations.
- **Quality notes:**
  - Pre-registered, sealed, hashed rounds with Holm correction.
  - One Jev call per window; simulated data.
  - No COI declared.
  - All responses, prompts and code released (github.com/mutianwei521/hydrojev).

### 2610.01834 — Code Owns the Simulation, Jev Owns the Evaluation

- **Authors:** Yaodong Yang; Hongyao Tang; Yi Ma; Xingyu Fan; Weixun Wang; Jinpeng Li; Tianpei Yang (CUHK; Tianjin University; Shanxi University; independent researcher; CAIR-HKISI CAS; Nanjing University). **First version:** 2026-10-01. **Version read:** v1. **Primary category:** cs.AI. **License:** CC BY 4.0.
- **Model actually tested:** hosted Jev, "version jev-1.13.0", zero-shot (§2).
- **Design:**
  - Tasks:
    - 150 Cognitive Reflection Test (CRT) items × 4 option orders.
    - 210 random 3×3 matrix games × 3 orders.
    - ALFWorld: 140 seen and 134 unseen games.
    - DeepMind Control Stacker: 20 native and 40 new-instruction episodes.
  - Every decision is labelled evaluation vs simulation and aligned vs misleading, computed from the environment, not from Jev's choices.
  - Comparators:
    - Surface-shortcut rule.
    - Published human/GPT CRT results.
    - Hand-written controller; random.
    - Word-overlap rule with the same lookahead (§2–6).
- **Key findings:**
  - Evaluation succeeds: CRT 0.99 correct, 0.01 intuitive answer; control items 0.96 (Table 1).
  - G2 (manipulation by surface cues):
    - Misleading games: accuracy 28–37% with the lure picked in 53–71%. An instruction to reason does not help; stating the opponent's action gives 97–99% (§4.1).
    - ALFWorld seen: 93% on E steps and 99% on aligned S-known steps, but 36% on misleading steps, where the lure (a command naming a task object) is picked 56% of the time. Unseen: 96 / 95 / 43 / 51% (§5.1).
    - 90% of game errors and 89% of misleading ALFWorld errors go to the lure, vs 50% and 12% expected by chance (§8).
    - Wording "after cleaning it" gives 24% correct vs 69% when cleaning is mentioned first (§8).
  - G5 (decomposition of the decision chain):
    - In a separate call, Jev predicts the opponent's action correctly 90% of the time. Its single-call choice is still only 32–35% correct whether or not that prediction is right.
    - Writing its own prediction into the state gives 94%. Given a wrong written action it plays the best response to that action in 24/26 calls (§4.3; Table 2).
  - G6 (code-supplied simulation):
    - ALFWorld lookahead raises solved unseen games from 42/134 (31%) to 116/134 (87%). Word-overlap with the same lookahead solves 18 (§5.3).
    - Stacker: raw torques 0/20; code-simulated skills 9/20 vs controller 8/20; new instructions 22/40 vs 3/40 (Table 3).
  - Reproducibility caveat: "Repeating a single call changes its probabilities by 0.04 on average"; option order shifts probabilities, so decisions are averaged over orders (§2; Reproducibility).
  - Authors' limitations:
    - One model and one API version.
    - Exact environment copies are used for lookahead.
    - One-step lookahead only.
    - Partly post-hoc analysis of which predictions Jev can make (§8).
- **Proposed axes and codes:**
  - G2 — **N** (empirical: yes). Lexical overlap with the task description reliably pulls Jev to the wrong option whenever the correct one requires unstated inference.
  - G5 — **Q** (empirical: yes). Splitting a decision into an explicit prediction step, written into the state, and an evaluation step makes the chain inspectable and largely fixes the failure. Jev also follows a written-in wrong premise.
- **Relevance to a PoL2-style safety valve:** Gives a design rule for clause evaluation. A valve should only be asked questions that can be settled from facts present in its input. Anything that requires predicting consequences, ordering subgoals or inferring an unstated step should be computed by code, or by a separate logged call, and written into the state. Clause and option wording must avoid echoing words of the case description, because echoes act as lures. Because Jev follows whatever premise is written in, the intermediate facts are themselves audit points.
- **Quality notes:**
  - Moderate sample sizes; option-order averaging; bootstrap intervals.
  - Academic authors.
  - Code and raw runs promised ("We will release"), not yet linked.

### 2610.01231 — Judgement in the Age of Jev: From Evaluation Scarcity to Evaluation Abundance

- **Authors:** Richard Hill (University of Huddersfield). **First version:** 2026-10-01. **Version read:** v1. **Primary category:** cs.CY. **License:** CC BY-SA 4.0.
- **Model actually tested:** none. This is a conceptual perspective that treats hosted Jev and TypeSafe's vendor claims as a "technological provocation" (§1–2).
- **Design:** integrative conceptual synthesis drawing on rebound economics, cheap prediction, machine evaluation, reliance and executive-judgement literature. No data.
- **Key arguments (non-empirical):**
  - G7: a conditional "Jevons hypothesis for machine evaluation": cheaper evaluation may increase total evaluation consumption, e.g. moving from sampling 10% of transactions to all of them. The relevant cost is "the total cost of a usable evaluative act within a workflow, not inference price alone" (§5).
  - G6: confidence thresholds and exception routing "can allocate attention and practical decision rights", and should be studied as organisation design: who sets thresholds, and which cases become invisible (§7.5, §9).
  - G6 (correlated evaluators): many machine evaluators may give little independent evidence. The paper cites a third-party finding that nine LLM judges were worth about two independent votes (§6.3).
  - G5: "qualification attrition": downstream evaluators cannot restore qualifications lost from the representation they receive (§6.2, §8.3).
- **Proposed axes and codes:**
  - G6 — **Q** (empirical: no). Thresholds reallocate decision rights; evaluator independence must be established architecturally, not by counting evaluators.
  - G7 — **Q** (empirical: no). Public-scale deployment may increase, not reduce, total evaluation and exception-handling demand.
  - G5 — **Q** (empirical: no). Auditability depends on preserving qualifications up to the point of authorisation.
- **Relevance to a PoL2-style safety valve:** Supplies governance vocabulary that the empirical papers lack. Setting a valve threshold is a delegation of decision rights. Agreement between valve instances is not independent corroboration if they share evidence and criteria (compare the R1 agreement gate in 2610.02048, which works because R1 is built differently). Cheap valves may multiply the cases needing human review.
- **Quality notes:** No empirical content. Single author; no COI. Vendor performance figures are explicitly not treated as evidence.

### 2610.01079 — Jev-IDS: System One Models for Network Intrusion Detection

- **Authors:** Paulo Severo; Silvio E. Quincozes; Amanda Dias (Federal University of Pampa, Brazil). **First version:** 2026-10-01. **Version read:** v1. **Primary category:** cs.CR. **License:** CC BY 4.0.
- **Model actually tested:** hosted Jev, "we explicitly specify the jev-1.13.0 Jev version" (§4.2).
- **Comparators:**
  - Methods sections and tables: Gemini 3.6 Flash with structured output.
  - **Abstract and conclusion name "GPT-5.6 Luna" instead.** See quality notes.
  - Random Forest: k-shot and full pool. Isolation Forest: unsupervised (§5.2).
- **Design:**
  - Data: NSL-KDD evaluation set of 2,000 flows: 874 normal, 1,126 attacks, of which 300 are "novel" attack types absent from KDDTrain+ (Table 1; §5.3).
  - Labelled examples per category: k ∈ {0, 1, 2, 4, 8}, three sampling seeds, so 6,000 decisions per finite k.
  - Two typed questions per flow: noul attack probability (threshold 0.5) and a 5-way category choice.
  - Invalid outputs counted as benign (fail-open) (§5.1).
  - Metrics: F1, precision, recall, novel recall, PR-AUC, ROC-AUC, McNemar, latency, list-price cost.
- **Key findings:**
  - G1 (Table 2):
    - Jev F1: k = 0 0.782 ± 0.005; k = 1 0.856 ± 0.025 (precision 0.953, recall 0.778, novel recall 0.747, PR-AUC 0.952, ROC-AUC 0.950); k = 8 0.854 ± 0.017.
    - Gemini F1: k = 1 0.880; k = 4 0.884.
    - RF: k = 1 F1 0.748, precision 0.598 (about 764 false alarms per seed vs about 43 for Jev) (§6.1). Full pool: F1 0.765, novel recall 0.263.
  - G1 (paired tests, Table 3):
    - Gemini wins discordant decisions on all flows at every k (p < 0.001).
    - Jev wins on novel attacks at k = 1 (74 vs 44, p = 0.007) and k = 2 (105 vs 57, p < 0.001). Not significant at k = 4 (p = 0.353) or k = 8 (p = 0.221).
    - Novel R2L recall: Jev 0.151–0.262 vs Gemini 0.000–0.071 (§6.2).
  - G7 (Table 4): Jev 308–335 ms vs Gemini 1.99–2.65 s; US$43–295 vs US$1,068–3,035 per million flow decisions. At k = 1: 7.7× faster, 22× cheaper.
  - G4: "probability calibration was not evaluated" (§6.1).
  - G6: a cascade escalating uncertain cases to an LLM or analyst is proposed but "not evaluated" (§7).
  - Authors' limitations:
    - NSL-KDD is dated; novelty is benchmark-specific, not real zero-day.
    - Common threshold, not optimized.
    - Repeated evaluation of the same flows across seeds not accounted for (§7).
- **Proposed axes and codes:**
  - G1 — **Q** (empirical: yes). High-precision detector with few labels, but lower recall than an LLM comparator, on a dated benchmark.
  - G7 — **Q** (empirical: yes). Order-of-magnitude cost and latency advantage; hosted-API latency is still far above local ML.
- **Relevance to a PoL2-style safety valve:** Moderate. It shows a pattern relevant to a "violating" detector: Jev is conservative (high precision, lower recall). A valve built on it would under-flag violations unless thresholds are tuned or low-confidence cases are escalated. The fail-open handling of invalid outputs is the opposite of what a safety valve should do.
- **Quality notes:**
  - Three seeds; 2,000 fixed flows.
  - **Internal inconsistency:** the abstract reports a "300-flow NSL-KDD pilot split", "5,400 decisions", F1 0.859, precision 0.941, recall 0.790, novel recall 0.838, k = 2 F1 0.839, "4.8 times faster and 3.8 times cheaper than GPT-5.6 Luna" and "15 times fewer false alarms". None of these match the body tables, which use Gemini 3.6 Flash, 2,000 flows and 6,000 decisions per k.
  - Contributions claim "two intrusion datasets"; only NSL-KDD is reported. Body figures are used above.
  - Funded by FAPERGS; no COI declared.
  - MIT code, prompts, splits and per-flow predictions released (github.com/jev-ids/jev-ids, commit 286a310).

### 2610.01006 — Beyond Answer Confidence: A Controlled Audit of Self-Knowledge in a Black-Box Decision Model

- **Authors:** Sharath M Shankaranarayana; Davor Runje; Jan Jannink (Synthpop.AI). **First version:** 2026-10-01. **Version read:** v1. **Primary category:** cs.AI. **License:** CC BY-NC-SA 4.0.
- **Model actually tested:** hosted Jev. The authors requested `jev-latest`, and "every response reported jev-1.13.0" (collection 26–30 Sept 2026) (§3). Open comparators (appendix): GLiNER2.5-Decide and a 5-member MiniLM deep ensemble.
- **Design:**
  - Paired interventions that vary the information supplied for a fixed item.
  - Data: over 15 public datasets (Banking77, CLINC150, PopQA, Daily Oracle news, HotpotQA, Quizbowl, TriviaQA, SimpleQA, MMLU-Redux/CF, ANLI, SelfAware, AmbigQA, ChaosNLI, etc.) and 6 generated task families.
  - Scale: 575,442 paid calls (573,234 analysed). Every cell queried 3 times and averaged.
  - Follow-up yes/no questions: settled, enough, known.
  - Metrics: SmoothECE, AUROC, total variation. Item- and month-clustered bootstrap (§3; App. D).
- **Key findings:**
  - G4 (calibrated when familiar):
    - SmoothECE: CLINC150 0.015–0.025; PopQA quintiles 0.020–0.033; MMLU-Redux 0.016; TriviaQA 0.031 (§4.1).
    - Abstaining below p_max 0.9 keeps 8,132/9,960 TriviaQA questions with 20 errors (§4.1), and 365/1,000 SimpleQA Verified with 1 error (App. C).
  - G4 (fails as an ignorance signal, Table 3):
    - Opaque intent codes: p_max 0.32 / 0.36 vs ideal 0.013 / 0.007 (GLiNER2.5-Decide: 0.017 / 0.010).
    - Fair die: 0.80 on "one" across all 720 orders. Fabricated entities: 0.52. Made-up future event: 0.76.
    - "A guess 'made with no information' raises the guessed option by 0.65" (§4.1).
  - G4 (knowledge boundary):
    - Past an observed late-2024 change point, Jev answers "no" to 92% of news questions vs 61% before; true share of "no" is 51–52%. Confidence rises from 0.75 to 0.82.
    - Log loss 0.71, worse than always answering 50/50 (0.69) (§4.1).
    - Gap +0.305 (Table 12). Recalibration on earlier months leaves 0.19–0.23 overconfidence. No order-preserving map reaches below 0.047 period-conditional error (§4.1).
  - G2 (manipulation by context): related but non-supporting paragraphs cut HotpotQA accuracy from 0.84 to 0.75 while confidence stays at 0.83 (§4.2). Stating that context may be irrelevant restores 0.84 (§4.3).
  - G4/G6 (targeted questions, Table 1):
    - "settled": AUROC 1.00.
    - "enough": 0.95 vs 0.85 for confidence.
    - "known": 0.91 on original contrasts, but drops to 0.74 with look-alike names (answer uncertainty 0.76) and 0.58 with dates removed (answer uncertainty 0.56).
    - Deleting a deciding fact drops P(enough) from 0.83 to 0.10, and a "cannot tell" option receives 0.91 (§4.2).
    - "enough" is 2–6 points less accurate than confidence as an acceptance filter at equal coverage (§4.2).
  - G6 ("not known" option, §4.3; App. C):
    - Chosen for 93% of post-boundary vs 36% of earlier questions.
    - Matched-coverage accuracy vs a confidence threshold: +0.051 when half the questions are post-boundary, +0.010 [−0.002, 0.043] at the panel mix of 0.27, −0.034 at 5%.
    - An explicit out-of-scope option flags 89% of off-topic CLINC150 requests at 3.5% false alarms (AUROC 0.982), but only 36% of held-out Banking77 intents with close relatives (App. C).
  - G3 (salience): ties follow the order in which chances are mentioned (99.6%) and preferences follow labels, not display positions (App. C). Under stated odds, Choice puts 0.98 on a 40% outcome; asking one yes/no question per outcome gives MAE 0.030 (Table 4).
  - Non-determinism: replicate SD ≈ 0.04 near p = 0.5; probabilities quantised to 0.01 (§3). 14 rewordings rank contrasts at AUROC 0.87–1.00 but shift absolute levels, so "thresholds must be set per wording" (§4.2).
  - Authors' limitations:
    - One version of one closed model.
    - Cue controls are exploratory and post hoc.
    - Date-removal labels come from a single AI-assistant annotator.
    - The boundary is an accuracy change point, not a verified cutoff (Limitations).
- **Proposed axes and codes:**
  - G4 — **Q** (empirical: yes). Confidence is calibrated on familiar closed-choice tasks but is a confident wrong signal under missing information or beyond the knowledge boundary. Separate "enough/settled" questions are much better readouts.
  - G2 — **N** (empirical: yes). Irrelevant or misleading context and uninformative cues move answers (+0.65) without lowering confidence.
  - G6 — **Q** (empirical: yes). Confidence-threshold abstention and explicit "not known"/out-of-scope options work in-scope or when boundary cases are common, and fail on near-scope inputs or at low prevalence.
  - G3 — **Q** (empirical: yes). Systematic salience and label preferences when evidence is uninformative.
- **Relevance to a PoL2-style safety valve:** Core evidence for the "insufficient" state. Jev's top-option confidence must not be used to detect missing evidence: with no relevant information it still backs a salient option at up to 0.80. The paper's practical recipe maps onto a valve: ask an explicit yes/no "is the evidence sufficient?" question on the same call (AUROC 0.95). Set its threshold per wording on held-out data, and treat "insufficient" as a separate decision from "conforming/violating". The paper also shows such an option must be validated at the expected prevalence of out-of-scope cases.
- **Quality notes:**
  - Very large and replicated (3 calls per cell).
  - Authors flag several analyses as exploratory or post hoc.
  - Not vendor-affiliated (Synthpop.AI).
  - Code released (github.com/Syntheme/beyond-answer-confidence).

### 2610.02046 — Prune First, Decide Fast: Scalable Semantic Query Processing with JEVDB

- **Authors:** Zhengle Wang; Hanxu Yan; Fuheng Zhao; Chunwei Liu (Purdue Data & AI System Lab; University of Utah). **First version:** 2026-10-01. **Version read:** v1. **Primary category:** cs.DB. **License:** CC BY 4.0.
- **Model actually tested:** hosted Jev **jev-1.13.0**, in two modes (§4.1):
  - JEVDB-Flash: Jev at a fixed 0.5 threshold, no escalation.
  - JEVDB: Jev fast path plus a calibrated uncertainty band escalated to gpt-6-luna.
  - The paper states the project "is not affiliated with or endorsed by TypeSafe AI".
- **Design:**
  - SemBench: 21 text/structured queries. Baselines are LOTUS, Palimpzest and ThalamusDB; their numbers are SemBench's published Gemini 2.5 Flash results (mean of 5 runs). JEVDB-Flash is a single run.
  - Shelob: authors' TPC-DS-derived semantic-join workload, 5 queries × XS/S/M tiers, up to 540,180 candidate pairs per join, 1,200 s limit.
  - Escalation calibration: 400 items per predicate against the LLM judge; tolerated recall/precision loss ε = 0.05.
  - Metrics: query-specific quality (F1 etc.), cost, latency (§4.1).
- **Key findings:**
  - G7 (SemBench, Table 3; §4.2):
    - JEVDB-Flash is fastest on all 21 queries and cheapest on 19.
    - Totals: 41.50 s and US$1.06, vs LOTUS 3,709 s / US$14.28 and Palimpzest 2,988 s / US$19.81.
    - Quality best or tied on 14/21 and within 0.02 on 4 more. Deficits: Movie Q5 0.90 vs 1.00; Q6 0.80 vs 0.84; MMQA Q3f 0.86 vs 1.00.
  - G1 (fixed-threshold Jev is predicate-dependent): on Shelob, JEVDB-Flash mean F1 is 66.3% / 64.0% / 63.2% (XS/S/M). Q4 reaches only 23.8–30.4% F1, Q1 85.3–88.9% (Table 4, §4.3).
  - G6 (calibrated escalation):
    - Full JEVDB reaches 91.5–98.7% F1 (means 97.5 / 96.1 / 95.7%) at total latency 320.6 / 727.8 / 2,616 s and cost US$0.37 / 1.16 / 5.81, plus a one-off US$0.54 index (Table 4, §4.3).
    - Semantic Bloom Filters remove 87.4% of 1.78M candidate pairs. Condition-index scoring cuts escalations from 194K to 87K (−55.2%) (§4.3).
  - Baselines: 14 of 45 baseline tier–query runs finish within 1,200 s; none finishes at tier M (§4.3).
  - Authors' limitations: given as future work only (cost-based SBF selection; multimodal; maintenance and versioning of the semantic index against model and prompt) (§5).
- **Proposed axes and codes:**
  - G6 — **Q** (empirical: yes). A band calibrated on 400 items per predicate turns an unreliable fixed-threshold Jev (≈64% F1) into a ≈96% F1 pipeline. The reference is an LLM judge and the authors' own answer keys, not humans.
  - G7 — **Q** (empirical: yes). Strong cost and latency scaling at 10⁵–10⁶ candidate decisions; single runs.
  - G1 — **Q** (empirical: yes). Accuracy at a fixed threshold varies from 24% to 89% F1 by predicate, so each predicate needs validation.
- **Relevance to a PoL2-style safety valve:** Shows the valve pattern "Jev decides when confident, escalates a calibrated uncertainty band" at very large scale, with explicit precision/recall loss tolerances. The ≈64% → ≈96% gap shows that a fixed 0.5 threshold is not a safe default for any clause. It also points to a maintenance duty: cached semantic indexes must be versioned against the model, prompt and condition.
- **Quality notes:**
  - JEVDB-Flash and JEVDB are single runs; SemBench baselines are taken from published tables, not rerun.
  - **Inconsistency:** the abstract claims 72–89× latency and up to 18.7× cost reduction; the conclusion states 88× / 71× and 12.5× / 17.4×.
  - Academic; non-affiliation with TypeSafe stated.
  - Code and benchmarks "previewed at https://jevdb.org".

---

## 3. Notes for integration

- **Overlap with the existing corpus:** none of the 15 IDs or keys collide with `paper/corpus.bib`. Authors Rafe & Das already have one corpus entry (a crash-narrative calibration companion). 2610.00213 and 2610.00346 are their follow-ups.
- **Multi-axis papers most worth adding to the G4/G6 synthesis:**
  - 2609.39496 (G4 N: "None" option fails)
  - 2610.01006 (G4 Q / G2 N: confidence is not an ignorance signal; "enough" question works)
  - 2610.00346 (G3 N, G6 Q: out-of-scope leakage 0.310; polarity flips)
  - 2610.02048 (G6 Q, pre-registered gated cascade; G2 N, concealed attacks)
- **Data-quality flags to carry into the evidence table:**
  - 2610.01079: abstract/body mismatch.
  - 2610.02046: abstract/conclusion speed-up mismatch.
  - 2609.40241: unpinned alias.
  - 2609.39496: version not stated.
