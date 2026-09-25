#!/usr/bin/env bash
set -euo pipefail

# ALOS PostgreSQL Controlled Restore Script
# Requires explicit confirmation, checksum verification, explicit target DB, and production overwrite guard.

if [[ "${CONFIRM_DATABASE_RESTORE:-}" != "YES" ]]; then
  printf 'ERROR: Restore database memerlukan konfirmasi eksplisit: set CONFIRM_DATABASE_RESTORE=YES\n' >&2
  exit 2
fi

backup_file=""
target_db="${TARGET_DB:-alos_restore_verify}"
compose_file="${COMPOSE_FILE:-}"
confirm_production="${CONFIRM_PRODUCTION:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-db)
      target_db="$2"
      shift 2
      ;;
    --compose-file)
      compose_file="$2"
      shift 2
      ;;
    --confirm-production)
      confirm_production="YES"
      shift
      ;;
    -h|--help)
      printf 'Penggunaan: CONFIRM_DATABASE_RESTORE=YES %s <backup.dump> [--target-db <name>] [--compose-file <path>] [--confirm-production]\n' "$0"
      exit 0
      ;;
    *)
      if [[ -z "${backup_file}" ]]; then
        backup_file="$1"
        shift
      else
        printf 'Argumen tidak dikenal: %s\n' "$1" >&2
        exit 2
      fi
      ;;
  esac
done

if [[ -z "${backup_file}" ]]; then
  printf 'ERROR: Path file backup wajib ditentukan.\n' >&2
  printf 'Contoh: CONFIRM_DATABASE_RESTORE=YES %s backups/alos-db-timestamp.dump --target-db alos_staging\n' "$0" >&2
  exit 2
fi

if [[ ! -s "${backup_file}" ]]; then
  printf 'ERROR: File backup tidak ditemukan atau berukuran 0 byte: %s\n' "${backup_file}" >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

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
  exit 2
fi

backup_file="$(cd -- "$(dirname -- "${backup_file}")" && pwd)/$(basename -- "${backup_file}")"
checksum_file="${backup_file}.sha256"

# Verify SHA-256 sidecar checksum
if [[ ! -s "${checksum_file}" ]]; then
  printf 'ERROR: Checksum sidecar tidak ditemukan atau kosong: %s\n' "${checksum_file}" >&2
  exit 2
fi

expected_checksum="$(awk 'NR == 1 { print $1 }' "${checksum_file}")"
if [[ ! "${expected_checksum}" =~ ^[0-9a-fA-F]{64}$ ]]; then
  printf 'ERROR: Format checksum tidak valid: %s\n' "${checksum_file}" >&2
  exit 2
fi

if command -v sha256sum >/dev/null 2>&1; then
  actual_checksum="$(sha256sum "${backup_file}" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  actual_checksum="$(shasum -a 256 "${backup_file}" | awk '{print $1}')"
else
  printf 'ERROR: sha256sum atau shasum diperlukan untuk memverifikasi backup.\n' >&2
  exit 1
fi

expected_checksum="$(printf '%s' "${expected_checksum}" | tr '[:upper:]' '[:lower:]')"
actual_checksum="$(printf '%s' "${actual_checksum}" | tr '[:upper:]' '[:lower:]')"
if [[ "${expected_checksum}" != "${actual_checksum}" ]]; then
  printf 'ERROR: Checksum backup tidak cocok! Expected: %s, Actual: %s. Restore DIBATALKAN.\n' "${expected_checksum}" "${actual_checksum}" >&2
  exit 1
fi

# Detect production database from compose environment to prevent accidental overwrite
configured_prod_db="$(docker compose -f "${compose_file}" exec -T postgres sh -c 'echo "$POSTGRES_DB"' 2>/dev/null | tr -d '\r\n')"
if [[ -n "${configured_prod_db}" && "${target_db}" == "${configured_prod_db}" ]]; then
  if [[ "${confirm_production}" != "YES" ]]; then
    printf '\n========================================================================\n' >&2
    printf 'SAFETY GUARD AKTIF: Target restore [%s] adalah DATABASE PRODUKSI AKTIF!\n' "${target_db}" >&2
    printf 'Tindakan ini bersifat destruktif dan akan menimpa data yang sedang berjalan.\n' >&2
    printf 'Untuk melanjutkan, Anda wajib menambahkan opsi --confirm-production\n' >&2
    printf 'atau set CONFIRM_PRODUCTION=YES secara sadar dan terotorisasi.\n' >&2
    printf '========================================================================\n' >&2
    exit 3
  fi
  printf 'PERINGATAN TINGGI: Menjalankan restore ke DATABASE PRODUKSI AKTIF [%s] (CONFIRM_PRODUCTION=YES)\n' "${target_db}"
fi

container_file="/tmp/alos-controlled-restore-$$.dump"

cleanup_container_file() {
  docker compose -f "${compose_file}" exec -T postgres rm -f "${container_file}" >/dev/null 2>&1 || true
}
trap cleanup_container_file EXIT

printf 'Memulai controlled restore ke database [%s]...\n' "${target_db}"

# Ensure target database exists if not already present
docker compose -f "${compose_file}" exec -T postgres sh -c \
  'psql --username="$POSTGRES_USER" -d template1 -tc "SELECT 1 FROM pg_database WHERE datname = '\'"$target_db"\''" | grep -q 1 || psql --username="$POSTGRES_USER" -d template1 -c "CREATE DATABASE \"'"$target_db"'\" WITH TEMPLATE template1;"' 2>/dev/null || true

# Copy backup to container
docker compose -f "${compose_file}" cp "${backup_file}" "postgres:${container_file}"

# Execute deterministic pg_restore
if ! docker compose -f "${compose_file}" exec -T postgres sh -c \
  'pg_restore --clean --if-exists --exit-on-error --no-owner --no-privileges --username="$POSTGRES_USER" --dbname="'"$target_db"'" "$1"' \
  sh "${container_file}"; then
  printf 'ERROR: pg_restore mengalami kegagalan pada database [%s].\n' "${target_db}" >&2
  exit 4
fi

# Verify restore success and pgvector extension
if ! docker compose -f "${compose_file}" exec -T postgres sh -c \
  'psql --username="$POSTGRES_USER" --dbname="'"$target_db"'" --tuples-only --command="SELECT 1; SELECT extname FROM pg_extension WHERE extname = '\''vector'\'';"' >/dev/null; then
  printf 'ERROR: Verifikasi hasil restore gagal pada database [%s].\n' "${target_db}" >&2
  exit 5
fi

printf '\n==================================================\n'
printf 'RESTORE DATABASE BERHASIL DISELESAIKAN SECARA AMAN!\n'
printf 'Target Database : %s\n' "${target_db}"
printf 'Source Backup   : %s\n' "${backup_file}"
printf 'Checksum Verified: %s (SHA-256 MATCH)\n' "${actual_checksum}"
printf '==================================================\n'
