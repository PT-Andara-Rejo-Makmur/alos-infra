#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"
compose_file="${COMPOSE_FILE:-${repo_root}/environments/local/compose.yaml}"
backup_dir="${BACKUP_DIR:-${repo_root}/backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
container_file="/tmp/alos-${timestamp}.dump"
backup_file="${backup_dir}/alos-${timestamp}.dump"
checksum_file="${backup_file}.sha256"

cleanup_container_file() {
  docker compose -f "${compose_file}" exec -T postgres rm -f "${container_file}" >/dev/null 2>&1 || true
}
trap cleanup_container_file EXIT

mkdir -p "${backup_dir}"
docker compose -f "${compose_file}" exec -T postgres sh -c \
  'pg_dump --format=custom --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --file="$1"' \
  sh "${container_file}"
docker compose -f "${compose_file}" cp "postgres:${container_file}" "${backup_file}"

test -s "${backup_file}"
if command -v sha256sum >/dev/null 2>&1; then
  checksum="$(sha256sum "${backup_file}" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  checksum="$(shasum -a 256 "${backup_file}" | awk '{print $1}')"
else
  printf 'sha256sum atau shasum diperlukan untuk membuat checksum backup.\n' >&2
  exit 1
fi
printf '%s  %s\n' "${checksum}" "$(basename -- "${backup_file}")" >"${checksum_file}"

printf 'Backup dibuat: %s\n' "${backup_file}"
printf 'Checksum dibuat: %s\n' "${checksum_file}"
printf 'Lanjutkan dengan off-site copy, retention, dan restore test sesuai operator policy.\n'
