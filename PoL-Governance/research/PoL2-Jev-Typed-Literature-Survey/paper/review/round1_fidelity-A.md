# Round 1 — Fidelity review A: Section 4, axes G1–G3 (sections/04_evidence.tex, lines 1–178, incl. Figure `fig:fragility`)

Reviewer lens: does every number and attributed claim match its source? Sources were checked against full text: the local PDFs (scratchpad/fulltext), arXiv HTML for non-local preprints, Zenodo full texts (PDF/MD/zip via the API), the grey URLs, and GitHub (README, plus the README at the v0.1 commit 33cc930 and the commit 7cd0164 of zh-decision-bench).

## Verified claims (correct as written)

- L12: Just Ask Jev has ten failure types, 44 benchmarks, five target models and 7,193 instances — arx29429 abstract; Sec. 3; Table 1. jev-1.13.0 confirmed (Sec. 3, l.387).
- L13: median AUROC 0.886 [0.821, 0.952] over 31 benchmarks, zero-shot — arx29429 Sec. 4.1.
- L13: beats the baselines on most benchmarks (25/31) — arx29429 Sec. 4.1. See the nit on the word "supervised", NEW-fidA-5.
- L13: 63× cheaper; $0.30 vs $18.96 over the 19 judge-scored benchmarks — arx29429 Sec. 4.5.
- L14: StrongREJECT κ 0.809 vs 0.811 — arx29429 Sec. 4.5.
- L15: median +0.006 out of sample — arx29429 Sec. 4.2. See the CI hedge, NEW-fidA-4.
- L17–18: failures are relational, and much of the context gain comes from fields that encode the label — arx29429 abstract; Sec. 1.
- L21: pooled ECE 0.047, median per-benchmark ECE 0.168 — arx29429 Sec. 4.4. The 0.074 comparator is wrong, see NEW-fidA-1.
- L22: median F1 0.706 at t=0.5 and 0.822 with a cross-validated threshold — arx29429 Sec. 4.4.
- L23: the replication covers 5 sub-experiments and 1,155 items (255+150+150+300+300), with median absolute difference 0.0036 — jkf87 README; results/runs/*/metrics.md.
- L23: TensorTrust-hijack naive:noul has F1 0.158 at 0.5 and F1 0.947 cross-validated (2-fold), thresholds 0.35/0.35 — tensor_trust_hijack metrics.md.
- L23: none of the five fitted thresholds is 0.5 — README ("5개 적합 문턱값에 0.5가 하나도 없습니다"); metrics.md.
- L26: 5,219 trajectories, 4 benchmarks, mean positive-class F1 77.8 vs 74.1 (GLM-5.2), median latency 0.99 s, $0.000195 per valid judgement — arx34862 abstract; Tables 2 and 4.
- L27: precision 77.1 vs 91.9; Jev wins 2 of 4 benchmarks (ATBench500, MCPHunt) — arx34862 Table 2; abstract.
- L28: retrospective trace classification; "economical screening signal" — arx34862 abstract.
- L31: Jev vs 3 System One models, 7 judges (2 general + 5 reasoning) and 4 specialists — arx33401 Table 1; Sec. 3.1.
- L32: Jev is the best typed model on R-Judge and AgentHarm, and Nimble (~9B, local weights) leads WAInjectBench — arx33401 Sec. 4.2.
- L32: R-Judge AUROC 0.961 vs Laya 0.533 — arx33401 Sec. 5.2.
- L33: Jev misses all 130 no-EI injections with 1 benign false flag — arx33401 Sec. 4.2.
- L33: p<0.1 — arx33401 Sec. 5.2 (130 of the 133 low-score unsafe items are no-EI).
- L33: 130 false negatives at confidence ≥0.95 — arx33401 Sec. 5.2.
- L35: highest AUROC among the cheap-tier models on all six binary tasks, tie on NLI, 3–63× lower cost — zen22885291 abstract; Sec. 3.1. See the scope issue, NEW-fidA-14.
- L37: 1,916 items, 50 CWE classes, top-1 0.458 vs 0.495, higher top-3/top-5, 55.9× lower cost — arx34963 Table I; Table II.
- L37: pass rate 0.635→0.707, 89 regressions — arx34963 abstract; Sec. IV-B.
- L40: JevLite is a Qwen3-4B LoRA readout; the 3-seed ensemble has AUROC .974 and ECE .052 — arx23959 abstract; Table 2.
- L41: legit (n=12) 100%; gray/legit 38.1%; synthetic callers; test-set exposure; ModernBERT not significantly worse — arx23959 abstract; Table 2.
- L45: five assurance properties; a real P4 enforcement gap in NeuroSploit, which the author develops (competing interest); no Jev mentions — arx22664 abstract; Sec. IX.
- L46: one run with and one without the Jev layer, exploratory — arx28940 abstract; Sec. IX.
- L50: 35.71% FPR for untuned Laya-322M — arx33671 Table II.
- L51: live latency 41.6 ms on N=130 — arx33671 Sec. IV-A; Table III.
- L52: SafetyBench-ZH 60.33→56.81%, and 65.05% with replay — arx33671 Table V.
- L53: Jev not run — arx33671 (appears only in Related Work).
- L70: 510 cases; 9/510 (1.8%) — arx28613 Sec. 5.1.
- L71: the ignore-previous marker lowers attacker probability (−0.032 [−0.060, −0.014]) — arx28613 Sec. 5.2.
- L72: mean best-so-far 0.043→0.084; validated ASR 1.8%→3.5% — arx28613 Sec. 5.4.
- L74: "change but do not eliminate" — arx28613 abstract.
- L77–78: 312/508 = 61.4%, Wilson CI 57.1–65.5 (reported by the authors), 229 at ≥0.7, budget 64, median 31 words — arx30243 Sec. 4.2; Table 1. Jev 1.13.0.
- L79: other systems 64.9–73.2% (Qwen 185/285, OpenSourceJev 238/328, Von 240/328) — arx30243 Table 1. See NEW-fidA-20.
- L80: one-shot target-aware 16.9% vs neutral 2.2% — arx30243 Table 1.
- L81: 89/140 (63.6%) vs 79/140 (56.4%), paired CI 2.1–12.9 pp — arx30243 Sec. 4.3.
- L84: 9,744 variants, 812 questions, 66 scenarios, compared against the clean answer and a re-run — arx31142 Sec. 3.3. jev-1.13.0 pinned. See the nit, NEW-fidA-22.
- L85: excess ≤1.2 pp at the one-sided 95% bound; out-of-schema fields bill no tokens — arx31142 Sec. 4.2.
- L87: opinion 12.1% [8.5, 15.5]; authority 10.1%, "statistically tied" — arx31142 Sec. 4.2; Table 2.
- L88: 87.4%→68.5% — arx31142 Table 3.
- L89: 24.1% pass the 0.8 gate; 38.0% pushed below the gate — arx31142 Sec. 4.4.
- L90: 11% (5/45) shell and 27% (12/45) investment flips on Kev-0.8B — zen22959854 Sec. 5.2.
- L90: 48.4% vs 8.4% on the action gate — zen23038928 Sec. 5.2.
- L94: all nine combinations succeed at least once; 25/27; about $0.50 per success — Check Point blog.
- L95: untrusted marking and anti-injection instructions make no meaningful difference (18→17 of 27) — Check Point blog.
- L96: $0.56 → $4.39 with reasoning; "Jev has no reasoning setting" — Check Point blog.
- L98: "Adversarial content" is listed as failure mode 6 of 9 — docs.typesafe.ai/model-jaggedness/jev-1.13.
- L127: Laya yes/no 76.9% vs 0/1 6.5%, +70.4 [67.6, 73.1], AUC 0.938→0.232 — arx26758 Sec. 4.1; Table 1.
- L128: Open-Jev 19.5% — arx26758 Sec. 4.5; Table 6.
- L129: Jev 32.5%, test-retest ≤1.33% ("24 times"), AUC 0.815→0.581 — arx26758 Sec. 4.5.
- L130: 0% type errors throughout — arx26758 Sec. 4.
- Fig. caption (c): question counts (Open-Jev 1,800; Laya and Jev 1,200) — arx26758 Table 6.
- L132: 1 of 27 papers passes the option-name test — arx32160 Table 6 (T3 applies to all 27). The extracted table is garbled, so this is assigned with moderate confidence.
- L135: ANLI 38.8% of predictions and 51.3% of errors on Neutral — arx38827 Intro. typesafe/jev-1.13-20260917.
- L136: 75.8% for Jev (range 67.2–75.8%); K=2→14 gives 95.9%→54.5% for Jev — arx38827 Secs. 4.1 and 4.3.
- L138: zen22864020: first-introduced entity gets dominant probability (hosted Jev) — abstract. See the hedge, NEW-fidA-30.
- L138: zen23023694: run-to-run variation ≤0.08 on hosted Jev 1.13, while rewording moves answers more — README; main.tex.
- L139: 98.2–99.5% for fine-tuned Laya — arx33689 Sec. VI-C. See the nit, NEW-fidA-31.
- L140: 9.8% vs 13.8% vs 23.5% — arx35865 abstract; Table (l.491–494).
- L143–145: 6,336 pairwise claims, 8 traits, White 51.12% of first picks, 6/8 traits, beauty 80, leadership 76 — Simmons blog.
- L146: counterbalancing not done, so a position effect is possible — Simmons blog (author's own statement).
- L149: 15 eval tasks of 18 (7,977 items); trails the per-task best on 14/15; median −11.6 macro-F1; 44× cheaper — arx24574 abstract; Sec. 4.1.
- L150: better than verbalised confidence of 16/19 LLMs; 0.157 vs 0.066–0.075 — arx24574 Sec. 4.2.
- L151: empathy: 78% of items at ≥0.9 confidence, accuracy 0.383, task accuracy 0.371 (= 185/498, Table 13), ECE 0.538, three balanced classes (166 each) — arx24574 Sec. 4.4; Tables 13 and 22.
- L152: preregistered cascade; a quarter to half of the cost — arx24574 Sec. 3 (AsPredicted #312,511); Sec. 4.5.
- L157: v0.1 (26 Sep, commit 33cc930) did not test Jev; Laya multilingual 28.0% (CS, n=25) / 10.6% (voice); zh-TW 12.8% — README@33cc930.
- L158: v0.2 calls v0.1 "partly a small-sample artifact"; Jev's "shipped calibration is already good on zh voice routing" (n=323) — README@7cd0164. See NEW-fidA-36.
- L159: Chinese-Jev initialised from Laya Multilingual; 69.20 vs 68.35; ECE 3.78 vs 11.45; Legal 60.10 vs 68.35; Finance 64.72 vs 78.39; Medical 87.65 vs 84.29; average ECE 12.08 vs 5.57 — arx36965 Tables 1–2; Sec. 4.
- L160: 0.884 vs 0.780 on Polish — zen23022986 abstract. See NEW-fidA-37 on the English claim.
- L161: all three models degrade on low-resource languages — arx37647 abstract (jev-1.13.0).
- L162: 488 coefficients; lowest of 14 teams by 0.0018 RMSE, untested; raw 2.0731 vs calibrated 1.0645 — arx35293 Secs. 4.2–4.3. See the nit, NEW-fidA-38.
- L165–167: 24 VSM items, 288,000 answers, ICC 0.997, 0.08 (English), 87% / 62%, LTO reversed, lower confidence in Arabic — arx36399 abstract; Fig. 1.
- L168: Sol 0.359 vs 0.639; Jev interaction −0.0197 with a post hoc p0 of 2.2e-09 — arx35286 abstract; Sec. 4; App. B.
- L169: six models; ranking depends on the instrument — zen23055593 abstract (jev-1.13.0).
- L176: compression direction varies by task — arx38827 Sec. 4.1.
- L177: unprompted Jev answers like its American personas — arx36399.

---

## Findings

### NEW-fidA-1 [major]
- Location: sections/04_evidence.tex:21
- Claim in paper: "poor per benchmark (median ECE 0.168, against 0.074 for a constant predictor)"
- Source says: arx29429 Sec. 4.4: "Its median per-benchmark ECE, however, is 0.168 against 0.074 under perfect calibration". Table 15: "Null: ECE when labels are drawn from" the predicted probabilities (a "perfect-calibration null").
- Problem: 0.074 is the ECE that a perfectly calibrated predictor would show through sampling noise alone at these benchmark sizes. It is not the ECE of a constant predictor. The paper's wording changes the meaning: a reader would infer that Jev is worse than a trivial baseline, which the source does not say.
- Suggested fix: "poor per benchmark (median ECE 0.168, against 0.074 expected from sampling noise alone under perfect calibration; 24 of 31 benchmarks exceed that null)"

### NEW-fidA-2 [minor]
- Location: sections/04_evidence.tex:21
- Claim in paper: "and the median F1-optimal threshold is about 0.35, not 0.5."
- Source says: arx29429 Sec. 4.4: "The median F1-optimal threshold of 0.35 (Figure 6(b)) is weaker evidence, because even a calibrated score has its optimum at half the optimal F1 (Lipton et al., 2014), about 0.42 here."
- Problem: the authors explicitly hedge this number. Even a perfectly calibrated score would put its F1-optimal threshold below 0.5 (about 0.42 here). The paper drops that hedge.
- Suggested fix: "...and the median F1-optimal threshold is about 0.35 (the authors call this weaker evidence, since even a calibrated score would be optimal near 0.42 here)."

### NEW-fidA-3 [minor]
- Location: sections/04_evidence.tex:22
- Claim in paper: "Median F1 is 0.706 at the default threshold and 0.822 at a cross-validated one."
- Source says: arx29429 Sec. 4.4: "The gain comes from unvalidated labels (0.678 to 0.853), mostly four rule-scored benchmarks ... On validated labels, t=0.5 is as good (0.721 vs. 0.694), and a threshold fitted on ten labels costs 0.025."
- Problem: under the heading "Thresholds do not transfer", the paper omits that on human-validated labels the default threshold was as good as a fitted one. The headline gain is concentrated in rule-scored benchmarks with unvalidated labels.
- Suggested fix: add "The gain comes mostly from benchmarks with unvalidated (rule- or judge-scored) labels; on human-validated labels the default threshold did as well (0.721 vs 0.694)."

### NEW-fidA-4 [nit]
- Location: sections/04_evidence.tex:15
- Claim in paper: "a question tailored to each benchmark beats the generic one by a median of only +0.006 AUROC out of sample."
- Source says: arx29429 Sec. 4.2: "+0.006 [-0.004, +0.015] AUROC (24/1/11, Wilcoxon p=0.055) ... a small gain whose CI includes zero". The comparator is "the in-sample best of five generic readouts".
- Problem: "beats" overstates an effect whose CI includes zero.
- Suggested fix: "...differs from the generic one by a median of only +0.006 AUROC out of sample (95% CI −0.004 to +0.015)."

### NEW-fidA-5 [nit]
- Location: sections/04_evidence.tex:13
- Claim in paper: "beats supervised baselines on most of them"
- Source says: arx29429 Sec. 4.1: "exceeds the better of response length and an in-domain TF-IDF logistic regression ... wins on 25 of 31 benchmarks".
- Problem: one of the two baselines (response length) is not supervised, and the count should be given.
- Suggested fix: "beats an in-domain TF-IDF classifier and a response-length baseline on 25 of them"

### NEW-fidA-6 [major]
- Location: sections/04_evidence.tex:36 and 59 (polbox)
- Claim in paper: "Another Zenodo study, comparing Laya, \jev{} and a cheap generative model as judgement layers, reports that its cheap judge was near-perfect when an answer was explicitly stated but collapsed when it had to notice that something was \emph{absent} (0.99 versus 0.31) without lowering its self-reported confidence, and that its failures did not complement the generative model's errors" (L36). Also: "and absence is harder to detect than presence~\cite{zen22901853}" (L59, in the G1 recommendation box about Jev).
- Source says: zen22901853 (MANUSCRIPT.md) Sec. 3.6, table: "Laya | 0.3091 | 0.5643 | all FALSE; LLM | 1.0000 | 0.0012". Sec. 6.0 attributes explicit_support 0.9909 to Laya. Abstract box: "The fourth [claim] — that a dissimilar judge supplies incremental coverage — is not supported in any of the three task regimes (the first two regimes are unmeasurable because the LLM is at ceiling; the third lacks power)".
- Problem:
  - The judge that collapsed is the open Laya model, not Jev. "Its cheap judge" in a paragraph about Jev, followed by a recommendation box about Jev, invites misattribution.
  - The generative LLM scored 1.00 on the same "absent" items, so "absence is harder to detect than presence" is not a general finding. It holds for one local typed judge on templated items (n=220 per stratum).
  - "Its failures did not complement" turns "not supported / unmeasurable / underpowered" into a negative finding.
- Suggested fix (L36): "...reports that the open Laya judge was near-perfect when an answer was explicitly stated but collapsed when it had to notice that something was absent (0.99 versus 0.31, n=220 each; the generative judge scored 1.00 on the same items), without lowering its self-reported confidence; the hypothesis that its errors complement the generative model's could not be supported."
- Suggested fix (L59): "...and, for at least one open typed judge, absence was far harder to detect than presence~\cite{zen22901853}."

### NEW-fidA-7 [minor]
- Location: sections/04_evidence.tex:33
- Claim in paper: "while falsely flagging a single benign input; it also made 130 misses at confidence $\geq 0.95$."
- Source says: arx33401 Sec. 5.2: "At values ≥0.95, WAInjectBench false-negative counts are 130 for Jev". Jev's total WAInjectBench misses are 167 (Sec. 6).
- Problem: "also" implies 130 further errors on top of the 130 no-EI misses. The source does not say these are additional. Given the p<0.1 analysis, they very likely largely coincide with the no-EI misses. Readers may double-count.
- Suggested fix: "...while falsely flagging a single benign input; 130 of its 167 misses were made at confidence ≥0.95."

### NEW-fidA-8 [minor]
- Location: sections/04_evidence.tex:40
- Claim in paper: "and decided 1.14 turns earlier than an LLM judge under the same hang-up rule"
- Source says: arx23959 Sec. 5: "on the 36 calls where both hang up it decides 1.14 turns earlier on average [0.55, 1.67] ... at the cost of one fewer detection ... The rule is an illustration: we do not choose an operating point".
- Problem: the paper drops the conditioning (calls where both hang up), the cost (one fewer detection) and the "illustration" hedge. Separately, the gray/legit 38.1% (L41) rests on n=3 scenarios.
- Suggested fix: "...and, on the 36 calls where both systems hung up under an illustrative rule, decided 1.14 turns earlier on average (at the cost of one fewer detection)..."; and "...on ambiguous 'grey' legitimate calls (three scenarios) was 38.1%".

### NEW-fidA-9 [minor]
- Location: sections/04_evidence.tex:46–47
- Claim in paper: "which its author describes as exploratory and not statistically meaningful" / "Their lasting point is architectural: whether an agent stays within its authorised scope is enforced by code around the model, not by the model's judgement."
- Source says:
  - arx28940 abstract: the observations "do not constitute a controlled experiment with statistical power".
  - arx28940 Sec. X-G (Scenario 7): "A Noul question evaluates each discovered asset against the P4 authorization token's scope specification: 'Does this discovered asset ... fall within the authorized scope ...?'"
- Problem:
  - The second paper actually proposes using Jev's judgement for scope checks on discovered assets, on top of the code-enforced token. Attributing to both papers the view that scope is "not [enforced] by the model's judgement" misstates arx28940.
  - Both papers are by the same single author (dos Santos), who also develops NeuroSploit. They are not independent evidence.
  - "Not statistically meaningful" paraphrases "without statistical power".
- Suggested fix: "Two papers by the same author... The second compares one run with and one without a Jev decision layer, which the author describes as exploratory and without statistical power; it also proposes a Jev question for scope checks, layered on a code-enforced capability token. The first paper's point is architectural: ... enforced by code around the model."

### NEW-fidA-10 [major]
- Location: sections/04_evidence.tex:49–50
- Claim in paper: "\paragraph{A guardrail trained for one language loses another.} COGNIT-Guard, a pre-ingestion guardrail that escalates from a CPU classifier to a fine-tuned Laya model on low confidence, reached 98.85\% accuracy with a 0.42\% benign false-positive rate on its own benchmark"
- Source says:
  - arx33671: DUCS-Bench is built from "Chinese statutory consultations"; SafetyBench-ZH is also Chinese. The loss is from formal compliance queries to general safety categories (e.g. Offensiveness 55.33%→46.67%).
  - The 98.85% / 0.42% are from the clean unseen DUCS-Bench split (N=607) for the fine-tuned Laya-322M alone on the NPU path (Table II; Sec. IV-F(1): "Pure compliance fine-tuning ... on Laya-322M (98.85% Acc)").
  - The cascade itself was measured only on the 130-query live slice (99.23%, 0.00% FPR).
- Problem:
  - The heading is factually wrong. Training and test are both Chinese, so the loss is across domains, not languages.
  - The headline accuracy is attributed to the cascade, but it was measured on the fine-tuned model alone.
- Suggested fix: heading "A guardrail specialised for one domain loses general coverage." Text: "...whose fine-tuned Laya-322M reached 98.85% accuracy with a 0.42% benign false-positive rate on the 607-item clean test split of the authors' own Chinese compliance benchmark (untuned: 35.71% FPR). The full cascade was measured only on a 130-query live slice (41.6 ms). Fine-tuning lowered accuracy on the general Chinese SafetyBench-ZH from 60.33% to 56.81%; mixing a 458-item experience-replay set into fine-tuning removed this loss (65.05%)."

### NEW-fidA-11 [minor]
- Location: sections/04_evidence.tex:37
- Claim in paper: "On secure-code review, \jev{} classified 1{,}916 items into 50 weakness classes with lower top-1 accuracy than a frontier model ... repair guided by its diagnosis raised the security pass rate from 0.635 to 0.707 but also broke 89 previously secure samples"
- Source says: arx34963 Sec. III-A: a 50-way CWE classification of CyberSecEval Instruct `origin_code` snippets against benchmark labels. Sec. IV-B: repair of Qwen2.5-Coder-32B outputs, with the pass rate measured by CyberSecEval's Insecure Code Detector; LLM-guided repair reached 0.661 and regressed 79 samples.
- Problem:
  - "Secure-code review" overstates a controlled CWE-labelling task.
  - Without the LLM-guided comparator, the 89 regressions read as a Jev-specific defect, when the LLM-guided repair also broke 79.
- Suggested fix: "On a 50-way CWE classification of 1,916 CyberSecEval snippets, Jev had lower top-1 accuracy than GPT-5.6-Sol (0.458 vs 0.495) but slightly higher top-3/top-5, at 55.9× lower estimated cost. Repair of generated code guided by its diagnosis raised the detector-measured security pass rate from 0.635 to 0.707 (LLM-guided: 0.661) but broke 89 previously secure samples (LLM-guided: 79)."

### NEW-fidA-12 [minor]
- Location: sections/04_evidence.tex:5 (applies to L26, L93–96, L143–145, L23)
- Claim in paper: "Unless stated otherwise, ``\jev{}'' means the hosted \texttt{jev-1.13} model"
- Source says:
  - arx34862 names no Jev version ("1.13" does not occur).
  - The Check Point blog states no version.
  - The Simmons blog says only "typesafe-ai/jev via Vercel AI Gateway" (probabilities rounded to 2 dp by the gateway).
  - The jkf87 replication used "jev-latest" and its README says "논문이 어느 Jev 버전으로 쟀는지 모릅니다".
- Problem: the default convention silently assigns jev-1.13 to results whose sources do not report a version.
- Suggested fix: mark these results "version not reported", e.g. after \cite{arx34862}, \cite{checkpoint2026jev} and \cite{simmons2026saidno} add "(Jev version not reported)". Alternatively, add to L5: "where a source reports no version, we say so".

### NEW-fidA-13 [minor]
- Location: sections/04_evidence.tex:72–73
- Claim in paper: "and raised success on fresh validation calls from 1.8\% to 3.5\%. Successes concentrated on items with small initial decision margins or where the attacker controlled more of the observation."
- Source says: arx28613 Table: "Validated ASR at B = 24 3.5% [0.0, 10.0]%", 9→18 successful cases of 510. Abstract: "Exploratory analysis links these successes to small initial decision margins or greater attacker control".
- Problem: the paper omits the very wide interval and the small absolute count. It also drops the source's "exploratory" hedge on the mechanism.
- Suggested fix: "...from 1.8% to 3.5% (18 of 510 cases; 95% CI 0–10%). In an exploratory analysis, successes concentrated on..."

### NEW-fidA-14 [minor]
- Location: sections/04_evidence.tex:35
- Claim in paper: "In a large cross-task benchmark of 54{,}634 \jev{} decisions, posted on Zenodo, \jev{} had the highest AUROC of the cheap-tier models on all six ... tasks, and tied on the NLI task, at 3--63$\times$ lower cost"
- Source says: zen22885291 Sec. 7 / Table 12: the 54,634 decisions are Jev alone re-run on the complete splits ("54,634 decisions, $0.97"). The head-to-head comparisons use shared samples of 500–600 items per task. "Highest" is a point estimate; Jev is significantly better than Haiku on 3 of 7 tasks and never significantly worse. The cost multiple is 2.9–7.1× vs the GPT cheap tier and 36–63× vs Haiku.
- Problem: the comparative claim is attributed to the 54,634-decision set, which was not used for the comparison. The size of the comparison is overstated.
- Suggested fix: "In a Zenodo benchmark on seven public tasks (500–600 shared items each; Jev alone was also re-run on the full splits, 54,634 decisions), Jev had the highest point-estimate AUROC of the cheap-tier LLMs on all six binary ... tasks, tied Claude Haiku 4.5 on NLI, and was never significantly worse, at 3–63× lower cost."

### NEW-fidA-15 [major]
- Location: sections/04_evidence.tex:90
- Claim in paper: "Two Zenodo studies of the open Kev-0.8B model report the same pattern: the strongest attack flipped 11\% of shell-command and 27\% of investment decisions, and a fixed 0.8 threshold did not hold~\cite{zen22959854}"
- Source says: zen22959854 Sec. 5.2: "flipped 5 of 45 action-gate items (11%, 95% CI 2-24%) and 12 of 45 investment items (27%, 11-44%) ... three attacked wrong answers passed at T = 1 and none as served."
- Problem:
  - "A fixed 0.8 threshold did not hold" is true only at the raw temperature T=1. At the served temperature no attacked wrong answer passed. This reverses the practical conclusion for the deployed configuration.
  - The 11%/27% come from one study (n=45 each, wide CIs), not from "two studies".
- Suggested fix: "A Zenodo study of the open Kev-0.8B model found that the strongest attack flipped 11% (5/45) of shell-command and 27% (12/45) of investment decisions, and that a fixed 0.8 threshold let attacked wrong answers through when the model's raw (T=1) confidence was used, though not at its served temperature~\cite{zen22959854}\zmark{}."

### NEW-fidA-16 [minor]
- Location: sections/04_evidence.tex:90 (last sentence) and 103 (polbox)
- Claim in paper: "In both studies, a threshold set by coverage rather than fixed at 0.8 sent the attacked wrong answers to review." (L90); "and in a multi-question call one such sentence can change several governance flags at once~\cite{zen23038928}" (L103)
- Source says: zen23038928 abstract: "none of the 589 answers a note turned from right to wrong got through" at τ50, but "in 14 attacked requests per temperature, a note agreeing with an existing mistake pushed a harmful command past both the decision and human-review gates". The τ50 gate let 38 (served) / 34 (raw) "boosted mistakes" through (Sec. 5.4). Sec. 6: "All results come from Kev-0.8B, not Jev." The multi-flag effect held in 3 of 4 question×scenario pairs.
- Problem:
  - "The attacked wrong answers" overstates: only answers flipped from right to wrong were all caught. Attacks that reinforced existing mistakes got past both gates.
  - In the polbox, the multi-flag claim directly follows a Jev claim, but it comes from an open 0.8B model.
- Suggested fix (L90): "In both studies, a coverage-based threshold sent every answer the attack flipped from right to wrong to review, although attacks that reinforced an existing mistake could still pass both the decision and review gates."
- Suggested fix (L103): "...and, in an open typed model, one such sentence in a multi-question call changed several governance answers at once~\cite{zen23038928}\zmark{}."

### NEW-fidA-17 [minor]
- Location: sections/04_evidence.tex:87
- Claim in paper: "and 88.8\% of the targeted Choice flips landed on the option the attacker named."
- Source says: arx31142 Sec. 4.2: the 88.8% applies to Choice questions with more than two options, pooled over flips from all five delivered targeted attacks (uniform chance 31.2%).
- Problem: placed straight after the opinion result, the sentence reads as an opinion-attack statistic. It is pooled over five attacks and limited to multi-option Choice questions.
- Suggested fix: "...and, pooled over the five targeted attacks, 88.8% of flips on multi-option Choice questions landed on the option the attacker named (chance: 31.2%)."

### NEW-fidA-18 [minor]
- Location: sections/04_evidence.tex:88
- Claim in paper: "On the human-reviewed subset, accuracy fell from 87.4\% to 68.5\% under the opinion attack."
- Source says: arx31142 Table 3 and text: 124 of the 143 labels equal the model's own five-run answer. The authors say this measures "consistency with largely model-derived labels, not accuracy against independent ground truth".
- Problem: the source's own hedge is dropped, so the number reads as accuracy against independent gold labels.
- Suggested fix: "On a human-reviewed subset whose labels largely match the model's own clean answers, agreement fell from 87.4% to 68.5% under the opinion attack (the authors caution this is not accuracy against independent ground truth)."

### NEW-fidA-19 [minor]
- Location: sections/04_evidence.tex:85 and 103
- Claim in paper: "Rewording the question stayed within re-run noise" (L85); "an unverified observer's opinion ... moved \jev{} as much as an injected command~\cite{arx31142}" (L103)
- Source says:
  - arx31142 Sec. 4.2: the bound covers benign edits (739 of 812 word/spacing edits change only spacing), and the authors "ran no adversarial paraphrase search".
  - The opinion is "statistically tied" with authority impersonation (10.1%), "the strongest injected command". The other commands flipped fewer decisions (8.9%, 8.1%). The commands were spliced into question fields, the stronger attacker tier.
- Problem:
  - "Rewording" may be read as robustness to adversarial paraphrase.
  - "As much as an injected command" generalises from the strongest command. It also omits that the commands needed question-field access while the opinion only needed state access, which is the point that actually strengthens the survey's argument.
- Suggested fix (L85): "Benign rewording of the question (mostly spacing and word edits; no adversarial paraphrase search) stayed within re-run noise..."
- Suggested fix (L103): "...moved Jev about as much as the strongest injected command (12.1% vs 10.1%, statistically tied), even though the command was placed in the question itself~\cite{arx31142}..."

### NEW-fidA-20 [minor]
- Location: sections/04_evidence.tex:79
- Claim in paper: "Three other decision systems, including an open-source \jev{} replica, flipped on 64.9--73.2\% of their correct decisions"
- Source says: arx30243: "OpenSourceJev, an open Jev-style interface built on Qwen3-1.7B Q8". The rates are measured on each system's own initially-correct items (n=285, 328, 328), not on Jev's 508.
- Problem: calling it a "replica" overstates its relation to Jev. The comparison is not on identical items.
- Suggested fix: "Three other decision systems, including an open Jev-style interface built on Qwen3-1.7B, flipped on 64.9–73.2% of their own initially correct decisions"

### NEW-fidA-21 [nit]
- Location: sections/04_evidence.tex:77
- Claim in paper: "short, fluent context additions (median 31 words) that preserve the source, question, choices and correct answer"
- Source says: arx30243 Sec. 3.2: answer preservation was checked automatically by a target-blind Gemma4-12B call. The median of 31 words (IQR 21–54) is over the 312 successful contexts.
- Problem: preservation is a design constraint checked by a model, not a verified property.
- Suggested fix: "...context additions (median 31 words among successful ones), constrained, and automatically checked by a separate model, to preserve the source, question, choices and correct answer"

### NEW-fidA-22 [nit]
- Location: sections/04_evidence.tex:84
- Claim in paper: "applied 9{,}744 single-edit, non-adaptive attacks"
- Source says: arx31142: the 9,744 variants include 2,436 Structure delivery-control variants; 7,308 are delivered attacks across nine attack types.
- Problem: the attack count is inflated by control variants.
- Suggested fix: "applied 9,744 single-edit, non-adaptive variants (7,308 delivered attacks plus delivery controls)"

### NEW-fidA-23 [minor]
- Location: sections/04_evidence.tex:93–94
- Claim in paper: "A Check Point team ran a multi-turn adaptive attack agent against a single \jev{}-based application ... the strongest attacker succeeded in 25 of 27 attempts, typically by the fourth turn"
- Source says: Check Point blog: "three agentic attackers, ten turns each, three independent runs per configuration"; "25 of 27 runs, succeeding on the fourth turn on average"; "This is a focused, directional study, not a benchmark. We used only a single application with a single manipulation objective." "First look" is in the title only.
- Problem:
  - "An attack agent" understates the design (three attackers).
  - "Typically by" changes "on average" into a statement about the typical case.
  - The single manipulation objective is omitted.
- Suggested fix: "A Check Point team ran three multi-turn adaptive attack agents (ten turns, three runs each) against a single Jev-based due-diligence application with one manipulation objective... the strongest attacker succeeded in 25 of 27 runs, on average at the fourth turn..."; and L97: "The authors call the study a focused, directional study of one application, not a benchmark."

### NEW-fidA-24 [nit]
- Location: sections/04_evidence.tex:96
- Claim in paper: "For the generative comparator, turning on reasoning raised the cost..."
- Source says: Check Point blog refers to "Model II" (67% success at $0.56 with reasoning off; 19% at $4.39 with it on).
- Problem:
  - The blog does not explicitly call Model II a generative LLM. Reasoning implies it is one, so this is a minor point.
  - The fall in success rate (67%→19%) is the more informative half of the result and is omitted.
- Suggested fix: "For the comparator model, turning on reasoning cut attack success from 67% to 19% and raised the cost of a successful break from $0.56 to $4.39; Jev has no such setting."

### NEW-fidA-25 [nit]
- Location: sections/04_evidence.tex:129
- Claim in paper: "24 times its test--retest noise of 1.33\%"
- Source says: arx26758 Sec. 4.5: "we run the aligned arm twice on 300 questions. At most 1.33% of the decisions change between the two runs".
- Problem: the floor is an upper bound from a 300-question re-run, while the 32.5% is on 1,200 questions.
- Suggested fix: "...about 24 times its test–retest floor (at most 1.33% of decisions changed between two runs on 300 questions)"

### NEW-fidA-26 [nit]
- Location: sections/04_evidence.tex:127
- Claim in paper: "a systematic inversion that no threshold can repair"
- Source says: arx26758: "AUC below 50% means the ranking is reversed".
- Problem: "No threshold can repair" is the survey's inference, not the source's statement. Strictly, a known inversion could be undone by flipping the score; what fails is detecting it without labels.
- Suggested fix: "a systematic inversion of the ranking (AUC below chance) that a type check cannot detect"

### NEW-fidA-27 [nit]
- Location: sections/04_evidence.tex:114 (Figure caption)
- Claim in paper: "``Von'' is an open 0.4B typed model"
- Source says: "Von" appears only in panel (b), with data from arx30243 Table 1. It does not appear in arx26758, but the description sits in the caption text for (d), which cites arx26758.
- Problem: the gloss is attached to the wrong panel and source, and the 0.4B size was not verified against arx30243 in this round.
- Suggested fix: move the gloss into item (b): "...\cite{arx30243}; 'Von' is an open typed model evaluated in that study..." Confirm its size in arx30243 before stating "0.4B".

### NEW-fidA-28 [minor]
- Location: sections/04_evidence.tex:136
- Claim in paper: "Two random orderings of the same ordinal options agreed on only 74.4\% of items."
- Source says: arx38827 Sec. 4.2 / Table 2: "the two orders produce the same label on only 58.1–59.9% of ordinal items for the KEV models and 74.4% for JEV 1.13". This is on six datasets; nominal-item agreement is ≥95.6%.
- Problem: the scope (six datasets, ordinal items) is dropped, so the number reads as a general order-instability rate.
- Suggested fix: "On six datasets, two random orderings of the same ordinal options agreed on only 74.4% of items (nominal options: ≥95.6%)."

### NEW-fidA-29 [nit]
- Location: sections/04_evidence.tex:136 and 176
- Claim in paper: "the share of the scale used fell from 95.9\% with two levels to 54.5\% with fourteen" (L136); "graded answers are compressed onto fewer levels than the scale offers" (L176)
- Source says: arx38827 Sec. 4.3: "From K=2 to K=14, R falls from 95.9% to 54.5% for JEV 1.13". R is the predicted effective support relative to the gold effective support (gold ≈99.8% at K=2 and 97.0% at K=14).
- Problem: the metric is relative to the gold labels' spread, not to the number of levels offered. The difference is small here because the gold labels are nearly uniform.
- Suggested fix: L136 "...the decisions' effective spread relative to the (near-uniform) gold labels fell from 95.9%..."; L176 "...compressed onto fewer effective levels than the gold labels use..."

### NEW-fidA-30 [minor]
- Location: sections/04_evidence.tex:138
- Claim in paper: "when several entities were equally eligible, \jev{} gave most probability to the one introduced first in the context~\cite{zen22864020}; a perfectly repeatable typed model still moved its decision boundary ...~\cite{zen23065532}"
- Source says:
  - zen22864020: an exploratory, adaptive black-box study on synthetic "machine" items. Results "are not population-level accuracy or calibration measurements"; list order and table order were changed together (Sec. 4.13).
  - zen23065532 abstract: "Laya, an open-source model designed for typed decisions" (41 texts, 492 observations).
- Problem:
  - The first claim drops the source's strong exploratory hedge.
  - The second does not name the model. Placed between two Jev results, it reads as Jev.
- Suggested fix: "...in a small exploratory black-box study, Jev gave most probability to the one introduced first in the context...; a perfectly repeatable open typed model (Laya) still moved its decision boundary..."

### NEW-fidA-31 [nit]
- Location: sections/04_evidence.tex:139
- Claim in paper: "A fine-tuned open model in a network-control study returned its trained answer for 98.2--99.5\% of questions whose meaning had been changed"
- Source says: arx33689 Sec. VI-C / Table V: "fine-tuned Laya returned its known-question answer for 0.982–0.995 of item-seed pairs" on templates that change only the question.
- Problem: the unit (item-seed pairs) and the model (Laya FT) are not stated.
- Suggested fix: "A fine-tuned open model (Laya) in a network-control study returned its trained answer for 98.2–99.5% of item–seed pairs in which only the question's meaning had been changed"

### NEW-fidA-32 [nit]
- Location: sections/04_evidence.tex:144
- Claim in paper: "with an average ``yes'' probability of about 3\%"
- Source says: Simmons blog headline: "3% Typical chance Jev calls a direct racial superiority claim true across 6,720 claims". Per-group mean P(true) on the pairwise claims is 3.16–4.49%.
- Problem: "average" is not quite the blog's "typical"; the group means range up to 4.5%.
- Suggested fix: "with a typical 'yes' probability of about 3% (group means 3.2–4.5%)"

### NEW-fidA-33 [minor]
- Location: sections/04_evidence.tex:150
- Claim in paper: "though worse than three frontier models (median ECE 0.157 versus 0.066--0.075)"
- Source says: arx24574 Sec. 4.2: "The median intervals overlap ... Under equal-mass binning the frontier margin narrows and Sonnet 5 falls slightly behind Jev, while Opus 5 stays ahead under every binning". The frontier ECEs are on verbalised confidence, which some LLMs did not give for all items ("to estimate on 55 percent of items").
- Problem: the source's own robustness hedges are dropped, so the ranking reads as firmer than reported.
- Suggested fix: "...though three frontier models had lower point estimates (median ECE 0.157 versus 0.066–0.075; intervals overlap, and only Opus 5 stays ahead under every binning)."

### NEW-fidA-34 [nit]
- Location: sections/04_evidence.tex:155
- Claim in paper: "TypeSafe states that English is \jev{}'s primary language and that Chinese, Japanese and Korean are ``handled but not equally well''"
- Source says: docs.typesafe.ai/models: "English is the primary training language and where accuracy is currently best." and "Other languages, including CJK scripts, are handled but not equally well; test on your own content before relying on Jev for a non-English workload."
- Problem: the quoted phrase applies to all other languages, with CJK given only as an example. The caveat is narrowed to three named languages.
- Suggested fix: "TypeSafe states that English is Jev's primary training language and that other languages, including CJK scripts, are 'handled but not equally well'~\cite{typesafe_models}."

### NEW-fidA-35 [minor]
- Location: sections/04_evidence.tex:157–158
- Claim in paper: "for the open Laya multilingual model it reported 28\% answer flips when option order was swapped on a 25-item customer-service subset (10.6\% on voice routing) and 12.8\% flips between simplified and traditional script. Its second release (28~September) revised the claim of systematic over-confidence in Chinese as partly a small-sample artefact (over-confidence on one business scenario remained), and reported that hosted \jev{} needed no recalibration on Chinese voice routing."
- Source says:
  - README@33cc930 (v0.1) confirms 28.0% / 10.6% / 12.8% and that Jev was "未测".
  - README@7cd0164 (v0.2) revises the Laya option-order rates to 20.6% (CS, n=34) / 10.8% (voice, n=323) and adds hosted Jev at 2.9% / 1.9% option-order and 1.7% zh-TW flips (n=323 voice).
  - What remains is that Laya's "zh binary-judgment over-confidence outruns the package's correction range". Limitations: "v0.1 business-scenario groups have n=15–25 — wide CIs"; "Single human adjudicator".
- Problem:
  - The paper reports superseded v0.1 Laya numbers while citing v0.2 for other points.
  - It omits v0.2's directly relevant hosted-Jev robustness figures, which are the only Chinese order and script measurements on hosted Jev in the section.
  - "Over-confidence on one business scenario remained" does not match v0.2, which locates the residual over-confidence in Laya's binary judgements.
- Suggested fix: "...for the open Laya multilingual model it reported 28% option-order flips on a 25-item customer-service subset (revised to 20.6% on 34 items in v0.2), 10.6% on voice routing and 12.8% between simplified and traditional script. Its second release revised the claim of systematic over-confidence as partly a small-sample artefact (Laya's over-confidence on binary judgements remained), and found that hosted Jev needed no recalibration on Chinese voice routing and flipped only 1.9% (option order) and 1.7% (script) of voice-routing decisions (n=323)."

### NEW-fidA-36 [nit]
- Location: sections/04_evidence.tex:159
- Claim in paper: "reported 69.20\% accuracy on a general Chinese decision benchmark against 68.35\% for hosted \jev{}"
- Source says: arx36965: the benchmark is CJ-Bench, introduced by the same authors; Chinese-Jev is trained on their 10M-example corpus from the same data pipeline.
- Problem: "a general Chinese decision benchmark" hides that it is the authors' own benchmark, which matters for a +0.85 pp margin.
- Suggested fix: "...on the authors' own general Chinese benchmark (CJ-Bench) against 68.35% for hosted Jev..."

### NEW-fidA-37 [major]
- Location: sections/04_evidence.tex:160
- Claim in paper: "For Polish, a dedicated open model scored 0.884 against \jev{}'s 0.780, while the two were indistinguishable in English~\cite{zen23022986}"
- Source says: zen23022986:
  - "basal-1.0-4.5B reaches 0.884 on held-out Polish decisions against 0.780 for the commercial Jev API". These are 7,081 items from the authors' own generators, which Sec. 20 says "favours our model".
  - English parity holds only on the held-out EN decision set (1,479 items: "0.741 vs 0.736, paired difference +0.005 [-0.020, +0.029]").
  - On the public English JevBench (231 items), Jev scores 0.861 vs basal's 0.740 (Table 23), and the authors say basal is "weaker by design" there.
- Problem: "indistinguishable in English" overgeneralises one in-house English set and omits a contrary public-benchmark result from the same source. The Polish advantage is also on the authors' own generated items.
- Suggested fix: "For Polish decision items generated by its authors, a dedicated open 4.5B model (basal-1.0) reached 0.884 accuracy against Jev's 0.780; on their held-out English set the two were statistically indistinguishable (0.741 vs 0.736), but on the public English JevBench items Jev scored higher (0.861 vs 0.740)~\cite{zen23022986}\zmark{}."

### NEW-fidA-38 [nit]
- Location: sections/04_evidence.tex:162
- Claim in paper: "frozen \jev{} with 488 coefficients fitted on a CPU achieved the lowest aggregate regression error"
- Source says: arx35293: the 488 coefficients cover the whole three-task system (100 Task-1 ridge, 332 Task-2 rerankers, 32 VA maps, 24 fusion), not just the regression task.
- Problem: this implies a 488-parameter regression head.
- Suggested fix: "frozen Jev, adapted with 488 CPU-fitted coefficients across the whole system, achieved..."

### NEW-fidA-39 [nit]
- Location: sections/04_evidence.tex:168
- Claim in paper: "while \jev{}'s interaction was small (0.020 in absolute value) but, on post hoc tests, not zero"
- Source says: arx35286: Jev's panel "uses a different rubric, normalised to 0-1, and cannot establish an impartiality ranking against chat systems"; "Jev's small observed interactions therefore do not establish superior debiasing"; p-values are "explicitly unregistered" and conditional.
- Problem: set beside the chat models' 0.28 interaction, the sentence invites a comparison the author explicitly disclaims.
- Suggested fix: append "(Jev was scored on a different rubric, so the author cautions against comparing its magnitude with the chat models')".

### NEW-fidA-40 [nit]
- Location: sections/04_evidence.tex:169
- Claim in paper: "An audit of six models including \jev{} on a politically sensitive question found that model rankings depended on whether claims, choices or labels were used as the instrument"
- Source says: zen23055593 (preprint draft 0.7): the swap is chiefly between Jev and Claude Sonnet 5 ("Jev and Claude Sonnet 5 thus trade places"). An addendum finds the label-side result "specific to Claude Sonnet 5": Sonnet 5.5 did not reproduce it, and Jev was not re-run.
- Problem: the generalisation to "model rankings" loses the addendum's qualification.
- Suggested fix: "...found that Jev and Claude Sonnet 5 swapped places depending on whether claims, choices or labels were used as the instrument (an addendum found the label-side result did not recur in Claude Sonnet 5.5)~\cite{zen23055593}\zmark{}."

---

## Summary

Of the roughly 110 quantitative and attributive claims checked in G1–G3, most numbers are transcribed correctly. The fidelity problems lie in the attribution and scope of claims.

There are five major issues:
1. **NEW-fidA-1:** the Just Ask Jev comparator ECE 0.074 is described as a "constant predictor" when it is a perfect-calibration null.
2. **NEW-fidA-6:** the Zenodo "absence vs presence" collapse (0.99 vs 0.31) belongs to the open Laya model, not Jev. The generative judge scored 1.00 on the same items. The finding is nevertheless used in the G1 recommendation box as a general property of typed valves.
3. **NEW-fidA-10:** the COGNIT-Guard paragraph heading ("trained for one language loses another") is wrong, since both benchmarks are Chinese. Its headline 98.85%/0.42% belongs to the fine-tuned model alone, not the cascade.
4. **NEW-fidA-15:** "a fixed 0.8 threshold did not hold" for Kev-0.8B is true only at the raw temperature. At the served temperature no attacked wrong answer passed.
5. **NEW-fidA-37:** "indistinguishable in English" for basal-1.0 omits that Jev was clearly better on the public English JevBench (0.861 vs 0.740).

The minor findings mostly restore dropped hedges or conditions:
- the 0.35 threshold being "weaker evidence"; the default threshold being as good on validated labels;
- the CI of 0–10% on adaptive injection success;
- conditioning on calls where both systems hung up for the 1.14-turn gain;
- largely model-derived "human-reviewed" labels;
- 88.8% pooled across attacks;
- order agreement limited to six datasets.

Others name models that open-weight or unversioned sources actually used: Kev-0.8B in the G2 policy box, Laya in zen23065532, an "open-source Jev replica" that is a Qwen3-1.7B Jev-style interface, and hosted-Jev results whose version is unreported (arx34862, Check Point, Simmons). The zh-decision-bench paragraph cites superseded v0.1 Laya numbers and omits v0.2's hosted-Jev Chinese robustness results.

Coverage is 40 findings: 5 major, 19 minor, 16 nit. Two items remain uncertain:
- The "1 of 27" option-name count in arx32160 is verified only with moderate confidence because the extracted table is garbled.
- The "0.4B" size given for "Von" in the figure caption was not confirmed.
