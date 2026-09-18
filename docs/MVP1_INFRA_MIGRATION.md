# Migrasi Infrastruktur MVP-1

Audit dilakukan terhadap `andara-alos-ai/alos` branch `develop` pada pinned commit
`01416390287114a451a22e16ff14e493df43362f`. Source tidak diubah dan branch `main` tidak
digunakan. Audit mencakup 45 file di `infra/` serta script dan runbook operasional MVP-1 yang
berhubungan dengan deployment, health, backup, dan restore.

## Keputusan migrasi

| Sumber MVP-1 | Keputusan | Implementasi target |
|---|---|---|
| `infra/compose/*.yaml` | ADAPT | Compose dipisahkan menjadi local, staging, dan production untuk Web, Backend, GENESIS, PostgreSQL, Caddy, serta OTEL. |
| `infra/proxy/Caddyfile*` | ADAPT | Caddy hanya memiliki upstream Web dan Backend. Tidak ada route GENESIS atau PostgreSQL. |
| `infra/environments/*` | ADAPT | `.env.example` per environment tanpa credential nyata. |
| `infra/database/001_*.sql`–`024_*.sql` | DO NOT MIGRATE | Application migration dimiliki repository aplikasi, bukan Infra. |
| `infra/docker/platform.Dockerfile` | DEPRECATE | Image monolith tidak dipakai; Dockerfile dimiliki `alos-backend` dan `genesis-ai`. |
| `infra/docker/web.Dockerfile` | DEPRECATE | Dockerfile Web dimiliki `alos-web`; Infra hanya melakukan wiring image/build context. |
| `infra/systemd/*` | DEPRECATE | Path/user host legacy tidak dibawa. Compose adalah baseline deployment saat ini. |
| Placeholder identity/object-storage/observability/secrets | ADAPT | Hanya boundary dan dokumentasi nyata yang dipertahankan; tidak menambahkan MinIO atau monitoring stack lain. |
| Backup dan restore script MVP-1 | ADAPT | Custom-format `pg_dump`, SHA-256 sidecar, confirmation gate, cleanup, dan verification query. |
| Preflight dan deployment knowledge | ADAPT | CI validation, preflight checklist, dan runbook tanpa deployment otomatis. |
| Script reset destructive | DO NOT MIGRATE | Tidak dibawa ke baseline. |

## Boundary hasil migrasi

```text
Internet -> Caddy -> Web
                  -> Backend -> GENESIS (internal)
                           -> PostgreSQL (data)
```

- Web hanya berada di network edge dan tidak menerima URL atau token GENESIS.
- Backend berada di edge, internal, dan data sehingga menjadi penghubung resmi ke GENESIS dan
  pemilik akses database bisnis.
- GENESIS hanya berada di network internal, tanpa port host, network data, `DATABASE_URL`, atau
  dependency startup ke PostgreSQL.
- PostgreSQL hanya berada di network data dan tidak mempublikasikan port host.
- Staging/production hanya memakai prebuilt application image dan tidak menjalankan development
  server.

## Pengetahuan yang dipertahankan

- Healthcheck setiap service dan health script lintas service.
- PostgreSQL custom-format backup serta integrity sidecar.
- Restore yang membutuhkan approval eksplisit dan checksum valid.
- Image rollback terpisah dari database recovery.
- Caddy security header dan public routing.
- Correlation flow Web → Backend → GENESIS → Tool → Backend.
- OpenTelemetry sebagai configuration boundary saja.

## Keterbatasan

- Docker Engine tidak tersedia pada host audit ini; validasi penuh `docker compose config` dan
  `caddy validate` tetap dijalankan oleh GitHub Actions dan harus dijalankan operator sebelum
  deployment.
- Production image digest, DNS, TLS, secret manager, backup provider, retention, RPO/RTO, HA,
  alerting destination, dan object-storage provider belum ditentukan.
- `NEXT_PUBLIC_ALOS_API_BASE_URL` harus sudah benar ketika image Web dibangun. Runtime environment
  tidak boleh diasumsikan dapat mengubah nilai public yang telah dibundel oleh Next.js.
- Restore production tetap memerlukan isolated restore drill dan application invariant checks;
  checksum saja bukan bukti compatibility.

