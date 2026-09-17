# Runbook Backend Down

1. Anggap authoritative command path unavailable; jangan beralih ke browser-local state.
2. Periksa Caddy upstream, Backend health/log, database health, disk, dan resource limit.
3. Gunakan correlation ID terakhir bila tersedia, lalu korelasikan log service.
4. Pulihkan Backend atau rollback image sesuai compatibility plan.
5. Verifikasi authentication, tenant/scope enforcement, decision, audit, dan critical workflow.

Frontend boleh menampilkan disconnected state, tetapi tidak boleh memanggil GENESIS langsung.
