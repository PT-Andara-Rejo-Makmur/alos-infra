"""Prove packaged document jobs and graceful shutdown using disposable PostgreSQL data.

Run with the Backend Python environment after building its image. Only the named
validation container/database are changed; an existing application stack is untouched.
"""

import argparse
import asyncio
import io
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import ZipFile

import asyncpg
import httpx
from alos.config import Settings
from alos.main import create_app
from sqlalchemy.engine import make_url


async def command(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    include_stderr: bool = False,
) -> str:
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        async with asyncio.timeout(120):
            output, error = await process.communicate()
    except TimeoutError:
        process.kill()
        await process.communicate()
        raise RuntimeError(
            f"{args[0]} did not finish within the validation timeout"
        ) from None
    if process.returncode:
        raise RuntimeError(f"{args[0]} failed: {error.decode(errors='replace')}")
    return (output + (error if include_stderr else b"")).decode().strip()


async def prove(
    image: str,
    *,
    database_host: str = "host.docker.internal",
    database_port: int | None = None,
    network: str | None = None,
) -> None:
    infra = (await asyncio.to_thread(Path(__file__).resolve)).parents[1]
    backend = infra.parent / "alos-backend"
    contracts = infra.parent / "alos-contracts"
    base = make_url(os.environ["ALOS_TEST_DATABASE_URL"])
    database_name = "alos_worker_validation_" + uuid4().hex[:12]
    container_name = "alos-worker-validation-" + uuid4().hex[:12]
    url = base.set(database=database_name)
    docker_url = url.set(host=database_host, port=database_port or url.port)
    admin_url = base.set(drivername="postgresql", database="postgres")
    admin = await asyncpg.connect(admin_url.render_as_string(hide_password=False))
    validation_root = (infra.parent / ".codex" / "validation").resolve()
    validation_root.mkdir(parents=True, exist_ok=True)
    app = None
    started = False
    container_requested = False
    try:
        await admin.execute(f'CREATE DATABASE "{database_name}"')
        await command(
            sys.executable,
            "-m",
            "alembic",
            "upgrade",
            "head",
            cwd=backend,
            env={
                **os.environ,
                "DATABASE_URL": url.render_as_string(hide_password=False),
            },
        )
        with TemporaryDirectory(
            prefix="worker-objects-", dir=validation_root
        ) as directory:
            objects = await asyncio.to_thread(Path(directory).resolve)
            assert objects.is_relative_to(validation_root)
            app = create_app(
                Settings(
                    _env_file=None,
                    APP_ENV="development",
                    DATABASE_URL=url.render_as_string(hide_password=False),
                    ALOS_CONTRACTS_PATH=contracts,
                    ENABLE_TEST_REGISTRATION=True,
                    DOCUMENT_OBJECT_ROOT=objects,
                    EMAIL_PROVIDER="test",
                )
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://worker-validation",
            ) as client:
                email = "document-worker@validation.test"
                password = "WorkerValidation!2026"
                registration = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": email,
                        "password": password,
                        "display_name": "Document Operator",
                        "tenant_id": "tenant_worker",
                        "organization_id": "org_worker",
                        "workspace_id": "workspace_worker",
                        "workspace_key": "document-operations",
                        "workspace_name": "Document Operations",
                        "workspace_type": "BUSINESS",
                        "role_refs": ["DIVISION_MEMBER"],
                        "permission_refs": [
                            "work.read",
                            "work.write",
                            "document.version",
                        ],
                        "scope_refs": ["scope.documents"],
                        "data_scope": "WORKSPACE",
                    },
                )
                assert registration.status_code == 201, registration.text
                login = await client.post(
                    "/api/v1/auth/login", json={"email": email, "password": password}
                )
                assert login.status_code == 200, login.text
                headers = {"Authorization": "Bearer " + login.json()["access_token"]}
                archive = io.BytesIO()
                with ZipFile(archive, "w") as document:
                    document.writestr(
                        "word/document.xml",
                        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
                        'wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'
                        "Bukti kesiapan fasilitas karyawan."
                        "</w:t></w:r></w:p></w:body></w:document>",
                    )
                uploads = []
                for filename, mime, payload in (
                    ("review.txt", "text/plain", b"Bukti pekerjaan perlu diperiksa."),
                    (
                        "readiness.docx",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        archive.getvalue(),
                    ),
                ):
                    document = await client.post(
                        "/api/v1/documents",
                        headers=headers,
                        json={
                            "title": filename,
                            "category": "OPERATIONS",
                            "data_classification": "INTERNAL",
                        },
                    )
                    assert document.status_code == 201, document.text
                    document_id = document.json()["document_id"]
                    uploaded = await client.post(
                        f"/api/v1/documents/{document_id}/uploads",
                        headers={**headers, "Content-Type": mime},
                        params={"filename": filename, "version": "1"},
                        content=payload,
                    )
                    assert uploaded.status_code == 202, uploaded.text
                    uploads.append(
                        (
                            document_id,
                            uploaded.json()["upload_id"],
                            uploaded.json()["content_hash"],
                        )
                    )
                container_requested = True
                await command(
                    "docker",
                    "create",
                    "--name",
                    container_name,
                    *(("--network", network) if network else ()),
                    "--mount",
                    f"type=bind,source={objects},target=/data/documents",
                    "--env",
                    "APP_ENV=test",
                    "--env",
                    "ALOS_CONTRACTS_PATH=/contracts",
                    "--env",
                    "DOCUMENT_OBJECT_ROOT=/data/documents",
                    "--env",
                    "DATABASE_URL=" + docker_url.render_as_string(hide_password=False),
                    "--entrypoint",
                    "python",
                    image,
                    "-m",
                    "alos.jobs.runner",
                )
                started = True
                await command("docker", "start", container_name)
                for _ in range(45):
                    states = [
                        await client.get(
                            f"/api/v1/documents/uploads/{upload_id}", headers=headers
                        )
                        for _, upload_id, _ in uploads
                    ]
                    if all(
                        response.json()["status"] == "SUCCEEDED" for response in states
                    ):
                        break
                    await asyncio.sleep(1)
                else:
                    raise AssertionError(
                        "Packaged worker did not complete both document jobs"
                    )
                for (document_id, _, digest), status in zip(
                    uploads, states, strict=True
                ):
                    assert status.json()["source_id"]
                    versions = await client.get(
                        f"/api/v1/documents/{document_id}/versions", headers=headers
                    )
                    assert versions.status_code == 200 and len(versions.json()) == 1
                    assert versions.json()[0]["content_hash"] == digest
                    assert versions.json()[0]["source_version"] == "1"
                    # Extraction does not grant approval or access to unreviewed content.
                    content = await client.get(
                        f"/api/v1/documents/{document_id}/content", headers=headers
                    )
                    assert content.status_code == 409
                await command("docker", "stop", "--time", "15", container_name)
                exit_code = await command(
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.ExitCode}}",
                    container_name,
                )
                assert exit_code == "0", "Worker did not stop gracefully after SIGTERM"
                await command("docker", "rm", container_name)
                started = False
                container_requested = False
                print(
                    "PASS: packaged TEXT/DOCX jobs, source/version hashes, "
                    "review boundary and SIGTERM shutdown"
                )
    except Exception:
        if container_requested:
            try:
                logs = await command(
                    "docker",
                    "logs",
                    "--tail",
                    "60",
                    container_name,
                    include_stderr=True,
                )
                print(logs)
            except RuntimeError:
                pass
        raise
    finally:
        try:
            if started or container_requested:
                try:
                    await command("docker", "rm", "--force", container_name)
                except RuntimeError as error:
                    if "No such container" not in str(error):
                        raise
        finally:
            try:
                if app is not None:
                    await app.state.database.dispose()
                await admin.execute(
                    f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'
                )
            finally:
                await admin.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="alos-backend:business-validation")
    parser.add_argument("--worker-database-host", default="host.docker.internal")
    parser.add_argument("--worker-database-port", type=int)
    parser.add_argument("--network")
    arguments = parser.parse_args()
    asyncio.run(
        prove(
            arguments.image,
            database_host=arguments.worker_database_host,
            database_port=arguments.worker_database_port,
            network=arguments.network,
        )
    )
