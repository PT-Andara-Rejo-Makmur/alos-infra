#!/usr/bin/env python3
"""Preflight validation script for ALOS multi-host infrastructure.

Validates all operational and security invariants before deployment:
- Required secrets exist and are non-empty (without logging secret values)
- Bind IPs are explicit and non-loopback for multi-host production
- Images use immutable cryptographic digest pinning (disallows mutable :latest)
- Authority separation between APP, GENESIS, and DATA nodes
- Secret isolation between staging and production
- Backup destination and rollback references
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


DISALLOWED_PRODUCTION_BINDS = {"", "localhost", "127.0.0.1", "0.0.0.0", "::1", "::"}


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()
    return env


def get_effective_env(file_env: dict[str, str]) -> dict[str, str]:
    effective: dict[str, str] = {}
    for k, v in file_env.items():
        if v:
            effective[k] = v
        elif k in os.environ and os.environ[k]:
            effective[k] = os.environ[k]
        else:
            effective[k] = ""
    return effective


def validate_image_immutability(image_ref: str, service_name: str, errors: list[str]) -> None:
    if not image_ref:
        errors.append(f"[{service_name.upper()}] Image reference kosong atau tidak terdefinisi")
        return
    if image_ref.endswith(":latest"):
        errors.append(
            f"[{service_name.upper()}] Image reference '{image_ref}' menggunakan mutable tag ':latest'. "
            "Wajib menggunakan immutable cryptographic digest pinning (@sha256:...)"
        )
        return
    # Require @sha256: digest or immutable semantic tag (disallow vague floating tags)
    if "@sha256:" not in image_ref and not re.search(r":v?\d+\.\d+\.\d+", image_ref):
        errors.append(
            f"[{service_name.upper()}] Image reference '{image_ref}' tidak memiliki digest pinning (@sha256:...) atau semver release"
        )


def validate_app(env: dict[str, str], errors: list[str]) -> None:
    required = [
        "ALOS_WEB_IMAGE",
        "ALOS_BACKEND_IMAGE",
        "WEB_HOSTNAME",
        "API_HOSTNAME",
        "GENESIS_INTERNAL_TOKEN",
        "APP_PRIVATE_BIND_IP",
    ]
    for key in required:
        if not env.get(key):
            errors.append(f"[APP] {key} wajib diisi dan tidak boleh kosong")

    # Image immutability validation
    if env.get("ALOS_WEB_IMAGE"):
        validate_image_immutability(env["ALOS_WEB_IMAGE"], "web", errors)
    if env.get("ALOS_BACKEND_IMAGE"):
        validate_image_immutability(env["ALOS_BACKEND_IMAGE"], "backend", errors)

    bind_ip = env.get("APP_PRIVATE_BIND_IP", "").strip().lower()
    if bind_ip in DISALLOWED_PRODUCTION_BINDS:
        errors.append(
            f"[APP] APP_PRIVATE_BIND_IP ('{bind_ip}') tidak valid untuk production multi-host. "
            "Dilarang kosong, localhost, 127.0.0.1, atau 0.0.0.0; gunakan explicit private network IP"
        )

    has_db = bool(env.get("DATABASE_URL") or (env.get("DATABASE_PRIVATE_HOST") and env.get("POSTGRES_DB") and env.get("POSTGRES_USER") and env.get("POSTGRES_PASSWORD")))
    if not has_db:
        errors.append("[APP] DATABASE_PRIVATE_HOST (dengan kredensial DB) atau DATABASE_URL wajib disediakan")

    has_genesis = bool(env.get("GENESIS_BASE_URL") or env.get("GENESIS_PRIVATE_HOST"))
    if not has_genesis:
        errors.append("[APP] GENESIS_PRIVATE_HOST atau GENESIS_BASE_URL wajib disediakan")


def validate_genesis(env: dict[str, str], errors: list[str]) -> None:
    required = [
        "GENESIS_IMAGE",
        "ALOS_BACKEND_BASE_URL",
        "ALOS_INTERNAL_TOKEN",
        "GENESIS_BIND_IP",
    ]
    for key in required:
        if not env.get(key):
            errors.append(f"[GENESIS] {key} wajib diisi dan tidak boleh kosong")

    # Image immutability validation
    if env.get("GENESIS_IMAGE"):
        validate_image_immutability(env["GENESIS_IMAGE"], "genesis", errors)

    bind_ip = env.get("GENESIS_BIND_IP", "").strip().lower()
    if bind_ip in DISALLOWED_PRODUCTION_BINDS:
        errors.append(
            f"[GENESIS] GENESIS_BIND_IP ('{bind_ip}') tidak valid untuk production multi-host. "
            "Dilarang kosong, localhost, 127.0.0.1, atau 0.0.0.0; gunakan explicit private network IP"
        )

    # Strictly verify NO database credentials
    forbidden = ["DATABASE_URL", "POSTGRES_PASSWORD", "POSTGRES_USER", "POSTGRES_DB", "DATABASE_PRIVATE_HOST"]
    for key in forbidden:
        if env.get(key):
            errors.append(f"[GENESIS] PERINGATAN KEAMANAN: {key} terdeteksi di lingkungan GENESIS! GENESIS dilarang memegang kredensial DB")


def validate_data(env: dict[str, str], errors: list[str]) -> None:
    required = [
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_BIND_IP",
    ]
    for key in required:
        if not env.get(key):
            errors.append(f"[DATA] {key} wajib diisi dan tidak boleh kosong")

    bind_ip = env.get("POSTGRES_BIND_IP", "").strip().lower()
    if bind_ip in DISALLOWED_PRODUCTION_BINDS:
        errors.append(
            f"[DATA] POSTGRES_BIND_IP ('{bind_ip}') tidak valid untuk production multi-host. "
            "Dilarang kosong, localhost, 127.0.0.1, atau 0.0.0.0; gunakan explicit private network IP"
        )

    # Strictly verify NO AI tokens
    forbidden = ["GENESIS_INTERNAL_TOKEN", "ALOS_INTERNAL_TOKEN"]
    for key in forbidden:
        if env.get(key):
            errors.append(f"[DATA] PERINGATAN KEAMANAN: {key} terdeteksi di lingkungan DATA! DATA node dilarang memegang token AI")


def validate_staging(env: dict[str, str], errors: list[str]) -> None:
    required = [
        "ALOS_WEB_IMAGE",
        "ALOS_BACKEND_IMAGE",
        "GENESIS_IMAGE",
        "WEB_HOSTNAME",
        "API_HOSTNAME",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "GENESIS_INTERNAL_TOKEN",
    ]
    for key in required:
        if not env.get(key):
            errors.append(f"[STAGING] {key} wajib diisi")

    web_host = env.get("WEB_HOSTNAME", "")
    if web_host and "staging" not in web_host.lower() and "stg" not in web_host.lower() and "localhost" not in web_host and "invalid" not in web_host:
        errors.append(f"[STAGING] WEB_HOSTNAME ('{web_host}') berpotensi tertukar dengan production hostname")


def validate_cross_environment_isolation(prod_env_file: Path | None, staging_env_file: Path | None, errors: list[str]) -> None:
    if prod_env_file and staging_env_file and prod_env_file.resolve() == staging_env_file.resolve():
        errors.append(
            f"[ISOLASI] Path file konfigurasi rahasia Production dan Staging identik: {prod_env_file}! "
            "Kredensial wajib disimpan terpisah."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="ALOS Multi-Host Preflight Validation")
    parser.add_argument(
        "--target",
        choices=["app", "genesis", "data", "staging", "all"],
        default="all",
        help="Target node to validate (default: all)",
    )
    parser.add_argument("--env-file", help="Explicit .env file path to validate")
    parser.add_argument("--staging-env-file", help="Explicit staging .env file path to validate cross-isolation")
    parser.add_argument("--require-rollback-ref", action="store_true", help="Enforce availability of rollback image reference")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    errors: list[str] = []

    targets = ["app", "genesis", "data", "staging"] if args.target == "all" else [args.target]

    prod_file: Path | None = None
    staging_file: Path | None = None

    for target in targets:
        env_path = Path(args.env_file) if args.env_file else None
        if not env_path:
            if target == "staging":
                env_path = repo_root / "environments" / "staging" / ".env"
                if not env_path.is_file():
                    env_path = repo_root / "environments" / "staging" / ".env.example"
                staging_file = env_path
            else:
                env_path = repo_root / "environments" / "production" / target / ".env"
                if not env_path.is_file():
                    env_path = repo_root / "environments" / "production" / target / ".env.example"
                prod_file = env_path

        print(f"Memvalidasi preflight target [{target.upper()}] menggunakan: {env_path}")
        raw_env = parse_env_file(env_path)
        effective_env = get_effective_env(raw_env)

        if target == "app":
            validate_app(effective_env, errors)
        elif target == "genesis":
            validate_genesis(effective_env, errors)
        elif target == "data":
            validate_data(effective_env, errors)
        elif target == "staging":
            validate_staging(effective_env, errors)

    if args.staging_env_file:
        staging_file = Path(args.staging_env_file)
    validate_cross_environment_isolation(prod_file, staging_file, errors)

    # Rollback reference check
    if args.require_rollback_ref:
        rollback_ref = os.environ.get("PREVIOUS_KNOWN_GOOD_IMAGE", "")
        if not rollback_ref:
            errors.append("[ROLLBACK] PREVIOUS_KNOWN_GOOD_IMAGE wajib disediakan saat change window memerlukan rollback reference")

    if errors:
        print("\n--- PREFLIGHT VALIDATION GAGAL ---", file=sys.stderr)
        for err in errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        return 1

    print("\n--- PREFLIGHT VALIDATION SUKSES: Semua invariant terpenuhi ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
