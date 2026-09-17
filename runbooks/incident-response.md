# Runbook Incident Response

## Stabilkan

Tetapkan incident commander, severity, timeline, affected tenant/scope, dan communication channel.
Prioritaskan containment tanpa menghapus evidence. Jangan memasukkan secret atau personal data ke
chat/ticket yang tidak disetujui.

## Investigasi

Gunakan `correlation_id` untuk mengikuti Web → Backend → GENESIS → Tool → Backend. Kumpulkan
timestamp, image digest, config version, container status, logs, health, network change, dan audit
reference. Redact credential.

## Pulihkan

Pilih restart, rollback, secret rotation, restore, atau traffic isolation berdasarkan evidence dan
approval. Setelah recovery, verifikasi authority boundary, tenant isolation, audit continuity,
backup state, dan user journey.

## Setelah incident

Dokumentasikan root cause, impact, detection gap, timeline, remediation owner, due date, dan test
regression. Hindari menyebut incident selesai sebelum authoritative state dan audit konsisten.
