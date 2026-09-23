"""Deterministic public Backend-to-GENESIS-to-Backend integration smoke."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

BASE_URL = "http://127.0.0.1:8000"
CORRELATION_ID = "corr_integration_stack_001"


def request(
    path: str,
    *,
    payload: dict | None = None,
    token: str | None = None,
    correlation_id: str = CORRELATION_ID,
) -> dict:
    headers = {"X-Correlation-ID": correlation_id}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    operation = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(operation, timeout=30) as response:
        return json.load(response)


def expect_denied(path: str, payload: dict, token: str) -> None:
    try:
        request(path, payload=payload, token=token)
    except urllib.error.HTTPError as exc:
        if exc.code not in {403, 422}:
            raise
    else:
        raise AssertionError("Authority expansion was not denied")


def main() -> int:
    registration = {
        "email": "integration@alos.test",
        "password": "integration-password",
        "display_name": "Integration Runner",
        "tenant_id": "tenant_integration_001",
        "organization_id": "org_integration_001",
        "workspace_id": "workspace_integration_001",
        "roles": ["integration_runner"],
        "permissions": ["tools.diagnostic.execute", "research.request"],
        "scopes": ["scope.diagnostic", "research.technology"],
        "data_scope": "COMPANY",
    }
    request("/api/v1/auth/register", payload=registration)
    login = request(
        "/api/v1/auth/login",
        payload={"email": registration["email"], "password": registration["password"]},
    )
    token = login["access_token"]
    bootstrap = request("/api/v1/integration/bootstrap", payload={}, token=token)
    run = {
        "agent_id": bootstrap["agent_id"],
        "agent_version": bootstrap["agent_version"],
        "capability_id": "capability.runtime.diagnostic",
        "input": {"message": "integration roundtrip"},
        "requested_tool_ids": ["diagnostic.echo"],
        "scope_refs": ["scope.diagnostic"],
        "execution_budget": {
            "max_tokens": 100,
            "max_steps": 3,
            "max_tool_calls": 1,
            "timeout_seconds": 10,
        },
        "execution_mode": "TEST",
    }
    result = request("/api/v1/agent-runs", payload=run, token=token)
    assert result["status"] == "COMPLETED"
    assert result["correlation_id"] == CORRELATION_ID
    assert result["tool_results"][0]["status"] == "SUCCESS"
    assert result["usage"]["input_tokens"] > 0

    cancellation_correlation = "corr_integration_cancel_001"
    cancellation_run = {
        **run,
        "input": {"message": "cancel safely", "wait_for_cancellation": True},
    }
    internal_token = os.environ["GENESIS_INTERNAL_TOKEN"]
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(
            request,
            "/api/v1/agent-runs",
            payload=cancellation_run,
            token=token,
            correlation_id=cancellation_correlation,
        )
        run_id = None
        for _ in range(30):
            try:
                current = request(
                    "/internal/v1/integration/agent-runs?correlation_id="
                    + quote(cancellation_correlation),
                    token=internal_token,
                    correlation_id=cancellation_correlation,
                )
                run_id = current["run_id"]
                break
            except urllib.error.HTTPError as exc:
                if exc.code >= 500:
                    time.sleep(0.1)
                    continue
                raise
        assert run_id is not None
        cancelled = request(
            f"/api/v1/agent-runs/{run_id}/cancellation",
            payload={"reason": "deterministic integration cancellation"},
            token=token,
            correlation_id=cancellation_correlation,
        )
        assert cancelled["status"] == "CANCEL_REQUESTED"
        cancelled_result = pending.result(timeout=30)
    assert cancelled_result["status"] == "CANCELLED"
    assert cancelled_result["correlation_id"] == cancellation_correlation

    factory = request(
        "/api/v1/genesis/factory/analyze",
        payload={
            "requirement": "Buat laporan ringkas status operasional untuk direview manajemen",
            "preferred_capability_type": "REPORT",
        },
        token=token,
    )
    assert factory["correlation_id"] == CORRELATION_ID

    research = request(
        "/api/v1/research/requests",
        payload={
            "question": "Evaluasi bukti teknologi internal yang sudah diotorisasi.",
            "source_mode": "INTERNAL",
            "domain": "TECHNOLOGY",
        },
        token=token,
    )
    assert research["correlation_id"] == CORRELATION_ID

    evidence = bootstrap["evidence_ref"]
    research_result = request(
        "/api/v1/integration/research",
        payload={
            "evidence_id": evidence["evidence_id"],
            "question": "Analisis bukti internal yang diotorisasi Backend.",
        },
        token=token,
    )
    assert research_result["correlation_id"] == CORRELATION_ID
    assert research_result["findings"][0]["evidence_refs"] == [evidence]
    assert research_result["recommendations"][0]["backlog_candidate"] is True

    review = request(
        "/api/v1/reviews",
        payload={
            "subject": {
                "review_id": "review.integration.001",
                "subject_id": bootstrap["agent_id"],
                "subject_version": bootstrap["agent_version"],
                "tenant_id": registration["tenant_id"],
                "organization_id": registration["organization_id"],
                "workspace_id": registration["workspace_id"],
                "correlation_id": CORRELATION_ID,
                "purpose": "Validate the governed Backend and GENESIS runtime boundary.",
                "materiality": "NON_MATERIAL",
                "business_context": {
                    "registry_digest": bootstrap["registry_digest"],
                    "subject_type": "agent",
                },
                "capability": {
                    "capability_id": "capability.runtime.diagnostic",
                    "version": "1.0.0",
                    "name": "Runtime Diagnostic",
                    "purpose": "Validate the governed Backend and GENESIS runtime boundary.",
                    "owner": login["principal"]["actor_id"],
                    "capability_type": "AGENT",
                    "output_state": "NEEDS_REVIEW",
                    "lifecycle_state": "DRAFT",
                    "scope_refs": ["scope.diagnostic"],
                    "tool_ids": ["diagnostic.echo"],
                    "permission_refs": ["tools.diagnostic.execute"],
                    "risk_level": "LOW",
                },
                "scope": ["scope.diagnostic"],
                "permissions": ["tools.diagnostic.execute"],
                "skills": [],
                "tools": [
                    {
                        "tool_id": "diagnostic.echo",
                        "purpose": "Backend-authorized tool: diagnostic.echo",
                        "backend_executor": True,
                    }
                ],
                "model_policy": {
                    "gateway_required": True,
                    "policy_ref": "policy.runtime-test",
                },
                "delegation_policy": {
                    "enabled": False,
                    "lineage_required": True,
                    "max_depth": 0,
                },
                "execution_budget": {"max_tokens": 100, "max_steps": 3},
                "evidence_refs": [evidence],
            },
            "evaluation_subject": {
                "subject_id": bootstrap["agent_id"],
                "subject_version": bootstrap["agent_version"],
                "tenant_id": registration["tenant_id"],
                "organization_id": registration["organization_id"],
                "workspace_id": registration["workspace_id"],
                "correlation_id": CORRELATION_ID,
                "observations": {},
            },
        },
        token=token,
    )
    assert review["identity"]["correlation_id"] == CORRELATION_ID
    assert "it_decision" not in review
    assert "director_decision" not in review

    expect_denied(
        "/api/v1/agent-runs",
        {**run, "requested_tool_ids": ["admin.unauthorized"]},
        token,
    )
    expect_denied(
        "/api/v1/agent-runs",
        {**run, "scope_refs": ["scope.admin"]},
        token,
    )
    print("Backend-GENESIS deterministic integration passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
