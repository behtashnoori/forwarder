# Expert-Only Multi-File Documents — LPAF-Governed Implementation Design

**Status:** Implementation design complete; bounded Build authority depends on the verdict in this artifact

**Design date:** 2026-09-20

**Canonical parent:** `ed6d0d9954b273f35f8f4ebc8f9ec5008cd82d6f`

**Governing baseline:** LPAF v2.2 and its mandatory Agent Entry Protocol, with the v2.3 Product Integration / `REFERENCE_IMPACT` gate applied as the Forwarder strong default

**Artifact class:** Level B combined Mission Contract and implementation design

**REFERENCE_IMPACT:** `NONE`

**REFERENCE_IMPACT_STATUS:** `CLOSED_FOR_DOCUMENTS_DESIGN`

**DOCUMENT_SCHEMA_DECISION:** `NO_SCHEMA_CHANGE_REQUIRED`

**Expected migration:** No

This is the repository's single Mission Contract and implementation-design artifact for the capability. It follows the established combined-artifact convention under `docs/operational/design/`; no duplicate governance form is created. It changes no runtime, test, migration, database, deployment, Production system, or LPAF framework.

## A. LPAF Mission / Outcome

### A.1 Mission

Design the smallest correct Golden-controlled implementation that lets only the active owning Transport Expert manage several immutable files under one logical document requirement, append new sibling files, replace one explicitly selected current file while the System preserves history, and retry only a file whose upload is known to have failed.

### A.2 Outcome

A later Build can implement the accepted PDR-020 / ADR-050 behavior without inventing a batch transaction, replacing every sibling, granting Customer or Admin write authority, weakening private storage or validation, changing Shipment ownership, making file count equal readiness, or importing the FWD-07 donor wholesale.

The resulting contract is:

```text
DOCUMENT_MANAGING_ACTOR=OWNING_TRANSPORT_EXPERT_ONLY
SYSTEM_PRESERVES_DOCUMENT_VERSION_HISTORY=YES
MULTI_FILE_UNIT_OF_WORK=ONE_EXISTING_SINGLE_FILE_REQUEST
APPEND_PRESERVES_CURRENT_SIBLINGS=YES
REPLACEMENT_TARGET=ONE_EXPLICIT_CURRENT_FILE_VERSION
KNOWN_FAILED_FILE_RETRY=FAILED_FILE_ONLY
AMBIGUOUS_UPLOAD_OUTCOME_IS_FAILURE=NO
ONE_TRANSPORT_EXPERT_PER_SHIPMENT=YES
EXPERT_REASSIGNMENT_WORKFLOW_APPROVED=NO
```

### A.3 Scope

In scope for the later Build:

- the existing Request/Case Documents route, service, `CaseDocumentsTab`, and Request Detail entry;
- multi-selection implemented as bounded independent calls to the existing single-file upload operation;
- explicit append and explicit targeted replace actions;
- current-file and per-lineage history presentation;
- truthful per-file queue outcomes and retry of a known failed item only;
- owning-Expert-only mutation guards on both Request/Case-owned and Shipment-owned document mutation paths;
- preservation of separately governed Expert and same-organization Admin/Manager read/download behavior;
- safe Unicode display filenames while storage keys remain generated and private;
- focused authorization, concurrency, storage, readiness-regression, frontend, PostgreSQL, and browser evidence.

Out of scope:

- Customer or Admin/Manager document management;
- Expert reassignment, former-Expert access, or document handoff;
- generalized Customer/stakeholder read visibility;
- a batch backend endpoint or all-or-nothing multi-file transaction;
- durable failed-upload evidence, resumable upload, cross-device recovery, or the donor ADR-049 operation lifecycle;
- changing document catalog values, configured file caps, assessment policy, retention, legal hold, purge, signature, malware scanning, OCR, preview, ZIP/bulk download, or public links;
- a second document store, physical modular extraction, generic DMS, migration, deployment, or Production access.

### A.4 Applicable LPAF lifecycle and rigor

This is an LPAF Level B Product/Production design mission covering M0 Mission through M4 Solution. M5 Build, M6 Verify, M7 Release, M8 Operate, and M9 Improve are specified as future evidence gates but are not executed here. Applicable MUST controls are evidence before assertion; explicit owner/SOR; domain-chain and history semantics; end-to-end positive and negative authorization; compatibility; normal user journey; reference-impact declaration; and recoverable verification evidence.

### A.5 Mission gate

| Gate | Design result |
| --- | --- |
| MISSION | Bounded expert-only multi-file document completion against Golden |
| OUTCOME | Buildable append, targeted replace, system history, known-failure retry, and preserved read policy |
| CAPABILITY_OWNER | Product — Documents & Collaboration; Document system owns file/history mechanics |
| SYSTEM_OF_RECORD | Persisted parent owns authority; `CaseDocumentRequirement`, `CaseDocumentFile`, `ArtifactAssociation`, and `OperationalDocumentRequirement` retain their bounded SOR roles |
| ACTOR / ENTITLEMENT | Active owning Transport Expert only for mutation |
| TENANT / DATA SCOPE | Server-derived parent Organization and parent/file lineage; non-disclosing cross-tenant denial |
| USER JOURNEY | Normal Shipment/Case navigation → Documents → add/append/replace/history/retry → leave/reopen |
| STATE OWNER | Document service owns file current/history state; MDPM owns readiness; parent owns management authority |
| HISTORY OWNER | System |
| STORAGE OWNER | `PrivateDocumentStorage` owns private bytes; Document service owns metadata and transaction compensation |
| READINESS OWNER | MDPM / `OperationalDocumentRequirement` policy and exact-version association |
| UPSTREAM / DOWNSTREAM | Parent ownership and requirement snapshot upstream; readiness, operational transitions, references, and evidence consumers downstream |
| MODULE BOUNDARY | Parent authorization → document command/validation/storage/history → explicit MDPM exact-version association |
| PUBLIC CONTRACT | Opaque parent/definition/file identities; no storage key, raw path, internal DB identity, or client-supplied owner as authority |
| API IMPACT | Additive projection fields and explicit target input; existing single-file commands remain the transaction boundary |
| SCHEMA IMPACT | None |
| COMPATIBILITY IMPACT | Existing rows, bytes, version numbers, history, numeric compatibility routes, and read visibility remain valid |
| ACCEPTANCE CONTRACT | One/many/append/targeted replace/history/partial result/retry/readiness/history compatibility |
| NEGATIVE AUTHORIZATION CONTRACT | Customer, Admin/Manager mutation, same-org non-owner Expert, other tenant, inactive/revoked actor, forged parent/child, stale/non-current target denied |

### A.6 Facts, assumptions, unknowns, and decisions

**FACT:** the required Golden worktree was clean before branching; local and refreshed remote canonical refs were equal at `ed6d0d9954b273f35f8f4ebc8f9ec5008cd82d6f`; the current commit is the Documents reference-reconciliation commit; Alembic reports exactly one repository head, `20260924_request_cargo_items`.

**FACT:** Golden already stores several active immutable `CaseDocumentFile` rows under one `CaseDocumentRequirement`, enforces the requirement's active-file cap under a row lock, assigns a unique requirement-scoped version sequence, retains superseded bytes, and records `superseded_by` and audit events.

**FACT:** the current Request Documents UI selects one file and invokes replace whenever any active file exists; the current replace route chooses the latest active row rather than a user-selected target.

**FACT:** current MDPM readiness selects one explicit active exact-version association for an `OperationalDocumentRequirement`; it does not count all files in the Request requirement.

**FACT:** current Request document upload has no idempotency receipt. The Shipment-owned free-title upload path does use `OperationalIdempotency`, but that does not make Request upload recovery solved.

**ASSUMPTION:** none is used to broaden actor, visibility, retention, catalog limits, reassignment, or schema authority.

**UNKNOWN:** generalized Customer/stakeholder read visibility and retention/purge remain separately Proposed under PDR-008/ADR-020 and PDR-011. They are not required for this Build.

**DECISION NEEDED:** none blocks the bounded known-failure implementation. Exactly-once recovery after an ambiguous lost response remains a future reliability decision and must not be represented as current-release behavior.

## B. Authoritative References

This design is derived from, and does not supersede:

- LPAF v2.2 Architecture Framework and Agent Entry Protocol;
- LPAF v2.3 Product Integration governance as a strong default;
- PDR-020 Owning-Expert-Only Document Management;
- ADR-050 Owning-Expert Document Management and System-Owned History;
- ADR-030 MDPM Document Readiness Policy;
- ADR-047 Fixed Responsible Transport Expert per Operational Shipment;
- ADR-010 Idempotency and Optimistic Locking, without importing an unaccepted upload-recovery design;
- FDD-001 Documents target vocabulary;
- FDM-001 Documents owner/SOR boundary;
- Canonical Business Object Catalog entries for DocumentArtifact, DocumentAttachment, DocumentVersion, and DocumentRequirement;
- the Decision Index, Forwarder Architecture Baseline, Operational Architecture Baseline, and S6 Golden Business Journey E;
- `docs/operational/evidence/documents-reference-reconciliation-20260920.md`;
- `docs/operational/evidence/post-d2-product-gap-review-20260920.md`, especially the accepted no-migration Request Documents completion boundary.

The FWD-07 lineage `811bbbaed5d2eb48c5f713b88991ce73b80c20b8` through `a778bc8516e2d71b8665acd046191fbc5f0493e8` is donor evidence only.

## C. Reference Impact

```text
REFERENCE_IMPACT = NONE
REFERENCE_IMPACT_STATUS = CLOSED_FOR_DOCUMENTS_DESIGN
```

Rationale: PDR-020, ADR-050, FDD-001, FDM-001, the Canonical Catalog, architecture baselines, and S6 already establish the actor, parent authority, owner/SOR split, multi-file/append/targeted-replace behavior, system-owned history, known-failure retry, readiness boundary, and user journey. This artifact selects the smallest implementation shape within that accepted truth. It changes no Product outcome, authority, data owner, lifecycle, visibility, reassignment rule, retention rule, or public promise.

Reference impact becomes `UPDATE_REQUIRED` and Build stops if implementation requires Customer/Admin mutation, a different owning actor, replace-all, inherited assessment, generalized read visibility, a new retention/scanner promise, durable lost-response recovery, or a new requirement-readiness rule.

## D. Existing Golden Document Inventory

| Area | Exact current Golden behavior | Design consequence |
| --- | --- | --- |
| Logical Request requirement | `CaseDocumentRequirement` is an immutable Request snapshot of definition code/revision, required flag, formats, maximum size, maximum active count, and sort order | Reuse; one requirement may own several active file rows when its snapshotted cap permits |
| Operational requirement | `OperationalDocumentRequirement` is the Shipment-level readiness policy snapshot with applicability, required assessment level, target transition, active/version state | Remains readiness SOR; it is not a binary/file row |
| Physical file/version | `CaseDocumentFile` contains opaque `public_id`, parent/tenant ownership, requirement link, generated storage key, filename/type/size/hash, requirement-scoped `version_number`, status, uploader/time, supersession, and logical-deletion metadata | Reuse as one immutable physical version; do not add a parallel version table |
| Multiple active files | No unique constraint limits a requirement to one active row; service counts active rows and compares with `max_active_file_count` while locking the requirement | Backend capability exists; frontend reachability is missing |
| Current marker | `status='active'`; historical replacement uses `status='superseded'`; logical deactivation uses `status='deleted'` | Reuse; historical rows do not become current again |
| Version allocation | `max(version_number)+1` under a requirement lock; `(case_requirement_id, version_number)` is unique | Reuse as immutable requirement-local sequence; derive per-lineage ordinal for presentation |
| Replacement | Service can replace a supplied row and writes `old.superseded_by=new.id`, but the Request route supplies the latest active row implicitly | Keep service primitive; make target `public_id` mandatory and remove latest fallback |
| Append | Existing `/files` operation inserts one independent active row without superseding siblings | Reuse unchanged as the per-file command |
| Request upload | One multipart file per request; each call validates and commits independently | Use bounded sequential calls for multi-selection; no batch endpoint |
| Shipment-owned upload | Existing free-title Shipment path is one-file, fixed 25 MiB, all detected formats, requires `Idempotency-Key`, accepts an explicit replacement public ID in the backend; its UI exposes append only | Preserve as a separate compatibility surface; apply owning-Expert-only mutation guard and regression tests |
| Formats | Detected allowlist is JPEG, PNG, WebP, PDF, DOCX, XLSX; the requirement snapshot supplies the allowed subset | Validate every file independently; never trust browser MIME alone |
| Size | Requirement snapshot controls size; definition validation permits 1 byte through 100 MiB. Request miscellaneous and Shipment free-title uploads use 25 MiB | Preserve all existing limits; no global increase |
| Active count | Requirement snapshot controls the cap; definition validation permits 1–100. The governed international catalog package currently has 46 definitions, each at one active PDF of 10 MiB | Multi-file is available only where configured; this Build does not alter catalog values |
| Filename | Request path currently uses `secure_filename`, one allowed extension, and a generated safe download name; generated random storage identity is separate | Reimplement the donor's safe Unicode display-name concept while retaining path/control/separator/extension checks and generated storage keys |
| Content validation | Magic/structure checks inspect JPEG/PNG/WebP/PDF and bounded DOCX/XLSX packages; extension must match detected content; empty, spoofed, malformed, oversize, and disallowed content fails | Preserve and test; multi-select does not weaken validation |
| Storage | Private configured root; generated partition/name; temporary exclusive write, SHA-256, flush/fsync, atomic replace; failed DB transaction removes the final binary | Preserve; never expose `storage_key` or path |
| Uploader/time | `uploaded_by` and `uploaded_at` are persisted; Request projection omits uploader display, Shipment projection includes actor label and recorded time | Add governed uploader label and time to internal Request projection/UI without exposing internal user ID |
| Audit | Request path records upload, supersession, download, and logical deletion in `DocumentAuditEvent`; Shipment path records upload/deactivation in `OperationalAudit` | Preserve; add explicit append/replace outcome details/correlation without binary/path data |
| Download | Parent is authorized first; child must belong to that parent; private path is revalidated; Request active and superseded rows are downloadable, deleted rows are not; Request download is audited | Preserve current/history download and its read policy; add opaque file route, keep numeric route compatibility-only |
| Delete/deactivate | Logical status change with actor/time/reason; bytes and row remain; current UI offers it only for active rows | Preserve as logical deactivation, not physical purge; do not fold it into replace |
| Request summary | `complete=bool(active_files)` and summary counts requirements with at least one active file | Treat as `has_current_file`, not operational readiness or approval |
| MDPM association | `ArtifactAssociation` binds an exact file/version; association replacement supersedes the old association; assessment binds to that association | Preserve exact-version semantics and independent reassessment |
| MDPM readiness | Service chooses one active association and its latest assessment. Missing/superseded/deleted exact version is not ready | Preserve one selected exact-version rule for this slice; extra sibling files are eligible choices, not automatic readiness inputs |
| Case Documents UI | One file input; when any current file exists it calls `/replace`; flat active rows; history includes all versions and can repeat active rows; no uploader/time/status queue | Replace with explicit Add files, per-file Replace, per-lineage History, and transient queue |
| DocumentReadiness UI | Lists eligible active typed Request files; lets user select one association and assess it | No functional redesign required; add regression evidence that superseded history cannot satisfy readiness |
| Customer/public projection | No Customer/Public Documents file list, history, or download projection exists; public tracking does not expose these files | Keep unchanged |

Current tests already prove immutable storage/history, active and superseded authorized downloads, audit, cross-case/guessed-ID denial, Organization Admin read, unassigned Expert denial, fault compensation, and PostgreSQL cap/version/replacement races. They also deliberately characterize the current single-file auto-replace UI when cap is greater than one.

## E. Actor / Entitlement

| Actor | Read current/history | Upload/append | Targeted replace | Retry known failure | Deactivate | Result |
| --- | --- | --- | --- | --- | --- | --- |
| Active owning Transport Expert | Preserve current governed access | Allowed | Allowed | Allowed | Allowed under current logical-deactivation policy | Parent-derived authority plus state validation |
| Same-org non-owning Expert | Denied under current document paths | Denied | Denied | Denied | Denied | Membership is not ownership |
| Same-org Admin/Manager | Preserve current tenant-scoped oversight/read where already authorized | Denied | Denied | Denied | Denied | Read authority never becomes manage authority |
| Customer | No new visibility | Denied | Denied | Denied | Denied | No Customer Documents management or projection is added |
| Other tenant | Denied non-disclosively | Denied | Denied | Denied | Denied | Server-derived tenant fence |
| Inactive/revoked actor, including recorded owner | Denied | Denied | Denied | Denied | Denied | Live identity and exactly one active membership required |
| Platform Admin | No implicit tenant-work read | Denied | Denied | Denied | Denied | Platform authority is not tenant document authority |

The current runtime is drift because Request document mutations reuse `can_access_request_detail`, allowing Organization Admin with `request.read`, and Shipment `document.manage` aliases `operational_shipment.create`, also permitting eligible Organization Admin. Accepted-Quote Shipment authority also still follows the current Request assignee rather than the immutable Shipment owner required by ADR-047. Build must correct these mutation paths without reducing their approved read paths.

## F. Read vs Manage

Current authoritative runtime read inventory:

| Actor | Request/Case list/history/download | Shipment document list/download |
| --- | --- | --- |
| Owning Expert | Allowed through current assigned-Request policy | Allowed for current accepted-Quote Request assignee or Direct Shipment responsible Expert; accepted-Quote derivation is ADR-047 drift |
| Customer | No Documents endpoint/projection | No Documents endpoint/projection |
| Admin/Manager | Same-organization read/download is allowed when the current parent read capability permits it | Same-organization read/download is allowed when current operational Shipment read capability permits it |
| Other same-org Expert | Denied; no assignment means no Request document access | Denied for `document.read`; project-derived `shipment.read` does not expand document read |
| Other tenant | Denied before child serialization; Shipment path uses non-disclosing 404 | Denied non-disclosively |

Build separates `document.read` from `document.manage`. Read/list/history/download continue through the current accepted parent-read policy. Every mutation uses a new explicit owning-Expert document-management policy. UI capability visibility follows the same distinction: an authorized Admin/Manager reader may see documents but sees no Add, Replace, Retry, or Deactivate control.

No Customer-safe projection is inferred. PDR-008/ADR-020 remain the only future path for generalized visibility.

## G. Owner / SOR and Module Boundary

| Concern | Owner | System of Record / compatibility authority |
| --- | --- | --- |
| Product capability | Product — Documents & Collaboration | PDR-020 / ADR-050 |
| Request/Case mutation authority | Authoritative persisted Case/Request owning Expert | `ShipmentRequest` parent assignment within the Case scope |
| Shipment mutation authority | Operational Shipment boundary | `OperationalShipment.primary_responsible_expert_id` target under ADR-047; no Request reassignment inheritance |
| Logical requirement | Parent/document policy | `CaseDocumentRequirement` and, for readiness, `OperationalDocumentRequirement` |
| Physical file/version metadata | Document system | `CaseDocumentFile` |
| Version/history | Document system / System | immutable rows, `status`, `version_number`, `superseded_by`, audit, retained private bytes |
| Contextual exact-version use | Parent/document association policy | `ArtifactAssociation` |
| Binary custody | Private document storage | generated private object/path identity |
| Readiness | MDPM | `OperationalDocumentRequirement`, one selected current exact-version association, assessment policy |

The module boundary is enforced in services, not by a physical refactor:

```text
persisted parent + live actor/membership
  -> document management policy
  -> one file command
  -> validation + private storage + CaseDocumentFile + audit transaction
  -> current/history read projection
  -> optional explicit MDPM exact-version association
  -> derived readiness
```

A file ID, definition ID, Project membership, stale list result, cached authorization, client owner/tenant field, or storage key cannot establish authority.

## H. Requirement / File / Version / Readiness Model

| Concept | Precise design meaning |
| --- | --- |
| Logical Document Requirement | One immutable parent-scoped evidence-policy snapshot: title/type, required flag, allowed formats, maximum size, maximum active files. It is not a file or a readiness result. |
| Logical File | One append root plus zero or more targeted replacement successors. It is a derived lineage over existing file-version rows, not a new table or parallel domain concept. |
| Physical File / File Version | One immutable `CaseDocumentFile` row and private binary. Every replacement produces another row; bytes/checksum/version identity never mutate. |
| Current file | The terminal lineage member with `status='active'`. A requirement may have several current logical files. |
| Historical file | A prior lineage member with `status='superseded'`, or a logically deactivated row under current policy. It remains system history but is not current evidence. |
| Readiness state | Derived MDPM result over applicability, one explicitly selected current exact-version association, and its assessment. It is not derived from raw active-file count. |

Existing `version_number` is a monotonic sequence within the requirement, so two independent roots may be recorded as versions 1 and 2 and a replacement of the first as version 3. The public projection must additionally derive `lineage_version` (`1`, `2`, ...) by walking the existing supersession chain. `logical_file_public_id` is the opaque public ID of the root row, derived rather than persisted. No internal numeric ID is shown to users.

If traversal finds a cycle, a missing successor inside an otherwise claimed chain, two predecessors for one successor, a cross-parent link, or a nonterminal active member, serialization and replacement fail closed and Build stops for data adjudication. No synthetic history is generated.

## I. Multi-File

The backend already supports:

```text
CaseDocumentRequirement
  -> current root A
  -> current root B
  -> current root C
```

The future UI may select several files only when the snapshotted requirement allows remaining capacity. Each selection becomes a separate request in user selection order. The server independently locks the requirement, re-counts current active rows, validates the file, and either commits that file or returns its own error. A concurrent upload or smaller remaining cap may therefore produce a truthful mixed outcome.

The Build does not alter `max_active_file_count`. The current international catalog's cap of one means its requirements remain single-current-file until separately governed policy/configuration changes them. A custom or later governed requirement with cap three may hold `page1.jpg`, `page2.jpg`, and `bill-of-lading.pdf` together.

## J. Append

Append is the existing single-file `/files` command with no replacement target.

Starting state:

```text
A(current), B(current)
```

Appending C yields:

```text
A(current), B(current), C(current)
```

No status, version relation, assessment, or audit fact on A/B changes. The new row is a new logical-file root, receives the next requirement-scoped version number, its own private bytes and metadata, and an append audit fact. Append at the cap returns a stable known failure and does not change siblings.

## K. Targeted Replace

Replacement uses the same one-file service operation with a mandatory opaque `replaces_file_public_id`. The server must:

1. authorize the parent and actor before looking up the child;
2. lock the requirement and selected target;
3. prove target tenant, parent, requirement, and `status='active'`;
4. validate the new file fully before changing target state;
5. write a new immutable row with the next requirement sequence;
6. set only the selected target to `superseded`, record time and `superseded_by`;
7. record upload and targeted-supersession audit facts;
8. commit, or compensate the new binary and preserve the old current row on any failure.

Example:

```text
A(current), B(current)
replace target=A with A2

A(superseded -> A2), A2(current), B(current)
```

The route must not query “latest active” as a substitute for a target. A missing, foreign, deleted, already-superseded, or concurrently replaced target returns a stable conflict/not-found result and creates no new current file. Replacement does not consume an additional active-count slot.

## L. Version History

History is system-owned and immutable:

- `CaseDocumentFile.public_id` is the version identity;
- `status` is the current/history availability marker;
- requirement-scoped `version_number` is the immutable recording order;
- `superseded_by` is the existing forward successor relation;
- the inverse relation derives the predecessor and root;
- `DocumentAuditEvent` records append, upload, targeted supersession, download, and deactivation facts;
- old private bytes remain present and can be downloaded only through current authorized history-read policy.

The service creates every successor fresh and permits a replacement only for one locked active target, which prevents branching in the command path. It never accepts an arbitrary successor supplied by the client. The existing PostgreSQL concurrent-replacement test shape is retained and extended to two sibling roots so the loser cannot alter either chain.

History UI is grouped under its logical current file. The current row is not duplicated inside its own historical list. A fully deactivated lineage appears in a separate inactive-history group where current read policy permits it.

## M. Partial Failure / Retry

The selected files are not one business transaction. The client uses a sequential queue over the existing safe one-file API:

```text
A -> 201 SUCCEEDED
B -> definitive validation/storage response FAILED
C -> 201 SUCCEEDED
```

Result:

```text
A=PRESERVED
B=FAILED_AND_RETRYABLE_IF_ERROR_CLASS_PERMITS
C=PRESERVED
RETRY_TARGET=B_ONLY
```

Queue states are `queued | uploading | succeeded | failed | unknown`. The queue retains each selected `File` object only in browser memory for the active page. A Retry button is attached to the failed item and resubmits only that item; A/C are never rebuilt or resubmitted. A corrected file selection is a new queue item.

Failed state is frontend transient state. The backend persists only governed successful files, audit facts, and existing failure logs/telemetry; it does not create a fake `CaseDocumentFile` or fake history row for B. A stable server response that proves no commit (validation, cap, stale target, or compensated storage/transaction failure) is a known failure. Authorization denials are definitive but not retryable without restored authority.

No batch endpoint, batch table, or batch rollback is introduced.

## N. Lost Response / Ambiguous Commit

Current evidence is explicit:

- Request/Case upload has no idempotency key or durable operation receipt;
- an accepted upload can commit and the client can lose the response;
- list/read may reveal a similar new row, but filename and checksum cannot prove intent because intentional identical append is valid;
- Request `version_number` and history identify committed rows but do not correlate a client attempt;
- the Shipment free-title upload's existing idempotency receipt protects only that separate endpoint and does not solve Request upload.

Therefore current Request idempotency plus list/read is **not sufficient for transparent exactly-once recovery**. Read-after-write is still useful for inspection but cannot prove which identical operation committed.

### Required for the current release

- Network abort, timeout, and any response that does not prove rollback are `unknown`, never `failed`.
- Unknown items expose `Refresh and inspect`, not `Retry`.
- The UI reloads the governed current list and highlights filename/time/type/size candidates without claiming correlation.
- The UI never automatically resubmits an unknown item and never tells the user it is safe to retry it.
- Only a definite failure receives the failed-file Retry action.
- If the user deliberately chooses a fresh append after inspection, it is presented as a new action that may create another valid identical file.

This prevents the current release from causing an accidental duplicate through blind automated retry, while honestly preserving the unresolved ambiguity.

### Future hardening

Stable per-file operation identity, durable receipt/query, cross-refresh/device discovery, staged-byte recovery, expiry/retention, and exactly-once replay require a separately accepted contract. The donor ADR-049 is Proposed evidence, not authority. Such a future choice may require an additive document-owned operation table and migration; it is not part of this design, schema decision, or Build verdict.

## O. Document Readiness

The governed rule for this slice is the existing ADR-030 exact-version subset rule:

```text
eligible current files under CaseDocumentRequirement
  -> Expert explicitly selects one file/version for OperationalDocumentRequirement
  -> one active ArtifactAssociation
  -> independent assessment of that exact version
  -> derived readiness
```

- Multiple current Case files are individually eligible candidates; they do not collectively or automatically satisfy the operational requirement.
- Exactly one selected active association is the governed subset for the current MDPM policy.
- Append of an unassociated sibling does not change readiness.
- Replacement of an unassociated sibling does not change readiness.
- Replacement of the associated exact version makes the old association ineligible because the file is no longer active; readiness becomes missing/superseded until the new exact version is explicitly associated and independently assessed.
- Historical superseded or deleted versions cannot satisfy readiness.
- A failed upload creates no eligible current file and cannot satisfy readiness.
- Request `complete=bool(active_files)` is only “has current file”; the UI must not label it approved, verified, or operationally ready.

Supporting several simultaneously assessed files as one composite readiness set would be a new policy decision and is outside this Build. `MORE_FILES_DOES_NOT_MEAN_MORE_READY` remains invariant.

## P. File Limits / Validation

Authoritative limits and behavior:

- formats detected by server: `jpeg`, `png`, `webp`, `pdf`, `docx`, `xlsx`;
- allowed subset: the frozen `CaseDocumentRequirement.allowed_formats`;
- maximum Request requirement size: frozen `max_file_size_bytes`, defined within 1 byte–100 MiB;
- maximum active Request files: frozen `max_active_file_count`, defined within 1–100;
- current governed international catalog: 46 definitions, each PDF-only, 10 MiB, active cap one;
- Request miscellaneous and Shipment free-title maximum: 25 MiB; no new count policy is invented;
- extension and detected content must match;
- filename must be a single safe Unicode NFC display name with no path/control semantics, one allowed final extension, and a maximum persisted length;
- DOCX/XLSX package entry count/member size/content-types remain bounded;
- zero-byte, malformed, spoofed, disallowed, oversize, and unsafe-name files fail individually;
- backend cap/validation remains authoritative despite frontend preflight.

The UI derives `accept`, size text, and remaining capacity from the requirement projection. If a selection exceeds known remaining capacity, it asks the user to reduce the selection instead of knowingly sending guaranteed failures. Races can still produce a per-file cap conflict and are reported truthfully.

## Q. API Contract

### Q.1 List current files and authorized history

Reuse `GET /api/expert/requests/{request_public_id}/documents`.

The additive target projection supplies:

- opaque requirement selector: DocumentDefinition `public_id` plus frozen source revision;
- configured limits and allowed formats;
- `has_current_file` (`complete` retained as a compatibility alias only);
- `current_files`, each with opaque version ID, derived logical-file/root ID, filename, safe type, size, upload time, governed uploader label, `current=true`, requirement recording sequence, derived lineage version, and targeted history;
- inactive lineages separately where current read policy permits;
- no storage key/path, internal database identity, raw membership ID, or client owner/tenant field.

Existing numeric `id` fields and integer routes remain compatibility-only during the bounded Build; the new UI does not display or treat them as authority. The handler adds an opaque selector route resolved by `(request, definition_public_id, frozen revision)` rather than creating a requirement-identity table.

### Q.2 Upload / append

Reuse the existing single-file requirement upload handler. Its canonical opaque-selector form is:

```text
POST /api/expert/requests/{request_public_id}/document-requirements/{definition_public_id}/files
multipart: file, source_definition_revision, optional description
```

No replacement field means append. One request contains one file and returns one `201` file projection. The existing integer route delegates to the same handler for compatibility.

### Q.3 Targeted replace

Use the same handler and add:

```text
replaces_file_public_id={selected current version public_id}
```

The existing `/replace` route remains a compatibility adapter but must require the same explicit field and call the same service. Missing target returns `422 REPLACEMENT_TARGET_REQUIRED`; there is no latest-active fallback. Changed/non-current target returns `409 REPLACEMENT_TARGET_CHANGED`; foreign or mismatched lineage is non-disclosing.

### Q.4 Download current/historical

Add an opaque route handled by the existing download service:

```text
GET /api/expert/requests/{request_public_id}/documents/{file_public_id}/download
```

It serves active or superseded versions after parent-first read authorization and child-lineage/storage revalidation. Deleted/unavailable versions remain unavailable. The numeric route is compatibility-only.

### Q.5 Delete/deactivate

Use the same opaque file selector with `DELETE` and mandatory reason. Behavior remains logical deactivation with retained row, bytes, and audit; no physical purge. This action uses manage authorization. It is not replacement and cannot create a successor.

### Q.6 Retry

There is no retry endpoint. A known retryable failure reuses the same single-file append or targeted-replace command for that queue item. An unknown outcome is not submitted again by the product.

### Q.7 Error contract

The Build adds stable codes while retaining the current error envelope compatibility. Minimum codes are:

`DOCUMENT_FILE_REQUIRED`, `DOCUMENT_FILENAME_UNSAFE`, `DOCUMENT_CONTENT_UNSUPPORTED`, `DOCUMENT_EXTENSION_MISMATCH`, `DOCUMENT_FORMAT_NOT_ALLOWED`, `DOCUMENT_FILE_TOO_LARGE`, `DOCUMENT_ACTIVE_LIMIT_REACHED`, `REPLACEMENT_TARGET_REQUIRED`, `REPLACEMENT_TARGET_CHANGED`, `DOCUMENT_PARENT_NOT_FOUND`, and `DOCUMENT_MUTATION_FORBIDDEN`.

Responses disclose no foreign parent/file existence. A file-level frontend outcome is derived from its own response; there is no synthetic batch response.

### Q.8 Shipment-owned compatibility surface

Existing `GET/POST/DELETE /api/internal/operational-shipments/{shipment}/documents...` remains. Its backend already uses opaque file identity, explicit replacement input, and `Idempotency-Key`. Build changes its mutation authorization to owning Expert only and preserves current read behavior. It does not convert the free-title Shipment collection into the Request requirement workflow or weaken its 25 MiB/content rules.

## R. Frontend UX

Use the existing Documents surfaces and normal navigation. The primary logical-requirement implementation is `CaseDocumentsTab` in Request Detail.

For each Requirement card show:

- title and required/optional label;
- allowed formats, maximum size, active count/cap, and `has current file` rather than a misleading readiness label;
- current file cards with filename, safe type, size, upload time, uploader label where authorized, current indicator, lineage version, Download, Replace, History, and current-policy Deactivate;
- requirement-level **Add files** with multi-select, disabled only when no capacity remains.

Replace belongs to one current file card and accepts exactly one replacement. It never appears as a requirement-level “new version/latest” action.

History expands beneath its logical file and shows immutable prior versions, status, time, uploader, version indicators, and authorized download. It does not duplicate unrelated siblings or the current row.

The transient queue shows one row per selected file:

```text
queued -> uploading -> succeeded
                   -> failed [Retry if retryable]
                   -> unknown [Refresh and inspect; no Retry]
```

Successful rows stay visible while siblings continue. Retry invokes only its item. Inputs reset only after their queue item is captured. Keyboard focus, `aria-live` outcome announcements, Persian/RTL layout, mobile wrapping, and meaningful empty/loading/error/denied states are required.

An Admin/Manager who reaches the existing read surface sees the same authorized current/history data in read-only mode with no mutation controls. Customer/public UI is unchanged.

## S. Authorization

Build introduces one document management policy separate from parent read policy.

For every mutation:

1. authenticate and reload the actor;
2. require active actor and exactly one active Organization membership;
3. resolve the opaque parent within that Organization before any child lookup;
4. require canonical `EXPERT` authority, never Platform or Organization Admin;
5. require actor equality with the persisted owning Expert of the routed parent scope;
6. resolve requirement and selected file only through that authorized parent;
7. prove tenant, parent, owner type, requirement, target current state, and non-quarantine state;
8. recheck under the transaction lock immediately before mutation.

Request/Case-owned file commands derive authority from the authoritative Case/Request parent. Shipment-owned commands derive authority from the fixed `OperationalShipment` responsible Expert. Request reassignment must not mutate an existing Shipment owner or grant Shipment-owned file management. If a required Shipment owner is null/ambiguous under current ADR-047 drift, the command fails closed; Build must not guess or fall back to Admin.

Required denials:

- same-org non-owning Expert;
- Organization Admin/Manager even with read/configuration capabilities;
- Customer;
- Platform Admin;
- other tenant;
- inactive/revoked actor or membership;
- forged tenant/owner input;
- known/guessed child ID with no authorized parent;
- parent/requirement/file mismatch;
- stale, superseded, deleted, or foreign replacement target;
- cached/listed authorization after revocation.

UI visibility is not a security boundary. Every route and service test must prove the server denial and absence of DB/storage/audit side effects.

## T. Storage / Security

Preserve:

- private storage rooted in configured non-public storage;
- generated storage partitions and names unrelated to display filename;
- exclusive temporary write, bounded streaming, SHA-256, fsync, atomic promote, and transaction compensation;
- canonical parent/file revalidation on download;
- server-side content detection and extension match;
- safe Unicode display metadata with separator/control/path rejection;
- no raw storage path/key, signed/public URL, binary body, token, or credential in API, UI, audit, or logs;
- upload/supersession/download/deactivation audit with actor, parent, file/version, outcome, and reason/correlation where applicable;
- existing quarantine checks and fail-closed unavailable-file behavior.

No malware-scanner certification exists in this slice. The Build neither claims one nor weakens current content validation. Adding scanning/quarantine workflow is a separately governed security capability.

## U. FWD-07 Classification

Nothing is merged, cherry-picked, or copied wholesale.

Vocabulary mapping: `CONTROLLED_REUSE` means the earlier gate's `REUSE_SEMANTICS`, and `REIMPLEMENT` means `REIMPLEMENT_AGAINST_GOLDEN`. `REJECT` and `NOT_NEEDED` are identical in both request sections.

| Donor file/behavior | Disposition | Golden use |
| --- | --- | --- |
| `case_document_service` use of existing many active rows and independent `/files` calls | `CONTROLLED_REUSE` | Semantics already exist in Golden; retain current service/storage foundation |
| `CaseDocumentsTab` multi-select with sequential independent submissions | `REIMPLEMENT` | Rebuild against current Golden API, owning-Expert policy, cap, queue states, and unknown-outcome rule |
| Per-file saved/failed result concept and focused component/API tests | `REIMPLEMENT` | Extend to queued/uploading/succeeded/failed/unknown and an actual failed-item Retry button |
| Donor safe Unicode display filename normalization with generated private key | `CONTROLLED_REUSE` | Reapply the bounded metadata idea after Golden filename/content/path tests |
| Donor append reachability and same-name/different-bytes evidence | `CONTROLLED_REUSE` | Preserve semantics and port assertions to current Golden tests |
| Donor “replace latest” requirement action | `REJECT` | Target must be the selected current file public ID |
| Donor Request-assignment/Admin mutation behavior | `REJECT` | PDR-020/ADR-047/ADR-050 owning-Expert policy is authoritative |
| Donor reselect-only retry message | `REIMPLEMENT` | Retry only a retained known-failed queue item; unknown has no Retry |
| Donor lost-response browser finding | `CONTROLLED_REUSE` | Use as negative evidence proving unknown is not failure |
| Proposed ADR-049 operation table, staged lifecycle, 90-day discovery, tombstones, and cross-session recovery | `NOT_NEEDED` | Future hardening only; unaccepted and outside current Product scope |
| Donor no-schema/no-batch conclusion for known failure | `CONTROLLED_REUSE` | Confirmed independently against current Golden schema and accepted post-D2 reference |
| Mobile Request Detail repair/browser scenarios | `REIMPLEMENT` | Revalidate current Golden shell, tabs, RTL, and two viewports |
| Donor CI/dependency/migration-head repairs and cumulative safety harness | `NOT_NEEDED` | Current Golden has a different head/tooling baseline; use current qualification paths |

Disposition summary: reuse semantics and focused evidence; reimplement UI/tests and authorization against Golden; reject latest replacement and broader donor authority; leave the proposed recovery subsystem out of the current release.

## V. Schema Decision

```text
DOCUMENT_SCHEMA_DECISION = NO_SCHEMA_CHANGE_REQUIRED
EXPECTED_MIGRATION = NO
```

Evidence:

- several `CaseDocumentFile` rows may be active for one requirement;
- requirement rows persist type/size/count limits;
- every physical version has opaque identity, immutable metadata/bytes, version sequence, uploader/time, status, and audit;
- `superseded_by` plus status represents targeted forward history and existing data already uses it;
- requirement locking and a fresh successor row make the command lineage linear without a new logical-file table;
- one-file transactions already preserve successful siblings on later failure;
- `ArtifactAssociation` already binds the exact current version used by readiness;
- known failed upload state need not be durable business evidence;
- exactly-once ambiguous recovery is outside the current release.

No existing row is rewritten, backfilled, inferred, or moved. No parallel `DocumentVersion` concept is created. Authorization and orchestration changes alone do not justify a migration.

## W. Migration Design

Not applicable because `DOCUMENT_SCHEMA_DECISION=NO_SCHEMA_CHANGE_REQUIRED`.

The later Build must prove that no migration file changed, the repository still has exactly one Alembic head, and that head descends from the then-current canonical head (the design baseline head is `20260924_request_cargo_items`). A future accepted lost-response recovery design would require its own migration contract, upgrade/downgrade safety, populated-downgrade policy, historical compatibility, and PostgreSQL qualification; none is pre-approved here.

## X. Browser Journey

Browser evidence is specified, not executed in Design.

Primary owning-Expert journey at desktop and mobile RTL:

1. Log in as the active owning Expert through the normal login path.
2. Navigate through the normal Expert Requests/Shipment/Case list to the detail page and open Documents; no deep link is used as the primary proof.
3. Open a requirement configured with capacity at least four and select A, B, and C in one chooser.
4. Observe one queue row per file, three independent requests, truthful progress, and success; leave and reopen Documents and verify all three current files and metadata.
5. Use Add files to append D; verify A/B/C remain current and unchanged.
6. Choose A's own Replace action and upload A2; verify A2 is current, A is in A's history, and B/C/D are unchanged.
7. Download A historical and A2 current through the UI and verify the intended bytes.
8. Select valid E, invalid F, valid G; verify E/G remain successful, F is the only failed item, and no earlier file is resubmitted.
9. Retry only F with a valid correction; browser network evidence must show one request for that item and no A/B/C/D/E/G upload.
10. Exercise a delivery-abort/timeout characterization: show `unknown`, refresh current files, and prove no automatic retry or “failed” claim.
11. Leave through ordinary navigation, return, and verify current/history persistence.

Denial journey, where the existing browser harness supports the persona:

- log in as another same-organization Expert, navigate normally, and prove the target Case is absent or the known route is denied without document metadata; or
- log in as same-organization Admin/Manager with the accepted oversight read, open Documents, prove current/history is readable and every mutation control is absent, then prove a direct mutation request is denied in backend evidence.

Evidence records role/authority, tenant, environment, candidate commit, repository/Alembic identity, normal route sequence, network outcomes, assertions, and screenshots/logs without credentials, storage paths, or private file contents.

## Y. Acceptance / Negative Authorization

Future Build tests must prove at least:

1. owning Expert uploads one valid file;
2. owning Expert selects and uploads multiple files through independent commands;
3. append preserves every existing current sibling;
4. targeted replace changes only the selected logical file;
5. previous target version remains immutable, auditable, downloadable history;
6. successor becomes current and has the derived next lineage version;
7. sibling current files, bytes, metadata, status, and history are unchanged;
8. mixed success/failure preserves successes;
9. Retry invokes the failed item only;
10. Customer mutation is denied;
11. Admin/Manager mutation is denied while approved read remains unchanged;
12. same-org non-owning Expert mutation is denied;
13. other-tenant mutation/read is denied non-disclosively;
14. inactive/revoked actor and membership are denied at action time;
15. guessed child ID and parent/requirement/file mismatch are denied without side effect;
16. existing read visibility does not broaden or shrink;
17. readiness ignores superseded/deleted history and requires the selected new exact version to be associated and assessed;
18. historical Request files and existing replacement chains remain readable and compatible;
19. cap one still permits only one active root, while cap greater than one permits append only to the cap;
20. concurrent append at the last slot yields one success and one known cap failure without orphan bytes;
21. concurrent replacement of the same target yields one successor and one safe conflict; another sibling remains current;
22. invalid extension/content/size/name fails only that item;
23. same display filename with different bytes creates independent current roots; intentional identical append remains permitted;
24. safe Persian/Unicode display name round-trips while storage identity remains generated/private;
25. storage write/promote/flush/audit/commit failures leave no orphan current row/binary and preserve the prior target;
26. a lost response is shown as unknown and is not automatically retried;
27. Request summary `has_current_file` does not claim approval/readiness;
28. Customer/public tracking payloads remain unchanged;
29. Shipment-owned document upload/delete/replacement mutations also deny Admin/Manager and non-owner actors while current reads remain governed;
30. no migration diff exists and Alembic remains single-head.

Qualification in Build includes focused service/API/frontend tests, existing case-document fault and PostgreSQL suites extended for selected-target siblings, assigned-work/tenant/revocation regressions, MDPM readiness regressions, TypeScript/build/lint, two-viewport browser UAT, and the repository's current full affected gates. Tests must bind results to the implementation candidate; donor PASS is not Golden PASS.

## Z. Build Scope / Stop Conditions

### Z.1 Smallest planned Build scope

Backend:

- `backend/services/case_document_service.py`: safe Unicode display-name validation; explicit target replacement; lineage grouping/projection; uploader display; stable errors/audit details; retain storage transaction behavior;
- `backend/routes/case_documents.py`: separate read/manage authorization; opaque requirement/file selectors; one-file append/replace contract; apply owning-Expert mutation rule to Request and Shipment document paths;
- `backend/services/assigned_work_authorization.py` or one narrowly owned document-policy helper: encode document read versus manage without changing unrelated action semantics;
- `backend/services/shipment_document_service.py`: only the minimal management-guard/explicit-replacement consistency needed for the global PDR-020 rule;
- no expected functional change to `document_readiness_service.py`; add regression protection for exact-version invalidation.

Frontend:

- `src/components/CaseDocumentsTab.tsx`: Add files, per-file Replace/History, metadata, queue, failed-only Retry, unknown handling, RTL/mobile/accessibility;
- `src/lib/api.ts`: opaque additive types/routes and explicit replacement field;
- `src/pages/RequestDetail.tsx`: only if current tab reachability/responsiveness requires a bounded repair;
- `src/components/ShipmentDocuments.tsx`: mutation visibility/targeted replacement only as needed to enforce the accepted actor/action contract; do not merge it with MDPM.

Tests/evidence:

- existing case-document, fault-injection, schema-parity/current-head, PostgreSQL concurrency, authorization, MDPM, component, and browser suites extended according to section Y;
- no migration, no seed/catalog update, no broad modular refactor.

Shared hotspots are `backend/routes/case_documents.py`, `backend/services/case_document_service.py`, `backend/services/assigned_work_authorization.py`, `backend/models.py` as read-only schema authority, `src/lib/api.ts`, Request Detail, and the two Documents components. Build must avoid unrelated changes in these files.

### Z.2 Stop conditions

Stop Build and return to governance if:

- any authoritative reference conflicts with owning-Expert-only management or system-owned history;
- Customer/Admin/Manager write, another same-org Expert, owner transfer, reassignment, or former-Expert access is required;
- parent ownership cannot be derived unambiguously from persisted server state;
- implementation requires replace-latest, replace-all, destructive overwrite, or approval inheritance;
- multiple current files require raising a governed cap or changing the catalog rather than honoring the snapshot;
- readiness must assess all files or a composite subset instead of the accepted one exact-version association;
- a durable failed/unknown upload operation, exactly-once recovery, staged upload, or cross-session receipt is made current-release scope;
- a migration, synthetic history/backfill, file movement, second store, or parallel version model appears necessary;
- existing Admin/Manager read oversight or another approved read path would have to be removed;
- Customer/public visibility, retention/purge, legal hold, signature, scanner, preview/OCR, ZIP/bulk download, or public URL is required;
- safe parent-first authorization cannot prevent guessed-child and cross-tenant disclosure;
- current private-storage validation/compensation cannot be preserved;
- migration graph is not exactly one head or any runtime/test/migration change leaks into this design-only branch.

## Verdict

READY — DOCUMENTS IMPLEMENTATION MAY BEGIN
