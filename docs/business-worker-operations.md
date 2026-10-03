# Operasi worker bisnis dan object dokumen

Compose local, integration, staging, dan production app menjalankan
`jobs-worker` dari image Backend yang sama. Worker menjalankan
`python -m alos.jobs.runner`, memakai private data network dan PostgreSQL
Backend, serta volume `document-objects` yang sama. Worker tidak membuka port
publik dan tidak menerima credential provider model GENESIS.

Backend dan worker harus memakai image dan canonical contracts yang cocok.
Jalankan migration terlebih dahulu. Untuk production/staging, konfigurasi
email tetap mengikuti aturan Settings Backend existing; notification bisnis
saat ini dikirim melalui inbox aplikasi, tidak melalui SMTP baru.

`DOCUMENT_OBJECT_ROOT=/data/documents` menunjuk volume privat. Container image
membuat direktori tersebut untuk user non-root. Sesuaikan permission volume
existing tanpa memberikan akses publik. Object disimpan immutable menurut
tenant, organisasi, workspace, dan SHA-256. DB menyimpan metadata, provenance,
versi, serta ekstraksi teks; binary dokumen berada di volume.

Backup perlu menangkap PostgreSQL dan object volume yang konsisten. Setelah
restore, verifikasi satu upload berhasil, Source/DocumentVersion terbaca,
review/approval tetap benar, serta hash object cocok. Backup PostgreSQL saja
tidak cukup untuk memulihkan file. Downgrade migration yang menghapus lineage
ditolak; gunakan koreksi additive atau pemulihan snapshot terkoordinasi.

Periksa log worker, status/attempts/error code `jobs.queue`, dan upload status
API untuk diagnosis. Error aman tidak memuat konten file atau credential.
Lease yang hilang dipulihkan; hasil worker lama tidak dapat menulis versi
dokumen atau pemberitahuan setelah claim diambil worker lain. Jangan
menandai job SUCCEEDED melalui SQL untuk melewati review.

Routing, tenggat, pengingat, dan eskalasi ditentukan melalui policy Backend.
Konfigurasi perusahaan tidak memberikan grant seluruh workspace asing.
Notification obsolete dilewati bila versi pengajuan atau assignment berubah.
Pemberitahuan eskalasi tidak memberi akses detail proses maupun keputusan
Direktur otomatis.

Validasi Compose dengan `docker compose --env-file <env> -f <compose> config
--quiet`, lalu jalankan `scripts/verify-infra-topology.py`. Runtime worker dapat
diuji dengan upload TEXT/DOCX pada stack integration dan pemeriksaan hasil
Source/DocumentVersion. Restore proof existing memakai PostgreSQL disposable;
hasilnya tidak menggantikan pengujian pemulihan object volume production.

`scripts/test-business-worker.py` menyediakan pemeriksaan runtime pada satu
container dan database disposable. Gunakan Python environment Backend dengan
`ALOS_TEST_DATABASE_URL` yang menunjuk PostgreSQL pengujian yang dapat diakses
dari container melalui `host.docker.internal`, lalu jalankan
`python scripts/test-business-worker.py --image <image-backend>` dari Infra.
Jika PostgreSQL berada pada private network Docker, tentukan hostname/port
container melalui `--worker-database-host`, `--worker-database-port`, dan
`--network` sesuai network pengujian tersebut.
Script menguji upload TEXT/DOCX melalui API aktual, ekstraksi worker, lineage
hash/versi, penolakan konten sebelum approval, dan penghentian SIGTERM.
Hanya container/database bernama unik milik pemeriksaan itu yang dibersihkan.
