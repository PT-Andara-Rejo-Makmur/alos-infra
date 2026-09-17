# Runbook Restore Database

Restore bersifat destructive terhadap database target dan memerlukan approval.

1. Identifikasi target environment/database dan isolate traffic writer.
2. Verifikasi backup file, timestamp, checksum, encryption/access, serta restore-test evidence.
3. Ambil safety backup dari target sebelum perubahan.
4. Set `CONFIRM_DATABASE_RESTORE=YES` hanya pada sesi operator terkontrol.
5. Jalankan script restore dengan backup file eksplisit.
6. Verifikasi query, extension, application migration state, row-level invariants, dan smoke test.
7. Buka traffic bertahap dan monitor error/correlation ID.

```bash
CONFIRM_DATABASE_RESTORE=YES bash database/restore/restore.sh /path/backup.dump
```

Script bootstrap tidak mengimplementasikan point-in-time recovery, retention, off-site provider,
atau automated restore scheduling.
