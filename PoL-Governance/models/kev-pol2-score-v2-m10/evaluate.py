#!/usr/bin/env python3
"""Evaluate a released POL2 Kev checkpoint on labelled score JSONL."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from kev.api import question_keys
from kev.data import load_records
from kev.predictors import LocalPredictor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    predictor = LocalPredictor(
        str(args.run), args.device,
        context={"max_state": 4096, "max_branch": 4096, "max_packed": 8192},
    )
    total = 0
    correct = 0
    by_type = Counter()
    by_type_correct = Counter()
    items = []
    for record in load_records(args.data):
        prediction = predictor(record)
        for qid, question in record["questions"].items():
            keys = question_keys(question["type"], question.get("criteria"))
            probabilities = prediction["probabilities"][qid]
            answer = max(keys, key=lambda key: probabilities[key])
            gold = question["label"]
            if question["type"] == "noul" and isinstance(gold, bool):
                gold = "true" if gold else "false"
            hit = str(answer) == str(gold)
            total += 1
            correct += int(hit)
            by_type[question["type"]] += 1
            by_type_correct[question["type"]] += int(hit)
            items.append({
                "case_id": record.get("case_id"), "unit_id": record.get("unit_id"), "qid": qid,
                "type": question["type"], "gold": gold, "prediction": answer,
                "correct": hit, "probabilities": {key: probabilities[key] for key in keys},
            })
    result = {
        "rows": total, "accuracy": correct / total if total else 0.0,
        "by_type": {kind: {"rows": by_type[kind], "accuracy": by_type_correct[kind] / by_type[kind]} for kind in sorted(by_type)},
        "items": items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("rows", "accuracy", "by_type")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
