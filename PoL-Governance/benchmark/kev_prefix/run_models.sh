#!/bin/bash
# Kev 前后对照正式评测（GPU，须在静默时段之外执行；本脚本不启动训练）。
# 用法：bash benchmark/kev_prefix/run_models.sh [模型名...]
#   默认顺序：kev-original seed43 seed17 seed29
# 前置：prepare_eval.sh 已生成 $PRIV/{records,sidecar,join,suite}；
#       pin_checkpoints.py 已生成 $PRIV/ckpt/{kev-original,seed-43,seed-17,seed-29}（底座 revision 固定）。
# 产物：$PRIV/runs/<model>/{report.json,rows.json,...}、
#       $PRIV/aggregate-primary.json（共同上下文主表）、aggregate-extended.json（serving 敏感性）、
#       aggregate-full.json（含 overlong 全量）、training-context-stats.json。
set -euo pipefail
cd "$HOME"   # 避免仓库目录 shadow 掉 PyPI 的 datasets 等包
REPO="/mnt/c/Projects/DAism/NaturalDAO/PoL-Governance"
PRIV="${PRIV_DIR:-/home/wenbo/priv-eval}"
SUITE="${SUITE_DIR:-$PRIV/suite-eval}"   # screen_suite.py 产出的可执行 suite（row<=2048 tokens）
export PYTHONPATH="$HOME/src/kev"
export KEV_DTYPE=bf16 KEV_BACKEND=torch KEV_MERGE=1 KEV_ATTN=eager KEV_CUDA_GRAPHS=0 KEV_FUSED=0
export HSA_ENABLE_DXG_DETECTION=1 PYTORCH_ROCM_ARCH=gfx1100
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
source "$HOME/src/polgov/.venv/bin/activate"

declare -A RUNS=(
  [kev-original]="$PRIV/ckpt/kev-original"
  [seed43]="$PRIV/ckpt/seed-43"
  [seed17]="$PRIV/ckpt/seed-17"
  [seed29]="$PRIV/ckpt/seed-29"
)
MODELS=("$@")
if [ ${#MODELS[@]} -eq 0 ]; then MODELS=(kev-original seed43 seed17 seed29); fi
for name in "${MODELS[@]}"; do
  run="${RUNS[$name]:?unknown model $name}"
  if [ ! -d "$run" ]; then echo "missing pinned checkpoint $run (run pin_checkpoints.py first)"; exit 2; fi
done
mkdir -p "$PRIV/runs"

for name in "${MODELS[@]}"; do
  run="${RUNS[$name]}"
  out="$PRIV/runs/$name"
  if [ -e "$out" ]; then echo "refusing to overwrite existing $out"; exit 2; fi
  echo "== scoring $name ($run) =="
  /usr/bin/time -v python -m kev.benchmark --run "$run" --suite "$SUITE" --out "$out" --device cuda \
    2>&1 | tee "$PRIV/runs/$name.log"
done

# 共同上下文主口径（原版 384/1024/2048 = Kev 官方 suite CONTEXT）
if [ ! -f "$PRIV/rids-training-context.txt" ]; then
  python "$REPO/benchmark/kev_prefix/fit_training_context.py" --join "${JOIN_FILE:-$PRIV/join-eval.jsonl}" \
    --suite-dir "$SUITE" --out-rids "$PRIV/rids-training-context.txt" \
    --out-json "$PRIV/training-context-stats.json"
fi
JOIN="${JOIN_FILE:-$PRIV/join-eval.jsonl}"
ARGS=(); for name in "${MODELS[@]}"; do ARGS+=(--run "$name=$PRIV/runs/$name"); done
python "$REPO/benchmark/kev_prefix/aggregate.py" --join "$JOIN" "${ARGS[@]}" \
  --reference kev-original --subset-rids "$PRIV/rids-training-context.txt" \
  --out "$PRIV/aggregate-primary.json"
python "$REPO/benchmark/kev_prefix/aggregate.py" --join "$JOIN" "${ARGS[@]}" \
  --reference kev-original --no-ci --out "$PRIV/aggregate-extended.json"
python "$REPO/benchmark/kev_prefix/aggregate.py" --join "$JOIN" "${ARGS[@]}" \
  --reference kev-original --include-overlong --no-ci --out "$PRIV/aggregate-full.json"
echo "done: $PRIV/aggregate-{primary,extended,full}.json"