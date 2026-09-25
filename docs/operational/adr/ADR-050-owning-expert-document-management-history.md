# ADR-050: Owning-Expert Document Management and System-Owned History

- **Status:** ACCEPTED — target architecture; reference phase only
- **Date:** 2026-09-20
- **Owners / decision authority:** Product Owner; Architecture Owner; Security Owner; Operations Owner
- **Affected domain:** Shipment/Case Documents management, file/version lineage, readiness, authorization
- **Implementation authority:** None. This ADR changes no runtime, schema, data, permission, test, deployment, or Production system.
- **Identifier note:** ADR-048 and ADR-049 are already used in read-only donor lineages and are not reused by this canonical decision.

## Context

PDR-019 preserved multi-file, append, targeted replacement with history, and failed-file retry, but blocked Documents because its actor/action matrix was unknown. PDR-020 now makes the Product decision: only the active owning Transport Expert manages files. ADR-047 makes OperationalShipment the fixed responsible-Expert authority after Shipment creation and approves no Shipment reassignment workflow.

The current Golden model contains useful foundations: `CaseDocumentRequirement`, immutable `CaseDocumentFile` rows and private bytes, version/status/supersession metadata, `DocumentAuditEvent`/`OperationalAudit`, `OperationalDocumentRequirement`, `ArtifactAssociation`, and `DocumentAssessment`. Current runtime is not target authority where it grants Organization Admin management, roots accepted-Quote Shipment access in the current Request assignee, or models only one effective active readiness association.

## Decision

Document management is a parent-authorized capability, not an independent attachment permission.

```text
PARENT_AUTHORIZATION_ROOT=AUTHORITATIVE_SHIPMENT_OR_CASE
DOCUMENT_MANAGING_ACTOR=OWNING_TRANSPORT_EXPERT_ONLY
HISTORY_OWNER=SYSTEM
```

- For an OperationalShipment Documents surface, `OperationalShipment` and its fixed responsible Transport Expert under ADR-047 are the authorization root.
- For a pre-Shipment Request/Case Documents surface, the existing authoritative Request/Case owning Expert is the root until a separately governed OperationalShipment exists.
- A Project relation, generic Organization membership, Admin/Manager title, Customer relation, Request identifier, child/file identifier, client-supplied owner, or attachment permission never creates management authority.
- The active owner initiates upload, append, targeted replace, and retry of a known failed file. The system validates, persists, versions, supersedes, audits, and preserves history.
- There is no document transfer/reassignment model and no former-Expert access semantic.

## Domain and module boundary

The Document boundary owns file validation, immutable version metadata, private byte custody, current/history projection, operation outcome, and audit. The parent Shipment/Case boundary owns management entitlement. MDPM owns logical operational requirement satisfaction/readiness; it does not own binary mutation.

| Concept | Meaning | State/history owner |
| --- | --- | --- |
| `DocumentRequirement` | Logical required/optional evidence contract for a parent scope | Requirement policy/snapshot owner |
| `DocumentArtifact` / compatibility `CaseDocumentFile` | One immutable physical file version plus intrinsic metadata; private storage owns bytes | Document system |
| `DocumentAttachment` / compatibility `ArtifactAssociation` | Contextual use of an exact version by a parent or requirement | Parent/document association policy |
| `DocumentVersion` | One immutable member of a file lineage | System-owned replacement/supersession policy |
| `DocumentReadiness` | Derived result for a logical requirement | MDPM readiness policy/projection |

Public contracts use opaque governed identities and never expose storage keys as authority. Physical modular extraction, a second document store, generic polymorphic owner tables, and an enterprise DMS are not authorized.

## Multi-file and append contract

One logical requirement may contain multiple current physical files. Each file has an independent immutable identity, validation result, stored bytes, metadata, current/history state, and operation outcome.

Append adds new current evidence without changing valid siblings. The system must enforce the logical requirement's type, size, and active-file limit. Append never means replace-all, and the existence of more files does not by itself improve readiness.

## Targeted replacement and history contract

Replacement targets exactly one selected current file/version:

```text
current version
-> owning Expert requests replacement
-> system validates and creates a governed new version
-> new version becomes current where applicable
-> old version remains immutable and auditable
```

The command must bind the parent, logical requirement/context, selected current file identity, expected current version/state where applicable, actor, tenant, and retry/idempotency contract. Destructive overwrite, silent binary mutation, replacement of every sibling, reuse of an older unsafe version, and approval inheritance are prohibited.

## Retry and partial-failure contract

For a selection A, B, C where A succeeds, B fails, and C succeeds:

```text
A=PRESERVED
B=FAILED_AND_RETRYABLE
C=PRESERVED
RETRY_TARGET=B_ONLY
```

Each file is an independently attributable result. A failed sibling does not roll back or replace a successful sibling. A later design must distinguish a known failure from an unknown/lost response and apply ADR-010 idempotency principles; the Proposed donor ADR-049 is not accepted by this decision.

## Readiness contract

Readiness remains a derived property of the logical requirement, applicability, current eligible evidence, and required assessment level.

- Historical superseded versions remain visible to authorized history readers but do not count as additional current evidence.
- Replacement invalidates the prior exact-version association for current readiness and requires assessment of the new exact version under ADR-030.
- Append and replace have different effects and audit facts.
- Design must state whether a requirement needs one, all, or a governed subset of its current files; raw count is never the rule.
- A failed upload that created no governed current file cannot satisfy readiness.

## Read versus manage

This ADR changes management authority only. Existing accepted read/history/download visibility for the owning Expert and same-Organization Admin/Manager oversight may remain under their separate read contracts. It grants no Customer or public visibility. PDR-008 remains Proposed for generalized visibility and Customer-safe projection; lack of management authority must not be used to infer lack of read authority, and read authority must not be used to infer management authority.

## Authorization and negative contract

Every operation derives active identity, tenant, parent, owner, requirement/context, and current file/version from server-side state at action time. Denial is required for:

1. another Transport Expert in the same Organization;
2. Admin/Manager attempting upload, append, replace, or retry;
3. Customer attempting any management action;
4. other-tenant actor or target;
5. inactive/revoked actor, including the recorded owner;
6. forged tenant/owner/parent/file relationship;
7. child identifier, stale list/cache result, or public identity without certified parent lineage;
8. replacement target that is non-current, foreign, deleted, or not in the governed logical context.

## Supersession and alignment

- **PDR-019 §6:** its actor-decision blocker is superseded by PDR-020 and this ADR. Other PDR-019 decisions remain unchanged.
- **PDR-009:** its Proposed Customer upload/replacement recommendation is superseded by PDR-020; historical text remains unchanged.
- **ADR-020:** remains Proposed for generalized artifact/attachment scopes, visibility, classification, bulk download, retention, and stakeholder grants. Any implication of a broader document management actor is constrained by this Accepted ADR.
- **ADR-030:** remains authoritative for exact-version assessment/readiness. This ADR adds the multi-file/current-set rule and does not turn history into readiness.
- **ADR-047:** remains authoritative for fixed OperationalShipment ownership and no reassignment workflow.

## Compatibility and schema forecast

Existing Request-owned and Shipment-owned file rows, private bytes, checksums, audit, version numbers, and supersession history remain valid. No backfill, file movement, destructive rewrite, storage migration, or permission mutation is authorized.

```text
DOCUMENT_SCHEMA_CHANGE_REQUIRED=TO_BE_CONFIRMED_IN_DESIGN
```

The design phase must prove whether existing structures are sufficient for:

- multiple current files associated with one logical operational requirement;
- stable targeted file lineage rather than replace-latest ambiguity;
- explicit current/version identity and history traversal;
- per-file known failure versus unknown outcome and safe retry;
- readiness over a governed current evidence set.

Schema change must not be inferred merely because runtime code needs authorization or orchestration changes. If an additive schema is necessary, it requires a later accepted design, migration/rollback contract, disposable PostgreSQL proof, and one-head verification.

## API and acceptance contract

Future design must define parent-routed list/history/download and owning-Expert-only upload/append/replace/retry commands; file-level responses for multiple selections; stable idempotency/conflict errors; non-disclosing authorization; safe filenames/content detection/private storage; and a normal Documents journey with leave/return.

Before implementation Freeze, evidence must cover owning Expert success; other same-Organization Expert, Admin/Manager management, Customer management, other tenant, inactive/revoked actor, forged lineage, stale target, mixed A/B/C outcome, retry B only, targeted replacement, history preservation, readiness semantics, and no owner-transfer route.

## Consequences

The design has one understandable management actor and one parent authorization root while preserving separate oversight/read policies. The system, not the Expert, owns historical integrity. The tradeoff is intentional: Admin/Manager cannot repair continuity by uploading, and Customer cannot contribute files. Any future change requires a new Product decision and scoped supersession.

## Reference impact

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
REFERENCE_IMPACT_STATUS=CLOSED_FOR_DOCUMENTS_DESIGN
DOCUMENTS_IMPLEMENTATION_GATE=READY_FOR_DESIGN
```

## Status history

- 2026-09-20: ACCEPTED — owning-Expert-only management, system-owned history, multi-file/retry/readiness boundaries recorded; no implementation authority.
- 2026-09-25: P3-06 implementation is bounded by [ADR-061](ADR-061-contextual-document-version-visibility.md). The owning-Expert rule remains; ADR-061 adds typed exact-version context, explicit visibility/audience and audit without broadening Customer or Admin management.
