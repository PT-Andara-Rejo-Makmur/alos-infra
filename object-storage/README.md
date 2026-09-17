# Object Storage Boundary

Object storage belum diprovision oleh bootstrap. Interface konfigurasi hanya terdiri dari
`OBJECT_STORAGE_ENDPOINT` dan `OBJECT_STORAGE_BUCKET`. Credential tidak boleh menggunakan prefix
publik, tidak disimpan di Git, dan harus berasal dari secret manager deployment.

Pemilihan provider, encryption, retention, lifecycle, versioning, dan access policy memerlukan
requirement/ADR baru. MinIO tidak ditambahkan.
