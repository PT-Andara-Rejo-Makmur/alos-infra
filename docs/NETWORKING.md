# Networking

## Ingress

Caddy menerbitkan 80/443 dan merutekan dua hostname: Web ke `web:3000`, API ke `backend:8000`.
Tidak ada route untuk GENESIS, PostgreSQL, atau OTLP.

## Edge

`caddy`, `web`, dan `backend` berada pada network `edge`. Web tidak menjadi anggota network
`internal` maupun `data`, sehingga tidak memiliki container route langsung ke GENESIS/database.

## Internal dan data

Backend dan GENESIS berada di `internal`; OTEL Collector juga berada di network ini. Hanya Backend
yang berada di `data`; PostgreSQL juga hanya berada di `data`. Karena itu GENESIS tidak memiliki
route network langsung ke database bisnis. Jika GENESIS memerlukan persistence runtime/reference
di masa depan, gunakan database dan network terpisah melalui keputusan arsitektur eksplisit.
Kedua network ditandai `internal: true`.

Local Web/Backend dipublish ke `127.0.0.1`, bukan semua host interface. GENESIS/PostgreSQL hanya
menggunakan `expose`, yang tidak menerbitkan host port.

Firewall provider/host harus mengikuti baseline pada `networking/firewall/README.md`.
