#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_DATABASE_RESTORE:-}" != "YES" ]]; then
  printf 'Set CONFIRM_DATABASE_RESTORE=YES setelah approval untuk menjalankan restore.\n' >&2
  exit 2
fi
if [[ $# -ne 1 || ! -s "$1" ]]; then
  printf 'Penggunaan: CONFIRM_DATABASE_RESTORE=YES %s <backup.dump>\n' "$0" >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"
compose_file="${COMPOSE_FILE:-${repo_root}/environments/local/compose.yaml}"
backup_file="$(cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")"
container_file="/tmp/alos-controlled-restore.dump"

docker compose -f "${compose_file}" cp "${backup_file}" "postgres:${container_file}"
docker compose -f "${compose_file}" exec -T postgres sh -c \
  'pg_restore --clean --if-exists --exit-on-error --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" "$1"' \
  sh "${container_file}"
docker compose -f "${compose_file}" exec -T postgres rm -f "${container_file}"
docker compose -f "${compose_file}" exec -T postgres sh -c \
  'psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --tuples-only --command="SELECT 1; SELECT extname FROM pg_extension WHERE extname = '\''vector'\'';"'

printf 'Restore selesai. Jalankan application smoke test dan verification checklist sebelum membuka traffic.\n'
