# Evidence codebook v3 (symmetric, detector use)

## Definitions used for coding

- **Typed decision model**: a model that returns a probability distribution over options declared by the caller (or a probability for a yes/no statement) without generating free text. Includes hosted Jev and open models built on the same interface (Laya, Open-Jev, JevLite, Kev, SemIf, this-that-model, Von, Nimble, basal, Chinese-Jev, ...), and Jev-style readouts of generative models when the study treats them as such.
- **Detector use**: the model's output is a recorded signal that ranks, prioritises, or triggers review, or triggers only actions that are bounded in time and fully reversible.
- **Judge use**: the output, without contemporaneous human confirmation, determines an outcome that restricts a person's speech, resources or account beyond a short bounded period, or that cannot be fully reversed on appeal. Codes are NOT assigned for judge use; the paper argues about judge use separately.

## Axes (governance requirements derived from PoL2 clauses)

- G1 Detection: can it detect violations, harmful or out-of-scope AI behaviour (accuracy, AUROC, F1, threshold transfer)?
- G2 Attackability: can content under review steer the decision (injection, context additions, opinions, adaptive attacks)?
- G3 Semantic fairness: are decisions stable under option names/definitions, order, wording, language and script, and fair across groups and cultures?
- G4 Honesty: are probabilities calibrated and coherent, and does the model abstain / choose "insufficient" when it should?
- G5 Decision chains: can a decision that is only a number be audited, decomposed and explained?
- G6 Oversight: does "act when confident, escalate when unsure" work (cascades, gates, deferral, error correlation with escalation targets)?
- G7 Public scale: use for population simulation, public administration or large-scale deployment (cost, representativeness, ecosystem).

## Codes (one per document x axis, for detector use)

- **S (supports)**: the study's primary result on this axis shows the typed model performing the function at least as well as its comparator(s) under the study's own conditions — or, without a comparator, meeting the study's stated criterion — with no extra condition (local threshold fitting, recalibration, restriction to a language/domain, human review) that the study had to add for it to work.
- **N (negative)**: the primary result shows the typed model failing the function (e.g. attack success on a substantial share, ranking inversion, systematic bias, calibration the study judges unusable, confident errors a gate cannot catch) or performing clearly worse than its comparator(s).
- **Q (qualifies)**: the primary result is mixed across tasks or sub-types, or success depends on a condition the study had to add.
- Tie-break: if positive and negative findings are both primary, code Q. A study is coded once per axis by its primary finding for that axis.
- Rule (iv) (added to Appendix E in round 2 of the review, but missing from this file until 2026-10-08, when the update-search second coder pointed out the gap): conditions that constitute a requirement's test are not added conditions. These are adversarial content for G2, name, order or language perturbations for G3, and adversarially selected items for G6. A failure under them is coded N, while a success that needs a condition outside the test is coded Q.
- Non-empirical items (essays, opinion, theory, position) are recorded with empirical = no and excluded from tallies.

## Additional fields per row

- `system`: `hosted` (TypeSafe Jev, any version), `open` (open typed model), `both`, or `none` (no typed model measured).
- `jev_version`: as reported (e.g. `jev-1.13.0`), or `not reported`, or `n/a`.
- `comparator`: result of the typed model relative to a generative-model comparator on this axis: `better`, `similar`, `worse`, `mixed`, or `none` (no generative comparator on this axis).
- `rationale`: one sentence with the decisive numbers and a locator (section/table/figure).

## Quality appraisal (one row per document)

- `verification`: `full text` / `record description` / `abstract` / `live source` (what WE read).
- `independence`: `independent` / `author-built system` (authors evaluate a system or tool they built) / `vendor` (TypeSafe-affiliated) / `unclear`.
- `design`: `preregistered` / `held-out` (held-out or cross-validated evaluation, or repeated runs) / `single-run` / `case study` / `non-empirical`.
- `size_uncertainty`: `n+CI` (sample sizes and intervals or tests reported) / `n only` / `none`.
- `quality` (as first written; superseded): `higher` if verification = full text or live source AND design in {preregistered, held-out} AND size_uncertainty = n+CI; `lower` if design in {single-run, case study} OR size_uncertainty = none OR verification in {record description, abstract}; otherwise `moderate`.
- Design rating actually used (round 2 of the review; computed by `scripts/merge_coding.py` and `scripts/merge_update.py` from the fields above, and stated in §3; written into this file on 2026-10-08 after round-12 review R12A-5):
  - **stronger**: design in {preregistered, held-out}, AND size_uncertainty = n+CI, AND independence = independent;
  - **weaker**: design in {single-run, case study, non-empirical}, OR size_uncertainty = none;
  - **moderate**: all other cases.
  - Coders record the fields; they do not assign the rating.
