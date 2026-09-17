# Production

Production Compose adalah configuration skeleton nyata, bukan deployment otomatis. Sebelum
aktivasi, operator wajib menetapkan:

- immutable image digest untuk Web, Backend, dan GENESIS;
- trusted pgvector, Caddy, dan OpenTelemetry Collector image pin;
- public Web/API hostname dan DNS;
- secret melalui approved secret manager/deployment environment;
- persistent volume, capacity, encryption, backup, retention, dan recovery target;
- TLS policy, firewall, resource sizing, alerting destination, RPO/RTO, dan support ownership.

Jalankan preflight serta approved deployment runbook. Production Compose tidak melakukan build,
source mount, hot reload, atau development server. Bootstrap GitHub Actions tidak memegang secret
dan tidak mengeksekusi deployment.
