# Forwarderet Multi-Tenant Architecture Contract (MT-0)

**Status:** mechanically enforced architecture foundation; runtime multi-tenant readiness remains **NO — NOT YET PROVEN**  
**Inventory:** `docs/architecture/tenant-ownership-inventory.yaml`  
**Authoritative persisted organization model:** `OperationalOrganization`  
**Canonical domain term:** Organization  
**Canonical tenant key:** `organization_id`

This contract complements, and does not replace, the multi-tenant productization master plan. MT-0 changes no schema and does not claim that a second real company is safe to onboard.

## Vocabulary

- **Platform:** the Forwarderet control plane and shared technical/product services outside any one organization.
- **Organization:** the canonical business domain term for a company boundary. The current persisted authority is `OperationalOrganization`. Its broad rename is deferred because it would require a migration without improving MT-0 safety.
- **Tenant:** the security and data-isolation boundary represented by one Organization in a resolved Tenant Context. It is not a second model or a client-selectable ID.
- **Membership:** `OperationalMembership`, the organization-owned association granting a global user permission to act in an organization.
- **Tenant Staff:** a global `ExpertUser` acting through one active, server-validated Membership. Staff is a context, not a user subtype.
- **Platform Admin:** a future, separately authorized control-plane actor. The current global `ExpertUser.role == "admin"` is legacy RBAC and is neither proof of Platform Admin nor Company Admin authority.
- **Public Customer:** an unauthenticated or separately authenticated external person. Customer identity does not establish tenant context.
- **Public Capability:** constrained unauthenticated access requiring tenant-aware resolution plus hard-to-guess bearer material. It describes an access artifact/projection, never ownership of the underlying business row.
- **Tenant Context:** an immutable organization identity established by the backend from current authorization evidence. Body, path, query, host, or header IDs cannot elevate authority.
- **Tenant-Owned Resource:** a resource whose organization is proven directly or through one mandatory, unambiguous parent path.
- **Platform-Scoped Resource:** an explicitly allowlisted control-plane, identity, or genuinely shared catalog resource. Missing `organization_id` never implies platform scope.

The database permits several active memberships for a user, but current operational resolution requires exactly one active membership in an active organization and fails otherwise. MT-0 records this mismatch; tenant selection belongs to MT-2.

## Ownership classes

Every persisted business entity and important association table is classified exactly once:

1. `TENANT_OWNED_DIRECT`: has a non-null `organization_id`. This proves row ownership only; it does not prove that every referenced row belongs to the same tenant. The inventory records known integrity gaps.
2. `TENANT_OWNED_INDIRECT`: ownership follows one declared, non-null, FK-backed parent path terminating in direct ownership. Competing, nullable, textual, or polymorphic paths are not accepted. Reparenting is an ownership-changing operation and must fail unless tenant equivalence is proven.
3. `PLATFORM_SCOPED`: a deliberate allowlist exception with a rationale and platform-controlled writers.
4. `PUBLIC_CAPABILITY_SCOPED`: an access artifact, endpoint, or minimal projection constrained by both tenant context and bearer capability. It never makes underlying data public or ownerless.
5. `LEGACY_AMBIGUOUS`: current ownership cannot be proven. This is a defect register, not an authorization exemption.

New mapped models and association tables must enter the inventory in the same change. Contract tests reconcile the inventory with SQLAlchemy metadata, validate direct keys and indirect paths, require platform rationales, and require actionable ambiguity records.

## Trust boundaries and fail-closed rules

- The backend is authoritative for tenant isolation; frontend filtering is not a security control.
- `organization_id` alone does not prove safety. Commands must validate all referenced resources against the same Tenant Context.
- Missing, inactive, conflicting, or ambiguous tenant context fails closed.
- Cross-tenant IDs fail with a non-disclosing response and must not mutate rows, audit/outbox records, storage, or caches.
- Tenant checks precede permission checks only where needed for non-disclosure; having a permission never permits crossing tenants.
- Background jobs and events carry immutable tenant identity and establish it before data access. Platform-wide work partitions explicitly by tenant.
- Storage metadata and storage objects share the same tenant ownership. Authorization happens before object access.
- Caches, selectors, lists, exports, reports, logs, notifications, and downloads are part of the isolation boundary.
- RLS is later defense in depth, never the primary authorization system.

`backend.tenancy.TenantContext`, `require_tenant_context`, and `assert_same_tenant` are minimal fail-closed primitives. Constructing a context does not authorize it. MT-0 does not install request middleware or refactor services to use them.

## Mandatory tenant-isolation behavior contract

Future tenant-owned resource adapters must use equivalent permissions for Tenant A and Tenant B and prove:

- A can read/list/detail A and cannot read/list/detail or discover B;
- selectors, searches, counts, and pagination exclude B, including queries matching B;
- A cannot update or delete B, and B remains unchanged;
- A cannot create or update a resource by referencing B-owned IDs;
- swapping an A parent with a B child fails closed;
- valid permissions never cross tenants, while missing permissions within a tenant remain denied;
- missing, inactive, or conflicting membership/context is rejected;
- downloads authorize metadata and tenant before opening storage; and
- public capability tests remain separate from authenticated tenant tests.

Unsupported operations must be explicitly marked not applicable. HTTP boundaries should use opaque public identifiers and normally return a non-disclosing 404 for another tenant's resource.

## Public tracking: implemented capability boundary

Before MT-3, `GET /api/public/track/<identifier>` accepted numeric
`ShipmentRequest.id` and weak/global legacy tracking codes.  Numeric IDs were
not capabilities and the broad response did not satisfy this contract.

MT-3 now implements the endpoint as `PUBLIC_CAPABILITY_SCOPED`: only the exact
ADR-052 `SR2-` capability can resolve, ownership is derived and validated
server-side, and a fixed minimized projection is returned.  Numeric IDs,
authenticated public UUIDs, malformed or unknown values, and legacy weak codes
all receive the same non-disclosing 404.  `ShipmentRequest`,
`ShipmentTracking`, transport units, logs, quotes, and case documents remain
`LEGACY_AMBIGUOUS`; only the explicit response allowlist is public data.

### ADR-052 bounded supersession

ADR-052 is the accepted MT-3 authority for the shared public Request route.  It
retains the `PUBLIC_CAPABILITY_SCOPED` classification but replaces the proposed
caller-visible tenant-plus-capability lookup with one globally unique,
versioned 128-bit bearer capability.  The backend resolves exactly one Request
by that capability, derives its governed `TENANT` or `INTAKE` ownership
envelope, applies the current quarantine guard, and emits a fixed minimized
allowlist.  The caller supplies no tenant or resource ID.  Numeric IDs,
authenticated Request UUIDs, malformed/unknown values, and legacy weak codes
all share one non-disclosing failure.  This is tenant-aware server-side
derivation, not global code lookup as ownership or client-selected tenant
context.

## Legacy area register

| Area | Current owner model | Current risk | Required future slice |
|---|---|---|---|
| Requests | No direct owner; nullable Project link | public intake, staff/admin queries, and IDs are not tenant-bound | MT-1 ownership; MT-2 scoping |
| CRM | Global Customer graph and role-only access | lists/details/writes cross a future tenant boundary | MT-1, MT-2 |
| Administration | Legacy global `admin` role and unscoped request/user operations | platform and tenant authority are conflated | MT-2/MT-2A; UI only in MT-5 |
| Documents | Indirect through unscoped request; storage key has no tenant namespace | metadata/object ownership cannot independently be proven | MT-1, MT-2B |
| Branding/public portal | One global `SiteSetting` namespace | cannot represent separate tenants; cache/content crossover if reused | MT-7 |
| Public tracking | ADR-052 `SR2-` capability with server-derived ownership and minimized projection | rate limiting, capability rotation/revocation, hashed-at-rest storage, and infrastructure access-log redaction remain defense-in-depth hardening | MT-3 closed for the P0 authority defect; later governed hardening |

Existing legacy flows may continue unchanged during MT-0. New tenant-sensitive dependencies on ambiguous resources are prohibited. Ambiguous rows must never be silently assigned to a default organization; MT-1 must profile, adjudicate/backfill, quarantine unresolved data, and add same-tenant constraints.

## Phase dependencies

- **MT-1:** resolve every ambiguous data owner, backfill without assumptions, add non-null keys and same-tenant constraints, including request/quote/customer/document and direct-child integrity gaps.
- **MT-2:** establish central immutable request tenant context from validated membership; provide multi-membership selection; replace manual/unscoped access and separate platform authority. MT-2B covers documents, jobs, notifications, and caches.
- **MT-3:** implemented and qualified through ADR-052 Request tracking: numeric/legacy lookup is rejected, a versioned high-entropy capability is required, ownership is derived server-side, and only the minimal public projection is emitted.  Rotation/revocation UI, hashed-at-rest capability storage, generalized rate limiting, and infrastructure access-log redaction remain additive hardening.

Company/platform admin UI, licensing, branding, domains, and other later roadmap slices remain out of MT-0.

## Why RLS is deferred

Legacy rows have no proven owner, many children use indirect paths, background and admin contexts are undefined, and pooled connection context is not implemented. Adding RLS now could both break legitimate flows and create false confidence. After MT-1 and MT-2, MT-10 may add transaction-local context, `FORCE RLS`, least-privilege application roles, explicit privileged maintenance roles, and pool/worker tests while preserving application authorization as the primary control.
