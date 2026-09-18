# Local Development

## 1. Siapkan workspace

Pastikan `alos-contracts`, `alos-backend`, `genesis-ai`, dan `alos-web` berada sejajar dengan
`alos-infra` dan setiap repository aplikasi memiliki Dockerfile yang valid. Docker harus
mendukung BuildKit named build context.

## 2. Siapkan environment

Masuk ke `alos-infra/environments/local`, salin `.env.example` menjadi `.env`, lalu isi minimal:

```dotenv
POSTGRES_DB=alos
POSTGRES_USER=alos
POSTGRES_PASSWORD=<development-only-value>
GENESIS_INTERNAL_TOKEN=<development-only-value>
```

Jangan menggunakan production credential.

## 3. Validasi dan start

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Build pertama dapat memerlukan waktu karena tiga sibling application image dibuat. Compose
memberikan `alos-contracts` sebagai named build context kepada ketiganya. Backend dan GENESIS
membundel schema/events canonical ke `/contracts`, sedangkan Web memakai generated TypeScript
hanya pada build stage.

## 4. Periksa health

Linux/macOS:

```bash
bash ../../scripts/health-check.sh
```

Windows PowerShell:

```powershell
..\..\scripts\health-check.ps1
```

Script memeriksa Web/Backend melalui loopback host dan GENESIS/PostgreSQL melalui internal
container exec. Tidak perlu menerbitkan port GENESIS atau database.

## 5. Buka aplikasi

Buka `http://127.0.0.1:3000`. Backend tersedia di `http://127.0.0.1:8000`. Port dapat diubah pada
`.env`. Karena `NEXT_PUBLIC_*` biasanya dibundel ketika image Web dibangun, lakukan rebuild Web
setelah mengganti Backend public URL.

UI memanggil Backend, lalu Backend memanggil GENESIS melalui network `internal`. Selain contract
yang sudah dibundel ke image, local Compose me-mount sibling `alos-contracts` secara read-only ke
`/contracts` agar perubahan contract lokal dapat diuji tanpa membuat state contract lain. Uji
jalur lengkap tanpa membuka port GENESIS:

```bash
curl -i -H "X-Correlation-ID: corr_local_001" \
  http://127.0.0.1:8000/api/v1/system/integration
```

Header respons, `correlation_id` top-level, dan `genesis.correlation_id` harus bernilai
`corr_local_001`. GENESIS dan PostgreSQL tetap tidak dipublikasikan ke host.

`NEXT_PUBLIC_ALOS_API_BASE_URL` dipasang sebagai Docker build argument agar browser bundle hanya
mengenal URL Backend publik. Backend mengizinkan origin Web lokal melalui `CORS_ALLOWED_ORIGINS`;
operator harus mengganti keduanya bersama-sama untuk host staging/production, lalu menjalankan
`docker compose up --build -d web`. Tidak ada URL GENESIS yang boleh masuk ke environment Web.

## Logs dan stop

```bash
docker compose logs -f --tail=200 web backend genesis postgres otel-collector
docker compose stop
docker compose down
```

Named volume PostgreSQL dipertahankan oleh `down`. Jangan tambahkan `--volumes` kecuali data
development memang boleh dihapus.
