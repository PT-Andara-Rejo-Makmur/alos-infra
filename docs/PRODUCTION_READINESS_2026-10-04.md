# Audit dan implementasi ALOS — 4 Oktober 2026

**Status: perubahan development telah diimplementasikan dan diverifikasi lokal; seluruh platform belum dinyatakan production-ready.** Target 12 Oktober 2026 tetap memerlukan gate staging, model nyata, penerimaan bisnis, dan persetujuan deployment. Tidak ada commit, push, perubahan main, deployment production, atau penghapusan data operasional dalam pekerjaan ini.

**Integrasi dilanjutkan setelah redesign Web:** pengguna menyatakan tampilan sudah final. Desain tersebut dipertahankan dan diuji ulang: Web 618 tes, GENESIS 638 tes, ARA BFF 10 pemeriksaan, ARA NORMAL/provider mock 30 pemeriksaan, dan browser 11 skenario lulus. Sebanyak 22 perbandingan hash membuktikan source Backend/GENESIS yang diperiksa cocok dengan image lokal dan audit yang berjalan. Konfigurasi lokal kini memakai NORMAL ketika model dikonfigurasi; mode TEST tidak lagi dipaksakan oleh Compose. Status dan badge ARA mengikuti authority dan sumber respons. Rincian hasil sesudah redesign ada pada [laporan integrasi development](INTEGRATION.md).

**UAT terbaru atas arahan “anda yang uji”:** 25 skenario browser dan 619 tes Web lulus,
disertai 9 tes integrasi Backend serta 1 regresi tambahan untuk catatan historis.
Cacat verifikasi/penutupan Temuan dengan Tugas korektif belum selesai telah diperbaiki
di Backend dan pesan tindakan Web. Sepuluh pemeriksaan ARA BFF diulang dan lulus pada
GENESIS TEST. Aplikasi development lokal telah diperbarui; identitas container, image
dan volume database operasional tetap sama. Scan image terbaru tetap memblokir gate
produksi karena findings HIGH. Rincian dan log ada pada
[laporan UAT bisnis](BUSINESS_UAT_2026-10-04.md).

Paket source dan diff checkpoint: `alos-infra/.audit/alos-development-review-2026-10-04.zip`, disertai manifest SHA-256 setiap file serta baseline tiap repository. Ini snapshot lokal untuk review/pemulihan, bukan commit, release atau deployment. File `scripts/seed_demo_data.py` milik pengguna dikecualikan. Jangan reset/checkout atau mengganti seluruh repository Web dengan template sehingga perubahan lokal checkpoint hilang.

## Sumber yang diaudit

Semua checkout berada pada `development`. Infra di-fast-forward ke development terbaru sebelum perubahan. SHA berikut adalah baseline; perubahan lokal belum berada pada commit tersebut.

| Repository | Baseline SHA |
| --- | --- |
| alos-web | bdd80e76db3efd2dfc3b6f7e287c1adf2912f6e8 |
| alos-backend | fb0cbc002182b37382b165548ee7614df3f40389 |
| genesis-ai | ff11f49ac6659d6054e1a0ac1c67bb12cf2ee0dc |
| alos-contracts | c39bb6db6f851b9fbdd626fa14fca0853fcdae3e |
| alos-infra | 45d8dbd3d9c94e08f5a8a7dafff86e27a11920cf |

Audit menelusuri routing workspace, BFF/session, domain services, Shared Work/processes, lifecycle dan registry agent, tool catalog, evidence/memory, model planner, contracts/generated types, migrations, worker, dependency graph, compose, CI, backup/restore, dan preflight. Pencarian TODO juga diperiksa terhadap call sites; helper legacy yang tidak dipakai bukan bukti bahwa layar aktif tidak berfungsi.

## Akar masalah dan perbaikan

1. **ARA NORMAL masih dipersempit oleh pencocokan kata kunci Backend.** Kini Backend memperoleh tool catalog dari versi ACTIVE yang telah dirilis, kemudian membatasinya menurut Principal. GENESIS/model memilih sumber relevan secara dinamis. Matcher lama hanya digunakan dalam TEST. Detail read tanpa referensi tidak dipaksakan menjadi tool call. Authority, permission, scope, budget, lifecycle, dan approval tetap milik Backend.
2. **History tidak tersedia untuk planner produksi.** Enam pesan terakhir, masing-masing maksimum 1.000 karakter, diteruskan sebagai data tanpa instruction authority. Pertanyaan lanjutan dapat memilih sumber sebelumnya; fakta harus dibaca dan diverifikasi kembali. Memory lama tidak menjadi fakta terkini.
3. **Verifikasi factual mengharuskan semua tool eligible dibaca, dan jawaban menyerupai dump.** Dalam mode dinamis, coverage diperiksa terhadap sumber yang benar-benar berhasil dibaca. Claims tetap harus cocok dengan JSON pointer dan tipe nilai sumber. Renderer memakai label bisnis, mempertahankan null/unknown, menyembunyikan authority metadata, dan membatasi daftar tanpa menyebutnya sebagai total perusahaan.
4. **Percakapan sosial dan permintaan tindakan bergantung pada keyword interception.** Model dapat memilih sapaan/bantuan/terima kasih yang dibatasi pada respons tanpa klaim faktual. Proposal TASK/MATERIAL_ACTION/CAPABILITY_DRAFT diperiksa terhadap permission aktual dan tetap membutuhkan review; tidak mengeksekusi tindakan. Pertanyaan tentang perhatian pekerjaan tidak otomatis menjadi pembuatan task.
5. **Analisis numerik belum memiliki verifikasi perhitungan.** Operasi SUM/DIFFERENCE/RATIO/PERCENT_CHANGE dihitung oleh runtime menggunakan Decimal atas claims indikator canonical yang telah diverifikasi. Sumber dan path indikator dibatasi; metadata `available`, satuan `COUNT/AMOUNT/PERCENT`, indeks unik, pembagi, dan baseline diperiksa. Model tidak dapat mengirim nilai hasil perhitungannya sendiri. Ini belum merupakan analisis kausal atau financial advice bebas.
6. **Delegasi mengambil tool pertama yang eligible meskipun tidak relevan.** Child read sekarang berasal dari sumber yang benar-benar dipakai parent dan tetap berada dalam release serta scope yang disahkan. Cancellation parent/child dan evidence lineage tetap diperiksa.
7. **Timeout client GENESIS generik lebih pendek daripada anggaran run.** Transport mengikuti deadline Backend dengan overhead lima detik; definisi legacy tanpa deadline dibatasi 30 detik oleh server. Kegagalan transport ditutup sebagai FAILED/TIMED_OUT, dan timeout/unavailable diproyeksikan sebagai 503. ARA tanpa release ditolak sebelum reservasi percakapan.
8. **KPI unavailable dan grafik bernilai nol kurang jelas.** Dashboard bersama menggunakan kartu responsif, hierarki nilai unavailable, coverage indikator, dan panel grafik konsisten. Grafik seluruh kategori nol menampilkan status eksplisit serta tabel angka aslinya. ARA menampilkan pertanyaan pending segera, mengikuti pesan terbaru tanpa memaksa scroll pembaca, dan mendukung Ctrl/Command+Enter.
9. **Dependency security.** Next/eslint-config-next ditingkatkan ke 16.3.6; pytest dan pip minimum aman diterapkan, serta PyJWT framework GENESIS minimum 2.15. Braces 3.0.3 masih dilaporkan advisory upstream dan belum memiliki rilis patch di registry saat audit. Patch lokal membatasi kedalaman parse/compile/expand/stringify, termasuk AST eksternal. Security gate menguji mitigasi dan hanya mengizinkan advisory spesifik tersebut pada dependency development yang dipatch. Image Web final tidak membawa ESLint, Vitest, atau Playwright.
10. **Preflight dapat menerima tag versi sebagai immutable dan mengabaikan precedence environment.** Image/rollback kini wajib digest SHA-256 lengkap. Environment, termasuk override kosong, mengikuti precedence Compose. File eksplisit ikut pemeriksaan isolasi staging/production.
11. **Contoh dan fallback endpoint router memakai HTTP publik.** Fallback tersebut dihapus dari development, integration, staging dan production. Konfigurasi GENESIS staging/production dan preflight sekarang menolak koneksi model tanpa HTTPS. Preflight juga memerlukan API key dan setidaknya satu profil model, serta menolak kredensial di URL. Endpoint HTTPS yang benar tetap harus berasal dari konfigurasi deployment yang disahkan.
12. **Audit paket terpasang tidak mencakup seluruh image.** Scan Trivy menemukan library bawaan pip dan npm serta PCRE OS yang rentan. Installer build dihapus dari runtime dan pembaruan PCRE dipasang. Staging diselaraskan dengan pembatasan capabilities produksi. CI sekarang mengaudit image dan menyimpan seluruh findings. Gate ketat tetap menolak delapan CVE OS unik tanpa patch distro; rincian ada pada [laporan container security](CONTAINER_SECURITY_2026-10-04.md).
13. **Image infrastruktur masih membawa dependency rentan.** Caddy diperbarui ke artifact 2.11.6 yang tersedia dan collector contrib diganti core 0.162.0 setelah verifikasi semua komponen konfigurasi dan transport OTLP. Database candidate dibangun dari PostgreSQL 16 Alpine, pgvector 0.8.7 dengan commit/checksum sumber yang dipin, dan gosu 1.19 dengan Go 1.27.1. Compiler tidak masuk runtime. Ketiganya sekarang memiliki 0 HIGH/CRITICAL dalam scan. Preflight meminta digest database eksplisit dan menolak override image pendukung mutable. Migrasi database operasional lintas distro belum dilakukan atau disahkan.
14. **Restore proof lama tidak benar-benar menguji guard script.** Tes sekarang menjalankan `backup.sh` dan `restore.sh` pada Compose disposable, memverifikasi marker/vector, HNSW/IVFFlat dan nearest-vector setelah restore. Script restore membatasi identifier target, memakai parameter SQL/command, tidak menelan kegagalan pembuatan database, dan memastikan ekstensi vector benar-benar ada. Checksum rusak, konfirmasi kosong, target aktif dan target tidak aman terbukti ditolak oleh script sesungguhnya.

Contracts menambahkan `CONVERSATION` tanpa sumber, failed source, proposal, research, atau review. Python/TypeScript diregenerasi; compatibility terhadap development tidak mendeteksi breaking change yang belum disahkan. CI menambahkan security gates dan browser E2E beserta artifacts. **CI remote untuk perubahan ini belum berjalan karena perubahan belum dipush sesuai instruksi.**

## Bukti pengujian

Semua business fixtures merupakan data sintetis pada lingkungan audit disposable, bukan data perusahaan yang sah. Aplikasi lokal telah diperbarui untuk integrasi development, dengan image/volume database lama dipertahankan dan backup sebelum pembaruan disimpan secara privat. Pada batch UAT, helper demo lokal tidak dijalankan. Pada cleanup dokumentasi, script tidak terpakai tersebut dihapus dari source setelah salinannya disimpan pada arsip pemulihan privat; data operasional tidak diubah. Database operasional tidak dijadikan target acceptance, dan release fixture tidak menjadi persetujuan produksi.

| Pemeriksaan | Hasil lokal |
| --- | --- |
| Backend full suite setelah pembaruan dependency | 1.367 passed; 9 SQLAlchemy deprecation warnings |
| Backend regresi tambahan setelah perbaikan transport/release/public route | 28 passed; Ruff dan Mypy lulus |
| GENESIS full suite setelah integrasi model dan redesign | 638 passed; Ruff dan Mypy lulus |
| Web full suite setelah UAT bisnis | 619 passed, 47 files; lint dan typecheck lulus; run final menggunakan 2 worker sesudah Docker build selesai |
| Backend regresi UAT Temuan, Tugas dan authority | 9 tes integrasi lulus dan 1 regresi penutupan catatan historis lulus; Ruff/Mypy lulus. Backend memblokir verifikasi/penutupan bila Tugas korektif tertaut belum COMPLETED |
| Contracts | 242 passed; 159 schemas, OpenAPI, examples, generated checks dan compatibility lulus |
| Stack integration smoke, image build produksi | PASS: seluruh domain, Shared Work, PostgreSQL, lifecycle, evidence, cancellation, review, runtime |
| ARA melalui cookie dan Web BFF | PASS: 10 pemeriksaan termasuk injection, isolation, denied Finance, proposal/draft, sembilan sumber Executive dan child/research |
| ARA NORMAL dengan provider mock dan PostgreSQL | PASS: 30 pemeriksaan pada environment lokal dan paket Docker; dynamic read, history, perhitungan, evidence, review, isolation, cancellation, fabricated output dan provider outage |
| Browser desktop/mobile seluruh tujuh workspace, business workflow dan ARA | 25 passed pada image terbaru: 11 skenario platform ditambah 14 skenario UAT bisnis, termasuk transaksi Decimal, booking approval/stale decision, task dependency, TXT/DOCX/versioning, Reports/Findings dan penolakan akses |
| Packaged worker TEXT/DOCX | PASS: source/version hash, review boundary, SIGTERM |
| Backup/restore PostgreSQL + pgvector pada image database final | PASS: script backup/restore sesungguhnya, checksum, marker/vector, HNSW/IVFFlat, nearest-vector, tamper, konfirmasi, guard target aktif dan identifier aman |
| Caddy/collector | PASS: konfigurasi aktual, OTLP traces/metrics/logs sintetis diterima dan diproyeksikan oleh exporter debug |
| Topology | 27 invariant lulus |
| Preflight regression | 7 tes lulus, termasuk subcase digest database/image pendukung, rollback dan TLS/model configuration |
| Dependency audits Python lokal | Backend, GENESIS, contracts: tidak ada known vulnerability yang dilaporkan |
| Dependency audit Python pada image final | Backend dan GENESIS: tidak ada known vulnerability pada paket terpasang yang dilaporkan pip-audit |
| Dependency audit Web | 0 advisory tanpa mitigasi; 1 advisory Braces tetap dilaporkan upstream dan dipatch lokal |
| Container image scan enam layanan | Web: 0 findings. Database/Caddy/collector: masing-masing 1 finding, 0 HIGH/CRITICAL. Backend/GENESIS: masing-masing 166 findings, 44 HIGH berupa delapan CVE OS unik, 0 fixable HIGH/CRITICAL. Gate ketat: BLOCKED |
| Scan ulang image setelah UAT bisnis | Web tetap 0 findings; Backend tetap 166 findings/44 HIGH/0 fixable HIGH/CRITICAL. Gate strict exit 1, BLOCKED |
| Regresi gate keamanan image | 5 tes lulus; laporan tidak lengkap ditolak, scratch collector hanya pada digest yang diverifikasi, findings tanpa patch tetap terlihat dan ditolak pada mode strict |
| Uji latency terbatas ARA TEST | 12 permintaan, concurrency 3, seluruhnya berhasil; median 8,397 detik, p95/max 8,939 detik; belum membuktikan kapasitas produksi |

Log dan laporan lokal disimpan pada `.audit/` (diabaikan Git). Screenshot/trace/report browser berada pada `alos-web/test-results/` dan `alos-web/playwright-report/`. Full suite Backend selesai sebelum perubahan terakhir pada transport/public route dan guard Tugas korektif; regresi targeted dan pengujian stack melengkapi verifikasi perubahan tersebut. Angka suite tidak dijumlahkan karena sebagian targeted tests juga ada pada full suite. Rincian acceptance terbaru ada pada [laporan UAT bisnis](BUSINESS_UAT_2026-10-04.md).

Bukti pada stack database final: `.audit/stack-data-image-integration-final.log`, `.audit/ara-data-image-bff-final.log`, `.audit/ara-data-image-production-final.log`, `.audit/browser-data-image-audit-final.log`, `.audit/restore-controlled-audit-final.log`, `.audit/telemetry-transport-audit-final.log` dan `.audit/image-security-audit-final.log`. Gate strict tetap tercatat gagal pada `.audit/image-security-strict-gate-final.log` karena findings OS tanpa patch.

Pernah terjadi source timeout saat acceptance dijalankan bersamaan dengan build dan suite berat; pengulangan lulus. Failure menutup dengan status jujur, tanpa membuat jawaban kosong palsu. Hasil latency TEST memerlukan profiling dan optimasi sebelum menetapkan SLA; pengujian kapasitas dan latency model nyata masih merupakan gate produksi.

## Yang belum siap dan kebutuhan eksternal

- **ARA kualitas Hermes belum terbukti.** Konfigurasi model development kini tersedia dan telah menyelesaikan connectivity serta sebagian percakapan/pembacaan sumber sintetis. Eval lanjutan belum lulus: pengulangan pembacaan sumber ditemukan lalu diperbaiki, tetapi pemeriksaan ulang terhenti karena 9Router mengembalikan HTTP 503 dengan indikasi kuota habis. Pengguna menunda pengujian nyata sampai kuota atau profil cadangan tersedia. Provider mock membuktikan protokol, grounding, dan kontrol, bukan naturalness atau kualitas analisis model nyata. Perlu eval percakapan Indonesia, follow-up lintas divisi, prompt injection, latency/biaya, dan kegagalan provider menggunakan data staging yang disahkan.
- **Release authority produksi.** Versi agent/model policy/scopes/permission yang sesuai harus melalui lifecycle review dan release nyata. Fixture release pada acceptance tidak digunakan sebagai keputusan bisnis produksi.
- **Container security gate belum tertutup.** Delapan CVE OS unik masih dilaporkan HIGH pada base Debian Backend/GENESIS tanpa patch stable. Non-root, read-only filesystem, no-new-privileges dan drop capabilities mengurangi permukaan akses; penilaian reachability, base yang dipatch atau keputusan risiko keamanan yang disahkan masih diperlukan. Gate strict telah diuji dan gagal sebagaimana mestinya.
- **Implementasi tambahan masih terlihat pada repository.** Route legacy Property kontraktor, material/pengadaan dan RAB; HR compensation; IT assets/support masih mempunyai layar unavailable dan belum mempunyai domain contracts terkait yang lengkap. Sebagian tidak ada pada navigasi aktif. Ini bukan fitur siap dan tidak diganti dengan form yang melaporkan success palsu. Kebijakan payroll, procurement/material approval, ownership sumber, dan acceptance bisnis perlu ditetapkan sebelum workflow materialnya dinyatakan siap.
- Integrasi eksternal, live monitoring/SLA, live CI/deployment execution, regulasi otomatis, tanda tangan digital, dan sinkronisasi aset belum terbukti aktif. Inventory recording tidak sama dengan menjalankan layanan eksternal.
- Provisioning empat VPS, DNS/TLS/firewall, secrets staging/production, image digests final, monitoring/alert delivery, backup operasional, restore/RTO/RPO, dan rollback pada environment tujuan belum diverifikasi. Restore disposable bukan disaster recovery produksi yang telah disahkan.
- Kandidat database baru menggunakan Alpine; volume/database Debian yang sudah berjalan membutuhkan logical dump/restore ke volume staging baru dan verifikasi collation/index/aplikasi serta rollback. Database operasional tidak diganti pada audit ini; image registry rilis belum dipublish.
- CI remote dan cross-repository release bundle belum dapat diverifikasi pada perubahan lokal tanpa commit/push. Build dependency ranges masih dapat berubah pada rebuild; final artifact harus dipin dan diuji bersama.

## Urutan menuju 12 Oktober

| Waktu | Gate berbasis risiko |
| --- | --- |
| 5–6 Oktober | Review diff; verifikasi CI pada bundle yang disahkan; konfigurasi model staging dan release authority; eval ARA nyata dan negative authorization |
| 6–8 Oktober | Tutup scope modul yang masih unavailable dengan contracts/approval rules serta penerimaan bisnis; integrasi sumber yang dipilih |
| 8–10 Oktober | UAT seluruh workflow; load/latency dan security checks; migration, backup/restore dan rollback staging pada image digest final |
| 11 Oktober | Bukti semua gate, keputusan go/no-go, rollout dan rollback plan |
| 12 Oktober | Deployment production hanya setelah persetujuan; target tanggal tidak menggantikan bukti kesiapan |

Jadwal ini merupakan urutan gate, bukan jaminan semua scope selesai pada tanggal tersebut. Masalah yang dapat diperbaiki di repository telah dikerjakan pada batch ini; pekerjaan implementasi tambahan di atas belum dinyatakan selesai.
