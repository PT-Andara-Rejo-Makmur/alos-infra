# Staging

Staging menggunakan prebuilt application image. Operator harus mengisi `.env` dari secret/config
system, hostname DNS, dan immutable image reference.

Application image harus berasal dari Dockerfile repository masing-masing dengan named build
context `contracts` yang menunjuk ke revision/tag `alos-contracts` yang sama. Backend dan GENESIS
harus memiliki canonical catalog pada `/contracts` dan `ALOS_CONTRACTS_PATH=/contracts`; Web harus
dibangun dengan generated TypeScript dari revision tersebut. Catat revision contract bersama
image digest sebagai release evidence.

```bash
cd environments/staging
docker compose --env-file .env config --quiet
docker compose --env-file .env pull
docker compose --env-file .env up -d
```

Verifikasi TLS, Web, Backend, internal GENESIS, PostgreSQL, correlation flow, migration, backup,
restore test, rollback, serta kecocokan `/contracts/VERSION`. Staging harus menyerupai production
boundary tetapi memakai resource, credential, hostname, volume, dan tenant test yang terpisah.
