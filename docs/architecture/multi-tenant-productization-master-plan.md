# Forwarderet Multi-Tenant Architecture Discovery and Productization Master Plan

**Status:** Architecture discovery only; no implementation authorized  
**Repository state reviewed:** `aa066a3d4f41ef6ab7031522e878bd4ed369e1e6`  
**Immutable release verified:** annotated tag `v1.9.1` peels to `05414d7d5b17153c3f1efcb5beff0adf7a600af6`  
**Decision:** Shared application, shared PostgreSQL database, shared schema, mandatory organization isolation.  
**Readiness:** **NO — NOT YET PROVEN**

This report is sanitized. It contains no credentials, production data, PII, or customer-confidential values. All findings are based on repository inspection; Production was not accessed.

## A. Initial repository state

The development HEAD exactly matched the expected commit. The existing branch was ahead of its upstream and the worktree already contained unrelated modified/untracked files. Those pre-existing changes were preserved. `docs/architecture/` already existed and was selected for this report. The release tag was not moved, no commit was made, and nothing was pushed.

## B. Agent execution summary

Three independent read-only audits examined: (1) domain/data/auth/RLS/tests; (2) data access/public tracking/domains/branding; and (3) provisioning/storage/async/backup/UX. The primary reviewer independently inspected repository identity and key paths. The findings were consolidated rather than concatenated. A final independent challenge review is recorded in section AJ.

## C. Current Organization architecture

`OperationalOrganization` is a minimal operational-slice model: numeric primary key, globally unique UUID `public_id`, name, active flag, and creation timestamp (`backend/operational_models.py:18-26`). It has no slug, domain, lifecycle reason, portal settings, license, entitlement, owner, or provisioning state. Newer operational aggregates point to it, but most legacy product data does not.

Actual relationship map:

```text
ExpertUser (global identity, global role)
  -> OperationalMembership (organization_id, user_id, active, JSON permissions)
      -> OperationalOrganization
          -> Project -> ExecutionUnit -> OperationalEvent
          -> OperationalShipment -> route/milestone/work-item domains
          -> OIP / MDPM / Economics / tenant catalogs

ShipmentRequest / Customer / legacy CRM / legacy tracking
  -> mostly global or only partially/indirectly connected to the operational organization
```

Organization is required in the newer operational slice but absent or ambiguous in legacy workflows. `is_active` is only an operational status and must not be overloaded as a license state.

## D. Current User/Membership architecture

`ExpertUser` is global, with globally unique username/email and one global role; it has no tenant FK (`backend/models.py:160-188`). `OperationalMembership` is a many-to-many bridge and permits multiple organizations at the database level (`backend/operational_models.py:242-264`). Runtime resolution instead demands exactly one active membership across active organizations and fails with a tenant-scope violation otherwise (`backend/services/operational_service.py:67-88`). There is no tenant selector, switching flow, or tenant claim in the JWT. Multi-membership is structurally possible but operationally unsupported.

## E. Current permission architecture

Two systems coexist:

- Legacy global hierarchical RBAC (`admin > crm_manager > supervisor > business_expert > expert`) is attached to `ExpertUser` (`backend/security.py:190-271`). A global admin is not a company admin.
- Operational permissions are arbitrary strings stored in membership JSON and checked in services (`backend/services/operational_service.py:51-64,91-112`).

There is no normalized tenant-role model, permission catalog/version, grant provenance, explicit platform-admin authority, or company-admin boundary. Frontend route guards are UX only; backend enforcement remains mandatory.

## F. Database tenant coverage

| Entity group | Tenant key | Mode / nullable | Enforcement | Risk |
|---|---|---|---|---|
| Organization, membership | direct `organization_id` on membership | non-null | FK + service resolution | multi-membership runtime gap |
| Project | direct | non-null | FK, org-aware unique, service predicate | comparatively strong |
| OperationalShipment/work/audit/outbox/idempotency | direct | non-null | FKs/constraints + services | app-layer read isolation only |
| OIP, MDPM, economics, tenant cargo/logistics | direct | non-null | composite constraints and service predicates | defense in depth still needed |
| ExecutionUnit/Event, route children, configuration children | indirect through parent | non-null parent | nested service joins | missed-join risk; hard RLS |
| ExpertQuote | `operational_organization_id` | nullable | service-dependent | **CROSS_TENANT_RISK** |
| ShipmentRequest, tracking/log/message/notification | none/indirect | ambiguous | legacy authorization | **CROSS_TENANT_RISK** |
| Customer and CRM entities | none | global | global role/service checks | **CROSS_TENANT_RISK** |
| Case document metadata/audit | indirect through request | no direct tenant | case checks | **CROSS_TENANT_RISK** |
| Global reference catalogs | intentionally none | global | shared catalog contract | safe only if explicitly classified |
| Site settings/branding/uploads | none | global | global admin/public read | cannot represent tenants |

Representative evidence: project constraints (`backend/operational_models.py:58-89`), economics same-tenant FK (`backend/economics_models.py:8-21`), MDPM keys (`backend/mdpm_models.py:9-122`), and legacy request tracking (`backend/models.py:330-338`).

## G. Query/command tenant isolation

The organization scoping strategy is **INCONSISTENT platform-wide**: strong but repeated application-layer scoping in newer operational services, legacy global access elsewhere, and no universal repository/query guard. Positive examples combine resource identity with organization (`backend/services/execution_unit_service.py:50-63`) and issue non-disclosing not-found responses. However, direct ID lookups, globally scoped admin/user/CRM paths, nullable ownership, and public global code lookups remain. No PostgreSQL read-isolation backstop exists.

Classifications:

- New operational authenticated paths: generally `SAFE`, with `DEFENSE_IN_DEPTH_NEEDED`.
- Legacy global administration/CRM/request paths: `UNKNOWN` or `CROSS_TENANT_DEFECT` for a multi-company deployment.
- Public tracking numeric/global lookup: `CROSS_TENANT_DEFECT`.

## H. Public tracking architecture

`GET /api/public/track/<identifier>` is intentionally unauthenticated (`backend/routes/public_tracking.py:21-28`). Numeric input selects `ShipmentRequest.id`; other input globally selects `tracking_code`, with no host or organization predicate (`backend/services/tracking_service.py:9-16`). A second project-public flow globally resolves `Project.tracking_code`. No tenant-domain context participates.

Legacy request codes are generated with about 31 bits from six base-36 characters, with a 24-bit fallback and a predictable ID-derived fallback (`backend/services/shipment_service.py:490-500`). Project codes use UUID4 hex (128 random bits) and are globally unique (`backend/operational_models.py:63-64,82-84`). Neither flow has expiry, rotation, revocation, tracking-access audit, or route-applied rate limiting.

## I. Public tracking security assessment

**Can a tracking code from Tenant B be used through Tenant A context? YES.** If both domains route to this deployment, Host is ignored and a valid code is searched globally. The code acts as a bearer capability for code-based lookup, but legacy numeric-ID lookup means possession of a capability is not even required.

The legacy payload includes database ID, customer name/phone, route/address, cargo/value/instructions, expert contact information, quote information, and dates (`backend/services/tracking_service.py:52-64,121-155`). Existing 404 behavior reveals validity, and no endpoint rate limit was found. Codes occur in path URLs and therefore may enter browser history, proxy/access logs, analytics, and referrers unless explicitly controlled.

Target contract:

```text
verified Host -> active TenantDomain -> tenant public policy
             + normalized high-entropy tracking capability
             -> lookup only by (tenant_id, capability_hash)
             -> explicit versioned public projection
```

Use tenant-scoped uniqueness, while retaining enough entropy that codes are operationally collision-free across the platform. Tenant-scoped uniqueness enforces the trust boundary; global uniqueness may remain as an implementation convenience but must never authorize cross-host lookup. Prefer at least 96–128 random bits, store a keyed hash where practical, support rotation/revocation and optional expiry, apply uniform errors and tenant/IP/capability-aware rate limits, audit attempts without logging plaintext capabilities, set restrictive cache/referrer policies, and never accept numeric IDs. Historical tracking availability must be an explicit policy independent of staff license state.

## J. Staff authentication boundary

Login and JWT identify a global user, not a tenant (`backend/auth.py:21-48`; `backend/security.py:99-185`). Tenant context is later derived server-side from membership, which avoids trusting a client-supplied org but cannot support a legitimate multi-org user. Target: authenticate platform identity, resolve an explicit active tenant from a valid membership (host/session/short-lived tenant context), bind it to every request, and fail closed on missing, inactive, conflicting, or unauthorized context.

## K. Platform Admin gap

No distinct platform-admin model or UI exists. The current global `admin` role and admin-creation tooling are not a safe product boundary. The only organization provisioning path is a CLI that creates a minimal organization and membership (`backend/operational_cli.py:323-330`). Target platform administration needs separately authorized company provisioning, lifecycle, verified domains, license truth, portal configuration, health, audit, and tightly controlled break-glass support; routine platform admins should not browse tenant shipment content.

## L. Company Admin gap

No tenant-scoped company-admin role exists. A future company admin may manage staff, tenant roles/grants, controlled company/portal settings, and invitations only for the resolved tenant. It must not modify platform licensing truth, domain verification, other tenants, or platform-admin identities.

## M. License/entitlement gap

No license/subscription/plan/entitlement enforcement was found. Target concepts must remain separate:

```text
Organization operational status
License (plan/status/effective interval/limits)
Entitlements (versioned feature decisions)
Public portal policy (tracking/request submission/history)
```

All commercial mutations should call a central entitlement decision service; reads and historical public tracking should follow separately configured policy. No billing or pricing belongs in the first implementation.

## N. Tenant URL/domain options

1. A single `forwarderet.com` entry can support an explicit tenant selector/path, but it weakens public brand separation and makes code-only tenant discovery tempting.
2. `alpha.forwarderet.com` is the recommended commercial model after the isolation foundation: wildcard DNS/TLS, trusted proxy Host preservation, canonical lower-case host parsing, verified `TenantDomain` mapping, and unknown-host fail-closed behavior.
3. `tracking.alpha.com` should remain architecture-compatible, not initially implemented. It requires proof-of-control, collision protection, certificate automation/renewal, safe removal, canonical redirects, and anti-host-header poisoning controls.

Current nginx forwards Host (`nginx.conf:61-68`) but uses `server_name localhost`; the backend has CORS origin validation but no tenant Host resolver. Local development should use a reserved test suffix or explicit header accepted only in test/dev.

## O. Public portal/branding architecture

Current site settings are one global key-value namespace and logo uploads are globally stored/served (`backend/routes/site_settings.py:6-63`; `backend/services/settings_service.py:57-102`). Target controlled `OrganizationPortalSettings` should include display name, logo asset, approved color tokens, locale/contact metadata, powered-by policy, and independent portal/tracking/request flags. No arbitrary CSS or tenant HTML. Host-resolved settings must be cache-keyed by tenant/domain and unknown hosts must receive no tenant content.

## P. Documents/storage isolation

Case document metadata has no direct tenant key and storage paths use `{case_id}/{shard}/{uuid}` without a tenant prefix (`backend/models.py:1522-1599`; `backend/services/document_storage_service.py:43-82`). Route checks nest files under a case and storage resolution prevents traversal, but neither metadata nor object namespace independently proves tenant isolation.

P0 requires non-null tenant ownership on metadata/audit, same-tenant constraints, centralized authorization on list/upload/download/delete, opaque tenant-prefixed storage keys, and adversarial tests. P1 adds manifests, scanning/quarantine, retention/legal hold, orphan reconciliation, and coordinated DB/object backup.

## Q. Audit/outbox/background isolation

Operational audit/outbox rows carry non-null organization IDs and producers propagate them (`backend/operational_models.py:1076-1111`; `backend/services/operational_service.py:345-374`). This is a good foundation, but no dispatcher was found and `published_at` is not demonstrably advanced. Legacy document/CRM/console audits and notifications lack direct tenant ownership. No general worker framework or tenant-context contract exists.

Every future event/job must contain immutable tenant ID, actor/system identity, public resource ID, correlation and idempotency keys. Workers must establish tenant context, re-check resource ownership, reject missing/ambiguous context, and partition explicitly privileged platform-wide work per tenant. Add leasing/retries/dead-letter behavior and tenant-scoped observability.

## R. PostgreSQL RLS recommendation

**IMPLEMENT LATER**, after application-layer scoping and non-null ownership are complete. No RLS policies or tenant session setting exist today. Immediate RLS would be unsafe because legacy rows lack ownership, many children are indirect, pooled connections can leak session state, background/admin/reporting paths lack contracts, and migrations/backfills need bypass behavior.

When ready: use transaction-local tenant context (`SET LOCAL`), FORCE RLS for the application role, a separately controlled migration/platform role, explicit policies for every tenant table, pool/transaction reset tests, worker propagation tests, and failure tests for missing context. RLS is defense in depth, never a substitute for service authorization. MT-0 must produce a table-by-table RLS inventory and ADR deciding direct tenant columns versus safe parent-join policy per table. Adoption becomes mandatory when application scoping is complete and before any unreviewed reporting/worker role receives tenant data access; an annually reviewed exception is required to defer it further.

## S. Backup/restore implications

Repository deployment material shows PostgreSQL backup plumbing and requires coordinated database/document backup, but no tenant export/restore tool. Restoring one tenant today is **complex and not practically routine**: ownership is absent/indirect, global identities/catalogs/settings are shared, FK ordering and sequence/ID collisions require remapping, and storage lacks tenant prefixes.

Target operations: encrypted off-site PITR plus versioned object backup; a tenant data manifest; logical export with checksums/schema version; restore into quarantine; referential/tenant validation; controlled merge with ID mapping and audit. Deletion must be staged through suspension, retention/legal-hold review, export, and object/data purge—not broad cascades. Global users shared with other tenants survive; only the target memberships and tenant-bound sessions/capabilities are revoked. Audit retention, legal hold, identity unlinking, and object purge are separate manifest decisions.

## T. Existing tenant-security tests

There are meaningful slice tests for foreign-project non-disclosure, cross-tenant logistics commands, OIP foreign resources, inactive membership, permissions, and PostgreSQL constraints (for example `backend/tests/test_project_configuration.py:169-180,240-311`, `backend/tests/test_oip.py:158-164`, and `backend/tests/test_reporter_permission_postgresql.py:244-259`). Public tests explicitly preserve numeric tracking access (`backend/tests/test_multi_unit_tracking_api.py:114-116`), which is negative security evidence.

## U. Missing adversarial tests

A mandatory tenant-isolation matrix must exercise two tenants, two staff identities, a multi-membership identity, platform identity, and anonymous clients across read/create/update/delete/export/download/selector/public paths. Missing gates include legacy CRM/request/customer/report/user boundaries; A-host+B-code; numeric tracking rejection; rate limit and response-uniformity; rotated/expired/disabled capability; document metadata/object access; notification/audit/outbox/job tenant propagation; tenant switching; license/public-policy combinations; cache keys; unknown/forged Host; RLS/direct SQL; backup/export completeness; and absence of internal fields from public projections.

## V. Target architecture

Choose **A: one application, one release line, shared PostgreSQL, shared schema, mandatory organization isolation**. It best fits the existing operational slice. This is a current ADR decision, not a permanent assumption. Reopen it when regulation/data residency, customer-managed keys, contractual physical isolation, regional placement, noisy-neighbor limits, tenant scale, or tenant-specific RTO/RPO cannot be met economically in the shared tier. The ADR must compare measured fleet-migration, connection, reporting, backup/restore, staffing, and per-tenant infrastructure costs for all three options. Instance-per-tenant is currently least attractive because it multiplies release and operational state.

Core components: `Organization`, `TenantDomain`, `Membership`, tenant roles/grants, request `TenantContext`, scoped repository/service APIs, `License` and entitlement decisions, portal policy/settings, tenant-owned public capabilities, tenant-owned documents/audits/jobs, and later PostgreSQL RLS.

## W. Trust-boundary model

| Boundary | Identity | Tenant resolution | Authorization / allowed data | Fail closed |
|---|---|---|---|---|
| 1 Platform Admin | separate platform authority + strong auth | explicit target tenant for management action | tenant metadata/license/domain/health; content only audited break-glass | no platform grant, no action; no implicit content access |
| 2 Tenant Staff | global user + active membership | verified membership plus explicit active tenant | role/grant and entitlement-scoped tenant operational data | missing/conflicting/inactive membership => deny |
| 3 Public Customer | anonymous + tracking capability | verified Host/domain first | versioned public projection for `(tenant, capability)` only | unknown host/foreign/invalid/disabled => uniform non-disclosing failure |
| 4 Background/System | workload identity + immutable job tenant | envelope tenant, revalidated on execution | one tenant and declared operation; platform jobs explicitly partition | missing tenant or mismatch => reject/dead-letter |
| 5 Database/Storage | least-privilege app/worker roles | transaction context + row/object tenant key | same-tenant rows/objects; later FORCE RLS | missing DB context/invalid prefix => deny |

## X. Data-model gap matrix

| Area | Current state | Target state | Gap / security impact | Complexity | Priority |
|---|---|---|---|---|---|
| Organization | minimal operational row | lifecycle, immutable slug/key | insufficient product identity | M | P0 |
| Membership | bridge + JSON grants; runtime exactly-one | explicit active tenant, tenant roles/grants | ambiguous multi-membership | H | P0 |
| User | global identity + global role | platform identity separated from tenant grants | privilege spillover | H | P0 |
| Role/Permission | global hierarchy + JSON strings | normalized/versioned tenant roles and platform grants | inconsistent enforcement | H | P0/P1 |
| Customer | global legacy | tenant-owned | cross-tenant risk | H | P0 |
| Project | direct tenant | retain, enforce everywhere | RLS/backstop missing | M | P0 |
| Request | global legacy | non-null tenant + same-tenant links | tracking/CRM root gap | H | P0 |
| Quote | nullable tenant | non-null, same tenant as request/project | ambiguous ownership | H | P0 |
| OperationalShipment | direct tenant | retain composite integrity | app-only reads | M | P0 |
| Tracking | global lookup; numeric IDs accepted | tenant+hashed capability and public projection | critical disclosure/IDOR | H | P0 |
| Documents | indirect metadata, unprefixed objects | direct tenant metadata + tenant object prefix | dual-layer leakage/ops risk | H | P0 |
| MDPM | direct tenant | centralized context + later RLS | repeated enforcement | M | P0 |
| Economics/FX | direct tenant in newer slice | centralized context + later RLS | sensitive financial data | M | P0 |
| OIP | direct tenant | centralized context + later RLS | operational intelligence risk | M | P0 |
| Audit | split direct/indirect | immutable direct tenant everywhere | incomplete accountability | M | P0 |
| Outbox | direct tenant, no dispatcher | tenant-safe dispatcher contract | async behavior unproven | M | P1 |
| License | absent | separate effective-dated license | no commercial control | M | P1 |
| Entitlements | absent | centralized decision service | feature leakage/inconsistency | M | P1 |
| Domains | absent | verified tenant-domain mapping | Host cannot establish tenant | M | P1 |
| Portal settings | global | controlled tenant-owned settings/policy | branding/data crossover | M | P1 |

## Y. Tenant-isolation matrix

| Resource | Read | Create | Update | Delete | Public | Tenant key | Current safety | Required change |
|---|---|---|---|---|---|---|---|---|
| Organization/membership | partial CLI/global admin | CLI | partial | cleanup tooling | none | direct | not productized | platform/company admin APIs + audit |
| Customer/CRM | global legacy checks | global | global | global | none | absent | not tenant-safe | add/backfill tenant; scope all paths |
| Request/Quote | legacy/global; quote partial | legacy | legacy | legacy | rich global/numeric lookup | absent/nullable | defect | tenant ownership + same-tenant constraints |
| Project/Units | scoped operational | scoped | scoped | limited | global code lookup | direct/indirect | staff good; public unsafe | central context + host-bound public lookup |
| OperationalShipment/routes | scoped | scoped | scoped | constrained | via projections | direct/indirect | generally safe slice | systematic matrix + later RLS |
| Selectors/catalogs | mix tenant/shared | permissioned | permissioned | permissioned | none | direct or declared global | mixed | formal shared-vs-tenant catalog policy |
| MDPM | scoped | scoped | scoped | scoped | none | direct | good slice, unproven whole matrix | central guard/tests |
| Economics/FX | scoped | scoped | scoped | scoped | none | direct | good slice, high sensitivity | central guard/tests/RLS later |
| OIP | scoped | system/scoped | scoped | constrained | none | direct | good slice | central guard/tests |
| Documents | case authorization | authenticated | authenticated | authenticated | no case files | indirect | not tenant-proven | direct tenant + object prefix + tests |
| Audit/outbox/notifications | mixed | system | append/mark | limited | none | mixed | partial | direct tenant and worker contract |
| Tracking | global | generated | no rotation | no revocation | anonymous | absent from lookup | **critical defect** | tenant+capability, minimize, rate-limit |
| Reports/exports | global/legacy and scoped mix | n/a | n/a | n/a | none | mixed | unproven | tenant-scoped export contract/tests |

## Z. P0 findings

Before a second real company: formal and mechanically enforced tenant inventory; non-null tenant ownership/backfill for all tenant business/security data; eliminate numeric/global public tracking; central immutable request tenant context and scoped service APIs; minimum platform-vs-tenant authority separation (including constraining legacy global-admin endpoints/CLIs); tenant-aware document metadata/object keys; tenant-aware notifications/jobs/events/caches; minimum commercial entitlement enforcement; least-privilege database roles; exhaustive adversarial matrix; migration/rollback and integrity gates. Any unresolved cross-tenant path is a release blocker. Rich company/platform administration UIs remain P1, but their security boundary does not.

## AA. P1 findings

Rich company/platform administration UIs, transactional self-service provisioning, full license/entitlement administration, controlled tenant portal settings, subdomains, production outbox operations, tenant export/retention operations, and commercial operational monitoring.

## AB. P2/P3 findings

P2: custom-domain support, tenant logical restore tooling, RLS defense in depth, advanced audit analytics, automated certificate lifecycle, portability. P3: optional authenticated customer portal, specialized isolation tiers, richer controlled themes. Arbitrary CSS and premature per-tenant infrastructure are not recommended.

## AC. Proposed phased roadmap

Every phase is documentation-only in this mission. Database changes below are proposals, not executed work.

### MT-0 — Architecture Contract (P0)

- **Goal/why:** freeze tenant terminology, ownership inventory, shared-data classifications, trust boundaries, public projection, error semantics, and migration invariants before code diverges.
- **Dependencies:** this report and human decisions.
- **DB/backend/frontend:** no schema; ADRs, repository/API contracts, UI boundary map. Add a checked-in machine-readable manifest covering every model/table; route+verb; repository/service; CLI/job/event; cache; object namespace; export/report/selector/admin search; notification/email link; log/analytics channel; and bulk/direct-ORM path. Each entry records owner, platform/shared/tenant class, enforcement, public projection, retention/export/delete behavior, and tests. CI fails when a new artifact is unclassified.
- **Security/test gates:** approved manifest, adversarial matrix, route/model inventory reconciliation, raw-SQL inventory, and threat model signed off. Global catalogs receive platform-only writers, versioned immutable identifiers, overlay rules, localization/deprecation, and cache invalidation contracts.
- **Rollback:** documentation revision only.
- **Done:** automated inventory reconciliation proves every persisted/served/asynchronous artifact is classified and has an accountable migration owner.

### MT-1 — Tenant Data Integrity Foundation (P0)

- **Goal/why:** make tenant ownership unambiguous and enforce same-tenant relationships.
- **Dependencies:** MT-0; production data profiling in separately authorized work.
- **DB:** execute bounded-domain **expand -> resumable/idempotent backfill -> shadow consistency measurement -> validate -> contract** subphases. Use online/concurrent indexing and `NOT VALID` then controlled validation where supported. Add composite uniques/FKs only after validation. Never infer a default tenant. Quarantine ambiguous rows with business adjudication and deny their use.
- **Backend/frontend:** version-compatible writes and read precedence; instrument divergence; explicit deployment order; block quarantined operations; no broad all-domain flag day.
- **Security/test gates:** zero unexplained orphan/divergent rows; adjudicated quarantine count and policy; quote/request/customer deduplication checks; document-object reconciliation; cross-tenant FK attempts fail; lock/capacity/time estimates and backup/restore rehearsal.
- **Rollback:** named rollback point at each bounded-domain subphase; additive state retained until old writers are retired; reconciliation can resume safely after partial deployment. Freeze new-tenant onboarding throughout.
- **Done:** each bounded domain independently has proven ownership, constraints, consistency SLOs, and signed contract cutover.

### MT-2 — Central Tenant Context / Scoping (P0)

- **Goal/why:** replace repeated/manual scoping with mandatory fail-closed context and scoped repositories.
- **Dependencies:** MT-1.
- **DB:** context/audit support as needed; no RLS yet.
- **Backend:** resolver, scoped query/command APIs, explicit platform operations, multi-membership selection. The authenticated tenant is selected only from server-validated membership, bound to the session/access token and an immutable request context; Host may constrain but never elevate it. Header/body/path tenant IDs cannot override context. Revalidate membership/org status and revoke/age out sessions after membership changes.
- **Frontend:** tenant indicator/switcher only for valid memberships; CSRF-protected switching; defined concurrent-tab and stale-token behavior; route boundary separation.
- **Security/test gates:** A/B CRUD/selector/export matrix; missing/conflicting context denied; self-escalation, cross-tenant/platform grant, last-admin, stale-session, confused-deputy and switch-CSRF tests. Break-glass requires named approval, reason, short expiry, content scope, and immutable audit.
- **Rollback:** feature-gated adapters while old paths are retired; cannot roll back after second tenant without re-isolation review.
- **Done:** no tenant resource service accepts an unscoped identifier.

### MT-2A — Authority and Database Privilege Baseline (P0)

- **Goal/why:** remove global-admin spillover and broad database bypass before a second tenant.
- **Dependencies:** MT-0/2.
- **DB/backend/frontend:** separate minimum platform authority from tenant-admin grants; constrain/retire every legacy global admin endpoint and CLI; introduce least-privilege app, worker, reporting and migration roles. The app role is never superuser, schema/table owner, or `BYPASSRLS`; raw SQL is allowlisted/reviewed. Rich admin UIs remain later phases.
- **Security/test gates:** endpoint/CLI privilege matrix; grant inspection in CI; platform permissions cannot be assigned by tenant admins; platform support has no routine tenant content access.
- **Rollback:** emergency recovery uses a separately controlled, audited operator role; never restore global app-admin spillover.
- **Done:** platform and tenant authority are enforced at backend and DB boundaries.

### MT-2B — Documents, Async, Notifications and Cache Isolation (P0)

- **Goal/why:** close non-HTTP and dual-layer leakage paths before onboarding.
- **Dependencies:** MT-1/2.
- **DB/storage:** tenant key/backfill and same-tenant constraints on document/audit/notification metadata; migrate objects to opaque tenant-prefixed keys with manifests, checksums, orphan reconciliation and reversible copy-then-switch.
- **Backend:** central tenant authorization for upload/list/download/delete and any signed URL; immutable tenant in job/event/notification envelopes; worker context validation; tenant partitioning; leases/retries/dead-letter; tenant-keyed caches and invalidation.
- **Frontend:** no direct storage key; tenant-safe notification and download links.
- **Security/test gates:** A/B object, signed-link, recipient, retry/DLQ, cache poisoning and orphan tests. Define `Vary`/cache keys, `Referrer-Policy`, no-store rules and sanitized edge/app logs.
- **Rollback:** retain old objects read-only until manifest reconciliation; replay only tenant-validated envelopes.
- **Done:** metadata and objects independently enforce tenant ownership; no async/cache path can lose tenant context.

### MT-3 — Public Tracking Tenant Isolation (P0)

- **Goal/why:** remove the present anonymous cross-tenant/IDOR defect while preserving passwordless tracking.
- **Dependencies:** MT-1/2 and public projection contract. P0 uses a canonical verified platform host plus an opaque, non-enumerable tenant route/portal identifier resolved before the capability; code-only tenant discovery is forbidden. Trusted forwarded-host values are accepted only from configured proxies. MT-8 later adds subdomains without changing the contract.
- **DB:** tenant-owned capability records/hash, state, rotation/revocation/optional expiry, access audit.
- **Backend:** reject numeric IDs; `(tenant, capability)` lookup; minimized projection; externally non-disclosing/timing-controlled failure; rate/cache/log protections. Issue high-entropy replacements for legacy/predictable codes, provide a bounded tenant-safe compatibility resolver, communicate migration, revoke old codes, and set a removal date. Canonical redirects never reveal tenant existence.
- **Frontend:** host-aware code entry, safe error, no sensitive URL persistence where avoidable.
- **Security/test gates:** A-host+B-code, brute force, cache, logs, old/rotated/disabled codes, field allowlist.
- **Rollback:** temporary dual-code mapping behind tenant-safe resolver; never re-enable numeric lookup.
- **Done:** anonymous access is impossible without both valid tenant context and capability.

### MT-3A — Minimum Commercial Entitlement Gate (P0 for commercial launch)

- **Goal/why:** a second-tenant security pilot may run only under an explicit audited all-features policy; any commercial tenant requires enforceable rights.
- **Dependencies:** MT-2A.
- **DB/backend/frontend:** minimum effective-dated license/entitlement decision record and backend mutation gate; absent/invalid/expired decision fails closed for commercial actions. Public historical tracking policy remains independent.
- **Security/test gates:** clock-boundary/time-zone tests, cache invalidation, audited support override expiry, race-safe quota accounting where a quota is enabled; entitlements can never grant data authorization.
- **Rollback:** audited emergency policy with bounded expiry; never silently default to enabled.
- **Done:** commercial actions have a deterministic entitlement decision; richer administration remains MT-6.

### MT-4 — Company Administration (P1)

- **Goal/why:** tenant admins manage staff/settings without platform privilege.
- **Dependencies:** MT-2.
- **DB/backend/frontend:** tenant roles/grants/invitations; company-admin APIs and shell.
- **Security/test gates:** self-escalation, last-admin, cross-tenant invite/grant tests.
- **Rollback:** preserve grants; disable UI/API feature gate.
- **Done:** company admin lifecycle is tenant-contained and audited.

### MT-5 — Platform Administration (P1)

- **Goal/why:** safe provisioning and tenant lifecycle from a distinct authority.
- **Dependencies:** MT-1/2/4.
- **DB/backend/frontend:** platform grants, provisioning state/idempotency/audit; company/domain/health UI.
- **Security/test gates:** no routine content access; break-glass approval/audit; transactional provisioning tests.
- **Rollback:** retain CLI recovery path and idempotent reconciliation.
- **Done:** a tenant and initial admin can be provisioned consistently without global-admin leakage.

### MT-6 — License / Entitlement Foundation (P1)

- **Goal/why:** separate commercial rights from org health and public history.
- **Dependencies:** MT-5.
- **DB/backend/frontend:** effective-dated license and entitlement records; central decision service; status presentation.
- **Security/test gates:** expired/suspended/entitled matrix; checks at backend mutation boundaries.
- **Rollback:** default policy explicitly versioned; emergency override audited.
- **Done:** staff commercial actions and public tracking follow independent policies.

### MT-7 — Tenant Public Portal / Branding (P1)

- **Goal/why:** controlled tenant presentation without arbitrary executable styling.
- **Dependencies:** MT-3/5.
- **DB/backend/frontend:** tenant portal settings/assets/policies; tenant-keyed caches and branded shell.
- **Security/test gates:** asset ownership, XSS/content policy, cache separation, safe defaults.
- **Rollback:** Forwarderet default theme.
- **Done:** each tenant sees only its approved portal data and assets.

### MT-8 — Subdomain Resolution (P1)

- **Goal/why:** `tenant.forwarderet.com` establishes public tenant context.
- **Dependencies:** MT-3/7 and infrastructure authorization.
- **DB/backend/frontend:** verified domain mapping; trusted Host middleware; canonical links.
- **Security/test gates:** unknown/forged Host, proxy chain, wildcard TLS/DNS, cache/CORS tests.
- **Rollback:** shared canonical domain with explicit safe tenant path.
- **Done:** wildcard subdomains resolve deterministically and unknown hosts fail closed.

### MT-9 — Custom Domain Readiness (P2)

- **Goal/why:** preserve enterprise compatibility without premature launch.
- **Dependencies:** MT-8.
- **DB/backend/frontend:** domain verification/certificate states; canonical-domain behavior.
- **Security/test gates:** ownership takeover, stale mapping, certificate renewal/removal.
- **Rollback:** disable custom mapping and redirect to platform subdomain.
- **Done:** design and APIs are ready; production enablement remains separate.

### MT-10 — PostgreSQL RLS Defense in Depth (P2)

- **Goal/why:** contain missed application predicates.
- **Dependencies:** complete non-null ownership, MT-2, tenant-safe jobs/admin/reporting.
- **DB:** policies/FORCE RLS, transaction-local tenant setting, separate privileged roles.
- **Backend/frontend:** transaction context integration; no UI change.
- **Security/test gates:** direct SQL, pool reuse, missing context, worker, migration/bypass tests.
- **Rollback:** staged table-by-table policies with incident plan; never disable without release gate.
- **Done:** all tenant tables deny reads/writes without valid context and app checks remain.

### MT-11 — Tenant Isolation Browser/Security Acceptance (P0 release gate)

- **Goal/why:** prove end-to-end isolation, not merely unit intent.
- **Dependencies:** MT-1 through MT-8 as applicable.
- **DB/backend/frontend:** test fixtures/instrumentation only.
- **Security/test gates:** full matrix across API/browser/download/cache/export/public/roles; automated negative suite.
- **Rollback:** failed gate blocks onboarding; no bypass.
- **Done:** signed evidence shows Tenant A cannot access Tenant B by any supported channel.

### MT-12 — Multi-Tenant Production Hardening (P1)

- **Goal/why:** operationally safe commercial launch.
- **Dependencies:** MT-11.
- **DB/backend/frontend:** PITR/object backups, quotas, monitoring, tenant-aware support/runbooks, retention/export/deletion controls.
- **Security/test gates:** restore rehearsal, failover, capacity, incident and suspension/license drills.
- **Rollback:** tenant onboarding freeze, per-tenant suspension, release rollback with schema compatibility.
- **Done:** second-tenant launch checklist and operational evidence are approved.

## AD. Recommended first implementation slice

**MT-0 objective:** “Define and approve the authoritative tenant architecture contract: classify every persisted model, endpoint, file object, cache, event, and job as platform/shared/tenant-owned; specify tenant resolution and fail-closed authorization for platform admin, tenant staff, public tracking, background work, and database/storage; define the tenant-isolation test matrix and migration invariants, without changing runtime behavior.”

Do this first. It prevents unsafe piecemeal columns and establishes acceptance criteria for MT-1 through MT-3.

## AE. Architecture artifact path

`docs/architecture/multi-tenant-productization-master-plan.md`

## AF. Files changed

Only this new documentation artifact was created. No product code, migrations, schemas, permissions, runtime configuration, release files, or deployment assets were modified by this mission.

## AG. Git state

No commit, tag movement, branch change, push, or deployment. The worktree had pre-existing unrelated changes; they were left intact.

## AH. v1.9.1 integrity confirmation

The annotated `v1.9.1` tag peeled to the expected published release commit `05414d7d5b17153c3f1efcb5beff0adf7a600af6`. The tag was not changed.

## AI. Production untouched confirmation

Production was not accessed. No Production credentials or values were inspected. No DNS, IIS, TLS, database, deployment, or external service action occurred.

## AJ. Independent architecture review

**ARCHITECTURE REVIEW — PASS**

The first independent challenge returned revision-required findings around P0 authority separation, documents/async/cache isolation, tenant bootstrap for public tracking, commercial entitlement gating, migration safety, enforceable inventory, tenant-context escalation, and database privileges. The roadmap was revised with MT-2A, MT-2B, MT-3A and strengthened MT-0 through MT-3 contracts. The reviewer then confirmed that all eight plan-level blockers were addressed. This pass validates the proposed plan, not the current runtime: readiness remains NO until implementation and signed MT-11/MT-12 evidence.

## AK. Multi-company readiness answer

If we onboard Company B tomorrow using the current codebase, is Forwarderet provably safe for multi-company production?

**NO — NOT YET PROVEN**

## AL. Final classification

**MULTI-TENANT ARCHITECTURE DISCOVERY COMPLETE — READY FOR HUMAN ROADMAP APPROVAL**
