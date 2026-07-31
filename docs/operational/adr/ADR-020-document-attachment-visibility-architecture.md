# ADR-020: Document Attachment and Visibility Architecture

- Status: Proposed
- Date: 2026-07-31

## 1. Context

Current case-document management provides immutable file metadata, private storage, requirement snapshots, versions, checksum, logical deletion, and audit at ShipmentRequest level. Multi-shipment Projects require documents at Project, OperationalShipment, ExecutionUnit, and event scopes, with stakeholder-specific visibility and safe single/bulk download. Copying binaries for every scope would create integrity, retention, and storage problems.

## 2. Decision

Separate **DocumentArtifact** from **DocumentAttachment** (link).

- DocumentArtifact owns one immutable binary and intrinsic metadata/checksum.
- DocumentAttachment links an artifact to one supported scope and carries contextual type, visibility, classification, ownership, approval, and tags.
- One artifact may have several attachments. A binary must not be duplicated merely because it belongs to several scopes.
- Supported attachment scopes are `project`, `shipment`, `execution_unit`, and `event`, using the same public identifiers defined by ADR-017 through ADR-019.

Document requirements remain policy snapshots. An attachment may satisfy a requirement only through an explicit validated relationship; filename or tag matching is insufficient.

## 3. Domain definitions

- **DocumentArtifact:** immutable stored binary plus storage key, safe filename, detected media type, size, checksum, signature metadata, uploader, and creation time.
- **DocumentAttachment:** scoped relationship from artifact to Project, OperationalShipment, ExecutionUnit, or OperationalEvent.
- **Document version:** immutable artifact/attachment revision in a lineage; replacement creates a new version and supersedes the prior active version.
- **Visibility:** audience policy: `internal`, `customer`, `carrier`, `customs_representative`, or `selected_stakeholders`.
- **Classification:** sensitivity/business classification independent of audience, governed by an approved catalog.
- **Approval status:** `not_required`, `pending`, `approved`, `rejected`, or `expired` unless a later policy refines the catalog.
- **Retention status:** `active`, `retention_hold`, `expired`, or `logically_deleted`.

## 4. Invariants

- Artifact identity and checksum are immutable; replacement creates a new artifact/version.
- Storage keys and sequential database IDs are never public authorization tokens.
- Every attachment has exactly one primary scope, organization, owner, document type, visibility, classification, and timestamps.
- Multiple attachments may reference one artifact without copying its binary.
- Visibility and classification are explicit and deny by default. Project visibility cannot override a more restrictive attachment/classification policy.
- `selected_stakeholders` contains explicit principal/party relationships; free-text recipient lists are not authorization.
- Metadata includes document type, version, owner, uploader, created/occurred date, visibility, classification, approval status, verifier, expiry, tags, checksum, digital-signature metadata, and retention status where applicable.
- Verification and approval record actor, time, evidence/reason, policy version, and event/audit references.
- Logical deletion removes normal availability but preserves metadata, audit, retention holds, and version lineage. Physical purge requires retention policy and an auditable privileged job.
- A deleted/superseded attachment cannot silently make an older unsafe version active.
- Download authorization is evaluated at request time for each attachment, including bulk jobs.

## 5. Security implications

Binary storage remains private and outside release/static roots. Downloads pass through authenticated/authorized services or short-lived scoped URLs. Authorization evaluates organization, scope resource, stakeholder relationship, visibility, classification, approval/retention status, and requested action. Customer projections are allowlisted and must never include internal attachments, storage keys, filesystem paths, or unrestricted signed URLs. Upload validates extension, detected media type, size, checksum, and malware policy when available. Bulk downloads apply limits, rate controls, expiry, audit, and per-item permission checks to prevent internal-file leakage.

## 6. Data and migration implications

Future additive design may treat current `CaseDocumentFile` as the initial artifact or bridge it to a new artifact identity, while `CaseDocumentRequirement` remains the Request-level policy snapshot. Existing `shipment_request_id` represents legacy request/case context and is not silently redefined as Project scope. New attachment/link records add canonical scopes. Current versions, hashes, storage keys, logical deletion, and audit are preserved. No schema or data change occurs in this phase.

## 7. API implications

Additive APIs provide paginated document inventories by scope, upload artifact plus attachment, attach an existing permitted artifact, replace/version, verify/approve/reject, single download, bulk-download job creation/status, and manifest retrieval. Mutations require idempotency, expected version where applicable, explicit permissions, and stable errors. Bulk selection is resolved server-side and frozen in an auditable job; clients cannot submit arbitrary storage keys. Existing expert case-document endpoints remain supported.

## 8. UI implications

Project, shipment, unit, and event views show documents within their actual scope and visibility. Staff see classification/approval/expiry badges and can preview the customer-visible set. Customers see only authorized attachments and never inactive internal versions. Bulk download shows scope, count, estimated size, excluded items, and expiry before confirmation. Version lineage and verification history are inspectable.

## 9. AI-native implications

AI receives extracted metadata/content only through a separate permission-checked processing policy; artifact access does not follow merely from Project access. Recommendations cite document public ID, version, classification-safe evidence, and expiry/completeness findings. Agent upload, attach, classify, approve, or download actions are explicit authorized commands with audit and human approval until policy permits otherwise. AI must not broaden visibility or select stakeholders autonomously without approved rules.

## 10. Alternatives considered

- Add nullable project/unit/event FKs directly to CaseDocumentFile: rejected because one artifact can belong to several scopes and nullable-polymorphic ownership becomes inconsistent.
- Copy binaries per scope: rejected due to storage waste, checksum/version drift, and retention ambiguity.
- Store visibility only on artifact: rejected because the same binary may be attached under different contextual permissions, subject to classification ceilings.
- Put documents in public/static storage: rejected due to leakage risk.
- Build ZIP synchronously in the request process for all sizes: rejected due to memory, timeout, and denial-of-service risk.

## 11. Consequences

Artifact integrity and storage are decoupled from business context and audience. Documents can safely span scopes without binary duplication. The model requires stronger permission evaluation, attachment/version lineage, retention governance, and asynchronous export capability.

## 12. Risks

- Conflicting visibility across attachments to the same artifact.
- Missing stakeholder lifecycle updates leaving stale access.
- Malware or active-content threats in office/PDF files.
- Large ZIP jobs exhausting CPU, disk, or bandwidth.
- Manifest leakage if it lists unauthorized filenames/metadata.
- Retention conflicts between scopes or jurisdictions.
- Digital signature metadata being mistaken for cryptographic verification without validation.

## 13. Backward compatibility

Current DocumentDefinition, CaseDocumentRequirement, CaseDocumentFile, DocumentAuditEvent, private storage, and expert routes continue to operate. Legacy files are represented as Request-context documents and may later receive Project/Shipment attachments through verified lineage. Existing binaries are not moved or duplicated during initial adoption. No immediate breaking API change is required.

## 14. Rollout strategy

Approve visibility/classification/retention catalogs; add public artifact identity and attachment model; bridge current files read-only; expose internal inventory; enable scoped uploads for a cohort; add customer projection after leakage tests; then add asynchronous bulk ZIP and manifests with quotas. Malware scanning and signature verification gates must be defined before claims of verified safety/authenticity.

## 15. Rollback strategy

Disable new attachment mutations and customer/bulk document projections; route staff to current case-document APIs; stop export workers; expire generated download links/packages; retain artifacts, attachments, audit, and manifests for reconciliation. Never roll back by deleting shared binaries.

## 16. Open questions

- Product Owner/Security: exact visibility and selected-stakeholder matrix.
- Compliance: classification catalog, retention periods, legal holds, and physical purge authority.
- Operations: maximum file, project download, ZIP size/count, and package expiry.
- Security: malware scanning engine, quarantine behavior, and active-content policy.
- Legal/Compliance: accepted digital signature standards and verification evidence.
- Product Owner: whether customer uploads are in scope and their approval workflow.
- Architecture: background worker/object-storage strategy for large exports.

## 17. Acceptance criteria for approving the ADR

- Artifact versus attachment separation and no-duplicate-binary invariant are approved.
- All four scopes use the same public identifiers as the other ADRs.
- Visibility, classification, stakeholder, approval, verification, expiry, and retention policies have named owners.
- Single and bulk download enforce per-item authorization and produce audit.
- Structured ZIP contains a permission-filtered manifest with checksum/version/scope and no internal metadata leakage.
- Current case-document models have an additive compatibility path.
- Logical deletion, retention hold, and physical purge responsibilities are distinct.
- Customer allowlist and negative leakage tests are mandatory before rollout.
