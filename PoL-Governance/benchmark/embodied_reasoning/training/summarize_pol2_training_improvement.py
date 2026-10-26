"""Create a transparent, per-seed comparison table from the ablation outputs."""
from __future__ import annotations
import json, statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
OUT = RESULTS / "pol2-training-improvement-comparison-20261026.json"
ACTIONS = ("inspect", "wait", "done")
CONDITIONS = (
    ("2 epochs, CE, original validation", "kev-pol2-rule-composition-20261026/results.json", "pol2_sft"),
    ("2 epochs, pairwise structured loss", "kev-pol2-structured-loss-20261026/results.json", "pol2_structured_pairwise"),
    ("2 epochs, state-balanced validation", "kev-pol2-balanced-validation-20261026/results.json", "pol2_sft_state_balanced_validation"),
    ("4 epochs, state-balanced validation", "kev-pol2-4epoch-balanced-validation-20261026/results.json", "pol2_sft_state_balanced_validation"),
    ("6 epochs, state-balanced validation", "kev-pol2-6epoch-balanced-validation-20261026/results.json", "pol2_sft_state_balanced_validation"),
)

def row_metrics(run):
    predictions = run["predictions"]
    n = len(predictions)
    per_action = {}
    for action in ACTIONS:
        group = [p for p in predictions if p["policy_action"] == action]
        per_action[action] = {
            "n_per_seed": len(group),
            "exact": sum(p["predicted_action"] == action for p in group) / len(group),
        }
    test = run["test"]
    return {
        "n_prompts": n,
        "contract_exact": test["contract_exact"],
        "macro_action_exact": statistics.mean(per_action[a]["exact"] for a in ACTIONS),
        "admissible": test["admissible"],
        "unauthorized_transfer": test["unauthorized_transfer"],
        "false_done": test["false_done"],
        "per_action": per_action,
    }

def main():
    conditions = []
    for label, relative, arm in CONDITIONS:
        data = json.loads((RESULTS / relative).read_text(encoding="utf-8"))
        runs = [r for r in data["runs"] if r.get("arm") == arm]
        seed_metrics = [row_metrics(r) for r in runs]
        keys = ("contract_exact", "macro_action_exact", "admissible", "unauthorized_transfer", "false_done")
        means = {k: statistics.mean(m[k] for m in seed_metrics) for k in keys}
        per_action_means = {a: statistics.mean(m["per_action"][a]["exact"] for m in seed_metrics) for a in ACTIONS}
        conditions.append({"condition": label, "arm": arm, "seeds": [r["seed"] for r in runs],
                           "seed_metrics": seed_metrics, "mean": means, "per_action_mean": per_action_means})
    baseline = conditions[0]["mean"]
    for condition in conditions:
        condition["delta_vs_baseline"] = {k: condition["mean"][k] - baseline[k]
                                           for k in baseline}
    payload = {
        "experiment": "Exploratory matched-seed PoL2 typed-action training ablations",
        "test_reuse": "All conditions use the previously public 134-state, two-phrase composition test. Treat this as exploratory method development, not an untouched confirmatory holdout.",
        "sample_unit": "268 prompts per seed = 134 unique typed states x 2 phrasings; prompts are paired within state and are not independent state draws.",
        "metrics": {
            "contract_exact": "micro accuracy across all test prompts",
            "macro_action_exact": "unweighted mean of exact rates for inspect, wait, done",
            "admissible": "fraction predicted action in the frozen contract's eligible set",
            "unauthorized_transfer": "fraction of all prompts with an ineligible transfer prediction",
            "false_done": "fraction of all prompts with done while terminal predicate is false",
        },
        "conditions": conditions,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT)
    for condition in conditions:
        m = condition["mean"]
        print(f"{condition['condition']}: exact={m['contract_exact']:.4f}, macro={m['macro_action_exact']:.4f}, admissible={m['admissible']:.4f}; per-action={condition['per_action_mean']}")

if __name__ == "__main__":
    main()
