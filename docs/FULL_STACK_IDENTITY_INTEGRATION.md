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

`scripts/integration-smoke.py` provisions canonical test identities through the explicitly gated
development bootstrap. It verifies login through the Web session boundary, whoami, workspace
listing, active-workspace selection, protected page loading, and denial of an unauthorized
workspace.

The same smoke also creates a multi-workspace actor and proves that login does not select a hidden
default, an explicit selection keeps the same actor and exposes the selected workspace's role,
revocation clears the active context, and the revoked workspace cannot be selected again. Negative
coverage rejects cross-organization account provisioning, client-supplied tenant authority, and a
cross-organization membership assignment.

After the identity boundary checks, the smoke executes the existing governed Backend-to-GENESIS
runtime, cancellation, Factory, research, review, and authority-expansion negative cases.

The integration compose enables test registration and deterministic runtime tools only in this
non-production environment. It uses generated run-specific CI secrets and never production secrets.
