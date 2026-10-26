"""Exploratory test of state-balanced checkpoint selection for PoL2 SFT."""
from __future__ import annotations
import json, random, statistics, sys, time
from datetime import datetime, timezone
from pathlib import Path
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_rule_composition_generalization as prior
import run_kev_pol2_internalization as pilot

OUT = HERE / "results" / "kev-pol2-balanced-validation-20261026"
PRIOR_RESULTS = HERE / "results" / "kev-pol2-rule-composition-20261026" / "results.json"
SEEDS = (20261026, 20261027, 20261028)

def state_balanced(rows):
    groups = {}
    for row in rows:
        groups.setdefault(tuple(row["typed_state"]), []).append(row)
    if len(groups) != 10:
        raise RuntimeError(f"Expected 10 train/validation-supported states, got {len(groups)}")
    n = min(map(len, groups.values()))
    selected = []
    for state, group in sorted(groups.items(), key=lambda x: str(x[0])):
        rng = random.Random(9001 + sum(map(ord, "|".join(map(str, state)))))
        group = list(group)
        rng.shuffle(group)
        selected.extend(group[:n])
    return selected

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
    from kev.checkpoint import Checkpoint
    initial = Checkpoint(pilot.INITIAL_CHECKPOINT)
    tok = initial.load_tokenizer() if hasattr(initial, "load_tokenizer") else None
    if tok is None:
        from kev.model import load_tokenizer
        tok = load_tokenizer(pilot.BASE_ID, revision=pilot.BASE_REVISION)
    train, valid_all, test = prior.build_data()
    valid = state_balanced(valid_all)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train_used", train), ("validation_state_balanced", valid), ("composition_test", test)):
        prior.write_jsonl(args.output_dir / f"{name}.jsonl", rows)
    runs, started = [], time.perf_counter()
    for seed in args.seeds:
        out = args.output_dir / "adapters" / f"seed-{seed}"
        print(f"[balanced-validation] seed={seed} rows={len(train)} validation={len(valid)} test={len(test)}", flush=True)
        rec = pilot.train_one(seed, "pol2_sft", train, valid, out, initial, tok, args.device,
                              epochs=args.epochs, batch_size=args.batch_size)
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
        rec.update(test=prior.metric(pred), predictions=pred, seed=seed, arm="pol2_sft_state_balanced_validation")
        runs.append(rec)
        del model
        if args.device.startswith("cuda"):
            torch.cuda.empty_cache()
    old = json.loads(PRIOR_RESULTS.read_text(encoding="utf-8"))["arm_summary"]["pol2_sft"]
    metrics = [r["test"] for r in runs]
    summary = {
        "baseline_pol2_sft_prior_experiment": {k: old[k] for k in
            ("mean_contract_exact", "mean_admissible", "mean_unauthorized_transfer", "mean_false_done", "seed_metrics")},
        "state_balanced_validation": {
            "mean_contract_exact": statistics.mean(m["contract_exact"] for m in metrics),
            "mean_admissible": statistics.mean(m["admissible"] for m in metrics),
            "mean_unauthorized_transfer": statistics.mean(m["unauthorized_transfer"] for m in metrics),
            "mean_false_done": statistics.mean(m["false_done"] for m in metrics),
            "seed_metrics": metrics,
        },
    }
    summary["delta_balanced_minus_baseline"] = {
        k: summary["state_balanced_validation"][f"mean_{k}"] - summary["baseline_pol2_sft_prior_experiment"][f"mean_{k}"]
        for k in ("contract_exact", "admissible", "unauthorized_transfer", "false_done")}
    payload = {
        "experiment": "Exploratory state-balanced checkpoint selection for PoL2 contract SFT",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "design": {
            "scope": "narrow synthetic operationalization, contract v0.2; not complete PoL2",
            "status": "exploratory follow-up; test lattice and prior scores were public before this selection rule was chosen",
            "training_change": "checkpoint selected by mean validation NLL with exactly equal representation for each of 10 supported typed states (5 rows/state)",
            "training_loss": "ordinary four-way preferred-action cross-entropy; unchanged",
            "training_rows": len(train), "validation_rows_before_balancing": len(valid_all),
            "validation_rows_after_balancing": len(valid), "validation_state_counts": {str(s): sum(tuple(r['typed_state']) == s for r in valid) for s in sorted({tuple(r['typed_state']) for r in valid}, key=str)},
            "test_prompts": len(test), "same_seeds_as_baseline": args.seeds, "epochs": args.epochs,
            "limitations": [
                "The test was already public and previously examined; this is exploratory, not independent confirmation.",
                "Only the finite synthetic contract v0.2 lattice is tested; not complete PoL2 or physical robotics.",
                "Labels and legal-action sets derive from one operationalization, not independent normative ground truth.",
                "The lattice contains no held-out positive transfer target.",
                "Three seeds are descriptive and insufficient for a population-level causal claim.",
            ],
        },
        "summary": summary, "runs": runs,
        "runtime": {"device": torch.cuda.get_device_name(0) if args.device.startswith("cuda") else args.device,
                    "torch": torch.__version__, "elapsed_seconds": time.perf_counter() - started},
    }
    (args.output_dir / "results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": summary, "elapsed_seconds": payload["runtime"]["elapsed_seconds"]}, ensure_ascii=False, indent=2), flush=True)

if __name__ == "__main__":
    main()
