# Local Development

## 1. Siapkan workspace

Pastikan `alos-backend`, `genesis-ai`, dan `alos-web` berada sejajar dengan `alos-infra` dan setiap
repository memiliki Dockerfile yang valid.

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

Build pertama dapat memerlukan waktu karena tiga sibling application image dibuat.

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

## Logs dan stop

```bash
docker compose logs -f --tail=200 web backend genesis postgres otel-collector
docker compose stop
docker compose down
```

Named volume PostgreSQL dipertahankan oleh `down`. Jangan tambahkan `--volumes` kecuali data
development memang boleh dihapus.
