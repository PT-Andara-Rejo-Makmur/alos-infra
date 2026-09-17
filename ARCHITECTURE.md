# Arsitektur Infrastruktur ALOS

## Authority dan ownership

Infra memiliki runtime topology, container, network, volume, ingress, health, telemetry wiring,
backup mechanism, serta operational procedure. Infra tidak memiliki business schema, migration,
permission policy, AI orchestration, atau release decision.

## Network zones

```text
public ingress: Internet -> Caddy
edge network:   Caddy <-> Web / Backend
internal:       Backend <-> GENESIS / OpenTelemetry
data network:   Backend / GENESIS <-> PostgreSQL
```

Network `internal` dan `data` menggunakan `internal: true`. GENESIS, PostgreSQL, dan OTLP tidak
memiliki `ports` pada staging/production. Web hanya menerima public Backend URL dan tidak menjadi
anggota network internal/data.

## Environment strategy

- **Local** membangun sibling repository dan mengekspos Web/Backend ke loopback host. GENESIS dan
  PostgreSQL tetap container-internal.
- **Staging** memakai image registry, Caddy ingress, named volume terpisah, dan placeholder
  hostname/secret operator.
- **Production** memakai immutable image reference, restart policy, read-only application
  filesystem, explicit resource guard, named volume, dan Caddy-managed TLS.

Tidak ada source bind mount atau development command pada staging/production.

## Database boundary

Image pgvector menyediakan PostgreSQL dan extension binary. Initialization hanya mengaktifkan
extension `vector`; tabel, role domain, dan application migration tetap berada di application
repository. Backup/restore script bekerja pada database yang dipilih operator dan tidak
menjadwalkan retention atau off-site storage.

## Observability

OpenTelemetry Collector menerima OTLP dari service internal dan menggunakan exporter `debug`
pada baseline. Exporter produksi merupakan deployment-specific configuration yang harus ditinjau
sebelum aktivasi. Repository tidak memasang Prometheus, Grafana, Loki, atau stack tambahan.

## Failure model

Kegagalan GENESIS tidak memberi browser jalur langsung ke AI; Backend harus menolak atau
mendegradasi fitur AI secara eksplisit. Kegagalan Backend menghentikan command authoritative.
Rollback image dan database recovery merupakan prosedur terpisah.
