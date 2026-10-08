# Update search 2026-10-08: document notes, group U1

Primary coder: AI agent, 2026-10-08. All eight documents were read in full from the scratchpad text files (HTML versions; 2610.03387 is v2). All eight are **coded**. None is context-only or non-empirical. Codes are for detector use (CODEBOOK_v3).

**arx02267 (2610.02267, late-indexed). Paired Jev/Laya evaluation for agent harnesses.** Hosted jev-1.13.0 and open Laya 0.3.21 were tested on 11 decision points (7,283 base cases and 6,640 variants), with a self-audit. Jev led on 9 of 11 points. Injection screening reached AUROC .98, but Jev passed 25.5% of harmful requests (Laya 81.5%) and was unusable for PII. Option-order flips were 1.8% for Jev and 30.3% for Laya, and wording moved accuracy by 5–15 pp. Pooled ECE was 0.143/0.080 for Jev. The pre-screen saved only 4.3%, and held-out thresholds overshot the 5% FNR target (p95 up to 16.7%).
- G1 Q: confirms the box (good ranking on injection; sub-type failures in safety and PII).
- G3 Q: confirms (robustness is model-dependent, and Jev is far less order-sensitive than Laya).
- G4 Q: confirms (calibration is local and needs per-domain recalibration).
- G6 Q: confirms (thresholds fixed in advance miss their targets on new data; savings are small).
- Flag: safety and moderation gate (harmful-request screening).

**arx02293 (2610.02293, late-indexed). HakemBench, a Turkish typed-decision benchmark.** It has 4,275 questions in 7 tracks, including **prompt-injection guardrails and offensive-comment moderation**. 16 rows were scored. Jev 1.13 ranked 4th (composite 0.825), just behind three hosted chat LLMs (0.827–0.888). Its order sensitivity was 0.039 against 0.366–0.590 for Laya. Calibration axis 0.706, selective automation 0.935. Open typed encoders were near or below the surface-cue baseline. The gold labels are AI-made, and the lab's own model is on the board.
- G1 Q, G4 Q, G6 Q: confirm (hosted Jev is near but below the best LLMs; open models are much weaker).
- G3 Q: confirms (Jev robust to order, paraphrase and English translation; slot signal 0.059 [0.020, 0.107] hints at contamination).
- Flag: non-English (Turkish) evidence that Jev transfers. The moderation-track numbers are not in the paper itself.

**arx02486 (2610.02486, late-indexed). sbert2s1, typed models built by the authors from biomedical sentence encoders.**
- G4 Q: confirms "calibration is local". After temperature scaling, seen-task ECE was 3.8–4.3, against 8.5–9.1 for Qwen3.8-27B and Gemma-4-31B. Held-out tasks were poorly calibrated, and answerability on long notes was near chance.
- G3 Q: order flips were 10–17% for cross heads (including Laya-large) and 0.3% for the prior-fused head.
- G6 Q: confirms the box. Escalating the 20% least confident questions to Gemma raised accuracy from 59.5 to 68.4 (Gemma alone 62.1), but the budget was fixed retrospectively on the test set.
- Hosted Jev was not measured. The privacy name-gate reached AUROC about 72–78 zero-shot against 100 for the LLMs (App. H). This is noted here and not coded.

**arx02586 (2610.02586, late-indexed). Labels override definitions in open Jev-style models.** Three laya checkpoints follow the option label, not the definition. Neutral A/B labels gave +0.1511 on PolicyBench-XF, and a contradicting label cut accuracy to 0.1357. von is invariant. The cause is prompt rendering, and LLM label readouts show the same effect. Negated yes/no questions are not read (flip 0.9656–0.9825). Under label conflict, confidence ranks errors backwards (AUROC 0.2433).
- G3 N: confirms "decisions can follow the names of options rather than the definitions bound to them"; neutral identifiers are again the fix.
- G4 N: confirms "related probabilities do not always cohere" (negation).
- G6 N: confirms. Confident errors pass the gate, and a second-rendering disagreement check catches them.
- Open models only; Jev was not measured.

**arx08829 (2610.08829, late-indexed). Emo-Jev, EMOTION RECOGNITION (tension T1) and CHINESE DATA.** Hosted jev-1.13.0 was run zero-shot on sentiment, emotion, sarcasm and humour (8 datasets, including the **Chinese CMMA** emotion set) against five LLMs under IO and CoT prompting. Jev-Direct averaged 62.93% macro-F1, against 67.28% for the best LLM, and ranked first on no dataset. English E-c emotion: 52.47 vs 52.61. Chinese CMMA: 21.06 vs 19.82–23.31 for the LLMs (all low). Jev cost 96.41% less than Gemini IO, and its median latency was 250 ms. Decomposing the decision into atomic judgments, or adding multi-path judgments to the state, did not help: average macro-F1 was 62.00% and 61.61%, and decomposition alone 57.31%.
- G1 Q: confirms the box (cheap, mid-pack, below the best).
- G5 Q: qualifies the second half of the box ("writing intermediate facts into the state ... more accurate"), because here the decomposed chains were not more accurate.
- For T1: this adds to the thin, mixed emotion evidence. The study classifies the emotion expressed in texts and posts and does not infer the inner state of a person. Its accuracy on Chinese emotion is low for every system (macro-F1 about 20–23). Single run, no intervals; quality lower.

**arx03073 (2610.03073, post-window). SecJev, security typed models built by the authors on Kev.** In-domain task-macro accuracy was 90.34–94.51%, level with generative SFT. On new sources, only 48.67% of BIPIA injections were caught, and 66.40% of benign IoT-23 traffic was flagged.
- G1 Q: confirms (thresholds and transfer fail across sources).
- G3 S: paraphrase and permutation agreement were 95–99%. This is the only S code in this group. It is an in-domain fine-tuned model, so it does not change the G3 box.
- G4 Q: confirms "calibration is local" (raw ECE 1.53–2.18% in-domain; confidence on the general suites not recovered).
- Hosted Jev was not measured.

**arx03324 (2610.03324, post-window). HateDecide, HATE-SPEECH MODERATION (safety valve, hate language).** Hosted jev-1.13.0 and five open decision models were tested on 4 English hate-speech datasets, with no task training. Jev's macro-F1 was .826/.691/.738/.960, against GPT-6 Sol at .897/.682/.776/.976. Commercial LLMs were significantly ahead of all decision models only on Dynamic. Every model was weak at telling hate from offensive language (3-class: Jev .532, Sol .604). Definitions changed up to 27.9% of predictions, with gains and losses equally frequent (8 vs 8). Decomposition helped in 6 of 30 comparisons and hurt in 11. On HateCheck, Jev came within 1.6 points of Sol at about 97% lower cost.
- G1 Q: qualifies the box slightly in Jev's favour. The box says "often below the best ones", but here Jev is close to commercial LLMs on 3 of 4 hate datasets. The direction is unchanged: the hate/offensive boundary and conduct type (.538) remain weak, which matches "errors concentrate in sub-types".
- G3 Q: confirms (wording and definitions move decisions; Jev is least sensitive).
- G5 Q: qualifies, as for 08829. Decomposition makes the criterion inspectable but is not more accurate.
- G6 Q: confirms that results depend on the escalation target (Sol helps, Luna hurts). Exploratory.
- G7 Q: confirms that it is cheap at scale, conditional on local validation.
- English only.

**arx03387 (2610.03387 v2, post-window). Candidate coverage and rejection-policy transfer, THREE-VALUED/ABSTENTION.** Laya, hosted jev-1.13.0 and Qwen2.5-7B were tested with an explicit NONE option.
- G4 Q: confirms "'none' is chosen inconsistently". With NONE, Jev detected 63.7% of omitted answers at 3.3% false rejection, against 45.0% for Qwen and 86.0%/27.7% for Laya. Its out-of-scope detection dropped from 84.0% to 75.0% as the menus grew. On DBpedia its none-score AUROC was 0.987.
- G6 N: confirms. Thresholds calibrated in one task exceeded 5% false rejection in 6 of 12 transfers (Jev 69.3% on Emotion), or disabled rejection altogether.
- G3 Q: NONE wording moved Laya by +25.0 points and left Jev unchanged.
- Flag: this is the closest evidence here to PoL2's third "state of absence" value. Jev abstains better than a generative 7B model but misses about a third of absent answers.

## Summary for U1
- Tiers: coded 8 (5 late-indexed, 3 post-window); context 0; non-empirical 0.
- Rows: 27. Codes: S 1, Q 22, N 4. By requirement: G1 5, G3 7, G4 6, G5 2, G6 6, G7 1.
- Direction changes: none. G1 hate-speech evidence (03324) is somewhat more favourable to hosted Jev than "often below the best ones". G5 evidence (08829, 03324) qualifies the accuracy benefit of decomposed chains. Neither reverses a box.
