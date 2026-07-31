# Architecture Phase 0.5 Product Decision Register

- Status: Partially Accepted
- Date: 2026-07-31
- Reconciliation date: 2026-07-31
- Scope: Decision closure for ADR-017 through ADR-020
- Version impact in this documentation phase: None
- Database impact in this documentation phase: None
- Deployment impact in this documentation phase: None

## Purpose and decision protocol

This register makes Product decisions and unresolved choices explicit before implementation. A recommendation is not an approval unless the record explicitly identifies it as the Accepted decision. Each record's own status governs; this register currently contains Accepted, Deferred, and Proposed records.

`Blocks Slice 1` means Slice 1 must not enable the affected write path or claim the affected behavior is canonical before approval. A non-blocking decision may be deferred only with its stated fail-safe behavior active. No implementation may silently substitute an engineering assumption for a Product decision.

## PDR-001 — Project customer cardinality

- **Decision ID:** PDR-001
- **Topic:** Project customer cardinality and separation of commercial party roles.
- **Options:** (A) exactly one customer organization and no separate party roles; (B) one primary customer organization plus explicit payer, consignee, cargo-owner, and other party-role relationships; (C) multiple co-owning legal customers with equal Project authority.
- **Accepted option:** Option B. A Project has exactly one primary customer organization for ownership, authorization, and portfolio reporting. Payer, consignee, cargo owner, notify party, and other legal parties are separate typed relationships and do not automatically receive ownership or access. Multiple co-owners require a later explicit policy.
- **Rationale:** One security owner keeps tenant and customer authorization deterministic while typed party roles represent real commercial arrangements without conflating payment, custody, and visibility.
- **Operational impact:** Staff can coordinate several legal parties while escalation and responsibility retain one primary customer owner.
- **Security impact:** Party presence never grants access. Each non-owner party needs an explicit stakeholder grant and scope.
- **Data impact:** Project requires `primary_customer_organization_id`; typed Project-party relationships require role, validity period, and source/provenance.
- **Migration impact:** Additive. Legacy customer linkage may populate the primary owner only when unambiguous; ambiguous cases are quarantined for review.
- **UX impact:** Project header shows primary customer separately from payer, consignee, cargo owner, and other stakeholders.
- **AI-agent impact:** Agents may reason about party roles but must not infer authority from payer/consignee/cargo-owner status.
- **Decision owner:** Product Owner — Customer and Commercial Domain
- **Required approvers:** Product Owner, Operations Owner, Security Owner, Data Owner
- **Status:** Accepted
- **Acceptance date:** 2026-07-31
- **Blocking Slice:** Slice 1 — Project identity, ownership, access scope, and legacy backfill eligibility.
- **Default fail-safe behavior if unresolved:** Do not create canonical Projects or auto-group legacy records. Any read-only prototype treats one explicitly selected customer organization as owner and grants no access to other parties.

## PDR-002 — Project authority

- **Decision ID:** PDR-002
- **Topic:** Authority to create, close, cancel, and transfer Project ownership.
- **Options:** (A) admin-only for every action; (B) role- and state-based authority with elevated controls for destructive/sensitive actions; (C) any assigned expert; (D) customer self-service authority.
- **Accepted option:** Option B. `project.create` belongs to authorized Project Managers and Administrators. Normal close requires `project.close`, completion guards, and a reason when warnings remain. Cancel requires `project.cancel`, Operations Manager or Administrator authority, reason, expected version, and audit. Ownership transfer requires `project.transfer`, Administrator or designated Customer Governance Manager authority, target validation, reason, and two-person approval when the legal customer changes. Customer users may request these actions but cannot execute them initially.
- **Rationale:** Routine creation/closure should not bottleneck on administrators, while cancellation and legal ownership transfer need stronger segregation of duties.
- **Operational impact:** Defines accountable roles and avoids informal reassignment or status edits.
- **Security impact:** Requires deny-by-default permissions, organization scope, expected version, idempotency, reason, audit, and elevated approval for customer transfer.
- **Data impact:** Commands need actor, reason, version, approval, previous/new owner, and event/audit records.
- **Migration impact:** Existing assignment fields are not Project authority. New permissions and ownership history are additive.
- **UX impact:** Actions appear only when authorized; close/cancel/transfer use guarded confirmation and show unmet conditions.
- **AI-agent impact:** AI may recommend or prepare actions. It cannot close, cancel, or transfer without the same permissions and required human approval/policy.
- **Decision owner:** Product Owner — Operational Governance
- **Required approvers:** Product Owner, Operations Owner, Security Owner
- **Status:** Accepted
- **Acceptance date:** 2026-07-31
- **Blocking Slice:** Slice 1 — create authority and authorization model. Close/cancel/transfer commands may remain disabled until their workflow slice.
- **Default fail-safe behavior if unresolved:** No Project mutations. Read-only projections may be reviewed; close, cancel, transfer, and AI-prepared execution remain disabled.

## PDR-003 — Project identifier

- **Decision ID:** PDR-003
- **Topic:** Internal code, public tracking identity, visibility, and format.
- **Options:** (A) expose the sequential database ID; (B) one shared human-readable code for internal and public use; (C) separate internal project code and high-entropy public tracking code.
- **Accepted option:** Option C. Use an immutable opaque public ID for API/resource identity, an organization-local human-readable internal code such as `PRJ-YYYY-NNNNNN`, and a separate high-entropy public tracking code. Internal code is visible to authorized staff and may be shown to authenticated customers when Product approves; public tracking code is customer-shareable, revocable/rotatable through a controlled action, and never derived from database ID or internal code.
- **Rationale:** Separating operational reference from public capability reduces enumeration and permits public-code revocation without changing Project identity.
- **Operational impact:** Staff receive a searchable stable reference; support can rotate a compromised public code without renaming the Project.
- **Security impact:** Public code needs cryptographic entropy, rate limiting, non-enumerating errors, audit for rotation, and no embedded customer information.
- **Data impact:** Requires distinct immutable `public_id`, unique organization-scoped `project_code`, public tracking credential/hash or protected value, status, issued/rotated timestamps, and issuer.
- **Migration impact:** Additive; existing ShipmentRequest tracking codes are not silently promoted to Project codes. Compatibility links may remain.
- **UX impact:** UI labels clearly distinguish “Project code” from “Public tracking code” and avoid exposing internal numeric IDs.
- **AI-agent impact:** Agents use opaque IDs in actions, may display authorized internal codes, and must treat public codes as sensitive credentials rather than evidence.
- **Decision owner:** Product Owner — Project Experience
- **Required approvers:** Product Owner, Security Owner, Operations Owner
- **Status:** Accepted
- **Acceptance date:** 2026-07-31
- **Blocking Slice:** Slice 1 — Project API identity, uniqueness, search, and customer-safe design.
- **Default fail-safe behavior if unresolved:** Use only an opaque internal public ID in non-public prototypes; do not enable public Project tracking or expose sequential/internal codes.

## PDR-004 — Project completion rule

- **Decision ID:** PDR-004
- **Topic:** Delivered/cancelled combinations, partial completion, and forced closure.
- **Options:** (A) completed only when every unit is delivered; (B) completed when every non-cancelled active unit is delivered and at least one unit is delivered; (C) staff may mark completed regardless of children; (D) administratively closed as a separate control from operational completion.
- **Accepted decision:** Combine Options B and D. `completed` is derived when at least one ExecutionUnit is delivered and every active non-cancelled unit is delivered. Cancelled units remain visible in counts and may raise an attention alert but do not block completion. `partially_delivered` applies when at least one unit is delivered and at least one active non-cancelled unit is not delivered. If every active unit is cancelled, Project is `cancelled`. Forced closure never fabricates `completed`; it records a separate administrative closure state/flag, reason, actor, approval, and unresolved obligations.
- **Rationale:** Operational truth must not be overwritten for administrative convenience, while valid cancellations should not prevent completion of delivered scope.
- **Operational impact:** Dashboards distinguish fully delivered scope, partial delivery, all-cancelled Projects, and administratively closed exceptions.
- **Security impact:** Forced closure requires elevated permission, reason, expected version, audit, and potentially two-person approval.
- **Data impact:** Aggregate projection needs counts by unit lifecycle plus closure metadata independent from lifecycle status.
- **Migration impact:** Existing `attention_required` aggregate values must not be mapped to lifecycle status without reconciliation. Backfill is projection-only and additive.
- **UX impact:** Completion summary displays delivered/cancelled/remaining counts. Forced closure is visually distinct and never shown as successful delivery.
- **AI-agent impact:** AI may recommend closure with evidence but cannot convert unresolved/cancelled work into delivered state.
- **Decision owner:** Product Owner — Operational Lifecycle
- **Required approvers:** Product Owner, Operations Owner, Reporting/Data Owner, Security Owner for forced closure
- **Status:** Accepted
- **Acceptance date:** 2026-07-31
- **Blocking Slice:** Slice 1 — canonical aggregate status and acceptance tests.
- **Default fail-safe behavior if unresolved:** Never mark a Project completed automatically. Show a provisional derived summary and `completion_policy_unapproved`; forced closure remains unavailable.

## PDR-005 — ExecutionUnit code policy

- **Decision ID:** PDR-005
- **Topic:** Uniqueness scope, reuse after deactivation, and human-readable versus generated codes.
- **Options:** (A) globally unique user-entered code; (B) Project-local user-entered code with reuse; (C) generated Project-local canonical code plus optional external/vehicle references; (D) OperationalShipment-local code.
- **Recommended option:** Option C. Generate a stable human-readable canonical code unique within Project, for example `U-0001`, and retain it permanently, including after deactivation. Never reuse a canonical code. Store truck plate, container number, wagon number, booking reference, airway reference, warehouse lot, customs lot, and customer labels as typed external references that may have their own validation/uniqueness policies.
- **Rationale:** A generated immutable code avoids collisions and mutable real-world identifiers while remaining readable in bulk operations, ZIPs, reports, and customer communication.
- **Operational impact:** Units can be referenced consistently even when vehicle/container/booking assignment changes.
- **Security impact:** Unit codes are references, not authorization credentials; APIs still use opaque public IDs and scoped access.
- **Data impact:** Requires Project-scoped sequence/allocator, immutable canonical code, public ID, and typed external-reference collection.
- **Migration impact:** Existing legacy `unit_code` is preserved as a legacy/external reference unless it passes deterministic collision checks; canonical codes are generated during approved backfill.
- **UX impact:** Show canonical code prominently and external references with their type; prevent users from editing the canonical code.
- **AI-agent impact:** AI uses canonical codes for explanations and public IDs/versions for commands; it does not treat external identifiers as stable ownership keys.
- **Decision owner:** Product Owner — Execution Operations
- **Required approvers:** Product Owner, Operations Owner, Data Owner
- **Status:** Deferred
- **Deferral date:** 2026-07-31
- **Deferral reason:** ExecutionUnit is outside SLICE-001.
- **Slice disposition:** Deferred from SLICE-001; revisit for the authorized ExecutionUnit slice.
- **Default fail-safe behavior if unresolved:** Do not generate or rewrite codes. Preserve legacy values read-only, use opaque IDs internally, and block canonical unit creation.

## PDR-006 — ExecutionUnit lifecycle

- **Decision ID:** PDR-006
- **Topic:** Canonical cross-mode statuses versus mode-specific statuses.
- **Options:** (A) one large status list containing every road/rail/sea/air/warehouse/customs term; (B) one small shared lifecycle plus mode-specific milestones/checkpoints/events; (C) separate lifecycle model/table for every mode.
- **Recommended option:** Option B. Shared core lifecycle: `not_started`, `ready`, `in_progress`, `arrived`, `delivered`, `cancelled`. `delayed`, `blocked`, stale, document-incomplete, and attention-required are alerts/conditions. Loading, gate-in/out, departed, transshipment, customs inspection/clearance, warehouse received/released, flight booked/uplifted, vessel loaded/discharged, and similar mode details are typed checkpoints/events and projections, not additions to the shared lifecycle. Type-specific specialist state may exist only through a reviewed linked model when it has independent invariants.
- **Rationale:** A stable core enables Project aggregation and multimodal reporting without erasing mode-specific operational detail.
- **Operational impact:** Operations receive detailed checkpoint views while leadership/customer summaries remain comparable across modes.
- **Security impact:** Status transitions use explicit commands, expected version, idempotency, permission, and audit. Event visibility is evaluated separately.
- **Data impact:** Unit stores/rebuilds core-state projection; detailed states reside in unified events, milestones, checkpoints, and mode metadata.
- **Migration impact:** Legacy statuses require an approved mapping table with quarantine for ambiguous values. `delayed` must migrate to alert plus the preceding valid lifecycle state.
- **UX impact:** UI shows core status and separate mode-specific latest checkpoint/alerts, avoiding a single overloaded badge.
- **AI-agent impact:** AI can compare shared lifecycle while citing mode events. It must not invent a core transition from an unverified mode event.
- **Decision owner:** Product Owner — Multimodal Operations
- **Required approvers:** Product Owner, Road/Rail/Sea/Air/Warehouse/Customs Operations representatives, Data Owner
- **Status:** Deferred
- **Deferral date:** 2026-07-31
- **Deferral reason:** ExecutionUnit lifecycle belongs to a later slice.
- **Slice disposition:** Deferred from SLICE-001; revisit for the later ExecutionUnit lifecycle slice.
- **Default fail-safe behavior if unresolved:** Preserve legacy statuses without canonical transition writes; expose `lifecycle_unmapped` internally and exclude ambiguous units from automatic completion.

## PDR-007 — ExecutionUnit split and merge policy

- **Decision ID:** PDR-007
- **Topic:** Quantity, custody, document inheritance, event history, and traceability during split/merge.
- **Options:** (A) mutable parent rewritten into children; (B) immutable lineage events with new units and quantity/custody reconciliation; (C) no split/merge support.
- **Recommended option:** Option B for the future. Split creates new child units and deactivates/supersedes the source for further execution without deleting it. Merge creates a new survivor unit or designates one under an approved rule; all source units remain in lineage. Quantity/weight/volume/custody totals must reconcile using unit-of-measure-aware rules. Events remain on their original units and Project timeline links the lineage event. Documents are not copied: inheritable attachments create explicit new links according to document type/visibility policy; non-inheritable documents require review.
- **Rationale:** Immutable lineage preserves custody and audit evidence and avoids rewriting operational history.
- **Operational impact:** Supports consolidation/deconsolidation while maintaining traceability across carriers, warehouses, and customs.
- **Security impact:** Split/merge needs elevated permission, reason, expected versions for all sources, idempotency, custody authorization, and atomic lineage creation.
- **Data impact:** Requires lineage relation/event, reconciled quantity dimensions, custody references, and per-document inheritance decisions.
- **Migration impact:** Additive future slice; no backfill should infer historical split/merge without evidence.
- **UX impact:** Dedicated preview shows source/target quantities, custody, documents, warnings, and irreversible lineage before confirmation.
- **AI-agent impact:** AI may propose a reconciliation plan but cannot execute split/merge until quantitative, custody, permission, and document policies are approved.
- **Decision owner:** Product Owner — Execution Operations
- **Required approvers:** Product Owner, Operations Owner, Customs/Compliance Owner, Data Owner, Security Owner
- **Status:** Proposed
- **Blocking Slice:** Deferred — blocks the future split/merge slice, not Slice 1.
- **Default fail-safe behavior if unresolved:** Split and merge commands do not exist or return a stable feature-disabled response. Operators record a reviewed exception without altering unit ancestry.

## PDR-008 — Document visibility matrix

- **Decision ID:** PDR-008
- **Topic:** Visibility for internal users, customer, carrier, customs representative, and selected stakeholders.
- **Options:** (A) Project-wide visibility inherited by every document; (B) explicit attachment visibility plus classification ceiling and stakeholder grants; (C) internal/customer boolean only.
- **Recommended option:** Option B. `internal` is the default. `customer`, `carrier`, and `customs_representative` require explicit attachment visibility and an active relationship to the scoped Project/Shipment/Unit. `selected_stakeholders` requires explicit principal/party grants with validity and purpose. Classification and legal restrictions may only reduce access; Project membership never broadens an attachment. Suggested baseline matrix:

| Audience | Default access | Additional condition |
|---|---|---|
| Internal | Denied unless role/scope permits | Classification and least-privilege permission |
| Customer | Denied | Explicit `customer` visibility, customer relationship, approved/available version |
| Carrier | Denied | Explicit `carrier` visibility and assignment to relevant Shipment/Unit |
| Customs representative | Denied | Explicit customs visibility, mandate validity, relevant customs scope |
| Selected stakeholders | Denied | Explicit named grant, scope, purpose, validity period |

- **Rationale:** Document access is contextual and must not be inherited from broad Project visibility.
- **Operational impact:** Staff must classify attachments and manage stakeholder relationships; document sharing becomes auditable.
- **Security impact:** Deny-by-default, server-side per-attachment authorization, no storage-key exposure, negative leakage tests, and access revocation are mandatory.
- **Data impact:** Attachment requires visibility, classification, relationship/grant references, validity period, policy version, and audit.
- **Migration impact:** Existing CaseDocumentFile records default to internal and are not exposed to customers/partners until explicitly classified and attached.
- **UX impact:** Staff see audience/classification badges and customer-view preview. Unauthorized audiences receive no metadata or filename.
- **AI-agent impact:** AI access is evaluated as its own principal and cannot infer document access from Project access or broaden visibility.
- **Decision owner:** Product Owner — Documents and Collaboration
- **Required approvers:** Product Owner, Security Owner, Compliance/Legal Owner, Operations Owner
- **Status:** Proposed
- **Blocking Slice:** Deferred for unit/document Slice; not required for Slice 1 if Slice 1 creates no document links or customer document exposure.
- **Default fail-safe behavior if unresolved:** All existing and new documents remain internal-only; partner/customer document APIs and AI document ingestion remain disabled.

## PDR-009 — Customer document operations

- **Decision ID:** PDR-009
- **Topic:** Customer view, download, upload, replace, and approve operations.
- **Options:** (A) view/download only; (B) controlled upload with staff verification in addition to view/download; (C) full customer replace/approve authority; (D) no customer document operations.
- **Recommended option:** Option B in a later slice. Customers may view/download only explicitly customer-visible, available versions. Upload creates a quarantined/pending artifact linked to the customer and visible to authorized staff plus the uploading customer; it does not satisfy a requirement until validation. Customers may replace only their own pending/rejected upload under explicit versioning rules, never an approved artifact. Customers cannot approve compliance/operational documents; a separate acknowledgement action may record receipt/acceptance where Product requires it.
- **Rationale:** Customer contribution is valuable, but approval and replacement of authoritative documents require segregation of duties.
- **Operational impact:** Staff verification queue and rejection/re-upload workflow are required.
- **Security impact:** Requires authenticated customer membership, upload scanning, size/type limits, quarantine, per-file authorization, rate limits, and audit.
- **Data impact:** Requires upload source, uploader party, quarantine/verification state, replacement lineage, rejection reason, and acknowledgement separate from approval.
- **Migration impact:** Additive future slice; existing files remain internal and cannot be customer-replaced.
- **UX impact:** Customer UI distinguishes uploaded, scanning, pending review, rejected, approved, superseded, and acknowledged states.
- **AI-agent impact:** AI may classify/recommend verification but cannot approve or publish a customer upload without authorized human/policy action.
- **Decision owner:** Product Owner — Customer Experience
- **Required approvers:** Product Owner, Security Owner, Compliance Owner, Operations Owner
- **Status:** Proposed
- **Blocking Slice:** Deferred — blocks customer-document slice, not Slice 1.
- **Default fail-safe behavior if unresolved:** No customer document endpoints. Existing customer UI cannot list, download, upload, replace, or approve documents.

## PDR-010 — Operational thresholds and bulk limits

- **Decision ID:** PDR-010
- **Topic:** Stale updates, SLA thresholds, bulk update limits, and ZIP size/file limits.
- **Options:** (A) one global hard-coded threshold set; (B) versioned policy defaults with mode/service/organization overrides; (C) no automated thresholding.
- **Recommended option:** Option B. Approve a versioned threshold policy. For Slice 1, use a provisional stale-update default of 24 hours after execution starts, with explicit service/mode override and `unknown` when no approved policy applies. SLA thresholds are defined per milestone/service scope, not inferred from stale-update time. Bulk updates use a conservative synchronous maximum of 50 explicitly selected units per command; larger sets require a future asynchronous job and preview. ZIP generation is deferred to an asynchronous export policy; provisional upper bounds for Product/Security approval are 500 files and 2 GiB uncompressed per package, with a lower environment quota allowed.
- **Rationale:** Thresholds differ by mode and service, but bounded defaults are needed for deterministic alerts and denial-of-service protection.
- **Operational impact:** Operations owns policy versions and exceptions; alerts identify the policy used. Large actions/exports become jobs rather than long HTTP requests.
- **Security impact:** Limits mitigate accidental mass change, lock amplification, resource exhaustion, and archive abuse. Bulk authorization remains per item.
- **Data impact:** Alerts/jobs record policy version, threshold, evaluation time, selection criteria, counts, and per-item results.
- **Migration impact:** No historical breach is fabricated. Existing records are evaluated prospectively or in a labeled backfill against an approved policy version.
- **UX impact:** UI shows threshold source, stale duration, bulk selection count, excluded/failed items, and export quota before execution.
- **AI-agent impact:** AI recommendations cite the threshold policy. Agent bulk actions are capped identically and cannot partition requests to bypass limits.
- **Decision owner:** Operations Owner — Service Control
- **Required approvers:** Product Owner, Operations Owner, Security Owner, Platform/SRE Owner
- **Status:** Deferred
- **Deferral date:** 2026-07-31
- **Deferral reason:** Freshness and stale-update alerts belong to later summary/timeline work.
- **Slice disposition:** Deferred from SLICE-001; freshness/stale-update policy, SLA catalog, bulk execution, and ZIP limits require their respective later slices.
- **Default fail-safe behavior if unresolved:** Do not label units delayed or SLA-breached automatically. Expose update age only; mark alert policy `unconfigured`. Bulk update and ZIP generation remain disabled.

## PDR-011 — Retention, legal hold, purge, and digital signatures

- **Decision ID:** PDR-011
- **Topic:** Retention period, legal hold, physical purge, and digital-signature policy.
- **Options:** (A) one fixed retention period and manual deletion; (B) classification/jurisdiction/contract-based retention schedule with legal hold and privileged purge; (C) retain forever; (D) immediate deletion on logical delete.
- **Recommended option:** Option B, with no physical purge until Legal approves the schedule. Retention is policy-driven by document/event classification, jurisdiction, contract, and case closure date. Legal hold overrides expiry, logical deletion, and purge. Physical purge is an asynchronous privileged job with two-person approval, immutable manifest/audit, referential checks, and proof of completion. Digital signatures are considered verified only when validated against an approved signature standard/trust provider with certificate, timestamp, validation result, and evidence; a signature image or metadata alone is not verification.
- **Rationale:** Retention and signature validity are legal controls and cannot be safely reduced to a universal engineering default.
- **Operational impact:** Compliance owns schedules/holds; operators can logically delete but not physically purge outside policy.
- **Security impact:** Prevents unauthorized destruction and false claims of signature authenticity. Purge and hold actions require least privilege and segregation of duties.
- **Data impact:** Requires retention policy/version, basis date, expiry, hold records, purge eligibility/result, signature validation evidence, and immutable audit.
- **Migration impact:** Existing artifacts/events default to retention status `active/unclassified`; no existing binary is purged by migration.
- **UX impact:** UI shows retention/hold/signature-validation state and disables incompatible actions with policy reasons.
- **AI-agent impact:** AI may detect expiry or recommend review but cannot release legal hold, purge, or declare a signature valid without approved verification evidence and authority.
- **Decision owner:** Legal/Compliance Owner
- **Required approvers:** Legal/Compliance Owner, Security Owner, Product Owner, Data Protection Owner, Operations Owner
- **Status:** Proposed
- **Blocking Slice:** Deferred for physical purge, legal-hold automation, and signature verification. A minimal retention metadata contract should be approved before document architecture implementation, not before Slice 1.
- **Default fail-safe behavior if unresolved:** Preserve all events, documents, versions, and audit records; allow logical deletion from normal views but prohibit physical purge and claims of verified digital signature.

## Decision summary

| Decision ID | Decision or Recommendation | SLICE-001 disposition | Owner | Status |
|---|---|---:|---|---|
| PDR-001 | Accepted Option B: one primary customer organization plus typed payer/consignee/cargo-owner relationships | Approved | Product Owner — Customer and Commercial Domain | Accepted |
| PDR-002 | Accepted Option B: role/state-based authority; elevated cancel and ownership transfer | Approved; SLICE-001 uses only its authorized scope | Product Owner — Operational Governance | Accepted |
| PDR-003 | Accepted Option C: separate opaque public ID, internal Project code, and high-entropy public tracking code | Approved; public tracking remains outside SLICE-001 | Product Owner — Project Experience | Accepted |
| PDR-004 | Accepted Options B and D: complete when all non-cancelled units are delivered; forced closure remains separate | Approved; summary calculation remains outside SLICE-001 | Product Owner — Operational Lifecycle | Accepted |
| PDR-005 | Recommended Option C remains unchanged | Deferred: ExecutionUnit is outside SLICE-001 | Product Owner — Execution Operations | Deferred |
| PDR-006 | Recommended Option B remains unchanged | Deferred: ExecutionUnit lifecycle belongs to a later slice | Product Owner — Multimodal Operations | Deferred |
| PDR-007 | Immutable split/merge lineage with quantity, custody, and attachment-link reconciliation | No | Product Owner — Execution Operations | Proposed |
| PDR-008 | Explicit attachment visibility plus classification ceiling and stakeholder grants | No | Product Owner — Documents and Collaboration | Proposed |
| PDR-009 | Controlled customer upload/replacement with staff verification; no customer approval | No | Product Owner — Customer Experience | Proposed |
| PDR-010 | Recommended Option B remains unchanged | Deferred: freshness and stale-update alerts belong to later summary/timeline work | Operations Owner — Service Control | Deferred |
| PDR-011 | Policy-based retention; legal hold overrides; no purge/signature claim without approval/evidence | No | Legal/Compliance Owner | Proposed |

## SLICE-001 decision disposition

The Architecture Authority resolved the SLICE-001 decisions as follows on 2026-07-31:

1. PDR-001 through PDR-004 are Accepted using their documented recommended options.
2. PDR-005 is Deferred because ExecutionUnit is outside SLICE-001.
3. PDR-006 is Deferred because ExecutionUnit lifecycle belongs to a later slice.
4. PDR-010 is Deferred because freshness and stale-update alerts belong to later summary/timeline work.
5. The accepted PDR-004 policy governs future summary behavior, but Project Summary calculation was not part of SLICE-001.

## Non-blocking deferred decisions

- PDR-005 remains disabled until an authorized ExecutionUnit slice.
- PDR-006 retains its documented fail-safe behavior until a later lifecycle slice.
- PDR-007 may be deferred by keeping split/merge disabled.
- PDR-008 may be deferred while all documents remain internal and Slice 1 creates no document attachments.
- PDR-009 may be deferred by exposing no customer document operations.
- PDR-010 remains unconfigured; freshness/stale-update alerts, SLA catalogs, executable bulk updates, and ZIP quotas remain disabled until their later slices.
- PDR-011 may be deferred for Slice 1 by retaining all records, honoring manual/legal holds conservatively, prohibiting physical purge, and making no digital-signature verification claims.

## Readiness verdict

**SLICE-001 governance reconciled.** PDR-001 through PDR-004 are Accepted. PDR-005, PDR-006, and PDR-010 are Deferred with explicit reasons and fail-safe behavior. PDR-007 through PDR-009 and PDR-011 remain Proposed and unchanged in substance. This reconciliation does not authorize any later slice.
