#!/bin/bash
# JevBench（第三方 coherence 基准）第二主表：对每个 checkpoint 起 kev.serve（GPU）并跑 mini。
# 用法：bash benchmark/kev_prefix/run_jevbench.sh [模型名...]   （需在静默时段外；一次一个模型）
# 说明：jevbench==0.1.0 装在 ~/src/polgov/jevbench-venv（数据随包、可离线）；不把任何题目写入仓库。
set -euo pipefail
cd "$HOME"
REPO="/mnt/c/Projects/DAism/NaturalDAO/PoL-Governance"
PRIV="${PRIV_DIR:-/home/wenbo/priv-eval}"
OUT="${JEV_OUT:-$HOME/jev-runs}"
PORT="${JEV_PORT:-8009}"
JEVC="$HOME/src/polgov/jevbench-venv/bin/jevbench"
SUITE="${JEV_SUITE:-jevbench-mini}"
export PYTHONPATH="$HOME/src/kev"
export KEV_DTYPE=bf16 KEV_BACKEND=torch KEV_MERGE=1 KEV_ATTN=eager KEV_CUDA_GRAPHS=0 KEV_FUSED=0
export HSA_ENABLE_DXG_DETECTION=1 PYTORCH_ROCM_ARCH=gfx1100

declare -A RUNS=(
  [kev-original]="$PRIV/ckpt/kev-original"
  [seed43]="$PRIV/ckpt/seed-43"
  [seed17]="$PRIV/ckpt/seed-17"
  [seed29]="$PRIV/ckpt/seed-29"
)
MODELS=("$@"); if [ ${#MODELS[@]} -eq 0 ]; then MODELS=(kev-original seed43); fi
mkdir -p "$OUT"
if [ ! -x "$JEVC" ]; then echo "missing jevbench venv at $HOME/src/polgov/jevbench-venv"; exit 2; fi

for name in "${MODELS[@]}"; do
  run="${RUNS[$name]:?unknown model $name}"
  report="$OUT/$name-${SUITE}.json"
  if [ -e "$report" ]; then echo "refusing to overwrite $report"; exit 2; fi
  log="$OUT/$name-serve.log"
  echo "== serve $name ($run) on :$PORT =="
  source "$HOME/src/polgov/.venv/bin/activate"
  python -m kev.serve --run "$run" --host 127.0.0.1 --port "$PORT" --device cuda > "$log" 2>&1 &
  SERVER=$!
  trap 'kill $SERVER 2>/dev/null || true' EXIT
  ready=0
  for i in $(seq 1 240); do
    if curl -s --max-time 2 "http://127.0.0.1:$PORT/v1/models" > /dev/null 2>&1; then ready=1; break; fi
    if ! kill -0 $SERVER 2>/dev/null; then echo "server exited; tail of $log:"; tail -40 "$log"; exit 3; fi
    sleep 2
  done
  if [ $ready -ne 1 ]; then echo "server not ready in time; tail:"; tail -40 "$log"; exit 4; fi
  curl -s "http://127.0.0.1:$PORT/v1/models" > "$OUT/$name-models.json"
  echo "== check $name =="
  "$JEVC" check --url "http://127.0.0.1:$PORT/v1/systemone" --model kev-latest | tee "$OUT/$name-check.txt"
  echo "== eval $name suite=$SUITE =="
  # 缓存隔离（2026-10-28 实测）：jevbench 0.1.0 的请求缓存按 URL+请求内容做键，不区分 serve 的 checkpoint；
  # 单独 --no-cache 仍复用了旧响应（两个模型的分数逐位相同），必须每模型用全新 --cache-dir，并用 serve 日志的
  # POST 计数复核请求确实打到本模型的 server。
  CACHE_DIR="$OUT/cache-$name"
  rm -rf "$CACHE_DIR"
  "$JEVC" eval --url "http://127.0.0.1:$PORT/v1/systemone" --model kev-latest \
    --name "$name" --suite "$SUITE" --concurrency 1 --no-cache --cache-dir "$CACHE_DIR" \
    --out "$report" | tee "$OUT/$name-eval.txt"
  POSTS=$(grep -c "POST /v1/systemone" "$log" || true)
  echo "serve POST count for $name: $POSTS"
  if [ "$POSTS" -lt 100 ]; then echo "refusing: too few requests hit the $name server ($POSTS)"; exit 5; fi
  kill $SERVER 2>/dev/null || true
  wait $SERVER 2>/dev/null || true
  sleep 3
done
echo "done: $OUT"