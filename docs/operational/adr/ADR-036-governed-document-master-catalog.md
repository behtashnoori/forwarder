# ADR-036: Governed Document Master Catalog Metadata and Catalog Lifecycle

- Status: ACCEPTED
- Date: 2026-08-20
- Owners: Product, Architecture, Data, Operations, and Security
- Affected domain: Platform document vocabulary, document policy, reference-data governance
- Implementation state: Architecture accepted; no runtime, migration, or catalog package is created by this decision

## Context

`DocumentDefinition` is the platform-global governed document vocabulary and file-policy record. Existing organization, project, request, and operational models consume that identity for different purposes. The completed Document Master Catalog design and domain-resolution reviews identified a need for bilingual terminology, classification, applicability, aliases, provenance, and a controlled activation lifecycle without turning the catalog into a requirement engine or rewriting historical evidence.

ADR-021 and ADR-028 require explicit domain models, administrator-managed reference data, and a valid empty-catalog state. ADR-006 and ADR-011 require additive, explicitly executed migration. ADR-030 preserves the distinction between definition, configured requirement, runtime snapshot, exact artifact version, assessment, and readiness. This ADR extends those decisions and does not supersede them.

## Problem

The current `DocumentDefinition` shape has a stable code, opaque public identity, one title, description, legacy requirement default, file-policy fields, a coarse applicability scope, activation, ordering, revision, and audit attribution. It cannot faithfully represent the governed catalog metadata and evidence needed for a bilingual, multi-jurisdiction, multi-mode catalog.

The architecture must permit catalog candidates to be reviewed and deferred independently of production activation. It must also prevent catalog enrichment or optional package application from changing tenant policy, requirement snapshots, uploaded files, approval state, or external operational references.

## Decision

### 1. Canonical document chain and authority

The canonical chain remains:

```text
DocumentDefinition
├── OrganizationDocumentRequirement
├── ProjectDocumentRequirement
└── CaseDocumentRequirement
    └── CaseDocumentFile

Organization/project policy
└── OperationalDocumentRequirement
    └── ArtifactAssociation
        └── exact CaseDocumentFile version
```

`DocumentDefinition` is tenant-neutral platform vocabulary. It is not a file, uploaded artifact, requirement instance, approval, readiness result, operational status, or structured external authorization. Catalog presence and catalog activation create no requirement, snapshot, association, assessment, workflow action, or status transition.

Platform-authorized administration controls canonical identity and catalog metadata. Organization authority controls only organization policy. Project authority controls project overrides. Shipment materialization and exact-file use remain governed by ADR-030. Backend authorization is authoritative independently of UI visibility.

### 2. Additive `DocumentDefinition` metadata

The target model supports the following governed metadata in addition to the existing record:

- immutable normalized `code` and existing opaque `public_id`;
- `name_fa` and `name_en`;
- one controlled `family`;
- governed `description`;
- optional bilingual reference-number labels;
- `expiry_applicability` as a controlled value, initially `NOT_APPLICABLE`, `OPTIONAL`, or `APPLICABLE`;
- `organization_policy_overridable`, defaulting to allowed for existing definitions;
- a catalog lifecycle state and a distinct source-review status;
- normalized aliases and normalized jurisdiction, transport-mode, process-stage, business-scope, and provenance associations.

`organization_policy_overridable` is a policy capability flag, not a requirement value. A restricted definition does not become required, applicable, or materialized merely because it is restricted. Future enforcement must reject unauthorized tenant-policy mutation and preserve existing effective-policy behavior; activation of a restricted definition is blocked until conflicts with existing tenant policies have been planned and resolved explicitly.

### 3. Compatibility treatment of existing fields

Existing production semantics are retained:

- `title` remains the legacy display label and compatibility fallback. New readers may prefer the requested locale-specific name and fall back to `title`; migration may not guess translations.
- `description` retains its current meaning and may become the canonical governed description without rewriting historical snapshots.
- `is_required` remains only the existing compatibility-fallback default described by organization document policy. It is not catalog activation and is not reinterpreted as universal requirement policy.
- `allowed_formats`, `max_file_size_bytes`, `max_active_file_count`, and `sort_order` retain their file-policy/display semantics.
- `is_active` remains the compatibility-facing activation projection during additive adoption. The new lifecycle is authoritative only after an accepted implementation defines a safe dual-read/switch plan; the two values must not be allowed to contradict silently.
- `applicability_scope` retains the legacy `all`/`domestic`/`international` contract during transition. Normalized jurisdiction applicability is the target; no existing row is inferred or rewritten from the coarse value without reviewed mapping evidence.
- `revision`, actor attribution, and timestamps remain. Future metadata writes participate in revision/concurrency and audit controls.

No field is removed, renamed, or repurposed by this ADR. A later contract phase may deprecate redundant compatibility columns only after N/N-1 consumers, data reconciliation, rollback, and historical behavior are proven.

### 4. Controlled document family

Family is a required, bounded classification vocabulary with this starting set:

`COMMERCIAL`, `TRANSPORT`, `FORWARDING`, `CUSTOMS`, `WAREHOUSE`, `RELEASE`, `CERTIFICATE`, `PERMIT_AUTHORIZATION`, `INSURANCE`, `FINANCE`, `SAFETY`, and `OPERATIONAL_NOTICE`.

Family codes are platform-governed and immutable. A future addition requires catalog governance. Family is for navigation, search, reporting, and review only; it is not a workflow, permission, authorization, approval, ownership, or automatic-requirement boundary.

### 5. Governed bilingual aliases

Aliases use a normalized child relation to `DocumentDefinition`, with the original display value, normalized search value, language/script tag where known, lifecycle/audit metadata, and parent identity. An alias is tenant-neutral terminology and never creates another definition.

Normalization is deterministic and Unicode-aware, including trim, case folding where applicable, whitespace normalization, and an explicitly versioned punctuation policy. Normalization must preserve meaningful distinctions and must not rely on lossy transliteration.

Within the active platform catalog, one normalized alias may resolve to exactly one `DocumentDefinition`. An alias must not collide with another definition's code or active normalized alias. A canonical code match takes precedence only for lookup; it does not permit a conflicting alias to be stored. Ambiguous candidates fail closed and require steward resolution. No migration or catalog apply automatically merges definitions, changes foreign keys, or remaps historical records based on aliases.

### 6. Jurisdiction applicability

Jurisdiction is a normalized many-to-many applicability model, not a two-value Iran/international column and not tenant ownership. It supports:

- global applicability;
- international or cross-border applicability;
- one or more country jurisdictions using the existing governed country reference where safe; and
- jurisdiction-specific provenance and definitions.

The relation must prevent duplicate logical associations and validate referenced country identities. A definition with no reviewed normalized jurisdiction remains unknown/unclassified during transition; absence must not be interpreted as global. The legacy `applicability_scope` remains available until explicit reconciliation and switch gates pass.

### 7. Transport-mode applicability

Transport mode is normalized many-to-many applicability. It reuses existing governed transport-mode/reference identity when that identity and lifecycle are compatible; implementation must not create a competing vocabulary. The model supports `ROAD`, `SEA`, `AIR`, `RAIL`, `MULTIMODAL`, and an explicit `MODE_INDEPENDENT` applicability marker.

`WAREHOUSE` and `CUSTOMS` are not transport modes. They belong to family and/or process-stage classification. No mode tag drives routing, workflow, requirement generation, or authorization.

### 8. Process-stage applicability

Process stage is a controlled many-to-many catalog classification starting with `PRE_SHIPMENT`, `BOOKING`, `ORIGIN`, `IN_TRANSIT`, `ARRIVAL`, `WAREHOUSE`, `CUSTOMS_DECLARATION`, `CUSTOMS_CLEARANCE`, `RELEASE`, `DELIVERY`, and `POST_DELIVERY`.

These tags support discovery and policy authoring only. They do not execute workflow, create transitions, materialize requirements, determine readiness, or infer customs/banking state.

### 9. Business-scope applicability

Business scope is a controlled many-to-many descriptive classification starting with `REQUEST`, `PROJECT`, `OPERATIONAL_SHIPMENT`, `CARGO`, and `MULTIPLE`.

Business applicability is not technical ownership. This ADR does not authorize `ExecutionUnit` document ownership. If `EXECUTION_UNIT` is later introduced as a discovery tag, it must be explicitly marked non-owning until a separate Accepted ADR defines ownership, association, authorization, migration, and exact-version semantics.

### 10. Provenance and review status

Each platform catalog definition must have one or more normalized provenance records before activation. A provenance record identifies source authority, source reference/title, optional safe locator, source version or publication/effective date, jurisdiction, reviewer, review timestamp, and review notes. It stores citations and metadata, not copies of external source documents or sensitive payloads.

Source review status is distinct from catalog lifecycle and preserves these meanings:

- `VERIFIED`: authoritative evidence and its applicability were independently verified under the review policy;
- `SOURCE_CONFIRMED`: a named authoritative source confirms the definition, but the review has not claimed the stronger verified level;
- `SOURCE_CONFIRMATION_REQUIRED`: the proposed source or exact authoritative evidence is incomplete;
- `DOMAIN_CONFIRMATION_REQUIRED`: documentary/domain meaning or placement still requires a named subject-matter decision.

Status changes require actor, reason, evidence reference, timestamp, and revision control. Only `VERIFIED` or `SOURCE_CONFIRMED` may satisfy the source gate for activation. Jurisdiction-specific activation additionally requires evidence applicable to every activated jurisdiction; one country's source cannot silently authorize another.

### 11. Catalog lifecycle and activation gate

Catalog lifecycle is separate from source review and uses:

`DRAFT` → `REVIEWED` → `SOURCE_CONFIRMED` → `ACTIVE` → `DEPRECATED`.

`SOURCE_CONFIRMED` in this lifecycle means the definition has passed its required provenance gate; it does not collapse the finer review-status distinction above. Transitions are explicit, permission-controlled, revision-checked, and audited. Skipping forward states is prohibited. Correction returns a non-active row to the appropriate review state. Deprecation preserves identity and references; codes are never reused and rows are not hard-deleted.

Activation requires, at minimum, valid canonical code, bilingual names, family, file-policy compatibility, non-ambiguous aliases, explicit applicability classification, sufficient provenance, an eligible review status, no policy conflict, and a named actor/reason. Failure leaves the row non-active. Candidate/design data may exist outside the production catalog or as non-active governed rows, but incomplete candidates may not become active automatically.

For compatibility during migration, an implementation must define one authoritative lifecycle projection at each rollout phase and fail closed on disagreement with legacy `is_active`. This ADR itself changes no active state.

### 12. Preserved catalog-row decisions

The domain-resolution decisions are preserved as catalog-review inputs, not seed authorization:

- Keep generic fallbacks: `RAIL_CONSIGNMENT_NOTE`, `FREIGHT_MANIFEST`, `CONTAINER_MANIFEST`, `CUSTOMS_DECLARATION`, and `PAYMENT_CONFIRMATION`.
- Treat `REGISTRATION_ORDER` and `STATISTICAL_REGISTRATION` as possible evidence definitions only when provenance is confirmed; their structured domains remain future work.
- Rename candidates before publication: `WAREHOUSE_RELEASE` to `IRAN_CARRIER_RELEASE`, `RELEASE_ORDER` to `CONTAINER_RELEASE_ORDER`, and `DELIVERY_NOTICE` to `GOODS_DELIVERY_NOTICE`.
- Exclude the universal `QUARANTINE_CERTIFICATE` umbrella and the broad `BANKING_IMPORT_DOCUMENT` definition.
- Defer `GATE_PASS`.
- Retain `PROOF_OF_DELIVERY`, `REMITTANCE_ADVICE`, and `SWIFT_PAYMENT_MESSAGE` only as future candidates subject to product/domain evidence.

Unresolved Iran-specific definitions, unconfirmed finance subtypes, `GATE_PASS`, and `BARFARABARAN_REFERENCE` may remain excluded indefinitely without blocking this architecture. `BARFARABARAN_REFERENCE` remains outside `DocumentDefinition`. No row is created or activated by this ADR.

### 13. External-reference and structured-domain boundary

Document identity is not an external operational reference. In particular, a B/L, AWB, CMR, warehouse receipt, registration-order evidence artifact, customs declaration, payment confirmation, gate-pass artifact, or container release order is not its number, identifier, transaction/status, QR/access token, or release reference.

ADR-036 introduces no generic `ExternalReference` owner, lifecycle, or API. That requires separate architecture authority.

`REGISTRATION_ORDER` and `STATISTICAL_REGISTRATION` may later identify evidence artifact types. This does not authorize their number, authority, status, validity, amendments, commodity coverage, payment/FX linkage, or external-system identity. Artifact evidence and structured authorization remain distinct.

### 14. Tenant-policy and UI boundary

Platform catalog records and aliases are tenant-neutral. An organization cannot redefine canonical code, identity, family, aliases, provenance, or lifecycle. Organization-specific relevance, requirement level, conditions, and notes belong to `OrganizationDocumentRequirement` or an explicitly accepted organization-policy extension. Project overrides remain project-owned. Configuration changes affect only later snapshots under existing policy; they do not rewrite current shipments or files.

Platform Admin UI may manage governed vocabulary metadata. Organization Admin UI may manage organization policy only. A platform administrator does not implicitly receive tenant context, and an organization administrator does not receive platform-catalog mutation authority.

### 15. Governed catalog package and apply

A future optional Document Master Catalog package follows ADR-021/028 and existing reference-data mechanics. It uses a strict, schema-validated, non-executable format with schema version, catalog version, source version, deterministically ordered content, and a SHA-256 checksum over canonical content excluding the checksum field.

`plan` is read-only and reports create, unchanged, conflict, excluded/deferred, and invalid counts. Normal `apply` is transactional, additive, and idempotent: absent approved identities may be created; exact matches are no-ops; any governed-field drift, inactive/deprecated identity, alias ambiguity, missing relation, provenance failure, or duplicate identity aborts all writes. Normal apply has no update, rename, deactivate, delete, merge, or policy-write mode. Such changes require a separately approved change mode and reconciliation record.

Apply requires explicit confirmation, expected checksum, environment, named operator, approval reference, and platform authority. Production additionally requires the repository-standard explicit production confirmation and separate execution authorization. Startup, application import, health checks, release validation, and Alembic migrations never apply catalog data. An empty catalog remains valid. Package application never writes organization/project policy or creates runtime requirements.

### 16. Audit and idempotency

Catalog metadata mutations record actor, authority scope, action, target public identity, old/new revision or safe diff, reason, correlation/idempotency identity, timestamp, and result. Retry-sensitive writes use request-hash idempotency and expected revision/optimistic concurrency consistent with ADR-010.

Each package apply records a secret-safe execution identity, operator, approval reference, schema/catalog/source versions, checksum, environment, mode, planned/created/unchanged/conflict/excluded counts, start/completion timestamps, result (`started`, `succeeded`, `failed`, or `refused`), and sanitized failure/conflict outcome. The existing `ReferenceDataSeedRun` convention may be extended or replaced by a document-catalog-specific execution record only through the implementation migration; organization-scoped operational audit must not be repurposed as platform apply authority.

## Alternatives

1. Store all metadata in JSON on `DocumentDefinition`: rejected because alias uniqueness, referential jurisdiction/mode integrity, provenance review, querying, and auditable lifecycle transitions require relational constraints.
2. Create one generic EAV/reference table: rejected under ADR-021 because it weakens domain validation and governance.
3. Treat aliases as definitions or auto-merge on alias match: rejected because identity becomes ambiguous and historical foreign keys could be silently rewritten.
4. Use only `INTERNATIONAL`/`IRAN` and one transport mode per definition: rejected because jurisdiction and mode are independently many-to-many and must scale.
5. Activate every reviewed candidate or block the architecture on unresolved rows: rejected; activation is evidence-gated and deferred rows are valid.
6. Make the catalog authoritative for organization requirements: rejected because vocabulary and tenant policy have different owners and lifecycles.
7. Seed through migration/startup or make population a deployment gate: rejected by ADR-011 and ADR-028.

## Consequences

The model gives stable bilingual identity, searchable terminology, scalable applicability, provenance, and an auditable activation boundary. It preserves existing files, requirements, policy precedence, and public identities. Costs include additional relational tables, steward review, locale/search normalization rules, more complex admin UI, and an explicit compatibility rollout between legacy fields and normalized metadata.

Classification and applicability remain descriptive. Consumers must not treat a family, mode, stage, scope, or active catalog row as executable policy. Incomplete evidence becomes visible as a review state rather than guessed production truth.

## Compatibility

Existing `DocumentDefinition.public_id`, numeric internal primary key, code, relationships, request requirements, project/organization policies, operational snapshots, file versions, artifact associations, assessments, and APIs remain intact. Existing rows receive no inferred translation, family, applicability, provenance, or lifecycle in this architecture-only task.

Future adoption is expand-first. Legacy reads continue while new metadata is populated and verified. No automatic remapping is permitted from aliases, renamed candidates, or normalized applicability. Historical definitions are not rewritten. Catalog enrichment alone changes no requirement level, applicability resolution, runtime snapshot, readiness, or association.

## Migration impact

No migration is created or executed by this ADR. A future implementation requires one or more additive migrations for metadata and normalized relations, with a sole Alembic head, explicit indexes and uniqueness constraints, reversible schema downgrade where practicable, and retained data/audit if application rollback occurs.

Backfill must be bounded, idempotent, evidence-based, observable, and fail closed. Unknown values remain unknown. Compatibility columns are retained through expand, populate, verify, dual-read/shadow comparison, switch, and a separately authorized contract phase. Catalog data is never inserted by schema migration.

## Security/tenant impact

The catalog is allowlisted platform-scoped vocabulary with platform-controlled writers. Platform catalog access grants no tenant content access. Organization policy derives organization identity from authenticated membership or another trusted context; client-supplied tenant IDs cannot broaden scope. Cross-tenant policy and document associations continue to fail closed. Audit and errors exclude source-document bodies, credentials, storage paths, and forbidden tenant data.

## Operational impact

No runtime or deployment impact occurs now. Future catalog apply is optional, explicit, transactional, conflict-aware, and independently observable. Failures leave the prior catalog and every tenant policy unchanged. Search indexes and administration queries must be bounded and paginated where appropriate.

## Rollback

For a future implementation, application rollback disables new metadata writes and returns reads to compatible legacy fields while retaining additive metadata, provenance, apply evidence, and audit for reconciliation. Package apply rollback never deletes referenced definitions or rewrites tenant policy; corrections use an approved forward catalog version or explicit deprecation. A destructive database downgrade after dependent rows exist requires separate authority and preserved/exported evidence.

## Validation

Implementation authority requires:

- schema and migration tests on SQLite compatibility and PostgreSQL, including sole-head downgrade/re-upgrade evidence;
- N/N-1 API and legacy-field fallback tests;
- normalized alias collision, Unicode normalization, code collision, and ambiguous-resolution tests;
- jurisdiction/mode/stage/scope referential and duplicate-constraint tests;
- lifecycle transition, provenance eligibility, deprecation, concurrency, and audit tests;
- plan/apply checksum, idempotency replay, drift conflict, atomic rollback, secret-safe failure, environment, approval, and production-confirmation tests;
- platform-admin versus organization-admin and cross-tenant negative tests;
- proof that catalog creation/activation never creates policy, requirements, files, associations, assessments, workflows, or statuses;
- UI separation and accessibility/localization checks; and
- architecture governance, changed-scope secret scan, and `git diff --check`.

No runtime/full-suite test is required for this architecture-only decision.

## Explicit exclusions

This ADR does not define or authorize ExternalReference architecture; structured Registration Order or Statistical Registration domains; `ExecutionUnit` document ownership; a document workflow engine; customs or banking workflow; automatic document requirement generation; runtime code; migration; seed/catalog rows; production access; deployment; or push.

## Supersedes / superseded by

- Supersedes: none
- Superseded by: none
- Extends: ADR-021, ADR-028, and ADR-030 without changing their authority
- Context only: ADR-020 remains PROPOSED and grants no implementation authority

## Status history

- 2026-08-20: ACCEPTED — the authorized architecture review found no contradiction with Accepted ADRs; unresolved catalog rows remain safely excluded behind the explicit provenance and activation gates.
