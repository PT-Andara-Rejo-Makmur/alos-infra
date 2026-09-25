# ALOS Infrastructure

`alos-infra` adalah source of truth untuk local runtime, staging/production deployment
configuration, networking, reverse proxy, PostgreSQL/pgvector, service wiring, observability,
secrets interface, backup, restore, rollback, dan operational runbook ekosistem ALOS.

Repository ini tidak memiliki application migration, business logic, AI reasoning, frontend
source, atau production secret.

## Arsitektur Target MVP-2 (Multi-Host 4 VPS)

```text
[ INTERNET ]
     |
     | (Port 80/443 Public)
     v
========================================================================
[ PRODUCTION - VPS 1: APP ]
  - Ingress: Caddy (Reverse Proxy, TLS Management)
  - Web: alos-web (Next.js SSR/BFF, port container 3000)
  - Backend: alos-backend (FastAPI Otoritas Utama, port container 8000)
    * Public via Caddy: https://api.<domain>
    * Private listener: APP_PRIVATE_BIND_IP:8000 (GENESIS callback)
========================================================================
        |   ^                                   |
        |   | Private Net                       | Private Net
        |   | (Outbound 8100 / Callback 8000)   | (TCP 5432)
        v   |                                   v
====================================   =================================
[ PRODUCTION - VPS 2: GENESIS ]        [ PRODUCTION - VPS 3: DATA ]
  - Service: genesis-ai (Port 8100)      - Database: PostgreSQL + pgvector
  - Intelligence / ModelGateway          - Storage: Named Volume Persistence
  - BackendToolClient -> VPS 1 :8000     - Backup: pg_dump Custom + Checksum
  - ISOLATED: No Public Ports,           - ISOLATED: No Public Ports,
              No DB Network / Route                  No Internet Inbound
====================================   =================================

------------------------------------------------------------------------
[ STAGING - VPS 4: STAGING (Single Host Isolate) ]
  - Caddy Ingress (Staging Hostnames)
  - Web Staging | Backend Staging | GENESIS Staging | PostgreSQL Staging
  - 100% Terpisah dari Credential, Volume, dan Jaringan Production
------------------------------------------------------------------------
```

### Prinsip Otoritas Jaringan:
- **Web -> Backend -> GENESIS**: Web frontend hanya berbicara ke Backend API. Tidak ada rute langsung Web ke GENESIS.
- **Backend = Authority**: Backend adalah satu-satunya entitas yang berwenang mengakses database bisnis dan memanggil GENESIS.
- **GENESIS -> Backend Callback**: GENESIS memanggil endpoint internal Backend (`:8000`) hanya melalui interface private untuk eksekusi tools (`BackendToolClient`) dan pengecekan pembatalan (`BackendCancellationProbe`).
- **GENESIS = Intelligence**: GENESIS tidak memiliki akses fisik/jaringan ke database bisnis (`GENESIS DENY DB`).
- **No Public Database/AI/Backend-Callback Exposure**: Port GENESIS (8100), PostgreSQL (5432), dan listener private Backend (8000) dilarang dibuka ke internet publik.

## Prasyarat

- Git
- Docker Engine dengan Docker Compose v2
- Python 3.10+
- Bash untuk script Unix atau PowerShell 7 untuk script Windows
- Sibling repository `alos-contracts`, `alos-backend`, `genesis-ai`, dan `alos-web` (untuk local build)
- Docker BuildKit/buildx yang mendukung named build context

## Layout workspace

```text
alos-workspace/
├── alos-contracts/
├── alos-backend/
├── genesis-ai/
├── alos-web/
└── alos-infra/
```

## Lingkungan Deployment

Repository ini menyediakan konfigurasi terisolasi:

1. **Local Development** (`environments/local/`):
   Membangun sibling repository secara lokal, mengekspos Web (`3000`) dan Backend (`8000`) ke loopback host. GENESIS dan PostgreSQL tetap container-internal.
2. **Production Multi-Host** (`environments/production/`):
   - `app/` (VPS 1): Caddy, Web, Backend (`compose.yaml`, `.env.example`).
   - `genesis/` (VPS 2): `genesis-ai` terisolasi (`compose.yaml`, `.env.example`).
   - `data/` (VPS 3): PostgreSQL + pgvector, backup (`compose.yaml`, `.env.example`).
3. **Staging** (`environments/staging/`):
   1 VPS full stack untuk pengujian end-to-end sebelum promosi ke production.

## Menjalankan Local

### Windows PowerShell:
```powershell
Set-Location environments\local
Copy-Item .env.example .env
# Isi POSTGRES_PASSWORD dan GENESIS_INTERNAL_TOKEN dengan nilai development lokal.
docker compose config
docker compose up --build -d
..\..\scripts\health-check.ps1
```

### Linux/macOS:
```bash
cd environments/local
cp .env.example .env
# Isi POSTGRES_PASSWORD dan GENESIS_INTERNAL_TOKEN dengan nilai development lokal.
docker compose config
docker compose up --build -d
bash ../../scripts/health-check.sh
```

## Operasi & Verifikasi Multi-Host

### Preflight Check Sebelum Deployment:
```bash
python scripts/preflight-check.py --target all
```

### Pengujian Regresi Topologi Multi-Host (15 Invariant):
```bash
python scripts/verify-infra-topology.py
```

### Health Check per Node:
```bash
# Bash:
bash scripts/health-check.sh --target app
bash scripts/health-check.sh --target genesis
bash scripts/health-check.sh --target data
bash scripts/health-check.sh --target staging

# PowerShell:
.\scripts\health-check.ps1 -Target app
.\scripts\health-check.ps1 -Target genesis
.\scripts\health-check.ps1 -Target data
.\scripts\health-check.ps1 -Target staging
```

## Database & Backup

- Infra mengelola container PostgreSQL, inisialisasi pgvector, named volume, dan script backup/restore.
- Backend memiliki schema serta migration Alembic.
- Script backup [database/backup/backup.sh](database/backup/backup.sh) membuat custom-format `pg_dump` dengan verifikasi sidecar SHA-256.
- Script restore [database/restore/restore.sh](database/restore/restore.sh) mensyaratkan `CONFIRM_DATABASE_RESTORE=YES` dan validasi checksum sebelum restore.

## Dokumentasi Terkait

- [Arsitektur Umum](ARCHITECTURE.md)
- [Networking & Authority Matrix](docs/NETWORKING.md)
- [Panduan Production 3 VPS](docs/PRODUCTION.md)
- [Panduan Staging](docs/STAGING.md)
- [Database & Boundary](docs/DATABASE.md)
- [Backup & Restore](docs/BACKUP_RESTORE.md)
- [Struktur Folder](docs/FOLDER_STRUCTURE.md)
- [Preflight Checklist](deployment/preflight/README.md)
