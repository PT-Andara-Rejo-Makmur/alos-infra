# Runbook GENESIS Down

1. Konfirmasi `/health` melalui internal exec dan periksa container status/log.
2. Verifikasi Backend sehat dan tidak memberi browser/direct fallback ke GENESIS.
3. Tandai fitur AI unavailable/degraded melalui Backend behavior yang disetujui.
4. Periksa PostgreSQL, OTLP, token/config, DNS network internal, dan resource exhaustion.
5. Restart hanya service GENESIS bila aman; jangan membuka port publik sebagai workaround.
6. Verifikasi Backend → GENESIS dengan correlation ID dan catat incident evidence.

Business command non-AI hanya dilanjutkan jika Backend policy menyatakannya aman.
