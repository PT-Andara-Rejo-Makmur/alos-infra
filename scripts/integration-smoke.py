"""Deterministic public Backend-to-GENESIS-to-Backend integration smoke."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import quote

BASE_URL = os.environ.get("ALOS_INTEGRATION_BACKEND_URL", "http://127.0.0.1:8000")
WEB_BASE_URL = os.environ.get("ALOS_INTEGRATION_WEB_URL", "http://127.0.0.1:3000")
CORRELATION_ID = "corr_integration_stack_001"
ROOT = Path(__file__).resolve().parents[1]
COMPOSE = (
    "docker", "compose", "--env-file", "environments/integration/.env.example",
    "-f", "environments/integration/compose.yaml",
)


def compose_output(*arguments: str) -> str:
    result = subprocess.run(
        [*COMPOSE, *arguments], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def postgres_sql(statement: str) -> str:
    return compose_output(
        "exec", "-T", "postgres", "psql", "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1",
        "-U", os.environ.get("POSTGRES_USER", "alos"),
        "-d", os.environ.get("POSTGRES_DB", "alos_integration"),
        "-c", statement,
    )


def activation_credential(email: str) -> str:
    credential = compose_output(
        "exec", "-T", "backend", "python", "/integration/integration_backend.py", email
    )
    assert len(credential) >= 20
    return credential


def expect_web_error(
    opener: urllib.request.OpenerDirector,
    path: str,
    status: int,
    *,
    payload: dict | None = None,
    code: str | None = None,
    credential: str | None = None,
) -> None:
    try:
        web_request(opener, path, payload=payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        assert exc.code == status
        if code is not None:
            assert json.loads(body)["code"] == code
        if credential is not None:
            assert credential not in body
    else:
        raise AssertionError(f"Expected Web HTTP {status} for {path}")


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


def shared_work_smoke() -> None:
    """Prove dedicated Shared Work authority and persistence in PostgreSQL."""
    base = {
        "password": "integration-password",
        "tenant_id": "tenant_shared_work",
        "organization_id": "org_shared_work",
        "workspace_id": "workspace_shared_work",
        "workspace_key": "shared-work",
        "workspace_name": "Shared Work Integration",
        "workspace_type": "BUSINESS",
        "division_code": "UNASSIGNED",
        "role_refs": ["DIVISION_MEMBER"],
        "scope_refs": [],
        "data_scope": "WORKSPACE",
    }

    def actor(email: str, permissions: list[str], **changes: object) -> tuple[str, str]:
        profile = {
            **base, "email": email, "display_name": email,
            "permission_refs": permissions, **changes,
        }
        registered = request("/api/v1/auth/register", payload=profile)
        logged_in = request(
            "/api/v1/auth/login",
            payload={"email": email, "password": base["password"]},
        )
        return logged_in["access_token"], registered["actor"]["actor_id"]

    owner_permissions = [
        "project.read", "project.create", "project.archive", "task.read", "task.create",
        "task.update",
        "task.assign", "task.complete", "approval.read", "approval.request",
        "approval.approve", "document.read", "document.create", "document.version",
        "document.review", "document.approve", "report.read", "report.create",
        "report.review", "finding.read", "finding.create", "finding.update",
        "finding.verify", "work.evidence.link", "work.comment.create",
        "work.relation.link", "work.checklist.manage",
    ]
    owner, owner_id = actor("shared-owner@alos.test", owner_permissions)
    reviewer, reviewer_id = actor(
        "shared-reviewer@alos.test",
        ["task.read", "approval.approve", "document.approve", "report.review",
         "finding.verify"],
    )
    publisher, _ = actor(
        "shared-publisher@alos.test",
        ["document.retire", "report.publish", "report.archive", "finding.close"],
    )
    legacy, _ = actor("shared-legacy@alos.test", ["work.read", "work.write"])
    remote, _ = actor(
        "shared-remote@alos.test", ["work.read", "work.write"],
        workspace_id="workspace_shared_remote", workspace_key="shared-remote",
        workspace_name="Remote Shared Work",
    )

    project = request(
        "/api/v1/projects", token=owner,
        payload={"code": "SHARED-INT", "name": "Shared Work Integration"},
    )
    project_id = project["project_id"]
    assert project["status"] == "PLANNED"
    assert project["owner_actor_id"] == owner_id
    members = request("/api/v1/workspace-members", token=owner)
    assert {member["actor_id"] for member in members} >= {owner_id, reviewer_id}
    task = request(
        "/api/v1/tasks", token=owner,
        payload={"title": "Shared Work Task", "project_id": project_id},
    )
    task_id = task["task_id"]
    assert task["project_name"] == project["name"]
    blocker = request(
        "/api/v1/tasks", token=owner, payload={"title": "Shared Work Prerequisite"},
    )
    dependency_path = f"/api/v1/tasks/{task_id}/dependencies"
    assert request(
        dependency_path, token=owner,
        payload={"blocked_by_task_id": blocker["task_id"]},
    )["blocked_by"][0]["title"] == "Shared Work Prerequisite"
    assert request(f"/api/v1/tasks/{task_id}", token=owner)["blocked_by"][0][
        "blocked_by_task_id"
    ] == blocker["task_id"]
    expect_denied(
        dependency_path, {"blocked_by_task_id": blocker["task_id"]}, legacy,
        expected_statuses={403},
    )
    assert request(
        f"/api/v1/tasks/{task_id}/assign", token=owner,
        payload={"owner_actor_id": reviewer_id},
    )["owner_actor_id"] == reviewer_id
    expect_denied(
        f"/api/v1/tasks/{task_id}/complete", None, owner,
        method="POST", expected_statuses={409},
    )
    assert request(
        f"/api/v1/tasks/{blocker['task_id']}/complete", token=owner, method="POST"
    )["status"] == "COMPLETED"
    assert request(
        f"/api/v1/tasks/{task_id}/complete", token=owner, method="POST"
    )["status"] == "COMPLETED"
    assert request(f"/api/v1/tasks/{task_id}", token=owner)["status"] == "COMPLETED"
    project = request(f"/api/v1/projects/{project_id}", token=owner)
    assert project["progress_percentage"] == 100
    assert project["tasks_count"] == 1
    assert project["risk_level"] == "LOW"
    expect_denied(f"/api/v1/projects/{project_id}", None, remote, expected_statuses={404})

    approval = request(
        "/api/v1/approvals", token=owner,
        payload={"subject_type": "PROJECT", "subject_id": project_id,
                 "materiality_value": 1250000.50},
    )
    approval_id = approval["approval_id"]
    assert approval["subject_title"] == project["name"]
    assert approval["requester_name"] == "shared-owner@alos.test"
    assert approval["materiality_value"] == 1250000.50
    expect_denied(
        f"/api/v1/approvals/{approval_id}/approve", {}, owner,
        expected_statuses={403},
    )
    expect_denied(
        f"/api/v1/approvals/{approval_id}/approve", {}, legacy,
        expected_statuses={403},
    )
    assert request(
        f"/api/v1/approvals/{approval_id}/approve", payload={}, token=reviewer
    )["status"] == "APPROVED"

    document = request(
        "/api/v1/documents", token=owner,
        payload={"title": "Shared Work Policy", "category": "Policy",
                 "data_classification": "INTERNAL", "project_id": project_id,
                 "description": "Authoritative document metadata",
                 "effective_date": "2026-10-01"},
    )
    document_id = document["document_id"]
    assert document["project_name"] == project["name"]
    assert request(
        f"/api/v1/documents/{document_id}/links", token=owner,
        payload={"target_type": "TASK", "target_id": task_id},
    )["entity_id"] == task_id
    assert request(
        f"/api/v1/documents/{document_id}/links", token=owner,
        payload={"target_type": "APPROVAL", "target_id": approval_id},
    )["entity_id"] == approval_id
    assert request(f"/api/v1/documents/{document_id}", token=owner)["tasks_count"] == 1
    assert request(f"/api/v1/tasks/{task_id}", token=owner)["documents_count"] == 1
    assert request(f"/api/v1/approvals/{approval_id}", token=owner)["documents_count"] == 1
    assert any(item["entity_id"] == document_id for item in request(
        f"/api/v1/work/TASK/{task_id}/relations", token=owner
    ))
    checklist_path = f"/api/v1/work/TASK/{task_id}/checklist"
    checklist = request(checklist_path, token=owner, payload={"body": "Inspect source"})
    assert request(
        f"{checklist_path}/{checklist['item_id']}/complete", token=owner, method="POST"
    )["completed"] is True
    assert len(request(checklist_path, token=owner)) == 1
    source_id = "source_shared_work_smoke"
    assert postgres_sql(
        "INSERT INTO core.sources "
        "(source_id,tenant_id,organization_id,workspace_id,title,source_type,"
        "data_classification,created_by,created_at) VALUES "
        "('source_shared_work_smoke','tenant_shared_work','org_shared_work',"
        "'workspace_shared_work','Verified fixture','PDF','INTERNAL',"
        "'shared_work_fixture',now()); "
        "INSERT INTO core.source_versions "
        "(source_id,source_version,tenant_id,organization_id,workspace_id,"
        "storage_uri,content_hash,status,created_by,created_at) VALUES "
        "('source_shared_work_smoke','1','tenant_shared_work','org_shared_work',"
        "'workspace_shared_work','urn:alos:source:shared-work:1',"
        "'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',"
        "'VERIFIED','shared_work_fixture',now()); "
        "SELECT status FROM core.source_versions "
        "WHERE source_id='source_shared_work_smoke';"
    ) == "VERIFIED"
    source_options = request(
        f"/api/v1/documents/{document_id}/source-options", token=owner
    )
    assert {item["source_id"] for item in source_options} == {source_id}
    assert all("storage_uri" not in item for item in source_options)
    version = request(
        f"/api/v1/documents/{document_id}/versions", token=owner,
        payload={"version": "1.0", "source_id": source_id, "source_version": "1"},
    )
    assert version["content_hash"].startswith("sha256:")
    expect_denied(
        f"/api/v1/documents/{document_id}/approve", None, owner,
        method="POST", expected_statuses={403},
    )
    expect_denied(
        f"/api/v1/documents/{document_id}/review", None, legacy,
        method="POST", expected_statuses={403},
    )
    assert request(
        f"/api/v1/documents/{document_id}/review", token=owner, method="POST"
    )["status"] == "IN_REVIEW"
    assert request(
        f"/api/v1/documents/{document_id}/approve", token=reviewer, method="POST"
    )["status"] == "APPROVED"
    assert request(
        f"/api/v1/documents/{document_id}/retire", token=publisher, method="POST"
    )["status"] == "RETIRED"
    assert request(
        f"/api/v1/documents/{document_id}/versions", token=owner
    )[0]["content_hash"] == version["content_hash"]

    definition = request(
        "/api/v1/work/reports/definitions", token=owner,
        payload={"name": "Operational definition", "report_type": "OPERATIONAL",
                 "frequency": "MONTHLY", "review_required": True,
                 "recipients": [], "sections": ["Summary"], "data_sources": []},
    )
    definition_id = definition["report_definition_id"]
    assert request(
        f"/api/v1/work/reports/definitions/{definition_id}", token=owner
    )["name"] == "Operational definition"
    assert request(
        f"/api/v1/work/reports/definitions/{definition_id}", token=owner,
        payload={"description": "Monthly result"}, method="PATCH",
    )["description"] == "Monthly result"
    report = request(
        "/api/v1/work/reports/results", token=owner,
        payload={"title": "Shared Work Result", "report_type": "OPERATIONAL",
                 "description": "Monthly summary", "period_start": "2026-09-01",
                 "period_end": "2026-09-30", "project_id": project_id},
    )
    report_id = report["report_id"]
    report_path = f"/api/v1/work/reports/results/{report_id}"
    assert request(f"{report_path}/submit-review", token=owner, method="POST")["status"] == "IN_REVIEW"
    expect_denied(f"{report_path}/review", None, owner, method="POST", expected_statuses={403})
    expect_denied(f"{report_path}/review", None, legacy, method="POST", expected_statuses={403})
    assert request(f"{report_path}/review", token=reviewer, method="POST")["status"] == "APPROVED"
    published = request(f"{report_path}/publish", token=publisher, method="POST")
    assert published["status"] == "PUBLISHED" and published["published_at"]
    assert request(f"{report_path}/archive", token=publisher, method="POST")["status"] == "ARCHIVED"

    finding = request(
        "/api/v1/work/findings", token=owner,
        payload={"title": "Shared Work Finding", "severity": "MEDIUM",
                 "project_id": project_id, "corrective_action_task_id": task_id,
                 "due_date": "2026-10-30", "impact": "Service interruption"},
    )
    finding_id = finding["finding_id"]
    finding_path = f"/api/v1/work/findings/{finding_id}"
    assert request(f"{finding_path}/start", token=owner, method="POST")["status"] == "IN_PROGRESS"
    assert request(
        f"{finding_path}/submit-verification", token=owner, method="POST"
    )["status"] == "PENDING_VERIFICATION"
    expect_denied(f"{finding_path}/verify", None, owner, method="POST", expected_statuses={403})
    expect_denied(f"{finding_path}/verify", None, legacy, method="POST", expected_statuses={403})
    verified = request(f"{finding_path}/verify", token=reviewer, method="POST")
    assert verified["status"] == "VERIFIED"
    assert verified["verifier_actor_id"] == reviewer_id
    assert verified["corrective_action_task_title"] == task["title"]
    assert request(f"{finding_path}/close", token=publisher, method="POST")["status"] == "CLOSED"

    relations = request(f"/api/v1/projects/{project_id}/relations", token=owner)
    assert {item["entity_type"] for item in relations} >= {
        "TASK", "APPROVAL", "DOCUMENT", "REPORT", "FINDING",
    }
    evidence_id = "evidence_shared_work_smoke"
    assert postgres_sql(
        "INSERT INTO evidence.evidence_refs "
        "(evidence_id,tenant_id,organization_id,workspace_id,source_id,uri,"
        "content_hash,data_classification,validation_status,metadata_payload,captured_at) "
        "VALUES ('evidence_shared_work_smoke','tenant_shared_work','org_shared_work',"
        "'workspace_shared_work','source_shared_work_smoke','urn:alos:evidence:shared-work',"
        "'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',"
        "'INTERNAL','VERIFIED','{}',now()); "
        "SELECT validation_status FROM evidence.evidence_refs "
        "WHERE evidence_id='evidence_shared_work_smoke';"
    ) == "VERIFIED"
    entity_path = f"/api/v1/work/PROJECT/{project_id}"
    assert any(item["evidence_id"] == evidence_id for item in request(
        "/api/v1/work/evidence-candidates", token=owner
    ))
    assert request(
        f"{entity_path}/evidence", token=owner, payload={"evidence_id": evidence_id}
    )["source_id"] == source_id
    assert len(request(f"{entity_path}/evidence", token=owner)) == 1
    assert request(f"/api/v1/projects/{project_id}", token=owner)["evidence_count"] == 1
    assert request(
        f"{entity_path}/comments", token=owner, payload={"body": "Verified proof"}
    )["actor_id"] == owner_id
    assert len(request(f"{entity_path}/comments", token=owner)) == 1
    assert {item["event_type"] for item in request(
        f"{entity_path}/activity", token=owner
    )} >= {"project.created", "project.evidence_linked", "project.commented"}
    expect_denied(f"{entity_path}/evidence", None, remote, expected_statuses={404})

    for resource, identifier in (
        ("projects", project_id), ("tasks", task_id),
        ("work_approvals", approval_id), ("work_reports", report_id),
        ("work_findings", finding_id),
    ):
        expect_denied(
            f"/api/v1/domains/shared/{resource}/{identifier}",
            {"status": "DRAFT"}, legacy, method="PATCH", expected_statuses={409},
        )

    for table, column, identifier, status in (
        ("projects", "project_id", project_id, "PLANNED"),
        ("tasks", "task_id", task_id, "COMPLETED"),
        ("work_approvals", "approval_id", approval_id, "APPROVED"),
        ("documents", "document_id", document_id, "RETIRED"),
        ("work_reports", "report_id", report_id, "ARCHIVED"),
        ("work_findings", "finding_id", finding_id, "CLOSED"),
    ):
        assert postgres_sql(
            f"SELECT status FROM core.{table} WHERE {column}='{identifier}';"
        ) == status
    assert owner_id != reviewer_id
    print("Shared Work dedicated lifecycle and PostgreSQL integration passed")


def strategy_smoke() -> None:
    """Prove the deterministic Strategy cascade through a fresh persisted session."""
    executive = {
        "email": "strategy-executive@alos.test",
        "password": "integration-password",
        "display_name": "Strategy Integration Executive",
        "tenant_id": "tenant_integration_001",
        "organization_id": "org_integration_001",
        "workspace_id": "workspace_strategy_executive",
        "workspace_key": "strategy-executive",
        "workspace_name": "Strategy Executive Workspace",
        "workspace_type": "EXECUTIVE",
        "role_refs": ["EXECUTIVE"],
        "permission_refs": [
            "strategy.read",
            "strategy.company.manage",
            "strategy.review",
            "strategy.approve",
            "strategy.activate",
        ],
        "scope_refs": ["scope.strategy"],
        "data_scope": "COMPANY",
    }
    request("/api/v1/auth/register", payload=executive)
    unrelated = {
        **executive,
        "email": "strategy-unrelated@alos.test",
        "display_name": "Unrelated Strategy Workspace",
        "workspace_id": "workspace_strategy_unrelated",
        "workspace_key": "strategy-unrelated",
        "workspace_name": "Unrelated Strategy Workspace",
        "workspace_type": "BUSINESS",
        "role_refs": ["DIVISION_MEMBER"],
        "permission_refs": ["strategy.read"],
        "data_scope": "WORKSPACE",
    }
    request("/api/v1/auth/register", payload=unrelated)
    executive_login = request(
        "/api/v1/auth/login",
        payload={"email": executive["email"], "password": executive["password"]},
        correlation_id="corr_strategy_login_001",
    )
    unrelated_login = request(
        "/api/v1/auth/login",
        payload={"email": unrelated["email"], "password": unrelated["password"]},
        correlation_id="corr_strategy_unrelated_login_001",
    )
    token = executive_login["access_token"]
    unrelated_token = unrelated_login["access_token"]
    period = {
        "granularity": "ANNUAL",
        "starts_at": "2027-01-01",
        "ends_at": "2027-12-31",
    }
    plan_id = "plan.integration.rkap.2027"
    root_target_id = "target.integration.corporate.akad"
    derived_target_id = "target.integration.sales.leads"
    plan = request(
        "/api/v1/strategy/plans",
        payload={
            "plan_id": plan_id,
            "version": 1,
            "plan_type": "OPERATING_PLAN",
            "name": "RKAP 2027 Integration Proof",
            "owner_workspace_id": executive["workspace_id"],
            "owner_role_ref": "EXECUTIVE",
            "period": period,
            "scope": {"type": "COMPANY", "ref": None},
            "materiality": "MATERIAL",
            "source_refs": ["source:integration-rkap"],
            "evidence_refs": ["evidence:integration-rkap"],
        },
        token=token,
        correlation_id="corr_strategy_plan_001",
    )
    assert plan["lifecycle_state"] == "DRAFT"
    root_target = {
        "target_id": root_target_id,
        "version": 1,
        "code": "KPI-INTEGRATION-AKAD",
        "name": "Integration corporate akad target",
        "plan_ref": {"id": plan_id, "version": 1},
        "objective_ref": None,
        "metric_code": "KPI-INTEGRATION-AKAD",
        "scope": {"type": "COMPANY", "ref": None},
        "period": period,
        "measurement_type": "CUMULATIVE",
        "unit": "COUNT",
        "owner_workspace_id": executive["workspace_id"],
        "owner_role_ref": "EXECUTIVE",
        "materiality": "MATERIAL",
        "source_refs": ["source:integration-rkap"],
        "evidence_refs": ["evidence:integration-rkap"],
    }
    request(
        "/api/v1/strategy/targets",
        payload=root_target,
        token=token,
        correlation_id="corr_strategy_target_001",
    )
    request(
        f"/api/v1/strategy/targets/{root_target_id}/observations",
        payload={
            "observation_id": "observation.integration.corporate.akad",
            "target_id": root_target_id,
            "target_version": 1,
            "kind": "TARGET",
            "value": 7,
            "unit": "COUNT",
            "period": period,
            "source_ref": "evidence:integration-rkap",
            "source_mode": "MANUAL_EVIDENCED",
            "observed_at": "2026-09-27T00:00:00Z",
            "verified_at": "2026-09-27T00:01:00Z",
            "verification_state": "VERIFIED",
            "evidence_refs": ["evidence:integration-rkap"],
        },
        token=token,
        correlation_id="corr_strategy_observation_001",
    )
    preview = request(
        "/api/v1/strategy/cascade/preview",
        payload={
            "root_target_ref": {"target_id": root_target_id, "version": 1},
            "rules": [
                {
                    "cascade_rule_id": "rule.integration.required-leads",
                    "rule_type": "RATIO_DIVIDE_CEIL",
                    "input_target_refs": [{"target_id": root_target_id, "version": 1}],
                    "output_target_refs": [{"target_id": derived_target_id, "version": 1}],
                    "parameters": {},
                }
            ],
            "rule_inputs": {"rule.integration.required-leads": {"input": 7, "ratio": 0.3}},
            "assumption_refs": [],
            "constraints": [
                {
                    "constraint_id": "constraint.integration.capacity",
                    "constraint_type": "CAPACITY",
                    "critical": True,
                    "required_value": 24,
                    "available_value": 24,
                    "applies": True,
                }
            ],
        },
        token=token,
        correlation_id="corr_strategy_preview_001",
    )
    assert preview["status"] == "VALID"
    assert preview["calculation_trace"][0]["output"] == "24"
    assert preview["calculation_trace"][0]["rounding_mode"] == "CEILING"
    assert preview["constraint_results"][0]["result"] == "PASS"
    targets_after_preview = request("/api/v1/strategy/targets", token=token)
    assert [item["target_id"] for item in targets_after_preview] == [root_target_id]

    derived_target = {
        **root_target,
        "target_id": derived_target_id,
        "code": "KPI-INTEGRATION-LEADS",
        "name": "Integration derived sales lead target",
        "scope": {"type": "DIVISION", "ref": "workspace_strategy_sales"},
        "owner_workspace_id": "workspace_strategy_sales",
        "owner_role_ref": "DIVISION_LEAD",
    }
    accepted = request(
        f"/api/v1/strategy/cascade-runs/{preview['cascade_run_id']}/accept",
        payload={"derived_targets": [derived_target]},
        token=token,
        correlation_id="corr_strategy_accept_001",
    )
    assert accepted["status"] == "ACCEPTED"
    accepted_target = request(f"/api/v1/strategy/targets/{derived_target_id}", token=token)
    assert accepted_target["target"]["lifecycle_state"] == "DRAFT"
    assert accepted_target["target"]["cascade_run_id"] == preview["cascade_run_id"]

    submitted = request(f"/api/v1/strategy/plans/{plan_id}/submit", payload={}, token=token)
    assert submitted["lifecycle_state"] == "UNDER_REVIEW"
    approved = request(f"/api/v1/strategy/plans/{plan_id}/approve", payload={}, token=token)
    assert approved["lifecycle_state"] == "APPROVED"
    activated = request(f"/api/v1/strategy/plans/{plan_id}/activate", payload={}, token=token)
    assert activated["lifecycle_state"] == "ACTIVE"

    fresh_login = request(
        "/api/v1/auth/login",
        payload={"email": executive["email"], "password": executive["password"]},
        correlation_id="corr_strategy_fresh_session_001",
    )
    fresh_token = fresh_login["access_token"]
    persisted_plan = request(f"/api/v1/strategy/plans/{plan_id}", token=fresh_token)
    persisted_target = request(
        f"/api/v1/strategy/targets/{derived_target_id}", token=fresh_token
    )
    assert persisted_plan["lifecycle_state"] == "ACTIVE"
    assert persisted_target["target"]["lifecycle_state"] == "ACTIVE"
    expect_denied(
        f"/api/v1/strategy/targets/{derived_target_id}",
        None,
        unrelated_token,
        expected_statuses={403},
    )


def identity_lifecycle_smoke(registration: dict, admin_token: str) -> None:
    """Exercise employee authority through the live Web and PostgreSQL stack."""
    workspace_id = registration["workspace_id"]
    tenant_id = registration["tenant_id"]
    organization_id = registration["organization_id"]
    employee_id = "employee_integration_identity"
    email = "identity-employee@alos.test"
    expired_employee_id = "employee_integration_expired"
    expired_email = "identity-expired@alos.test"

    for person_id, person_email, number in (
        (employee_id, email, "INTEGRATION-IDENTITY-001"),
        (expired_employee_id, expired_email, "INTEGRATION-IDENTITY-002"),
    ):
        assert postgres_sql(
            "INSERT INTO hr.employees "
            "(employee_id, tenant_id, organization_id, workspace_id, actor_id, "
            "employee_number, full_name, email, employment_status, join_date, "
            "department_code, created_at, updated_at) VALUES "
            f"('{person_id}', '{tenant_id}', '{organization_id}', '{workspace_id}', NULL, "
            f"'{number}', 'Integration Employee', '{person_email}', 'ACTIVE', "
            "CURRENT_DATE - 1, 'IT', now(), now()) RETURNING employee_id;"
        ) == person_id

    candidates = request("/api/v1/identity/provisioning-candidates", token=admin_token)
    assert {item["employee_id"] for item in candidates} >= {employee_id, expired_employee_id}

    def provision(person_id: str, person_email: str) -> dict:
        account = request(
            "/api/v1/identity/accounts",
            token=admin_token,
            payload={
                "employee_id": person_id,
                "email": person_email,
                "workspace_id": workspace_id,
                "role_refs": ["DIVISION_MEMBER"],
                "effective_at": "2026-01-01T00:00:00Z",
            },
        )
        assert account["activation_state"] == "PENDING"
        assert re.fullmatch(r"actor_[0-9a-f]{32}", account["actor_id"])
        assert postgres_sql(
            "SELECT count(*) = 1 FROM core.auth_accounts "
            f"WHERE actor_id = '{account['actor_id']}' AND activation_state = 'PENDING';"
        ) == "t"
        assert postgres_sql(
            "SELECT count(*) = 1 FROM hr.employees "
            f"WHERE employee_id = '{person_id}' AND actor_id = '{account['actor_id']}';"
        ) == "t"
        return account

    account = provision(employee_id, email)
    credential = activation_credential(email)
    credential_hash = hashlib.sha256(credential.encode()).hexdigest()
    assert postgres_sql(
        "SELECT count(*) = 1 FROM core.activation_challenges "
        f"WHERE challenge_id = 'activation_{account['actor_id']}' "
        f"AND token_hash = '{credential_hash}' AND consumed_at IS NULL;"
    ) == "t"

    employee_cookies = CookieJar()
    employee_browser = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(employee_cookies)
    )
    expect_web_error(
        employee_browser,
        "/api/session/login",
        401,
        payload={"email": email, "password": "EmployeePass!123"},
        code="INVALID_CREDENTIALS",
    )
    expect_web_error(employee_browser, "/api/session", 401)

    activation_payload = {
        "token": credential,
        "password": "EmployeePass!123",
        "password_confirmation": "EmployeePass!123",
    }
    expect_web_error(
        employee_browser,
        "/api/session/activate",
        422,
        payload={**activation_payload, "token": "invalid-integration-activation-credential"},
        code="ACTIVATION_CHALLENGE_INVALID",
        credential="invalid-integration-activation-credential",
    )

    expired_account = provision(expired_employee_id, expired_email)
    expired_credential = activation_credential(expired_email)
    postgres_sql(
        "UPDATE core.activation_challenges SET expires_at = now() - interval '1 second' "
        f"WHERE challenge_id = 'activation_{expired_account['actor_id']}';"
    )
    expect_web_error(
        employee_browser,
        "/api/session/activate",
        422,
        payload={
            "token": expired_credential,
            "password": "ExpiredPass!123",
            "password_confirmation": "ExpiredPass!123",
        },
        code="ACTIVATION_CHALLENGE_INVALID",
        credential=expired_credential,
    )
    assert postgres_sql(
        "SELECT count(*) = 1 FROM core.auth_accounts "
        f"WHERE actor_id = '{expired_account['actor_id']}' AND activation_state = 'PENDING';"
    ) == "t"

    status, activation = web_request(
        employee_browser, "/api/session/activate", payload=activation_payload
    )
    assert status == 200
    assert activation == {"actor_id": account["actor_id"], "activation_state": "ACTIVATED"}
    expect_web_error(employee_browser, "/api/session", 401)
    assert postgres_sql(
        "SELECT count(*) = 1 FROM core.activation_challenges "
        f"WHERE challenge_id = 'activation_{account['actor_id']}' "
        "AND consumed_at IS NOT NULL;"
    ) == "t"
    expect_web_error(
        employee_browser,
        "/api/session/activate",
        422,
        payload=activation_payload,
        code="ACTIVATION_CHALLENGE_INVALID",
        credential=credential,
    )

    status, employee_login = web_request(
        employee_browser,
        "/api/session/login",
        payload={"email": email, "password": "EmployeePass!123"},
    )
    assert status == 200
    assert isinstance(employee_login, dict) and employee_login["authenticated"] is True
    session_cookie = next(
        cookie.value for cookie in employee_cookies if cookie.name == "alos_backend_session"
    )
    status, session = web_request(employee_browser, "/api/session")
    assert status == 200 and isinstance(session, dict)
    assert session["principal"]["actor"]["actor_id"] == account["actor_id"]
    assert session["principal"]["active_workspace"]["workspace"]["workspace_id"] == workspace_id
    status, workspaces = web_request(employee_browser, "/api/backend/api/v1/workspaces")
    assert status == 200 and isinstance(workspaces, list)
    assert [item["workspace"]["workspace_id"] for item in workspaces] == [workspace_id]
    assert workspaces[0]["role_refs"] == ["DIVISION_MEMBER"]
    expect_web_error(employee_browser, "/api/backend/api/v1/identity/accounts", 403)
    assert postgres_sql(
        "SELECT count(*) = 1 FROM core.auth_sessions "
        f"WHERE actor_id = '{account['actor_id']}' AND active = true AND revoked_at IS NULL;"
    ) == "t"

    # Resend activation challenge for expired account
    resend_result = request(
        f"/api/v1/identity/actors/{expired_account['actor_id']}/activation/resend",
        token=admin_token,
        payload={},
    )
    assert resend_result["activation_state"] == "PENDING"
    assert resend_result["actor_id"] == expired_account["actor_id"]
    resent_credential = activation_credential(expired_email)
    resent_hash = hashlib.sha256(resent_credential.encode()).hexdigest()
    assert postgres_sql(
        "SELECT count(*) = 1 FROM core.activation_challenges "
        f"WHERE token_hash = '{resent_hash}' AND expires_at > now() AND consumed_at IS NULL;"
    ) == "t"

    suspended = request(
        f"/api/v1/identity/actors/{account['actor_id']}/suspend",
        token=admin_token,
        payload={"reason": "Integration access revocation"},
    )
    assert suspended == {"actor_id": account["actor_id"], "active": False}
    assert postgres_sql(
        "SELECT count(*) = 1 FROM core.auth_accounts "
        f"WHERE actor_id = '{account['actor_id']}' "
        "AND active = false AND administrative_state = 'SUSPENDED';"
    ) == "t"
    assert postgres_sql(
        "SELECT count(*) = 1 FROM core.auth_sessions "
        f"WHERE actor_id = '{account['actor_id']}' AND active = false "
        "AND revoked_at IS NOT NULL;"
    ) == "t"
    expect_web_error(employee_browser, "/api/session", 401)
    expect_web_error(employee_browser, "/api/backend/api/v1/workspaces", 401)
    expect_denied(
        "/api/v1/auth/whoami", None, session_cookie, expected_statuses={401}
    )
    expect_web_error(
        employee_browser,
        "/api/session/login",
        401,
        payload={"email": email, "password": "EmployeePass!123"},
        code="INVALID_CREDENTIALS",
    )

    # Reactivate the account
    reactivated = request(
        f"/api/v1/identity/actors/{account['actor_id']}/activate",
        token=admin_token,
        payload={"reason": "Integration reactivation"},
    )
    assert reactivated == {"actor_id": account["actor_id"], "active": True}
    assert postgres_sql(
        "SELECT count(*) = 1 FROM core.auth_accounts "
        f"WHERE actor_id = '{account['actor_id']}' "
        "AND active = true AND administrative_state = 'ENABLED';"
    ) == "t"

    # Login works again after reactivation
    status, reactivated_login = web_request(
        employee_browser,
        "/api/session/login",
        payload={"email": email, "password": "EmployeePass!123"},
    )
    assert status == 200 and isinstance(reactivated_login, dict) and reactivated_login["authenticated"] is True

    # Password reset flow
    status, reset_request = web_request(
        employee_browser,
        "/api/session/password-reset/request",
        payload={"email": email},
    )
    assert status == 200
    assert "Jika email terdaftar" in reset_request.get("message", "")
    assert postgres_sql(
        "SELECT count(*) >= 1 FROM core.password_reset_challenges prc "
        "JOIN core.auth_accounts aa ON prc.account_id = aa.account_id "
        f"WHERE aa.actor_id = '{account['actor_id']}' AND prc.consumed_at IS NULL;"
    ) == "t"

    reset_token = activation_credential(email)
    new_password = "NewEmployeePass!456"
    status, reset_confirm = web_request(
        employee_browser,
        "/api/session/password-reset/confirm",
        payload={
            "token": reset_token,
            "password": new_password,
            "password_confirmation": new_password,
        },
    )
    assert status == 200
    assert "Kata sandi berhasil diperbarui" in reset_confirm.get("message", "")
    assert postgres_sql(
        "SELECT count(*) >= 1 FROM core.password_reset_challenges prc "
        "JOIN core.auth_accounts aa ON prc.account_id = aa.account_id "
        f"WHERE aa.actor_id = '{account['actor_id']}' AND prc.consumed_at IS NOT NULL;"
    ) == "t"

    # Old password fails
    expect_web_error(
        employee_browser,
        "/api/session/login",
        401,
        payload={"email": email, "password": "EmployeePass!123"},
        code="INVALID_CREDENTIALS",
    )

    # Login with new password succeeds
    status, new_login = web_request(
        employee_browser,
        "/api/session/login",
        payload={"email": email, "password": new_password},
    )
    assert status == 200 and isinstance(new_login, dict) and new_login["authenticated"] is True

    # Re-suspend to satisfy workflow persistence invariant
    request(
        f"/api/v1/identity/actors/{account['actor_id']}/suspend",
        token=admin_token,
        payload={"reason": "Integration completion suspension"},
    )
    postgres_sql(
        f"DELETE FROM core.auth_sessions WHERE actor_id = '{account['actor_id']}' "
        "AND session_id NOT IN ("
        f"  SELECT session_id FROM core.auth_sessions WHERE actor_id = '{account['actor_id']}' "
        "  ORDER BY created_at ASC LIMIT 1"
        ");"
    )



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
        "role_refs": ["DIVISION_MEMBER"],
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
        "role_refs": ["DIVISION_MEMBER"],
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
    identity_lifecycle_smoke(registration, token)
    multi_account = request(
        "/api/v1/auth/register",
        payload={
            **registration,
            "email": "integration-multi@alos.test",
            "display_name": "Multi Workspace Actor",
            "role_refs": ["DIVISION_MEMBER"],
            "permission_refs": ["tools.diagnostic.execute"],
            "scope_refs": ["scope.diagnostic"],
            "data_scope": "WORKSPACE",
        },
    )
    multi_actor_id = multi_account["actor"]["actor_id"]
    request(
        f"/api/v1/identity/actors/{multi_actor_id}/memberships",
        payload={
            "workspace_id": beta_registration["workspace_id"],
            "role_refs": ["DIVISION_LEAD"],
            "effective_at": "2026-01-01T00:00:00Z",
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
    assert selected_beta["membership"]["role_refs"] == ["DIVISION_LEAD"]
    multi_whoami = request("/api/v1/auth/whoami", token=multi_token)
    assert multi_whoami["actor"]["actor_id"] == multi_actor_id
    assert multi_whoami["active_workspace"]["workspace"]["workspace_id"] == beta_registration["workspace_id"]
    assert multi_whoami["active_workspace"]["role_refs"] == ["DIVISION_LEAD"]
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
            "employee_id": "employee_foreign_attempt",
            "email": "cross-org@alos.test",
            "workspace_id": foreign_registration["workspace_id"],
            "role_refs": ["DIVISION_MEMBER"],
            "effective_at": "2026-01-01T00:00:00Z",
        },
        token,
        expected_statuses={403},
    )
    expect_denied(
        "/api/v1/identity/accounts",
        {
            "employee_id": "employee_foreign_attempt",
            "email": "cross-tenant@alos.test",
            "workspace_id": registration["workspace_id"],
            "role_refs": ["DIVISION_MEMBER"],
            "effective_at": "2026-01-01T00:00:00Z",
            "tenant_id": foreign_registration["tenant_id"],
        },
        token,
        expected_statuses={422},
    )
    expect_denied(
        f"/api/v1/identity/actors/{foreign_actor['actor']['actor_id']}/memberships",
        {
            "workspace_id": registration["workspace_id"],
            "role_refs": ["DIVISION_MEMBER"],
            "effective_at": "2026-01-01T00:00:00Z",
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

    shared_work_smoke()
    strategy_smoke()

    bootstrap = request("/api/v1/integration/bootstrap", payload={}, token=token)
    run = {
        "agent_id": bootstrap["agent_id"],
        "agent_version": bootstrap["agent_version"],
        "capability_id": "capability.runtime.diagnostic",
        "input": {"message": "integration roundtrip"},
        "requested_tool_ids": ["diagnostic.echo"],
        "scope_refs": ["scope.diagnostic"],
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
    print("Web-Backend-PostgreSQL-GENESIS deterministic integration passed")
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
