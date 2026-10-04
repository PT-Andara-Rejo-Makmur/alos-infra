#!/usr/bin/env python3
"""Automated Restore Proof Test for ALOS Infrastructure.

Validates that database backups are actually restorable and maintain data integrity:
1. Provisions disposable test container/database.
2. Seeds database with test table, extension, and verifiable data marker.
3. Executes custom-format backup and calculates SHA-256 checksum.
4. Restores into a completely clean secondary test database.
5. Verifies schema, pgvector extension, and marker data in the restored database.
6. Cleans up disposable assets and reports PASS.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def run_cmd(cmd: list[str], check: bool = True, capture: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=check,
        env=env,
    )


def test_restore_proof() -> None:
    print("==================================================")
    print("MEMULAI PENGUJIAN RESTORE PROOF DISPOSABLE DATABASE")
    print("==================================================")

    container_name = f"alos-restore-proof-{uuid4().hex[:12]}"
    pg_user = "alos_test"
    pg_pass = "test_pass_secure_123"
    src_db = "alos_src_test"
    dst_db = "alos_dst_test"
    temp_dir = Path(tempfile.mkdtemp(prefix="alos_restore_proof_"))
    compose_path = temp_dir / "compose.json"
    compose_path.write_text(json.dumps({"name": container_name, "services": {"postgres": {
        "image": os.environ.get("ALOS_RESTORE_POSTGRES_IMAGE", "pgvector/pgvector:pg16@sha256:7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a"),
        "container_name": container_name,
        "environment": {"POSTGRES_USER": pg_user, "POSTGRES_PASSWORD": pg_pass, "POSTGRES_DB": src_db},
    }}}), encoding="utf-8")
    bash = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")
    if not bash or not Path(bash).is_file():
        raise RuntimeError("Bash is required to verify the actual backup and restore scripts")
    helper_env = {**os.environ, "COMPOSE_PROJECT_NAME": container_name,
                  "BACKUP_DIR": (temp_dir / "backups").as_posix(), "CONFIRM_DATABASE_RESTORE": "YES",
                  "MSYS2_ARG_CONV_EXCL": "postgres:;/tmp/"}
    compose = ["docker", "compose", "-p", container_name, "-f", str(compose_path)]

    try:
        # 1. Start disposable postgres container
        print(f"\n[1/6] Menjalankan disposable PostgreSQL container [{container_name}]...")
        run_cmd([*compose, "up", "--detach"])

        # 2. Wait for postgres to be ready and accept queries
        print("  -> Menunggu container postgres siap dan menerima query...")
        ready = False
        for _ in range(40):
            res = run_cmd([
                "docker", "exec", container_name,
                "psql", "-U", pg_user, "-d", src_db, "-c", "SELECT 1;"
            ], check=False)
            if res.returncode == 0:
                ready = True
                break
            time.sleep(1)

        if not ready:
            raise RuntimeError("Postgres container gagal siap dalam waktu 40 detik.")
        print("  -> PostgreSQL siap menerima query.")

        # 3. Seed source database with marker and vector extension
        print(f"\n[2/6] Menyemai data uji & extension pada database sumber [{src_db}]...")
        seed_sql = """
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE alos_restore_proof_marker (
            id SERIAL PRIMARY KEY,
            marker_key VARCHAR(64) NOT NULL UNIQUE,
            proof_secret VARCHAR(128) NOT NULL,
            vector_data vector(3),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        INSERT INTO alos_restore_proof_marker (marker_key, proof_secret, vector_data)
        VALUES ('ALOS_RESTORE_PROOF_KEY_2026', 'INTEGRITY_VERIFIED_RESTORE_VALID', '[0.1, 0.2, 0.3]');
        INSERT INTO alos_restore_proof_marker (marker_key, proof_secret, vector_data)
        SELECT 'synthetic_' || i, 'SYNTHETIC_ONLY', ('[' || i || ',' || i || ',' || i || ']')::vector
        FROM generate_series(1, 30) AS i;
        CREATE INDEX proof_hnsw ON alos_restore_proof_marker USING hnsw (vector_data vector_l2_ops);
        CREATE INDEX proof_ivfflat ON alos_restore_proof_marker USING ivfflat (vector_data vector_l2_ops) WITH (lists = 1);
        """
        run_cmd([
            "docker", "exec", "-i", container_name,
            "psql", "-U", pg_user, "-d", src_db, "-c", seed_sql
        ])
        print("  -> Data marker dan vector extension berhasil dibuat di database sumber.")

        # 4. Perform pg_dump and compute SHA-256 sidecar
        print(f"\n[3/6] Membuat pg_dump custom format dari [{src_db}]...")
        run_cmd([bash, (REPO_ROOT / "database/backup/backup.sh").as_posix(), compose_path.as_posix()], env=helper_env)
        dumps = list((temp_dir / "backups").glob("*.dump"))
        assert len(dumps) == 1, "Backup script must produce exactly one dump"
        dump_on_host = dumps[0]
        checksum_on_host = Path(str(dump_on_host) + ".sha256")
        assert dump_on_host.is_file() and dump_on_host.stat().st_size > 0, "Dump file kosong atau tidak ada"

        content = dump_on_host.read_bytes()
        calculated_sha = hashlib.sha256(content).hexdigest()
        assert checksum_on_host.read_text().split()[0] == calculated_sha, "Actual backup sidecar checksum mismatch"
        print(f"  -> Dump berhasil disalin ke host ({len(content)} bytes, SHA-256: {calculated_sha[:16]}...).")

        # 5. Create clean destination database and restore
        print(f"\n[4/6] Menyiapkan database tujuan bersih [{dst_db}] dan menjalankan pg_restore...")
        restore_command = [bash, (REPO_ROOT / "database/restore/restore.sh").as_posix(), dump_on_host.as_posix(),
                           "--compose-file", compose_path.as_posix(), "--target-db", dst_db]
        restore_res = run_cmd(restore_command, check=False, env=helper_env)

        if restore_res.returncode != 0:
            raise RuntimeError(f"pg_restore gagal: {restore_res.stderr}")
        print("  -> pg_restore selesai tanpa error.")

        # 6. Verify restored database marker and integrity
        print(f"\n[5/6] Verifikasi data marker & skema pada database hasil restore [{dst_db}]...")
        verify_query = """
        SELECT marker_key, proof_secret, vector_data::text
        FROM alos_restore_proof_marker
        WHERE marker_key = 'ALOS_RESTORE_PROOF_KEY_2026';
        """
        verify_res = run_cmd([
            "docker", "exec", container_name,
            "psql", "-U", pg_user, "-d", dst_db, "-t", "-A", "-F|", "-c", verify_query
        ])

        output_line = verify_res.stdout.strip()
        parts = output_line.split("|")
        assert len(parts) >= 3, f"Output query verifikasi tidak lengkap: '{output_line}'"
        assert parts[0] == "ALOS_RESTORE_PROOF_KEY_2026", f"Marker key salah: {parts[0]}"
        assert parts[1] == "INTEGRITY_VERIFIED_RESTORE_VALID", f"Proof secret salah: {parts[1]}"
        assert parts[2] == "[0.1,0.2,0.3]", f"Vector data salah: {parts[2]}"

        print("  -> Marker key terverifikasi: PASS")
        print("  -> Proof secret terverifikasi: PASS")
        print("  -> Pgvector datatype & embeddings terverifikasi: PASS")
        nearest = run_cmd(["docker", "exec", container_name, "psql", "-U", pg_user, "-d", dst_db, "-Atc",
                           "SELECT marker_key FROM alos_restore_proof_marker ORDER BY vector_data <-> '[0.1,0.2,0.3]' LIMIT 1;"])
        assert nearest.stdout.strip() == "ALOS_RESTORE_PROOF_KEY_2026"
        indexes = run_cmd(["docker", "exec", container_name, "psql", "-U", pg_user, "-d", dst_db, "-Atc",
                           "SELECT count(*) FROM pg_indexes WHERE indexname IN ('proof_hnsw', 'proof_ivfflat');"])
        assert indexes.stdout.strip() == "2"
        print("  -> HNSW/IVFFlat indexes and nearest-vector query after restore: PASS")

        # 7. Check checksum verification failure behavior
        print("\n[6/6] Verifikasi fail-closed jika checksum tidak valid...")
        production_attempt = run_cmd([*restore_command[:-1], src_db], check=False, env=helper_env)
        assert production_attempt.returncode == 3 and "SAFETY GUARD AKTIF" in production_attempt.stderr
        invalid_target = run_cmd([*restore_command[:-1], 'bad; DROP DATABASE fixture;'], check=False, env=helper_env)
        assert invalid_target.returncode == 2 and "identifier ASCII aman" in invalid_target.stderr
        checksum_on_host.write_text("0" * 64 + "  " + dump_on_host.name + "\n", encoding="ascii")
        tamper_attempt = run_cmd(restore_command, check=False, env=helper_env)
        assert tamper_attempt.returncode == 1 and "Checksum backup tidak cocok" in tamper_attempt.stderr
        unsigned_env = {**helper_env, "CONFIRM_DATABASE_RESTORE": ""}
        unsigned_attempt = run_cmd(restore_command, check=False, env=unsigned_env)
        assert unsigned_attempt.returncode == 2 and "konfirmasi eksplisit" in unsigned_attempt.stderr
        print("  -> Actual restore script: tampered checksum, missing confirmation, production overwrite and unsafe target blocked.")

        print("\n==================================================")
        print("HASIL: AUTOMATED RESTORE PROOF SUKSES (PASS)!")
        print("Keterangan: Database dump terbukti valid, restorable,")
        print("dan menjamin integritas skema relasional + pgvector.")
        print("==================================================")

    finally:
        # Cleanup container and temporary directory
        run_cmd([*compose, "down", "--volumes"], check=False)
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        test_restore_proof()
    except Exception as exc:
        print(f"\nERROR RESTORE PROOF: {exc}", file=sys.stderr)
        sys.exit(1)
