# Documents Reference Reconciliation — 2026-09-20

- **Scope:** Documentation/reference reconciliation only
- **Branch:** `codex/documents-reference-reconciliation`
- **Parent:** `4c5c3a1b16256ba13fa4b967ea1d397dda987202`
- **Canonical branch at qualification:** `integration/golden-controlled`
- **Canonical local/remote comparison at qualification:** `0/0` against `github/integration/golden-controlled`
- **Runtime / test / migration / database / deployment / Production authority:** None

## A. LPAF Governance Gate

The active governing baseline is **LPAF v2.2**, approved and ACTIVE on 2026-09-03, with the mandatory `LPAF-v2.2-Agent-Entry-Protocol.md`. LPAF v2.3 Product Integration is a REVIEWED CANDIDATE, not the active baseline; its reference-impact, journey, RBAC reachability, negative authorization, and reference-alignment gates are applied here as the Forwarder strong default. No generic LPAF file changed.

**MISSION:** close Documents actor/entitlement, parent authority, ownership, version-history, retry, readiness, and reference truth before implementation design.

**OUTCOME:** Accepted PDR-020 and ADR-050 plus reconciled living Forwarder references; no runtime or environment mutation.

| Gate field | Reconciled result |
| --- | --- |
| CAPABILITY_OWNER | Product — Documents & Collaboration; Document system owns file/history mechanics; parent Shipment/Case owns management entitlement |
| SYSTEM_OF_RECORD | Parent ownership in persisted Shipment/Case; requirement/file/version/association/readiness SORs separated in §F |
| ACTOR / ROLE / ENTITLEMENT | Active owning Transport Expert only for management |
| TENANT / DATA SCOPE | Server-derived parent Organization; other tenant denied non-disclosively; no client ownership trust |
| USER JOURNEY | Existing Shipment/Case Documents entry; multi-file, append, targeted replace, failed-file retry; leave/return/history defined in S6 and §J |
| STATE OWNER | Document system owns file/version state; MDPM owns readiness; parent owns actor authority |
| DATA OWNER | Parent scope owns business context; private document storage owns bytes; Document system owns metadata/history |
| HISTORY OWNER | System, not Expert/Admin/Customer |
| UPSTREAM / DOWNSTREAM | Shipment/Case ownership and requirements upstream; readiness and operational workflow downstream |
| MODULE BOUNDARY | Parent authorization → Document commands/storage/history → MDPM readiness; no physical extraction authorized |
| PUBLIC CONTRACT | Opaque parent/file/version identities; no storage key or client owner as authority; no public management surface |
| API IMPACT | Future parent-routed, file-level result, targeted replace, idempotent/retry-safe commands; no API changed here |
| SCHEMA IMPACT | `TO_BE_CONFIRMED_IN_DESIGN`; no schema or migration authorized |
| COMPATIBILITY IMPACT | Existing bytes/rows/history preserved; current broader writes and Request-derived Shipment authority recorded as drift |
| ACCEPTANCE CONTRACT | Owner success, A/B/C mixed result, targeted replace/history, logical readiness, ordinary leave/return |
| NEGATIVE AUTHORIZATION CONTRACT | Other Expert, Admin/Manager management, Customer management, other tenant, inactive/revoked actor, forged lineage, stale target denied |

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
```

### Evidence classification

- **FACT:** repository references previously recorded `BLOCKED_PENDING_DOCUMENT_ACTOR_DECISION`; current models contain file/version/history foundations; current runtime authorization is not fully aligned with ADR-047/PDR-020.
- **FACT:** the Product Owner has now selected owning-Transport-Expert-only management and system-owned history.
- **ASSUMPTION:** none used to broaden actor, tenant, visibility, reassignment, schema, or implementation authority.
- **UNKNOWN:** exact additive schema need remains a design question; generalized Customer/stakeholder read visibility remains separately Proposed under PDR-008/ADR-020.
- **DECISION NEEDED:** none for the management actor/ownership/history design gate. Future design decisions remain listed in §S.

## B. Previous Ambiguity

PDR-019 §6 approved functional behavior but blocked Documents because Customer, owning Transport Expert, and Admin/Manager action entitlements were undecided. PDR-009 historically recommended controlled Customer upload/replacement, while PDR-008/ADR-020 kept generalized visibility Proposed. FDD-001, FDM-001, S6, the capability map, and drift register therefore carried a management blocker.

Historical records were not rewritten. PDR-020 explicitly supersedes the PDR-019 Documents actor blocker and PDR-009's Customer-management recommendation. ADR-050 constrains any broader management implication in Proposed ADR-020 while leaving generalized read visibility in its historical Proposed state.

## C. Product Owner Decision

```text
DOCUMENT_MANAGING_ACTOR=OWNING_TRANSPORT_EXPERT_ONLY

CUSTOMER_DOCUMENT_MANAGEMENT_ALLOWED=NO
ADMIN_MANAGER_DOCUMENT_MANAGEMENT_ALLOWED=NO
OTHER_SAME_ORG_EXPERT_DOCUMENT_MANAGEMENT_ALLOWED=NO
CROSS_TENANT_DOCUMENT_MANAGEMENT_ALLOWED=NO

SYSTEM_PRESERVES_DOCUMENT_VERSION_HISTORY=YES

DOCUMENT_MULTI_FILE_DIRECTION=APPROVED
DOCUMENT_APPEND_DIRECTION=APPROVED
DOCUMENT_REPLACE_WITH_HISTORY_DIRECTION=APPROVED
DOCUMENT_FAILED_FILE_RETRY_DIRECTION=APPROVED

EXPERT_REASSIGNMENT_WORKFLOW_APPROVED=NO
```

Management includes upload, append, targeted replacement, and retry of a known failed file. It does not include read-only oversight, requirement policy administration, document catalog administration, assessment/verification, retention/purge, or public/customer projection.

## D. Actor / Entitlement Matrix

| Actor | Manage | Authority result |
| --- | --- | --- |
| Active owning Transport Expert | ALLOWED | Parent-derived Shipment/Case ownership plus action/state validation |
| Other Transport Expert, same Organization | DENIED | Membership is not ownership |
| Admin/Manager | NOT A DOCUMENT MANAGEMENT ACTOR | Existing oversight/read remains separate |
| Customer | NOT A DOCUMENT MANAGEMENT ACTOR | No upload/append/replace/retry capability |
| Other tenant | DENIED | Tenant-first, non-disclosing denial |
| Inactive/revoked actor, including recorded owner | DENIED | Active identity/membership required at action time |

No standalone attachment permission, public ID, Project membership, stale list result, cached response, Request identifier, or client-supplied tenant/owner bypasses the parent root.

## E. Read vs Manage

This reconciliation changes management truth only.

- Owning Expert governed read/history/download remains distinct from write authority.
- Same-Organization Admin/Manager may retain existing Accepted tenant-scoped oversight/read, but cannot upload, append, replace, or retry.
- Customer document read/download is not newly granted. PDR-008/ADR-020 remain Proposed for a future generalized allowlisted projection.
- No new public, other-Expert, cross-tenant, partner, carrier, customs, or AI visibility is granted.

```text
CUSTOMER_DOCUMENT_READ_POLICY=PDR_008_REMAINS_PROPOSED_NO_NEW_VISIBILITY_GRANTED
ADMIN_MANAGER_DOCUMENT_READ_POLICY=PRESERVE_EXISTING_GOVERNED_OVERSIGHT_ONLY
```

Therefore `cannot upload` does not mean `cannot view`, and `can view` never means `can manage`.

## F. Owner / SOR / History Owner

| Concern | Capability/state owner | System of Record / compatibility authority |
| --- | --- | --- |
| Parent management entitlement | Shipment/Case boundary | `OperationalShipment` fixed owner after creation under ADR-047; authoritative Request/Case owner before Shipment |
| Reusable policy | Document policy/catalog | `DocumentDefinition` and organization/project policy records |
| Logical requirement | Parent/document policy | `CaseDocumentRequirement` and `OperationalDocumentRequirement` in their bounded scopes |
| Physical file/version metadata | Document system | `CaseDocumentFile` until a later Accepted additive design |
| Binary bytes | Private document storage | Generated private storage identity; never public authority |
| Contextual exact-version use | Parent/document association policy | `ArtifactAssociation` / future canonical `DocumentAttachment` |
| Version/history chain | System | immutable file/version lineage, supersession metadata, audit, retained private bytes |
| Readiness | MDPM | logical requirement + applicability + eligible current exact-version association(s) + assessment policy |

`DocumentRequirement`, physical file/evidence, `DocumentVersion`, contextual attachment/use, and DocumentReadiness are not synonyms.

## G. Multi-File

One logical DocumentRequirement may contain multiple current physical files within governed type, size, and active-count limits. Every file has independent identity, metadata, validation, outcome, current/history state, and audit. Multiple physical files do not create multiple logical requirements and do not automatically increase readiness.

## H. Append

Append creates a new current sibling file. It preserves every valid current sibling and does not resubmit, replace, or re-version them. Append has its own audit/result and respects the logical requirement's configured limits.

## I. Replace / Version History

Replacement targets exactly one selected current file/version. The owning Expert requests replacement; the System validates and creates a new immutable version; the new version becomes current where applicable; the old version remains immutable, auditable, and available only under authorized history/read policy.

Destructive overwrite, replace-all-siblings, silent fallback to an older version, and inherited approval/verification are prohibited. ADR-030 continues to require independent assessment of the new exact version.

## J. Retry / Partial Failure

```text
A=SUCCESS_PRESERVED
B=FAILED_RETRYABLE
C=SUCCESS_PRESERVED
RETRY=B_ONLY
```

The future public contract returns truthful file-level outcomes. A failure does not roll back valid siblings and a retry does not resend or replace A/C. A known failure and an unknown/lost response must be distinguished in design; ADR-010 governs replay/conflict principles. No all-or-nothing batch is assumed.

Journey: ENTRY existing Shipment/Case Documents surface; ACTOR owning Transport Expert; DISCOVERY ordinary Shipment/Case navigation; USE choose one/many, upload, append, targeted replace, retry failed file; RESULT governed per-file state plus system-owned history; LEAVE return to Shipment/Case; RETURN reopen current/history; DENIAL the negative matrix in §D; FAILURE preserves successful siblings; DOWNSTREAM logical document readiness/operational workflow.

## K. Document Readiness

Readiness is the derived result of the logical requirement contract, applicability, eligible current evidence, and required assessment. Append and Replace are semantically different. Historical superseded versions remain audit evidence but do not count as additional current required evidence. A failed upload that produced no governed current file cannot satisfy readiness.

The future design must state the governed evidence rule for each logical requirement; it may require one, all, or a defined subset of current files. Raw quantity is never the rule:

```text
MORE_FILES_DOES_NOT_MEAN_MORE_READY
```

## L. Customer Role

Customer does not upload, append, replace, or retry Documents. No Customer write endpoint, UI action, generic capability, or implied ownership is approved. A future Customer-safe read/download projection requires explicit visibility authority and allowlisting under PDR-008/ADR-020; this reconciliation grants none.

## M. Admin/Manager Role

Admin/Manager remains a separately governed same-Organization oversight actor. Existing read/oversight may be preserved, but generic Organization membership or Admin capability must not authorize document upload, append, targeted replace, retry, or owner substitution. Requirement/catalog/policy administration is a different capability and does not make Admin/Manager a file-management actor.

## N. ADR-047 / Expert Ownership Alignment

```text
ONE_TRANSPORT_EXPERT_PER_SHIPMENT=YES
EXPERT_REASSIGNMENT_WORKFLOW_APPROVED=NO
```

OperationalShipment is the target fixed-owner SOR. This reconciliation defines no former Expert, replacement Expert, transfer on reassignment, automatic replacement for inactive owner, or document handoff. Current accepted-Quote Request-assignee-derived access is drift to be corrected in a later bounded implementation, not target authority.

## O. References Updated

| Reference | Reconciliation |
| --- | --- |
| `docs/operational/PDR-020-documents-expert-only-management.md` | New Accepted Product decision; explicit supersession and scope |
| `docs/operational/adr/ADR-050-owning-expert-document-management-history.md` | New Accepted target architecture; owner/history/readiness/API/schema forecast |
| `docs/operational/decision-index.md` | PDR-020/ADR-050 indexed; PDR-009/PDR-019/ADR-020 supersession scopes visible |
| `docs/architecture/ADR-INDEX.md` | ADR-050 indexed; ADR-020 management scope constrained |
| `docs/operational/FDD-001-forwarder-data-dictionary.md` | Requirement/file/version/attachment/readiness vocabulary and actor/history truth reconciled |
| `docs/operational/canonical_business_object_catalog.md` | Document canonical definitions and management/read separation reconciled |
| `docs/operational/FDM-001-forwarder-domain-map.md` | Documents owner/SOR edge unblocked for design |
| `docs/architecture/FORWARDER-ARCHITECTURE-BASELINE.md` | Data ownership, management entitlement, history and drift added |
| `docs/operational/architecture_baseline_v1.md` | Living baseline status/cross-reference updated |
| `docs/operational/platform_capability_map_v1.md` | CAP-005 actors, ownership, roadmap and traceability updated |
| `docs/governance/S6-GOLDEN-BUSINESS-JOURNEYS.md` | Blocked Documents journey replaced with target journey contract |
| `docs/architecture/ARCHITECTURE-DRIFT-REPORT.md` | Actor reference resolved; runtime/design drift remains OPEN |
| This evidence file | LPAF gate, decisions, donor review, forecast, closure, and verdict |

Historical PDR-008/PDR-009/PDR-019, ADR-020, the Phase 0.5 Workshop, and prior reconciliation evidence were not silently rewritten. Their current scope/status is reconciled through new decisions and living indexes.

## P. FWD-07 Classification

Read-only donor lineage reviewed: `811bbbaed5d2eb48c5f713b88991ce73b80c20b8` through `a778bc8516e2d71b8665acd046191fbc5f0493e8`. Nothing was merged or cherry-picked.

| Donor concept | Classification | Reason |
| --- | --- | --- |
| Multiple active files for one Request requirement, governed max count, distinct generated storage keys | ALIGNED | Matches multi-file direction and private immutable-file principle |
| Independent per-file submissions and saved/failed UI results | ALIGNED | Preserves successful siblings and enables failed-file-only retry |
| Donor Request-assignment authorization and existing Admin access | REIMPLEMENT_AGAINST_GOLDEN | Target must derive the owning Shipment/Case Expert and deny Admin management under PDR-020/ADR-047/050 |
| Donor “replace latest” requirement action | REJECTED | Target replacement selects one explicit current file/version; latest-by-query is not a sufficient target contract for multi-file |
| Lost-response recovery proposal / donor ADR-049 | REIMPLEMENT_AGAINST_GOLDEN | Unknown outcome is real design input, but ADR-049 is Proposed and not accepted; design must apply ADR-010 without importing donor authority |
| Unicode display filename with generated private storage key | ALIGNED | Safe metadata/storage separation is compatible; no runtime adoption occurs here |
| Donor code, tests, CI harness, browser evidence, database orchestration, and dependency changes | NOT_NEEDED | Documentation-only phase; no Build or qualification import is authorized |

## Q. Schema Forecast

```text
DOCUMENT_SCHEMA_CHANGE_REQUIRED=TO_BE_CONFIRMED_IN_DESIGN
DOCUMENTS_IMPLEMENTATION_GATE=READY_FOR_DESIGN
```

The Golden model already contains multiple file rows, immutable bytes/checksums, version/status/supersession metadata, private storage, audit, exact-version associations, assessment, and readiness. Design must still prove that the current structures safely express multiple current files for one operational logical requirement, targeted file lineage, current/version identity, per-file known/unknown outcome, and readiness over a current evidence set. Authorization/orchestration changes alone do not imply a schema migration.

No migration is created or authorized. If later design proves an additive schema necessary, it requires its own accepted migration/rollback/compatibility contract and disposable PostgreSQL verification.

## R. Reference Impact Closure

Every affected living project reference now points to PDR-020/ADR-050 for management truth while preserving older decision history.

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
REFERENCE_IMPACT_STATUS=CLOSED_FOR_DOCUMENTS_DESIGN
```

Closure means the management actor, negative entitlements, parent root, history owner, multi-file/append/replace/retry semantics, readiness boundary, and user journey are authoritative enough for bounded design. It does not claim implementation, browser acceptance, test, database qualification, migration, release, deployment, or Production completion.

## S. Remaining Decisions

These are future design/policy items, not actor-reference conflicts:

1. Prove schema sufficiency or propose the minimal additive design for multi-current associations, targeted lineage, and upload-operation outcome.
2. Define the per-requirement eligible-current-evidence rule without converting file count into readiness.
3. Define idempotency and unknown/lost-response recovery under ADR-010; donor ADR-049 is evidence only.
4. Resolve generalized Customer/stakeholder read/download visibility separately under PDR-008/ADR-020 before granting it.
5. Resolve retention/legal hold/purge/signature policy under PDR-011 before implementing those actions.
6. In the later Build slice, converge Shipment authorization on ADR-047 and remove Admin/Manager document-management paths without disturbing their separately governed read/oversight or policy-administration capabilities.

Repository-only verification for this phase:

```text
ALEMBIC_HEAD=20260924_request_cargo_items
ALEMBIC_HEAD_COUNT=1
MIGRATION_FILES_CHANGED=NO

LOCAL_DEVELOPMENT_DB_ACCESSED_AS_AUTHORITY=NO
LOCAL_DEVELOPMENT_DB_CHANGED=NO

RUNTIME_PRODUCT_CHANGED=NO
TESTS_CHANGED=NO
MIGRATIONS_CHANGED=NO
LPAF_FRAMEWORK_CHANGED=NO
PRODUCTION_ACCESSED=NO
```

No tests were run because the authorized phase explicitly changes references only. Documentation/reference consistency and repository graph checks are the applicable verification.

## T. Verdict

PASS — DOCUMENTS REFERENCES RECONCILED UNDER LPAF
