# Indeks Dokumentasi alos-infra

Mulai dari [README repository](../README.md). Panduan runtime mengikuti source
dan contracts terkini; requirements/compatibility bukan klaim seluruh fitur siap.
Bukti tes bertanggal hanya berlaku untuk source dan environment yang dicatat.
Status lintas repository dipusatkan pada [readiness produksi](https://github.com/PT-Andara-Rejo-Makmur/alos-infra/blob/development/docs/PRODUCTION_READINESS_2026-10-04.md).

Authority tetap Web → Backend → GENESIS, dengan Backend sebagai pemilik data,
akses dan keputusan. Secret, dump, log privat dan artifacts lokal tidak masuk Git.

## Operasi dan integrasi

- [Governed ARA acceptance](ara-acceptance.md)
- [Backup dan Restore](BACKUP_RESTORE.md)
- [Operasi worker bisnis dan object dokumen](business-worker-operations.md)
- [Canonical Identity Security Closure Baseline](CANONICAL_IDENTITY_SECURITY_CLOSURE_BASELINE.md)
- [Database](DATABASE.md)
- [Struktur Folder](FOLDER_STRUCTURE.md)
- [Full-stack Identity Integration](FULL_STACK_IDENTITY_INTEGRATION.md)
- [Instalasi Tooling](INSTALLATION.md)
- [Integrasi Development dan Pengujian Disposable](INTEGRATION.md)
- [Local Development](LOCAL_DEVELOPMENT.md)
- [External production model gateway operations](model-gateway-operations.md)
- [Networking ALOS MVP-2 (Multi-Host 4 VPS)](NETWORKING.md)
- [Observability](OBSERVABILITY.md)
- [Panduan Deployment Production (APP, GENESIS, DATA dan Model Gateway)](PRODUCTION.md)
- [Shared Gate Validation](SHARED_GATE_VALIDATION.md)
- [Panduan Deployment Staging (VPS 4 Full-Stack)](STAGING.md)

## Bukti pengujian dan gate 4 Oktober 2026

- [Pengujian bisnis development — 4 Oktober 2026](BUSINESS_UAT_2026-10-04.md)
- [Runtime container security — 4 October 2026](CONTAINER_SECURITY_2026-10-04.md)
- [Audit dan implementasi ALOS — 4 Oktober 2026](PRODUCTION_READINESS_2026-10-04.md)

## Runbook dan deployment

- [Runbook Backend Down](../runbooks/backend-down.md)
- [Runbook Deploy Production ALOS (Multi-Host 4 VPS)](../runbooks/deploy.md)
- [Runbook GENESIS Down](../runbooks/genesis-down.md)
- [Runbook Incident Response & Disaster Recovery (DR) ALOS](../runbooks/incident-response.md)
- [Runbook Restore Database ALOS](../runbooks/restore.md)
- [Runbook Rollback Rilis Production ALOS](../runbooks/rollback.md)
- [Preflight checklist](../deployment/preflight/README.md)
- [Secrets operating model](../security/secrets/README.md)
- [Firewall](../networking/firewall/README.md)

## Pemeriksaan sebelum commit

Dari sibling checkout Infra, jalankan `python scripts/verify-documentation.py`.
Pemeriksaan memvalidasi link file kelima repository serta casing Linux tanpa jaringan.
