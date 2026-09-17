# Observability

OpenTelemetry Collector menerima OTLP gRPC `4317` dan HTTP `4318` pada network internal. Baseline
exporter `debug` memungkinkan wiring verification tanpa menambah monitoring platform.

Setiap request harus mempertahankan `correlation_id` sepanjang alur:

```text
Web → Backend → GENESIS → ToolRequest/ToolResult → Backend
```

Correlation ID harus muncul pada structured error/log/trace attribute dan tidak boleh mengandung
secret atau personal data. Backend tetap memiliki authoritative audit; telemetry bukan pengganti
audit trail.

Sebelum production, operator harus mengganti/menambah exporter yang disetujui, authentication,
TLS, sampling, retention, redaction, dan destination. Repository ini tidak memasang Prometheus,
Grafana, Loki, atau backend telemetry lain.
