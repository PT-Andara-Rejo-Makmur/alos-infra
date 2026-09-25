# Runbook Deploy Production ALOS (Multi-Host 4 VPS)

Dokumen ini mendefinisikan alur rilis aman (*safe deployment pipeline*) untuk lingkungan production multi-host ALOS MVP-2.

---

## 1. Alur Rilis Baku Production

```text
  [ 1. PRE-DEPLOYMENT SAFETY BACKUP ]
                  ↓
  [ 2. PREFLIGHT ENFORCEMENT CHECK ]
                  ↓
  [ 3. SINGLE-RUN DATABASE MIGRATION ]
                  ↓
  [ 4. POST-MIGRATION SCHEMA VERIFICATION ]
                  ↓
  [ 5. ROLLING / ORDERED SERVICE STARTUP ]
                  ↓
  [ 6. NODE HEALTH CHECKS ]
                  ↓
  [ 7. SMOKE TESTS & TRAFFIC OPEN ]
```

---

## 2. Prosedur Rilis per Langkah

### Langkah 1: Pre-Deployment Safety Backup
Jalankan backup database snapshot di VPS 3 (DATA) sebelum melakukan rilis:
```bash
# Di VPS 3 DATA:
bash database/backup/backup.sh
```
Catat lokasi file dump dan pastikan file sidecar `.sha256` terverifikasi.

### Langkah 2: Preflight Enforcement Check
Jalankan preflight check di seluruh target node untuk memvalidasi konfigurasi, image immutability, dan isolasi secret:
```bash
# Di node manajemen / VPS:
python scripts/preflight-check.py --target all
```
Jika preflight menghasilkan error, **HENTIKAN RILIS SEGERA** dan perbaiki variabel yang bermasalah.

### Langkah 3: Eksekusi Migrasi Database Tunggal (Single-Run Semantics)
> [!CRITICAL]
> Jangan biarkan beberapa replica/container backend menjalankan migrasi secara bersamaan! Gunakan script migrasi dedicated.

Di VPS 1 APP (atau node runner dengan akses database privat):
```bash
# Di VPS 1 APP:
CONFIRM_MIGRATION=YES PRE_MIGRATION_BACKUP_VERIFIED=YES \
  bash database/migration/migrate.sh --env-file /etc/alos/production/app.env
```
Script ini akan:
1. Memverifikasi konfirmasi pre-migration backup.
2. Memeriksa status skema saat ini (`alembic current`).
3. Menjalankan migrasi satu kali (`alembic upgrade head`) menggunakan kontainer sementara tanpa memulai replica background.
4. Memvalidasi head revision paska-migrasi.

### Langkah 4: Rilis Service Sesuai Urutan Aman (Safe Startup Order)

1. **Deploy VPS 2 (GENESIS)**:
   ```bash
   # Di VPS 2 GENESIS:
   docker compose --env-file /etc/alos/production/genesis.env pull
   docker compose --env-file /etc/alos/production/genesis.env up -d --remove-orphans
   bash scripts/health-check.sh --target genesis
   ```

2. **Deploy VPS 1 (APP)**:
   ```bash
   # Di VPS 1 APP:
   docker compose --env-file /etc/alos/production/app.env pull
   docker compose --env-file /etc/alos/production/app.env up -d --remove-orphans
   bash scripts/health-check.sh --target app
   ```

### Langkah 5: Verifikasi Paska-Deploy
1. Periksa status seluruh container:
   ```bash
   docker compose ps
   ```
2. Jalankan health check menyeluruh:
   ```bash
   bash scripts/health-check.sh --target all
   ```
3. Lakukan smoke test:
   - Akses UI web di browser via `https://${WEB_HOSTNAME}`.
   - Uji endpoint API publik via `https://${API_HOSTNAME}/health`.
   - Uji flow AI reasoning dan validasi private callback Backend ↔ GENESIS.

### Langkah 6: Jika Terjadi Masalah
Jika salah satu service gagal start atau terjadi lonjakan error 5xx, segera rujuk ke:
- [runbooks/rollback.md](rollback.md) untuk prosedur rollback aman.
- [runbooks/incident-response.md](incident-response.md) untuk eskalasi insiden.
