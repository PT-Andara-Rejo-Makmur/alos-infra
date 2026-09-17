# Staging

Staging menggunakan prebuilt application image. Operator harus mengisi `.env` dari secret/config
system, hostname DNS, dan immutable image reference.

```bash
cd environments/staging
docker compose --env-file .env config --quiet
docker compose --env-file .env pull
docker compose --env-file .env up -d
```

Verifikasi TLS, Web, Backend, internal GENESIS, PostgreSQL, correlation flow, migration, backup,
restore test, dan rollback. Staging harus menyerupai production boundary tetapi memakai resource,
credential, hostname, volume, dan tenant test yang terpisah.
