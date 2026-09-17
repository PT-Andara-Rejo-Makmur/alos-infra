# Infrastructure Policies

- deny public route untuk GENESIS, PostgreSQL, dan OTLP;
- hanya Backend yang memiliki jalur aplikasi ke GENESIS;
- tidak ada secret di Git atau public frontend environment;
- application image production harus immutable dan telah melewati quality gate;
- backup/restore dan rollback memerlukan operator approval serta evidence;
- perubahan network, volume, atau secret interface wajib direview Platform dan service owner.
