# Service GENESIS

`genesis-ai` berada pada network internal dan menggunakan port container `8100`. Tidak ada Caddy
route atau host port untuk service ini. Hanya Backend yang boleh memanggil internal API GENESIS.

GENESIS bukan business database authority. Persistence runtime/reference di masa depan harus
memakai role/database yang dipisahkan dan migration milik repository GENESIS.
