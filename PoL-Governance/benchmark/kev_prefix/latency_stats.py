#!/usr/bin/env python3
"""从 Kev predictions.jsonl 提取延迟/输入 token 聚合（只输出统计，不含 id 或正文）。

用于 CPU 冒烟旁表（Ryzen 5700X / fp32 / 参考 kernel）与 GPU run 的逐记录延迟核对；
GPU 主延迟以 report.json 的 latency_ms 为准（本脚本可交叉核对）。

用法：
  python benchmark/kev_prefix/latency_stats.py --predictions <run>/predictions.jsonl --out <仓库外>/latency.json
"""
import argparse
import json
import statistics
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", default="")
    args = parser.parse_args()
    latencies, tokens = [], []
    with args.predictions.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            prediction = row.get("prediction") or {}
            if "latency_ms" in prediction:
                latencies.append(float(prediction["latency_ms"]))
            if "input_tokens" in prediction:
                tokens.append(int(prediction["input_tokens"]))
    if not latencies:
        raise SystemExit("no latency_ms in predictions")
    ordered = sorted(latencies)
    report = {
        "schema": "kev-prefix-latency/1",
        "label": args.label,
        "records": len(latencies),
        "latency_ms": {"p50": round(statistics.median(ordered), 3),
                       "p95": round(ordered[max(0, int(0.95 * len(ordered)) - 1)], 3),
                       "mean": round(sum(ordered) / len(ordered), 3),
                       "min": round(ordered[0], 3), "max": round(ordered[-1], 3)},
        "input_tokens": {"mean": round(sum(tokens) / len(tokens), 1) if tokens else None,
                         "p95": sorted(tokens)[max(0, int(0.95 * len(tokens)) - 1)] if tokens else None,
                         "max": max(tokens) if tokens else None},
        "tokens_per_s": round(1000.0 * sum(tokens) / sum(ordered), 1) if tokens else None,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
