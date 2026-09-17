# Ringkasan

Jelaskan environment, network, volume, secret interface, atau runbook yang berubah.

## Checklist

- [ ] Seluruh `docker compose config --quiet` lulus.
- [ ] GENESIS dan PostgreSQL tidak memiliki published port.
- [ ] Frontend tidak memiliki network/direct URL ke GENESIS.
- [ ] Production tidak memakai build context, source mount, atau development server.
- [ ] Tidak ada secret, credential, hostname perusahaan, atau IP nyata.
- [ ] Migration aplikasi tidak ditambahkan ke Infra.
- [ ] Backup, restore, rollback, dan failure impact telah dipertimbangkan.
- [ ] Dokumentasi/runbook Bahasa Indonesia diperbarui.
- [ ] Perubahan ini tidak melakukan production deployment dari bootstrap CI.
