# Deployment Staging

Staging menggunakan `environments/staging/compose.yaml` dan image registry, bukan local build.
Isi environment operator, validasi config, pull image, jalankan migration aplikasi sesuai runbook,
kemudian `docker compose up -d`. Staging harus menguji health, network isolation, backup/restore,
rollback, serta user journey sebelum production.
