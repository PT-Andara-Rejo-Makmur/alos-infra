#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
compose_file="${COMPOSE_FILE:-${repo_root}/environments/local/compose.yaml}"
web_port="${ALOS_WEB_PORT:-3000}"
backend_port="${ALOS_BACKEND_PORT:-8000}"

check_http() {
  local service_name="$1"
  local url="$2"
  printf 'Memeriksa %s ... ' "${service_name}"
  curl --fail --silent --show-error --max-time 5 "${url}" >/dev/null
  printf 'sehat\n'
}

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
