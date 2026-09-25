# Networking ALOS MVP-2 (Multi-Host 4 VPS)

Arsitektur jaringan ALOS MVP-2 dirancang untuk memisahkan domain otoritas bisnis, antarmuka pengguna, pemrosesan kecerdasan buatan, dan persistensi data ke dalam node VPS terpisah pada environment Production, serta 1 VPS terisolasi pada environment Staging.

## 1. Topologi Jaringan Production (3 VPS)

```text
[ INTERNET ]
     |
     | (Port 80/443 Public)
     v
========================================================================
[ PRODUCTION - VPS 1: APP ]
  - Ingress: Caddy (Reverse Proxy, TLS Management)
  - Web: alos-web (Next.js SSR/BFF, port container 3000)
  - Backend: alos-backend (FastAPI Otoritas Utama, port container 8000)
    * Public via Caddy: https://api.<domain>
    * Private listener: APP_PRIVATE_BIND_IP:8000 (GENESIS callback)
========================================================================
        |   ^                                   |
        |   | Private Net                       | Private Net
        |   | (Outbound 8100 / Callback 8000)   | (TCP 5432)
        v   |                                   v
====================================   =================================
[ PRODUCTION - VPS 2: GENESIS ]        [ PRODUCTION - VPS 3: DATA ]
  - Service: genesis-ai (Port 8100)      - Database: PostgreSQL + pgvector
  - Intelligence / ModelGateway          - Storage: Named Volume Persistence
  - BackendToolClient -> VPS 1 :8000     - Backup: pg_dump Custom + Checksum
  - ISOLATED: No Public Ports,           - ISOLATED: No Public Ports,
              No DB Network / Route                  No Internet Inbound
====================================   =================================
```

---

## 2. Network Authority Matrix

| SOURCE | DESTINATION | PORT / PROTOCOL | ALLOW / DENY | REASON |
|---|---|---|---|---|
| **Internet** | **VPS 1 (App)** | 80, 443 / TCP | **ALLOW** | Public HTTP/HTTPS ingress via Caddy reverse proxy. |
| **Internet** | **Backend private (VPS 1)** | 8000 / Any | **DENY** | Port 8000 Backend hanya diikat ke IP private host untuk callback GENESIS; dilarang terekspos ke internet publik. |
| **Internet** | **VPS 2 (GENESIS)** | 8100 / Any | **DENY** | GENESIS adalah internal intelligence plane; tidak boleh memiliki public attack surface. |
| **Internet** | **VPS 3 (Data)** | 5432 / Any | **DENY** | Database bisnis tidak boleh terekspos ke internet publik dalam kondisi apapun. |
| **Internet** | **VPS 4 (Staging)** | 80, 443 / TCP | **ALLOW** | Ingress publik terbatas untuk verifikasi fungsional staging. |
| **Web** | **Backend** | 8000 / TCP | **ALLOW** | Web BFF meneruskan authenticated browser requests ke authoritative backend API. |
| **Web** | **GENESIS** | 8100 / TCP | **DENY** | Browser / Web dilarang mengakses AI secara langsung tanpa validasi otoritas Backend. |
| **Web** | **PostgreSQL** | 5432 / TCP | **DENY** | Web frontend tidak memiliki otoritas schema atau direct SQL access. |
| **Backend (VPS 1)** | **GENESIS (VPS 2)** | 8100 / TCP | **ALLOW** | Backend mengeksekusi governed AI requests melalui jaringan private. |
| **GENESIS (VPS 2)** | **Backend (VPS 1)** | 8000 / TCP | **ALLOW** | Private network callback only: eksekusi tool (`BackendToolClient`) & cancellation probe (`BackendCancellationProbe`). |
| **Backend (VPS 1)** | **PostgreSQL (VPS 3)** | 5432 / TCP | **ALLOW** | Backend adalah satu-satunya entitas yang memiliki authority atas schema dan data bisnis. |
| **GENESIS (VPS 2)** | **PostgreSQL (VPS 3)** | 5432 / TCP | **DENY** | AI dilarang mengakses database bisnis secara langsung (mencegah bypass otoritas & data poisoning). |
| **GENESIS (VPS 2)** | **Internet** | 443 / TCP | **ALLOW** | Outbound akses ke model provider eksternal (OpenAI/Anthropic/Gemini) sesuai kebutuhan. |
| **PostgreSQL (VPS 3)** | **Internet Inbound** | Any | **DENY** | PostgreSQL hanya mendengarkan request pada interface private. |

---

## 3. Tanggung Jawab Firewall Host & Provider

> [!CRITICAL]
> **Docker Compose Sendirian Tidak Menjamin Isolasi Multi-Host!**
> Docker Compose mengelola container network pada host lokal saja. Komunikasi antar-VPS fisik wajib diamankan pada level host OS (firewall UFW/iptables) dan/atau cloud provider (VPC Security Groups / WireGuard mesh).

### Aturan Firewall Wajib per Node:

1. **VPS 1 (APP):**
   - Inbound Public: ALLOW `80/tcp`, `443/tcp`.
   - Inbound Private: ALLOW `8000/tcp` **hanya dari IP Private VPS 2 (GENESIS)** untuk service-to-service callback.
   - Inbound Management: ALLOW `SSH` (hanya dari IP administrator terdaftar).
   - Outbound: ALLOW ke VPS 2 (`8100/tcp`), VPS 3 (`5432/tcp`), dan Internet (`80/tcp`, `443/tcp`).

2. **VPS 2 (GENESIS):**
   - Inbound: ALLOW `8100/tcp` **hanya dari IP Private VPS 1**.
   - Inbound Public: **DROP/DENY SEMUA**.
   - Inbound Management: ALLOW `SSH` (hanya dari IP administrator terdaftar).
   - Outbound: ALLOW ke Internet `443/tcp` (provider model API) dan ke IP Private VPS 1 `8000/tcp` (tool callback & cancellation probe). Dilarang keras menghubungkan ke VPS 3 (`5432`).

3. **VPS 3 (DATA):**
   - Inbound: ALLOW `5432/tcp` **hanya dari IP Private VPS 1**.
   - Inbound Public: **DROP/DENY SEMUA**.
   - Inbound dari VPS 2: **DROP/DENY**.
   - Inbound Management: ALLOW `SSH` (hanya dari IP administrator terdaftar).
   - Outbound: Terbatas hanya untuk sinkronisasi off-site backup.

4. **VPS 4 (STAGING):**
   - Menggunakan 1 host fisik mandiri dengan Docker internal bridge network (`edge`, `internal`, `data`).
   - Inbound Public: ALLOW `80/tcp`, `443/tcp` untuk staging hostname.
   - Database dan GENESIS port tidak dipublikasikan ke host interface publik.

---

## 4. Mitigasi Docker iptables Bypass

Pada Linux, Docker secara default memodifikasi iptables dan dapat mem-bypass rule UFW jika port dipetakan ke `0.0.0.0`.
Untuk mencegah kecelakaan keamanan ini:
1. Compose file pada VPS 1, VPS 2, dan VPS 3 mengikat port secara eksplisit ke private IP interface:
   - VPS 1 APP (Backend callback listener): `"${APP_PRIVATE_BIND_IP:?APP_PRIVATE_BIND_IP wajib diisi}:${ALOS_BACKEND_PORT:-8000}:8000"`
   - VPS 2 GENESIS: `"${GENESIS_BIND_IP:?GENESIS_BIND_IP wajib diisi}:${GENESIS_PORT:-8100}:8100"`
   - VPS 3 DATA: `"${POSTGRES_BIND_IP:?POSTGRES_BIND_IP wajib diisi}:${POSTGRES_PORT:-5432}:5432"`
2. Preflight check (`scripts/preflight-check.py`) secara ketat menolak nilai kosong, `localhost`, `127.0.0.1`, `0.0.0.0`, dan `::1` untuk seluruh private bind IP.
3. Operator wajib memastikan rule iptables chain `DOCKER-USER` diatur dengan benar saat provisioning VPS.
