# Preflight Deployment Multi-Host

Sebelum melakukan rilis atau perubahan konfigurasi pada lingkungan staging maupun production (VPS 1, VPS 2, VPS 3, VPS 4), jalankan checklist dan skrip validasi preflight otomatis.

## 1. Validasi Preflight Otomatis

Gunakan skrip `scripts/preflight-check.py` untuk memastikan seluruh invariant keamanan dan variabel wajib terpenuhi:

```bash
# Validasi menyeluruh (seluruh target node):
python scripts/preflight-check.py --target all

# Atau validasi node tertentu sebelum eksekusi pada host terkait:
python scripts/preflight-check.py --target app
python scripts/preflight-check.py --target genesis
python scripts/preflight-check.py --target data
python scripts/preflight-check.py --target staging

# Validasi dengan penegasan referensi rollback dan isolasi path staging:
python scripts/preflight-check.py --target all --require-rollback-ref --staging-env-file /etc/alos/staging/staging.env
```

## 2. Invariant yang Diuji Preflight

### Node APP (VPS 1):
- Referensi image `ALOS_WEB_IMAGE` dan `ALOS_BACKEND_IMAGE` tersedia dan menggunakan immutable digest (`@sha256:...`). Dilarang keras menggunakan `:latest`.
- Interface listener callback private Backend `APP_PRIVATE_BIND_IP` wajib diisi dan bukan loopback (`127.0.0.1`/`localhost`/`0.0.0.0`).
- Endpoint private GENESIS (`GENESIS_PRIVATE_HOST` atau `GENESIS_BASE_URL`) telah diset.
- Endpoint private database (`DATABASE_PRIVATE_HOST` atau `DATABASE_URL`) telah diset beserta kredensial DB.
- Token otentikasi internal `GENESIS_INTERNAL_TOKEN` tersedia.
- Hostname publik `WEB_HOSTNAME` dan `API_HOSTNAME` tersedia.

### Node GENESIS (VPS 2):
- Referensi image `GENESIS_IMAGE` tersedia dan immutable (bukan `:latest`).
- Interface binding private `GENESIS_BIND_IP` wajib diisi dan bukan loopback (`127.0.0.1`/`localhost`/`0.0.0.0`).
- URL private backend `ALOS_BACKEND_BASE_URL` telah diset (menunjuk ke IP private VPS 1).
- Token `ALOS_INTERNAL_TOKEN` tersedia.
- **Invariant Keamanan**: Dilarang memiliki variabel `DATABASE_URL` atau `POSTGRES_*`.

### Node DATA (VPS 3):
- Kredensial database `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` tersedia.
- Interface binding private `POSTGRES_BIND_IP` wajib diisi dan bukan loopback (`127.0.0.1`/`localhost`/`0.0.0.0`).
- Persistensi volume `postgres-data` terkonfigurasi.
- **Invariant Keamanan**: Dilarang memiliki token internal AI `GENESIS_INTERNAL_TOKEN` / `ALOS_INTERNAL_TOKEN`.

### Node STAGING (VPS 4):
- Kredensial staging terpisah dari production secrets.
- Hostname tidak tertukar dengan production domain.

### Pemeriksaan Lintas Lingkungan (Cross-Environment Isolation):
- Path file rahasia Production (`/etc/alos/production/*.env`) dilarang identik dengan Staging (`/etc/alos/staging/staging.env`).
- Seluruh pesan kegagalan preflight menerapkan sanitasi ketat (tidak pernah mencetak nilai rahasia/password/token ke output).

## 3. Checklist Manual Operator

1. Pastikan port host firewall (UFW / iptables) diatur sesuai matrix jaringan [docs/NETWORKING.md](../../docs/NETWORKING.md).
2. Jalankan `docker compose config --quiet` pada direktori node target.
3. Ambil safety backup sebelum rilis skema database (`bash database/backup/backup.sh`).
4. Simpan tag/digest image saat ini untuk keperluan rollback cepat jika terjadi kegagalan (`runbooks/rollback.md`).
