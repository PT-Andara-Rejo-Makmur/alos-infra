# Service Backend

`alos-backend` adalah authority platform pada port container `8000`. Backend bergabung ke
`edge` untuk menerima traffic Caddy, `internal` untuk memanggil GENESIS/OTLP, dan `data` untuk
PostgreSQL. Internal token disediakan operator melalui secret interface.

Migration dijalankan oleh release procedure repository Backend, bukan didefinisikan di Infra.


SMTP delivery uses generic configuration in the staging/production .env examples. Supply
EMAIL_FROM, EMAIL_FROM_NAME, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD and APP_PUBLIC_URL
through environment/secrets. Switching SMTP providers changes configuration only. Empty or invalid
required SMTP configuration fails Backend Settings construction in staging/production. Readiness
only exposes email_configured, never credentials. Migrate legacy SMTP_APP_PASSWORD secrets to
SMTP_PASSWORD; Backend temporarily supports the old name when the canonical name is absent.
SMTP_USE_TLS=true uses STARTTLS on port 587 and implicit TLS on port 465. Integration uses the
explicit in-memory email adapter and needs no real sender or SMTP credentials.
