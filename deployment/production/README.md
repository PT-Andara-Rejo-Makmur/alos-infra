# Deployment Production Multi-Host (3 VPS)

Production ALOS MVP-2 dideploy melintasi 3 node VPS independen:
1. **VPS 1 (APP)**: `environments/production/app/` (Caddy, alos-web, alos-backend).
2. **VPS 2 (GENESIS)**: `environments/production/genesis/` (genesis-ai).
3. **VPS 3 (DATA)**: `environments/production/data/` (PostgreSQL + pgvector).

## Prinsip Operasional

1. **Jalankan Sesuai Urutan Aman**:
   - Node DATA (VPS 3) terlebih dahulu.
   - Migrasi Alembic dijalankan sebelum aplikasi Backend start.
   - Node GENESIS (VPS 2) distart dan diverifikasi healthcheck-nya.
   - Node APP (VPS 1) distart; Caddy hanya akan menerima traffic setelah Web & Backend sehat.
2. **Preflight Wajib**: Jalankan `python scripts/preflight-check.py --target <app|genesis|data>` sebelum `docker compose up -d`.
3. **Immutability**: Wajib menggunakan cryptographic digest (`@sha256:...`) untuk seluruh image aplikasi.
4. **Isolasi Network**: Pastikan firewall host (UFW/iptables) membatasi akses antar-node hanya melalui private network.

Untuk panduan lengkap, lihat [docs/PRODUCTION.md](../../docs/PRODUCTION.md) dan [docs/NETWORKING.md](../../docs/NETWORKING.md).
