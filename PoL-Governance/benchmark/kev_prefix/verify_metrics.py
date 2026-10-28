#!/usr/bin/env python3
"""用 Kev 官方指标实现交叉核对 aggregate.py 的指标（同一 rows.json，逐步比较）。

为什么：aggregate.py 是纯标准库重写；本脚本在同一份 Kev benchmark rows.json 上分别调用
kev.metrics.metrics 与本仓库 aggregate.metrics，报告 acc/brier/nll/ece_10 的差值。
若差值超过 1e-9 说明我们的口径偏离，必须在结果卡前修正。

用法（WSL，cd ~；PYTHONPATH=~/src/kev，项目 venv）：
  python benchmark/kev_prefix/verify_metrics.py --rows <run>/rows.json
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_aggregate():
    spec = importlib.util.spec_from_file_location("kev_prefix_aggregate", REPO / "benchmark" / "kev_prefix" / "aggregate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()
    from kev.metrics import metrics as kev_metrics
    rows = json.loads(args.rows.read_text(encoding="utf-8"))
    clean = [row for row in rows if row.get("variant") == "clean" and row.get("source") != "unknowable"]
    if not clean:
        raise SystemExit("no clean rows")
    official = kev_metrics(clean)
    ours = load_aggregate().metrics(clean)
    keys = ("acc", "brier", "nll", "ece_10")
    problems = []
    out = {"n": len(clean), "official": {k: official.get(k) for k in keys} | {"ece": official.get("ece")},
           "ours": {k: ours.get(k) for k in keys}}
    for key, official_key in (("acc", "acc"), ("brier", "brier"), ("nll", "nll"), ("ece_10", "ece")):
        delta = abs(float(ours[key]) - float(official[official_key]))
        out.setdefault("delta", {})[key] = delta
        if delta > args.tolerance:
            problems.append((key, delta))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if problems:
        print("MISMATCH:", problems, file=sys.stderr)
        return 2
    print("OK: aggregate metrics match kev.metrics within", args.tolerance)
    return 0


if __name__ == "__main__":
    sys.exit(main())
