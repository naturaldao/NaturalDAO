#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ] || [ ! -f .env ]; then
  printf 'Run ./install.sh first.\n' >&2
  exit 1
fi

set -a
. ./.env
set +a

if [ "${POL2_MANAGE_POSTGRES:-0}" = "1" ]; then
  docker compose up -d postgres >/dev/null
  ready=0
  for _ in $(seq 1 40); do
    if docker compose exec -T postgres pg_isready -U pol2 -d pol2 >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 1
  done
  if [ "$ready" != "1" ]; then
    printf 'PostgreSQL did not become ready.\n' >&2
    exit 1
  fi
fi

exec .venv/bin/python -m uvicorn service.app:app \
  --host "${POL2_HOST:-127.0.0.1}" \
  --port "${POL2_PORT:-18080}"
