# Struktur Folder

- `environments/local/`: Compose build sibling repository, loopback Web/Backend, dan example env.
- `environments/staging/`: registry-image Compose dengan Caddy ingress dan environment staging.
- `environments/production/`: production-only image Compose, guard resource, read-only app, dan
  operator-required configuration.
- `services/web/`, `backend/`, `genesis/`: runtime ownership dan network boundary tiap service.
- `docker/`: shared Docker convention boundary; saat ini application Dockerfile tetap dimiliki
  repository aplikasi.
- `networking/ingress/`: public ingress policy Caddy.
- `networking/internal/`: internal/data network rules.
- `networking/firewall/`: provider-neutral firewall baseline.
- `reverse-proxy/caddy/`: Caddyfile Web/API tanpa GENESIS route.
- `database/postgres/`: server/container boundary dan pgvector extension initialization.
- `database/pgvector/`: extension ownership dan larangan application index definition di Infra.
- `database/tenant/`: tenant/data-role isolation boundary.
- `database/backup/`: guarded Bash/PowerShell backup dan checksum sidecar.
- `database/restore/`: checksum-verified, confirmation-gated Bash/PowerShell restore scripts.
- `object-storage/`: configuration-only integration boundary; tidak ada MinIO/service.
- `observability/otel/`: OTLP receiver, processors, dan baseline debug exporter.
- `security/secrets/`: secret injection/rotation rules.
- `security/tls/`: Caddy TLS dan operator responsibility.
- `security/policies/`: invariant keamanan deployment.
- `deployment/preflight/`: checklist sebelum perubahan environment.
- `deployment/staging/`: boundary deployment staging.
- `deployment/production/`: boundary deployment production dan larangan bootstrap auto-deploy.
- `rollback/`: application rollback boundary.
- `recovery/`: controlled recovery dan gap RPO/RTO/provider.
- `runbooks/`: deploy, rollback, restore, degraded service, dan incident procedure.
- `scripts/`: health check Web, Backend, internal GENESIS, dan PostgreSQL untuk Bash/PowerShell.
- `docs/`: instalasi, environment operation, networking, database, observability, serta recovery.
- `.github/`: config validation CI, CODEOWNERS, dan pull request checklist.
