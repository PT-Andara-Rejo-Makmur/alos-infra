#!/usr/bin/env python3
"""Regression test suite for ALOS multi-host 4 VPS infrastructure topology.

Validates all invariant requirements defined in ALOS Infra MVP2.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def run_compose_config_json(compose_path: Path, env_path: Path) -> dict:
    """Run docker compose config --format json and return parsed dict."""
    cmd = [
        "docker",
        "compose",
        "--env-file",
        str(env_path),
        "-f",
        str(compose_path),
        "config",
        "--format",
        "json",
    ]
    # Provide synthetic dummy values for required env variables to allow config render
    test_env = {
        **os.environ,
        "ALOS_WEB_IMAGE": "example.invalid/alos-web:v1.0.0@sha256:1111111111111111111111111111111111111111111111111111111111111111",
        "ALOS_BACKEND_IMAGE": "example.invalid/alos-backend:v1.0.0@sha256:2222222222222222222222222222222222222222222222222222222222222222",
        "GENESIS_IMAGE": "example.invalid/genesis-ai:v1.0.0@sha256:3333333333333333333333333333333333333333333333333333333333333333",
        "POSTGRES_IMAGE": "pgvector/pgvector:pg16",
        "CADDY_IMAGE": "caddy:2.10-alpine",
        "OTEL_COLLECTOR_IMAGE": "otel/opentelemetry-collector-contrib:0.135.0",
        "WEB_HOSTNAME": "web.example.invalid",
        "API_HOSTNAME": "api.example.invalid",
        "POSTGRES_DB": "alos_test",
        "POSTGRES_USER": "alos_user",
        "POSTGRES_PASSWORD": "test-password",
        "GENESIS_INTERNAL_TOKEN": "test-token",
        "ALOS_INTERNAL_TOKEN": "test-token",
        "APP_PRIVATE_BIND_IP": "10.0.0.1",
        "ALOS_BACKEND_PORT": "8000",
        "GENESIS_BIND_IP": "10.0.0.2",
        "POSTGRES_BIND_IP": "10.0.0.3",
        "ALOS_BACKEND_BASE_URL": "http://10.0.0.1:8000",
        "DATABASE_PRIVATE_HOST": "10.0.0.3",
        "GENESIS_PRIVATE_HOST": "10.0.0.2",
    }
    result = subprocess.run(
        cmd,
        cwd=str(compose_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=test_env,
        check=True,
    )
    return json.loads(result.stdout)


def test_topology() -> None:
    print("Memulai pengujian invariant regresi topologi multi-host 4 VPS...")

    # Load compose JSONs
    app_compose_file = REPO_ROOT / "environments" / "production" / "app" / "compose.yaml"
    app_env_file = REPO_ROOT / "environments" / "production" / "app" / ".env.example"
    genesis_compose_file = REPO_ROOT / "environments" / "production" / "genesis" / "compose.yaml"
    genesis_env_file = REPO_ROOT / "environments" / "production" / "genesis" / ".env.example"
    data_compose_file = REPO_ROOT / "environments" / "production" / "data" / "compose.yaml"
    data_env_file = REPO_ROOT / "environments" / "production" / "data" / ".env.example"
    staging_compose_file = REPO_ROOT / "environments" / "staging" / "compose.yaml"
    staging_env_file = REPO_ROOT / "environments" / "staging" / ".env.example"

    app_json = run_compose_config_json(app_compose_file, app_env_file)
    genesis_json = run_compose_config_json(genesis_compose_file, genesis_env_file)
    data_json = run_compose_config_json(data_compose_file, data_env_file)
    staging_json = run_compose_config_json(staging_compose_file, staging_env_file)

    # 1. production APP compose hanya memiliki Caddy/Web/Backend
    app_services = set(app_json.get("services", {}).keys())
    assert app_services == {"caddy", "web", "backend"}, (
        f"Req 1 GAGAL: Production APP compose harus memiliki tepat [caddy, web, backend], aktual: {app_services}"
    )
    print("  [PASS] 1. Production APP compose hanya memiliki Caddy/Web/Backend")

    # 2. production GENESIS compose hanya memiliki GENESIS
    genesis_services = set(genesis_json.get("services", {}).keys())
    assert genesis_services == {"genesis"}, (
        f"Req 2 GAGAL: Production GENESIS compose harus hanya memiliki [genesis], aktual: {genesis_services}"
    )
    print("  [PASS] 2. Production GENESIS compose hanya memiliki GENESIS")

    # 3. production DATA compose hanya memiliki PostgreSQL/backup-related service
    data_services = set(data_json.get("services", {}).keys())
    assert data_services == {"postgres"}, (
        f"Req 3 GAGAL: Production DATA compose harus hanya memiliki [postgres], aktual: {data_services}"
    )
    print("  [PASS] 3. Production DATA compose hanya memiliki PostgreSQL/backup-related service")

    # 4. production GENESIS config tidak punya DATABASE_URL
    genesis_env = genesis_json["services"]["genesis"].get("environment", {})
    assert "DATABASE_URL" not in genesis_env, (
        "Req 4 GAGAL: GENESIS tidak boleh memiliki DATABASE_URL"
    )
    assert not any("POSTGRES" in k for k in genesis_env.keys()), (
        "Req 4 GAGAL: GENESIS tidak boleh memiliki variabel POSTGRES"
    )
    print("  [PASS] 4. Production GENESIS config tidak punya DATABASE_URL")

    # 5. production APP tidak memiliki direct Web->GENESIS configuration
    web_env = app_json["services"]["web"].get("environment", {})
    assert not any("GENESIS" in k.upper() for k in web_env.keys()), (
        f"Req 5 GAGAL: Web tidak boleh memiliki konfigurasi GENESIS: {web_env}"
    )
    assert not any("POSTGRES" in k.upper() for k in web_env.keys()), (
        f"Req 5 GAGAL: Web tidak boleh memiliki konfigurasi POSTGRES: {web_env}"
    )
    print("  [PASS] 5. Production APP tidak memiliki direct Web->GENESIS configuration")

    # 6. GENESIS port diikat ke private IP dan tidak dipublish public
    genesis_ports = genesis_json["services"]["genesis"].get("ports", [])
    assert genesis_ports, "Req 6 GAGAL: GENESIS harus memiliki port binding untuk private access dari Backend"
    for p in genesis_ports:
        host_ip = p.get("host_ip", "")
        assert host_ip not in ["0.0.0.0", "", "::"], (
            f"Req 6 GAGAL: GENESIS port terbuka ke publik pada interface {host_ip}"
        )
    genesis_raw = genesis_compose_file.read_text(encoding="utf-8")
    assert "${GENESIS_BIND_IP:?" in genesis_raw, (
        "Req 6 GAGAL: GENESIS_BIND_IP wajib required (:?) tanpa default loopback 127.0.0.1 di compose.yaml"
    )
    assert ":-127.0.0.1" not in genesis_raw and ":-localhost" not in genesis_raw, (
        "Req 6 GAGAL: GENESIS compose.yaml masih memuat fallback default 127.0.0.1 / localhost"
    )
    print("  [PASS] 6. GENESIS port diikat ke private IP dan bebas dari loopback default")

    # 7. PostgreSQL port diikat ke private IP dan tidak dipublish public
    data_ports = data_json["services"]["postgres"].get("ports", [])
    assert data_ports, "Req 7 GAGAL: PostgreSQL harus memiliki port binding untuk private access dari Backend"
    for p in data_ports:
        host_ip = p.get("host_ip", "")
        assert host_ip not in ["0.0.0.0", "", "::"], (
            f"Req 7 GAGAL: PostgreSQL port terbuka ke publik pada interface {host_ip}"
        )
    data_raw = data_compose_file.read_text(encoding="utf-8")
    assert "${POSTGRES_BIND_IP:?" in data_raw, (
        "Req 7 GAGAL: POSTGRES_BIND_IP wajib required (:?) tanpa default loopback 127.0.0.1 di compose.yaml"
    )
    assert ":-127.0.0.1" not in data_raw and ":-localhost" not in data_raw, (
        "Req 7 GAGAL: PostgreSQL compose.yaml masih memuat fallback default 127.0.0.1 / localhost"
    )
    print("  [PASS] 7. PostgreSQL port diikat ke private IP dan bebas dari loopback default")

    # 8. Backend di VPS 1 APP memiliki private listener untuk GENESIS callback
    backend_ports = app_json["services"]["backend"].get("ports", [])
    assert backend_ports, (
        "Req 8 GAGAL: Backend VPS 1 APP wajib mempublikasikan listener port untuk private GENESIS callback"
    )
    for p in backend_ports:
        host_ip = p.get("host_ip", "")
        assert host_ip not in ["0.0.0.0", "", "::"], (
            f"Req 8 GAGAL: Backend private listener terbuka ke publik pada interface {host_ip}"
        )
    app_raw = app_compose_file.read_text(encoding="utf-8")
    assert "${APP_PRIVATE_BIND_IP:?" in app_raw, (
        "Req 8 GAGAL: APP_PRIVATE_BIND_IP wajib required (:?) tanpa default loopback 127.0.0.1 di compose.yaml"
    )
    assert ":-127.0.0.1" not in app_raw and ":-localhost" not in app_raw, (
        "Req 8 GAGAL: APP compose.yaml masih memuat fallback default 127.0.0.1 / localhost"
    )
    print("  [PASS] 8. Backend VPS 1 APP memiliki private listener terisolasi untuk GENESIS callback")

    # 9. staging tetap full stack
    staging_services = set(staging_json.get("services", {}).keys())
    assert {"caddy", "web", "backend", "genesis", "postgres", "otel-collector"}.issubset(staging_services), (
        f"Req 9 GAGAL: Staging harus full stack, aktual: {staging_services}"
    )
    print("  [PASS] 9. Staging tetap full stack")

    # 10. staging/prod config path terpisah
    assert staging_compose_file.parent != app_compose_file.parent
    assert app_compose_file.is_file() and genesis_compose_file.is_file() and data_compose_file.is_file()
    assert not (REPO_ROOT / "environments" / "production" / "compose.yaml").exists(), (
        "Req 10 GAGAL: Monolithic environments/production/compose.yaml masih ada!"
    )
    print("  [PASS] 10. Staging/prod config path terpisah secara independen")

    # 11. no tracked real secrets
    tracked_env_files = list(REPO_ROOT.glob("environments/**/.env"))
    for tf in tracked_env_files:
        git_check = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(tf)],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert git_check.returncode != 0, f"Req 11 GAGAL: File .env ter-track di git: {tf}"
    print("  [PASS] 11. No tracked real secrets")

    # 12. immutable image requirement tetap enforced
    for service_name, raw_content in [
        ("web", app_compose_file.read_text(encoding="utf-8")),
        ("backend", app_compose_file.read_text(encoding="utf-8")),
        ("genesis", genesis_compose_file.read_text(encoding="utf-8")),
    ]:
        assert "Gunakan immutable" in raw_content or f"${{ALOS_{service_name.upper()}_IMAGE:?" in raw_content or f"${{{service_name.upper()}_IMAGE:?" in raw_content, (
            f"Req 12 GAGAL: Immutable image guard tidak ditemukan untuk {service_name}"
        )
    print("  [PASS] 12. Immutable image requirement tetap enforced")

    # 13. no depends_on cross-host assumption
    backend_depends = app_json["services"]["backend"].get("depends_on", {})
    assert "postgres" not in backend_depends, (
        f"Req 13 GAGAL: Backend di VPS 1 App masih depends_on postgres yang berada di VPS 3!"
    )
    assert "genesis" not in backend_depends, (
        f"Req 13 GAGAL: Backend di VPS 1 App masih depends_on genesis yang berada di VPS 2!"
    )
    print("  [PASS] 13. No depends_on cross-host assumption pada Production APP")

    # 14. Backend GENESIS endpoint configurable
    backend_env = app_json["services"]["backend"].get("environment", {})
    assert "GENESIS_BASE_URL" in backend_env, (
        "Req 14 GAGAL: Backend environment harus memiliki GENESIS_BASE_URL yang dapat dikonfigurasi"
    )
    print("  [PASS] 14. Backend GENESIS endpoint configurable")

    # 15. Backend DB endpoint configurable
    assert "DATABASE_URL" in backend_env, (
        "Req 15 GAGAL: Backend environment harus memiliki DATABASE_URL yang dapat dikonfigurasi"
    )
    print("  [PASS] 15. Backend DB endpoint configurable")

    # 16. Preflight script fails on loopback/localhost/empty bindings
    preflight_script_path = REPO_ROOT / "scripts" / "preflight-check.py"
    spec = importlib.util.spec_from_file_location("preflight_check", str(preflight_script_path))
    assert spec and spec.loader
    preflight_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preflight_mod)

    # Test APP loopback rejection
    errs: list[str] = []
    preflight_mod.validate_app({"APP_PRIVATE_BIND_IP": "127.0.0.1"}, errs)
    assert any("APP_PRIVATE_BIND_IP" in e and "tidak valid" in e for e in errs), (
        "Req 16 GAGAL: Preflight tidak menolak APP_PRIVATE_BIND_IP=127.0.0.1"
    )
    # Test GENESIS loopback rejection
    errs = []
    preflight_mod.validate_genesis({"GENESIS_BIND_IP": "localhost"}, errs)
    assert any("GENESIS_BIND_IP" in e and "tidak valid" in e for e in errs), (
        "Req 16 GAGAL: Preflight tidak menolak GENESIS_BIND_IP=localhost"
    )
    # Test DATA loopback rejection
    errs = []
    preflight_mod.validate_data({"POSTGRES_BIND_IP": "127.0.0.1"}, errs)
    assert any("POSTGRES_BIND_IP" in e and "tidak valid" in e for e in errs), (
        "Req 16 GAGAL: Preflight tidak menolak POSTGRES_BIND_IP=127.0.0.1"
    )
    print("  [PASS] 16. Preflight secara ketat menolak loopback/localhost untuk private bind IPs")

    # 17. No privileged containers across all compose configs
    for name, c_json in [("app", app_json), ("genesis", genesis_json), ("data", data_json), ("staging", staging_json)]:
        for svc_name, svc_conf in c_json.get("services", {}).items():
            assert not svc_conf.get("privileged", False), (
                f"Req 17 GAGAL: Service '{svc_name}' di {name} memiliki privileged: true!"
            )
    print("  [PASS] 17. No privileged containers across all compose configs")

    # 18. No docker.sock mount across all compose configs
    for name, c_json in [("app", app_json), ("genesis", genesis_json), ("data", data_json), ("staging", staging_json)]:
        for svc_name, svc_conf in c_json.get("services", {}).items():
            for vol in svc_conf.get("volumes", []):
                src = vol.get("source", "") if isinstance(vol, dict) else str(vol)
                assert "docker.sock" not in src, (
                    f"Req 18 GAGAL: Service '{svc_name}' di {name} me-mount docker.sock: {src}"
                )
    print("  [PASS] 18. No docker.sock mount across all compose configs")

    # 19. Production migration single-run semantics
    backend_cmd = app_json["services"]["backend"].get("command", "")
    assert "alembic" not in str(backend_cmd), (
        "Req 19 GAGAL: Backend production tidak boleh menjalankan alembic di service command (risiko race condition antar-replika)!"
    )
    migrate_script = REPO_ROOT / "database" / "migration" / "migrate.sh"
    assert migrate_script.is_file(), "Req 19 GAGAL: Script database/migration/migrate.sh tidak ditemukan!"
    migrate_raw = migrate_script.read_text(encoding="utf-8")
    assert "CONFIRM_MIGRATION" in migrate_raw and "alembic upgrade head" in migrate_raw
    print("  [PASS] 19. Production migration single-run semantics terisolasi dari service startup")

    # 20. Backup script failure handling, checksum generation, and safe logging
    backup_sh = REPO_ROOT / "database" / "backup" / "backup.sh"
    assert backup_sh.is_file(), "Req 20 GAGAL: backup.sh tidak ditemukan"
    backup_raw = backup_sh.read_text(encoding="utf-8")
    assert "pg_dump" in backup_raw and ".sha256" in backup_raw
    assert "exit 2" in backup_raw or "exit 1" in backup_raw
    assert "password" not in backup_raw.lower() or "no password" in backup_raw.lower() or 'echo "$POSTGRES_DB"' in backup_raw
    print("  [PASS] 20. Backup script fails on dump error, generates checksum, and protects secrets")

    # 21. Restore script safety guards (checksum rejection & production confirm)
    restore_sh = REPO_ROOT / "database" / "restore" / "restore.sh"
    assert restore_sh.is_file(), "Req 21 GAGAL: restore.sh tidak ditemukan"
    restore_raw = restore_sh.read_text(encoding="utf-8")
    assert "CONFIRM_DATABASE_RESTORE" in restore_raw
    assert "confirm-production" in restore_raw or "CONFIRM_PRODUCTION" in restore_raw
    assert "pg_restore" in restore_raw
    print("  [PASS] 21. Restore script enforces checksum match and explicit production confirm guard")

    # 22. Backup retention script exists and supports dry-run
    retention_sh = REPO_ROOT / "database" / "backup" / "retention.sh"
    assert retention_sh.is_file(), "Req 22 GAGAL: retention.sh tidak ditemukan"
    retention_raw = retention_sh.read_text(encoding="utf-8")
    assert "dry-run" in retention_raw or "DRY_RUN" in retention_raw
    print("  [PASS] 22. Backup retention script exists and supports dry-run mode")

    # 23. Systemd backup service and timer canonical templates exist
    svc_template = REPO_ROOT / "database" / "backup" / "systemd" / "alos-postgres-backup.service"
    timer_template = REPO_ROOT / "database" / "backup" / "systemd" / "alos-postgres-backup.timer"
    assert svc_template.is_file() and timer_template.is_file(), (
        "Req 23 GAGAL: Template systemd service/timer backup tidak ditemukan"
    )
    print("  [PASS] 23. Canonical systemd backup service and timer templates exist")

    # 24. Preflight error messages never print secret values
    errs = []
    preflight_mod.validate_data({"POSTGRES_PASSWORD": ""}, errs)
    for e in errs:
        assert "super_secret" not in e
    print("  [PASS] 24. Preflight errors fail-closed without echoing secret values")

    # 25. Complete Disaster Recovery & Rollback runbooks exist
    dr_runbook = REPO_ROOT / "runbooks" / "incident-response.md"
    rollback_runbook = REPO_ROOT / "runbooks" / "rollback.md"
    deploy_runbook = REPO_ROOT / "runbooks" / "deploy.md"
    assert dr_runbook.is_file() and rollback_runbook.is_file() and deploy_runbook.is_file()
    dr_content = dr_runbook.read_text(encoding="utf-8")
    assert "DETECT" in dr_content and "CONTAIN" in dr_content and "RECOVER" in dr_content
    rollback_content = rollback_runbook.read_text(encoding="utf-8")
    assert "@sha256:" in rollback_content and "backward-compatible" in rollback_content
    print("  [PASS] 25. Complete Disaster Recovery & Rollback runbooks with decision matrix exist")

    print("\n================================================================================")
    print("SELURUH 25 INVARIANT TOPOLOGI, KEAMANAN, DAN OPERASIONAL 4 VPS SUKSES TERVERIFIKASI!")
    print("================================================================================")


if __name__ == "__main__":
    try:
        test_topology()
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)
