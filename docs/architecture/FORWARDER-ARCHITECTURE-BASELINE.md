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
    │   └── RequestCargoItem 0..N (optional commercial Cargo information)
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
| Platform vocabulary | Platform: `DocumentDefinition`, `CargoType`, `UnitOfMeasure`, `PackagingType`, `TransportMeansType`, `TransportEquipmentType`, governed shared types and approved platform catalogs |
| Organization reference availability | Organization: explicit tenant-owned activation of central Cargo Type, UOM, Packaging Type, Transport Means Type and Transport Equipment Type under ADR-056; activation does not copy or own the platform definition |
| Organization configuration/master data | Organization: `OrganizationDocumentRequirement`, `CargoCatalogItem`, `LogisticsPoint`, memberships and organization policies |
| Project configuration | Project: services, `ProjectDocumentRequirement`, milestones, ordered `ProjectLogisticsPoint` associations |
| Commercial request | `ShipmentRequest`: intake, quote/referral lineage, legacy compatibility fields |
| Request Cargo | `ShipmentRequest` owns implemented `RequestCargoItem` children; `0..N`, optional for submission, no mandatory Cargo field under PDR-019 |
| Shipment execution | `OperationalShipment` |
| Shipment responsible Expert | `OperationalShipment`: exactly one fixed responsible Transport Expert under ADR-047; Request assignment does not mutate it |
| Independent execution | `ExecutionUnit` |
| Uploaded document binary metadata | `CaseDocumentFile`, owned by its source `ShipmentRequest`; contextual use is separate |
| Shipment document use/readiness | `OperationalDocumentRequirement` plus `ArtifactAssociation` and assessments |
| Document management entitlement | Authoritative Shipment/Case parent; owning active Transport Expert only under PDR-020/ADR-050 |
| Document version/history | System-owned immutable file/version lineage, private bytes, and audit; initiating Expert is not the history owner |
| Cargo master | Organization-owned `CargoCatalogItem` |
| Shipment cargo truth | `ShipmentCargoItem` immutable descriptive snapshot plus mutable controlled quantity/version |
| CRM | Organization-scoped internal `Customer`, contacts, opportunities, activities and link audit |
| Logistics place master | Platform-owned `GlobalLogisticsPoint` governance; tenant-owned `OrganizationGlobalLogisticsPointAdoption`; optional explicit organization-owned `LogisticsPoint` materialization; current organization `LogisticsPoint`-based project/tracking consumption; platform-owned `LogisticsPointType` (ADR-041; catalog population and legacy reconciliation remain separately controlled) |
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

PDR-020 and ADR-050 establish the implemented bounded management contract without activating ADR-020's generalized visibility model:

- only the active owning Transport Expert may upload, append, target one current file for replacement, or retry a known failed upload;
- Customer, Admin/Manager, other same-Organization Expert, other tenant, and inactive/revoked actor cannot manage files;
- existing separately governed read/history/download or Admin/Manager oversight may remain read-only; no Customer visibility is newly granted;
- one logical requirement may contain multiple current physical files, but append is not replace and file count is not readiness;
- replacement creates a new governed version, preserves the old immutable version/history, and does not inherit assessment under ADR-030;
- authority derives from the persisted parent and never from client-supplied tenant/owner, generic Organization membership, or a standalone attachment permission;
- ADR-047 remains authoritative: there is one fixed Shipment owner and no Expert reassignment/former-Expert document transfer model.

The qualified bounded implementation provides multiple current operational associations, targeted replacement lineage, immutable version history, and known-failure retry outcome. Generalized visibility, retention/purge, unknown-outcome exactly-once recovery, and enterprise DMS expansion remain separately governed; this baseline grants no Production migration or deployment authority.

## 9. Cargo architecture

```text
ShipmentRequest -> 0..N RequestCargoItem (commercial, optional)

CargoCatalogItem -> ShipmentCargoItem -> OperationalShipment (operational)
```

- Request Cargo and Shipment Cargo are different concepts and owners. Customer submission is valid with zero Request Cargo Items and no Cargo field is currently mandatory.
- Customer intake does not decide Shipment count, Cargo allocation, Execution Units, vehicles/containers, or Route Legs.
- Catalog items are organization-owned reusable master data, not transactional truth.
- Shipment cargo lines snapshot catalog identity and descriptive fields so later catalog edits do not rewrite history.
- A manual shipment line may exist without a catalog item but still uses governed CargoType and UOM.
- ADR-056 makes central CargoType and UOM availability explicit per organization. The authenticated internal Cargo options projection returns only active central definitions with active tenant activations; there is no global-active compatibility fallback on that governed Expert path.
- `PackagingType`, `TransportMeansType`, and `TransportEquipmentType` are explicit empty-capable platform catalogs with tenant-owned activation foundations. P3-01 does not add them to Cargo, Route, Execution Unit, or another operational record.
- Public Request Cargo options and validation remain unchanged by P3-01. Legacy `TransportMethod` remains the Request/intake and specialization compatibility catalog and is not reinterpreted as `TransportMeansType`.
- Cross-tenant catalog selection is rejected.
- No direct cargo allocation to `ExecutionUnit` currently exists. ADR-023 is PROPOSED; allocation must not be inferred or implemented until accepted.

## 10. Logistics and location architecture

`LogisticsPoint` is the future governed organization location master and `ProjectLogisticsPoint` is project configuration. `CanonicalLocation` remains the accepted route-facing bridge/snapshot abstraction from ADR-005. These roles are complementary.

`TrackingLocationReference` is a legacy platform tracking selector. It is not an alias of `LogisticsPoint`; new runtime dependence on it requires explicit authorization. Convergence needs an Accepted ADR covering tenant ownership, mapping, historical snapshots, free text, API compatibility, and rollback.

ADR-041 accepts a platform-owned `GlobalLogisticsPoint` and tenant-owned adoption boundary without changing tenant master ownership. The local implementation includes the empty platform schema/read boundary, Platform-Admin governance, tenant-owned `OrganizationGlobalLogisticsPointAdoption`, explicit optional materialization into a non-null tenant-owned `LogisticsPoint`, and certified current project/tracking consumption through existing `LogisticsPoint` identities and snapshots. Direct operational references to `GlobalLogisticsPoint` remain prohibited. Catalog population, existing-point linking, and reviewed legacy reconciliation remain separately controlled; the 64 legacy tracking rows are not a seed and are not mapped by name.

## 11. CRM architecture

CRM is an internal, database-backed, organization-scoped subsystem. It is not an external CRM integration. `ShipmentRequest.customer_id` links commercial intake to the internal CRM customer; `OperationalShipment.customer_id` is execution customer identity under ADR-034. Link/relink/unlink operations are audited. Access is currently role-gated through the backend role hierarchy; an external connector or fine-grained permission redesign requires an ADR.

## 12. Assignment and referral architecture

> **ADR-047 implemented contract:** Request assignment/referral remains commercial workflow. Operational Shipment ownership is a separate immutable Shipment-owned relation established at creation. No Shipment Expert reassignment/transfer/replacement workflow is approved. The statements below describe Request assignment behavior unless explicitly qualified.

- Assignment is tenant-fenced: request, candidate expert membership, rule, state, and logs remain within one organization.
- Direct assignment and rule pools validate runtime eligibility.
- Rule `round_robin` uses per-rule state; rule `least_workload` uses active-assignment count; an optional maximum workload filters candidates.
- The tenant-safe fallback uses oldest last-assignment/time-based round-robin and does not use the displayed workload metric.
- Displayed `ExpertUser.get_workload()` counts assigned and in-progress requests. It is not a universal workload definition.
- Changing included statuses, weights, fallback selection, or authority is an architecture/behavior decision requiring explicit approval and tests.

For Operational Shipment access, the owning active Transport Expert may act within entitlement/state; another same-organization Expert is denied by default and gains nothing through membership or later Request assignment; other tenants and inactive/revoked actors are denied. Same-organization Admin/Manager oversight remains action-specific and tenant-scoped. Accepted-Quote creation captures the issuing Expert as fixed owner; Direct creation validates one fixed responsible Expert. Application mutation and the database write-once invariant prevent owner transfer.

## 13. API, migration, audit, and reference-data gates

- New mutation endpoints require an authorized actor, tenant scope, stable errors, and idempotency/expected version where retries or concurrency matter.
- Cross-domain commands go through services; routes do not create hidden ownership.
- New migrations are additive, preserve a sole Alembic head, include downgrade/rollback policy, and never run at import/startup.
- Master/reference data uses explicit domain tables. Catalog import, when used, is versioned, checksummed, planned, explicitly applied, conflict-aware, transactional, and audited.
- Administrator-managed creation remains valid under ADR-028; a catalog is not a hidden deployment prerequisite.
- ADR-056 installation creates no central values and no organization activations. `CargoType`, UOM, Packaging, Means, and Equipment activation state belongs to the server-derived organization; Platform Admin authority over the central catalog grants no tenant mutation authority.
- Organization-specific reference definitions and promotion remain stopped on `DN08`; no local-definition or promotion route is part of the baseline.

## 14. Enforcement

Every Codex implementation task follows `CODEX-DEVELOPMENT-GATE.md`. Reviews use `ARCHITECTURE-REVIEW-CHECKLIST.md`. Automated checks enforce only reliable structural invariants; all other decisions remain explicit manual review gates.
