# Secrets Interface

File `.env.example` hanya mendeklarasikan nama variable. `.env` nyata diabaikan Git. Staging dan
production harus menerima `POSTGRES_PASSWORD` serta `GENESIS_INTERNAL_TOKEN` dari deployment
environment atau secret manager yang disetujui.

Lakukan rotation internal token secara terkoordinasi pada Backend dan GENESIS. Jangan memasukkan
secret ke image build argument, `NEXT_PUBLIC_*`, log, command history, atau pull request.
