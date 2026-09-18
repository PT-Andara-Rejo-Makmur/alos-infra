# Backup dan Restore

## Backup

Script menggunakan `pg_dump --format=custom`, menyalin file keluar container, memastikan file
tidak kosong, lalu menulis sidecar `<backup>.sha256`. Jalankan:

```bash
bash database/backup/backup.sh
```

atau `database/backup/backup.ps1`. Simpan dump dan sidecar bersama-sama. Operator masih harus
encrypt bila diperlukan, menyalin keduanya ke off-site storage, menerapkan retention, dan mencatat
evidence.

## Restore

Restore menggunakan `pg_restore --clean --if-exists` dan bersifat destructive terhadap target.
Script menolak berjalan tanpa `CONFIRM_DATABASE_RESTORE=YES`, backup file eksplisit, sidecar
SHA-256 yang sesuai, dan checksum yang valid. Checksum hanya membuktikan integritas file; approval,
compatibility review, serta isolated restore drill tetap wajib sebelum production restore.

Restore test harus dilakukan pada isolated environment, lalu diverifikasi melalui query database,
extension, migration state, application invariants, health, dan critical user journey. Catat durasi
untuk mengevaluasi RTO.

## Keterbatasan

Bootstrap belum menyediakan scheduler, object-storage provider, retention enforcement, encryption
key, immutable backup, point-in-time recovery, replication, atau cross-region recovery. Semua ini
membutuhkan requirement dan design review production.
