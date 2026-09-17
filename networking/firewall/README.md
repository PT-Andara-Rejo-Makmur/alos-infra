# Kebijakan Firewall

Firewall host/cloud berada di luar bootstrap provider-neutral ini. Baseline policy:

- buka TCP 80/443 hanya ke Caddy;
- batasi SSH/management sesuai operator policy;
- jangan buka 3000, 8000, 8100, 4317, 4318, atau 5432 ke Internet;
- batasi outbound sesuai kebutuhan registry, DNS, provider, dan object-storage endpoint;
- verifikasi rule nyata sebelum setiap deployment.
