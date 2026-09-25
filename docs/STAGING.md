# Panduan Deployment Staging (VPS 4 Full-Stack)

Environment Staging diimplementasikan sebagai **1 VPS mandiri terisolasi (VPS 4)** yang menjalankan seluruh stack ALOS dalam satu Docker daemon host, dengan segregasi jaringan internal (`edge`, `internal`, `data`).

## 1. Tanggung Jawab & Arsitektur VPS 4

- **Node**: VPS 4 STAGING
- **Services**: Caddy, `alos-web`, `alos-backend`, `genesis-ai`, PostgreSQL + pgvector, OpenTelemetry Collector.
- **Port Publik**: Hanya port `80/tcp` dan `443/tcp` pada Caddy yang dibuka ke internet publik (khusus domain staging).
- **Port Internal**: Port 3000, 8000, 8100, 5432, dan 4317 dilarang dipublikasikan ke host interface publik.
- **Segregasi Jaringan**:
  - `edge`: Caddy, Web, Backend.
  - `internal` (`internal: true`): Backend, GENESIS, OTEL Collector.
  - `data` (`internal: true`): Backend, PostgreSQL.

---

## 2. Invariant Isolasi terhadap Production

Staging dilarang keras berinteraksi dengan komponen production:
1. **Database & Volume**: Staging menggunakan named volume lokal (`postgres-data` di dalam project `alos-staging`). Dilarang menghubungkan staging Backend ke VPS 3 Production Data.
2. **Kredensial**: `POSTGRES_PASSWORD` dan `GENESIS_INTERNAL_TOKEN` staging harus bernilai acak dan terpisah dari production secrets.
3. **Domain / Hostname**: Wajib menggunakan subdomain staging khusus (misal: `staging.alos.id` dan `staging-api.alos.id`), tidak boleh menggunakan domain production.
4. **Model Route**: Menggunakan `DEFAULT_MODEL_ROUTE=disabled` secara default.

---

## 3. Parity Hardening dengan Production

Untuk memastikan parity yang akurat dengan production:
- Seluruh container aplikasi (`web`, `backend`, `genesis`, `otel-collector`) menerapkan `read_only: true` dan `tmpfs: [/tmp]`.
- Resource limits (`deploy.resources.limits`) dideklarasikan secara eksplisit untuk mencegah overcommit sumber daya pada VPS 4.
- Healthcheck aktif pada setiap container.

---

## 4. Cara Menjalankan Staging

1. Masuk ke direktori staging dan siapkan `.env`:
   ```bash
   cd environments/staging
   cp .env.example .env
   # Isi dengan image references dan kredensial staging
   ```
2. Jalankan validasi preflight staging:
   ```bash
   python ../../scripts/preflight-check.py --target staging
   ```
3. Validasi konfigurasi Compose dan jalankan stack:
   ```bash
   docker compose --env-file .env config --quiet
   docker compose --env-file .env pull
   docker compose --env-file .env up -d
   ```
4. Periksa kesehatan seluruh service staging:
   ```bash
   bash ../../scripts/health-check.sh --target staging
   # atau PowerShell:
   ..\..\scripts\health-check.ps1 -Target staging
   ```
