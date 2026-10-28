#!/usr/bin/env python3
"""CPU 延迟基准（Session B 要求的 CPU 成本/延迟口径）。

只用**公开** validation 子集（非私有），避免把保留集用于任何成本测量。
固定模型与输入记录后测 batch=1 单记录延迟（p50/p95）、输入 token 数与 tokens/s；加载时间单列。

用法（WSL；CPU，不需要静默时段，但同一时间不要与 GPU 任务并发）：
  python benchmark/kev_prefix/cpu_latency.py --run jaredpalmer/kev-4b@v1.0 \
      --data <仓库外>/public-smoke.jsonl --n 24 --out <仓库外>/cpu-latency-kev-original.json
"""
import argparse
import json
import statistics
import time
from pathlib import Path

from kev.checkpoint import LoadOptions
from kev.data import load_records
from kev.model import SERVING_CONTEXT_8K
from kev.predictors import LocalPredictor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--data", type=Path, required=True, help="public labelled requests JSONL (non-private)")
    parser.add_argument("--n", type=int, default=24)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", default="")
    args = parser.parse_args()
    records = load_records(args.data)[: args.n]
    if len(records) <= args.warmup:
        raise SystemExit("need more records than warmup")
    options = LoadOptions.from_env()          # CPU 用 KEV_DTYPE=fp32（默认）保持 exact path
    started = time.perf_counter()
    predictor = LocalPredictor(args.run, "cpu", options, context=SERVING_CONTEXT_8K)
    load_seconds = time.perf_counter() - started
    latencies, tokens = [], []
    for index, record in enumerate(records):
        prediction = predictor(record)
        if index >= args.warmup:
            latencies.append(prediction["latency_ms"])
            tokens.append(prediction["input_tokens"])
    total_ms = sum(latencies)
    report = {
        "schema": "kev-prefix-cpu-latency/1",
        "run": args.run,
        "label": args.label,
        "device": "cpu",
        "dtype": str(options.dtype or "float32"),
        "policy": "batch=1, one record per call, warmup excluded, public validation smoke set (non-private)",
        "records": len(latencies),
        "load_seconds": round(load_seconds, 3),
        "latency_ms": {"p50": round(statistics.median(latencies), 3),
                       "p95": round(sorted(latencies)[max(0, int(0.95 * len(latencies)) - 1)], 3),
                       "mean": round(total_ms / len(latencies), 3),
                       "min": round(min(latencies), 3), "max": round(max(latencies), 3)},
        "input_tokens": {"mean": round(sum(tokens) / len(tokens), 1), "max": max(tokens)},
        "tokens_per_s": round(1000.0 * sum(tokens) / total_ms, 1),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
