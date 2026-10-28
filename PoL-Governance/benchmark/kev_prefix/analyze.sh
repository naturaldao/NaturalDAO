#!/bin/bash
# 评测后分析与交叉核对（CPU，可反复重跑）。前置：run_models.sh 已产出 runs/* 与 aggregate-{primary,extended,full}.json。
# 用法：bash benchmark/kev_prefix/analyze.sh
set -euo pipefail
cd "$HOME"
REPO="/mnt/c/Projects/DAism/NaturalDAO/PoL-Governance"
PRIV="${PRIV_DIR:-/home/wenbo/priv-eval}"
source "$HOME/src/polgov/.venv/bin/activate"
export PYTHONPATH="$HOME/src/kev"

for name in kev-original seed43 seed17 seed29; do
  run="$PRIV/runs/$name"
  [ -d "$run" ] || continue
  echo "== verify metrics vs kev.metrics: $name =="
  python "$REPO/benchmark/kev_prefix/verify_metrics.py" --rows "$run/rows.json" \
    | sed '/^OK:/d' > "$PRIV/runs/$name/verify-metrics.json"
  tail -2 "$PRIV/runs/$name/verify-metrics.json"
done

for variant in primary extended full; do
  [ -f "$PRIV/aggregate-$variant.json" ] || continue
  python "$REPO/benchmark/kev_prefix/report_tables.py" --aggregate "$PRIV/aggregate-$variant.json" \
    > "$PRIV/tables-$variant.md"
  echo "tables-$variant.md:"; wc -l "$PRIV/tables-$variant.md"
done

python - "$PRIV" "$REPO" <<'PY'
import json, sys
from pathlib import Path
priv = Path(sys.argv[1])
summary = {"aggregates": {}, "verify_metrics": {}, "environment": {}, "training_context": None}
for variant in ("primary", "extended", "full"):
    path = priv / f"aggregate-{variant}.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        summary["aggregates"][variant] = {
            "settings": data.get("settings"),
            "suite": data.get("suite"),
            "runs": {name: {"n": run["served"]["overall"]["n"],
                            "clusters": run["coverage"]["clusters"],
                            "acc": run["served"]["overall"]["acc"],
                            "brier": run["served"]["overall"]["brier"],
                            "nll": run["served"]["overall"]["nll"],
                            "ece_10": run["served"]["overall"].get("ece_10"),
                            "ece_15": run["served"]["overall"].get("ece_15"),
                            "coverage_at_5pct_error": run["served"]["overall"].get("coverage_at_5pct_error"),
                            "temperature": run["run_metadata"].get("temperature"),
                            "latency_ms": run["run_metadata"].get("latency_ms"),
                            "suite_sha256": run["run_metadata"].get("suite_sha256")}
                     for name, run in data["runs"].items()},
            "paired": data.get("paired"),
            "variants": data.get("variants"),
        }
for run_dir in sorted((priv / "runs").glob("*/verify-metrics.json")):
    try:
        summary["verify_metrics"][run_dir.parent.name] = json.loads(run_dir.read_text(encoding="utf-8"))
    except Exception as error:
        summary["verify_metrics"][run_dir.parent.name] = {"error": str(error)}
for run_dir in sorted((priv / "runs").glob("*/report.json")):
    report = json.loads(run_dir.read_text(encoding="utf-8"))
    summary["environment"][run_dir.parent.name] = {
        "environment": report.get("environment"), "calibration": report.get("calibration"),
        "coverage": report.get("coverage"), "latency_ms": report.get("latency_ms"),
        "suite_sha256": report.get("suite_sha256"), "date_facts": report.get("date_facts"),
        "rotations": report.get("rotations")}
stats = priv / "training-context-stats.json"
if stats.is_file():
    summary["training_context"] = json.loads(stats.read_text(encoding="utf-8"))
(priv / "analysis-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("analysis-summary.json:", sum(len(v) for v in summary["aggregates"].values()))
PY
echo "done: $PRIV/analysis-summary.json, $PRIV/tables-*.md"