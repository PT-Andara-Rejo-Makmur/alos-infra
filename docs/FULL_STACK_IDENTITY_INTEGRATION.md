# Full-stack Identity Integration

The integration environment contains Web, Backend, GENESIS, PostgreSQL, the mounted Contracts
checkout, and telemetry collector.

## Network boundary

- Web joins only `edge` and can reach Backend there.
- Backend joins `edge`, private `internal`, and private `data`.
- GENESIS joins only private `internal`; it has no published port and no data network.
- PostgreSQL joins only private `data` and has no published port.
- Web receives no GENESIS URL and therefore has no direct network path to GENESIS or PostgreSQL.

## Smoke proof

`scripts/integration-smoke.py` provisions a canonical IT test account through the explicitly gated
development bootstrap, then verifies login through the Web session boundary, whoami, workspace
listing, active-workspace selection, protected page loading, and denial of an unauthorized
workspace. It then executes the existing governed Backend-to-GENESIS runtime, cancellation,
Factory, research, review, and authority-expansion negative cases.

The integration compose enables test registration and deterministic runtime tools only in this
non-production environment. It uses generated run-specific CI secrets and never production secrets.
