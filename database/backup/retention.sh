#!/usr/bin/env bash
set -euo pipefail

# ALOS Backup Retention Manager
# Rotates old backups according to retention policies with safe dry-run capabilities.

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../.." && pwd)"

backup_dir="${BACKUP_DIR:-${repo_root}/backups}"
daily_keep="${DAILY_RETENTION:-7}"
dry_run=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup-dir)
      backup_dir="$2"
      shift 2
      ;;
    --daily-keep)
      daily_keep="$2"
      shift 2
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    -h|--help)
      printf 'Penggunaan: %s [--backup-dir <path>] [--daily-keep <count>] [--dry-run]\n' "$0"
      exit 0
      ;;
    *)
      printf 'Argumen tidak dikenal: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

if [[ ! -d "${backup_dir}" ]]; then
  printf 'Direktori backup tidak ditemukan: %s\n' "${backup_dir}"
  exit 0
fi

# List all backup dump files sorted by modification time (newest first)
mapfile -t dump_files < <(find "${backup_dir}" -maxdepth 1 -name "alos-*.dump" -type f | sort -r)

total_dumps="${#dump_files[@]}"
printf 'Total file backup ditemukan: %d (di %s)\n' "${total_dumps}" "${backup_dir}"
printf 'Kebijakan retensi harian: simpan %d file terbaru\n' "${daily_keep}"

if [[ "${total_dumps}" -le "${daily_keep}" ]]; then
  printf 'Jumlah backup (%d) tidak melebihi batas retensi (%d). Tidak ada file yang dihapus.\n' "${total_dumps}" "${daily_keep}"
  exit 0
fi

# Files exceeding retention
delete_count=0
for ((i = daily_keep; i < total_dumps; i++)); do
  dump_to_delete="${dump_files[i]}"
  checksum_to_delete="${dump_to_delete}.sha256"

  if [[ "${dry_run}" == "true" ]]; then
    printf '[DRY-RUN] Akan menghapus: %s\n' "${dump_to_delete}"
    if [[ -f "${checksum_to_delete}" ]]; then
      printf '[DRY-RUN] Akan menghapus: %s\n' "${checksum_to_delete}"
    fi
  else
    printf 'Menghapus backup kedaluwarsa: %s\n' "${dump_to_delete}"
    rm -f "${dump_to_delete}"
    if [[ -f "${checksum_to_delete}" ]]; then
      rm -f "${checksum_to_delete}"
    fi
  fi
  ((delete_count++))
done

printf 'Selesai: %d file backup diproses untuk rotasi (dry_run=%s).\n' "${delete_count}" "${dry_run}"
