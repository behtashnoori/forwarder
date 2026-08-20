# ADR-039: External Operational Reference Architecture

- Status: ACCEPTED
- Date: 2026-08-20
- Owners: Architecture, Operations, Security, Transport domain stewardship
- Affected domain: operational shipments, execution units, documents, search, reference data

## Context

Forwarder has stable internal identities (`public_id`), customer tracking (`tracking_code`), document definitions, file versions, and operational document readiness. It has no governed model for external operational identifiers such as bill-of-lading, airway-bill, CMR, customs, warehouse, or external-system references. `DocumentDefinition.reference_number_label_fa/en` is presentation metadata, not a stored value. ADR-036 explicitly separates a document type from its number and reserves this decision.

The repository census and candidate evidence are recorded in `docs/architecture/EXTERNAL-REFERENCE-DOMAIN-MAP.md`. It proves the need for architecture but not one universal owner, cardinality, or global uniqueness rule. Barfarabaran semantics remain unverified.

## Problem

Forwarder needs tenant-safe display and search of external references without turning `DocumentDefinition` into operational storage, overloading public/internal identities, or creating an unconstrained EAV/polymorphic table. The decision must preserve referential integrity, history, document evidence, and bounded owners.

## Decision

Adopt a hybrid architecture: a governed platform `ExternalReferenceType` vocabulary plus owner-specific value tables. V1 authorizes only `OperationalShipmentExternalReference` and `ExecutionUnitExternalReference`. Each has a real owner FK and organization FK; the service verifies that the owner belongs to the same authoritative organization. There is no `owner_type TEXT/owner_id` pair.

### Type model

`ExternalReferenceType` is an explicit platform reference-data table, not an enum and not part of `DocumentDefinition`. It has immutable opaque identity and stable uppercase code; Persian/English names; description; allowed V1 owner applicability; issuer/source-authority description; format/normalization hint; search policy (`EXACT`, `PREFIX`, `DISPLAY_ONLY`, `NONE`); uniqueness policy (`NONE`, `OWNER`, `TENANT`, `ISSUER`); masking/display policy; provenance/review status; active/deprecated lifecycle; revision; and audit metadata.

Platform authority governs types under ADR-021/028 mechanics. Tenant users cannot redefine codes, normalization, applicability, or uniqueness. Type activation requires provenance, named domain approval, compatible owner applicability, tested normalization, and a non-ambiguous uniqueness rule. An empty or partially active vocabulary is valid. This catalog describes external references and must not duplicate document families, file policy, requirements, or document lifecycle.

### Value model and owners

Both owner-specific tables share a contract implemented explicitly rather than through EAV:

- immutable UUID v4 `public_id`, internal numeric PK, `organization_id`, concrete owner FK, and `external_reference_type_id`;
- original `display_value` and deterministic `normalized_value`; raw values are never rewritten merely because normalization changes;
- issuer/source-system metadata, optional issuer-scoped key, issued/effective timestamps only when proven applicable, source method, lifecycle state (`ACTIVE`, `SUPERSEDED`, `CANCELLED`), reason, version, and actor/timestamps;
- optional link to one exact `CaseDocumentFile` version through a separate tenant-checked association, not a second owner and not required for non-document references;
- a self-reference or explicit predecessor relation for correction/reissue/supersession; values are append-oriented and hard deletion is prohibited after use.

Only one active equivalent row per owner/type/normalized value is allowed. Additional uniqueness follows the active type policy and is enforced with PostgreSQL constraints/indexes where expressible plus transaction-safe service validation. No type defaults to global uniqueness. `ISSUER` scope includes a governed issuer key; unknown issuer cannot satisfy that policy.

V1 owners are `OperationalShipment` and `ExecutionUnit`. The latter inherits organization and shipment/project lineage. `ShipmentRequest`, Project, `ShipmentCargoItem`, `CaseDocumentFile`, document requirements, and arbitrary entities are not V1 owners. Project/search navigation is derived through the shipment/unit relationship. Adding an owner requires a later Accepted ADR or explicit ADR-039 amendment with FK, tenant, lifecycle, query, and migration evidence.

### Candidate disposition

- B/L, AWB, and CMR types may be activated in V1 only after governed type provenance and format/uniqueness review. Their values allow multiple rows and correction by supersession.
- Cotage and warehouse-receipt types may be present only as inactive candidates until authoritative owner, issuer, cardinality, and lifecycle confirmation.
- Registration-order number is excluded because it likely belongs to a structured trade-authorization domain and may need status, validity, amendments, and commodity coverage beyond a reference value.
- `BARFARABARAN_REFERENCE` remains `DOMAIN_CONFIRMATION_REQUIRED`, inactive, unseeded, and outside implementation scope.

### Document bridge

`BILL_OF_LADING` is a document definition; `BILL_OF_LADING_NUMBER` is a reference type. The same distinction applies to AWB, CMR, warehouse receipt, customs declaration/Cotage, and registration order. A value may link to an exact authorized `CaseDocumentFile` version when that file evidences it. The reference remains owned by its operational owner and the association must prove same tenant, compatible definition/type mapping, and exact version. Upload, association, or document approval never creates or validates a reference automatically. A reference never satisfies a document requirement by itself.

### Search, security, and exposure

Search is internal, tenant-first, authorized, bounded, paginated, and type-policy controlled. Exact normalized search is the default eligible mode; prefix search requires explicit type enablement, minimum length, caps, and rate limiting. Indexes begin with `organization_id` and type, followed by normalized value and active state as appropriate. Search results expose owner opaque identities, never numeric keys, and derive project navigation without making Project an owner.

The authoritative organization comes from authenticated membership or an already-authorized owner. Client `organization_id` is ignored/rejected and never establishes authority. Possession of a value, row `public_id`, document, or request `public_id` grants no access. Missing, foreign, and unauthorized references return non-enumerating outcomes. Raw values are excluded from default logs, telemetry, URLs, and audit summaries; approved keyed fingerprints may support abuse/correlation with retention policy.

External references are not publicly exposed and do not enter customer tracking by default. A later Accepted decision must name each type, projection, audience, masking, authorization, and abuse controls before exposure. Internal display may be masked per type/role. Mutation requires authorized tenant role, owner access, expected version, reason for supersession/cancellation, idempotency for retry-sensitive commands, and audit.

## Alternatives

1. **One generic polymorphic table.** Flexible and searchable, but `owner_type/owner_id` loses database FKs, cascades, tenant proof, and safe joins. Rejected as an EAV-like ambiguity boundary.
2. **Owner-specific typed tables without a type catalog.** Strong FKs and simple ORM, but duplicates type labels, normalization, lifecycle, and search policy across owners. Rejected as ungoverned and costly to extend.
3. **Document-instance-only number fields.** Strong document proximity, but cannot represent non-document system references, shipment search projections, several documents/reissues, or references before upload. Rejected.
4. **Selected hybrid.** Governed types plus two explicit owner tables and an optional exact-file association. It retains FK/tenant integrity and shared governance at the cost of duplicated value-table mechanics and explicit union/search services.

## Consequences

The architecture supports bilingual governed types, bounded owners, exact tenant-safe search, multiple values, and preserved correction history without confusing documents or identities. Costs include two tables and parallel constraints/services, catalog stewardship, normalization versioning, type activation review, union queries, and an explicit amendment for every new owner.

It intentionally does not model customs declarations, warehouse custody, trade authorizations, issuer masters, or Barfarabaran semantics. Those may later become specialist aggregates that link to or supersede simple reference use.

## Compatibility

Existing `tracking_code`, all `public_id` fields, numeric keys, `ShipmentTransportUnit.vehicle_reference`, document catalog metadata, document files, requirements, associations, and APIs remain unchanged. No existing free text is reclassified or backfilled without evidence. Legacy values are never guessed from filenames, labels, notes, tracking identities, or unit codes.

## Migration impact

No migration is created or executed by this ADR. A later implementation uses additive migrations from the then-current sole head: type table first, then the two owner tables, lifecycle/audit relations, constraints, and indexes. It creates no catalog rows in schema migration. Optional catalog apply is separately planned/checksummed/audited under ADR-028. Backfill begins with a read-only census; only proven values with proven tenant/owner/type mapping may be imported. Ambiguous values remain untouched/quarantined. Rollout is expand, optional controlled populate, verify, shadow search, cohort write/read, and separately authorized compatibility cleanup.

## Security/tenant impact

Every value is organization-owned and redundantly fenced to its owner. Composite constraints or service locks prove owner organization before insert/update and reject cross-tenant document links. Global administrative catalog authority grants no tenant-value access. Search authorization occurs before value comparison/results, responses do not reveal foreign existence, and raw sensitive values are minimized in logs/audit. Reference values never authorize or establish tenant context.

## Operational impact

There is no current runtime/deployment effect. Future search must measure query plans and index selectivity on PostgreSQL, cap prefix results, and monitor privacy-safe latency/outcome counts. Type deprecation blocks new values but preserves historical reads. A type-policy change cannot silently reinterpret existing normalized values or uniqueness; it requires conflict planning and revisioned rollout.

## Rollback

Application rollback disables new write/search surfaces and returns to existing shipment/unit/document views while retaining reference values, type identities, audit, and associations. Catalog deactivation blocks creation without deleting history. After adoption, schema downgrade must not drop referenced values; destructive contraction requires a separate decision, export/reconciliation evidence, and consumer retirement.

## Validation

A later implementation must prove sole-head upgrade/downgrade/re-upgrade on PostgreSQL and SQLite compatibility; concrete owner FK and same-tenant constraints; type applicability; normalization and collision behavior; uniqueness policies; append/supersede concurrency and idempotency; exact-file tenant/version/type compatibility; cross-tenant and non-enumerating negative cases; search caps/rate limits/query plans; audit/log redaction; no public/customer exposure; no confusion with tracking/public/internal identities; no automatic document readiness effect; N/N-1 compatibility; architecture governance; ADR index; `git diff --check`; and changed-scope secret scan.

## Explicit implementation boundary

This acceptance authorizes a later controlled V1 implementation goal to design and implement only the governed type table, the two concrete owner value tables, optional exact-file association, audit/history, internal exact/prefix search, and required migrations/tests. Initial active types are limited to provenance-approved B/L, AWB, and CMR. It does not authorize Cotage or warehouse values before confirmation; registration-order or Barfarabaran implementation; request/project/cargo/document ownership; a generic owner; catalog seed/apply; public/customer exposure; runtime work in this goal; production access; migration execution; deployment; release; or push.

## Supersedes / superseded by

- Supersedes: none
- Superseded by: none
- Extends: ADR-018, ADR-021, ADR-028, ADR-030, and ADR-036 without changing their existing authority

## Status history

- 2026-08-20: ACCEPTED — architecture and security boundaries are complete; unresolved candidates are safely inactive or excluded and do not block the bounded B/L, AWB, and CMR V1.
