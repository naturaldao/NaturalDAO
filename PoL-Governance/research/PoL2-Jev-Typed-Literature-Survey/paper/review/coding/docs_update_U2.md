# Update search 2026-10-08: group U2 document notes (primary coder)

All eight are arXiv, post-window, read in full from `scratchpad/update/arx<ID>.txt`. Tiers: coded 6, context 2, non-empirical 0.

## arx03935: JEVal, general decision models (Duan et al.). Tier: coded (G1 S, G4 Q, G7 Q)
- **Tested:** 25 configurations on 11,257 bilingual items (1,800 Chinese), plus probability-estimation probes, tau-bench, and social simulation (SocioBench, user profiling, ElectionSim).
- **G4:** Jev ECE 0.0532, below every generative LLM (Table 1). But on analytic distributions it puts 89.35% on the mode vs 35.60% true, the worst of all configurations. This qualifies the answer box (calibration is local; distributions are compressed onto the top choice) and confirms its direction.
- **G7:** confirms "simulated publics lean towards one population". Individual prediction matches LLMs (37.69% vs 37.90%) at 0.50 s vs 174 s. InnerJev voters call 47/51 states but with 2x vote-share MAE (6.52 vs 3.06) and a pro-Harris bias (+3.73).
- **G1 (thin):** AgentHarm, N=97, 84.54% vs 61.86-85.57%; confirms.
- **Flags:**
  - Emotion recognition (T1): GoEmotions accuracy 31.0%, ECE 0.306 (generative 23.0-37.0%, ECE 0.324-0.605).
  - Chinese-language data: C-Eval 84.5%, CMMLU 89.0%.
  - Group fairness: BBQ 98.0%. Not coded for G3, since it is not a primary analysis.
- **Not coded:** tau-bench, where Jev action selection lowers pass rate from 77.6% to 66.1% (Table 3; the text says 64.2%). No confidence gate is involved, so it is not G6. It could be read as composed decisions degrading (cf. G5/G6); for adjudication.

## arx04345: wireless System-One evaluation (Rahimi et al.). Tier: context
- **Tested:** hosted Jev vs GPT-Sol and Qwen on 30 antenna-selection and 30 RAN-slicing instances.
- **Results:** antenna capacity loss 20.19% vs 0.00% (GPT-Sol) and 17.33% (Qwen), at 1.52 s vs 12.86 s / 3.62 s. Slicing regret 0.131 vs 0.134-0.145.
- **Why not coded:** capability and latency only, with no calibration, escalation, detection or fairness measured.

## arx04985: security, privacy and dual use of Jev (Wang et al.). Tier: coded (G1 Q, G2 N, G7 N)
- **G2:** confirms "Yes" and the most negative reading. Jev-specific injection and a universal suffix reach 97-100% ASR on hosted Jev; poisoning implants NanoJev backdoors at up to 100% ASR.
- **G1:** confirms "ranking, not decision". AUROC 0.95-1.0 on prompt-injection, jailbreak, harmful-content and AI-text benchmarks. A fitted threshold is needed (AI-text accuracy 78% to 89%); NanoJev is near chance.
  - Flag: harmful-content detection on JailbreakBench and HarmBench, which is moderation-relevant.
- **G7 (judgment call, please adjudicate):** I coded privacy leakage and dual use as a deployment condition.
  - Labels alone leak gender, age, heart disease and ethnicity at 100%.
  - Jev refines harmful plans (2.3 to 4.5) and supports model extraction (49% to 92%).
  - Attribute inference is also an input-steering attack, so the second coder may place it under G2 only.
  - This would add a negative to G7 (currently S 5, Q 12, N 2). It qualifies the box (privacy is not addressed there) but does not reverse its direction.

## arx05107: SearchJev (Cao et al., Huawei; author-built). Tier: coded (G4 Q, G6 Q)
- **G4:** qualifies.
  - In distribution, ECE is 41-74% below same-size autoregressive Qwen, and Jev 1.13 has the lowest mean ECE.
  - Out of distribution, calibration does not transfer (SearchJev-4B rewriting ECE 26.9, verification 15.4).
  - Abstention-related: the evidence-sufficiency ("insufficient") decision is 96.0% for SearchJev-4B vs 79.8% for Jev, in distribution.
- **G6:** confirms "escalate to a stronger reasoner saves cost". Accuracy is 46-54% vs 45%, at roughly a quarter of the time. However, the gate threshold is unrecoverable and no delegated short-decision calls were logged; n=100, single run.
- **Flag:** Chinese-language data (63.7% of training rows are mainly Chinese; Chinese OOD sets such as CANDY).

## arx06354: GraphDecide (Yang et al.). Tier: context
- **Tested:** graph cognition, graph-text input and sequential optimization with 14 configurations.
- **Results:** Jev adjacency 100% but degree 67.8% and articulation 61.2%; direct TSP gap 59.66%.
- **Why not coded:** this is capability, not G1-G7. Input-form contrasts are not option-name, order or language fairness.
- **Possible G4 signal for adjudication:** 1,186 of 6,684 Jev probability vectors and 287 of 1,000 ogbn-arxiv test vectors did not sum to one.

## arx06425: SoK, semantic decision engines in network control loops (Li et al.). Tier: coded (G4 Q, G5 Q)
- **G4:** confirms "'none' is chosen inconsistently". The no-valid-candidate escalation succeeds for 45/48 contracts but only 4/120 infeasible routes, where three of four LLMs escalate more often (49-109/120).
- **G5:** confirms "writing intermediate facts/steps makes chains inspectable and more accurate". A public gate that moves feasibility checks to the controller raises Jev from 29 to 84/120, but this is a bundled intervention and the shared-quota gains are smaller. The audit also finds 4/50 loop claims supported and 9/139 families separating the three gates.
- **Load:** Jev rho 1.084 at 16 arrivals/s. Not coded.

## arx06625: JEV vs LLMs on seven political-science replications (Denney and DiGiuseppe). Tier: coded (G3 Q, G4 Q, G7 Q)
- **G4:** confirms "better than generative stated/token confidence, mixed against others". It beats GPT-6 Luna's token probabilities on 8/8 tasks when asked once (V-Dem 0.057 vs 0.390), but Qwen3.8-27B is better on the pairwise tasks, and the Luna gap vanishes when probabilities are averaged over both orders.
- **G7:** confirms the vendor-dependence and cost points, and qualifies the cost claim. Accuracy is on par, Jev is faster, it is not cheaper than Luna at batch prices, and its architecture is undisclosed.
- **G3:** confirms order dependence. Pairwise flip rate 8.8%, concentrated at low confidence; the effect on the scale is small (r 0.982).
- **Notes:**
  - The tweets are about content moderation (relevance and framing), not moderation decisions; no hate-speech task.
  - In Le Mens and Gallego, the "NA" reply was replaced by a separate yes/no relevance question at 0.5. This is related to abstention but not evaluated as such.

## arx06744: ufakzeka-karar, open Turkish typed model (Teke; author-built). Tier: coded (G1 Q, G3 S, G4 Q)
- **G3:** S by construction. Order sensitivity is 0.000, and paraphrase agreement 0.883 vs Jev 0.926. This confirms that "option rotation/neutral construction removes much order dependence". It is Turkish-only: the English Brier gap is -0.303, which I did not count as a fairness failure.
- **G4:** confirms "calibration is local". Temperature scaling worsens held-out ECE, and the 'not sure' (abstention) signal misses guardrail errors (12.2% wrong at >=0.99).
- **G1:** qualifies. Attack recall is 194/217, but only 128/201 harmless look-alikes pass, and the numbers were shaped by reading test results.
- **Flags:**
  - Hate speech / toxicity: Turkish offensive-language moderation (OffensEval-TR, supervised accuracy 0.844; HakemBench moderation 150/157 caught).
  - Abstention: the 'not sure' signal described above.
  - No Chinese-language data.

## Direction changes
None of the eight reverses an answer box. The closest are:
1. arx04985 adds strong privacy and dual-use negatives under G7, if adjudication keeps that axis.
2. arx03935 and arx06744 sharpen G4 toward "calibrated on average, but distributions are compressed and abstention signals miss errors".
