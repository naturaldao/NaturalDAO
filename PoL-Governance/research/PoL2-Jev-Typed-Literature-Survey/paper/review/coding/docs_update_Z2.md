# Update coding, group Z2 (Zenodo, post-window): document notes

Primary coder, 2026-10-08. Full texts are under `scratchpad\update\zen<ID>.txt` / `.pdf`. For 23123503 and 23187206 I also checked the Zenodo API records and the aiscanlab.com posts they cite. For 23119392 I checked the deposit notebook for a model version.

Tiers: coded 8 (23094628, 23119392, 23179064, 23186353, 23189584, 23200782, 23221456, 23225893). Context 1 (23123503). Non-empirical 1 (23138396). Excluded-no-evaluation 1 (23187206). There are 16 coded rows: S 0, Q 16, N 0.

**zen23094628, Yway (Burmese open typed model). Coded G3/G4/G6, all Q.**
- **Tested:** an XLM-R encoder with Laya's decision head on 32 Burmese Wikipedia task kinds, held-out articles and unseen wordings.
- **Key numbers:** routing 0.994; answerable 0.916. "Has a number" falls from 0.995 to 0.579 on an unseen wording. Zero-shot Laya scores 0.120 on Burmese topics. ECE is 0.006–0.035 after per-type temperatures. The answer checker catches 81% of wrong answers at threshold 0.5, and shown-answer quality rises from 0.44 to 0.68.
- **Against the answer boxes:** confirms G3 (language/wording dependence), G4 ("partly"; calibration needs fitted temperatures) and G6 (works only with real-error training).
- **Flags:** a three-band show/retrieve/"I don't know" policy is proposed but not evaluated. Non-English data (Burmese), not Chinese.

**zen23119392, PMI thresholds for Wikidata relations. Coded G4 Q.**
- **Tested:** hosted Jev (version not reported; the screening note's jev-1.13.0 is not in the paper or notebook) as the only, unvalidated judge of 40,725 relations.
- **Key numbers:** with no evidence supplied, the three-valued true/maybe/false output used "maybe" only 1.0% and 0.8% of the time. Identical or symmetric inputs got different verdicts: 7/46 and 4/127 duplicate groups, 18/1,836 and 22/445 reciprocal pairs.
- **Against the answer box:** qualifies/confirms G4 (an "insufficient" option is rarely chosen; outputs are not fully coherent).
- **Not coded G7:** the study uses Jev at population scale but measures nothing about whether the verdicts are correct.
- **Flags:** three-valued output.

**zen23123503, Paraphrastic Resistance (López López). Context.**
- **Why context:** it re-reports the Laya 2×2 numbers of Z-23065532. The checkpoint swap changed 38/41 and 32/41 decisions; removing class definitions changed 9/41 and 19/41 (Table 4). Z-23065532 is already coded for these in `evidence_coding.csv`.
- **What is new:** only the correlation between IRP and decision diversity (r = −.081) and a Gemini-family IRP evaluator comparison. Neither evaluates the typed model.
- **Set:** the same headline results (r = −0.081, means 8.06/8.34, E1/E2 shifts −0.14/−0.56) were posted at aiscanlab.com/index-of-paraphrastic-resistance-text-fragility/ with `article:published_time` 2026-09-27T22:56:36Z. The Zenodo PDF is dated 2 Oct, deposited 3 Oct. The first public version is therefore inside the main window: late-indexed (grey) rather than post-window. This does not matter for the tallies because the record is context.
- **Flags:** approve/review/reject ternary output (context only).

**zen23138396, Continuous cheat detection (Howren). Non-empirical, confirmed.**
- **Why non-empirical:** the abstract says "The design has not yet been implemented or evaluated". It is an architecture with cost-derived thresholds, escalation to reasoning models or humans, and human confirmation of every ban.
- **Flags:** content moderation and sanctions (account bans); fairness for accessibility hardware is discussed, not tested.

**zen23179064, Exact-target calibration audit (Velu). Coded G3/G4/G7, all Q.**
- **Key numbers (jev-1.13.0):** Choice is a step function on stated probabilities: a 45%→55% base rate raises it by 0.83–0.98 against a correct 0.10, and temperature-scaled Choice is still 55× worse than Noul on base rates. Noul stays within 0.015–0.027. The zero-evidence pull comes from the option word "heads" (+0.354), not from position.
- **Human-vote data:** neither primitive beats a uniform guess on contested ChaosNLI/DICES items. All three open "RLCD" models fail differently.
- **Against the answer boxes:** confirms G4 ("partly"; calibration is local, related probabilities do not cohere), G3 (name effects) and G7 (understates disagreement).
- **Flags:** DICES-350 is chatbot safety/harm rating, so it touches content moderation; Choice is worse than uniform on every DICES measure. The ChaosNLI "neutral" option is the third value.

**zen23186353, Noma (open sliced-decoder typed model). Coded G3/G4/G6, all Q.**
- **Key numbers:** sealed set 82.6% with ECE 0.043 after temperature scaling. Held-out multi-step: 48.2% accuracy at 70.8% confidence. Reversing the options changes 9.7% [6.2, 14.8] of answers.
- **Abstention:** the supervised abstain head reaches AUROC 0.82 (0.46 without supervision) on only 15 items, and needs a tuned threshold on out-of-scope queries.
- **Against the answer boxes:** confirms G3 (order dependence), G4 (calibration local and lost under shift) and G6 (gates miss a whole error class below 0.9).
- **Flags:** abstention output. "Tone and safety" is one sealed family (30/32), too small to code G1.

**zen23187206, IRP vs. typed decision system (López López). Excluded-no-evaluation.**
- **Why excluded:** the typed supervisor's model is never identified. Table 6 measures the "typed decision" through the same API path as `gemini-flash-latest` (mean 3,387 ms), which fits a schema-constrained generative model, not Laya. The Laya latencies in Table 5 come from the earlier study.
- **What it reports:** the supervisor had 0/30 failure recall against an IRP gate's 30/30.
- **If the author confirms the supervisor was Laya:** this would be G1 N, not independent of Z-23065532.
- **Set:** results were posted at aiscanlab.com on 2026-09-28 02:08 UTC, inside the main window.

**zen23189584, Jev runtime-governance PoC (Inoue). Coded G5 Q.**
- **Design:** a case study with two Human-Gated live calls (jev-latest resolved to jev-1.13.0), each with a four-label output.
- **Results:** SUFFICIENT 0.86 on F-01 and INSUFFICIENT 1.00 on F-02, both the expected labels. Both decision paths were reconstructed from hashed evidence, but only inside the author's deterministic shell. The J4 failure injection is offline and mocked (0 fail-open in 20 cases).
- **Against the answer box:** confirms G5 ("recorded and decomposed, not explained").
- **Flags:** an UNCERTAIN option was offered and never chosen (0.03 and 0.00).

**zen23200782, Typed per-turn supervision for SWE agents (Ramadan & Tall). Coded G6 Q.**
- **Key numbers:** active Jev scored +7.2 pp Resolve@1 over no supervisor (CI −4.3 to +18.8, n = 69). The no-message shadow arm scored +8.5 pp (CI 0.0 to +16.9). Active vs shadow was +1.6 pp.
- **Reading:** the effect is not distinguishable from run-to-run variation.
- **Against the answer box:** qualifies G6. It is a null/unresolved oversight result, which neither supports nor contradicts "depends on where escalation goes".

**zen23221456, System-One Control Bench (Pereira). Coded G4 Q, comparator worse.**
- **Key numbers (gridworld navigation):** full-context Jev wins 57% against Gemma 4 26B 61% and DeepSeek V4.1 Flash 60%; the paired difference is not established. Jev answers 90% of exam positions optimally.
- **Calibration:** in its own games, Jev's ECE is 0.21 and its Brier score 0.283 is worse than a constant (0.250). A Qwen3.5-4B chat-model readout has ECE 0.06. Laya and GLiClass are near chance.
- **Against the answer box:** qualifies G4. This is a pair where a generative comparator was better calibrated, and miscalibration appears in self-induced states, which fits "calibration is local".

**zen23225893, SignRule-Decide (Ildan). Coded G3/G4/G6, all Q.**
- **Model:** an open 4B Kev-style model with abstention.
- **Austria:** 99.3% agreement with the AI consensus on coalitions; test ECE 0.002/0.007 after temperature scaling.
- **Unseen Danish register:** rule type 62.4%. Learn-then-Test thresholds certified answering everything, and the risk was 14.3% against a 5% target. 10 of the 12 dangerous Austrian errors came at confidence ≥0.9.
- **Against the answer boxes:** confirms G6 ("thresholds fixed in advance missed their error targets on new data"), G4 (calibration local, abstention rarely triggered) and G3 (cross-language/register degradation).
- **Flags:** abstention; non-English (German, Norwegian, Danish) data.

## Direction of answer boxes

No Z2 finding changes the direction of any answer box; all 16 pairs are Q. G4 gains one pair where the typed model is worse than a generative comparator (23221456: ECE 0.21 vs 0.06). G6 gains one more out-of-distribution threshold failure (23225893: risk 14.3% against a 5% target).
