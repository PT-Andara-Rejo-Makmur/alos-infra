# Integrasi Development dan Pengujian Disposable

Alur aplikasi adalah Web → Backend → GENESIS. Backend memiliki database, identity,
scope, evidence, tool, worker, approval, run dan audit. GENESIS memakai model melalui
ModelGateway dan mengembalikan tool requests ke Backend, tanpa network/database
bisnis. Web memakai session HttpOnly dan BFF, tanpa credential GENESIS/provider.

## Layout dan build

Kelima repository berada sejajar. Docker BuildKit memberikan `alos-contracts`
sebagai named build context ke Backend, GENESIS dan Web. Generated artifacts
harus sesuai schema sebelum image dibangun. `NEXT_PUBLIC_*` merupakan build-time
value; perubahan public Backend URL memerlukan rebuild Web.

Backend dan jobs-worker menggunakan source/contracts, database dan document
object volume yang sama. GENESIS dan Backend harus memakai service token yang
sama pada setting service masing-masing. Token tidak masuk ke Web, Git atau log.

Ikuti [local development](LOCAL_DEVELOPMENT.md) untuk aplikasi lokal. Jangan
menyalin production secrets atau menjalankan UAT/pytest pada database operasional.
Untuk mengganti image aplikasi pada instalasi existing, gunakan `--no-deps`
setelah backup dan verifikasi kompatibilitas. Image PostgreSQL existing tetap
dipertahankan; logical migration antar-distro perlu rehearsal/rollback terpisah.

## NORMAL dan TEST

Local Compose mematikan `ENABLE_TEST_TOOLS` dan `ENABLE_TEST_RUNTIME` secara
default. NORMAL memerlukan released ACTIVE Agent/model policy yang diizinkan
Backend dan route model yang valid. Tanpa konfigurasi, kegagalan tampil eksplisit;
tidak ada fallback otomatis ke TEST.

Integration Compose memakai route deterministik dan test registration secara
eksplisit, dengan database/document volume/project terpisah. Fixture adalah data
sintetis dan tidak menjadi data perusahaan atau persetujuan rilis produksi.
Model readiness/discovery tidak membuktikan inference, kuota, biaya atau kualitas.
Lihat [operasi model gateway](model-gateway-operations.md).

## Menjalankan stack integration

Dari root `alos-infra`, salin `environments/integration/.env.example` ke file
environment integration privat yang baru, isi credential development khusus,
dan atur port agar tidak bertabrakan dengan aplikasi lokal. Pilih Web 13000 dan
Backend 18000 untuk browser UAT lokal. Contoh memakai project berbeda:

```bash
docker compose -p alos-integration-uat \
  --env-file environments/integration/.env \
  -f environments/integration/compose.yaml config --quiet
docker compose -p alos-integration-uat \
  --env-file environments/integration/.env \
  -f environments/integration/compose.yaml up --build --detach --wait
```

Periksa seluruh layanan dan worker. Script smoke/restore mempunyai pilihan URL,
Compose project atau env tersendiri; gunakan `--help` dan guard target disposable
pada [ARA acceptance](ara-acceptance.md), [worker](business-worker-operations.md)
dan [backup/restore](BACKUP_RESTORE.md). Jangan mengasumsikan shell flags yang
sama berlaku untuk semua script atau mengekspos GENESIS/PostgreSQL ke publik.

Browser E2E dijalankan dari Web dengan ALOS_E2E_WEB_URL, ALOS_E2E_BACKEND_URL dan
ALOS_E2E_ALLOW_TEST_REGISTRATION=1 sesuai [pengembangan Web](https://github.com/PT-Andara-Rejo-Makmur/alos-web/blob/development/docs/DEVELOPMENT.md).
Harness menolak stack lokal 3000/8000; port tersebut hanya diterima pada CI
dengan CI=true dan ALOS_E2E_DISPOSABLE_STACK=1. Hasil browser tersimpan pada
folder ignored, dan CI menyimpan artifacts sesuai workflow.

## Gate sebelum review/commit

```bash
python scripts/verify-documentation.py
python scripts/verify-infra-topology.py
python scripts/test-preflight.py
python scripts/test-image-security.py
```

Jalankan lint/typecheck/unit/integration/schema/generation/security di masing-masing
repository sesuai perubahan. Scan harus memakai image final yang benar-benar diuji,
bukan tag mutable yang sudah menunjuk artifact lain. Gate strict menolak seluruh
HIGH/CRITICAL, termasuk tanpa patch distro; functional PASS tidak menggantikannya.

Perubahan Contracts dan consumer perlu tersedia bersama sebelum integration CI
Infra dijalankan pada development. CI checkout mencatat SHA tiap repository;
hasil lokal atas working tree belum membuktikan remote CI. Commit/push dilakukan
pengguna setelah review, bukan oleh pembersihan dokumentasi ini.

## Bukti terkini dan batas hasil

[UAT 4 Oktober](BUSINESS_UAT_2026-10-04.md) mencatat 619 tes Web, 25 skenario
browser, 9+1 regresi Backend dan 10 pemeriksaan ARA BFF TEST. Checkpoint NORMAL
provider mock mencakup 30 pemeriksaan; model nyata belum menyelesaikan eval karena
kuota dan ditunda sesuai arahan pengguna. Desain final dipertahankan.

[Readiness produksi](PRODUCTION_READINESS_2026-10-04.md) memuat baseline,
bukti per tahap dan blocker; [container security](CONTAINER_SECURITY_2026-10-04.md)
memuat findings yang masih menolak gate produksi. Arsip/log privat berada di
`.audit/` dan tidak boleh menjadi isi release. Produksi belum dinyatakan siap.
