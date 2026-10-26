"""Exploratory matched-seed test of a pairwise structured objective.

Reuses the frozen narrow-contract composition lattice from the prior experiment.
Because that test is already public, this is an exploratory follow-up, not a new
confirmatory holdout. The only training change is an auxiliary pairwise margin.
"""
from __future__ import annotations
import json, statistics, sys, time
from datetime import datetime, timezone
from pathlib import Path
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_rule_composition_generalization as prior
import run_kev_pol2_internalization as pilot

OUT = HERE / "results" / "kev-pol2-structured-loss-20261026"
PRIOR_RESULTS = HERE / "results" / "kev-pol2-rule-composition-20261026" / "results.json"
SEEDS = (20261026, 20261027, 20261028)
PAIRWISE_WEIGHT = 0.25
PAIRWISE_MARGIN = 0.5

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {args.output_dir}")
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but unavailable")
    torch.set_num_threads(4)
    sys.path.insert(0, r"D:\cache\kev-runtime\Lib\site-packages")
    from kev.checkpoint import Checkpoint, LoadOptions
    initial = Checkpoint(pilot.INITIAL_CHECKPOINT)
    tok = initial.load_tokenizer() if hasattr(initial, "load_tokenizer") else None
    if tok is None:
        from kev.model import load_tokenizer
        tok = load_tokenizer(pilot.BASE_ID, revision=pilot.BASE_REVISION)
    train, valid, test = prior.build_data()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train_used", train), ("validation_used", valid), ("composition_test", test)):
        prior.write_jsonl(args.output_dir / f"{name}.jsonl", rows)
    runs, started = [], time.perf_counter()
    for seed in args.seeds:
        out = args.output_dir / "adapters" / f"seed-{seed}"
        print(f"[structured] seed={seed} rows={len(train)} test={len(test)}", flush=True)
        rec = pilot.train_one(seed, "pol2_sft", train, valid, out, initial, tok, args.device,
                              epochs=args.epochs, batch_size=args.batch_size,
                              pairwise_weight=PAIRWISE_WEIGHT, pairwise_margin=PAIRWISE_MARGIN)
        model = rec.pop("model")
        model.eval()
        pred = []
        with torch.no_grad():
            for start in range(0, len(test), 8):
                batch = test[start:start + 8]
                for row, output in zip(batch, model.forward_batch([pilot.encode_row(model, tok, r, "pol2_sft") for r in batch])):
                    action, probs = pilot.action_for(output[0], row["options"])
                    pred.append({"id": row["id"], "typed_state": row["typed_state"],
                                 "factor_deviations": prior.factor_deviations(tuple(row["typed_state"])),
                                 "variant": int(row["id"].split("-")[1]), "predicted_action": action,
                                 "policy_action": row["policy_action"], "eligible_actions": row["eligible_actions"],
                                 "probabilities": probs})
        rec.update(test=prior.metric(pred), predictions=pred, seed=seed,
                   arm="pol2_structured_pairwise", pairwise_weight=PAIRWISE_WEIGHT,
                   pairwise_margin=PAIRWISE_MARGIN)
        runs.append(rec)
        del model
        torch.cuda.empty_cache() if args.device.startswith("cuda") else None
    old = json.loads(PRIOR_RESULTS.read_text(encoding="utf-8"))
    old_arm = old["arm_summary"]["pol2_sft"]
    metrics = [r["test"] for r in runs]
    summary = {
        "baseline_pol2_sft_prior_experiment": {
            "mean_contract_exact": old_arm["mean_contract_exact"],
            "mean_admissible": old_arm["mean_admissible"],
            "mean_unauthorized_transfer": old_arm["mean_unauthorized_transfer"],
            "mean_false_done": old_arm["mean_false_done"],
            "seed_metrics": old_arm["seed_metrics"],
        },
        "structured_pairwise": {
            "mean_contract_exact": statistics.mean(m["contract_exact"] for m in metrics),
            "mean_admissible": statistics.mean(m["admissible"] for m in metrics),
            "mean_unauthorized_transfer": statistics.mean(m["unauthorized_transfer"] for m in metrics),
            "mean_false_done": statistics.mean(m["false_done"] for m in metrics),
            "seed_metrics": metrics,
        },
    }
    summary["delta_structured_minus_baseline"] = {
        k: summary["structured_pairwise"][f"mean_{k}"] - summary["baseline_pol2_sft_prior_experiment"][f"mean_{k}"]
        for k in ("contract_exact", "admissible", "unauthorized_transfer", "false_done")
    }
    payload = {
        "experiment": "Exploratory pairwise structured-loss follow-up on PoL2 contract composition",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "design": {
            "scope": "narrow synthetic operationalization, contract v0.2; not complete PoL2",
            "status": "exploratory follow-up; the reused test lattice and predictions were already public before this objective was chosen",
            "training_change": "add pairwise hinge margin to cross-entropy: preferred action > other eligible actions; every eligible action > every ineligible action",
            "pairwise_weight": PAIRWISE_WEIGHT, "pairwise_margin_logits": PAIRWISE_MARGIN,
            "training_rows": len(train), "validation_rows": len(valid), "test_prompts": len(test),
            "same_seeds_as_baseline": args.seeds, "epochs": args.epochs,
            "model_selection": "minimum validation target NLL, same rule as baseline",
            "limitations": [
                "The test is reused from a public prior experiment; this is not independent confirmation and no hyperparameter was selected on its scores.",
                "Only the finite synthetic contract v0.2 state lattice is tested; not the full PoL2 theory or a physical robot.",
                "Labels and the admissible set share the same operationalization; there is no independent normative ground truth.",
                "The test lattice contains no held-out positive transfer target.",
                "Three matched seeds are descriptive; they do not establish a population-level causal effect.",
            ],
        },
        "summary": summary,
        "runs": runs,
        "runtime": {"device": torch.cuda.get_device_name(0) if args.device.startswith("cuda") else args.device,
                    "torch": torch.__version__, "elapsed_seconds": time.perf_counter() - started,
                    "elapsed_scope": "training and evaluation"},
    }
    (args.output_dir / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": summary, "elapsed_seconds": payload["runtime"]["elapsed_seconds"]}, ensure_ascii=False, indent=2), flush=True)

if __name__ == "__main__":
    main()
