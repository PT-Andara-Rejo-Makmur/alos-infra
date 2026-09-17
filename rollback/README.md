# Rollback Boundary

Application rollback memilih immutable image sebelumnya dan menjalankan compatibility check.
Database restore bukan langkah default rollback. Jika migration tidak backward compatible,
ikuti recovery plan yang disetujui dan jangan menghapus volume atau menjalankan downgrade
otomatis tanpa evidence.
