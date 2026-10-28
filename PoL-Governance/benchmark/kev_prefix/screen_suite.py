#!/usr/bin/env python3
"""按 20GB 卡可执行性筛掉「超长 row」记录，产出评测用 suite（仓库外）。

背景：本机 RX 7900 XT 20GB + 无 flash-linear-attention 的 exact eager 路径下，row（state+单问题 branch）
超过 ~2k tokens 时 eager attention 的 L×L 缓冲会 OOM（实测 max_row 4,733 的 holdout/6056 触发 HIP OOM）。
主口径（共同上下文 384/1024/2048）的所有记录 row ≤1,024，不受影响；只有 serving 敏感性里的极少数长文档
需要剔除，并作为「本机不可评测项」如实计数（不做静默截断、不换 kernel）。

实现：完全走 Kev 路径（load_split + materialize + encode），max_row = len(state) + max(len(question row))。

用法（WSL，cd ~；PYTHONPATH=~/src/kev，项目 venv）：
  python benchmark/kev_prefix/screen_suite.py --suite-dir <仓库外>/suite --join <仓库外>/join.jsonl \
    --out-suite <仓库外>/suite-eval --out-join <仓库外>/join-eval.jsonl \
    --max-row-tokens 2048 --out-report <仓库外>/screening-report.json
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from kev.data import materialize
from kev.model import encode, load_tokenizer, rows_of
from kev.suite import load_split, read_manifest


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--join", type=Path, required=True)
    parser.add_argument("--out-suite", type=Path, required=True)
    parser.add_argument("--out-join", type=Path, required=True)
    parser.add_argument("--max-row-tokens", type=int, default=2048)
    parser.add_argument("--base", default="Qwen/Qwen3.5-4B-Base")
    parser.add_argument("--revision", default="1001bb4d826a52d1f399e183466143f4da7b741b")
    parser.add_argument("--out-report", type=Path, required=True)
    args = parser.parse_args()
    manifest = read_manifest(str(args.suite_dir))
    context = manifest.get("context", {})
    tokenizer = load_tokenizer(args.base, revision=args.revision)
    records = load_split(str(args.suite_dir), "development")
    lengths = {}
    excluded_clean = set()
    for record in records:
        internal = materialize(record)
        enc = encode(tokenizer, internal, max_state=context.get("max_state", 65536),
                     max_branch=context.get("max_branch", 73728), strict=True)
        state, _, rows = rows_of(enc)
        max_row = len(state) + max(len(row["ids"]) for row in rows)
        lengths[record["_meta"]["id"]] = {"variant": record["_meta"]["variant"],
                                          "parent": record["_meta"].get("parent_id"),
                                          "max_row": max_row, "packed": len(enc["ids"])}
        if record["_meta"]["variant"] == "clean" and max_row > args.max_row_tokens:
            excluded_clean.add(record["_meta"]["id"])
    excluded = set()
    for record_id, info in lengths.items():
        if info["variant"] == "clean" and record_id in excluded_clean:
            excluded.add(record_id)
        elif info["parent"] and info["parent"] in excluded_clean:
            excluded.add(record_id)
    kept_records = [record for record in records if record["_meta"]["id"] not in excluded]
    kept = [json.loads(line) for line in args.join.read_text(encoding="utf-8").splitlines() if line.strip()]
    kept_join = [row for row in kept if row["id"] not in excluded]
    excluded_questions = sum(len(row["questions"]) for row in kept if row["id"] in excluded and row["variant"] == "clean")
    args.out_suite.mkdir(parents=True, exist_ok=True)
    data_lines = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in kept_records)
    (args.out_suite / "development.jsonl").write_text(data_lines, encoding="utf-8")
    out_manifest = json.loads(json.dumps(manifest))
    out_manifest["files"] = dict(manifest.get("files", {}))
    out_manifest["files"]["development.jsonl"] = {"sha256": sha256_file(args.out_suite / "development.jsonl"),
                                                  "records": len(kept_records)}
    out_manifest["screening"] = {
        "max_row_tokens": args.max_row_tokens,
        "reason": "RX 7900 XT 20GB + exact eager path cannot hold the L x L attention buffer for longer rows",
        "excluded_clean_records": len(excluded_clean),
        "excluded_records_total": len(excluded),
        "excluded_clean_questions": excluded_questions,
        "excluded_max_row_range": [min((lengths[r]["max_row"] for r in excluded_clean), default=None),
                                   max((lengths[r]["max_row"] for r in excluded_clean), default=None)],
        "source_suite_manifest_sha256": sha256_file(args.suite_dir / "manifest.json"),
    }
    (args.out_suite / "manifest.json").write_text(json.dumps(out_manifest, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
    args.out_join.parent.mkdir(parents=True, exist_ok=True)
    args.out_join.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in kept_join), encoding="utf-8")
    report = {
        "schema": "kev-prefix-screening/1",
        "max_row_tokens": args.max_row_tokens,
        "records_in": len(records), "records_kept": len(kept_records),
        "records_excluded": len(excluded), "excluded_by_variant": dict(Counter(lengths[r]["variant"] for r in excluded)),
        "excluded_clean_records": len(excluded_clean), "excluded_clean_questions": excluded_questions,
        "kept_by_variant": dict(Counter(record["_meta"]["variant"] for record in kept_records)),
        "max_row_kept": max(lengths[r]["max_row"] for r in lengths if r not in excluded),
        "max_packed_kept": max(lengths[r]["packed"] for r in lengths if r not in excluded),
        "excluded_max_row": sorted(lengths[r]["max_row"] for r in excluded if lengths[r]["variant"] == "clean"),
        "suite_manifest_sha256": sha256_file(args.out_suite / "manifest.json"),
        "join_sha256": sha256_file(args.out_join),
    }
    args.out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
