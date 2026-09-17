# Runbook Deploy

## Sebelum deploy

1. Pastikan change ticket, reviewer, target environment, serta maintenance window jelas.
2. Catat current image reference dan hasil health check.
3. Verifikasi image baru immutable dan quality gate aplikasi lulus.
4. Jalankan preflight checklist dan backup bila perubahan menyentuh persistence/migration.
5. Jalankan `docker compose --env-file .env config --quiet`.

## Deploy

```bash
docker compose --env-file .env pull
docker compose --env-file .env up -d --remove-orphans
docker compose --env-file .env ps
```

Migration aplikasi dijalankan berdasarkan instruksi repository pemilik sebelum/ketika release,
bukan dari Infra secara generik.

## Verifikasi

Periksa Caddy, Web, Backend, GENESIS, PostgreSQL, logs, correlation flow, serta critical user
journey. Simpan evidence deployment. Jika health tidak stabil, hentikan traffic change dan ikuti
[rollback](rollback.md).
