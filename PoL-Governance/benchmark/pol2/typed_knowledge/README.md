# PoL2 typed-knowledge pilot v1.3

This public exploratory benchmark keeps five knowledge families separate and uses different task structures inside each family. It does not compute a cross-family score and is not a confirmatory test of theoretical internalization.

## Contents

- `build_dataset.py`: deterministically constructs the public dataset from the versioned PoL2 knowledge pack.
- `data-v1.3/`: 123 items, source-derived labels, and a manifest with source and output hashes.
- `run_models.py`: batched structured inference against local Ollama models; raw response sidecars are retained with prediction files.
- `score_runs.py`: exact-match and multi-label set metrics, plus matched item condition transitions and governance-rule strata.
- `plot_typed_eval.py`: creates a task-specific accuracy figure from the run summary.
- `runs-20261026-v1.3/`: complete local evaluation records and `summary.json`.

## Tasks and labels

| Family | Task(s) | n |
|---|---|---:|
| Concepts and relations | Definition-to-concept; directed relation completion | 26; 22 |
| Axioms and propositions | Axiom component identification; proposition source attribution | 4; 9 |
| Love languages | Definition-to-language among 16 types | 16 |
| Explicit governance rules | Review question-to-rule mapping | 28 |
| Researcher interpretations | Interpretation-to-source-anchor retrieval | 18 |

Labels are copied or derived deterministically from `POL2-Steward/pol2-service/knowledge/`. `reviewed` records, `candidate` rule mappings, approved-boundary references, and `validated_reference` interpretations retain their provenance. These statuses do not imply a comprehensive normative gold standard. Interpretation labels assess curated source-anchor retrieval, not truth or entailment.

## Conditions and validity note

- `closed_book`: no theory excerpt supplied.
- `source_context`: relevant raw source excerpts supplied, while structured target records, IDs, status fields, and approval metadata are withheld.
- The first direct-record context attempt exposed structured target identifiers/names and is invalid; it is excluded from v1.3 scores. The initial run directory is locally ignored and must not be reported as valid evidence.
- For the first four families, prompts/options are matched across conditions. Interpretation items were revised to use source-anchor options; both conditions were re-run for those items.

## Reproduction

From the repository root, with the same knowledge pack and local Ollama models installed:

```powershell
python PoL-Governance/benchmark/pol2/typed_knowledge/build_dataset.py
python PoL-Governance/benchmark/pol2/typed_knowledge/run_models.py --models qwen2.5:7b --conditions closed_book
python PoL-Governance/benchmark/pol2/typed_knowledge/run_models.py --models qwen2.5:7b --conditions source_context
python PoL-Governance/benchmark/pol2/typed_knowledge/run_models.py --models llama3.1:8b --conditions closed_book
python PoL-Governance/benchmark/pol2/typed_knowledge/run_models.py --models llama3.1:8b --conditions source_context
python PoL-Governance/benchmark/pol2/typed_knowledge/score_runs.py
python PoL-Governance/benchmark/pol2/typed_knowledge/plot_typed_eval.py
```

The checked-in data and result files represent the completed 2026-10-26 run, not a promise of bit-identical generation across Ollama/model revisions. Models were run locally through CPU inference. See [the full Research report](../../../../Research/Embodied/02-实验设计与审计/PoL2分类型知识评测先导.md) for the protocol, score tables, leakage audit, and limitations, and the [standard governance result card](../../../results/EVAL-04-qwen25-llama31-typed-knowledge-20261026/result-card.zh-CN.md) for the run config and combined predictions.
