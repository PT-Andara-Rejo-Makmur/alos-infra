# Shared Gate Validation

Validation date: 2026-09-20  
Decision: **READY**

## Result

| Scenario | Status | Evidence |
|---|---|---|
| Gate 1 scenario | **PASS** | ALOS Web established a Backend-issued session through a same-origin BFF, then completed Web → Backend → GENESIS over real HTTP with canonical `ExecutionContext`, correlation, least-privilege egress proposal, structured response, and audit coverage. |
| Private URL incremental UAT | **PASS** | An external-research decision was followed by Backend-owned retrieval of `https://127.0.0.1/private-evidence`. The request was rejected before HTTP with `EGRESS_PRIVATE_NETWORK_BLOCKED`; the research and retrieval events retained one correlation ID and the retrieval event recorded `BLOCKED`. |
| Cross-repository trace and integration | **PASS** | Contracts, Web, Backend, and GENESIS use the same canonical request/decision shapes. The full browser path preserved `corr_shared_web_gate_001`; Web calls only its same-origin Backend BFF and cannot call GENESIS directly. |
| R&D access negative test | **PASS** | Unauthorized domain access is denied before GENESIS. Browser attempts to submit `tenant_id`, `workspace_id`, `scope_refs`, or `permission_refs` are rejected with `REQUEST_VALIDATION_FAILED`; correlation is preserved and GENESIS is not called. |

## Live trace

The validation used isolated local ports and the committed service implementations:

- Web: `127.0.0.1:13000`
- Backend: `127.0.0.1:18000`
- GENESIS: `127.0.0.1:18100`
- Correlation: `corr_shared_web_gate_001`

Observed result:

```text
context_status=ACTIVE
login_status=200
session_cookie=HttpOnly; SameSite=Lax
token_exposed_in_browser_response=false
context_tenant=tenant_browser_gate
authorized_domains=TECHNOLOGY
research_state=NEEDS_REVIEW
research_decision=REQUEST_EXTERNAL_RESEARCH
research_correlation=corr_shared_web_gate_001
authority_injection_status=422
authority_injection_code=REQUEST_VALIDATION_FAILED
```

The temporary validation services were stopped. Existing processes on ports 8000 and
8100 were not modified.

## Automated evidence

Backend integration coverage verifies:

- Backend-authoritative context and domain projections;
- least-privilege `ExecutionContext` sent to GENESIS;
- tenant, organization, workspace, scope, permission, tool, and correlation lineage;
- success and denial audit events;
- private/loopback egress rejection before network access;
- one correlation ID across research decision and egress denial;
- rejection of public authority-expansion fields before GENESIS.

Quality result:

```text
Backend ruff       PASS
Backend mypy       PASS (119 source files)
Backend pytest     PASS (121 tests)
Web lint           PASS
Web typecheck      PASS
Web tests          PASS (173 tests)
Web build          PASS
Infra topology     PASS (local, staging, production)
```

The pytest cache warning is caused by the sandbox user's write permissions and does
not affect test execution or repository artifacts.

## Authentication boundary

ALOS Web now terminates the browser session at a same-origin route. Login credentials
are forwarded to Backend for verification, the Backend token is stored only in an
HttpOnly `SameSite=Lax` cookie, and protected calls are forwarded server-side with the
Backend-issued Bearer token. The token is not returned to browser JavaScript.

Infra supplies `ALOS_BACKEND_INTERNAL_URL=http://backend:8000` to the Web runtime.
GENESIS remains unreachable from Web and no authorization decision is performed in
the BFF.

## Remaining limitation

The current Backend token has no canonical expiry/refresh metadata. The Web cookie is
therefore a browser-session cookie and is cleared explicitly on logout or after a
Backend `401`. Token rotation and refresh remain a future identity-contract concern;
they are not required for this gate.
