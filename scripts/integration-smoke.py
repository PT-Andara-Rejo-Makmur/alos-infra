"""Deterministic public Backend-to-GENESIS-to-Backend integration smoke."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from urllib.parse import quote

BASE_URL = "http://127.0.0.1:8000"
WEB_BASE_URL = "http://127.0.0.1:3000"
CORRELATION_ID = "corr_integration_stack_001"


def request(
    path: str,
    *,
    payload: dict | None = None,
    token: str | None = None,
    correlation_id: str = CORRELATION_ID,
    method: str | None = None,
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
        method=method or ("POST" if payload is not None else "GET"),
    )
    with urllib.request.urlopen(operation, timeout=30) as response:
        if response.status == 204:
            return {}
        return json.load(response)


def web_request(
    opener: urllib.request.OpenerDirector,
    path: str,
    *,
    payload: dict | None = None,
    method: str | None = None,
) -> tuple[int, object]:
    headers = {"X-Correlation-ID": CORRELATION_ID}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    operation = urllib.request.Request(
        f"{WEB_BASE_URL}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers,
        method=method or ("POST" if payload is not None else "GET"),
    )
    with opener.open(operation, timeout=30) as response:
        content_type = response.headers.get("content-type", "")
        body: object = json.load(response) if "application/json" in content_type else response.read()
        return response.status, body


def expect_denied(
    path: str,
    payload: dict | None,
    token: str,
    *,
    method: str | None = None,
    expected_statuses: set[int] | None = None,
) -> None:
    try:
        request(path, payload=payload, token=token, method=method)
    except urllib.error.HTTPError as exc:
        if exc.code not in (expected_statuses or {403, 422}):
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
        "workspace_key": "it",
        "workspace_name": "Integration IT Workspace",
        "workspace_type": "IT_OPERATIONS",
        "division_code": "IT",
        "role_refs": ["IT_ADMIN"],
        "permission_refs": [
            "tools.diagnostic.execute",
            "research.request",
            "identity.accounts.manage",
            "identity.memberships.read",
            "identity.memberships.manage",
        ],
        "scope_refs": ["scope.diagnostic", "research.technology"],
        "data_scope": "COMPANY",
    }
    request("/api/v1/auth/register", payload=registration)

    beta_registration = {
        **registration,
        "email": "integration-beta-owner@alos.test",
        "display_name": "Integration Beta Owner",
        "workspace_id": "workspace_integration_002",
        "workspace_key": "it-beta",
        "workspace_name": "Integration IT Workspace Beta",
        "role_refs": ["WORKSPACE_MEMBER"],
        "permission_refs": [],
    }
    request("/api/v1/auth/register", payload=beta_registration)

    foreign_registration = {
        **registration,
        "email": "integration-foreign@alos.test",
        "display_name": "Foreign Organization Actor",
        "tenant_id": "tenant_integration_foreign",
        "organization_id": "org_integration_foreign",
        "workspace_id": "workspace_integration_foreign",
        "workspace_key": "foreign",
        "workspace_name": "Foreign Organization Workspace",
        "role_refs": ["WORKSPACE_MEMBER"],
        "permission_refs": [],
    }
    foreign_actor = request("/api/v1/auth/register", payload=foreign_registration)

    browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    status, web_login = web_request(
        browser,
        "/api/session/login",
        payload={"email": registration["email"], "password": registration["password"]},
    )
    assert status == 200
    assert isinstance(web_login, dict) and web_login["authenticated"] is True
    status, session = web_request(browser, "/api/session")
    assert status == 200
    assert isinstance(session, dict)
    assert session["principal"]["actor"]["tenant_id"] == registration["tenant_id"]
    status, workspaces = web_request(browser, "/api/backend/api/v1/workspaces")
    assert status == 200
    assert isinstance(workspaces, list) and len(workspaces) == 1
    assert workspaces[0]["workspace"]["workspace_id"] == registration["workspace_id"]
    status, selected = web_request(
        browser,
        "/api/backend/api/v1/auth/active-workspace",
        payload={"workspace_id": registration["workspace_id"]},
        method="PUT",
    )
    assert status == 200
    assert isinstance(selected, dict)
    assert selected["workspace"]["workspace_id"] == registration["workspace_id"]
    status, protected_page = web_request(browser, "/workspace/it")
    assert status == 200 and isinstance(protected_page, bytes)
    try:
        web_request(
            browser,
            "/api/backend/api/v1/auth/active-workspace",
            payload={"workspace_id": "workspace_unauthorized_001"},
            method="PUT",
        )
    except urllib.error.HTTPError as exc:
        assert exc.code == 403
    else:
        raise AssertionError("Unauthorized workspace selection was not denied")

    login = request(
        "/api/v1/auth/login",
        payload={"email": registration["email"], "password": registration["password"]},
    )
    token = login["access_token"]
    multi_account = request(
        "/api/v1/identity/accounts",
        payload={
            "email": "integration-multi@alos.test",
            "password": "integration-password",
            "display_name": "Multi Workspace Actor",
            "workspace_id": registration["workspace_id"],
            "role_refs": ["WORKSPACE_MEMBER"],
            "permission_refs": ["tools.diagnostic.execute"],
            "scope_refs": ["scope.diagnostic"],
            "data_scope": "WORKSPACE",
        },
        token=token,
    )
    multi_actor_id = multi_account["actor"]["actor_id"]
    request(
        f"/api/v1/identity/actors/{multi_actor_id}/memberships",
        payload={
            "workspace_id": beta_registration["workspace_id"],
            "role_refs": ["WORKSPACE_LEAD"],
            "permission_refs": ["tools.diagnostic.execute"],
            "scope_refs": ["scope.diagnostic"],
            "data_scope": "WORKSPACE",
        },
        token=token,
    )

    multi_login = request(
        "/api/v1/auth/login",
        payload={"email": "integration-multi@alos.test", "password": "integration-password"},
        correlation_id="corr_multi_workspace_login",
    )
    multi_token = multi_login["access_token"]
    assert multi_login["principal"]["actor"]["actor_id"] == multi_actor_id
    assert multi_login["principal"]["active_workspace"] is None
    expect_denied(
        "/api/v1/genesis/context-options",
        None,
        multi_token,
        expected_statuses={403},
    )
    selected_beta = request(
        "/api/v1/auth/active-workspace",
        payload={"workspace_id": beta_registration["workspace_id"]},
        token=multi_token,
        method="PUT",
        correlation_id="corr_multi_workspace_select",
    )
    assert selected_beta["actor_id"] == multi_actor_id
    assert selected_beta["workspace"]["workspace_id"] == beta_registration["workspace_id"]
    assert selected_beta["membership"]["role_refs"] == ["WORKSPACE_LEAD"]
    multi_whoami = request("/api/v1/auth/whoami", token=multi_token)
    assert multi_whoami["actor"]["actor_id"] == multi_actor_id
    assert multi_whoami["active_workspace"]["workspace"]["workspace_id"] == beta_registration["workspace_id"]
    assert multi_whoami["active_workspace"]["role_refs"] == ["WORKSPACE_LEAD"]
    protected_context = request("/api/v1/genesis/context-options", token=multi_token)
    assert protected_context["actor_id"] == multi_actor_id
    assert protected_context["workspace_id"] == beta_registration["workspace_id"]

    expect_denied(
        "/api/v1/auth/active-workspace",
        {"workspace_id": foreign_registration["workspace_id"]},
        multi_token,
        method="PUT",
        expected_statuses={403},
    )
    expect_denied(
        "/api/v1/identity/accounts",
        {
            "email": "cross-org@alos.test",
            "password": "integration-password",
            "display_name": "Cross Organization Attempt",
            "workspace_id": foreign_registration["workspace_id"],
            "role_refs": ["WORKSPACE_MEMBER"],
        },
        token,
        expected_statuses={403},
    )
    expect_denied(
        "/api/v1/identity/accounts",
        {
            "email": "cross-tenant@alos.test",
            "password": "integration-password",
            "display_name": "Cross Tenant Attempt",
            "workspace_id": registration["workspace_id"],
            "role_refs": ["WORKSPACE_MEMBER"],
            "tenant_id": foreign_registration["tenant_id"],
        },
        token,
        expected_statuses={422},
    )
    expect_denied(
        f"/api/v1/identity/actors/{foreign_actor['actor']['actor_id']}/memberships",
        {
            "workspace_id": registration["workspace_id"],
            "role_refs": ["WORKSPACE_MEMBER"],
        },
        token,
        expected_statuses={403, 404},
    )
    request(
        f"/api/v1/identity/actors/{multi_actor_id}/memberships/{beta_registration['workspace_id']}",
        token=token,
        method="DELETE",
    )
    revoked_whoami = request("/api/v1/auth/whoami", token=multi_token)
    assert revoked_whoami["actor"]["actor_id"] == multi_actor_id
    assert revoked_whoami["active_workspace"] is None
    expect_denied(
        "/api/v1/genesis/context-options",
        None,
        multi_token,
        expected_statuses={403},
    )
    expect_denied(
        "/api/v1/auth/active-workspace",
        {"workspace_id": beta_registration["workspace_id"]},
        multi_token,
        method="PUT",
        expected_statuses={403},
    )

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
                if exc.code == 404:
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
                    "owner": login["principal"]["actor"]["actor_id"],
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
    print("Web-Backend-GENESIS deterministic integration passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        correlation_id = exc.headers.get("x-correlation-id", "missing")
        print(
            f"Integration HTTP failure: {exc.code} {exc.geturl()} "
            f"(correlation_id={correlation_id})\n{response_body}",
            file=sys.stderr,
        )
        raise
