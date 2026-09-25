# Runbook Restore Database ALOS

Dokumen ini mendefinisikan prosedur pemulihan (*restore*) database PostgreSQL terkelola untuk lingkungan ALOS MVP-2.

> [!CAUTION]
> **Tindakan Destruktif:** Proses restore akan menghapus/menimpa skema dan data yang ada pada database target (`--clean --if-exists`). Jalankan hanya dengan otorisasi resmi (*human approval*) dan setelah mengambil snapshot cadangan (*safety backup*).

---

## 1. Safety Guards yang Ditegakkan

Script restore (`database/restore/restore.sh` dan `restore.ps1`) secara otomatis menerapkan 10 lapis pengamanan:

1. **Path Backup Eksplisit**: Operator wajib menentukan file `.dump` sasaran.
2. **Validasi Eksistensi File**: File tidak boleh kosong atau hilang.
3. **Validasi Checksum SHA-256 Sidecar**: File sidecar `.sha256` wajib ada dan cocok 100% sebelum operasi database dimulai.
4. **Default Target Non-Produksi**: Jika parameter `--target-db` tidak ditentukan, script secara default mengarah ke database verifikasi non-produksi (`alos_restore_verify`).
5. **Production Overwrite Guard**: Jika target database mengarah ke database produksi aktif, operasi akan ditolak kecuali operator menyertakan flag `--confirm-production` atau `CONFIRM_PRODUCTION=YES`.
6. **Konfirmasi Global Mandatory**: `CONFIRM_DATABASE_RESTORE=YES` wajib diset.
7. **Deterministik**: Menggunakan `pg_restore --clean --if-exists --exit-on-error`.
8. **Verifikasi Otomatis**: Memeriksa integritas query dan keberadaan extension `vector`.
9. **Kredensial Terlindungi**: Password dan token tidak pernah dicetak ke terminal atau log.
10. **Pembersihan Kontainer Otomatis**: File sementara di kontainer selalu dihapus via trap cleanup.

---

## 2. Prosedur Restore Standar

### A. Uji Coba Verifikasi Restore (Non-Produksi / Staging)

Untuk membuktikan bahwa file backup valid tanpa menyentuh database produksi:

```bash
# Di VPS 3 DATA atau Staging:
CONFIRM_DATABASE_RESTORE=YES \
  bash database/restore/restore.sh /opt/alos/backups/alos-db-20260925T020000Z.dump \
  --target-db alos_restore_verify
```

### B. Pemulihan Bencana ke Database Produksi Aktif

Hanya dijalankan saat pemulihan dari korupsi data atau disaster recovery:

1. **Isolasi Traffic Menulis**:
   - Di VPS 1 APP, matikan Backend untuk mencegah transaksi baru:
     ```bash
     docker compose --env-file /etc/alos/production/app.env stop backend
     ```

2. **Ambil Safety Backup dari Database Saat Ini**:
   - Meskipun data sedang rusak atau bermasalah, ambil backup snapshot terakhir untuk keperluan forensik:
     ```bash
     # Di VPS 3 DATA:
     bash database/backup/backup.sh
     ```

3. **Verifikasi Checksum File Cadangan yang Akan Dipulihkan**:
   ```bash
   sha256sum -c /opt/alos/backups/alos-db-target.dump.sha256
   ```

4. **Eksekusi Restore ke Database Produksi**:
   ```bash
   # Di VPS 3 DATA:
   CONFIRM_DATABASE_RESTORE=YES CONFIRM_PRODUCTION=YES \
     bash database/restore/restore.sh /opt/alos/backups/alos-db-target.dump \
     --target-db alos_production \
     --confirm-production
   ```

5. **Verifikasi Skema & Konsistensi Data**:
   - Periksa ekstensi:
     ```bash
     docker compose exec postgres psql -U alos_user -d alos_production -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
     ```
   - Periksa revisi skema Alembic dari container Backend:
     ```bash
     # Di VPS 1 APP:
     docker compose --env-file /etc/alos/production/app.env run --rm --no-deps backend alembic current
     ```

6. **Nyalakan Kembali Backend & Buka Traffic**:
   ```bash
   # Di VPS 1 APP:
   docker compose --env-file /etc/alos/production/app.env up -d backend
   bash scripts/health-check.sh --target all
   ```

7. **Dokumentasikan Pemulihan**:
   - Catat timestamp restore, nama file dump, checksum, operator penanggung jawab, dan nomor tiket insiden.
