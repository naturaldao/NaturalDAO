# Adjudication of update-search disagreements (third coder)

Date: 2026-10-08. Binding rules: `paper/review/CODEBOOK_v3.md` (including rule (iv)) and `tab:clauses` in `paper/sections/03_method.tex`.
Inputs: `adjudication_list.csv` (21 doc-axis pairs), first-coder rationales in `coding_update_{U1..U4,Z1,Z2}.csv`, second-coder rationales in `second_coder_update_B{1,2,3}.csv`, and the full texts in the session scratchpad (`update/arx2610.*.txt`, `update/zen*.txt`).

Result: 11 decisions agree with the first coder, 10 with the second, 0 with neither. Six decisions are S and three are N (corrected in round 12; the count of five was a typo).

## Decisions

| doc | axis | first | second | decision | comparator | reason (decisive number / locator) |
|---|---|---|---|---|---|---|
| arx03073 | G4 | Q | S | **Q** | none | Security-test ECE is low (1.53-2.18% raw, Table 9), but only after security fine-tuning. Calibration does not hold outside that domain: 0.8B general-transfer ECE is 21.10% against 4.19% for the initialisation (App. H, Table 27). Temperature scaling also raises test ECE (to 2.48-3.56%, Sec. 6.3). |
| arx03324 | G7 | Q | S | **S** | better | On HateCheck, Jev costs $0.033 per 1K texts at 336 ms, against $0.120/844 ms (Luna) and $1.177/1,426 ms (Sol), at 1.6 macro-F1 below Sol with no task training (Sec. 4.4, Fig. 5, Table 9). "Validate on own-policy sample" and "confirm on everyday traffic" are deployment caveats (Sec. 6). The result did not need them. |
| arx03387 | G6 | N | Q | **Q** | none | Source-calibrated gates exceed 5% false rejection in 6 of 12 transfers for Jev and Laya, and 69.3% for DBpedia→Emotion (Sec. 3.1, Fig. 2). They work only after target recalibration (82.5%/3.3%). Cross-task transfer is not a rule-(iv) test, so this is success that depends on an added condition. |
| arx03935 | G1 | S | Q | **S** | similar | The detection-relevant primary result is AgentHarm harmfulness: Jev 84.54% against 61.86-85.57% for the nine generative configurations (level with Qwen3.8-27B thinking, 1 point below the best), with no added condition (App. D.6, Tables 25-27). The second coder's overall JEVal accuracy is general capability, not G1. |
| arx05107 | G6 | Q | S | **Q** | better | Gated agents beat System-2-only (46.0/54.0% vs 45.0%, Table 4). However, they record 0 System-2 decision calls and δ cannot be recovered (Table 8, App. D.3), so escalation is not shown to work. The larger gain needs a search-trained, temperature-calibrated model; untuned Jev reaches 46.0%. |
| arx06625 | G3 | Q | S | **Q** | none | Order swap is the rule-(iv) test. The winner flips in 8.8%/8.5% of pairs, with position bias -0.0358 (App. B, Table 3), while the aggregate scale holds (r = 0.982). No generative order comparator exists ("we do not compare magnitudes") and no criterion is stated. The 95.95-99.06% range is for transitivity (coherence), not order stability. |
| arx06744 | G1 | Q | N | **N** | worse | Decision quality (macro F1 0.705) is below Jev 1.13 (0.851) and below every generative model on the board (0.741-0.901), and only 128/201 harmless guardrail look-alikes pass (Sec. 6, Table 2). The positive moderation counts are flagged as test-shaped and possibly style-inflated (Sec. 4), so they cannot offset this. |
| arx06744 | G4 | Q | N | **Q** | mixed | The guardrail track fails: smooth ECE 0.158, and 18 of 148 answers at confidence ≥0.99 are wrong. The other six tracks have ECE 0.025-0.084 with no errors at ≥0.99 (Sec. 5). The board calibration score of 0.482 sits inside the generative range (0.386-0.806, Table 2). This is mixed across sub-types; the paper says calibration "does not transfer everywhere". |
| arx07177 | G3 | Q | S | **S** | better | CLM's order-flip rate is 0.0002 (3 exact ties) against 0.2188 for the generative judge, and its length shift is -0.023 against -0.217; both differences are significant (Sec. 4, "Order and length stability"). Laya (0.4395, inputs truncated) is a secondary baseline. Near-chance accuracy is a G1 matter. |
| arx07716 | G3 | N | Q | **Q** | better | Some rule-(iv) tests fail: wording swings Open-Jev-2B by 26 points (0.454-0.714), and label-first on a small self-selected menu costs 19.6 points (Sec. 4.4, 5.4). Others pass: menu shuffling moves results ≤0.6 points, flips stay under 6% at 150 labels, and menu interventions are predicted within 4.2 points vs 1.6-15.8 for generative models. Both are primary, so the tie-break gives Q. |
| arx09188 | G3 | Q | S | **S** | better | Same answer in both presentation orders for 94.8% vs 90.6% (Qwen3-32B) of 500 TREC pairs, and 86.7% vs 72.0% of 80,000 MS MARCO pairs (App. N). The Othello coordinate-list rendering (14.4→24.3%, App. K) checks a strategic error that all judges share (Qwen 17.7%, OLMo 15.3%). It is not a stability failure. |
| arx09188 | G7 | Q | S | **Q** | mixed | Labelling is cheap ($1.97 vs 1.91 GPU-h; 21 min vs 5.1 GPU-h), but downstream quality at scale is mixed across tasks. The reranker matches (0.637 vs 0.630). The chess gain is +2.8 [-5.5, 11.0] vs +16.7 for Qwen. Jev-trained scores weaken Othello (-619.4 Elo) and Connect-4 (-157.7) (Sec. 5.1, 6, App. G). |
| arx09683 | G3 | Q | N | **N** | mixed | Under the rule-(iv) order shuffle, accuracy falls for most zero-shot typed models: Strands 0.59→0.38, Kev 9B 0.60→0.50, Laya 0.56→0.49, Kev 4B weapons 0.97→0.62. All of them over-choose "collect" at 1.6-1.8× chance in either order, a systematic bias (Sec. 5.1, Table 1). Insensitivity appears only in Clef-Flash and in task-trained models. Qwen without reasoning shares the bias (1.8); with reasoning it is lower (1.4). |
| arx09896 | G4 | Q | S | **Q** | better | Chip's ECE of 0.0032 needs fine-tuning on 88,604 target-task records. It does not transfer: JevBench ECE is 0.1633 (Original) and 0.3577 (Hard) (Tables 3-4). Hosted JEV (0.0271) beats the flagships (0.0307-0.0607), but the headline model's calibration is domain-restricted. |
| arx09896 | G7 | Q | S | **Q** | mixed | Typed models are much faster (118 ms Chip, 1,510 ms JEV, vs 4,631-16,009 ms flagships, Table 6). However, untuned JEV fails 678 of 5,000 records and reaches 84.52% FFD exact match vs 98.32-99.12% for the flagships (Table 3). Chip's 99.32% needs task training. |
| arx09937 | G7 | Q | S | **Q** | mixed | Jev costs US$18.69 for 190,582 requests at 0.19 s each, against about 2 s for local Qwen2.5 72B, which has no per-query cost and keeps data on site; "both are fast enough" (Sec. 4.7). The abstract says the probabilities "still needed correction" and detection was weak, so use requires recalibration and an operator. |
| zen22941164 | G4 | Q | S | **S** | none | WEV ECE is ≤0.06 on browser steps and ≤0.10 on out-of-domain transfer-v4 with no temperature fitting (Table 7, Sec. 5.4). A DONE threshold trades premature stops for recall as intended (8.5%→3.8%). BLOCKED recall of 3% (n = 29, Sec. 5.7) is a rare-class recognition miss for CAPTCHA/login pages (G1), not epistemic abstention. |
| zen23005202 | G1 | Q | S | **S** | similar | Mean accuracy over five public benchmarks is 83.6 (Jev) and 84.2 (Reflex-1) vs 85.6/84.8 (GPT-5.6/Gemini 3.8), "no training needed" (README Results). That is within 2 points with no added condition. The first coder's reasons (one run, no per-benchmark tables) are quality fields, not code. |
| zen23050542 | G1 | Q | S | **Q** | none | Discrimination beats TITAN-SR (median AUC 0.9827 vs 0.9760; S@95R 0.9339 vs 0.8970). However, the untuned 0.3 threshold gives pooled recall 0.9349 (50 FN) and reaches ≥99% recall in only 16 of 22 reviews (report.md primary analysis). G1 asks for thresholds that hold in deployment, so the result is mixed across reviews. |
| zen23088660 | G4 | Q | S | **Q** | none | Every band is underconfident, e.g. the 0.60-0.70 band is right 74.5-82.6% of the time and the 0.80-0.90 band 93.1-96.6% (slide 9). The probability is conservative, not calibrated. The study supports thresholding only and adds "on new data, check it the same way first". |
| zen23221456 | G4 | Q | N | **N** | worse | In its own games Jev's chosen-move probability is 0.72 while 51% of moves are optimal (ECE 0.21). Its Brier score of 0.283 is worse than a constant predictor (0.250); Laya and GLiClass are also worse than a constant. Only generative Qwen3.5-4B beats the constant (0.232 vs 0.249) (Sec. 5.7, Fig. 6). Exam ECE of 0.06 is a secondary single-decision check. |

## Boundary rules applied

1. **What counts as an added condition.** An added condition is something the study had to introduce for the typed model to reach the reported result. Examples: target/local threshold fitting or recalibration, temperature scaling, fine-tuning on the target task, restriction to the training domain or language (the result fails outside it), human or operator review.
   - Deployment advice the measured result did not need is not an added condition. Examples are "validate on your own policy sample" and "confirm on everyday traffic" (arx03324).
   - Evidence-quality limits are recorded in the quality fields, never in the code. Examples are a single run, no intervals, an author-built system and non-blind development (zen23005202, arx03935).
2. **Specialised (fine-tuned) typed models.** In-domain success after target-domain training supports S only if it also holds outside the training domain without correction (zen22941164: ECE ≤0.10 on transfer-v4). If it degrades out of domain, the result is domain-restricted and coded Q (arx03073, arx09896 G4/G7). A clean result from an untuned secondary typed model does not override the headline model's result.
3. **Comparator level.** "Similar" means a difference of about 2 points or less with no significant deficit reported, and counts as at least comparator level (arx03935, zen23005202). "Clearly worse" means below all or nearly all generative comparators on the axis's headline metric, or below a trivial baseline (Brier worse than a constant). Clearly worse is N when the positive findings are secondary or depend on added conditions (arx06744 G1, zen23221456).
4. **No comparator.** S requires that the study states a criterion, or reaches an unhedged conclusion, that the function is met. Partial instability under a test (arx06625), conservative miscalibration (zen23088660), or a fixed threshold that holds only in some sub-sets (zen23050542) is Q.
5. **Rule (iv).** Order, wording and rendering perturbations (G3), adversarial content (G2) and adversarially selected items (G6) are the test, not added conditions.
   - When failures under the test are the dominant primary result, the code is N. Example: systematic bias and order sensitivity across most typed models (arx09683).
   - When primary configurations both pass and fail, the tie-break gives Q (arx07716).
   - Cross-task threshold transfer is not a rule-(iv) test. A gate that works only after target recalibration is Q, not N (arx03387).
6. **What is primary.** The primary result is the study's own typed model and its headline analysis for the axis.
   - Baseline typed models are secondary: laya in arx07177. So are supporting diagnostics: exam ECE in zen23221456, the Othello rendering check in arx09188.
   - In multi-benchmark papers, the G1 result is the detection-relevant sub-benchmark (AgentHarm in arx03935), not overall general-knowledge accuracy.
   - A label that recognises an environment state (BLOCKED) is detection, not G4 abstention.
7. **G7 (public scale).** A cost or latency advantage is S only if output quality at scale is at comparator level without added conditions (arx03324). It is Q if downstream quality is mixed across tasks (arx09188), if quality or validity is materially worse for the untuned model (arx09896), or if use requires recalibration or an operator, or trades data locality (arx09937).
8. **G6 (oversight).** End-to-end gains of a gated system are not evidence that escalation works when the logs show no escalation calls and the gate threshold cannot be recovered. Such a result cannot be S (arx05107).

## RESOLVED (paste into scripts/merge_update.py)

```python
RESOLVED = {
    ("arx03073", "G4"): ("Q", "none", "Low in-domain ECE after security fine-tuning; general-transfer ECE 21.10% vs 4.19% init (App. H)"),
    ("arx03324", "G7"): ("S", "better", "$0.033/1K, 336 ms vs $0.120-1.177, 844-1426 ms; 1.6 F1 below Sol, no training"),
    ("arx03387", "G6"): ("Q", "none", "Gate thresholds fail 6/12 transfers; restored only by target recalibration (Sec. 3.1)"),
    ("arx03935", "G1"): ("S", "similar", "AgentHarm 84.54% vs 61.86-85.57% generative; level with best, no added condition"),
    ("arx05107", "G6"): ("Q", "better", "Agents beat System-2-only but zero escalation calls logged, delta unrecoverable (Table 8)"),
    ("arx06625", "G3"): ("Q", "none", "Order swap flips 8.8% of winners, bias -0.036; scale r=0.982; no comparator or criterion"),
    ("arx06744", "G1"): ("N", "worse", "Macro F1 0.705 below all generative (0.741-0.901); passes 128/201 harmless look-alikes"),
    ("arx06744", "G4"): ("Q", "mixed", "Guardrail ECE 0.158, 12.2% wrong at >=0.99; other tracks 0.025-0.084"),
    ("arx07177", "G3"): ("S", "better", "Order-flip 0.0002 vs 0.2188 generative; length shift -0.023 vs -0.217"),
    ("arx07716", "G3"): ("Q", "better", "Wording swings 26 pts, label-first -19.6 pts; shuffle <=0.6 pts, menu predictable"),
    ("arx09188", "G3"): ("S", "better", "Both-order agreement 94.8% vs 90.6% (TREC), 86.7% vs 72.0% (MS MARCO)"),
    ("arx09188", "G7"): ("Q", "mixed", "Cheap labels; reranker matches but chess +2.8 vs +16.7, Othello/Connect-4 weakened"),
    ("arx09683", "G3"): ("N", "mixed", "Shuffle cuts accuracy for most typed models; collect bias 1.6-1.8x chance either order"),
    ("arx09896", "G4"): ("Q", "better", "Chip ECE 0.0032 needs target fine-tuning; JevBench ECE 0.163/0.358"),
    ("arx09896", "G7"): ("Q", "mixed", "Faster, but JEV 678/5000 failures, 84.52% FFD; Chip needs task training"),
    ("arx09937", "G7"): ("Q", "mixed", "0.19 s, $18.69 vs local 72B 2 s, data on site; needs recalibration and operator"),
    ("zen22941164", "G4"): ("S", "none", "ECE <=0.06 in-domain, <=0.10 out of domain, no recalibration; DONE threshold works"),
    ("zen23005202", "G1"): ("S", "similar", "Mean 83.6/84.2 vs 85.6/84.8 frontier LLMs on five benchmarks, no training"),
    ("zen23050542", "G1"): ("Q", "none", "AUC 0.9827 > TITAN-SR, but untuned threshold >=99% recall in 16/22 reviews only"),
    ("zen23088660", "G4"): ("Q", "none", "Every band underconfident (0.60-0.70 band right 74.5-82.6%); conservative, not calibrated"),
    ("zen23221456", "G4"): ("N", "worse", "ECE 0.21, Brier 0.283 worse than constant; only generative Qwen beats constant"),
}
```
