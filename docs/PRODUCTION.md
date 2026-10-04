# Panduan Deployment Production (APP, GENESIS, DATA dan Model Gateway)

Arsitektur production ALOS MVP-2 membagi beban kerja ke dalam tiga node VPS terpisah untuk menjamin pemisahan otoritas keamanan dan skalabilitas:

- **VPS 1 (APP)**: Menjalankan Caddy reverse proxy, `alos-web`, dan `alos-backend`.
- **VPS 2 (GENESIS)**: Menjalankan `genesis-ai` (ModelGateway & runtime AI terisolasi).
- **VPS 3 (DATA)**: Menjalankan database PostgreSQL dengan ekstensi `pgvector` dan backup process.
- **Model Gateway (node/layanan eksternal keempat)**: Profil model yang telah disahkan, diakses hanya oleh GENESIS melalui HTTPS; bukan ingress Web atau pemegang kredensial database. Rujuk [operasi gateway](model-gateway-operations.md).

Setiap VPS memiliki file `compose.yaml` dan `.env.example` terdedikasi di bawah direktori `environments/production/`.

---

## 1. Spesifikasi Node & Direktori Konfigurasi

### Node 1: VPS 1 — APP (`environments/production/app/`)
- **Tanggung Jawab**: Ingress publik, rendering UI, dan otoritas logika bisnis Backend.
- **Port Publik**: `80/tcp` (HTTP) dan `443/tcp` (HTTPS) yang dikelola oleh Caddy.
- **Port Internal & Private**:
  - Web (`3000`) dan Backend (`8000`) terdaftar di internal Docker bridge `edge`.
  - Backend mempublikasikan listener port `8000/tcp` pada interface private host (`APP_PRIVATE_BIND_IP`) khusus untuk menerima callback dari GENESIS (`BackendToolClient` & `BackendCancellationProbe`).
- **Variabel Wajib Operator**:
  - `ALOS_WEB_IMAGE`, `ALOS_BACKEND_IMAGE` (wajib immutable image digest).
  - `WEB_HOSTNAME`, `API_HOSTNAME`.
  - `APP_PRIVATE_BIND_IP` (IP private host VPS 1, wajib diisi, bukan loopback).
  - `ALOS_BACKEND_PORT=8000`.
  - `DATABASE_PRIVATE_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
  - `GENESIS_PRIVATE_HOST`, `GENESIS_PORT`, `GENESIS_INTERNAL_TOKEN`.

### Node 2: VPS 2 — GENESIS (`environments/production/genesis/`)
- **Tanggung Jawab**: Eksekusi reasoning kecerdasan buatan terisolasi.
- **Port Publik**: **TIDAK ADA**.
- **Port Private**: Port `8100/tcp` diikat ke IP private host (`GENESIS_BIND_IP`).
- **Isolasi Database**: Dilarang memiliki `DATABASE_URL` atau koneksi ke VPS 3 Data.
- **Variabel Wajib Operator**:
  - `GENESIS_IMAGE` (immutable digest).
  - `GENESIS_BIND_IP` (IP private host VPS 2, wajib diisi, bukan loopback).
  - `ALOS_BACKEND_BASE_URL` (menunjuk ke IP private VPS 1: `http://<APP_PRIVATE_BIND_IP>:8000` untuk tool execution & cancellation probe).
  - `ALOS_INTERNAL_TOKEN` (identik dengan `GENESIS_INTERNAL_TOKEN` di VPS 1).
  - `DEFAULT_MODEL_ROUTE=nine_router` sesuai Compose GENESIS. Preflight mewajibkan HTTPS, key privat dan setidaknya satu profil; `disabled` adalah kill switch eksplisit, bukan bukti kesiapan produksi.

### Node 3: VPS 3 — DATA (`environments/production/data/`)
- **Tanggung Jawab**: Persistensi database relasional dan vector, WAL storage, serta proses backup.
- **Port Publik**: **TIDAK ADA**.
- **Port Private**: Port `5432/tcp` diikat ke IP private host (`POSTGRES_BIND_IP`).
- **Akses Diizinkan**: Hanya menerima koneksi inbound dari IP private VPS 1. Akses dari VPS 2 (GENESIS) ditolak.
- **Variabel Wajib Operator**:
  - `POSTGRES_IMAGE=<registry>/alos-postgres@sha256:<64-hex>`: image hasil `database/Dockerfile`, wajib scan dan restore proof sebelum rilis. Jangan memakai fallback mutable `pgvector:pg16` untuk deployment.
  - `POSTGRES_BIND_IP` (IP private host VPS 3, wajib diisi, bukan loopback).
  - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.

### Kandidat image database development

`database/Dockerfile` membangun PostgreSQL 16 pada Alpine dengan pgvector 0.8.7 dari
commit dan checksum sumber yang dipin, serta gosu 1.19 yang dibangun ulang dengan Go
1.27.1. Compiler tidak disalin ke runtime. CI membangun, memindai, dan menguji script
backup/restore sesungguhnya, termasuk HNSW/IVFFlat dan query nearest-vector.

Image ini sudah diuji pada database audit baru. Database operasional yang berasal
dari image Debian harus menjalani logical dump/restore ke volume staging baru,
verifikasi collation/index, penerimaan aplikasi dan rollback sebelum beralih basis
OS. Jangan mengganti image pada volume operasional hanya berdasarkan scan bersih.
Build lokal tidak menghasilkan digest registry yang bisa dideploy; operator harus
menetapkan digest artifact rilis yang telah disahkan.

---

---

## 2. Model Operasi Rahasia (/etc/alos/)

Pada host VPS nyata, kredensial sensitif disimpan di luar repository git dengan permission `0600`:
- VPS 1: `/etc/alos/production/app.env`
- VPS 2: `/etc/alos/production/genesis.env`
- VPS 3: `/etc/alos/production/data.env`

Jalankan compose dengan menyertakan flag `--env-file /etc/alos/production/<node>.env`.
Rujuk ke [security/secrets/README.md](../security/secrets/README.md) untuk detail panduan pengelolaan rahasia.

---

## 3. Urutan Deployment Paling Aman (Safe Deployment Order)

Untuk mencegah race condition dan kegagalan startup layanan, ikuti urutan rilis baku:

```text
Langkah 1: Safety Backup di VPS 3 (DATA)
          -> Jalankan: bash database/backup/backup.sh
          -> Verifikasi checksum SHA-256 sidecar

Langkah 2: Preflight Enforcement Check
          -> Jalankan: python scripts/preflight-check.py --target all
          -> Verifikasi immutability image dan kelengkapan secret

Langkah 3: Eksekusi Migrasi Database Tunggal
          -> Jalankan: CONFIRM_MIGRATION=YES PRE_MIGRATION_BACKUP_VERIFIED=YES \
                       bash database/migration/migrate.sh --env-file /etc/alos/production/app.env
          -> Verifikasi skema head revision selesai sebelum memulai backend

Langkah 4: Deploy VPS 2 (GENESIS)
          -> Jalankan container genesis-ai
          -> Verifikasi healthcheck internal: GET /health

Langkah 5: Deploy VPS 1 (APP)
          -> Jalankan container Backend, Web, dan Caddy
          -> Backend terhubung ke PostgreSQL (VPS 3) dan GENESIS (VPS 2)
          -> Caddy membuka traffic publik setelah Web & Backend dinyatakan healthy

Langkah 6: Smoke Test & Verifikasi End-to-End
          -> Jalankan validasi login, navigasi, dan flow correlation ID
```

---

## 4. Preflight & Verifikasi Sebelum Deploy

Sebelum menjalankan `docker compose up -d` di setiap node, jalankan validasi preflight:

```bash
# Di VPS 1 APP:
python scripts/preflight-check.py --target app

# Di VPS 2 GENESIS:
python scripts/preflight-check.py --target genesis

# Di VPS 3 DATA:
python scripts/preflight-check.py --target data
```

---

## 5. Kebijakan Immutability & Contracts

1. Seluruh image production (`ALOS_WEB_IMAGE`, `ALOS_BACKEND_IMAGE`, `GENESIS_IMAGE`) wajib menggunakan cryptographic digest pinning (misal: `@sha256:...`). Dilarang menggunakan tag mutable seperti `:latest`.
2. Image Backend dan GENESIS wajib membundel canonical contract di direktori `/contracts` dan menggunakan variabel lingkungan `ALOS_CONTRACTS_PATH=/contracts`.
3. Web image wajib dibangun menggunakan generated TypeScript dari revisi contract yang sama.
4. Rujuk [runbooks/rollback.md](../runbooks/rollback.md) jika diperlukan pemulihan rilis darurat.
