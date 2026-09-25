# Runbook Incident Response & Disaster Recovery (DR) ALOS

Dokumen ini adalah panduan penanganan insiden operasional dan pemulihan bencana (*disaster recovery*) untuk infrastruktur ALOS MVP-2 (Multi-Host 4 VPS).

> [!IMPORTANT]
> **Batasan Arsitektur MVP-2:**
> Sistem saat ini belum memiliki cluster HA otomatis (*no automatic failover*). Seluruh pemulihan host fisik dilakukan secara manual dan terkendali oleh operator berwenang.

Setiap skenario insiden wajib ditangani dengan metodologi baku:
**DETECT → CONTAIN → RECOVER → VERIFY → RECORD**

---

## 1. Skenario 1: Node APP (VPS 1) Mati / Crash

- **DETECT**:
  - Uptime monitoring mendeteksi HTTPS 502/504 atau timeout pada `WEB_HOSTNAME` dan `API_HOSTNAME`.
  - Host VPS 1 tidak merespons ping / SSH.
- **CONTAIN**:
  - Alihkan DNS / load balancer sementara ke maintenance static page jika tersedia.
  - Verifikasi bahwa VPS 2 (GENESIS) dan VPS 3 (DATA) tidak mengalami cascading failure.
- **RECOVER**:
  1. Akses cloud console provider (VPC dashboard) dan periksa status hardware/hypervisor host.
  2. Lakukan reboot host fisik via cloud console.
  3. Jika host rusak total (*unrecoverable hardware loss*):
     - Provision VPS 1 pengganti di subnet VPC yang sama.
     - Konfigurasi firewall host (UFW) dan binding private IP.
     - Deploy service via `environments/production/app/compose.yaml` menggunakan file rahasia `/etc/alos/production/app.env`.
- **VERIFY**:
  - Jalankan `health-check.sh --target app`.
  - Akses `https://${API_HOSTNAME}/health` dan `https://${WEB_HOSTNAME}`.
  - Verifikasi log Caddy (`docker compose logs -f caddy`).
- **RECORD**:
  - Catat durasi downtime, penyebab kegagalan host pada tiket post-mortem, dan periksa apakah ada request in-flight yang terputus.

---

## 2. Skenario 2: Node GENESIS (VPS 2) Mati / Crash

- **DETECT**:
  - Backend mencatat error timeout atau connection refused pada panggilan `GENESIS_BASE_URL` (`:8100`).
  - Metrik correlation ID menunjukkan kegagalan pada stage delegasi AI.
- **CONTAIN**:
  - Backend secara elegan mengembalikan pesan degraded service kepada pengguna bahwa fitur AI sementara tidak tersedia (logika bisnis non-AI tetap berjalan normal).
- **RECOVER**:
  1. Periksa container status di VPS 2: `docker compose ps`.
  2. Jika container crash karena OOM: periksa memory limits dan restart:
     ```bash
     docker compose --env-file /etc/alos/production/genesis.env up -d
     ```
  3. Jika host VPS 2 mati: reboot host atau provision ulang node GENESIS. Karena GENESIS bersifat stateless (tidak menyimpan database), node dapat diredeploy langsung menggunakan image immutable yang sama.
- **VERIFY**:
  - Jalankan `health-check.sh --target genesis`.
  - Cek health endpoint internal: `curl -fsS http://127.0.0.1:8100/health`.
  - Lakukan uji panggilan delegasi dari Backend ke GENESIS dan pastikan private callback kembali ke Backend berfungsi normal.
- **RECORD**:
  - Dokumentasikan spike memory/CPU yang memicu crash jika disebabkan oleh workload AI model.

---

## 3. Skenario 3: Node DATA (VPS 3) Mati / Crash

- **DETECT**:
  - Backend mencatat error `asyncpg.CannotConnectNowError` atau connection refused ke `DATABASE_PRIVATE_HOST:5432`.
  - Seluruh endpoint API yang membutuhkan persistensi menghasilkan HTTP 500.
- **CONTAIN**:
  - Segera set Caddy di VPS 1 ke mode maintenance page untuk menghentikan traffic write baru ke database yang sedang tidak stabil.
- **RECOVER**:
  1. Akses console VPS 3 DATA.
  2. Periksa status Docker daemon dan disk storage: `df -h` (pastikan disk volume database tidak penuh 100%).
  3. Periksa container PostgreSQL: `docker compose ps` dan logs: `docker compose logs postgres`.
  4. Lakukan restart container database:
     ```bash
     docker compose --env-file /etc/alos/production/data.env up -d postgres
     ```
  5. Jika volume fisik rusak: rujuk ke Skenario 4 (Database Corruption / Restore).
- **VERIFY**:
  - Uji kesiapan database: `docker compose exec postgres pg_isready -U alos_user -d alos_production`.
  - Verifikasi query: `docker compose exec postgres psql -U alos_user -d alos_production -c "SELECT 1;"`.
  - Buka kembali traffic di VPS 1 dan verifikasi konektivitas Backend.
- **RECORD**:
  - Catat log disk I/O, status WAL, dan durasi unavailability database.

---

## 4. Skenario 4: Kerusakan Data PostgreSQL (Corruption / Restore Required)

- **DETECT**:
  - PostgreSQL log melaporkan disk block corruption, checksum failure, atau data drop tak sengaja oleh operator.
- **CONTAIN**:
  - **ISOLATE IMMEDIATELY**: Matikan Backend di VPS 1 untuk menghentikan seluruh transaksi menulis:
    ```bash
    # Di VPS 1 APP:
    docker compose stop backend
    ```
- **RECOVER**:
  1. Tentukan restore target snapshot terkini dari direktori backup `/opt/alos/backups/` atau off-site storage.
  2. Verifikasi ketersediaan dan keabsahan checksum SHA-256 sidecar file dump.
  3. Lakukan snapshot darurat dari state database rusak saat ini sebelum menimpa data:
     ```bash
     bash database/backup/backup.sh
     ```
  4. Jalankan controlled restore dengan guard eksplisit:
     ```bash
     CONFIRM_DATABASE_RESTORE=YES CONFIRM_PRODUCTION=YES \
       bash database/restore/restore.sh /opt/alos/backups/alos-db-latest.dump \
       --target-db alos_production --confirm-production
     ```
- **VERIFY**:
  - Verifikasi extension vector: `SELECT extname FROM pg_extension WHERE extname = 'vector';`.
  - Verifikasi table counts dan status revisi Alembic: `alembic current`.
  - Jalankan test query read-only.
  - Nyalakan kembali Backend di VPS 1 dan jalankan smoke test.
- **RECORD**:
  - Catat RPO (Recovery Point Objective) dan RTO (Recovery Time Objective) aktual pada laporan insiden.

---

## 5. Skenario 5: Token Internal Terkompromi (Compromised Secret / Leak)

- **DETECT**:
  - Ditemukan indikasi kebocoran `GENESIS_INTERNAL_TOKEN` atau `POSTGRES_PASSWORD` (mis. terekspos di log publik atau repositori).
- **CONTAIN**:
  - Segera batasi network ingress firewall hanya ke IP terpercaya.
- **RECOVER**:
  - Lakukan prosedur rotasi darurat sesuai panduan [security/secrets/README.md](../security/secrets/README.md):
    - Untuk `GENESIS_INTERNAL_TOKEN`: buat token baru 32-byte hex, update file env di VPS 1 dan VPS 2, restart terkendali, dan invalidasi token lama.
    - Untuk `POSTGRES_PASSWORD`: ubah password di PostgreSQL engine, perbarui file env di VPS 1 dan VPS 3, restart Backend.
- **VERIFY**:
  - Pastikan panggilan menggunakan token lama ditolak dengan HTTP 401/403.
  - Pastikan Backend dan GENESIS berkomunikasi normal menggunakan token baru.
- **RECORD**:
  - Lakukan audit log akses selama periode token terkompromi untuk mendeteksi potensi eksfiltrasi data.

---

## 6. Skenario 6: Bad Deployment Rilis Aplikasi

- **DETECT**:
  - Paska deployment rilis baru, terjadi lonjakan HTTP 5xx, error regression, atau startup crash loop pada container `web` atau `backend`.
- **CONTAIN**:
  - Hentikan promosi traffic ke rilis baru.
- **RECOVER**:
  - Rujuk ke [runbooks/rollback.md](rollback.md):
    1. Periksa apakah rilis baru menyertakan migrasi skema database yang tidak backward-compatible.
    2. Jika skema kompatibel: deploy ulang previous known-good immutable image references.
    3. Jika skema tidak kompatibel: tentukan apakah perlu rollback database migration via Alembic downgrade atau restore database.
- **VERIFY**:
  - Jalankan health-check dan smoke test end-to-end.
- **RECORD**:
  - Tandai digest image yang rusak sebagai blacklisted dan buat regression test baru.

---

## 7. Skenario 7: Kegagalan Migrasi Database (Migration Failure)

- **DETECT**:
  - Skrip migrasi `database/migration/migrate.sh` gagal dengan exit code non-zero saat menjalankan `alembic upgrade head`.
- **CONTAIN**:
  - Jangan jalankan rilis Backend baru. Jangan nyalakan container Backend dengan versi baru.
- **RECOVER**:
  1. Baca log error Alembic secara teliti (sintaks DDL, lock timeout, constraint violation).
  2. Database masih berada pada state sebelum migrasi atau partial migration.
  3. Jika migrasi gagal di tengah transaksi:
     - Jika database mendukung transactional DDL (PostgreSQL mendukung sebagian besar DDL dalam transaksi): verifikasi apakah rollback otomatis terjadi.
     - Jika skema berada dalam state inconsistent: lakukan restore dari pre-migration backup yang diambil sesaat sebelum migrasi.
  4. Perbaiki script migrasi pada repository aplikasi sebelum mencoba kembali.
- **VERIFY**:
  - Jalankan `docker compose run --rm --no-deps backend alembic current` untuk memastikan head revision konsisten.
- **RECORD**:
  - Laporkan bug migrasi kepada tim backend engineer.

---

## 8. Skenario 8: Gangguan Konektivitas Private Network (Split-Brain / Network Partition)

- **DETECT**:
  - VPS 1 tidak dapat mencapai VPS 2 (`:8100`) atau VPS 3 (`:5432`), namun seluruh node aktif saat diakses via console/SSH.
- **CONTAIN**:
  - Periksa interface jaringan host (`ip addr`, `ip route`).
- **RECOVER**:
  1. Periksa firewall host (UFW / iptables):
     ```bash
     sudo ufw status verbose
     sudo iptables -L DOCKER-USER -n -v
     ```
  2. Periksa routing table provider / VPC peering / security group rules di dashboard cloud console.
  3. Pastikan tidak ada IP conflict atau lease DHCP private IP yang berubah.
  4. Lakukan ping dan traceroute antar IP private host.
- **VERIFY**:
  - Uji koneksi TCP: `nc -zv <PRIVATE_IP_GENESIS> 8100` dan `nc -zv <PRIVATE_IP_DATA> 5432` dari VPS 1.
  - Uji koneksi callback: `nc -zv <PRIVATE_IP_APP> 8000` dari VPS 2.
- **RECORD**:
  - Dokumentasikan outage jaringan provider dan verifikasi durasi MTTR.
