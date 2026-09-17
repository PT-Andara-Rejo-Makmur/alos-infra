# Database

## Ownership Infra

- PostgreSQL/pgvector image dan container;
- private data network;
- named persistent volume;
- availability healthcheck;
- extension binary dan bootstrap `vector` extension;
- backup/restore mechanism serta operational documentation.

## Ownership aplikasi

Backend dan GENESIS memiliki schema, migration, data lifecycle, compatibility, dan validation
sesuai domain. Infra tidak menyimpan Alembic migration atau application DDL/table definition.

Untuk shared server, buat role/database terpisah. GENESIS tidak boleh memperoleh credential ke
authoritative business schema. Production operator perlu menetapkan sizing, connection limits,
HA, patching, encryption, maintenance, retention, dan RPO/RTO.

Compose membentuk `DATABASE_URL` dari variable PostgreSQL. Gunakan password yang telah di-URL
encode bila mengandung karakter khusus, atau migrasikan aplikasi ke secret-file/component
configuration sebelum production agar credential tidak rusak oleh URI interpolation.
