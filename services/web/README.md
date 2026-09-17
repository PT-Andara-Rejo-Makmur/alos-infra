# Service Web

`alos-web` berjalan sebagai production Next.js server pada port container `3000`. Service hanya
bergabung ke network `edge`, menerima Backend public URL, dan tidak memiliki route jaringan ke
GENESIS atau PostgreSQL.

Local environment membangun sibling repository. Staging/production wajib memakai image yang
telah dibangun CI aplikasi; tidak ada source mount atau `pnpm dev`.
