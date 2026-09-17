#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"
compose_file="${COMPOSE_FILE:-${repo_root}/environments/local/compose.yaml}"
backup_dir="${BACKUP_DIR:-${repo_root}/backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
container_file="/tmp/alos-${timestamp}.dump"
backup_file="${backup_dir}/alos-${timestamp}.dump"

mkdir -p "${backup_dir}"
docker compose -f "${compose_file}" exec -T postgres sh -c \
  'pg_dump --format=custom --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --file="$1"' \
  sh "${container_file}"
docker compose -f "${compose_file}" cp "postgres:${container_file}" "${backup_file}"
docker compose -f "${compose_file}" exec -T postgres rm -f "${container_file}"

test -s "${backup_file}"
printf 'Backup dibuat: %s\n' "${backup_file}"
printf 'Lanjutkan dengan off-site copy, checksum, retention, dan restore test sesuai operator policy.\n'
