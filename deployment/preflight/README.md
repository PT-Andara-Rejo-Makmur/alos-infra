# Preflight Deployment

Sebelum staging/production:

1. pastikan image menggunakan immutable digest/tag dan berasal dari trusted registry;
2. jalankan `docker compose config --quiet` dengan environment nyata;
3. verifikasi Caddy hostname, DNS, TLS, firewall, disk, memory, dan backup target;
4. konfirmasi migration compatibility serta urutan aplikasi;
5. ambil backup dan catat checksum/restore-test evidence;
6. rekam current image reference untuk rollback;
7. siapkan health, log, correlation ID, dan escalation contact;
8. dapatkan approval sesuai change-management policy.
