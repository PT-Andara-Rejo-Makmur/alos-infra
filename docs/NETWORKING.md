# Networking

## Ingress

Caddy menerbitkan 80/443 dan merutekan dua hostname: Web ke `web:3000`, API ke `backend:8000`.
Tidak ada route untuk GENESIS, PostgreSQL, atau OTLP.

## Edge

`caddy`, `web`, dan `backend` berada pada network `edge`. Web tidak menjadi anggota network
`internal` maupun `data`, sehingga tidak memiliki container route langsung ke GENESIS/database.

## Internal dan data

Backend dan GENESIS berada di `internal`; OTEL Collector juga berada di network ini. Backend dan
GENESIS dapat berada di `data` untuk persistence responsibility, tetapi credential/schema harus
dipisahkan sesuai ownership. PostgreSQL hanya berada di `data`. Kedua network ditandai
`internal: true`.

Local Web/Backend dipublish ke `127.0.0.1`, bukan semua host interface. GENESIS/PostgreSQL hanya
menggunakan `expose`, yang tidak menerbitkan host port.

Firewall provider/host harus mengikuti baseline pada `networking/firewall/README.md`.
