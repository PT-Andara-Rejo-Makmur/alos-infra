# Tenant Database Boundary

Infrastructure tidak menentukan table-level tenant model. Backend dan contract menentukan
`tenant_id`, scope, serta enforcement. Infrastruktur hanya memastikan database tidak public dan
credential production memiliki least privilege sesuai role aplikasi.

Jika Backend dan GENESIS berbagi PostgreSQL server, gunakan database/role terpisah dan jangan
memberi GENESIS akses ke authoritative business schema.
