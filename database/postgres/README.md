# PostgreSQL

Infra menyediakan container, volume, healthcheck, dan pgvector binary/extension. Initialization
hanya mengaktifkan extension `vector`; tidak ada tabel atau application schema pada folder ini.

Operator harus memilih image pin/digest, storage class/volume, capacity, maintenance window, dan
high-availability design yang sesuai environment sebelum production.
