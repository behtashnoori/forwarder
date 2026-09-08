# ADR-045: Personal Dashboard Entitlement and RBAC

- Status: ACCEPTED
- Date: 2026-09-07
- Owners: Architecture Owner, Product Owner, Security/RBAC Owner
- Affected domain: Personal Analytics, tenant authorization, product navigation

## Context

Forwarder already persists private `PERSONAL` dashboards, exposes owner-scoped list/detail/update/archive/restore APIs, clones the source-controlled Operations Control Tower template, and snapshots a Saved View query into an owned dashboard. It does not yet expose a dashboard index or normal navigation entry.

The present authorization contract is inconsistent. Dashboard list, get, update, archive, and restore require authentication and resolve one active organization membership, organization, and owner, but do not require a dashboard capability permission. Template clone requires `operational_shipment.read`. Control Tower also uses `operational_shipment.read`. Saved View resources follow the same membership plus owner pattern; snapshot requires ownership of both source and target but no explicit dashboard entitlement. Semantic Analytics separately requires `operational_shipment.read` and applies current assigned-Shipment and Project access before query evaluation.

LPAF v2.2 remains the active governing baseline. The reviewed v2.3 candidate and the Personal Analytics architecture-drift record make RBAC reachability, normal navigation, cross-slice integration, and live browser acceptance explicit product-surface gates. This Forwarder-specific ADR complements those generic controls; it does not promote or modify LPAF.

ADR-042 establishes that authority persona, governed capability, tenant membership, and business-record scope are distinct. It identifies dashboards/reporting as requiring an approved companion decision rather than Basic Expert intrinsic authority. ADR-043 requires capability and assigned-work scope to be evaluated independently and prohibits role names or hidden navigation from acting as authorization.

## Problem

The product needs one explicit contract answering who may discover and operate a Personal Dashboard without treating Control Tower access or Shipment read access as the dashboard entitlement. The contract must preserve private ownership and tenant isolation while ensuring that opening a dashboard never grants access to data that the current user cannot otherwise read.

This ADR decides the target authorization model only. It does not authorize source, schema, migration, permission, role-mapping, route, navigation, test, release, or production changes.

## Current authorization matrix

| Capability / action | Current capability gate | Ownership gate | Data gate | Problem |
|---|---|---|---|---|
| Dashboard list | Authentication + one active organization membership | Query filters current organization and current owner | None until widgets execute | No explicit dashboard entitlement |
| Dashboard create | Only system-template clone; `operational_shipment.read` | New row uses current organization and owner | Template contains widgets requiring Shipment read at execution | Dashboard creation is coupled to Shipment/Control Tower permission |
| Dashboard get | Authentication + membership | Exact current organization and owner | Widget runtime is separate | No explicit dashboard entitlement |
| Dashboard update | Authentication + membership | Exact current organization and owner; active row and optimistic version | Definition validation; no data read | No explicit dashboard entitlement |
| Dashboard archive | Authentication + membership | Exact current organization and owner | None | No explicit dashboard entitlement |
| Dashboard restore | Authentication + membership | Exact current organization and owner | None | No explicit dashboard entitlement |
| Create from Control Tower template | `operational_shipment.read` | Created for current organization and owner | Live widget queries require Shipment read | Source-surface permission is being used as dashboard entitlement |
| Saved View list | Authentication + membership | Current organization and owner | None until applied/executed | No explicit product capability gate |
| Saved View snapshot | Authentication + membership | Source Saved View and target Dashboard must both be owned and active in current organization | Copied query executes later under live Analytics authorization | Missing explicit target-dashboard mutation entitlement |
| Control Tower | Frontend and Analytics use `operational_shipment.read` | Assigned-Shipment/tenant scope is applied by Analytics | Live Semantic Analytics authorization | Operational surface and dashboard creation are coupled |
| Analytics execution | `operational_shipment.read` | Canonical one-membership tenant context | `assigned_shipment_scope`, Project Access propagation, query filters that may narrow only | Correctly separates data scope from dashboard definition |
| Operational Shipments | `operational_shipment.read` for reads; separate create/action permissions | Tenant plus assigned-work/Project-access policies | Per-resource backend authorization | A data-domain entitlement, not a generic personal-workspace entitlement |

Three independent checks are therefore required:

1. **Capability entitlement:** may the actor use the Personal Dashboard product surface/action?
2. **Resource ownership:** is the private dashboard owned by this actor inside the actor's canonical tenant?
3. **Data authorization:** may the actor execute each widget query and view its underlying rows now?

Passing one check never substitutes for either of the others.

## Decision

Adopt **a dedicated Personal Dashboard capability family** (Option B).

The proposed permission keys follow the existing `resource.action` taxonomy:

- `personal_dashboard.read` — discover navigation, list owned dashboards, and open an owned dashboard.
- `personal_dashboard.manage` — create from an approved system template, update, archive, restore, and accept a Saved View snapshot into an owned dashboard.

`personal_dashboard.manage` does not silently grant data access. Implementations SHOULD assign `personal_dashboard.read` with `personal_dashboard.manage`; backend mutation endpoints MUST still check the manage key explicitly. Navigation is visible only when the authenticated actor has one unambiguous active organization membership and `personal_dashboard.read`. The frontend is a reachability control, not the security boundary; every API enforces its own capability.

All dashboard objects remain `PERSONAL`, `PRIVATE`, tenant-bound, and owner-bound. No organization-wide dashboard sharing, delegation, impersonation, or Platform Admin bypass is introduced. List and detail APIs return only the current actor's resources. Cross-owner and cross-tenant attempts remain non-disclosing.

Action contract:

| Action | Required proposed capability | Additional invariant |
|---|---|---|
| List | `personal_dashboard.read` | Current tenant + current owner only |
| Read/open | `personal_dashboard.read` | Current tenant + current owner only |
| Create | `personal_dashboard.manage` | Create for current tenant/current owner from an approved contract |
| Update | `personal_dashboard.manage` | Current tenant + owner + active status + expected version |
| Archive/restore | `personal_dashboard.manage` | Current tenant + owner; lifecycle rules preserved |
| Create from system template | `personal_dashboard.manage` | Template identity/version is server-controlled; Control Tower access is not required |
| Saved View to Dashboard snapshot | `personal_dashboard.manage` | Source Saved View and target Dashboard are active, current-tenant, and current-owner; expected dashboard version and provenance remain mandatory |

An implementation MAY additionally require `personal_dashboard.read` on mutation requests for policy clarity, but it MUST NOT treat `operational_shipment.read`, Control Tower reachability, authority persona, legacy role rank, or organization membership alone as a substitute for `personal_dashboard.manage`.

### Live widget authorization invariant

Having either Personal Dashboard permission MUST NOT grant or broaden underlying data access. Every widget/query executes using the current authenticated user, current membership, current capability permission for the queried domain, current assigned-work/Project access, and current resource policy. Stored dashboard and Saved View definitions are query configuration, not grants. Persisted results, authorization snapshots, client-supplied tenant/user identifiers, or template provenance cannot bypass live evaluation.

Current implementation evidence supports this invariant for Semantic Analytics Shipment widgets: Analytics requires `operational_shipment.read`; applies canonical tenant and `assigned_shipment_scope` before filtering, grouping, aggregation, or drilldown; Platform Admin authority alone supplies no tenant-work scope; and Project-access revocation narrows a previously snapshotted widget without modifying its stored query or provenance.

`LIVE_WIDGET_AUTHORIZATION_INVARIANT = PASS` for the currently implemented Semantic Analytics Shipment/ROWSET widgets. Each future data domain requires its own execution-time authorization evidence and must fail closed if unsupported.

## Options considered

### Option A — every authenticated organization member

Rejected. Membership is the authoritative tenant selector, but current architecture explicitly says it is not broad business-data or governed-capability authorization. This option is simple and makes first use easy, but it removes administrative control, conflicts with ADR-042's companion-decision requirement for dashboards/reporting, and makes future multi-domain analytics governance harder.

### Option B — dedicated Personal Dashboard capability

Selected. It cleanly separates workspace entitlement from data authorization and Control Tower, preserves least privilege, gives administrators an explicit grant/revoke surface, supports future non-Shipment widgets, and provides one stable contract for APIs and navigation. It adds migration/mapping and testing cost, but that cost is bounded and auditable.

### Option C — reuse an existing generic permission

Rejected because no genuinely generic personal-workspace or analytics-product permission exists in the inspected taxonomy. `oip.*`, reporting, economics, Project configuration, and operational permissions each govern narrower or higher-risk domains. Reusing one would encode accidental coupling.

### Option D — reuse `operational_shipment.read`

Rejected. It is a Shipment data-domain permission and currently also gates Control Tower/Analytics. Using it for dashboard ownership would keep the unwanted dependency, prevent clean support for dashboards containing other data domains, and confuse product entitlement with widget data access. It remains appropriate for Shipment widget execution.

## Role impact

Authority or legacy role names do not grant dashboard capability implicitly. Effective behavior is determined by canonical membership, explicit dashboard permissions, ownership, and underlying data grants.

| Current persona/role | Proposed dashboard entitlement | Dashboard ownership | Underlying data scope | Control Tower dependency |
|---|---|---|---|---|
| Platform Admin | None from authority alone; eligible only with an explicit, unambiguous tenant membership and explicit dashboard grant under a separately approved support policy | Own resources only in that membership | No implicit tenant data; existing domain authorization remains fail-closed | None; Control Tower access does not confer dashboard access |
| Organization Admin | Explicit `personal_dashboard.read/manage`; authority alone is insufficient | Own private resources only | Tenant-wide or narrower data only where the relevant accepted domain policy and permission allow it | None |
| Expert | Explicit `personal_dashboard.read/manage`; default grant approved for active canonical tenant membership | Own private resources only | Assigned-work, Project Access, and domain permissions constrain every widget | None |
| Legacy manager/supervisor/business role | No inference from role label; explicit membership permission required | Own private resources only | Existing explicit domain permissions and scope only | None |
| Active member without dashboard grant | No dashboard navigation or API access | Existing rows remain retained but inaccessible pending grant/authorized disposition | Unchanged | None |
| No membership, inactive membership, or multiple active memberships | Fail closed | None reachable | None | None |

### Proposed default role mapping for owner review

For backward-compatible rollout, propose additive grants of both keys to active, unambiguous tenant memberships that are already in the certified Personal Analytics user cohort: ordinary active `expert` users and tenant-bound Organization Admins. Do not infer grants from legacy `manager`, `supervisor`, `business_expert`, or `admin` names. Platform Admin receives no implicit grant. Existing dashboard owners outside the certified cohort require an evidence-based exception/grant decision; their rows must not be deleted or reassigned.

The Product/Architecture Owner accepted this mapping on 2026-09-07. Migration `20260916_personal_dashboard_permissions` grants the two keys only to active, unambiguous tenant memberships whose active user has canonical `ORGANIZATION_ADMIN` or `EXPERT` authority. It records introduced grants so downgrade removes only permissions introduced by this rollout.

## Control Tower relationship

Control Tower may remain an optional source/template context. A user who has both Control Tower's operational entitlement and `personal_dashboard.manage` may create a personal copy there. A user with Personal Dashboard entitlement but no Control Tower entitlement must still be able to create from the dashboard index through a server-approved template mechanism without entering Control Tower. A user with Control Tower/data access but no dashboard manage entitlement may view Control Tower but cannot create a personal dashboard.

This principle is compatible with the current template catalog and clone service after its authorization gate is separated from `operational_shipment.read` and enforced as `personal_dashboard.manage`. Widget execution continues to require its own data permissions.

`CONTROL_TOWER_AS_OPTIONAL_SOURCE = PASS`. Authenticated browser evidence confirms that a dashboard-only user can create, persist, and reopen a personal dashboard without Control Tower reachability; Shipment query execution remains separately protected.

## Saved View snapshot authorization

- Listing target dashboards requires `personal_dashboard.read` and returns active dashboards owned by the current actor in the canonical tenant.
- Adding a snapshot requires `personal_dashboard.manage` on the target surface.
- The existing source Saved View must remain active, private, tenant-bound, and owned by the current actor under the Saved View contract.
- The target dashboard must remain active, tenant-bound, and owned by the same current actor; client-supplied tenant or owner identity is ignored.
- Expected target version, immutable copied query semantics, and immutable provenance remain unchanged.
- Snapshot creation stores neither results nor an authorization grant. When the widget executes, its copied query is evaluated under the user's live domain permission and business-record scope. Revocation immediately narrows or denies execution.
- If no target exists, the UI may lead an entitled manager to dashboard creation; it must not create one by bypassing `personal_dashboard.manage`.

## Security consequences

The decision adds an explicit least-privilege gate while preserving owner and tenant fences. It prevents Control Tower or Shipment permissions from becoming accidental analytics-workspace grants. Negative tests must prove no metadata disclosure across owner/tenant boundaries and no data widening after a dashboard grant. Server-side enforcement remains authoritative.

## UX consequences

Navigation and `/dashboards` reachability have a deterministic entitlement: `personal_dashboard.read`. Create/edit/lifecycle actions are shown only with `personal_dashboard.manage`. Users without the read grant do not see the entry and receive a non-disclosing denial on direct API/route access. Entitled users do not need Control Tower or a known `public_id`.

## Backend impact

The accepted implementation centralizes capability checks in the dashboard service. Clone authorization uses `personal_dashboard.manage`; list/get use `personal_dashboard.read`; mutation and Saved View snapshot use `personal_dashboard.manage`. Analytics authorization is unchanged, while ownership, expected-version, and provenance rules remain enforced.

## Frontend impact

The accepted implementation adds `/dashboards` and «داشبوردهای من» through the shared operations navigation, with permission-aware loading, error, empty, list, create, open, and edit states. Control Tower clone visibility requires dashboard manage in addition to the operational surface entitlement.

## Migration and role-mapping impact

The existing JSON permission store can hold new keys without a schema-column change, but a new additive, explicitly executed migration or governed reconciliation is required to create the approved default grants consistently across environments and to produce auditable dry-run/apply evidence. No historical migration may be edited. The migration must be idempotent, preserve unknown/custom permissions, avoid role-name inference beyond the approved cohort, report ambiguous/inactive memberships, retain existing dashboards, and support rollback by removing only grants introduced by this rollout.

The exact default cohort and grant authority require owner acceptance. The current local database being behind repository head is not migration evidence and must not be used for mapping decisions.

## Test impact

Acceptance requires backend positive/negative tests for every action, missing/invalid/ambiguous membership, missing read/manage grant, cross-owner, cross-tenant, inactive resources, optimistic concurrency, and Platform Admin fail-closed behavior. It also requires tests proving Shipment widget execution denial/narrowing despite dashboard access; Project-access revocation; Saved View source/target ownership; snapshot provenance; Control Tower and dashboard entitlement independence; frontend navigation/action visibility; and a normal-user browser create, save, leave, navigate back, and reopen journey.

## Backward compatibility

Existing owned dashboard rows and API shapes remain valid. Authorization becomes intentionally stricter: users who relied on membership-only list/get/update or `operational_shipment.read` clone require an approved explicit grant. The rollout therefore needs inventory, cohort mapping, shadow/negative evidence where appropriate, and no destructive data change. Underlying Analytics contracts, Saved View v2 semantics, dashboard definitions, versions, provenance, and Project/Shipment authorization remain unchanged.

## Operational impact

Permission-denial telemetry should distinguish capability denial from ownership/not-found internally without disclosing foreign resources to clients. Rollout should monitor unexpected denials and grant distribution by canonical tenant while avoiding dashboard names, queries, or data in authorization logs.

## Rollback

Application rollback restores the previous product build but must not broaden data authorization. Permission grants introduced by the rollout may be removed only through the governed, auditable rollback path; dashboards and revisions remain intact. If capability evaluation is unavailable or ambiguous, dashboard APIs and navigation fail closed.

## Validation and acceptance prerequisites

Before changing this ADR to ACCEPTED or authorizing implementation, owners must approve:

1. the two-key capability model and implication policy;
2. the default membership cohort and grant/revoke authority;
3. treatment of existing dashboard owners outside that cohort;
4. whether Saved View itself later needs a separate companion entitlement decision; and
5. the migration/reconciliation, rollback, audit, and browser-acceptance evidence plan.

Implementation readiness becomes `YES` only after those decisions are recorded by the authorized owners. Acceptance of this ADR would authorize only the bounded RBAC Foundation slice described by an approved implementation mission; it would not authorize commit, deployment, or production mutation by itself.

## Supersedes / superseded by

- Supersedes: none
- Complements: ADR-042, ADR-043, Semantic Analytics Authorization v1, Saved View → Dashboard Widget Snapshot v1, Project Access Foundation v1
- Superseded by: none

## Status history

- 2026-09-07: PROPOSED — created from the Personal Analytics Product Surface RBAC stop gate; Architecture/Product/Security owner acceptance is required before implementation.
- 2026-09-07: ACCEPTED — the dedicated capability family, canonical cohort mapping, migration strategy, and live-authorization invariant were approved for the bounded Forwarder corrective slice.
- 2026-09-08: QUALIFICATION OPEN — PostgreSQL upgrade/downgrade/re-upgrade evidence passed after correcting migration correlation; authenticated browser evidence remains blocked and therefore Freeze is not authorized.
- 2026-09-08: QUALIFICATION CLOSED — all six authenticated browser journeys passed on disposable PostgreSQL with local Chrome, full frontend/backend regressions passed, and checked-in OpenAPI/Flask/frontend route alignment passed. Semantic Registry metadata is reachable with dashboard-read or Shipment-read capability; Analytics query execution still requires Shipment-read. The bounded corrective slice is ready for a Freeze commit, without authorizing commit, push, deploy, or Production mutation.
