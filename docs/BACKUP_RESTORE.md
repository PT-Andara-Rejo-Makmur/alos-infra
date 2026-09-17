# Backup dan Restore

## Backup

Script menggunakan `pg_dump --format=custom`, menyalin file keluar container, dan memastikan file
tidak kosong. Jalankan:

```bash
bash database/backup/backup.sh
```

atau `database/backup/backup.ps1`. Setelah backup, operator masih harus membuat checksum,
encrypt bila diperlukan, menyalin ke off-site storage, menerapkan retention, dan mencatat evidence.

## Restore

Restore menggunakan `pg_restore --clean --if-exists` dan bersifat destructive terhadap target.
Script menolak berjalan tanpa `CONFIRM_DATABASE_RESTORE=YES` dan backup file eksplisit.

Restore test harus dilakukan pada isolated environment, lalu diverifikasi melalui query database,
extension, migration state, application invariants, health, dan critical user journey. Catat durasi
untuk mengevaluasi RTO.

## Keterbatasan

Bootstrap belum menyediakan scheduler, object-storage provider, retention enforcement, encryption
key, immutable backup, point-in-time recovery, replication, atau cross-region recovery. Semua ini
membutuhkan requirement dan design review production.
