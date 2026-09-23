# Canonical Identity Security Closure Baseline

Audit date: 2026-09-24  
Branch: `development`

## Repository baseline

| Repository | Starting SHA | Development vs main | Working tree | Latest development CI |
| --- | --- | --- | --- | --- |
| `alos-contracts` | `90a01e8c3af4ca49653afcd827e252047aec05f2` | 2 ahead, 0 behind | clean | Contract quality: PASS |
| `alos-backend` | `927f54d37d41f4a6b5810bb69ef5e878289e032a` | 9 ahead, 0 behind | clean | Kualitas backend: PASS |
| `alos-web` | `6bc2d22bc2c2618ee55111f9ae101ab43b2d480f` | 3 ahead, 0 behind | pre-existing `next-env.d.ts` development-mode change only | Kualitas ALOS Web: PASS |
| `genesis-ai` | `c740b2aaa63775555451482c8ef421edd4cb9a79` | 28 ahead, 0 behind | clean | Kualitas GENESIS: PASS |
| `alos-infra` | `1da38f98580374928207090fac62f580a175736a` | 4 ahead, 0 behind | clean | Integrasi Backend dan GENESIS: PASS |

Contracts version is `1.7.0`. Alembic has one head:
`0008_canonical_identity_access`.

## Reproduced findings

### P0: client-controlled provisioning boundary

`POST /api/v1/identity/accounts` enforces
`identity.accounts.manage`, but forwards the complete request payload to
`AuthService.provision`. The service then constructs `ProvisionAccount` with
`tenant_id` and `organization_id` taken from that payload. The audit event also
records the client-supplied boundary. A principal in organization A can
therefore attempt to provision into organization or tenant B when it knows a
target boundary. Permission enforcement does not replace tenant and
organization boundary enforcement.

Required closure: production provisioning derives tenant and organization
from the authenticated principal, verifies the target workspace belongs to
that same active authority boundary, and fails closed on any mismatch.

### P0: active-workspace split brain

`AuthService.login` silently sets `active_workspace_id` from `accesses[0]`.
For multi-workspace actors this creates an implicit authority selection.

After workspace selection, `ProtectedDomainWorkspace` loads all accessible
workspaces and uses `find` over `workspace_key` or `division_code`. Two
same-domain workspaces can therefore produce:

- Backend active workspace B;
- visible Web workspace A (the first route match);
- roles projected from active membership B combined with workspace A.

Required closure: one active membership may be selected automatically;
multiple memberships require explicit selection. Protected Web surfaces must
consume the Backend session's `active_workspace` and only verify route
compatibility; they must never choose another workspace.

## Additional confirmed hardening gaps

- Production provisioning and membership mutation currently normalize legacy
  aliases through `CANONICAL_ROLE_MAP`; canonical APIs must reject aliases.
- A revoked active membership is omitted from the projection, but session
  state needs an explicit fail-closed regression proving there is no automatic
  fallback.
- Production self-registration is disabled and no explicit operator-only
  initial identity administrator bootstrap is present.
- Existing green CI does not yet exercise cross-tenant provisioning,
  same-domain multi-workspace selection, or revoked-active-workspace behavior.

## Non-goals retained

This closure does not create the full organization model, shared operational
modules, a production AI provider, a platform super-admin, or new GENESIS
business authority. Backend remains the authority; Web remains a projection;
GENESIS remains the intelligence/control plane.
