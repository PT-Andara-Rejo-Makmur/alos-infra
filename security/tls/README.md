# TLS

Caddy mengelola TLS untuk hostname Web dan API ketika DNS publik valid dan port 80/443 tersedia.
Operator bertanggung jawab atas DNS, certificate policy, private CA bila digunakan, serta
verification renewals. Service internal menggunakan private Compose network pada baseline;
internal mTLS memerlukan requirement baru.
