# Runtime container security — 4 October 2026

The local audit scans Backend, GENESIS, Web, PostgreSQL/pgvector, Caddy and the collector with
[Trivy image scanning](https://trivy.dev/docs/latest/references/configuration/cli/trivy_image/),
version 0.75.0 pinned to image digest
`sha256:af6acf9a6b85dfe389a1941505c0ce9efef52a4719635e1a962f022a3d855daa`.
The vulnerability database was fetched on 4 October 2026. Reports retain all severities,
including findings without a fixed version. The scanner runs locally against Docker;
telemetry is disabled and application images are not uploaded.

## Fixed findings

- Python runtime images update Debian packages during the build, installing the available
  PCRE security update from `10.46-1~deb13u2` to `10.46-1~deb13u3`.
- pip/setuptools/wheel are removed after the application is installed. pip's embedded SBOM
  had exposed vendored msgpack, setuptools and urllib3 findings that a standalone pip-audit
  inventory did not cover. The latest pip release still contained the affected urllib3.
  Removing installed build tooling removes that runtime dependency surface.
- The Web runtime removes npm/corepack/yarn and already prunes application development
  dependencies. The npm bundled dependency findings no longer appear in the final image.
- Staging now matches production capability restrictions: application services drop ALL
  capabilities, use a read-only root filesystem and prohibit new privileges. Caddy retains
  only NET_BIND_SERVICE. These are validated configuration properties, not a claim of a
  completed staging deployment.
- Caddy's old 2.10 image had 83 fixable HIGH findings. The available audited 2.11 image
  runs Caddy 2.11.6, passes the real Caddyfile validation and is pinned by digest.
- The old contrib collector had 69 fixable HIGH findings. The configured OTLP receivers,
  memory limiter, batch and debug exporter are all provided by the core collector
  0.162.0. Configuration validation and actual synthetic traces, metrics and logs
  transport passed; this does not prove application instrumentation or live alerts.
- Stock database images contained gosu compiled with Go 1.24.7, carrying fixable HIGH
  Go runtime findings. `database/Dockerfile` rebuilds gosu 1.19 with pinned Go 1.27.1.
  PostgreSQL 16 Alpine has fewer distro findings than the Debian pgvector image.
  [pgvector 0.8.7](https://github.com/pgvector/pgvector/releases/tag/v0.8.7) is built
  from its pinned commit and source archive checksum, using portable compilation
  as supported by its [Makefile](https://raw.githubusercontent.com/pgvector/pgvector/f37c13f68b57d2c3472b2214fbcff699d6d34876/Makefile).
  No compiler is copied to runtime. Actual backup/restore scripts, vector values,
  HNSW/IVFFlat indexes and nearest-vector queries passed on disposable databases.
  Existing Debian database volumes require staging logical migration, collation/index
  checks and rollback proof before switching distributions; no operational volume
  was switched during this audit.

## Final scan and remaining risk

| Image | All findings | HIGH/CRITICAL findings | Fixable HIGH/CRITICAL |
| --- | ---: | ---: | ---: |
| Backend | 166 | 44 | 0 |
| GENESIS | 166 | 44 | 0 |
| Web | 0 | 0 | 0 |
| PostgreSQL 16 Alpine + pgvector 0.8.7 | 1 | 0 | 0 |
| Caddy 2.11.6 | 1 | 0 | 0 |
| Core OpenTelemetry 0.162.0 | 1 | 0 | 0 |

Backend and GENESIS share the Debian base. The 44 HIGH findings are package/CVE pairs
for eight distinct CVEs: `CVE-2025-69720`, `CVE-2026-16742`, `CVE-2026-54369`,
`CVE-2026-76642`, `CVE-2026-78408`, `CVE-2026-78409`, `CVE-2026-78410` and
`CVE-2026-9538`. They are not 44 independent vulnerabilities in application code.
The stable distro had no fixed version available in the scan. Updating packages did
not remove them. No blanket ignore file or accepted-risk decision has been added.

Debian classifies the reported
[nsenter/cgroup issue](https://security-tracker.debian.org/tracker/CVE-2026-78408) and
[ncurses CLI issue](https://security-tracker.debian.org/tracker/CVE-2025-69720) as minor
issues without a stable DSA. This helps triage; it does not override the scanner or
approve the deployment. Assess actual reachable binaries, privileges, mounted host
resources and application execution paths for every finding before production.

CI builds the database candidate and scans all six runtime images, blocks fixable
HIGH/CRITICAL findings and uploads the full reports. The scratch collector has no OS
package result; the report gate accepts only its exact reviewed digest with a completed
Go binary scan and matching entrypoint. An arbitrary missing OS result is rejected.
Staging/production now require an explicit database image digest; mutable auxiliary
image overrides are also rejected by preflight. CI changes remain locally verified
and unpushed. This is a
remediation gate, not a production approval. The production gate is stricter:

```sh
python3 scripts/verify-image-security.py --strict \
  .audit/trivy/backend-final.json .audit/trivy/genesis-final.json .audit/trivy/web-final.json \
  .audit/trivy/postgres-alpine-final.json .audit/trivy/caddy-final.json .audit/trivy/otel-final.json
```

That strict command currently exits **1**, correctly rejecting the unresolved HIGH
findings. A patched base image or explicit, evidence-backed security risk decision is
required to close this gate. Final dependency audits and functional tests are recorded
separately in the readiness report; neither replaces container security assessment.

## Business UAT image checkpoint

After the corrective-task fix, Trivy 0.75.0 scanned the newly built Backend and Web
images using a refreshed vulnerability database. Web has 0 findings; Backend retains
166 findings, including 44 HIGH package/CVE pairs with 0 fixable HIGH/CRITICAL.
The strict report gate again exits 1 and remains BLOCKED. Reports are
`.audit/trivy/backend-business-uat.json`, `.audit/trivy/web-business-uat.json` and
`.audit/image-security-business-uat-strict.log`. GENESIS and infrastructure images
were not changed in this UAT batch; their earlier complete scans remain the checkpoint.
