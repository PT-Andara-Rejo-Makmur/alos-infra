#!/usr/bin/env bash
set -euo pipefail

# ALOS Production Migration Runner
# Enforces single-run migration semantics, pre-migration verification, and sanitized logging.

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

compose_file=""
env_file=""
skip_backup=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-file)
      compose_file="$2"
      shift 2
      ;;
    --env-file)
      env_file="$2"
      shift 2
      ;;
    --skip-backup)
      skip_backup=true
      shift
      ;;
    -h|--help)
      printf 'Penggunaan: CONFIRM_MIGRATION=YES %s [--compose-file <path>] [--env-file <path>] [--skip-backup]\n' "$0"
      exit 0
      ;;
    *)
      printf 'Argumen tidak dikenal: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

if [[ "${CONFIRM_MIGRATION:-}" != "YES" ]]; then
  printf 'ERROR: Migrasi database production memerlukan konfirmasi eksplisit: CONFIRM_MIGRATION=YES\n' >&2
  exit 2
fi

if [[ -z "${compose_file}" ]]; then
  if [[ -f "${repo_root}/environments/production/app/compose.yaml" ]]; then
    compose_file="${repo_root}/environments/production/app/compose.yaml"
  elif [[ -f "${repo_root}/environments/staging/compose.yaml" ]]; then
    compose_file="${repo_root}/environments/staging/compose.yaml"
  else
    compose_file="${repo_root}/environments/local/compose.yaml"
  fi
fi

cmd_args=("-f" "${compose_file}")
if [[ -n "${env_file}" ]]; then
  if [[ ! -f "${env_file}" ]]; then
    printf 'ERROR: File environment tidak ditemukan: %s\n' "${env_file}" >&2
    exit 2
  fi
  cmd_args=("--env-file" "${env_file}" "${cmd_args[@]}")
fi

printf '==================================================\n'
printf 'ALOS DATABASE MIGRATION RUNNER\n'
printf 'Target compose: %s\n' "${compose_file}"
printf '==================================================\n'

# 1. Pre-migration backup check
if [[ "${skip_backup}" != "true" ]]; then
  printf '\n[1/4] Memeriksa status backup sebelum migrasi...\n'
  if [[ -z "${PRE_MIGRATION_BACKUP_VERIFIED:-}" ]]; then
    printf 'PERINGATAN: Pastikan Anda telah mengambil snapshot database terkini di VPS 3 (DATA) sebelum melanjutkan.\n'
    printf 'Untuk melanjutkan, set PRE_MIGRATION_BACKUP_VERIFIED=YES atau jalankan dengan --skip-backup jika di lingkungan non-prod.\n' >&2
    exit 3
  fi
  printf '  -> Pre-migration backup terverifikasi (PRE_MIGRATION_BACKUP_VERIFIED=YES)\n'
else
  printf '\n[1/4] Pre-migration backup dilewati (--skip-backup aktif)\n'
fi

# 2. Preflight schema inspection
printf '\n[2/4] Memeriksa revisi skema database saat ini (alembic current)...\n'
if ! docker compose "${cmd_args[@]}" run --rm --no-deps backend alembic current 2>&1; then
  printf 'ERROR: Gagal membaca revisi skema database saat ini. Periksa konektivitas DB.\n' >&2
  exit 4
fi

# 3. Execute migration single-run
printf '\n[3/4] Menjalankan migrasi skema tunggal (alembic upgrade head)...\n'
if ! docker compose "${cmd_args[@]}" run --rm --no-deps backend alembic upgrade head 2>&1; then
  printf 'ERROR: Eksekusi migrasi database GAGAL! Segera rujuk runbooks/rollback.md untuk mitigasi.\n' >&2
  exit 5
fi

# 4. Verify post-migration schema head
printf '\n[4/4] Verifikasi revisi skema setelah migrasi...\n'
if ! docker compose "${cmd_args[@]}" run --rm --no-deps backend alembic current 2>&1; then
  printf 'ERROR: Verifikasi revisi skema setelah migrasi gagal.\n' >&2
  exit 6
fi

printf '\n==================================================\n'
printf 'MIGRASI BERHASIL DISELESAIKAN SECARA AMAN!\n'
printf 'Lanjutkan dengan rilis/start container backend di VPS 1 (APP).\n'
printf '==================================================\n'
