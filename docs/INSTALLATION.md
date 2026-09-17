# Instalasi Tooling

## Prasyarat

- Docker Engine yang aktif
- Docker Compose v2 (`docker compose version`)
- Git
- PowerShell 7 pada Windows atau Bash dan curl pada Linux/macOS

Clone seluruh repository sebagai sibling:

```text
alos-workspace/
├── alos-contracts/
├── alos-backend/
├── genesis-ai/
├── alos-web/
└── alos-infra/
```

## Windows PowerShell

```powershell
Set-Location alos-workspace\alos-infra\environments\local
Copy-Item .env.example .env
docker compose version
docker compose config
```

## Linux/macOS

```bash
cd alos-workspace/alos-infra/environments/local
cp .env.example .env
docker compose version
docker compose config
```

Isi secret development lokal sebelum `up`. Jangan mengisi contoh file atau melakukan commit
terhadap `.env`.
