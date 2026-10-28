#!/usr/bin/env python3
"""计算私有评测集在 **Kev 共同支持上下文** 下的可入子集（主分析口径）与长度分布。

背景（专家裁决 P0）：serving 上限（65k）不等于模型有证据支持的长上下文能力。原版 Kev-4B 以 384/1024/2048
（state/branch/packed）训练；M10 训练配置 max_state=4096（branch 4,736 / packed 5,760）。两者共同有证据的
范围 = 原版默认 384/1024/2048，即 Kev 官方 suite 的 CONTEXT。主表用该子集；serving 全量作为敏感性并报拒绝数。

实现：**完全走 Kev 自己的路径**（kev.data.materialize + kev.model.encode strict），不用手写近似。

输出（仓库外，临时）：
- --out-rids：可入主分析的 rid 列表（一行一个）
- --out-json：聚合统计（记录/问题数、拒绝原因、state token 分位数与分桶）

用法（WSL，cd ~；PYTHONPATH=~/src/kev，项目 venv）：
  python benchmark/kev_prefix/fit_training_context.py --join <仓库外>/join.jsonl \
    --suite-dir <仓库外>/suite --base Qwen/Qwen3.5-4B-Base \
    --revision 1001bb4d826a52d1f399e183466143f4da7b741b \
    --out-rids <仓库外>/rids-training-context.txt --out-json <仓库外>/training-context-stats.json
"""
import argparse
import collections
import json
from pathlib import Path

from kev.data import materialize
from kev.model import MAX_BRANCH, MAX_PACKED, MAX_STATE, encode, load_tokenizer
from kev.suite import load_split


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--join", type=Path, required=True)
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--base", default="Qwen/Qwen3.5-4B-Base")
    parser.add_argument("--revision", default="1001bb4d826a52d1f399e183466143f4da7b741b")
    parser.add_argument("--out-rids", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()
    tokenizer = load_tokenizer(args.base, revision=args.revision)
    join_rows = [json.loads(line) for line in args.join.read_text(encoding="utf-8").splitlines() if line.strip()]
    clean_join = {row["id"]: row for row in join_rows if row["variant"] == "clean"}
    suite = load_split(str(args.suite_dir), "development")
    clean_records = [record for record in suite if record["_meta"]["variant"] == "clean"]
    keep, stats = [], {
        "context": {"max_state": MAX_STATE, "max_branch": MAX_BRANCH, "max_packed": MAX_PACKED},
        "clean_records": len(clean_records), "clean_questions": sum(len(r["questions"]) for r in clean_records),
        "admitted_records": 0, "admitted_questions": 0,
        "admitted_questions_not_overlong": 0,
        "rejected_records": 0, "rejected_questions": 0, "rejected": collections.Counter(),
        "state_tokens": [], "packed_tokens": [],
    }
    for record in clean_records:
        joined = clean_join[record["_meta"]["id"]]
        internal = materialize(record)          # 与 kev.benchmark 完全同一条路径（api_request + to_record）
        try:
            enc = encode(tokenizer, internal, max_state=MAX_STATE, max_branch=MAX_BRANCH, strict=True)
        except Exception as error:              # ContextOverflow: state / branch
            message = str(error)
            key = "branch" if "branch" in message else "state"
            stats["rejected"][key] += 1
            stats["rejected_records"] += 1
            stats["rejected_questions"] += len(record["questions"])
            continue
        if len(enc["ids"]) > MAX_PACKED:
            stats["rejected"]["packed"] += 1
            stats["rejected_records"] += 1
            stats["rejected_questions"] += len(record["questions"])
            continue
        stats["admitted_records"] += 1
        stats["admitted_questions"] += len(record["questions"])
        stats["state_tokens"].append(enc["state_tokens"])
        stats["packed_tokens"].append(len(enc["ids"]))
        for question in joined["questions"]:
            keep.append(question["rid"])
            if not question.get("overlong"):
                stats["admitted_questions_not_overlong"] += 1
    out = dict(stats)
    out["rejected"] = dict(stats["rejected"])
    for name, values in (("state_tokens", stats["state_tokens"]), ("packed_tokens", stats["packed_tokens"])):
        values = sorted(values)
        out[name] = {"n": len(values), "min": values[0], "p50": values[len(values) // 2],
                     "p90": values[int(0.9 * len(values))], "p99": values[int(0.99 * len(values))], "max": values[-1]}
        out[name + "_buckets"] = dict(collections.Counter(
            "<=384" if v <= 384 else "385-1024" if v <= 1024 else "1025-2048" if v <= 2048 else ">2048" for v in values))
    unsafe = [rid for rid in keep if any(ch in rid for ch in ("\n", "\r", "\t", " "))]
    if unsafe:
        raise SystemExit(f"unsafe rids (whitespace): {len(unsafe)}; rebuild sidecar with convert.py")
    if len(set(keep)) != len(keep):
        raise SystemExit("duplicate rids in admitted set")
    args.out_rids.parent.mkdir(parents=True, exist_ok=True)
    args.out_rids.write_text("".join(rid + "\n" for rid in keep), encoding="utf-8")
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("clean_records", "clean_questions", "admitted_records", "admitted_questions",
                                          "admitted_questions_not_overlong", "rejected_records", "rejected_questions",
                                          "rejected", "state_tokens", "state_tokens_buckets")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()