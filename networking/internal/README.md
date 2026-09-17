# Internal Network

Network `internal` menghubungkan Backend, GENESIS, dan OpenTelemetry Collector. Network `data`
menghubungkan service yang memiliki persistence responsibility ke PostgreSQL. Keduanya memakai
Compose `internal: true` agar tidak menyediakan external route.
