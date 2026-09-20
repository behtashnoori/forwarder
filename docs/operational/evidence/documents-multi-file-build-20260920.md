# Expert-only multi-file Documents build evidence — 2026-09-20

## A. LPAF Governance Gate

The build was executed under the active LPAF v2.2 baseline and the v2.3 Product Integration / `REFERENCE_IMPACT` gate. Before implementation, the required design commit and the governing Forwarder decisions were checked and the gate resolved as follows:

```text
MISSION=IDENTIFIED
OUTCOME=IDENTIFIED
CAPABILITY_OWNER=IDENTIFIED
SYSTEM_OF_RECORD=IDENTIFIED
ACTOR_ENTITLEMENT=IDENTIFIED
TENANT_DATA_SCOPE=IDENTIFIED
USER_JOURNEY=IDENTIFIED
STATE_OWNER=IDENTIFIED
HISTORY_OWNER=IDENTIFIED
STORAGE_OWNER=IDENTIFIED
READINESS_OWNER=IDENTIFIED
MODULE_BOUNDARY=IDENTIFIED
API_IMPACT=IDENTIFIED
SCHEMA_IMPACT=NONE
COMPATIBILITY_IMPACT=IDENTIFIED
ACCEPTANCE_CONTRACT=IDENTIFIED
NEGATIVE_AUTHORIZATION_CONTRACT=IDENTIFIED
REFERENCE_IMPACT=NONE
DOCUMENT_SCHEMA_DECISION=NO_SCHEMA_CHANGE_REQUIRED
```

No material architecture or reference conflict was found during implementation.

## B. Starting State

- Worktree: `D:\1-webapp\15-forwarder-golden-20260921`
- Required starting branch: `codex/documents-implementation-design`
- Required and verified starting HEAD: `da63d3ef32f0fb16edb7f7cba0bfc484de655eae`
- Verified parent: `ed6d0d9954b273f35f8f4ebc8f9ec5008cd82d6f`
- Build branch: `codex/documents-multi-file-build`
- Starting worktree: clean
- Design artifact, PDR-020 and ADR-050: present
- Repository Alembic head: exactly one, `20260924_request_cargo_items`
- Migration diff at start and completion: none

## C. Actor / Authorization

Document mutation now has an explicit service-level authorization path separate from read authorization. It reloads the active identity, requires exactly one active organization membership, requires canonical `EXPERT` authority, resolves the parent server-side, compares the actor to the persisted parent owner, and rechecks under the mutation transaction lock.

For Request-owned documents the owner is `ShipmentRequest.assigned_to`. For Shipment-owned documents the owner is the persisted `OperationalShipment.primary_responsible_expert_id`; null legacy ownership fails closed. Admin/Manager, Platform Admin, same-organization peer Expert, cross-tenant Expert, inactive/revoked identity, foreign child identity and stale target mutations are denied without DB, storage or audit side effects.

## D. Current vs Historical File Model

The existing immutable `CaseDocumentFile` model is reused. No parallel version table or logical-file column was added. The public logical root is derived from the root row of the `superseded_by` chain and `lineage_version` is derived during projection.

Traversal fails closed on cycles, two predecessors, missing successors, cross-parent successors and invalid non-terminal lifecycle states. Public projections expose opaque identity, safe metadata, current status, uploader label and prior versions, never storage keys or internal database identities.

## E. Multi-File

One requirement can expose multiple current lineages up to its snapshotted `max_active_file_count`. The UI accepts a multi-selection and executes bounded independent one-file commands in order. Queue states are `queued`, `uploading`, `succeeded`, `failed` and `unknown`; a sibling's result cannot overwrite another sibling's state.

## F. Append

The canonical opaque requirement route accepts one file without a replacement target. An append creates a new logical root and leaves all current siblings unchanged. The backend remains the capacity authority and returns stable `DOCUMENT_ACTIVE_LIMIT_REACHED` conflict evidence when a concurrent command loses the last slot.

## G. Targeted Replace

Replacement requires `replaces_file_public_id`. The compatibility route also requires an explicit target and no longer falls back to the latest active row. Missing target is `422 REPLACEMENT_TARGET_REQUIRED`; stale/non-current target is `409 REPLACEMENT_TARGET_CHANGED`; foreign or mismatched children receive a non-disclosing not-found response.

The service locks the parent, requirement and exact scoped target, validates the new file, creates one immutable successor, supersedes only the target, records the relationship and audit, and compensates newly written storage on transaction failure. Concurrent replacement leaves one successor and one safe conflict while preserving an unrelated sibling.

## H. Version History

Each current-file card presents the current filename, safe MIME/extension, size, upload time, uploader label, current indicator, lineage version, Download, Replace, History and governed Deactivate action. Prior versions are presented once in reverse lineage order and remain downloadable when read authorization permits. Deactivation is logical; bytes, audit and history are retained.

## I. Partial Failure / Retry

Known retryable failures expose Retry only on the failed queue row. Component and browser network evidence proves an `E/F/G` selection can retain `E` and `G` as successful, retry `F` alone, submit `E` and `G` once each, and submit `F` exactly twice.

## J. Unknown Outcome

A timeout, abort or lost response that cannot prove rollback is projected as `unknown`, not failed. It has no Retry action and is never automatically resubmitted. The UI offers “Refresh and inspect”, reloads authoritative current files, and describes possible candidates without claiming exact correlation. Durable operation receipts remain future hardening and were not imported.

## K. Read vs Manage

Existing same-organization Admin/Manager document read/history behavior is preserved. The API returns `can_manage_documents`; Admin UI hides Add, Replace, Retry and Deactivate, while a direct Admin mutation receives `403 DOCUMENT_MUTATION_FORBIDDEN`. Read authorization remains governed by the pre-existing `document.read` path. No Customer document projection or management route was added.

## L. Readiness

MDPM readiness semantics are unchanged. Appending an unrelated sibling and replacing an unassociated lineage do not affect readiness. Replacing the exact active file selected by an `ArtifactAssociation` makes the old association ineligible as superseded until the new exact version is explicitly associated and assessed. Historical versions cannot satisfy readiness.

## M. Storage / Security

- Private generated storage keys remain unrelated to display filenames and are not projected.
- NFC-normalized safe Persian/Unicode filenames are preserved.
- Separators, traversal semantics, controls, overlong names, unsafe extensions, zero bytes, spoofed extension/content and malformed structured archives remain rejected.
- JPEG, PNG, WebP, PDF, DOCX and XLSX detection/inspection remains subject to each snapshotted allowed subset and size cap.
- Fault injection covers write, flush/fsync, promote, DB commit and audit failure. It proves no orphan current DB row, no orphan final binary and preservation of the old current target after failed replacement.

## N. FWD-07 Use

Controlled reuse was limited to the approved concepts: many-active-row semantics, independent uploads, safe Unicode filenames and append/lost-response evidence. Multi-file UI, queue, retry, responsive behavior and authorization were reimplemented in this codebase. Replace-latest and donor Request-assignment/Admin authority were rejected. ADR-049 durable recovery infrastructure was not imported. No merge, cherry-pick or wholesale donor replacement was used.

## O. PostgreSQL Concurrency

An owned local PostgreSQL 18 cluster and disposable head-migrated database were used. Five tests passed on the real engine:

- concurrent requirement initialization remains idempotent;
- concurrent first uploads allocate unique versions;
- concurrent replace of the same explicit target yields one successor and one `409`, preserving its sibling;
- concurrent append at the final slot yields one `201` and one `409 DOCUMENT_ACTIVE_LIMIT_REACHED`, with no orphan binary;
- concurrent miscellaneous appends remain independent.

Result: `5 passed`.

## P. Browser Evidence

The final browser run used a freshly created disposable PostgreSQL database migrated from zero to repository head and a dedicated private storage root. The three serial Playwright journeys passed:

1. Desktop owning Expert: normal login → Expert console → Request detail → Documents; A/B/C independent upload; reopen; D append; explicit A→A2 replacement; A historical and A2 current downloads; E/F/G mixed result; F-only retry with request-count proof; unknown timeout with no retry; leave/reopen persistence.
2. Mobile 390×844: normal owner navigation, RTL direction, no horizontal overflow, current/history reachability.
3. Same-organization Admin: read/history visible, mutation controls absent, and direct opaque upload denied with `403 DOCUMENT_MUTATION_FORBIDDEN`.

Result: `3 passed`.

## Q. Regression

| Qualification | Final result |
|---|---|
| Full backend, explicit owned PostgreSQL test DB | `1,297 passed, 98 skipped, 1 xfailed`, zero failures/errors |
| Focused Documents authorization/fault/readiness cohort | `66 passed, 1 skipped` |
| Real PostgreSQL Documents concurrency | `5 passed` |
| Full frontend inventory | `70 files / 329 tests passed` |
| Focused Documents component suite | `6 passed` |
| Final browser journeys | `3 passed` |
| Release/source/package/architecture cohort | `117 passed, 1 xfailed` |
| TypeScript | PASS |
| ESLint | PASS, zero errors; 13 pre-existing warnings outside this slice |
| Production frontend build | PASS, 2,546 modules transformed |
| Diff whitespace check | PASS |

The first full-backend attempt inherited the host's old `TEST_DATABASE_URL` and produced three setup errors in `test_tenant_architecture_contract.py` while `create_all` encountered an existing FK shape. No product assertion failed. The authoritative full rerun explicitly targeted the owned head-migrated PostgreSQL database and produced the clean result above.

## R. Database Contract

```text
DOCUMENT_SCHEMA_DECISION=NO_SCHEMA_CHANGE_REQUIRED
MIGRATION_ADDED=NO
MIGRATION_MODIFIED=NO
ALEMBIC_HEAD_COUNT=1
DATABASE_HEAD=20260924_request_cargo_items
DATABASE_CURRENT=20260924_request_cargo_items
DATABASE_PENDING=NO
```

The user's behind local development database was not used as qualification authority. No production database was contacted.

## S. Reference Re-check

Before PASS, PDR-020, ADR-050, ADR-030, ADR-047, FDD-001, FDM-001, the Canonical Business Object Catalog, Decision Index, Forwarder and operational architecture baselines, S6 Golden Journeys, the approved implementation design, LPAF v2.2 Agent Entry/Architecture and the v2.3 Product Integration governance gate were rechecked.

The implementation changes runtime authorization, additive opaque APIs, projections and UI behavior only. It does not change an approved product truth, domain owner, readiness owner, data owner or schema contract.

```text
REFERENCE_IMPACT_FINAL=NONE
```

## T. Scope Integrity

```text
DOCUMENT_MANAGING_ACTOR=OWNING_TRANSPORT_EXPERT_ONLY

DOCUMENT_MULTI_FILE_ENABLED=YES
DOCUMENT_APPEND_ENABLED=YES
DOCUMENT_TARGETED_REPLACE_ENABLED=YES
SYSTEM_PRESERVES_DOCUMENT_VERSION_HISTORY=YES
DOCUMENT_FAILED_FILE_RETRY_ENABLED=YES
SUCCESSFUL_FILES_REUPLOADED_ON_RETRY=NO
UNKNOWN_UPLOAD_AUTOMATIC_RETRY=NO

CUSTOMER_DOCUMENT_MANAGEMENT_ALLOWED=NO
ADMIN_MANAGER_DOCUMENT_MANAGEMENT_ALLOWED=NO
OTHER_SAME_ORG_EXPERT_DOCUMENT_MANAGEMENT_ALLOWED=NO
CROSS_TENANT_DOCUMENT_MANAGEMENT_ALLOWED=NO

EXPERT_REASSIGNMENT_WORKFLOW_ADDED=NO

DOCUMENT_SCHEMA_CHANGE_REQUIRED=NO
PRODUCT_MIGRATION_ADDED=NO

CONTROL_TOWER_BEHAVIOR_CHANGED=NO
NOTIFICATION_ACTIVATION_CHANGED=NO
CARGO_OPTIONALITY_CHANGED=NO

PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
```

## U. Remaining Risks

- UNKNOWN outcomes intentionally have no durable receipt or cross-session exactly-once correlation; the truthful recovery action is authoritative refresh/inspection.
- The repository retains pre-existing deprecation warnings, 13 lint warnings, a stale Browserslist-data warning and a large frontend chunk warning. They are not functional failures and were not expanded into this bounded build.
- Existing integer Request document routes remain compatibility-only; the new UI uses opaque Request, requirement-definition and file identities.

## V. Verdict

**PASS — EXPERT-ONLY MULTI-FILE DOCUMENT WORKFLOW COMPLETE**
