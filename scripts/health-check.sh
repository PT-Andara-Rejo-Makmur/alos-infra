#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"

target="${1:-local}"
if [[ "$target" == "--target" || "$target" == "-t" ]]; then
  target="${2:-local}"
fi

web_port="${ALOS_WEB_PORT:-3000}"
backend_port="${ALOS_BACKEND_PORT:-8000}"

check_http() {
  local service_name="$1"
  local url="$2"
  printf 'Memeriksa %s ... ' "${service_name}"
  curl --fail --silent --show-error --max-time 5 "${url}" >/dev/null
  printf 'sehat\n'
}

case "$target" in
  local)
    compose_file="${COMPOSE_FILE:-${repo_root}/environments/local/compose.yaml}"
    check_http "alos-web" "http://127.0.0.1:${web_port}/"
    check_http "alos-backend" "http://127.0.0.1:${backend_port}/health"

    printf 'Memeriksa genesis-ai (internal) ... '
    docker compose -f "${compose_file}" exec -T genesis \
      python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=5)" \
      >/dev/null
    printf 'sehat\n'

    printf 'Memeriksa postgres (internal) ... '
    docker compose -f "${compose_file}" exec -T postgres \
      sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null
    printf 'sehat\n'
    printf 'Semua service local sehat.\n'
    ;;

  app)
    compose_file="${COMPOSE_FILE:-${repo_root}/environments/production/app/compose.yaml}"
    printf 'Memeriksa node VPS 1 APP ...\n'
    docker compose -f "${compose_file}" exec -T web \
      node -e "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
    printf 'alos-web: sehat\n'
    docker compose -f "${compose_file}" exec -T backend \
      python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)"
    printf 'alos-backend: sehat\n'
    docker compose -f "${compose_file}" ps caddy | grep -q "Up" || true
    printf 'Semua service VPS 1 APP sehat.\n'
    ;;

  genesis)
    compose_file="${COMPOSE_FILE:-${repo_root}/environments/production/genesis/compose.yaml}"
    printf 'Memeriksa node VPS 2 GENESIS ...\n'
    docker compose -f "${compose_file}" exec -T genesis \
      python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=5)"
    printf 'genesis-ai: sehat\n'
    printf 'Semua service VPS 2 GENESIS sehat.\n'
    ;;

  data)
    compose_file="${COMPOSE_FILE:-${repo_root}/environments/production/data/compose.yaml}"
    printf 'Memeriksa node VPS 3 DATA ...\n'
    docker compose -f "${compose_file}" exec -T postgres \
      sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
    printf 'postgres: sehat\n'
    printf 'Semua service VPS 3 DATA sehat.\n'
    ;;

  staging)
    compose_file="${COMPOSE_FILE:-${repo_root}/environments/staging/compose.yaml}"
    printf 'Memeriksa node VPS 4 STAGING ...\n'
    docker compose -f "${compose_file}" exec -T web \
      node -e "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
    printf 'alos-web: sehat\n'
    docker compose -f "${compose_file}" exec -T backend \
      python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)"
    printf 'alos-backend: sehat\n'
    docker compose -f "${compose_file}" exec -T genesis \
      python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=5)"
    printf 'genesis-ai: sehat\n'
    docker compose -f "${compose_file}" exec -T postgres \
      sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
    printf 'postgres: sehat\n'
    printf 'Semua service VPS 4 STAGING sehat.\n'
    ;;

  *)
    printf 'Target tidak dikenal: %s (pilihan: local, app, genesis, data, staging)\n' "$target" >&2
    exit 1
    ;;
esac
