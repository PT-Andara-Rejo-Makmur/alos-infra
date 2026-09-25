# Kebijakan Firewall Host & Provider (4 VPS)

Firewall host OS (UFW / iptables / nftables) dan cloud provider security group berada di luar Docker daemon, tetapi **wajib dikonfigurasi** untuk menegakkan batas otoritas multi-host ALOS.

---

## 1. Baseline Policy per Node

### Node 1: VPS 1 APP
- **Inbound Public**: Buka TCP `80` dan `443` (Caddy reverse proxy).
- **Inbound Management**: Buka TCP `SSH` (port default `22` atau custom) hanya dari IP bastion / developer VPN terdaftar.
- **Inbound Private**: Buka TCP `8000` **hanya dari IP Private VPS 2 (GENESIS)** untuk service-to-service callback (BackendToolClient & BackendCancellationProbe). DROP semua trafik internal lainnya yang tidak terdaftar.
- **Outbound**:
  - Buka TCP `8100` ke IP Private VPS 2 (GENESIS).
  - Buka TCP `5432` ke IP Private VPS 3 (PostgreSQL).
  - Buka TCP `80/443` ke Internet (ACME Let's Encrypt TLS renewal, DNS, NTP).

### Node 2: VPS 2 GENESIS
- **Inbound Public**: **DROP SEMUA PORT**.
- **Inbound Private**: Buka TCP `8100` **hanya dari IP Private VPS 1 (APP)**.
- **Inbound Management**: Buka TCP `SSH` hanya dari IP terdaftar.
- **Outbound**:
  - Buka TCP `443` ke Internet (akses API LLM Model Gateway eksternal jika aktif).
  - Buka TCP `8000` ke IP Private VPS 1 (APP) untuk private callback (tool execution & cancellation probe).
  - **STRICT DENY**: Dilarang memiliki koneksi ke VPS 3 (`5432`).

### Node 3: VPS 3 DATA
- **Inbound Public**: **DROP SEMUA PORT**.
- **Inbound Private**: Buka TCP `5432` **hanya dari IP Private VPS 1 (APP)**.
- **Inbound dari VPS 2**: **DROP/DENY**.
- **Inbound Management**: Buka TCP `SSH` hanya dari IP terdaftar.
- **Outbound**:
  - Buka TCP `443` ke object storage endpoint (hanya untuk pengiriman off-site backup).

### Node 4: VPS 4 STAGING
- **Inbound Public**: Buka TCP `80` dan `443` hanya untuk staging hostname.
- **Inbound Private/Management**: Buka TCP `SSH` hanya dari IP terdaftar.
- **Port Internal**: Port 3000, 8000, 8100, 5432, 4317 dilarang dipublikasikan ke host interface publik.

---

## 2. Pencegahan Docker iptables Bypass (UFW Integration)

Secara default di Linux, Docker memanipulasi iptables sehingga mapping port `ports: ["PORT:PORT"]` dapat mem-bypass rule UFW.
Untuk memastikan firewall tetap efektif:
1. Ikat port host ke private IP interface di `compose.yaml`:
   - App (Backend callback listener): `"${APP_PRIVATE_BIND_IP:?APP_PRIVATE_BIND_IP wajib diisi}:${ALOS_BACKEND_PORT:-8000}:8000"`
   - Genesis: `"${GENESIS_BIND_IP:?GENESIS_BIND_IP wajib diisi}:${GENESIS_PORT:-8100}:8100"`
   - Postgres: `"${POSTGRES_BIND_IP:?POSTGRES_BIND_IP wajib diisi}:${POSTGRES_PORT:-5432}:5432"`
2. Pastikan `scripts/preflight-check.py` telah memvalidasi bahwa seluruh bind IP bukan localhost, loopback, 0.0.0.0, atau kosong.
3. Tambahkan aturan eksplisit pada chain `DOCKER-USER` di iptables jika mempublikasikan port pada interface yang dapat diakses publik:
   ```bash
   # Contoh isolasi port 8000 di VPS 1 (hanya terima dari VPS 2 private IP)
   sudo iptables -I DOCKER-USER -i eth0 -p tcp --dport 8000 -s <VPS2_GENESIS_PRIVATE_IP> -j ACCEPT
   sudo iptables -A DOCKER-USER -i eth0 -p tcp --dport 8000 -j DROP

   # Contoh isolasi port 8100 di VPS 2 (hanya terima dari VPS 1 private IP)
   sudo iptables -I DOCKER-USER -i eth0 -p tcp --dport 8100 -s <VPS1_APP_PRIVATE_IP> -j ACCEPT
   sudo iptables -A DOCKER-USER -i eth0 -p tcp --dport 8100 -j DROP

   # Contoh isolasi port 5432 di VPS 3 (hanya terima dari VPS 1 private IP)
   sudo iptables -I DOCKER-USER -i eth0 -p tcp --dport 5432 -s <VPS1_APP_PRIVATE_IP> -j ACCEPT
   sudo iptables -A DOCKER-USER -i eth0 -p tcp --dport 5432 -j DROP
   ```

> [!NOTE]
> Spesifikasi firewall di atas merupakan acuan konfigurasi host sebelum provisioning VPS nyata. Enforcement aktual baru akan aktif ketika VPS fisik diprovisikan dan aturan firewall di atas diterapkan pada OS host.
