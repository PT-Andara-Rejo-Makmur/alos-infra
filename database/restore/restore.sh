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
checksum_file="${backup_file}.sha256"
container_file="/tmp/alos-controlled-restore.dump"

if [[ ! -s "${checksum_file}" ]]; then
  printf 'Checksum sidecar tidak ditemukan atau kosong: %s\n' "${checksum_file}" >&2
  exit 2
fi
expected_checksum="$(awk 'NR == 1 { print $1 }' "${checksum_file}")"
if [[ ! "${expected_checksum}" =~ ^[0-9a-fA-F]{64}$ ]]; then
  printf 'Format checksum tidak valid: %s\n' "${checksum_file}" >&2
  exit 2
fi
if command -v sha256sum >/dev/null 2>&1; then
  actual_checksum="$(sha256sum "${backup_file}" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  actual_checksum="$(shasum -a 256 "${backup_file}" | awk '{print $1}')"
else
  printf 'sha256sum atau shasum diperlukan untuk memverifikasi backup.\n' >&2
  exit 1
fi
expected_checksum="$(printf '%s' "${expected_checksum}" | tr '[:upper:]' '[:lower:]')"
actual_checksum="$(printf '%s' "${actual_checksum}" | tr '[:upper:]' '[:lower:]')"
if [[ "${expected_checksum}" != "${actual_checksum}" ]]; then
  printf 'Checksum backup tidak cocok. Restore dibatalkan.\n' >&2
  exit 1
fi

cleanup_container_file() {
  docker compose -f "${compose_file}" exec -T postgres rm -f "${container_file}" >/dev/null 2>&1 || true
}
trap cleanup_container_file EXIT

docker compose -f "${compose_file}" cp "${backup_file}" "postgres:${container_file}"
docker compose -f "${compose_file}" exec -T postgres sh -c \
  'pg_restore --clean --if-exists --exit-on-error --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" "$1"' \
  sh "${container_file}"
docker compose -f "${compose_file}" exec -T postgres sh -c \
  'psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --tuples-only --command="SELECT 1; SELECT extname FROM pg_extension WHERE extname = '\''vector'\'';"'

printf 'Restore selesai. Jalankan application smoke test dan verification checklist sebelum membuka traffic.\n'
