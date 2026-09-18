# ALOS Infrastructure

`alos-infra` adalah source of truth untuk local runtime, staging/production deployment
configuration, networking, reverse proxy, PostgreSQL/pgvector, service wiring, observability,
secrets interface, backup, restore, rollback, dan operational runbook ekosistem ALOS.

Repository ini tidak memiliki application migration, business logic, AI reasoning, frontend
source, atau production secret.

## Arsitektur

```text
Internet
   |
   v
 Caddy --------> alos-web
   |
   +-----------> alos-backend --------> genesis-ai
                         |              (internal network)
                         |
                         +-----------> PostgreSQL
                                       (data network)
```

Hanya Caddy yang menjadi ingress staging/production. GENESIS dan PostgreSQL tidak menerbitkan
host port. Browser berkomunikasi dengan Backend melalui public Backend hostname, bukan GENESIS.

## Prasyarat

- Git
- Docker Engine dengan Docker Compose v2
- Bash untuk script Unix atau PowerShell 7 untuk script Windows
- Sibling repository `alos-contracts`, `alos-backend`, `genesis-ai`, dan `alos-web`
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

Local Compose dijalankan dari `alos-infra/environments/local/` dan build context menunjuk ke
repository sibling. Build Backend, GENESIS, dan Web juga memakai named build context `contracts`
dari `alos-contracts`. Nama folder tersebut harus dipertahankan atau path Compose perlu disesuaikan.

## Menjalankan local — Windows PowerShell

```powershell
Set-Location alos-infra\environments\local
Copy-Item .env.example .env
# Isi POSTGRES_PASSWORD dan GENESIS_INTERNAL_TOKEN dengan nilai development lokal.
docker compose config
docker compose up --build -d
..\..\scripts\health-check.ps1
```

## Menjalankan local — Linux/macOS

```bash
cd alos-infra/environments/local
cp .env.example .env
# Isi POSTGRES_PASSWORD dan GENESIS_INTERNAL_TOKEN dengan nilai development lokal.
docker compose config
docker compose up --build -d
bash ../../scripts/health-check.sh
```

Web tersedia di `http://127.0.0.1:3000` dan Backend di `http://127.0.0.1:8000` dengan default
port example. GENESIS `:8100` dan PostgreSQL `:5432` hanya tersedia pada internal container
network; health script memeriksanya melalui `docker compose exec`.

## Operasi local

```bash
docker compose ps
docker compose logs -f --tail=200
docker compose stop
docker compose down
```

Jangan memakai `down --volumes` kecuali data development memang boleh dihapus.

## Environment files dan secret

Salin `.env.example` menjadi `.env` pada environment yang dipilih. File `.env` diabaikan Git.
Nilai kosong adalah interface yang harus diisi operator; contoh tidak berisi production secret.
Untuk staging/production, inject secret melalui deployment environment atau secret manager yang
disetujui organisasi, bukan melalui commit atau image layer.

Variable minimal meliputi PostgreSQL, port service, internal token GENESIS, object-storage
boundary, OpenTelemetry, image reference, dan hostname Caddy. Lihat file example masing-masing.

## Database

Infra memiliki PostgreSQL server/container, pgvector availability, volume, healthcheck, backup,
dan restore tooling. `alos-backend` memiliki schema serta migration authoritative business state.
GENESIS tidak memperoleh route atau credential database bisnis pada baseline ini. Persistence AI
di masa depan harus memakai ownership dan boundary terpisah melalui keputusan arsitektur eksplisit.
Tidak ada application migration pada repository ini.

Backup lokal/manual menghasilkan custom-format `pg_dump` beserta sidecar SHA-256. Restore
memverifikasi checksum terlebih dahulu, memerlukan konfirmasi eksplisit, dan menjalankan verification
setelah restore. Provider, retention scheduler, encryption key, off-site copy, dan immutable storage
belum disediakan oleh bootstrap.

## Staging dan production

Compose staging/production hanya menerima immutable application image melalui environment dan
tidak menjalankan development server atau source bind mount. Operator wajib mengisi hostname,
image digest/tag, database credential, internal token, volume/backup target, dan TLS/DNS.
Image Backend dan GENESIS wajib dibangun dengan canonical contract yang dibundel di `/contracts`;
image Web wajib dibangun dengan generated TypeScript dari revision contract yang sama. Release
pipeline harus mencatat revision/tag `alos-contracts` yang dipakai dan memverifikasi
`/contracts/VERSION` sebelum image dipromosikan.

Validasi sebelum deployment:

```bash
docker compose --env-file .env -f compose.yaml config --quiet
```

CI memvalidasi Compose/Caddy/script, membangun ketiga application image dengan contract context,
dan memeriksa contract catalog pada runtime image. CI tidak melakukan deployment.

## Rollback dan recovery

Rollback aplikasi menggunakan image sebelumnya setelah compatibility check. Database rollback
tidak disamakan dengan application rollback; gunakan restore hanya sebagai controlled recovery
setelah backup, approval, dan verification plan tersedia.

Runbook: [Deploy](runbooks/deploy.md), [Rollback](runbooks/rollback.md),
[Restore](runbooks/restore.md), [GENESIS down](runbooks/genesis-down.md),
[Backend down](runbooks/backend-down.md), dan
[Incident response](runbooks/incident-response.md).

## Keamanan dan observability

- Caddy adalah satu-satunya ingress staging/production.
- GENESIS hanya berada pada network `internal`; PostgreSQL hanya berada pada network `data`.
- Frontend tidak menerima GENESIS URL atau internal token.
- Backend menjadi satu-satunya application caller ke GENESIS.
- OTLP receiver hanya tersedia pada internal network.
- `correlation_id` mengalir Web → Backend → GENESIS → Tool → Backend.

## Dokumentasi

Lihat [Arsitektur](ARCHITECTURE.md), [Local Development](docs/LOCAL_DEVELOPMENT.md),
[Networking](docs/NETWORKING.md), [Database](docs/DATABASE.md),
[Observability](docs/OBSERVABILITY.md), [Backup/Restore](docs/BACKUP_RESTORE.md), dan
[Struktur Folder](docs/FOLDER_STRUCTURE.md). Keputusan adaptasi terhadap konfigurasi MVP-1 dicatat
di [Migrasi Infrastruktur MVP-1](docs/MVP1_INFRA_MIGRATION.md).
