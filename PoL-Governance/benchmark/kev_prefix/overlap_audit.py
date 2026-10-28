#!/usr/bin/env python3
"""数据重叠审计：私有评测集 vs M10 训练/回放数据（只输出计数与 digest，绝不输出正文）。

用途（专家 P0）：Kev 专项数据不同于 general v5 不能证明无污染/无重叠。本脚本按
规范化 state 的 sha256 与 (state,instructions) 的 sha256 做精确重叠计数，结果只含计数。

用法（WSL/Windows 均可，纯标准库）：
  python benchmark/kev_prefix/overlap_audit.py --holdout-items <私有 items.jsonl> \
      --candidate <release 训练/回放 jsonl> [--candidate ...] --out <仓库外>/overlap-audit.json
"""
import argparse
import hashlib
import json
from pathlib import Path


def normalise(text):
    return " ".join(str(text).casefold().split())


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def state_text(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def iter_jsonl(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def holdout_sets(path):
    states, pairs, item_ids = set(), set(), set()
    rows = 0
    for item in iter_jsonl(path):
        rows += 1
        if item.get("id"):
            item_ids.add(str(item["id"]))
        base = normalise(state_text(item.get("state")))
        states.add(sha(base))
        for question in item.get("questions") or []:
            if isinstance(question, dict):
                pairs.add(sha(base + "\x00" + normalise(question.get("prompt") or "")))
    return {"rows": rows, "states": states, "pairs": pairs, "item_ids": item_ids}


def candidate_sets(path):
    states, pairs, ids = set(), set(), set()
    rows = 0
    for row in iter_jsonl(path):
        rows += 1
        for key in ("case_id", "unit_id", "source_qid"):
            if row.get(key):
                ids.add(str(row[key]))
                break
        base = normalise(state_text(row.get("state")))
        states.add(sha(base))
        questions = row.get("questions")
        if isinstance(questions, dict):
            for question in questions.values():
                if isinstance(question, dict):
                    pairs.add(sha(base + "\x00" + normalise(question.get("instructions") or "")))
        elif isinstance(questions, list):
            for question in questions:
                if isinstance(question, dict):
                    pairs.add(sha(base + "\x00" + normalise(question.get("instructions") or "")))
    return {"rows": rows, "states": states, "pairs": pairs, "ids": ids}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout-items", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    holdout = holdout_sets(args.holdout_items)
    report = {"schema": "kev-prefix-overlap-audit/1",
              "holdout": {"rows": holdout["rows"],
                          "items_sha256": sha256_file(args.holdout_items)},
              "candidates": {}, "summary": {"any_exact_overlap": False}}
    for path in args.candidate:
        candidate = candidate_sets(path)
        state_overlap = holdout["states"] & candidate["states"]
        pair_overlap = holdout["pairs"] & candidate["pairs"]
        id_overlap = holdout["item_ids"] & candidate["ids"]
        report["candidates"][str(path)] = {
            "rows": candidate["rows"],
            "sha256": sha256_file(path),
            "holdout_states_matched": len(state_overlap),
            "holdout_questions_matched": len(pair_overlap),
            "holdout_item_ids_matched": len(id_overlap),
            "candidate_rows_sha256_unique": len(candidate["states"]),
        }
        if state_overlap or pair_overlap or id_overlap:
            report["summary"]["any_exact_overlap"] = True
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for path, values in report["candidates"].items():
        print(path, "rows", values["rows"], "state_match", values["holdout_states_matched"],
              "question_match", values["holdout_questions_matched"],
              "id_match", values["holdout_item_ids_matched"])


if __name__ == "__main__":
    main()
