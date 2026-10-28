#!/bin/bash
# 生成 Kev 前后对照评测所需的评测端文件（全部在仓库外）。
# 用法：bash benchmark/kev_prefix/prepare_eval.sh
# 说明：私有保留集只复制到 $PRIV（仓库外，中性文件名）；本脚本只打印聚合计数，不打印任何条目正文/id。
set -euo pipefail
cd "$HOME"   # 避免仓库目录 shadow 掉 PyPI 的 datasets 等包
REPO="/mnt/c/Projects/DAism/NaturalDAO/PoL-Governance"
PRIV="${PRIV_DIR:-/home/wenbo/priv-eval}"
ITEMS_SRC="$REPO/datasets/general/data/hf-export/private-holdout/benchmark.jsonl"
ITEMS="$PRIV/items.jsonl"

mkdir -p "$PRIV"
if [ ! -f "$ITEMS" ]; then
  cp "$ITEMS_SRC" "$ITEMS"
  echo "copied private items to neutral location (outside repo): $ITEMS"
else
  echo "private items already staged: $ITEMS"
fi

python3 "$REPO/benchmark/kev_prefix/convert.py" \
  --items "$ITEMS" \
  --out-records "$PRIV/records.jsonl" \
  --sidecar "$PRIV/sidecar.jsonl" \
  --manifest "$PRIV/convert-manifest.json"

python3 "$REPO/benchmark/kev_prefix/build_suite.py" \
  --records "$PRIV/records.jsonl" \
  --sidecar "$PRIV/sidecar.jsonl" \
  --out-suite "$PRIV/suite" \
  --out-join "$PRIV/join.jsonl" \
  --manifest "$PRIV/suite/manifest.json" \
  --permuted-sample 600 \
  --isolation

python3 - <<'PY'
import json, hashlib, pathlib
priv = pathlib.Path("/home/wenbo/priv-eval")
manifest = json.loads((priv / "suite" / "manifest.json").read_text(encoding="utf-8"))
convert = json.loads((priv / "convert-manifest.json").read_text(encoding="utf-8"))
items = priv / "items.jsonl"
print(json.dumps({
    "private_items_sha256": hashlib.sha256(items.read_bytes()).hexdigest(),
    "items_bytes": items.stat().st_size,
    "convert": {k: convert[k] for k in ("records_out", "questions_out", "questions_primary",
                                        "questions_overlong_flagged", "skipped")},
    "suite": {"clean_records": manifest["counts"]["clean_records"],
              "clean_questions": manifest["counts"]["clean_questions"],
              "permuted_records": manifest["counts"]["permuted_records"],
              "isolation_records": manifest["counts"]["isolation_records"],
              "suite_records": manifest["files"]["development.jsonl"]["records"]},
    "suite_manifest_sha256": hashlib.sha256((priv / "suite" / "manifest.json").read_bytes()).hexdigest(),
}, ensure_ascii=False, indent=2))
PY