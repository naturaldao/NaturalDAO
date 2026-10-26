#!/usr/bin/env python3
"""Run a released POL2 Kev checkpoint on typed-decision JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from kev.api import question_keys
from kev.data import load_records
from kev.predictors import LocalPredictor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    records = load_records(args.input)
    predictor = LocalPredictor(
        str(args.run), args.device,
        context={"max_state": 4096, "max_branch": 4096, "max_packed": 8192},
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        for record in records:
            prediction = predictor(record)
            answers = {}
            for qid, question in record["questions"].items():
                keys = question_keys(question["type"], question.get("criteria"))
                probabilities = prediction["probabilities"][qid]
                answer = max(keys, key=lambda key: probabilities[key])
                answers[qid] = {"answer": answer, "probabilities": {key: probabilities[key] for key in keys}}
            handle.write(json.dumps({
                "case_id": record.get("case_id"),
                "unit_id": record.get("unit_id"),
                "answers": answers,
                "execution_status": "ok",
            }, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
