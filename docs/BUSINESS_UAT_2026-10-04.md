# Pengujian bisnis development — 4 Oktober 2026

Pengujian dijalankan oleh coding agent atas arahan pengguna, melalui browser Chromium,
cookie Web BFF, API Backend, PostgreSQL, GENESIS TEST dan worker dokumen yang nyata.
Seluruh akun dan catatan merupakan fixture sintetis pada stack `alos-audit-20261004`
(Web 13000, Backend 18000) atau database tes pada PostgreSQL audit port 55432.
Fixture tidak diperlakukan sebagai data perusahaan atau keputusan produksi yang sah.
Pengujian model 9Router tetap ditunda sesuai arahan pengguna; tidak ada inference tambahan.

## Cakupan penerimaan teknis

- Sales: Customer → Lead → kualifikasi, relasi ke Unit Property, pembuatan Booking,
  persetujuan independen, eksekusi eksplisit, konsumsi sekali, penolakan self-approval,
  persetujuan pending, replay dan keputusan lama setelah tanggal Booking berubah.
- Property: pembuatan dan pembaruan Unit; luas yang belum diketahui tetap null.
- Finance: rekening dan transaksi bank; nominal `90071992547409.93` tersimpan persis
  sebagai Decimal, mata uang tetap IDR, transaksi tidak dapat diedit.
- Legal: perjalanan form Kontrak; status DRAFT dan tanggal yang belum diketahui tetap null.
- HR/GA: Permintaan Fasilitas → IN_PROGRESS, tanpa mengarang catatan penyelesaian.
- IT: pembuatan/pembaruan inventaris Sistem dan criticality; tidak ada provisioning eksternal.
- Shared Work: ketergantungan Tugas, penyelesaian berurutan dan progress Proyek,
  penolakan baca/mutasi workspace asing, dan penolakan CRUD Sales tanpa peran divisi.
- Dokumen: metadata tanpa file, review diblokir tanpa versi, upload TXT/DOCX lewat worker,
  pemeriksaan SHA-256 byte asli, klasifikasi, isi hanya dapat digunakan setelah persetujuan,
  reviewer independen, penolakan akses asing, idempotensi upload, konflik nomor versi dan
  lineage versi lama yang tetap utuh.
- Laporan dan Temuan: pengajuan, pemeriksaan oleh pengguna berbeda, penerbitan/arsip atau
  verifikasi/penutupan yang eksplisit dan mengikuti kewenangan Backend.
- Cakupan sebelumnya tetap mencakup tujuh dashboard desktop/mobile, Shared Work, Strategy,
  Campaign, ARA bersumber pada TEST, fokus composer dan penolakan BFF anonim.

## Cacat yang ditemukan dan diperbaiki

`SharedWorkService.transition_finding` sebelumnya hanya memeriksa lifecycle Temuan dan
independensi reviewer. Tugas korektif yang tertaut belum diperiksa: API dan browser dapat
menghasilkan VERIFIED walaupun Tugas masih belum selesai. Reproduksi menggunakan fixture
terisolasi berhasil pada tes integrasi PostgreSQL dan browser, sebelum perbaikan.

Backend kini membaca dan mengunci Tugas dalam transaksi yang sama, memvalidasi visibilitas
terhadap principal aktif, dan mewajibkan COMPLETED sebelum `verify` atau `close`.
Pengajuan pemeriksaan tetap tersedia; reviewer dapat menelaah pekerjaan yang belum selesai,
tetapi belum dapat menyatakan Temuan terselesaikan. Temuan tanpa Tugas korektif tetap
mengikuti lifecycle pemeriksaan manusia yang berlaku. Tidak ada penyelesaian otomatis,
penggantian reviewer, perubahan catatan operasional atau bypass evidence/approval.

Penolakan mengembalikan `FINDING_CORRECTIVE_ACTION_INCOMPLETE` (409), tidak memutasi
status/verifier atau menambah audit sukses. Web menampilkan tindakan yang diperlukan:
selesaikan tugas korektif yang tertaut sebelum memverifikasi atau menutup Temuan.
Pemeriksaan pada `close` juga melindungi catatan VERIFIED historis yang tidak konsisten.

## Bukti dan batas hasil

| Pemeriksaan terbaru | Hasil dan bukti lokal pada `.audit/` |
| --- | --- |
| Browser Chromium pada image development audit | **25 passed**, 6 menit: 14 skenario bisnis baru dan 11 skenario platform; `browser-business-uat-final.log` |
| Web full unit/component suite | **619 passed**, 47 file, 193,75 detik; `web-business-uat-suite-complete.log` |
| Web lint dan typecheck | PASS; `web-business-uat-lint-final.log`, `web-business-uat-typecheck-final.log` |
| Backend Temuan/Tugas/workspace authority | **9 passed**, PostgreSQL nyata; `finding-corrective-regression-after.log` |
| Backend close untuk Temuan VERIFIED historis dengan Tugas belum selesai | **1 passed**; `finding-legacy-close-regression.log` |
| Backend Ruff/Mypy | PASS; Mypy 241 file source; `finding-corrective-quality.log` |
| ARA melalui cookie Web BFF → Backend → GENESIS TEST | **10 pemeriksaan PASS**: history, evidence, injection, authority, isolation, Finance denied, proposal dan child/research; `ara-business-uat-bff.log` |
| Penolakan target database aplikasi lokal oleh harness UAT | PASS: guard menolak 3000/8000 sebelum registrasi fixture; `uat-operational-target-refusal.log` |
| Build image Backend/jobs dan Web | PASS; `uat-backend-build.log`, `uat-web-build.log`, `uat-local-web-build.log` |
| Deployment aplikasi development lokal dan audit | Web/Backend/GENESIS/PostgreSQL sehat; worker berjalan, pemrosesan TXT/DOCX terbukti pada browser audit. Worker tidak mempunyai Docker healthcheck sendiri |
| Source pada image yang berjalan | Empat SHA-256 modul `domains/shared_work.py` cocok dengan source host, pada Backend/jobs lokal dan audit; `uat-runtime-source-proof.json` |
| HTTP lokal setelah update | Web 3000 dan Backend 8000/health: 200; BFF Finance anonim: 401; `uat-runtime-source-proof.json` |
| Database operasional sebelum/sesudah update aplikasi | ID container, image dan named volume **sama**; `uat-runtime-source-proof.json`. Compose menggunakan `--no-deps`, tanpa mengganti PostgreSQL |
| Trivy pada image Web terbaru | **0 findings**; `trivy/web-business-uat.json`, `image-security-business-uat.log` |
| Trivy pada image Backend terbaru | **166 findings, 44 HIGH, 0 fixable HIGH/CRITICAL**; `trivy/backend-business-uat.json` |
| Gate strict image produksi | **BLOCKED**, exit 1 untuk 44 findings HIGH. Penolakan tetap berlaku; `image-security-business-uat-strict.log` |

Screenshot tiap skenario bisnis tersimpan pada `alos-web/test-results/`; report browser ada
pada `alos-web/playwright-report/index.html`. Semua bukti di atas merupakan penerimaan
teknis development dengan fixture sintetis, bukan persetujuan bisnis atau produksi.
Full suite Backend 1.367 tes adalah checkpoint sebelum perbaikan terakhir; suite tersebut
tidak diklaim telah dijalankan ulang setelah guard Tugas korektif. GENESIS 638 tes dan
contracts 242 tes berasal dari checkpoint integrasi sebelumnya yang source-nya tidak
berubah pada tahap UAT ini. Angka targeted test tidak dijumlahkan ke full suite.

Run parsial yang dihentikan saat Docker build dan empat worker unit test bersaing untuk
RAM tidak dihitung sebagai PASS. Run Web sebelumnya mencatat 618 passed dan 1 kegagalan
tes mock outage Approvals; mock diubah menjadi outage persisten dan penantian render async.
Full suite final kemudian menyelesaikan seluruh 619 tes dengan dua worker.
Perubahan harness awal juga tidak dihitung sebagai cacat aplikasi: navigasi tab harus
dibuka, Booking berawal PENDING, update Booking hanya menyediakan tanggal sesuai contracts,
isi dokumen DRAFT ditolak 409, dan peran divisi memperoleh permission default menurut policy.

CI integration diberi penanda disposable agar guard UAT menerima stack CI 3000/8000 hanya
pada CI dengan opt-in eksplisit. Development lokal 3000/8000 ditolak oleh harness UAT.
CI remote untuk perubahan lokal belum dijalankan karena pengguna melarang commit/push.

Kesiapan seluruh platform produksi belum dinyatakan: model nyata, TLS gateway, temuan OS
pada image Backend/GENESIS, environment tujuan dan modul legacy masih mengikuti
[gate produksi](PRODUCTION_READINESS_2026-10-04.md). Tidak ada Git commit/push,
perubahan main, deployment production atau penghapusan data operasional.

Snapshot source/diff dan bukti terbaru disimpan lokal pada
`.audit/alos-business-uat-development-review-2026-10-04.zip`, dilengkapi manifest file,
baseline lima repository, SHA-256 serta pemeriksaan isi ZIP. Kredensial, dump database,
file `.env`, folder `.audit` dan script seed milik pengguna tidak termasuk source bundle.
