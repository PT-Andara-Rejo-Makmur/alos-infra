# Production

Production Compose adalah configuration skeleton nyata, bukan deployment otomatis. Sebelum
aktivasi, operator wajib menetapkan:

- immutable image digest untuk Web, Backend, dan GENESIS;
- revision/tag `alos-contracts` yang sama untuk ketiga image, beserta verifikasi
  `/contracts/VERSION` pada image Backend dan GENESIS;
- trusted pgvector, Caddy, dan OpenTelemetry Collector image pin;
- public Web/API hostname dan DNS;
- secret melalui approved secret manager/deployment environment;
- persistent volume, capacity, encryption, backup, retention, dan recovery target;
- TLS policy, firewall, resource sizing, alerting destination, RPO/RTO, dan support ownership.

Jalankan preflight serta approved deployment runbook. Production Compose tidak melakukan build,
source mount, hot reload, atau development server. Bootstrap GitHub Actions tidak memegang secret
dan tidak mengeksekusi deployment.

Backend dan GENESIS production image wajib membundel canonical catalog di `/contracts` dan memakai
`ALOS_CONTRACTS_PATH=/contracts`. Web image wajib dibangun menggunakan generated TypeScript dari
revision contract yang sama. Jangan mengunduh contract yang mutable pada saat container start.
