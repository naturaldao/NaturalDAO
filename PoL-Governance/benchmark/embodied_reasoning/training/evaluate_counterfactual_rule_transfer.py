"""Evaluate rule-sensitive behavior on paired counterfactual state changes.

The test cases are generated from the same frozen v0.2 contract used to create
distillation labels. This is a mechanism-oriented diagnostic, not an independent
validation of the normative mapping or of complete PoL2 understanding.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_kev_pol2_internalization as pilot

ROOT = HERE.parents[4]
DEFAULT_RUN = HERE / "results" / "kev-pol2-counterfactual-causal-20261026"
SEEDS = (20261026, 20261027, 20261028)
FACTORS = ("permission", "scope", "freshness", "location", "terminal")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_eval_rows() -> list[dict]:
    # Exclude repeated legal-transfer identity variants; this creates a complete
    # 3 x 3 x 2 x 4 x 2 state grid for each held-out instruction family.
    rows = [r for r in pilot.build_rows()["test"] if not r["id"].endswith(tuple(f"entity-{i:03d}" for i in range(192)))]
    expected = len(pilot.TEST_TEXTS) * 3 * 3 * 2 * 4 * 2
    if len(rows) != expected:
        raise RuntimeError(f"Expected complete counterfactual grid of {expected}, got {len(rows)}")
    for row in rows:
        row["options"] = list(pilot.ACTION_ORDER)
        row["policy_action_index"] = row["options"].index(row["policy_action"])
        row["task_only_action_index"] = row["options"].index(row["task_only_action"])
    return rows


def make_pairs(rows: list[dict]) -> dict[str, list[tuple[str, str, str]]]:
    by_case = {r["id"]: r for r in rows}
    by_cell: dict[tuple, dict] = {}
    for row in rows:
        state = tuple(row["state_family"].split("|"))
        # Restore typed variable values from the generator's state-family key.
        by_cell[(row["instruction_family"], state)] = row
    pairs: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for kind in pilot.TEST_TEXTS:
        cells = [(state, by_cell[(kind, state)]) for state in itertools.product(
            ("GRANTED", "DENIED", "UNKNOWN"), ("MATCH", "MISMATCH", "UNKNOWN"),
            ("FRESH", "STALE"), ("SOURCE", "TARGET", "OTHER", "UNKNOWN"), ("False", "True"))]
        for i, (state_a, row_a) in enumerate(cells):
            for state_b, row_b in cells[i + 1:]:
                diff = [k for k, (a, b) in enumerate(zip(state_a, state_b)) if a != b]
                if len(diff) == 1:
                    pairs[FACTORS[diff[0]]].append((row_a["id"], row_b["id"], kind))
    return pairs


def score_pairs(rows: list[dict], predictions: list[dict], pairs: dict[str, list[tuple[str, str, str]]]) -> dict:
    source = {r["id"]: r for r in rows}
    pred = {r["id"]: r["predicted_action"] for r in predictions}
    result = {}
    for factor, links in pairs.items():
        changed, invariant, endpoint_correct = [], [], []
        directional_groups: dict[str, list[float]] = defaultdict(list)
        invariant_groups: dict[str, list[float]] = defaultdict(list)
        for aid, bid, kind in links:
            a, b = source[aid], source[bid]
            target_changed = a["policy_action"] != b["policy_action"]
            pa, pb = pred[aid], pred[bid]
            correct_a, correct_b = pa == a["policy_action"], pb == b["policy_action"]
            if target_changed:
                ok = correct_a and correct_b and pa != pb
                changed.append(ok)
            else:
                ok = pa == pb
                invariant.append(ok)
            endpoint_correct.append(correct_a and correct_b)
            state_a = tuple(a["state_family"].split("|"))
            state_b = tuple(b["state_family"].split("|"))
            changed_axis = FACTORS.index(factor)
            group = "|".join([kind] + [v for j, v in enumerate(state_a) if j != changed_axis])
            if target_changed:
                directional_groups[group].append(float(ok))
            else:
                invariant_groups[group].append(float(ok))
        result[factor] = {
            "n_pairs": len(links),
            "n_decision_changing_pairs": len(changed),
            "directional_rule_response": statistics.mean(changed) if changed else None,
            "n_same_target_pairs": len(invariant),
            "irrelevant_to_target_invariance": statistics.mean(invariant) if invariant else None,
            "both_endpoints_correct": statistics.mean(endpoint_correct),
            "directional_group_scores": {k: statistics.mean(v) for k, v in sorted(directional_groups.items())},
            "invariance_group_scores": {k: statistics.mean(v) for k, v in sorted(invariant_groups.items())},
        }
    result["case_metrics"] = {
        "n_cases": len(rows),
        "exact_policy_action_accuracy": statistics.mean(pred[r["id"]] == r["policy_action"] for r in rows),
        "raw_action_admissibility": statistics.mean(pred[r["id"]] in r["eligible_actions"] for r in rows),
        "by_instruction_family": {
            kind: {"n": sum(r["instruction_family"] == kind for r in rows),
                  "exact_policy_action_accuracy": statistics.mean(pred[r["id"]] == r["policy_action"] for r in rows if r["instruction_family"] == kind),
                  "raw_action_admissibility": statistics.mean(pred[r["id"]] in r["eligible_actions"] for r in rows if r["instruction_family"] == kind)}
            for kind in sorted({r["instruction_family"] for r in rows})
        },
    }
    result["overall"] = {
        "n_pairs": sum(result[f]["n_pairs"] for f in FACTORS),
        "directional_rule_response": statistics.mean([result[f]["directional_rule_response"] for f in FACTORS if result[f]["directional_rule_response"] is not None]),
        "irrelevant_to_target_invariance": statistics.mean([result[f]["irrelevant_to_target_invariance"] for f in FACTORS if result[f]["irrelevant_to_target_invariance"] is not None]),
        "both_endpoints_correct": statistics.mean([result[f]["both_endpoints_correct"] for f in FACTORS]),
    }
    return result


def composition_overlap_metrics(rows: list[dict], predictions: list[dict], pairs: dict[str, list[tuple[str, str, str]]], train_families: set[str]) -> dict:
    source = {r["id"]: r for r in rows}
    pred = {r["id"]: r["predicted_action"] for r in predictions}
    out = {}
    for cohort in ("both_endpoints_seen_in_train", "at_least_one_endpoint_unseen_in_train"):
        out[cohort] = {}
        for factor, links in pairs.items():
            chosen = []
            for a, b, kind in links:
                seen_a = source[a]["state_family"] in train_families
                seen_b = source[b]["state_family"] in train_families
                if (cohort == "both_endpoints_seen_in_train" and seen_a and seen_b) or (
                    cohort == "at_least_one_endpoint_unseen_in_train" and not (seen_a and seen_b)):
                    chosen.append((a, b))
            changed, invariant = [], []
            for a, b in chosen:
                ra, rb = source[a], source[b]
                same = ra["policy_action"] == rb["policy_action"]
                if same:
                    invariant.append(pred[a] == pred[b])
                else:
                    changed.append(pred[a] == ra["policy_action"] and pred[b] == rb["policy_action"] and pred[a] != pred[b])
            out[cohort][factor] = {
                "n_pairs": len(chosen), "n_target_changing": len(changed), "n_target_invariant": len(invariant),
                "directional_rule_response": statistics.mean(changed) if changed else None,
                "target_invariant_prediction_rate": statistics.mean(invariant) if invariant else None,
            }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    ap.add_argument("--output", type=Path, default=DEFAULT_RUN / "counterfactual_results.json")
    ap.add_argument("--force", action="store_true", help="replace the aggregate JSON using cached per-model predictions")
    args = ap.parse_args()
    if args.output.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite {args.output}")
    if not torch.cuda.is_available():
        raise SystemExit("Pinned model evaluator requires CUDA; no implicit CPU fallback")
    sys.path.insert(0, r"D:\cache\kev-runtime\Lib\site-packages")
    from kev.checkpoint import Checkpoint, LoadOptions
    from kev.model import load_tokenizer
    initial = Checkpoint(pilot.INITIAL_CHECKPOINT)
    tok = load_tokenizer(pilot.BASE_ID, revision=pilot.BASE_REVISION)
    rows = canonical_eval_rows()
    pairs = make_pairs(rows)
    train_rows = [json.loads(x) for x in (args.run_dir / "train_used.jsonl").read_text(encoding="utf-8").splitlines() if x]
    train_families = {r["state_family"] for r in train_rows if not r["state_family"].startswith("legal-transfer-entity")}
    test_families = {r["state_family"] for r in rows}
    unseen_families = test_families - train_families
    started = time.perf_counter()
    torch.set_num_threads(4)
    torch.cuda.reset_peak_memory_stats()
    model_conditions = {}
    predictions = {}
    pred_cache = args.run_dir / "counterfactual_predictions"
    pred_cache.mkdir(parents=True, exist_ok=True)
    base_cache = pred_cache / "pretrained_kev.jsonl"
    if base_cache.exists():
        predictions["pretrained_kev"] = [json.loads(x) for x in base_cache.read_text(encoding="utf-8").splitlines() if x]
    else:
        base = initial.load("cuda", LoadOptions(dtype=torch.bfloat16, merge=False))[1]
        _, predictions["pretrained_kev"] = pilot.evaluate(base, tok, rows, "pol2_sft", batch_size=8)
        base_cache.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in predictions["pretrained_kev"]), encoding="utf-8")
        del base
        torch.cuda.empty_cache()
    model_conditions["pretrained_kev"] = {"checkpoint": pilot.INITIAL_CHECKPOINT}
    for arm in ("task_only", "pol2_sft"):
        for seed in SEEDS:
            path = args.run_dir / "adapters" / arm / f"seed-{seed}"
            if not (path / "adapter_model.safetensors").exists():
                raise SystemExit(f"Missing adapter {path}")
            name = f"{arm}_seed_{seed}"
            cache_path = pred_cache / f"{name}.jsonl"
            if cache_path.exists():
                predictions[name] = [json.loads(x) for x in cache_path.read_text(encoding="utf-8").splitlines() if x]
            else:
                model = Checkpoint(str(path)).load("cuda", LoadOptions(dtype=torch.bfloat16, merge=False))[1]
                _, predictions[name] = pilot.evaluate(model, tok, rows, "pol2_sft", batch_size=8)
                cache_path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in predictions[name]), encoding="utf-8")
                del model
                torch.cuda.empty_cache()
            model_conditions[f"{arm}_seed_{seed}"] = {
                "adapter_sha256": sha256(path / "adapter_model.safetensors"),
                "head_sha256": sha256(path / "head.pt"),
            }
            print(f"evaluated {arm} seed={seed}", flush=True)
    metrics = {name: score_pairs(rows, pred, pairs) for name, pred in predictions.items()}
    # Average seeds at the group level; pairs sharing the same unchanged state
    # and instruction family remain one bootstrap cluster.
    summaries = {}
    for arm in ("task_only", "pol2_sft"):
        for factor in FACTORS:
            summaries.setdefault(arm, {})[factor] = {}
            for metric_name, group_key in (("directional_rule_response", "directional_group_scores"),
                                           ("irrelevant_to_target_invariance", "invariance_group_scores")):
                seed_scores = [metrics[f"{arm}_seed_{s}"][factor][group_key] for s in SEEDS]
                common = sorted(set.intersection(*(set(x) for x in seed_scores)))
                values = [statistics.mean([d[k] for d in seed_scores]) for k in common]
                summaries[arm][factor][metric_name] = {
                    "n_clusters": len(values),
                    "mean_cluster_score": statistics.mean(values) if values else None,
                    "cluster_bootstrap_95_ci": cluster_bootstrap(values, 20261026 + FACTORS.index(factor) + (100 if group_key.startswith("invariance") else 0)) if values else None,
                }
    paired_factor_deltas = {}
    for factor in FACTORS:
        paired_factor_deltas[factor] = {}
        for metric_name, group_key in (("directional_rule_response", "directional_group_scores"),
                                       ("irrelevant_to_target_invariance", "invariance_group_scores")):
            by_arm = {}
            for arm in ("task_only", "pol2_sft"):
                seed_maps = [metrics[f"{arm}_seed_{s}"][factor][group_key] for s in SEEDS]
                common = sorted(set.intersection(*(set(x) for x in seed_maps)))
                by_arm[arm] = {k: statistics.mean([m[k] for m in seed_maps]) for k in common}
            common = sorted(set(by_arm["task_only"]) & set(by_arm["pol2_sft"]))
            diffs = [by_arm["pol2_sft"][k] - by_arm["task_only"][k] for k in common]
            paired_factor_deltas[factor][metric_name] = {
                "n_clusters": len(diffs), "mean_difference_pol2_minus_task_only": statistics.mean(diffs) if diffs else None,
                "cluster_bootstrap_95_ci": cluster_bootstrap(diffs, 20261100 + FACTORS.index(factor)) if diffs else None,
            }
    case_groups: dict[str, list[float]] = defaultdict(list)
    pred_by_arm_seed = {}
    for arm in ("task_only", "pol2_sft"):
        for seed in SEEDS:
            pred_by_arm_seed[arm, seed] = {r["id"]: r["predicted_action"] for r in predictions[f"{arm}_seed_{seed}"]}
    for row in rows:
        pol_correct = [pred_by_arm_seed["pol2_sft", s][row["id"]] == row["policy_action"] for s in SEEDS]
        task_correct = [pred_by_arm_seed["task_only", s][row["id"]] == row["policy_action"] for s in SEEDS]
        case_groups[row["state_family"]].append(statistics.mean(pol_correct) - statistics.mean(task_correct))
    case_diffs = [statistics.mean(x) for x in case_groups.values()]
    overlap_case_metrics = {}
    overlap_pair_metrics = {}
    for name, pred in predictions.items():
        pred_map = {r["id"]: r["predicted_action"] for r in pred}
        overlap_case_metrics[name] = {}
        for cohort in ("seen_state_family", "unseen_state_family"):
            subset = [r for r in rows if (r["state_family"] in train_families) == (cohort == "seen_state_family")]
            overlap_case_metrics[name][cohort] = {
                "n_cases": len(subset),
                "exact_policy_action_accuracy": statistics.mean(pred_map[r["id"]] == r["policy_action"] for r in subset) if subset else None,
                "raw_action_admissibility": statistics.mean(pred_map[r["id"]] in r["eligible_actions"] for r in subset) if subset else None,
            }
        overlap_pair_metrics[name] = composition_overlap_metrics(rows, pred, pairs, train_families)
    summary = {
        "experiment": "PoL2 state-variable counterfactual transfer and invariance test",
        "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "design": {
            "train_test_split": "held-out instruction phrase families and entity/target identities; the balanced 384-row training sample contains only a subset of the full state-family grid",
            "test_cases": len(rows), "instruction_families": sorted(pilot.TEST_TEXTS),
            "state_family_grid": {"test_families": len(test_families), "train_families_in_grid": len(train_families & test_families),
                                  "test_families_unseen_in_train": len(unseen_families), "unseen_state_families": sorted(unseen_families)},
            "factors": list(FACTORS), "pair_generation": "all pairs differing in exactly one state-family variable within the same instruction family",
            "candidate_order": list(pilot.ACTION_ORDER), "seeds": list(SEEDS),
            "labels": "frozen deterministic pol2-embodied-contract-v0.2 operational contract",
            "estimands": ["directional response when the contract-preferred action changes", "prediction invariance when the preferred action does not change", "both-endpoint exact rule match"],
        },
        "conditions": model_conditions,
        "provenance": {
            "training_runner_sha256": sha256(HERE / "run_kev_pol2_internalization.py"),
            "counterfactual_evaluator_sha256": sha256(Path(__file__).resolve()),
            "contract_sha256": sha256(HERE.parent / "pol2-embodied-contract-v0.2.json"),
            "base_model": f"{pilot.BASE_ID}@{pilot.BASE_REVISION}",
            "initial_checkpoint": pilot.INITIAL_CHECKPOINT,
            "training_run_results_sha256": sha256(args.run_dir / "results.json"),
        },
        "pair_counts": {factor: len(pairs[factor]) for factor in FACTORS},
        "metrics_by_model_seed": metrics,
        "metrics_by_state_family_overlap": overlap_case_metrics,
        "counterfactual_pairs_by_state_family_overlap": overlap_pair_metrics,
        "pooled_across_seed_cluster_bootstrap": summaries,
        "paired_cluster_differences": paired_factor_deltas,
        "paired_case_accuracy_difference": {
            "mean_difference_pol2_minus_task_only": statistics.mean(case_diffs),
            "n_state_family_clusters": len(case_diffs),
            "cluster_bootstrap_95_ci": cluster_bootstrap(case_diffs, 20261110),
        },
        "runtime": {"device": torch.cuda.get_device_name(0), "torch": torch.__version__,
                    "peak_cuda_memory_gib": torch.cuda.max_memory_allocated() / 2**30,
                    "elapsed_seconds": time.perf_counter() - started},
        "limitations": [
            "This is a post-training mechanistic behavioral diagnostic, not a fresh independent normative benchmark.",
            "The tested contract is a narrow synthetic embodied-action slice, not complete PoL2.",
            "Train and test share state-axis values; only phrase families and entity/target identities are held out.",
            "Labels are generated by the same executable contract that defines the target; the study cannot validate that operationalization itself.",
            "Output behavior and counterfactual consistency do not establish private representations, subjective understanding, or all-theory possession.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "overall": {name: value["overall"] for name, value in metrics.items()},
                      "pooled": summaries, "elapsed_seconds": summary["runtime"]["elapsed_seconds"]}, ensure_ascii=False, indent=2))


def cluster_bootstrap(values: list[float], seed: int, n: int = 10000) -> list[float]:
    rng = random.Random(seed)
    draws = sorted(statistics.mean(rng.choice(values) for _ in values) for _ in range(n))
    return [draws[int(0.025 * n)], draws[int(0.975 * n) - 1]]


if __name__ == "__main__":
    main()
