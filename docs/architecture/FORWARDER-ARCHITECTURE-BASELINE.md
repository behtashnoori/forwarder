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
| Logistics place master | Organization-owned `LogisticsPoint`; platform-owned `LogisticsPointType` |
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

`TrackingLocationReference` is a legacy platform tracking selector. It is not an alias of `LogisticsPoint`; new runtime dependence on it requires explicit authorization. Convergence needs an Accepted ADR covering tenant ownership, mapping, historical snapshots, free text, API compatibility, and rollback.

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
