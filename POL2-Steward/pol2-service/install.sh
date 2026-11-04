#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  printf 'Python 3.10 or newer is required.\n' >&2
  exit 1
fi
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
  printf 'Python 3.10 or newer is required.\n' >&2
  exit 1
}

printf 'Installing Python dependencies...\n'
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  base_url="${POL2_LLM_BASE_URL:-https://api.deepseek.com/v1}"
  model="${POL2_LLM_MODEL:-deepseek-flash}"
  api_key="${POL2_LLM_API_KEY:-}"

  if [ -z "$api_key" ] && [ -t 0 ]; then
    read -r -s -p "LLM API key: " api_key
    printf '\n'
  fi
  if [ -z "$api_key" ]; then
    printf 'POL2_LLM_API_KEY is required. Re-run with POL2_LLM_API_KEY set or use an interactive shell.\n' >&2
    exit 1
  fi

  external_database_url="${POL2_DATABASE_URL:-}"
  if [ -n "$external_database_url" ]; then
    manage_postgres=0
    postgres_password=""
    postgres_port=""
    database_url="$external_database_url"
  else
    manage_postgres=1
    postgres_password="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(24))')"
    postgres_port="${POL2_POSTGRES_PORT:-15432}"
    database_url="postgresql://pol2:$postgres_password@127.0.0.1:$postgres_port/pol2"
  fi
  service_token="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')"
  release_secret="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(32))')"
  umask 077
  cat > .env <<EOF
POL2_SIMPLE_MODE=1
POL2_ENV=preview
POL2_LLM_BASE_URL=$base_url
POL2_LLM_MODEL=$model
POL2_LLM_API_KEY=$api_key
POL2_HOST=127.0.0.1
POL2_PORT=18080
POL2_MANAGE_POSTGRES=$manage_postgres
POL2_POSTGRES_PORT=$postgres_port
POL2_POSTGRES_PASSWORD=$postgres_password
POL2_DATABASE_URL=$database_url
POL2_EMBEDDING_DIM=4096
POL2_SERVICE_TOKEN=$service_token
POL2_RELEASE_SECRET=$release_secret
POL2_ALLOW_CANDIDATE_PACKAGE=1
EOF
  printf 'Created .env with PostgreSQL settings and generated service secrets.\n'
fi

if [ ! -f packages/pol2-runtime-2026.10.21.1/package-manifest.json ]; then
  printf 'Bundled knowledge package is missing. Re-download the release package.\n' >&2
  exit 1
fi

set -a
. ./.env
set +a

case "${POL2_DATABASE_URL:-}" in
  postgresql://*|postgres://*) ;;
  *)
    printf 'POL2_DATABASE_URL must point to PostgreSQL. Remove the old .env and rerun install.sh.\n' >&2
    exit 1
    ;;
esac

if [ "${POL2_MANAGE_POSTGRES:-0}" = "1" ]; then
  if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    printf 'Docker with the compose plugin is required for the default PostgreSQL setup.\n' >&2
    exit 1
  fi
  printf 'Starting PostgreSQL/pgvector...\n'
  docker compose up -d postgres
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

.venv/bin/python - <<'PY'
import os
from service.store_postgres import PostgresStore

store = PostgresStore(os.environ['POL2_DATABASE_URL'], int(os.getenv('POL2_EMBEDDING_DIM', '4096')))
print('PostgreSQL ready; pgvector=', store.vector_available)
PY

printf 'Installation complete.\n'
printf 'Start the service with: ./start.sh\n'
printf 'Then set the Agent model base URL to: http://127.0.0.1:18080/v1\n'
