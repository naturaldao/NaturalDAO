# Update coding, group Z1 (Zenodo, dated within the main window, re-screened)

Primary coder: AI coder Z1, 2026-10-08. Brief: `update_coder_brief.md`. Every record was dated on or before 1 October 2026 but was missing from the 1 October inclusion list, so all rows carry `set = re-screened`. Per the consistency rule, a record with no evaluation (measurement) of a typed model would be `excluded-no-evaluation`. None of the 15 records met that condition. Two are tiered **context** because their only measurements do not bear on G1–G7.

Tiers: coded 13, context 2 (zen22921974, zen22979052), non-empirical 0, excluded-no-evaluation 0.

---

**zen22886178 — ExoNotes (Arce Alfaro). Coded: G3 Q.**
Hosted jev-1.13.0 turns TESS observer notes into features for a CatBoost predictor. Its probabilities are never thresholded. The preregistered headline is ΔAUC +0.0432 [+0.0324, +0.0547]. Paraphrase stability: all 7 predictive TESS features pass, but 2 label-echo features fail, and 3 of 6 Kepler features fail ρ (0.841, 0.828, 0.651). The paraphrase effect is 4.4× the re-ask noise, and jev-1.13.0 is not bit-stable (mean |Δ| ≈ 0.005 between identical requests). **Qualifies → confirms G3 "not by default"**: wording moves answers, more on new data.

**zen22904595 — Plan Once, Ground Locally (Shukla). Coded: G6 Q.**
Zero-shot Laya grounds plan steps with confidence thresholds, falling back to lexical matching and then an LLM replan. Plan-and-execute matches budget-matched ReAct (88.8% vs 92.0%) at about 1/6 of the tokens. Laya is not significantly better than word overlap (+2.3 pp [−0.2, +5.0]). It declines (chooses "none") on 46 of 277 grounding decisions, and its verification check never fired. **Confirms G6 "depends"**: the cascade saves cost, but the typed component adds little. Abstention: the "none" option was used and costs a replan.

**zen22921974 — daf-jev toolkit (Friedman). Context.**
A Python toolkit with live jev-latest benchmarks: batching speedup 3.98–18.55×; pipeline p50 0.129–0.133 s; "calibration" ECE 0.073 and Brier 0.0252, scored against the model's own modal answer over 6 states × 5 repeats; Noul repeat gap 0.005. There is no ground truth, so nothing bears on G4. The repeat stability is too thin (6 states) to code for G3. Measurements exist, so this is not excluded-no-evaluation.

**zen22933883 — Audio-Laya (Nammungkun). Coded: G1 Q.**
Spam/robocall detection. Laya on ASR transcripts scores Macro F1 89.2% and AUROC 94.9%. The author's direct-audio adaptation scores 99.6–100%, but labels are fully confounded with corpus. Zero-shot transfer fails: MInDS-14 accuracy is 6.2–8.5% against an 8.5% majority baseline. **Confirms G1 "not yet as a decision"**: the scores do not transfer. Audio only, English.

**zen22935043 — Calibration audit of Jev (Meng). Coded: G1 Q, G4 Q, G6 Q.**
- G1: Jev is more accurate than gpt-5.4-nano and gpt-4.1-nano and than an untrained NLI checkpoint, but less accurate than a task-exposed one on AG News (−2.30). Label wording alone moved the gap by about 40%.
- G4: ECE depends on question form. SST-2 yes/no 0.091 vs choice 0.020 (difference 0.071 [0.047, 0.086]). On AG News the mid-scale is overconfident (0.750 stated vs 0.612 observed). One temperature fixes most of it.
- G6: a 5% auto tier certifies in 0 of 2,000 AG News splits, and conformal singletons err 5.93% at a nominal 5%.

**Confirms G4 "partly / calibration is local"** and qualifies G6. Three-valued/abstention: 1.5% of conformal sets on the binary task are empty and need a fallback.

**zen22941164 — wev (Huang, Ren). Coded: G4 Q.**
Open typed models (Qwen3 1.7B/4B/8B) distilled from an LLM browser agent. The authors' WEV-4b gets 75.9% step success on unseen sites, against 0.0–21.2% for Laya and Kev. Calibration is good: ECE ≤ 0.059 on browser steps and ≤ 0.099 out of domain. **The "give up" option BLOCKED is recalled on 3% of 29 steps**, a three-valued/abstention item that confirms G4's "an explicit 'I don't know' is rarely chosen when correct". End to end the student matches its teacher (30 or 28 vs 27 of 153 tasks). Authors are Chinese, but all data are English.

**zen22945279 — jev-laya-classification-bench (Kinge). Coded: G1 Q, G3 S, G4 Q, G6 Q.**
12,000 federal IT solicitations; 741 rows with quote gold.
- G1: on primary class Jev 91.9% beats Qwen3.5-35B (89.6%) and Laya (78.0%). On fulfillment mode Jev 65.0% trails Qwen 71.0%.
- G3: nine question-structure × input variants all fall within 0.912–0.919.
- G4: Jev ECE 0.049 on primary class (fulfillment 0.125); Laya ECE 0.322.
- G6: at a 0.94 cutoff Jev accepts 86.5% of rows at 96.7% precision; Qwen and Laya never reach 95%. The cutoff was fitted in-sample.

**Confirms G4 and G6 as they stand.** The G3 S is narrow: question structure only, not names or definitions, so it does not move the box. Abstention: Jev's `text_insufficient` flag fires on 12.7% of rows and Laya's on 76.3%; neither is validated against gold.

**zen22979052 — Sev Arabic Preview v0.1 (Asiri). Context (borderline, flagged by the screener).**
An open Arabic typed model (mmBERT + typed head) released as a model, not a study. Its only figure is a dev-split result, 94.53% mean accuracy over 3 seeds with ECE ≈ 0.0053 after temperature calibration, which the author says is "not an external benchmark". No method, test set or comparison is given, and no Saudi/Gulf, OOD or code-switch evaluation was done. A measurement exists, so it is not tiered excluded-no-evaluation. It is too thin to code for G4. The author may instead treat it as a 1 October-style "tool without evaluation" exclusion; both readings leave the tallies unchanged. Non-English (Arabic).

**zen23005202 — Reflex-1 (Suzuki). Coded: G1 Q.**
Mean accuracy over 5 benchmarks: hosted Jev 83.6 and the author's Reflex-1 84.2, against GPT-5.6 85.6 and Gemini 3.8 84.8. The benchmarks include **tweet_eval emotion** (emotion recognition, T1) and **Civil Comments insult** (moderation/toxicity), but only means are in the deposit. Japanese data: MASSIVE ja-JP. **Confirms G1** (typed models in the same band as, or slightly below, frontier models at lower latency). Low quality: README only, with tables in an external blog.

**zen23047544 — Jev trading agent on Binance L2 data (Prados Tapia). Coded: G4 S.**
Reports ECE 0.0228, Brier 0.0274 and Sharpe 14.92 on 1,000 frozen ticks. Problems: the calibration target is undefined; the text and tables disagree (ECE 0.0542/0.0306 in the text vs 0.0546/0.0238 in Table 2); t = 24.85 is identical across rows; the LLM comparison is analytical. The coded S rests on a lower-quality, single-run study. **It should not move the G4 box** (nominally confirms "often well calibrated").

**zen23050542 — TITAN-SR replication with Jev (Kataoka). Coded: G1 Q.**
One Noul question over 142,504 records from 22 Cochrane reviews. Median AUC 0.9827. At the plugin's untuned 0.3 threshold, pooled recall is 0.935 and specificity 0.857, with recall ≥ 99% in only 16 of 22 reviews (minimum 0.692). The threshold was fixed in advance and transfers partly. **Confirms G1 "good ranking, thresholds vary by setting".**

**zen23075657 — Jev vs adapted encoders on ToxicChat (Hagino). Coded: G1 Q.** This is **toxicity / content moderation** (relevant to 安全阀 and 恨语).
At a threshold chosen on 1,000 dev labels, Jev reaches 90.52% recall at 3.24% FPR (AUROC 0.9849), against 35.63–58.91% recall for the encoders; only Jev passes the gate. But on human-annotated negatives its FPR is 5.39%, above the 5% tolerance, so the gate does not carry over to the human-labelled subset. **Confirms G1** (strong ranking; the decision threshold depends on the label mix and was fitted locally). Jailbreak is excluded from the target.

**zen23088660 — Confidence-gated reranking for domain-name segmentation (Wang, Liu). Coded: G4 Q, G6 S.**
- G6: a gate set on 1,000 names lifts held-out accuracy from 90.0% to 92.8% (178 corrected vs 65 broken). At p ≥ 0.90 it accepts 53.1% of names at 99.2% precision, and every threshold from 0.30 to 0.98 beats the baseline.
- G4: probabilities are conservative in every band, not calibrated.

G6 S **confirms the positive half of the G6 box** (a gate fixed in advance held on new data, with escalation to a rule-based fallback). It does not reverse it.

**zen23154999 — Local Laya + RAD intrusion detection (Cingil). Coded: G1 Q, G6 Q.**
- G1: the fine-tuned Laya with retrieval reaches F1 0.89 on synthetic logs and 0.98–0.99 on real SSH brute force, but misses slow port scans (recall 0.03–0.31) because the synthetic threshold does not transfer.
- G6: simulated autonomous blocking catches every attacker but makes 17 ± 25 wrongful isolations per replication. High-confidence false alarms lengthen risk-scaled blocks (5.5 vs 2.9 h), so the author keeps shadow mode with human approval as the default.

**Confirms G1** (thresholds fail on shift) **and G6** (confident errors).

**zen23094322 — Measuring Institutional AI Research in India (Dave). Coded: G7 Q.**
Jev labels 41,172 works for a public-policy bibliometric panel. Validation is only 88 agent-adjudicated records: 90.9% agreement, 97.2% at p ≥ 0.75. Including lower-confidence labels changes the total by +49.8%. Found via a companion link, not by the queries. **Confirms G7** (population-scale reading is cheap; conclusions depend on confidence routing and need an audit sample, which here is not human).

---

**Direction changes:** none. No record in Z1 reverses an answer box.
- The strongest positive items are zen23088660 (G6 S) and zen22945279 (G6 gate, G4). Both fit the existing G6 and G4 readings.
- zen23047544's G4 S comes from a lower-quality study.
