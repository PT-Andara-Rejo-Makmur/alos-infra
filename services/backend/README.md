# Service Backend

`alos-backend` adalah authority platform pada port container `8000`. Backend bergabung ke
`edge` untuk menerima traffic Caddy, `internal` untuk memanggil GENESIS/OTLP, dan `data` untuk
PostgreSQL. Internal token disediakan operator melalui secret interface.

Migration dijalankan oleh release procedure repository Backend, bukan didefinisikan di Infra.
