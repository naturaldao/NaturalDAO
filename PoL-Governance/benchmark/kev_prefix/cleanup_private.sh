#!/bin/bash
# 评测结束后删除私有数据临时副本（方式 2：只回传聚合，执行后删除）。
# 用法：bash benchmark/kev_prefix/cleanup_private.sh --yes
set -euo pipefail
PRIV="${PRIV_DIR:-/home/wenbo/priv-eval}"
if [ "${1:-}" != "--yes" ]; then
  echo "refusing: pass --yes to delete $PRIV"
  exit 2
fi
rm -rf "$PRIV"
echo "deleted $PRIV"
