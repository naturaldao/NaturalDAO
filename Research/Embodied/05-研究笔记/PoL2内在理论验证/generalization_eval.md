# PoL2 normative-theory generalization evaluation

## 1. What evidence distinguishes learned rules from memorized cases?

### Takeaway

A random held-out accuracy score is weak evidence for normative rule acquisition: examples can share near-duplicate surface forms, rule families, or familiar compositions across the split. The strongest practical evidence is a pre-registered behavioral profile across rule-held-out compositions, controlled counterfactuals, invariance tests, and action-grounded outcomes, with all claims explicitly limited to a frozen PoL2 specification version and evaluation distribution.

### Cited Findings

- SCAN tests whether a model can map familiar primitives into systematically novel command combinations. Lake and Baroni found that sequence-to-sequence models generalized when test examples differed only modestly from training examples, but failed on splits requiring systematic compositional skills. This shows why random IID splits can conceal a failure of rule recombination. [Lake & Baroni, ICML 2018](https://proceedings.mlr.press/v80/lake18a.html)
- CFQ introduced a distribution-based method for constructing compositional generalization splits and a realistic question-answering dataset. Its authors report that tested architectures failed to generalize compositionally, with compound divergence strongly negatively correlated with accuracy. It motivates measuring overlap/divergence of atomic rules and their compounds rather than relying on random splits. [Keysers et al., ICLR 2020 / arXiv](https://arxiv.org/abs/1912.09713)
- CheckList argues that held-out accuracy often overestimates generalization and proposes capability × test-type behavioral coverage, including minimum-functionality tests, label-preserving invariance tests, and directional tests where a perturbation should change predictions in a specified way. [Ribeiro et al., ACL 2020](https://aclanthology.org/2020.acl-main.442/)

### Inferences

- For PoL2, define each case by (a) atomic normative clauses it invokes, (b) clause composition/order, (c) entity/role bindings, (d) physical state and uncertainty, and (e) expected typed action decision. Split by *composition* and *scenario template*, not merely by wording. Keep individual clauses represented in training while withholding some clause combinations for a zero-shot composition test; separately hold out selected clauses entirely to test clause transfer.
- Report multiple regimes separately: random case split (sanity baseline), paraphrase/template-held-out, composition-held-out, and clause-held-out. A model that succeeds only on the random split has learned at most within-distribution behavior; composition-held-out success supports systematic transfer but does not establish the whole theory is represented.
- Because Kev is typed-choice plus SFT, score the selected action and the full choice distribution. Evaluate whether choices follow the same clause when options are reordered, renamed, or supplemented with plausible distractors; evaluate probability calibration and selective abstention separately from top-1 accuracy. Choice accuracy alone may be driven by label/option priors.
- Include simulator-executable decisions (permit, reject, defer/clarify, or choose safer feasible candidate) where possible. A model’s text explanation is not evidence that the action-selection policy follows that explanation; the action interface and the normative rationale should be separately scored.

### Gaps

- The cited compositionality papers establish evaluation methods and model-specific generalization behavior on their tasks; they do not show that their methods can certify acquisition of an open-ended moral or governance theory.
- A finite evaluation suite cannot establish complete understanding of an evolving theory. The defensible estimand is behavioral competence under a specified version, clause inventory, scenario distribution, and action interface.
- The current PoL2 labels and case inventory need an independently specified clause-to-action map before a clause-held-out split can be considered a valid test rather than a post-hoc interpretation of model errors.

## 2. How should PoL2 counterfactual and minimal-pair tests be designed?

### Takeaway

Use paired interventions to test both *sensitivity* to normatively decisive facts and *invariance* to irrelevant changes. Minimal pairs are powerful diagnostics only when the changed factor is genuinely isolated and the test distribution resembles deployment; passing them is not sufficient evidence of broad competence.

### Cited Findings

- BLiMP uses 67 datasets of 1,000 minimally different sentence pairs, designed from linguist-crafted grammar templates to isolate particular grammatical or semantic phenomena; aggregate human agreement with the labels was 96.4%. This is a precedent for controlled, phenomenon-specific contrast sets rather than a single opaque score. [Warstadt et al., TACL 2020](https://aclanthology.org/2020.tacl-1.25/)
- CheckList distinguishes invariance tests, where label-preserving perturbations should not change the prediction, from directional-expectation tests, where a targeted perturbation should change the prediction in a known direction. [Ribeiro et al., ACL 2020](https://aclanthology.org/2020.acl-main.442/)
- Vamvas and Sennrich caution that contrastive minimal-pair results can produce false positives if the hypothesis is poorly motivated, and that evaluation/deployment distribution mismatch weakens claims about deployed behavior. They recommend creating test pairs from machine-generated text when the target is machine-generated text. [Vamvas & Sennrich, BlackboxNLP 2021](https://aclanthology.org/2021.blackboxnlp-1.5/)

### Inferences

- Build a PoL2 contrast suite from clause-level tests. For each norm, specify beforehand: (1) facts that must change the decision; (2) facts that must not change it; (3) facts that should trigger uncertainty/clarification; and (4) conflicts where a higher-priority clause should dominate. Generate matched pairs by changing one semantic variable at a time, not simply one word.
- Candidate decisive variables for embodied tasks include: valid vs expired authorization; action within vs outside authorized scope; known vs occluded object state; reversible vs irreversible action; safe vs unsafe predicted outcome; and explicit stop condition present vs absent. For each pair, hold geometry, lexical frame, choice set, and all other facts constant. These are proposed test dimensions, not claims that they exhaust PoL2.
- Add metamorphic controls: change robot/object names, reorder answer choices, paraphrase narration, alter irrelevant background objects, or vary camera wording while preserving the decision. Expected invariance makes shortcut use visible. Conversely, make targeted state changes (e.g., clearance revoked, collision risk crosses threshold) and require a specified decision flip.
- Use both model-authored scenarios and simulator-generated states, then score the actual typed action and downstream simulator result. Check that pair members do not accidentally differ in multiple causal variables and include hard negatives with plausible but norm-violating actions.

### Gaps

- No cited paper validates these specific PoL2 variable choices; they must be derived from the project’s frozen clause definitions and physical action semantics.
- In a simulator, “one-variable” interventions may alter downstream feasibility or state. The experiment must record which variables are directly manipulated and which state changes are consequences.
- Minimal-pair success can reflect a local decision boundary rather than a compositional normative representation; it must be paired with held-out compositions and broader scenario sampling.

## 3. How can the evaluation limit contamination and support an evolving theory?

### Takeaway

Treat evaluation data as versioned experimental infrastructure: freeze the model and normative specification, sequester a newly generated test set, rotate challenge items, keep a public development set distinct from a hidden confirmatory set, and publish exact generators/scoring for reproducibility after the run. Monitor semantic overlap and generalization gaps, not just literal text duplication.

### Cited Findings

- ConStat defines benchmark contamination functionally as artificially inflated performance that does not generalize to rephrased samples, synthetic samples from the same distribution, or other benchmarks for the same task. It compares primary/reference benchmark performance relative to reference models to detect and quantify such inflation. [Dekoninck et al., NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/a7f89793b9e6f8c6568dbbb6ff727b9b-Abstract-Conference.html)
- LiveBench is designed to reduce contamination and judge bias through regularly updated questions, objective answer checking, and delayed release of recent questions. Its paper describes replacing roughly one sixth of the questions per monthly update, keeping a recent tranche private, and tracking version changes. [White et al., ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/e4a46394ba5378b3f9a186a5b4c650d1-Paper-Conference.pdf)
- Clean-Eval proposes generating paraphrase/back-translation variants of benchmark items to reduce surface-form contamination and evaluate performance across candidate equivalent forms. This is a useful auxiliary control but does not by itself detect memorized semantics or rule-family leakage. [Zhou et al., Findings of NAACL 2024](https://aclanthology.org/2024.findings-naacl.53/)

### Inferences

- Since PoL2 is expected to evolve, every run should pin a theory version (clause text/IDs, priorities, exceptions), data generator version, candidate-action schema, simulator version, adapter/base-model hashes, and evaluation code commit. A new normative version is a new condition: measure old-version retention, transfer to changed/new clauses, and behavior on explicit conflicts, rather than silently pooling old and new labels.
- Construct test items *after* SFT data and training choices are frozen. Keep a hidden confirmatory set whose labels and cases are not used for prompt tuning, threshold selection, or error-driven retraining. If results cause a model update, the previous test becomes development data; create a fresh confirmatory set for the next claim.
- Use semantic family and generation provenance to guard against leakage: deduplicate exact strings, normalized text, entity-swapped templates, and clause-composition signatures. Report the count removed at each level. A paraphrase test is not an independent test if it shares a memorized case template or composition with training.
- For a lightweight contamination audit, compare scores on (i) the original/known case set, (ii) independently generated paraphrases, (iii) novel simulator states sampled from the same task grammar, and (iv) held-out clause compositions. A disproportionate drop from (i) to (ii–iv) is evidence that the claim is narrower than case accuracy suggests; it is not by itself proof of training-data contamination.
- A clean report should publish per-clause, per-composition, per-pair, and action-outcome metrics; confusion matrices and abstention rates; confidence intervals clustered by scenario family (not treating correlated variants as independent); and failure examples selected by a fixed procedure.

### Gaps

- ConStat’s proposed statistical method uses benchmark/model comparison and was evaluated across several public LLM settings; this project’s small, custom Kev model may lack enough reference models or items for the same statistical procedure. The conceptual distinction between literal overlap and non-generalizing performance still applies, but a formal ConStat estimate may not be powered.
- Dynamic hidden sets reduce direct test leakage but trade off independent reproducibility. A practical compromise is to publish generators, schemas, scoring, and a delayed version of each hidden set after the confirmatory evaluation.
- No benchmark protocol can establish that a model “holds the complete PoL2 theory” in a metaphysical or unrestricted sense. The report should state a narrower operational conclusion, e.g. “SFT improves version-X clause-consistent typed decisions on the preregistered held-out composition and counterfactual suite, including simulator execution.”
