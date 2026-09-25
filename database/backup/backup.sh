#!/usr/bin/env bash
set -euo pipefail

# ALOS Production PostgreSQL Backup Script
# Creates a custom-format pg_dump with SHA-256 sidecar checksum and strict safety guards.

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

compose_file="${1:-${COMPOSE_FILE:-}}"
if [[ -z "${compose_file}" ]]; then
  if [[ -f "${repo_root}/environments/production/data/compose.yaml" ]]; then
    compose_file="${repo_root}/environments/production/data/compose.yaml"
  elif [[ -f "${repo_root}/environments/staging/compose.yaml" ]]; then
    compose_file="${repo_root}/environments/staging/compose.yaml"
  else
    compose_file="${repo_root}/environments/local/compose.yaml"
  fi
fi

if [[ ! -f "${compose_file}" ]]; then
  printf 'ERROR: Compose file tidak ditemukan: %s\n' "${compose_file}" >&2
  exit 1
fi

backup_dir="${BACKUP_DIR:-${repo_root}/backups}"
mkdir -p "${backup_dir}"

# Extract database identity safely from container
db_name="$(docker compose -f "${compose_file}" exec -T postgres sh -c 'echo "$POSTGRES_DB"' 2>/dev/null | tr -d '\r\n')"
if [[ -z "${db_name}" ]]; then
  db_name="alos"
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
container_file="/tmp/alos-${db_name}-${timestamp}.dump"
backup_file="${backup_dir}/alos-${db_name}-${timestamp}.dump"
checksum_file="${backup_file}.sha256"

# Accidental overwrite guard
if [[ -e "${backup_file}" ]]; then
  printf 'ERROR: File backup sasaran sudah ada: %s\n' "${backup_file}" >&2
  exit 1
fi

cleanup_container_file() {
  docker compose -f "${compose_file}" exec -T postgres rm -f "${container_file}" >/dev/null 2>&1 || true
}
trap cleanup_container_file EXIT

printf 'Memulai backup database [%s]...\n' "${db_name}"

# Execute pg_dump custom format without printing credentials
if ! docker compose -f "${compose_file}" exec -T postgres sh -c \
  'pg_dump --format=custom --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --file="$1"' \
  sh "${container_file}"; then
  printf 'ERROR: pg_dump gagal dijalankan di dalam container postgres.\n' >&2
  exit 2
fi

# Copy dump from container to host backup directory
if ! docker compose -f "${compose_file}" cp "postgres:${container_file}" "${backup_file}"; then
  printf 'ERROR: Gagal menyalin backup file dari container ke host: %s\n' "${backup_file}" >&2
  exit 3
fi

# Verify backup file on host is present and non-empty
if [[ ! -s "${backup_file}" ]]; then
  printf 'ERROR: File backup hasil dump tidak ditemukan atau berukuran 0 byte: %s\n' "${backup_file}" >&2
  rm -f "${backup_file}"
  exit 4
fi

# Generate SHA-256 checksum sidecar
if command -v sha256sum >/dev/null 2>&1; then
  checksum="$(sha256sum "${backup_file}" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  checksum="$(shasum -a 256 "${backup_file}" | awk '{print $1}')"
else
  printf 'ERROR: sha256sum atau shasum diperlukan untuk membuat checksum backup.\n' >&2
  rm -f "${backup_file}"
  exit 5
fi

if [[ -z "${checksum}" || ${#checksum} -ne 64 ]]; then
  printf 'ERROR: Gagal membuat checksum SHA-256 yang valid.\n' >&2
  rm -f "${backup_file}"
  exit 6
fi

printf '%s  %s\n' "${checksum}" "$(basename -- "${backup_file}")" >"${checksum_file}"

printf '\n==================================================\n'
printf 'BACKUP BERHASIL DIBUAT DENGAN AMAN!\n'
printf 'Database Identity : %s\n' "${db_name}"
printf 'Backup File       : %s (%s bytes)\n' "${backup_file}" "$(wc -c < "${backup_file}" | tr -d ' ')"
printf 'SHA-256 Checksum  : %s\n' "${checksum}"
printf 'Checksum File     : %s\n' "${checksum_file}"
printf '==================================================\n'
printf 'Rekomendasi Operasional:\n'
printf '1. Salin file dump dan checksum ke off-site object storage (mis. Cloudflare R2 / S3).\n'
printf '2. Jalankan rotasi retensi (database/backup/retention.sh).\n'
printf '3. Jangan bergantung pada satu node VPS yang sama untuk disaster recovery.\n'
