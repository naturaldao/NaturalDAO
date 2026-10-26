"""Score task-specific predictions without pooling distinct knowledge types."""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data-v1.3"
DEFAULT_RUNS = HERE / "runs-20261026-v1.3"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def score_predictions(preds: list[dict], items: dict[str, dict], labels: dict[str, dict]) -> dict:
    if not preds:
        return {"model": None, "condition": None, "n_predictions": 0, "error": "empty prediction file"}
    typ = preds[0]["knowledge_type"]
    expected = {item_id: row for item_id, row in items.items() if row["knowledge_type"] == typ}
    pred_by_id = {}
    duplicates = []
    for p in preds:
        if p["id"] in pred_by_id:
            duplicates.append(p["id"])
        pred_by_id[p["id"]] = p
    missing_ids = sorted(set(expected) - set(pred_by_id))
    extra_ids = sorted(set(pred_by_id) - set(expected))
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    errors = Counter()
    for item_id, item in expected.items():
        p = pred_by_id.get(item_id)
        label = labels[item_id]
        ok = p is not None and p.get("execution_status") == "ok" and p.get("prediction") is not None
        exact = ok and p["prediction"] == label["answer"]
        gold = set(label["answer"].split("|"))
        predicted = set(p["prediction"].split("|")) if ok else set()
        option_n = len(item["options"])
        random_exact = 1 / math.comb(option_n, len(gold)) if len(gold) <= option_n else 0.0
        for key in (item["knowledge_type"], item["task_type"]):
            groups[(key, "all")].append({"exact": bool(exact), "ok": ok, "submitted": p is not None, "gold": gold, "pred": predicted, "label": label, "item": item, "random_exact": random_exact})
        if not ok:
            errors[p.get("execution_status", "unknown") if p else "not_run"] += 1
        if item["knowledge_type"] == "explicit_governance_rules":
            stratum = "has_approved_boundary_reference" if label.get("approved_decisions") else "candidate_mapping_only"
            groups[("rule_label_basis", stratum)].append({"exact": bool(exact), "ok": ok, "submitted": p is not None, "gold": gold, "pred": predicted, "label": label, "item": item, "random_exact": random_exact})
    report_groups = {}
    for (key, _), rows in groups.items():
        correct = sum(x["exact"] for x in rows)
        tp = sum(len(x["gold"] & x["pred"]) for x in rows)
        fp = sum(len(x["pred"] - x["gold"]) for x in rows)
        fn = sum(len(x["gold"] - x["pred"]) for x in rows)
        # Same key may have several subdivisions; aggregate under a stable key.
        report_groups.setdefault(key, {})
        subkey = _ if _ != "all" else None
        metric = {
            "n_expected": len(rows), "n_submitted": sum(x["submitted"] for x in rows), "exact_match_n": correct, "exact_match_rate": correct / len(rows) if rows else None,
            "mean_random_exact_chance": sum(x["random_exact"] for x in rows) / len(rows) if rows else None,
            "execution_ok_n": sum(x["ok"] for x in rows), "missing_or_failed_n": sum(not x["ok"] for x in rows),
            "citation_or_set_micro_precision": tp / (tp + fp) if tp + fp else None,
            "citation_or_set_micro_recall": tp / (tp + fn) if tp + fn else None,
        }
        if subkey is None:
            report_groups[key].update(metric)
        else:
            report_groups[key][subkey] = metric
    return {
        "model": preds[0]["model_requested"],
        "condition": preds[0]["condition"],
        "knowledge_type": typ,
        "n_predictions": len(preds), "n_expected": len(expected),
        "complete": not missing_ids and not extra_ids and not duplicates,
        "missing_ids": missing_ids, "extra_ids": extra_ids, "duplicate_ids": sorted(set(duplicates)),
        "by_type_and_task": report_groups,
        "execution_errors": dict(errors),
        "interpretation": "Exact-match and set-overlap descriptives only; do not average across knowledge types.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    items = {x["id"]: x for x in read_jsonl(DATA / "items.jsonl")}
    labels = {x["id"]: x for x in read_jsonl(DATA / "labels.jsonl")}
    all_results = []
    prediction_files = []
    grouped_predictions: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for path in sorted(args.runs.glob("*.jsonl")):
        prediction_files.append(path)
        rows = read_jsonl(path)
        if rows:
            key = (rows[0]["model_requested"], rows[0]["condition"], rows[0]["knowledge_type"])
            grouped_predictions[key].extend(rows)
    if not all_results:
        if not grouped_predictions:
            raise SystemExit(f"No prediction files found in {args.runs}")
    for _, rows in sorted(grouped_predictions.items()):
        all_results.append(score_predictions(rows, items, labels))
    error_files = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(args.runs.glob("*.error.json"))]
    # Matched-item transitions between closed-book and source-context conditions.
    paired = []
    by_model: dict[str, dict[str, dict[str, dict]]] = defaultdict(lambda: defaultdict(dict))
    for path in prediction_files:
        pred_rows = read_jsonl(path)
        for p in pred_rows:
            if p["execution_status"] == "ok" and p["prediction"] is not None:
                by_model[p["model_requested"]][p["condition"]][p["id"]] = p
    for model, conditions in by_model.items():
        closed = conditions.get("closed_book", {})
        context = conditions.get("source_context", {})
        grouped: dict[str, list[dict]] = defaultdict(list)
        for item_id in set(closed) & set(context):
            item = items[item_id]
            gold = labels[item_id]["answer"]
            grouped[item["knowledge_type"]].append({
                "closed": closed[item_id]["prediction"] == gold,
                "context": context[item_id]["prediction"] == gold,
            })
        for typ, rows in grouped.items():
            transitions = Counter(
                "both_correct" if x["closed"] and x["context"] else
                "context_only_correct" if x["context"] else
                "closed_only_correct" if x["closed"] else "both_wrong"
                for x in rows
            )
            paired.append({"model": model, "knowledge_type": typ, "n_paired": len(rows), "transitions": dict(transitions), "closed_book_accuracy": sum(x["closed"] for x in rows) / len(rows), "source_context_accuracy": sum(x["context"] for x in rows) / len(rows), "net_context_gain_pp": 100 * (sum(x["context"] for x in rows) - sum(x["closed"] for x in rows)) / len(rows)})
    report = {
        "report_kind": "pol2_typed_knowledge_pilot",
        "dataset": json.loads((DATA / "manifest.json").read_text(encoding="utf-8")),
        "runs": all_results,
        "run_errors": error_files,
        "paired_context_comparisons": paired,
        "comparison_limit": "Descriptive matched-item transitions only; the public pilot is small, non-sealed, and labels are source-derived annotations rather than complete normative gold.",
    }
    output = args.output or args.runs / "summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "runs": [{"model": x["model"], "condition": x["condition"], "n": x["n_predictions"]} for x in all_results]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
