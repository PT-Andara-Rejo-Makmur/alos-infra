# Runbook Rollback

1. Deklarasikan rollback dan catat alasan/correlation ID terkait.
2. Periksa apakah schema masih kompatibel dengan image sebelumnya.
3. Ubah application image reference ke immutable reference terakhir yang sehat.
4. Jalankan `docker compose config --quiet`, lalu `docker compose up -d`.
5. Verifikasi health, logs, command path, dan audit trail.

Jangan menjalankan `down --volumes`, menghapus named volume, atau melakukan database restore
sebagai rollback rutin. Bila schema tidak kompatibel, hentikan perubahan dan gunakan controlled
recovery plan dengan owner aplikasi dan database.
