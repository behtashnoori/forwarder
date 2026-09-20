# PDR-020 — Owning-Expert-Only Document Management

- **Status:** ACCEPTED — target/reference phase only
- **Date:** 2026-09-20
- **Decision authority:** Product Owner
- **Rigor:** LPAF Level B; LPAF v2.3 Product Integration gate applied as a strong default
- **Implementation authority:** None. This decision changes no runtime, test, migration, database, deployment, or Production system.
- **Related authority:** PDR-008, PDR-009, PDR-019, ADR-020, ADR-030, ADR-047, ADR-050, FDD-001, and the Canonical Business Object Catalog.

## 1. Decision and scope

Only the active Transport Expert who owns the authoritative Shipment/Case may manage its document files.

```text
DOCUMENT_MANAGING_ACTOR=OWNING_TRANSPORT_EXPERT_ONLY

CUSTOMER_DOCUMENT_MANAGEMENT_ALLOWED=NO
ADMIN_MANAGER_DOCUMENT_MANAGEMENT_ALLOWED=NO
OTHER_SAME_ORG_EXPERT_DOCUMENT_MANAGEMENT_ALLOWED=NO
CROSS_TENANT_DOCUMENT_MANAGEMENT_ALLOWED=NO

SYSTEM_PRESERVES_DOCUMENT_VERSION_HISTORY=YES
```

Management means upload, append, targeted replacement of one current file, and retry of a failed file where the upload outcome is known. The owner is derived from the persisted parent authority; a client-supplied tenant, user, role, owner, Request assignment, Project membership, file identifier, or attachment permission cannot manufacture management authority.

This record closes and supersedes only the `BLOCKED_PENDING_DOCUMENT_ACTOR_DECISION` gate in PDR-019 §6. It also supersedes PDR-009's Proposed recommendation to permit controlled Customer upload/replacement. PDR-009 remains preserved as historical Proposed evidence. No Customer document write capability is approved.

PDR-008 remains Proposed for generalized read/download visibility, classification, and stakeholder grants. PDR-011 remains Proposed for retention, legal hold, purge, and signature policy. Neither record grants document management authority.

## 2. Actor and entitlement matrix

| Actor | Upload | Append | Targeted replace | Retry known failed file | Result |
| --- | --- | --- | --- | --- | --- |
| Active owning Transport Expert | ALLOWED | ALLOWED | ALLOWED | ALLOWED | Parent-derived authority plus action/state validation |
| Other Transport Expert in the same Organization | DENIED | DENIED | DENIED | DENIED | Organization membership is not ownership |
| Same-organization Admin/Manager | NOT A MANAGEMENT ACTOR | NOT A MANAGEMENT ACTOR | NOT A MANAGEMENT ACTOR | NOT A MANAGEMENT ACTOR | Oversight/read is separate from management |
| Customer | NOT A MANAGEMENT ACTOR | NOT A MANAGEMENT ACTOR | NOT A MANAGEMENT ACTOR | NOT A MANAGEMENT ACTOR | No Customer write capability |
| Other tenant | DENIED | DENIED | DENIED | DENIED | Non-disclosing tenant boundary |
| Inactive/revoked actor, including recorded owner | DENIED | DENIED | DENIED | DENIED | Active identity and membership required at action time |

There is no standalone attachment permission that bypasses the parent Shipment/Case authority.

## 3. Read versus manage

This decision governs management only. It does not infer that an actor who cannot upload cannot view.

- The owning Expert's existing governed read/history/download path remains separate from management.
- Existing same-organization Admin/Manager oversight/read visibility may be preserved where an Accepted authority and tenant-scoped read contract already allow it; it grants no upload, append, replace, or retry.
- No Customer read/download visibility is newly granted here. Generalized Customer-safe projections remain subject to PDR-008 and explicit allowlisting.
- No public, cross-tenant, other-Expert, or storage-key-based visibility is created.

```text
CUSTOMER_DOCUMENT_READ_POLICY=PDR_008_REMAINS_PROPOSED_NO_NEW_VISIBILITY_GRANTED
ADMIN_MANAGER_DOCUMENT_READ_POLICY=PRESERVE_EXISTING_GOVERNED_OVERSIGHT_ONLY
```

## 4. Approved functional behavior

```text
DOCUMENT_MULTI_FILE_DIRECTION=APPROVED
DOCUMENT_APPEND_DIRECTION=APPROVED
DOCUMENT_REPLACE_WITH_HISTORY_DIRECTION=APPROVED
DOCUMENT_FAILED_FILE_RETRY_DIRECTION=APPROVED
```

- **Multi-file:** one logical DocumentRequirement may have several current physical files within its governed limits.
- **Append:** adding a file does not replace or resubmit valid current siblings.
- **Replace:** the owning Expert selects one current file. The system creates a governed new version, makes it current where applicable, and retains the old version as immutable/auditable history. Destructive overwrite is not replacement.
- **Retry:** if A succeeds, B fails, and C succeeds, A and C remain successful and only B is retried. A batch is not all-or-nothing unless later storage design proves that constraint necessary.
- **File state:** each current/history projection preserves filename, detected content/type metadata, upload time, uploader, status, current/version identity, and history relationship using governed existing metadata where available.

The product direction does not authorize an enterprise DMS, Customer contribution workflow, Admin upload workflow, or generic Organization-member write access.

## 5. Ownership and System of Record

| Concern | Owner / System of Record |
| --- | --- |
| Management authorization root | Persisted Shipment/Case owner; OperationalShipment is the fixed-owner SOR after Shipment creation under ADR-047 |
| Logical requirement | Parent-scoped `DocumentRequirement`; current compatibility forms include `CaseDocumentRequirement` and `OperationalDocumentRequirement` |
| Physical file/version metadata | `CaseDocumentFile` compatibility authority until a later Accepted additive design; private document storage owns bytes |
| Contextual exact-version use | `ArtifactAssociation` / future canonical `DocumentAttachment` |
| Version/history preservation | System-owned document service, immutable file/version lineage, private storage, and audit records |
| Readiness | `OperationalDocumentRequirement`, exact current association(s), assessment policy, and derived readiness projection |

`DocumentRequirement`, physical file/evidence, `DocumentVersion`, contextual association, and DocumentReadiness are distinct concepts and lifecycle owners.

## 6. Readiness rule

Readiness is governed by the logical requirement contract, applicability, required assessment level, and its eligible current evidence set. File quantity alone never increases readiness.

- Append and replace are distinct operations.
- A superseded historical version cannot count as an additional current file or satisfy readiness merely because it remains stored.
- Replacement does not inherit approval/verification unless an Accepted policy explicitly says so; ADR-030 currently requires independent assessment for the new exact version.
- Several current files may support one logical requirement, but design must define whether one, all, or a governed subset is necessary for satisfaction without using `more files = more ready`.

## 7. Ownership continuity

ADR-047 remains authoritative:

```text
ONE_TRANSPORT_EXPERT_PER_SHIPMENT=YES
EXPERT_REASSIGNMENT_WORKFLOW_APPROVED=NO
```

This decision introduces no former Expert, replacement Expert, transfer-on-reassignment, automatic owner substitution, or document handoff workflow. An inactive/revoked owner is denied; continuity is not solved by granting Admin/Manager document management.

## 8. API, schema, compatibility, and negative authorization

Future APIs must derive tenant and owner server-side, authorize every file operation against the parent, return file-level outcomes for multi-file submissions, bind targeted replacement to an explicit current file/version, preserve successful siblings, and use stable non-disclosing denials.

Existing file/version/history data remains valid. Existing runtime permissions that allow Organization Admin management or derive accepted-Quote Shipment access from the current Request assignee are implementation drift, not target authority.

```text
DOCUMENT_SCHEMA_CHANGE_REQUIRED=TO_BE_CONFIRMED_IN_DESIGN
DOCUMENTS_IMPLEMENTATION_GATE=READY_FOR_DESIGN
```

Design must prove whether the current schema can represent multiple current files per logical operational requirement, explicit targeted replacement lineage, current/version identity, and any durable failed/unknown upload outcome without ambiguity. No schema or migration is authorized by this forecast.

Negative acceptance must cover other same-Organization Expert, Admin/Manager management, Customer management, other tenant, inactive/revoked owner, forged owner/tenant input, known child/file identifier, stale list/cache result, and parent/child lineage mismatch.

## 9. Reference and implementation status

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
REFERENCE_IMPACT_STATUS=CLOSED_FOR_DOCUMENTS_DESIGN

RUNTIME_PRODUCT_CHANGED=NO
TESTS_CHANGED=NO
MIGRATIONS_CHANGED=NO
LPAF_FRAMEWORK_CHANGED=NO
LOCAL_DEVELOPMENT_DB_CHANGED=NO
PRODUCTION_ACCESSED=NO
```

Reference closure means the management actor, parent authority, history owner, multi-file behavior, retry semantics, and readiness boundary are authoritative enough for a bounded design phase. It does not claim implementation, test, migration, browser acceptance, release, deployment, or Production completion.
