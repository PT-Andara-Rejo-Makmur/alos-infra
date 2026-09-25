# Secrets Management & Operating Model ALOS

Dokumen ini mendefinisikan arsitektur pengelolaan rahasia (*secrets management*), model operasi penyimpanan rahasia pada host, serta prosedur rotasi kredensial untuk lingkungan Production dan Staging ALOS MVP-2.

---

## 1. Prinsip & Batas Keamanan Rahasia

1. **Pemisahan Total Staging & Production**:
   - Seluruh password, token, dan kredensial Staging wajib berbeda 100% dari Production.
   - Dilarang keras meminjam atau mendaur ulang nilai kredensial antar-lingkungan.
2. **Kredensial Produksi Minimal**:
   - `POSTGRES_PASSWORD`: Password otentikasi database PostgreSQL (disimpan di VPS 1 APP dan VPS 3 DATA).
   - `GENESIS_INTERNAL_TOKEN`: Shared secret otentikasi internal service-to-service antara Backend dan GENESIS (disimpan di VPS 1 APP dan VPS 2 GENESIS).
3. **Placeholder Eksternal (Masa Depan)**:
   - `OPENAI_API_KEY`: Placeholder provider model masa depan. **Dilarang diaktifkan atau diwajibkan saat ini**. Default sistem tetap `DEFAULT_MODEL_ROUTE=disabled`.
4. **Larangan Kebocoran Kredensial**:
   - Rahasia dilarang dimasukkan ke dalam Docker build arguments (`ARG`).
   - Rahasia dilarang dimasukkan ke variabel publik Next.js (`NEXT_PUBLIC_*`).
   - Rahasia dilarang dicetak ke dalam log aplikasi, stdout/stderr container, maupun skrip CLI.
   - Rahasia dilarang di-commit ke dalam repositori Git.
   - File `.env` lokal diabaikan oleh `.gitignore`.
   - File `.env.example` hanya berisi placeholder kosong atau default non-sensitif.

---

## 2. Secret File Operating Model (/etc/alos/)

Untuk lingkungan multi-host VPS saat ini (sebelum migrasi ke centralized secret manager seperti Vault), rahasia disimpan di filesystem host di luar repositori Git menggunakan direktori standar `/etc/alos/`:

```text
/etc/alos/
├── production/
│   ├── app.env       # Untuk VPS 1 APP (dimiliki user deployer, mode 0600)
│   ├── genesis.env   # Untuk VPS 2 GENESIS (dimiliki user deployer, mode 0600)
│   └── data.env      # Untuk VPS 3 DATA (dimiliki user deployer, mode 0600)
└── staging/
    └── staging.env   # Untuk VPS 4 STAGING (dimiliki user deployer, mode 0600)
```

### Prosedur Setup Direktori & Hak Akses di Host Linux:

```bash
# Buat direktori rahasia terisolasi
sudo mkdir -p /etc/alos/production /etc/alos/staging
sudo chown -R root:deployer /etc/alos
sudo chmod 750 /etc/alos /etc/alos/production /etc/alos/staging

# Inisialisasi file rahasia kosong dengan hak akses ketat (hanya owner/deployer yang dapat membaca)
sudo touch /etc/alos/production/app.env \
           /etc/alos/production/genesis.env \
           /etc/alos/production/data.env \
           /etc/alos/staging/staging.env

sudo chown deployer:deployer /etc/alos/production/*.env /etc/alos/staging/*.env
sudo chmod 600 /etc/alos/production/*.env /etc/alos/staging/*.env
```

### Pemanggilan File Rahasia pada Docker Compose:

Saat menjalankan operasi deployment di masing-masing node VPS:
```bash
# Contoh di VPS 1 APP:
docker compose --env-file /etc/alos/production/app.env -f compose.yaml up -d

# Contoh di VPS 2 GENESIS:
docker compose --env-file /etc/alos/production/genesis.env -f compose.yaml up -d

# Contoh di VPS 3 DATA:
docker compose --env-file /etc/alos/production/data.env -f compose.yaml up -d
```

---

## 3. Prosedur Rotasi Rahasia (Secret Rotation)

### A. Rotasi `GENESIS_INTERNAL_TOKEN`

Prosedur ini dilakukan secara terkoordinasi untuk menghindari kegagalan panggilan service-to-service antara Backend dan GENESIS:

1. **Generate Token Baru**:
   ```bash
   NEW_TOKEN=$(openssl rand -hex 32)
   ```
2. **Update Konfigurasi Host**:
   - Di VPS 2 (GENESIS): perbarui `ALOS_INTERNAL_TOKEN=${NEW_TOKEN}` di `/etc/alos/production/genesis.env`.
   - Di VPS 1 (APP): perbarui `GENESIS_INTERNAL_TOKEN=${NEW_TOKEN}` di `/etc/alos/production/app.env`.
3. **Restart Service Terkendali**:
   - Restart node GENESIS terlebih dahulu:
     ```bash
     # Di VPS 2 GENESIS:
     docker compose --env-file /etc/alos/production/genesis.env up -d --force-recreate genesis
     ```
   - Restart service Backend pada node APP:
     ```bash
     # Di VPS 1 APP:
     docker compose --env-file /etc/alos/production/app.env up -d --force-recreate backend
     ```
4. **Verifikasi Kesehatan**:
   - Jalankan `health-check.sh` pada APP dan GENESIS.
   - Jalankan smoke test panggilan terotorisasi Backend → GENESIS dan GENESIS → Backend callback.
5. **Pencatatan**:
   - Simpan audit log rotasi (waktu, operator penanggung jawab, ticket approval).

### B. Rotasi `POSTGRES_PASSWORD`

Prosedur ini melibatkan pembaruan kredensial di PostgreSQL server dan client Backend:

1. **Pre-rotation Safety Backup**:
   - Ambil backup snapshot database sebelum melakukan perubahan apapun:
     ```bash
     # Di VPS 3 DATA:
     bash database/backup/backup.sh
     ```
2. **Generate Password Baru**:
   ```bash
   NEW_PASSWORD=$(openssl rand -base64 32 | tr -d '=/+')
   ```
3. **Update Role PostgreSQL di Server**:
   ```bash
   # Di VPS 3 DATA:
   docker compose exec -T postgres psql -U postgres -c "ALTER USER alos_user WITH PASSWORD '${NEW_PASSWORD}';"
   ```
4. **Update Konfigurasi Host**:
   - Di VPS 3 DATA: perbarui `POSTGRES_PASSWORD=${NEW_PASSWORD}` di `/etc/alos/production/data.env`.
   - Di VPS 1 APP: perbarui `POSTGRES_PASSWORD=${NEW_PASSWORD}` di `/etc/alos/production/app.env`.
5. **Restart Backend Client**:
   ```bash
   # Di VPS 1 APP:
   docker compose --env-file /etc/alos/production/app.env up -d --force-recreate backend
   ```
6. **Verifikasi Konektivitas**:
   - Cek health endpoint: `curl -fsS http://127.0.0.1:8000/health`.
   - Pastikan connection pool database terhubung dengan normal tanpa auth error.
7. **Rollback jika Terjadi Kegagalan**:
   - Jika Backend gagal terhubung ke database setelah update, segera kembalikan password lama di PostgreSQL:
     ```bash
     docker compose exec -T postgres psql -U postgres -c "ALTER USER alos_user WITH PASSWORD '${OLD_PASSWORD}';"
     ```
   - Kembalikan `POSTGRES_PASSWORD` di file env VPS 1 dan restart Backend.
