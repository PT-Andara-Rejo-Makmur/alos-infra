# Runbook Rollback Rilis Production ALOS

Dokumen ini mendefinisikan prosedur rollback aman untuk rilis production ALOS MVP-2 dengan menggunakan referensi image immutable dan analisis kompatibilitas migrasi database.

---

## 1. Prinsip Utama Rollback

1. **Penggunaan Immutable Digest Pinning**:
   - Rilis saat ini (*failing release*) dan rilis sebelumnya (*previous known-good release*) wajib didefinisikan menggunakan cryptographic digest (`@sha256:...`) atau immutable semver tag.
   - Dilarang keras menggunakan tag mutable seperti `:latest` untuk rollback.
2. **Evaluasi Kompatibilitas Database Wajib Dilakukan**:
   - Jika rilis melibatkan migrasi skema database (Alembic) yang **tidak backward-compatible**, rollback container aplikasi saja **TIDAK CUKUP** dan dapat menyebabkan crash loop / data corruption.
3. **Persetujuan Manusia (Human Operator Approval)**:
   - Keputusan untuk melakukan rollback aplikasi atau restore database wajib mendapatkan persetujuan eksplisit dari Incident Commander / Lead Engineer.

---

## 2. Matriks Keputusan Rollback

```text
                               Apakah rilis menyertakan migrasi DB?
                                       /                 \
                                    TIDAK                 YA
                                     /                     \
                      Jalankan Tipe A:           Apakah skema backward-compatible?
                     (Application Rollback)              /                 \
                                                       YA                 TIDAK
                                                       /                     \
                                           Jalankan Tipe A          Jalankan Tipe B / C:
                                      (App Rollback aman)      (Downgrade atau Controlled Restore)
```

| Tipe Kasus | Kondisi Skema | Tindakan yang Diambil | Risiko & Waktu |
|---|---|---|---|
| **Tipe A: App Rollback Only** | Tidak ada migrasi DB, atau kolom/tabel baru bersifat aditif & nullable (backward-compatible). | Kembalikan image env file ke known-good digest, restart container. | Rendah (~1-2 menit downtime). |
| **Tipe B: DB Downgrade** | Migrasi memiliki script `alembic downgrade` teruji dan tidak ada data loss pada kolom terkait. | Jalankan `alembic downgrade <revision>`, lalu kembalikan image app. | Sedang (~5 menit). |
| **Tipe C: DB Restore Required** | Skema mengalami perubahan destruktif (drop column, type alter, constraint ketat) dan downgrade gagal. | Hentikan traffic, restore database dari pre-migration snapshot. | Tinggi (RTO tergantung ukuran dump). |

---

## 3. Langkah Operasional Rollback

### Tipe A: Application Rollback (Image Rollback)

1. **Deklarasikan Rollback**:
   - Catat ticket insiden, correlation ID, dan rilis yang ditarik.
2. **Siapkan Pasangan Referensi Image**:
   ```bash
   # Referensi saat ini (failing):
   # ALOS_WEB_IMAGE=example.invalid/alos-web:v1.2.0@sha256:bad...
   # ALOS_BACKEND_IMAGE=example.invalid/alos-backend:v1.2.0@sha256:bad...
   # GENESIS_IMAGE=example.invalid/genesis-ai:v1.2.0@sha256:bad...

   # Referensi previous known-good:
   PREV_WEB_IMAGE="example.invalid/alos-web:v1.1.0@sha256:good111..."
   PREV_BACKEND_IMAGE="example.invalid/alos-backend:v1.1.0@sha256:good222..."
   PREV_GENESIS_IMAGE="example.invalid/genesis-ai:v1.1.0@sha256:good333..."
   ```
3. **Perbarui File Konfigurasi Host**:
   - Di VPS 1 APP (`/etc/alos/production/app.env`):
     ```bash
     sudo sed -i "s|^ALOS_WEB_IMAGE=.*|ALOS_WEB_IMAGE=${PREV_WEB_IMAGE}|" /etc/alos/production/app.env
     sudo sed -i "s|^ALOS_BACKEND_IMAGE=.*|ALOS_BACKEND_IMAGE=${PREV_BACKEND_IMAGE}|" /etc/alos/production/app.env
     ```
   - Di VPS 2 GENESIS (`/etc/alos/production/genesis.env`):
     ```bash
     sudo sed -i "s|^GENESIS_IMAGE=.*|GENESIS_IMAGE=${PREV_GENESIS_IMAGE}|" /etc/alos/production/genesis.env
     ```
4. **Deploy Ulang Service**:
   - Di VPS 2 GENESIS:
     ```bash
     docker compose --env-file /etc/alos/production/genesis.env up -d --remove-orphans
     ```
   - Di VPS 1 APP:
     ```bash
     docker compose --env-file /etc/alos/production/app.env up -d --remove-orphans
     ```
5. **Verifikasi**:
   - Jalankan `bash scripts/health-check.sh --target all`.
   - Pastikan logs bersih dari crash loop: `docker compose logs --tail=100 backend`.

---

### Tipe B / C: Database Rollback / Controlled Restore

Jika rollback aplikasi gagal akibat inkonsistensi skema database:

1. **Hentikan Ingress Traffic**:
   - Di VPS 1 APP, matikan service Backend agar tidak ada request baru yang corrupt:
     ```bash
     docker compose --env-file /etc/alos/production/app.env stop backend
     ```
2. **Pilihan 1: Alembic Downgrade (Jika Script Tersedia & Teruji)**:
   ```bash
   # Di VPS 1 APP:
   docker compose --env-file /etc/alos/production/app.env run --rm --no-deps backend alembic downgrade <TARGET_REVISION>
   ```
3. **Pilihan 2: Controlled Database Restore dari Pre-migration Snapshot**:
   - Jika downgrade tidak memungkinkan atau data corrupt:
   - Ambil emergency snapshot dari database saat ini:
     ```bash
     # Di VPS 3 DATA:
     bash database/backup/backup.sh
     ```
   - Lakukan restore dari file backup yang diambil tepat sebelum migrasi:
     ```bash
     # Di VPS 3 DATA:
     CONFIRM_DATABASE_RESTORE=YES CONFIRM_PRODUCTION=YES \
       bash database/restore/restore.sh /opt/alos/backups/alos-pre-migration-<timestamp>.dump \
       --target-db alos_production --confirm-production
     ```
4. **Deploy Ulang Image Previous Known-Good**:
   - Ikuti langkah Tipe A di atas.
5. **Nyalakan Kembali Backend & Buka Traffic**:
   ```bash
   docker compose --env-file /etc/alos/production/app.env up -d backend
   ```
6. **Verifikasi End-to-End**:
   - Jalankan validasi user flow dan cek audit trail.
