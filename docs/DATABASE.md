# Database

## Ownership Infra

- PostgreSQL/pgvector image dan container;
- private data network;
- named persistent volume;
- availability healthcheck;
- extension binary dan bootstrap `vector` extension;
- backup/restore mechanism serta operational documentation.

## Ownership aplikasi

Backend memiliki schema, migration, data lifecycle, compatibility, dan validation untuk
authoritative business domain. GENESIS tidak memiliki jalur network maupun credential ke database
bisnis pada bootstrap ini. Infra tidak menyimpan Alembic migration atau application DDL/table
definition.

Jika GENESIS kelak memerlukan persistence runtime/reference, gunakan role/database dan network
terpisah melalui perubahan arsitektur eksplisit; jangan sambungkan ke database bisnis. Production
operator perlu menetapkan sizing, connection limits, HA, patching, encryption, maintenance,
retention, dan RPO/RTO.

Compose membentuk `DATABASE_URL` dari variable PostgreSQL. Gunakan password yang telah di-URL
encode bila mengandung karakter khusus, atau migrasikan aplikasi ke secret-file/component
configuration sebelum production agar credential tidak rusak oleh URI interpolation.
