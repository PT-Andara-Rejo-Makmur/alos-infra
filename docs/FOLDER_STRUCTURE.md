# Struktur Folder

- `environments/local/`: Compose build sibling repository, loopback Web/Backend, dan example env.
- `environments/integration/`: stack disposable untuk smoke, ARA TEST, worker dan browser E2E.
- `environments/staging/`: registry-image Compose 1 VPS full-stack dengan Caddy ingress, isolasi named volume, dan environment staging.
- `environments/production/`: konfigurasi terdistribusi multi-host 3 VPS:
  - `app/`: VPS 1 APP (Caddy, Web, Backend) dengan public ingress.
  - `genesis/`: VPS 2 GENESIS (genesis-ai) terisolasi tanpa route database.
  - `data/`: VPS 3 DATA (PostgreSQL + pgvector, named volume persistence).
- `services/web/`, `backend/`, `genesis/`: runtime ownership dan network boundary tiap service.
- `docker/`: shared Docker convention boundary; application Dockerfile tetap dimiliki repository aplikasi.
- `networking/ingress/`: public ingress policy Caddy.
- `networking/internal/`: internal/data network rules.
- `networking/firewall/`: provider-neutral firewall baseline dan panduan iptables/UFW per VPS.
- `reverse-proxy/caddy/`: Caddyfile Web/API tanpa GENESIS route.
- `database/Dockerfile`: kandidat PostgreSQL 16 Alpine + pgvector, source/checksum dan build dependencies dipin.
- `database/postgres/`: server/container boundary dan pgvector extension initialization.
- `database/pgvector/`: extension ownership dan larangan application index definition di Infra.
- `database/tenant/`: tenant/data-role isolation boundary.
- `database/backup/`: guarded Bash/PowerShell backup dan checksum sidecar, mendukung target multi-host.
- `database/restore/`: checksum-verified, confirmation-gated Bash/PowerShell restore scripts.
- `object-storage/`: configuration-only integration boundary; tidak ada MinIO/service.
- `observability/otel/`: OTLP receiver, processors, dan baseline debug exporter.
- `security/secrets/`: secret injection/rotation rules per-node role.
- `security/tls/`: Caddy TLS dan operator responsibility.
- `security/policies/`: invariant keamanan deployment.
- `deployment/preflight/`: checklist dan skrip validasi sebelum perubahan environment.
- `deployment/staging/`: boundary deployment staging.
- `deployment/production/`: boundary deployment production terdistribusi dan urutan rilis aman.
- `rollback/`: application rollback boundary terpisah dari database recovery.
- `recovery/`: controlled recovery dan gap RPO/RTO/provider.
- `runbooks/`: deploy, rollback, restore, degraded service, dan incident procedure.
- `scripts/`:
  - `health-check.sh` & `health-check.ps1`: health check multi-target (`local`, `app`, `genesis`, `data`, `staging`).
  - `preflight-check.py`: validasi kesiapan konfigurasi dan invariant secret sebelum deploy.
  - `verify-infra-topology.py`: regression suite topologi multi-host 4 VPS; jumlah invariant mengikuti output script.
  - `integration-smoke.py`: public deterministic stack integration smoke test.
  - `ara-smoke.py` dan `verify-ara-roundtrip.py`: pemeriksaan ARA melalui BFF/Backend/GENESIS.
  - `test-business-worker.py` dan `test-restore-proof.py`: proof worker serta restore pada target disposable.
  - `verify-image-security.py`, `test-image-security.py`, `test-preflight.py`: gate dan regresi konfigurasi/keamanan.
  - `verify-documentation.py`: link file Markdown kelima repository, termasuk pemeriksaan case Linux.
- `docs/`: dokumentasi instalasi, multi-host deployment, networking authority matrix, database, serta recovery.
- `.github/`: config validation CI multi-compose, CODEOWNERS, dan pull request checklist.

Log, screenshot, arsip review/pemulihan dan dump privat bukan source aplikasi dan tidak
dimasukkan ke Git. Bukti lokal Infra berada di `.audit/`; bukti browser berada pada
folder ignored di Web. File `.env` berisi konfigurasi privat; hanya `.env.example` dilacak.
