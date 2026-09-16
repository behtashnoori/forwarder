# Forwarder Architecture Baseline

Status: ACCEPTED governance baseline for Forwarder v1.9.5.1
Authority: repository implementation plus Accepted ADRs indexed in `ADR-INDEX.md`

## 1. Product architecture principles

1. Forwarder is a modular monolith with explicit domain boundaries and one deployable application. Service extraction requires an Accepted ADR and operational evidence.
2. Commercial intent, operational execution, configuration, master data, evidence, audit, and projections are distinct concerns.
3. New work extends canonical aggregates. Compatibility code does not become canonical merely because it remains active.
4. Writes are explicit, authorized, tenant-scoped, auditable, idempotent where retry-sensitive, and concurrency-safe.
5. Migrations are additive and explicitly executed. Startup never migrates or seeds.
6. Historical facts are corrected by append/supersession where the domain requires history; master-data changes do not rewrite transactional snapshots.
7. Public APIs use opaque identities. Sequential database IDs never authorize access.
8. Unknown data remains unknown. Code must not invent tenant ownership, timezone, location, cargo allocation, customer identity, or document scope.

## 2. Mandatory architecture change rule

No implementation may silently change architecture. Development must stop, propose an ADR, obtain acceptance, and only then implement when work requires any of the following:

- new aggregate ownership or a changed canonical model;
- crossing or weakening a tenant boundary;
- a timestamp/storage/display contract change;
- document or cargo ownership change;
- a new master-data authority;
- changed API authority semantics;
- migration of functionality from a legacy model to a canonical model;
- destructive history/schema behavior or a new cross-domain write.

An implementation prompt is not itself ADR acceptance unless it explicitly accepts a named ADR decision.

## 3. Canonical domain hierarchy

ADR-017, ADR-018, and the implemented models establish:

```text
OperationalOrganization
└── Project
    ├── ShipmentRequest 0..N (commercial lineage, not execution)
    └── OperationalShipment 0..N (execution aggregate)
        └── ExecutionUnit 0..N (independently managed unit)
```

The intended operational path is `Project -> OperationalShipment -> ExecutionUnit`. `OperationalShipment` also owns route planning, milestones, operational document readiness, cargo lines, economics, exceptions, and work items within their accepted boundaries. Legacy and direct-operation compatibility can leave `project_id` or commercial lineage absent where an Accepted ADR permits it; that exception does not redefine the hierarchy.

## 4. Legacy compatibility path

`ShipmentRequest`, `ShipmentTracking`, `ShipmentTransportUnit`, `ShipmentTransportUnitUpdate`, and `TrackingLocationReference` remain supported compatibility models.

- New features MUST NOT target a legacy model unless an Accepted ADR explicitly authorizes that choice.
- A bridge or mapping must name source identity, canonical identity, tenant ownership, historical semantics, and failure behavior.
- No compatibility projection may write canonical truth back into a legacy aggregate implicitly.
- No legacy model may be removed before expand/migrate/verify/switch/contract gates pass.
- Existing behavior must not be “cleaned up” under a governance-only change.

See `LEGACY-CANONICAL-MAP.md`.

## 5. Tenant architecture

- Every organization-owned runtime query and mutation is scoped by the authoritative organization context.
- Organization ownership comes from authenticated membership, trusted hostname binding, or an already-authorized parent—not from body/query `organization_id`.
- Client-supplied organization identifiers are ignored or rejected; they never broaden scope.
- Cross-tenant assignments, catalog references, document associations, project links, and parent/child references fail closed.
- Public/platform authority and organization-admin authority are separate. Platform master-data mutation requires platform authority; tenant configuration requires organization authority.
- Organization hostname matching uses normalized exact hostnames, one active hostname binding per hostname, an active organization, and no request-body override.
- Ambiguous legacy ownership is quarantined and excluded from ordinary runtime access. Certification-only bypasses must be explicit and unavailable to product requests.
- Authorization is checked in the backend. Frontend visibility is not an authority boundary.

## 6. Data ownership

| Data | Canonical owner |
| --- | --- |
| Platform vocabulary | Platform: `DocumentDefinition`, governed shared types and approved platform catalogs |
| Organization configuration/master data | Organization: `OrganizationDocumentRequirement`, `CargoCatalogItem`, `LogisticsPoint`, memberships and organization policies |
| Project configuration | Project: services, `ProjectDocumentRequirement`, milestones, ordered `ProjectLogisticsPoint` associations |
| Commercial request | `ShipmentRequest`: intake, quote/referral lineage, legacy compatibility fields |
| Shipment execution | `OperationalShipment` |
| Independent execution | `ExecutionUnit` |
| Uploaded document binary metadata | `CaseDocumentFile`, owned by its source `ShipmentRequest`; contextual use is separate |
| Shipment document use/readiness | `OperationalDocumentRequirement` plus `ArtifactAssociation` and assessments |
| Cargo master | Organization-owned `CargoCatalogItem` |
| Shipment cargo truth | `ShipmentCargoItem` immutable descriptive snapshot plus mutable controlled quantity/version |
| CRM | Organization-scoped internal `Customer`, contacts, opportunities, activities and link audit |
| Logistics place master | Platform-owned `GlobalLogisticsPoint` Phase 1 empty catalog/read API; target tenant-owned `OrganizationGlobalLogisticsPoint` adoption; organization-owned `LogisticsPoint`; platform-owned `LogisticsPointType` (ADR-041; adoption/population pending) |
| Route location identity/history | `CanonicalLocation` bridge plus immutable location snapshots |
| Operational tracking/history | `OperationalEvent` and specialized event/audit models under their Accepted ADRs |

## 7. Time and timezone contract

- Real events are timezone-aware UTC Instants in Python.
- New Instant columns use `DateTime(timezone=True)` and PostgreSQL `timestamp with time zone` (`timestamptz`).
- API Instants are RFC 3339 strings ending in `Z` or carrying an explicit numeric offset.
- Browser `datetime-local` values are interpreted once in the declared browser/business timezone and converted once to UTC. Display converts an explicit Instant to the selected display timezone.
- Local Dates remain `DATE`/`YYYY-MM-DD` and are not converted through UTC midnight.
- Business local datetimes require wall-clock value, IANA timezone, owner/location, and an explicit resolution policy.
- `occurred_at` and `recorded_at` remain separate where late reporting matters.
- A proven UTC value MUST NOT be serialized without an offset. Offset-less serialization of proven UTC is prohibited.
- Legacy naive columns are not presumed UTC or local globally. Each column needs a proven source contract, explicit serializer, reversible migration plan, reconciliation, and rollback rehearsal.

ADR-016 and `time/time-data-type-guide.md` remain authoritative.

## 8. Document architecture

```text
DocumentDefinition                  platform vocabulary/file policy
├── OrganizationDocumentRequirement tenant applicability
├── ProjectDocumentRequirement      project configuration
└── CaseDocumentRequirement         request policy snapshot
    └── CaseDocumentFile            immutable uploaded-file version metadata

Project/organization policy
└── OperationalDocumentRequirement  shipment runtime snapshot
    └── ArtifactAssociation         exact CaseDocumentFile version use
        └── DocumentAssessment      append-oriented review/approval/verification
```

Requirements are not files. Upload is not approval. Configuration changes do not rewrite materialized shipment requirements. Files remain private and tenant-safe. An artifact association must match the operational shipment's organization, source request, definition, active typed version, and exact version rules.

There is currently no direct `ExecutionUnit` document ownership. Adding it requires an Accepted ADR; ADR-020 remains PROPOSED and MDPM explicitly excluded ExecutionUnit documents.

## 9. Cargo architecture

```text
CargoCatalogItem -> ShipmentCargoItem -> OperationalShipment
```

- Catalog items are organization-owned reusable master data, not transactional truth.
- Shipment cargo lines snapshot catalog identity and descriptive fields so later catalog edits do not rewrite history.
- A manual shipment line may exist without a catalog item but still uses governed CargoType and UOM.
- Cross-tenant catalog selection is rejected.
- No direct cargo allocation to `ExecutionUnit` currently exists. ADR-023 is PROPOSED; allocation must not be inferred or implemented until accepted.

## 10. Logistics and location architecture

`LogisticsPoint` is the future governed organization location master and `ProjectLogisticsPoint` is project configuration. `CanonicalLocation` remains the accepted route-facing bridge/snapshot abstraction from ADR-005. These roles are complementary.

`TrackingLocationReference` remains a legacy compatibility authority and is not
an alias of `LogisticsPoint`. Accepted ADR-035 governs the implemented expert
tracking selector and immutable tenant-point snapshots. New selection uses the
existing `logistics_point.read` permission and active authenticated organization
membership; the write rechecks that permission and unit/point tenant equality
through Logistics Network's `resolve_tracking_point` query contract. Public
tracking consumes only allowlisted historical snapshots, not the private catalog.

FWD-02 makes the bounded selector's pagination visible (`q`, `country_code`,
`type_code`, `limit` 1–100, `offset`; response `items`, `limit`, `offset`,
`has_more`). Errors remain explicit; client organization overrides are forbidden.
Geography request selectors retain Country/InternationalCity identity, show
UN/LOCODE and untranslated fallback names, and persist IDs through the existing
Commercial contract. An inactive country cannot offer newly selectable places;
old request and tracking references remain readable. No schema, map coordinates,
canonical tracking cutover or authority change is introduced.

General Geography imports remain optional under ADR-028. FWD-02's checksummed
UN/LOCODE 2025-1 profile covers all 249 published countries/territories and 115,208
unique locations worldwide (including 154 IR, 5,799 IT and 1,142 NO); it has no
country or transport-function shortlist. Approved/recognized and credible national
legacy statuses are preserved with source metadata; deletion and unverified or
unrecognized statuses are excluded. This is trade-location coverage, not a census
of every settlement or a service guarantee. New names retain untranslated source
spelling. Multi-function locations remain one identity, not fabricated facilities.

The public request form uses an opt-in paged projection of the existing geography
endpoint (`paged=1`, `q`, `country_id`, `limit` 1–100, `offset`; `items`, `has_more`,
`limit`, `offset`). Country is mandatory. Name/code search and 50-row pages avoid
loading entire national directories; the legacy array response remains compatible.
Selected identities survive search/pages and reset on country changes.

`international_geography_catalog` plans and applies only missing stable identities
into the existing tables, records `ReferenceDataSeedRun` evidence, refuses ambiguous
unbound historical same-name mappings and cross-country codes, and never
reactivates, renames or deletes existing records. Different source codes may share
a name; a name is not identity. Historical unbound seed rows require explicit
identity review before an optional import, not silent auto-binding. Existing v1
input and historical migrations remain unchanged. See FWD-02 evidence for exact
source eligibility, reproducibility, import procedures and recovery.

ADR-041 accepts a platform-owned `GlobalLogisticsPoint` and tenant-owned adoption
boundary without changing current tenant master ownership. Its implementation
status is tracked in ADR-INDEX; FWD-02 does not extend adoption or operational
consumption. `LogisticsPoint` remains non-null tenant-owned, whether materialized
under approved adoption or an organization-only facility. The legacy tracking
rows and China–Iran atlas are not geography seeds for this slice.

## 11. CRM architecture

CRM is an internal, database-backed, organization-scoped subsystem. It is not an external CRM integration. `ShipmentRequest.customer_id` links commercial intake to the internal CRM customer; `OperationalShipment.customer_id` is execution customer identity under ADR-034. Link/relink/unlink operations are audited. Access is currently role-gated through the backend role hierarchy; an external connector or fine-grained permission redesign requires an ADR.

## 12. Assignment and referral architecture

- Assignment is tenant-fenced: request, candidate expert membership, rule, state, and logs remain within one organization.
- Direct assignment and rule pools validate runtime eligibility.
- Rule `round_robin` uses per-rule state; rule `least_workload` uses active-assignment count; an optional maximum workload filters candidates.
- The tenant-safe fallback uses oldest last-assignment/time-based round-robin and does not use the displayed workload metric.
- Displayed `ExpertUser.get_workload()` counts assigned and in-progress requests. It is not a universal workload definition.
- Changing included statuses, weights, fallback selection, or authority is an architecture/behavior decision requiring explicit approval and tests.

## 13. API, migration, audit, and reference-data gates

- New mutation endpoints require an authorized actor, tenant scope, stable errors, and idempotency/expected version where retries or concurrency matter.
- Cross-domain commands go through services; routes do not create hidden ownership.
- New migrations are additive, preserve a sole Alembic head, include downgrade/rollback policy, and never run at import/startup.
- Master/reference data uses explicit domain tables. Catalog import, when used, is versioned, checksummed, planned, explicitly applied, conflict-aware, transactional, and audited.
- Administrator-managed creation remains valid under ADR-028; a catalog is not a hidden deployment prerequisite.

## 14. Enforcement

Every Codex implementation task follows `CODEX-DEVELOPMENT-GATE.md`. Reviews use `ARCHITECTURE-REVIEW-CHECKLIST.md`. Automated checks enforce only reliable structural invariants; all other decisions remain explicit manual review gates.

## 15. Notification and controlled action foundation (ADR-045)

Commercial owns valid quote/request transitions. `commercial.quote.available.v1`
is recorded through the public outbox service in the same local transaction;
an event uniqueness constraint is scoped to this event family. Existing outbox
families retain their semantics. The single quote consumer marks only this
event family published, atomically with its durable notification action.

Notification/Action owns intent, fixed versioned policy, short dispatch claims,
attempts, results, bounded retries and reconciliation. Provider adapters own
communication. An integration failure never rolls back committed Commercial
state. UNKNOWN requires reconciliation and old attempts cannot overwrite newer
ones. No exactly-once delivery guarantee is made.

ADR-045 authorizes only EMAIL simulation on explicit qualification configuration
and synthetic destinations. Public command adapters derive authenticated actor
context; the background worker uses the originating event's limited policy
delegation, revalidated against current authority, membership, assignment,
quote state and certified recipient linkage. No generic agent/workflow engine,
real provider, Production activation or new customer journey is authorized.

See [ADR-045](../operational/adr/ADR-045-notification-action-foundation.md) for
ownership, dispatch ordering, compatibility, migration and recovery contracts.

## 16. Commercial request transport intent (ADR-046, bounded FWD-03)

`ShipmentRequest.transport_intent` is a nullable versioned JSON value owned by
Commercial. Version 1 stores ordered `steps` containing road/rail/air/sea modes;
repetition, including adjacent repetition, is meaningful and retained. One
distinct mode is single-mode; two or more is combined. This preliminary customer
wish creates no RouteLeg, execution plan, feasibility approval or service promise.

The public v2 request endpoint uses server-selected validation: customer_choice
requires nonempty intent; forwarder_suggestion may remain null. The legacy endpoint
retains scalar compatibility without inferring order across historical scopes.
Both final-create paths reject blank cargo. The read-only prepare endpoint uses
the same Commercial normalization/projection and grants no submission authority;
submission repeats validation and trusted-host tenant resolution. Body organization
IDs do not convey ownership. Existing tracking capability is unchanged and does
not become authenticated customer ownership.

Commercial's shared projection is used by customer tracking, expert list/detail
and admin reads. Intent takes precedence; scoped legacy values remain readable.
Combined intent is never synthesized into a scalar, and the response explicitly
marks its display limitation for old clients. Known catalog aliases produce one
new selectable mode with retained catalog IDs. Unknown historical strings are
displayed verbatim; unknown catalog semantics are not inferred.

There is no request cargo/transport editor in this baseline. Narrow existing
mutations preserve intent; attempted transport changes through the status endpoint
are rejected explicitly. No new edit authority/state transition is granted.
Expert KPI counts use the list's assigned-work scope and common non-status filters.

Additive revision `20260916_fwd03_transport_intent` follows the verified sole head
`20260916_fwd01_notifications`. No backfill, startup migration or catalog import is
introduced. PostgreSQL downgrade locks the request table and refuses before DDL
when any non-null intent exists. Application rollback retains schema and intent.
Mother LPAF reference impact: NONE; global v2.2 and limited v2.4 pilot status stay
unchanged. See ADR-046 and its FWD-03 evidence for compatibility and qualification.

## 17. Governed quotation response (ADR-047/PDR-019 amended FWD-05)

ADR-047/PDR-019 are ACCEPTED as explicitly amended by the named Owner continuation
2026-09-16. The original proposal/discovery remains preserved in FWD-05 evidence;
acceptance is development authority, not implementation/qualification evidence.
Commercial extends ExpertQuote with quote-major.v1 money strings (EUR/USD major
units <=2 decimals, IRR integral rial), immutable identity/content, explicit effective
replacement chain and append-only response facts/receipts. Historical money values/
codes remain uninterpreted legacy evidence. Request status and quote response are
independent; no automatic operational/financial effects follow acceptance.

Authorization owns exact recipient/tenant/request/quote/content bounded possession
grants; tracking GET stays read-only and tracking POST loses write authority. The
retained Security review/technical feasibility gate precedes protected Build.
Accepted predecessor cannot be ordinarily replaced; declined/negotiating predecessor
replacement is explicit and serialized with response. Organization Admin configures
an audited issuer-validity IANA zone through existing settings. Missing source
blocks publication. Policy/Local Date/zone/resolved UTC deadline are immutable
quote snapshots; receipt time is system authority. Grant reads end at later
publication/expiry+30 days; reissue revokes prior grant without extending horizon.

Existing outbox/inbox/Notification contracts are reused; Commercial response event
is separate from quote.available. Adapter owns private fake payload transport;
worker has no commercial/customer authority. Current expert sees truthful readiness/
BLOCKED reason and owns follow-up. No manufactured verification, staff capability
fetch, arbitrary recipient or invented onboarding remediation route is allowed.

The external D:\1-webapp\28-AI-Rules reference remains unavailable. Owner explicitly
defers access only for FWD-05 pilot; REFERENCE_MAPPING=NOT_PROVEN. Unknown content
and alternate-folder mapping are unapproved. Recovery/review is required at FWD-05
end or before actual release, whichever earlier. See limited reference disposition
in FWD-05 evidence. No folder 28/29 rename/rewrite or unread-rule compliance claim.

Mother LPAF impact NONE: v2.2 globally ACTIVE, v2.4 OWNER_APPROVED /
PILOT_ADOPTION_ALLOWED / NOT_GLOBAL_ACTIVE; mother unchanged. Project impact
UPDATE_REQUIRED: reconciled ADR/PDR and indexes/baseline updated here. Protected
runtime, migration, PostgreSQL, Browser UAT and regression remain unqualified.

## 18. FWD-06 pre-build tracking decision checkpoint (2026-09-16)

The current RequestDetail intake targets the compatibility chain
ShipmentRequest/ShipmentTracking/ShipmentTransportUnit/ShipmentTransportUnitUpdate,
not canonical ExecutionUnit/OperationalEvent. Its operator-entered unit_code is
not the canonical system-generated U-code. Current canonical owners and the
ADR-040 public cohort/lineage gates are unchanged.

[ADR-048](../operational/adr/ADR-048-bounded-legacy-tracking-timeline.md) is PROPOSED,
not Accepted: it requests bounded legacy feature authority, internal timeline,
explicit recorded-time customer allowlist and governed command receipt reuse.
No proposed runtime change is implemented. Ordinary existing label/validation/
error fixes do not themselves require a parallel ADR; this pending gate concerns
the additional legacy capability, receipt contract and public visibility scope.

The explicit FWD-06 mission continues the missing-reference deferral only for
local FWD-06 development/qualification. See the new
[disposition](../operational/evidence/fwd-06-tracking-timeline/REFERENCE-28-DISPOSITION.md).
The exact path28 is unavailable; mapping NOT_PROVEN. This neither rewrites the
FWD-05 record nor waives this independent architecture gate. Review remains due
at FWD-06 end or before actual release, whichever earlier.

Mother LPAF unchanged: v2.2 GLOBAL_ACTIVE; v2.4 limited owner-approved pilot only,
expected current SHA256/re-attestation verified. Engineering/Product completion
and FWD-06 runtime/UAT gates are NOT_COMPLETE, not inherited from FWD-05 PASS.

## FWD-06 bounded acceptance continuation — 2026-09-16

ADR-048 is now ACCEPTED_FOR_BOUNDED_FWD06 by explicit Owner acceptance of proposal SHA256 A3FFFEAA2C364B5073410B67ACD1943DC22139CB1895809F9E2F4A5956875FD3. Earlier PROPOSED/pre-build entries above are historical checkpoints. The unchanged eight-point decision authorizes only the bounded compatibility tracking slice and local qualification. Implementation PASS remains pending. Current owner: multi_unit_tracking_service; subject: ShipmentTransportUnit; permitted contracts: existing assigned expert read/write, public visible snapshot allowlist plus recorded times, limited OperationalIdempotency command receipts. Canonical ownership/cutover, schema/history migration, correction, real release and Production are excluded. Review at FWD-06 end/before actual release; no next-mission extension. Future canonical lineage/cohort migration remains a dependency. Mother LPAF impact NONE; project contract impact UPDATE_REQUIRED within this slice. Reference28 mapping NOT_PROVEN; existing bounded deferral retained without security waiver.
