# Canonical Business Object Catalog

- Status: Authoritative vocabulary draft for Phase 0.6 review
- Date: 2026-07-31
- Scope: Entire Forwarder platform
- References: ADR-001 through ADR-020, PDR-001 through PDR-011, and the Operational Architecture Workshop
- Constraint: This catalog defines language; it does not authorize implementation or mark Proposed decisions Accepted.

## Part 1 — Purpose

### Why a canonical vocabulary is required

Forwarder currently contains commercial intake, operational execution, customer tracking, CRM, documents, reporting, control-tower, and future AI concepts. Several historical names describe implementation details rather than business meaning. Without one vocabulary, the same word can refer to a request, a shipment, a project, a vehicle, a file, a timeline record, or an audit record. That ambiguity creates incorrect cardinality, insecure authorization, incompatible APIs, duplicate models, misleading reports, and unreliable AI reasoning.

This catalog establishes one canonical name and definition for every core business object. A canonical name expresses domain meaning and remains stable even if tables, services, frameworks, or deployment boundaries change.

### Stability across implementation evolution

Business language is a compatibility contract. A table may be bridged, a class may move to another module, an API may gain a version, and a projection may be rebuilt without renaming the underlying business concept. Implementation names may temporarily retain legacy names for backward compatibility, but new designs must use canonical terminology and explicitly label compatibility aliases.

Terminology change is not a mechanical refactor. A change in canonical meaning requires impact analysis across ownership, lifecycle, security, data, migration, API, UI, reports, documentation, and AI behavior.

### Authoritative use

This catalog is the vocabulary reference for:

- **ADRs:** define architecture using canonical objects and state aliases explicitly.
- **PDRs:** decide business policies against canonical objects, not UI labels or legacy tables.
- **APIs:** use canonical resource/action names for new contracts and document compatibility paths.
- **Database:** use canonical table/column names for new schema, subject to additive migration rules.
- **Frontend and UI:** show unambiguous labels and preserve distinctions between Project, ShipmentRequest, OperationalShipment, and ExecutionUnit.
- **Backend:** name domain/application types after canonical concepts and isolate legacy adapters.
- **DTOs:** identify subject, direction, action, and version with canonical names.
- **Reports and dashboards:** declare the aggregation object and status owner.
- **Documentation:** use canonical terms first; aliases appear only in compatibility notes.
- **AI agents:** observe, explain, recommend, and prepare actions using canonical objects and identifiers.

When an existing Accepted ADR uses a broad word such as “Shipment” in prose, its formally defined object remains authoritative. This catalog clarifies future language without silently rewriting historical decisions.

## Part 2 — Canonical Business Objects

In the tables below, “aggregate owner” means the object that controls invariants and writes. “Lifecycle owner” means the service/aggregate policy authorized to transition the object. A projection or value object has no independent write lifecycle.

### 2.1 Coordination, commercial, and execution objects

| Business Concept | Canonical Name | Business Definition | Technical Definition | Aggregate Owner | Primary Identifier | Lifecycle Owner | Parent Object | Child Objects | Visible To | Deprecated Aliases | Future Compatibility Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Project | `Project` | Business coordination boundary for related requests, shipments, units, alerts, reports, and scoped documents | Future Project aggregate; ADR-017 uses `OperationalProject` as possible persistence name, but business/API term is Project | Self | Opaque `project_id`; internal `ProjectCode` is a reference | Project policy/application service | Organization; primary Customer relationship | ShipmentRequests, OperationalShipments, Stakeholders, Reports, DocumentAttachments | Authorized staff, customer/stakeholders through scoped projections | Case, Job, Shipment, Request when used as Project | Keep stable across modular/service extraction; ownership decisions remain governed by PDR-001/PDR-002 |
| Shipment request | `ShipmentRequest` | Customer/commercial intake, quotation, assignment, and decision record | Existing `ShipmentRequest` model and commercial services | Self | Opaque/request ID; legacy tracking reference remains compatibility data | Commercial request service | Optional Project; Customer/Organization context | Quotations, commercial comments, requirements, lineage to OperationalShipments | Customer and authorized commercial/operations staff | Request, Case, Shipment Request Case | Never rename to Shipment or Project; commercial status only |
| Operational shipment | `OperationalShipment` | Executable end-to-end shipment owning route planning and execution | Existing `OperationalShipment` aggregate | Self | Opaque `operational_shipment_id` / existing `public_id` | OperationalShipment service | Project; lineage to ShipmentRequest/accepted Quotation | Routes, Milestones, Checkpoints, ExecutionUnits, Exceptions | Authorized operations; customer through allowlisted projection | ShipmentJob, Shipment, Operation | `ShipmentJob` stays prohibited; one Request may create several shipments after policy approval |
| Execution unit | `ExecutionUnit` | Independently stateful physical or logical unit of execution inside a shipment | Canonical model/contract described by ADR-018; legacy persistence is `ShipmentTransportUnit` | Self for independently concurrent unit state | Opaque `execution_unit_id`; immutable Project-local unit code | ExecutionUnit service | OperationalShipment | OperationalEvents, DocumentAttachments, Milestones/Checkpoint references, Reports, Alerts | Authorized operations; customer/partners through scoped projection | ShipmentTransportUnit, TrackingUnit, OperationalUnit, Unit | Legacy table/API may remain behind adapter; do not create a table per mode without ADR |
| Quotation | `Quotation` | Commercial offer for a ShipmentRequest with amount, validity, terms, and customer response | Canonical commercial object; existing model is `ExpertQuote` | ShipmentRequest commercial boundary or Quotation aggregate if later justified | Opaque `quotation_id` | Quotation/commercial service | ShipmentRequest | Approval/customer response and accepted-shipment lineage | Customer, assigned commercial staff, authorized management | Quote, ExpertQuote, Offer | Existing `ExpertQuote` is a compatibility class/table name; new contracts prefer Quotation |
| Customer | `Customer` | Legal or business party receiving services and associated with commercial/project ownership | Existing customer records plus future organization/party relationship | Customer/CRM boundary | Opaque `customer_id` | CRM/customer governance | Optional Organization/party hierarchy | Contacts, ShipmentRequests, Project relationships, Stakeholder roles | Authorized CRM/operations; the customer’s authorized users | Client, Shipper when used generically | Payer, consignee, and cargo owner are Stakeholder roles, not aliases for Customer owner |
| Organization | `Organization` | Security, operational, customer, partner, or legal grouping used for ownership and access scope | Canonical organization identity; current operational organization is `OperationalOrganization` | Self | Opaque `organization_id` | Organization governance | Optional parent Organization | Users, Roles, Projects, memberships, Stakeholders | Members and authorized administrators | Tenant, Company, OperationalOrganization when used generically | “Tenant” describes isolation behavior, not the primary business name |
| Stakeholder | `Stakeholder` | Typed relationship between a party and a scoped business object | Future relationship containing party, scope, role, purpose, and validity | Scope owner (Project/Shipment/etc.) | Opaque `stakeholder_id` | Scope membership/governance service | Project, OperationalShipment, ExecutionUnit, or DocumentAttachment | Visibility grants/contacts | Authorized staff and the stakeholder where policy permits | Payer, Consignee, CargoOwner, NotifyParty as object names | Those terms become stakeholder-role values; presence never grants access automatically |

### 2.2 Operational history, state, route, and work objects

| Business Concept | Canonical Name | Business Definition | Technical Definition | Aggregate Owner | Primary Identifier | Lifecycle Owner | Parent Object | Child Objects | Visible To | Deprecated Aliases | Future Compatibility Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Operational event | `OperationalEvent` | Immutable fact about an operationally significant occurrence | Unified versioned event envelope and source-linked records per ADR-019 | Subject aggregate emits; event store owns immutability | Opaque `operational_event_id` | No mutable lifecycle; correction through superseding event | Primary scope: Project, OperationalShipment, ExecutionUnit, or DocumentAttachment/Artifact | Related evidence and projection references | Permission-filtered internal/customer/partner timelines | Update, Activity, History item, Tracking update when used generically | Existing MilestoneEvent and unit updates may link/emit; lightweight event sourcing, not universal full event sourcing |
| Timeline | `Timeline` | Ordered, permission-filtered view of relevant events | Rebuildable read projection with deterministic ordering and pagination | Projection owner, not a write aggregate | Projection cursor plus subject identifier | Projector/reconciliation policy | Project, OperationalShipment, ExecutionUnit, or Document | Timeline entries derived from OperationalEvents | Audience-specific projection | History, Activity Feed, Tracking History | Never accept direct arbitrary timeline writes; writes occur through business actions/events |
| Operational status | `OperationalStatus` | Current shared execution lifecycle state of an operational object | Typed value/projection owned by Project, OperationalShipment, Route, or ExecutionUnit | The subject aggregate | Subject ID + status value/version | Subject lifecycle policy | Subject object | None | Subject’s authorized audiences | TrackingStatus, ShipmentStatus when ambiguous | Status values are qualified by owner; never use one global unowned `status` meaning |
| Operational alert | `OperationalAlert` | Derived condition requiring attention without changing lifecycle truth | Rebuildable alert projection with type, severity, policy version, subject, and resolution/work link | Alert/control-tower projection | Opaque `operational_alert_id` or deterministic subject/type key | Alert policy/projector | Project, OperationalShipment, ExecutionUnit, Milestone, DocumentRequirement | Tasks/Exceptions as applicable | Authorized operations; limited customer alerts when explicitly published | AttentionRequired status, Warning, Flag | Delay, stale update, SLA breach, exception, and missing document may produce alerts |
| Task | `Task` | Assigned actionable work with owner, due time, state, and source | Canonical work-queue item; existing operational `WorkItem` and CRM task are bounded implementations | Task/work-queue boundary | Opaque `task_id` | Task service | Project/Shipment/Unit/Exception/CRM context | Comments, approvals, referenced actions | Assigned team/users and authorized managers | WorkItem, To-do, CRMTask when used generically | Qualify subtype (`OperationalTask`, `CrmTask`) only when behavior differs; Task is not source of operational truth |
| Milestone | `Milestone` | Planned or required control point whose actual outcome derives from verified evidence/events | Existing operational `Milestone` model | OperationalShipment/active RoutePlan | Opaque `milestone_id` | Milestone verification policy | Route/RouteLeg/Checkpoint under OperationalShipment | MilestoneEvents, evidence, Alerts | Operations; customer through published projection | Step, Tracking Step, Stage | Existing MilestoneEvent remains authoritative for verification; not synonymous with status |
| Route | `Route` | Versioned plan for movement/processing through locations, legs, and checkpoints | Business concept implemented by revisioned `RoutePlan` plus RouteLeg and dependencies | OperationalShipment | Opaque `route_id`; revision/version | Route planning/orchestration service | OperationalShipment | RouteLegs, Checkpoints, Milestones, dependencies | Operations; customer through summarized projection | RoutePlan when used as business synonym, Journey, Path | Backend persistence may retain RoutePlan; UI/API must distinguish Route from a particular revision where necessary |
| Checkpoint | `Checkpoint` | Ordered operational control location/activity within a Route | Existing `OperationalCheckpoint` and associated Milestones | Route/OperationalShipment | Opaque `checkpoint_id` | Route orchestration/checkpoint policy | Route and optionally RouteLeg | Milestones, OperationalEvents, Alerts | Operations; customer if published | TrackingLocation, Stop, Stage | CanonicalLocation is reference data, not a Checkpoint; checkpoint captures operational context/snapshot |
| Exception | `OperationalException` | Governed deviation/problem with state, owner, evidence, and resolution | Canonical exception case; current route exceptions/work items are partial implementations | Self or control-tower boundary | Opaque `operational_exception_id` | Exception service | Project/Shipment/Unit/Route/Milestone/Document | Tasks, Comments, Approvals, OperationalEvents | Authorized operations; customer only if published | ExceptionCase, RouteException, Issue, Problem | Use type qualifier for specialized policy, not as a duplicate base concept |
| Delay | `DelayCondition` | Derived or reported lateness affecting a subject relative to an approved policy/plan | Alert/event combination with expected/actual times, cause, duration, source, and policy version | Subject/alert projection | OperationalEvent/Alert ID; no standalone mutable identity required unless managed as Exception | Delay policy; resolution from events/projection | Project/Shipment/Unit/Route/Milestone | OperationalAlert and possibly OperationalException | Operations; customer when explicitly published | Delayed status, Late flag | `delayed` is not a shared lifecycle state; may open an OperationalException |
| SLA | `ServiceLevelAgreement` | Versioned commitment/policy defining measurable service targets and escalation | Policy/catalog plus subject association and derived evaluation | SLA policy boundary | Opaque `sla_policy_id` + version | SLA governance owner; evaluation projector | Organization/Project/service scope | Threshold rules, evaluations, Alerts | Authorized staff; customer summary if contractual | SLA, Service Level, Due threshold | Acronym `SLA` is permitted; status/breach remains derived and policy-versioned |

### 2.3 Document and approval objects

| Business Concept | Canonical Name | Business Definition | Technical Definition | Aggregate Owner | Primary Identifier | Lifecycle Owner | Parent Object | Child Objects | Visible To | Deprecated Aliases | Future Compatibility Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Document artifact | `DocumentArtifact` | One immutable binary and its intrinsic technical metadata | Private stored binary metadata: checksum, media type, size, storage key, uploader, signature metadata | Document boundary | Opaque `document_artifact_id`; checksum is integrity evidence, not identity | Immutable; retention/purge policy only | Organization/document store | DocumentVersions/Attachments as modeled | Only through an authorized DocumentAttachment or privileged storage operation | File, CaseDocumentFile, UploadedFile | Existing CaseDocumentFile may bridge to artifact; storage key is never public identity |
| Document attachment | `DocumentAttachment` | Contextual link between a DocumentArtifact and one business scope | Link containing scope, type, visibility, classification, owner, approval, tags, validity | Scope/document boundary | Opaque `document_attachment_id` | Document attachment/version policy | Project, OperationalShipment, ExecutionUnit, or OperationalEvent | DocumentVersions, Approvals, AuditEntries | Audiences allowed by visibility, classification, relationship, and permission | Attachment, Document, LinkedFile | Multiple attachments may reference one artifact; binary is not copied merely for multi-scope association |
| Document version | `DocumentVersion` | Immutable revision in a document lineage | Version record linking artifact/attachment lineage and supersession | DocumentAttachment/document boundary | Opaque `document_version_id` + lineage version number | Replacement/supersession policy | DocumentAttachment or logical document lineage | Approvals, verification evidence | Same as authorized attachment/version policy | FileVersion, ReplacementFile | Existing CaseDocumentFile `version_number` maps additively; old versions remain auditable |
| Requirement | `DocumentRequirement` | Versioned policy snapshot defining a required/optional document and validation limits for a scope | Existing DocumentDefinition/CaseDocumentRequirement concepts separated into definition and applied requirement | Scope/document policy owner | Opaque `document_requirement_id`; definition code/revision | Requirement policy; satisfaction is derived | ShipmentRequest initially; future Project/Shipment/Unit scope | Satisfying DocumentAttachments/Versions | Authorized staff; customer when request/upload action is permitted | Requirement, CaseDocumentRequirement, DocumentDefinition when conflated | Use `DocumentDefinition` for reusable policy definition and `DocumentRequirement` for applied snapshot |
| Attachment visibility | `AttachmentVisibility` | Explicit permitted audience category for a DocumentAttachment | Controlled value: internal, customer, carrier, customs representative, selected stakeholders | DocumentAttachment | Value plus attachment/policy version | Visibility policy; changes through explicit action | DocumentAttachment | Stakeholder grants where applicable | The named audience only after all additional checks | Visibility, IsCustomerVisible boolean | Classification can only restrict further; default is internal/deny-by-default |
| Approval | `Approval` | Traceable decision by an authorized principal about a proposed action, event, document, or exception | Record with subject, decision, actor, authority, policy, reason/evidence, timestamps, and correlation | Approval/workflow boundary or subject policy | Opaque `approval_id` | Approval policy | Any approvable subject | AuditEntry and emitted OperationalEvent | Authorized participants; limited result projection to customer | Verification, Sign-off, CustomerResponse when conflated | Verification and acknowledgement are distinct approval types/acts; do not equate signature image with approval |

### 2.4 Identity, authorization, communication, and evidence objects

| Business Concept | Canonical Name | Business Definition | Technical Definition | Aggregate Owner | Primary Identifier | Lifecycle Owner | Parent Object | Child Objects | Visible To | Deprecated Aliases | Future Compatibility Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Role | `Role` | Named collection of responsibilities used as an input to authorization | Role definition and organization-scoped assignment; not sufficient without resource/attribute checks | Identity/authorization boundary | Opaque `role_id` or governed stable code | Security governance | Organization | Role assignments/Permissions | Administrators; users may see own roles | UserType, AccessLevel | Avoid hard-coding business decisions solely by role string |
| User | `User` | Authenticated human principal with memberships and assignments | Canonical principal; existing internal user/customer identity models may remain bounded | Identity boundary | Opaque `user_id` | Identity/session governance | Organization membership(s) | Role assignments, sessions, authored events/comments/audit references | Self and authorized administrators | ExpertUser, AdminUser, CustomerUser when used as universal base | Specialized profiles may retain names; authentication session never owns shipment lifecycle |
| Permission | `Permission` | Explicit allowed action on a scoped resource subject to policy and attributes | Stable action code evaluated with principal, resource, organization, relationships, state, and policy version | Authorization policy boundary | Stable permission code | Security governance | Role/policy; evaluated against resource | Policy decisions/AuditEntries | Administrators and policy engine; users may see effective capabilities | Capability, Privilege, UI Guard | UI visibility is not permission; deny by default |
| Notification | `Notification` | Delivery-oriented message informing a recipient of an event, task, alert, or required action | Channel-independent notification record and delivery attempts | Notification boundary | Opaque `notification_id` | Notification service | Source event/task/alert | Delivery attempts/preferences | Intended recipients and administrators | Alert, Message, Email when conflated | Notification is not OperationalAlert and not source of business truth |
| Comment | `Comment` | Human-authored contextual discussion attached to a business object | Append-style message with author, subject, visibility/classification, time, and optional reply chain | Subject/comment boundary | Opaque `comment_id` | Comment moderation/visibility policy | Project/Request/Shipment/Unit/Task/Exception/Document | Replies/attachments if later approved | Audience permitted by scope/visibility | Note, InternalNote, CustomerMessage, ExpertConsoleMessage | Customer message and internal note are visibility-qualified Comments; comments do not change status |
| Audit entry | `AuditEntry` | Immutable security/accountability record of an action or policy decision | Append-only actor/action/resource/outcome/reason/correlation/policy record | Audit boundary | Opaque `audit_entry_id` | Immutable; retention policy only | Organization and referenced resource | None | Security, auditors, authorized administrators | Log, OperationalAudit, DocumentAuditEvent, AuditLog | AuditEntry is not OperationalEvent, Timeline, or application log; specialized legacy tables may bridge |

### 2.5 Reporting, presentation, and identifier objects

| Business Concept | Canonical Name | Business Definition | Technical Definition | Aggregate Owner | Primary Identifier | Lifecycle Owner | Parent Object | Child Objects | Visible To | Deprecated Aliases | Future Compatibility Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Report | `Report` | Reproducible business output with declared scope, filters, as-of time, policy/version, and format | Query/export definition plus generated artifact/job metadata | Reporting boundary | Opaque `report_id` or stable definition code + run ID | Reporting/export service | Organization/Project/other declared scope | Sections, rows, generated DocumentArtifact | Authorized audiences defined per report | Export, XLSX, Statement when used generically | Filename/format is not the report identity; unit/timeline reports must declare scope |
| Dashboard | `Dashboard` | Interactive read model presenting metrics, alerts, queues, and navigation for a declared audience | UI/read projection composition; no direct domain writes | Presentation/read-model boundary | Stable dashboard code | Product/read-model governance | Audience/workspace | Widgets, filters, links to actions | Intended authorized audience | Panel, Console, Control Tower when conflated | Control Tower is a specialized dashboard/work queue, not a new source of truth |
| Tracking code | `TrackingCode` | High-entropy shareable/revocable public tracking credential or reference | Protected/hashed value with issue, rotation, revocation, scope, and audit metadata | Scope identity/access policy | The protected code; never sequential/derived | Tracking-access governance | Project or legacy ShipmentRequest | Public projection access record | Intended customer/share recipients | TrackingNumber, PublicCode, Request ID | Future Project TrackingCode is separate from legacy request code and ProjectCode |
| Project code | `ProjectCode` | Stable human-readable organization-local internal Project reference | Immutable generated code such as approved `PRJ-YYYY-NNNNNN` policy | Project | Code unique within owning Organization | Project identity policy | Project | None | Authorized staff; customer only if Product approves | CaseNumber, JobNumber, ProjectNumber | Not an authorization credential and not the API primary identifier |

## Part 3 — Naming Rules

### 3.1 Business terms

- Use singular PascalCase canonical names when referring to formal objects: `Project`, `ShipmentRequest`, `OperationalShipment`, `ExecutionUnit`.
- Use ordinary lowercase only for generic prose when no formal object is intended.
- Qualify ambiguous states and identifiers by owner: `project_status`, `execution_unit_status`, `project_code`.
- Use `OperationalShipment` in full when execution aggregate meaning matters. Do not shorten it to Shipment in contracts.
- Use `DocumentArtifact` for binary identity and `DocumentAttachment` for business context.

### 3.2 API names

- Resources use lowercase plural kebab-case: `/projects`, `/shipment-requests`, `/operational-shipments`, `/execution-units`, `/operational-events`, `/document-attachments`.
- JSON fields use `snake_case`: `project_id`, `execution_unit_id`, `occurred_at`, `attachment_visibility`.
- Explicit actions use verb endpoints only for domain commands: `/projects/{id}/close`, not arbitrary status PATCH.
- New public contracts use opaque IDs. Sequential IDs and storage keys are not public identifiers.
- Compatibility routes retain legacy names only with documentation and deprecation ownership.

### 3.3 Database tables and columns

- New tables use singular `snake_case` canonical names unless repository migration convention explicitly requires plural: `project`, `execution_unit`, `operational_event`, `document_attachment`.
- Foreign keys use `<canonical_object>_id`: `project_id`, `operational_shipment_id`.
- Status columns are owner-qualified when a row contains more than one state domain.
- Times use semantic suffixes: `_at` for instants, `_date` for local dates; `occurred_at` and `recorded_at` remain distinct.
- Public/opaque identifiers use `public_id` only when the owning table makes scope unambiguous; cross-object DTOs use qualified names.
- Legacy table names remain unchanged until an approved additive migration/deprecation plan exists.

### 3.4 Backend classes

- Domain/entity classes use canonical PascalCase names.
- Application services use `<Object><Action>Service` or bounded module naming, such as `ExecutionUnitUpdateService`.
- Compatibility adapters include `Legacy` or the source name explicitly; they do not redefine the canonical object.
- Projection classes end with `Projection`; policy classes end with `Policy`; commands end with `Command`.

### 3.5 Frontend components

- Components use canonical object plus purpose: `ProjectSummary`, `ExecutionUnitTable`, `OperationalTimeline`, `DocumentAttachmentList`.
- Avoid generic `Detail`, `Item`, or `Card` names without an object qualifier in exported components.
- UI translations must preserve domain distinctions even if concise labels are used visually.

### 3.6 DTO names

- Use `<Object><Operation><Request|Response>Vn`, for example `ExecutionUnitListResponseV1` or `ProjectCloseRequestV1`.
- Read projections may use `<Object>SummaryDTO` or `<Object>DetailDTO`; command payloads are not called DTOs without action context.
- Never use `ShipmentDTO` when the object is ShipmentRequest or OperationalShipment.

### 3.7 Event names

- Event type strings use past-tense canonical subject/action in dot-separated lowercase: `execution_unit.status_changed`, `project.closed`, `document_attachment.visibility_changed`.
- Command names use imperative form: `CloseProject`, `UpdateExecutionUnitStatus`.
- Event payloads include schema version and canonical subject identity.
- Do not name a mutable command result an event.

### 3.8 Report and dashboard names

- Reports declare scope and purpose: `ProjectExecutionSummary`, `ExecutionUnitTimelineReport`, `DocumentInventoryReport`.
- Generated filenames may include safe ProjectCode and as-of date but do not become object identifiers.
- Dashboards declare audience/function: `OperationsControlTowerDashboard`, `CustomerProjectDashboard`.

### 3.9 File names

- Architecture/documentation filenames use lowercase `snake_case.md` unless the established ADR convention applies.
- ADR filenames retain `ADR-NNN-kebab-case.md`.
- Do not encode “final”, “new”, or “latest” as version semantics; use governed version/date/status metadata.

### 3.10 ADR and PDR terminology

- ADRs define architecture decisions and use canonical terms in titles/decisions.
- PDRs define Product choices and cite the canonical object plus decision scope.
- An ADR/PDR may mention a legacy alias only in Context, Alternatives, Migration, or Compatibility sections and must name the canonical replacement.
- Proposed/Accepted status is explicit; this catalog does not change it.

### 3.11 Prohibited abbreviations

Do not introduce these in external contracts or primary domain names: `Proj`, `Req`, `ShipReq`, `OpShip`, `ExecUnit`, `TrkUnit`, `Doc`, `Att`, `Evt`, `Stat`, `Notif`, `Perm`, `Usr`, `Cust`, `Org`.

Permitted established abbreviations when defined: `API`, `DTO`, `ADR`, `PDR`, `SLA`, `ERP`, `BPM`, `AI`, `UTC`, `UUID`, `ZIP`, `XLSX`. Identifier suffix `id` is permitted.

### 3.12 Words that must never be used interchangeably

- Project ≠ ShipmentRequest ≠ OperationalShipment ≠ ExecutionUnit.
- Customer ≠ Organization ≠ Stakeholder ≠ User.
- Role ≠ Permission.
- OperationalStatus ≠ OperationalAlert ≠ OperationalException ≠ DelayCondition.
- OperationalEvent ≠ Timeline ≠ AuditEntry ≠ Notification ≠ Comment.
- Route ≠ Checkpoint ≠ Milestone ≠ Task.
- DocumentArtifact ≠ DocumentAttachment ≠ DocumentVersion ≠ DocumentRequirement.
- Verification ≠ Approval ≠ Customer acknowledgement ≠ Digital signature validation.
- ProjectCode ≠ TrackingCode ≠ opaque primary identifier.
- Lifecycle status ≠ administrative closure ≠ activation/deactivation.
- Task/Work queue ≠ source of operational truth.

## Part 4 — Canonical Status Vocabulary

Every status has exactly one owner. New generic `status` fields are prohibited when the owner is not obvious from the resource.

### 4.1 Business status

Owner: `ShipmentRequest` commercial lifecycle.

Canonical concept: `ShipmentRequestBusinessStatus`. Existing values are compatibility-governed until a separate accepted status catalog; operational values such as departed, arrived, or delivered must never be added. Current values such as `new`, `assigned`, `in_progress`, `quoted`, `waiting_for_customer`, `won`, `lost`, and `closed` remain commercial meanings only.

`won` indicates commercial eligibility; it does not mean execution started or completed.

### 4.2 Operational status

Owner: the specific execution aggregate/projection.

| Owner | Canonical status type | Canonical values/direction |
|---|---|---|
| Project | `ProjectOperationalStatus` | Proposed: `not_started`, `in_progress`, `partially_delivered`, `completed`, `cancelled`; subject to PDR acceptance |
| OperationalShipment | `OperationalShipmentStatus` | Existing lifecycle remains owned by OperationalShipment; expansion requires its state ADR/matrix |
| ExecutionUnit | `ExecutionUnitStatus` | Proposed shared core: `not_started`, `ready`, `in_progress`, `arrived`, `delivered`, `cancelled`; subject to PDR acceptance |
| Route/RouteLeg/Checkpoint | Owner-qualified route status | Defined by route orchestration state matrices; never promoted directly to Project status |

`delayed`, `overdue`, `blocked`, `stale`, `attention_required`, and `incomplete_documents` are not shared lifecycle statuses. They are alert/exception/projection concepts.

### 4.3 Document status

Owners are distinct:

- `DocumentArtifactRetentionStatus`: proposed `active`, `retention_hold`, `expired`, `logically_deleted`; physical purge is an audited outcome, not an ordinary status transition.
- `DocumentVersionStatus`: active/current, superseded, logically deleted/quarantined as governed by document policy.
- `DocumentRequirementSatisfactionStatus`: `missing`, `pending_validation`, `satisfied`, `rejected`, `expired` as a derived result; exact values require document-slice approval.

Do not combine artifact retention, version currency, malware quarantine, requirement satisfaction, visibility, or approval in one document `status`.

### 4.4 Approval status

Owner: `Approval` policy for a specific subject and approval type.

Proposed common vocabulary: `pending`, `approved`, `rejected`, `expired`, `withdrawn`, plus `not_required` only when policy explicitly declares no approval requirement. Verification and customer acknowledgement must use qualified types and must not silently set approval status.

### 4.5 Lifecycle status

“LifecycleStatus” is not a global enum. It is the class of owner-specific state machines. Its owner is always named. Activation/deactivation, administrative closure, retention, task workflow, notification delivery, and audit immutability are separate state domains.

Status transition rules must be defined by the owning aggregate’s Accepted ADR/state matrix and executed through explicit actions with authorization, expected version, idempotency, and audit as applicable.

## Part 5 — Alias Registry

Aliases are recognized for compatibility and search. They must not become primary names in new architecture, APIs, UI headings, reports, migrations, or AI-generated designs.

| Legacy Name | Canonical Name | Reason | Compatibility | Removal Strategy |
|---|---|---|---|---|
| `ShipmentTransportUnit` | `ExecutionUnit` | Legacy name is tied to tracking and physical transport | Existing model/table/API may remain behind adapter | Introduce canonical contracts additively; deprecate external legacy routes after usage gate; table rename is optional |
| `TrackingUnit` | `ExecutionUnit` | Tracking is a projection, not execution ownership | Recognize in searches/import vocabulary only | Reject in new schemas/contracts; update documentation when touched |
| `OperationalUnit` | `ExecutionUnit` | Ambiguous with organizational unit | No new compatibility object | Replace in drafts before approval |
| `Request` | `ShipmentRequest` | Too generic | Permitted only in local prose with immediate context | Use full canonical name in contracts/types/headings |
| `Shipment` for intake | `ShipmentRequest` | Confuses commercial request with execution | Preserve legacy UI text only where behavior cannot yet change | Correct labels during compatibility UI slice |
| `Shipment` for execution | `OperationalShipment` | Omits execution boundary | Broad prose may remain in historical ADR-016 context | Use full name in all new formal artifacts |
| `ShipmentJob` | `OperationalShipment` | Explicitly deprecated by ADR-003 | Human migration notes only; no entity/class/table/API | Prohibit new uses; remove incidental prose when separately authorized |
| `Case` for Project | `Project` | Case is ambiguous with request/document case | Existing case-document routes/models remain compatibility names | Do not create Project `case_id`; bridge legacy case scope explicitly |
| `Case` for request | `ShipmentRequest` | Hides commercial semantics | Existing expert “case” UI may remain temporarily | Adopt ShipmentRequest label/type in new features |
| `File` | `DocumentArtifact` | File describes binary, not business context | UI may say “file” for upload control only | Domain/API/storage contracts use DocumentArtifact |
| `CaseDocumentFile` | `DocumentArtifact` and legacy Request attachment context | Current row combines artifact/context/version concerns | Existing model remains authoritative until document migration | Bridge artifact identity and attachments additively; no silent reinterpretation |
| `Attachment` | `DocumentAttachment` | Too generic and confused with binary | Generic UI icon text permitted | Formal object/type/API uses full canonical name |
| `Document` | `DocumentArtifact` or `DocumentAttachment` as explicitly qualified | Word conflates binary and scoped link | Natural-language umbrella term only | Require qualifier in technical artifacts |
| `ExpertQuote` | `Quotation` | Actor-specific implementation name is not business concept | Existing class/table/routes remain | New business/API terms use Quotation; adapter maps legacy object |
| `Quote` | `Quotation` | Informal abbreviation | UI prose may retain if Product prefers | Formal domain/contract names use Quotation |
| `WorkItem` | `Task` (`OperationalTask` when qualification is needed) | Implementation/read-model name | Existing operational work queue remains | New cross-platform vocabulary uses Task; do not rename accepted schema without migration decision |
| `ExceptionCase` / `RouteException` | `OperationalException` | Specialized names should not duplicate base concept | Existing route exception model/API remains | Qualify exception type within canonical OperationalException model/contracts |
| `AttentionRequired` status | `OperationalAlert` | Attention is a condition, not lifecycle | Legacy aggregate projection may continue during fallback | Canonical projection returns lifecycle plus alerts separately |
| `Delayed` status | `DelayCondition` plus prior valid `OperationalStatus` | Delay must not erase lifecycle truth | Legacy status maps through explicit compatibility projection | Approved backfill/mapping; retain source event and ambiguity quarantine |
| `Tracking history` | `Timeline` | Customer-oriented alias for event projection | UI label may remain | Technical projection/DTO uses Timeline |
| `Activity` | `OperationalEvent`, `Comment`, `Task`, or CRM activity as qualified | Too broad | Existing CRM Activity remains CRM-bounded | Require explicit object qualification in new work |
| `Log` / `AuditLog` | `AuditEntry` when accountability is intended | Log may mean diagnostics rather than audit | Existing audit tables remain | New audit contracts use AuditEntry; application logs remain technical logs |
| `TrackingNumber` / `PublicCode` | `TrackingCode` | Multiple names for public tracking reference | Legacy payload fields remain versioned compatibility | New Project contracts use TrackingCode; document old fields |
| `ProjectNumber` / `CaseNumber` / `JobNumber` | `ProjectCode` | Avoid conflating internal reference and identity | Imported external references may preserve source name | New internal generated reference uses ProjectCode |

## Part 6 — Reserved Concepts

Reserved concepts have names and boundaries but are intentionally not implemented by this phase. Reservation prevents future teams from using the names for incompatible objects.

| Reserved Concept | Intended meaning | Anticipated owner/relationship | Explicitly not authorized now |
|---|---|---|---|
| `Warehouse` | Facility/operational domain for storage and handling | Organization/location boundary; WarehouseLot may be ExecutionUnit type | Warehouse inventory/WMS implementation |
| `Customs` | Regulatory execution domain for declarations, inspections, holds, clearance | OperationalShipment/ExecutionUnit events and specialist records | Full customs filing/compliance engine |
| `FinancialSettlement` | Reconciliation and settlement of operational financial obligations | Future finance aggregate linked by references/events | Ledger, invoice, payment, or accounting source of truth |
| `ContainerBooking` | Carrier booking for containerized sea/rail movement | OperationalShipment/Route/ExecutionUnit reference | Booking integration or separate aggregate without ADR |
| `RailConsignment` | Rail-specific consignment contract/reference | OperationalShipment and wagon ExecutionUnits | New standalone table/lifecycle without invariants review |
| `SeaBooking` | Sea carrier booking/voyage allocation | OperationalShipment and sea/container ExecutionUnits | Vessel ownership model or carrier API integration |
| `AirWaybill` | Air cargo contract/reference, including master/house relationships | OperationalShipment/air cargo ExecutionUnit | Air cargo financial/customs implementation |
| `ERPIntegration` | Versioned adapter boundary for ERP identities, commands, and events | Platform integration module | Direct ERP writes to domain tables |
| `BPMProcess` | Orchestrated long-running process coordinating explicit domain actions | BPM adapter; domain aggregates remain sources of truth | Generic engine-owned mutation of statuses |
| `AIRecommendation` | Evidence-backed, non-mutating proposed insight/action | AI governance boundary, scoped to canonical subjects | Automatic execution or approval |
| `AIAction` | Authorized execution of an explicit domain command by an AI principal | Same business API/policy/audit as human/service actions | Direct database mutation or broad autonomous role |
| `SplitMergeLineage` | Immutable ancestry and reconciliation for ExecutionUnit split/merge | ExecutionUnit relationship/event | Split/merge commands before PDR-007 acceptance |
| `DigitalSignatureValidation` | Cryptographic validation result/evidence under approved trust policy | Document/Approval boundary | Treating signature image/metadata as verified signature |
| `LegalHold` | Retention override prohibiting purge for specified subjects/artifacts/events | Compliance/retention boundary | Release/purge automation before PDR-011 acceptance |

## Part 7 — AI Vocabulary

AI agents must treat this catalog as a controlled ontology, not a suggestion list.

1. Use canonical names in observations, recommendations, prepared actions, explanations, audit summaries, and generated technical designs.
2. Never invent synonyms, shorten formal names, or promote a legacy alias to a new object name.
3. Recognize aliases in user input and legacy data, then normalize them explicitly: “legacy ShipmentTransportUnit, canonical ExecutionUnit.”
4. Ask for clarification when “shipment,” “case,” “document,” “status,” “event,” or “owner” could identify more than one canonical concept.
5. Never infer authority from vocabulary. Customer, payer, consignee, cargo owner, Stakeholder, User, Role, and Permission remain distinct.
6. Never infer lifecycle from an alert: DelayCondition does not change ExecutionUnitStatus by itself.
7. Prefer canonical identifiers and include object type with every referenced ID.
8. Explanations must state status owner and evidence scope: “ExecutionUnit status,” not “the status.”
9. Prepared actions must name the canonical command target, expected version, policy/permission, evidence, and correlation identity.
10. Alias recognition does not authorize compatibility behavior or schema changes.
11. Reserved concepts may be discussed as future designs but must be labeled “reserved/not implemented.”
12. AI-generated ADR/PDR/API/migration proposals must pass a vocabulary check against this catalog.

## Part 8 — Governance

### Catalog owner

The accountable business owner is the Product Owner for Platform Domain Language. Architecture is the technical steward. Operations, Security, Data, and relevant domain owners are mandatory reviewers for objects affecting their policies.

### Adding a new object

1. Search this catalog and Alias Registry for an existing meaning.
2. Provide business definition, technical boundary, owner, identifier, lifecycle owner, relationships, visibility, security, data/migration, and AI impact.
3. Demonstrate that the proposal is an object rather than a status, event type, role, UI component, report column, or alias.
4. Resolve conflicts through a PDR for business meaning and an ADR for architecture/ownership when material.
5. Add the object only after required approvals; Reserved status may be used before implementation.

### Deprecating a name

- Record canonical replacement, reason, compatibility surface, owner, telemetry/usage gate, removal strategy, and earliest removal release.
- Deprecation does not authorize immediate rename/drop.
- Legacy names may persist in tables/APIs through adapters but cannot be used in new primary contracts.
- Removal follows additive migration, consumer verification, deprecation window, and rollback planning.

### Changing terminology

A spelling correction that does not change meaning requires catalog-owner and Architecture review. A semantic change, merge, split, ownership change, or identifier change requires Product approval and usually a new/updated PDR and ADR. Accepted historical documents are not silently edited; contradictions are documented and supersession is explicit.

### Relationship to ADRs and PDRs

- This catalog answers “what is this object called and what does it mean?”
- A PDR answers “which business policy/option is approved?”
- An ADR answers “which architecture and ownership decision is approved?”
- If an Accepted ADR/PDR intentionally defines a more specific meaning, it governs that decision scope. The catalog must be updated through governance to remain consistent.
- Proposed ADR/PDR text does not automatically make a catalog recommendation an Accepted product decision.

### Required terminology gate

Every future ADR, PDR, migration design, API contract, database design, UI feature, report, and AI action design must include a vocabulary check. CI automation may later detect prohibited aliases, but automated checks do not replace semantic review.

## Part 9 — Consistency Review

This review covers existing ADRs, ADR-017 through ADR-020, PDR-001 through PDR-011, and the workshop. Existing documents were not modified.

### Missing concepts

The Phase 0.5 documents clearly define Project, ShipmentRequest, OperationalShipment, ExecutionUnit, OperationalEvent, Timeline, DocumentArtifact, and DocumentAttachment. The following cross-platform concepts were not previously defined with one canonical contract and are supplied by this catalog:

- `DocumentVersion`, `DocumentRequirement`, and `AttachmentVisibility` as distinct document concepts.
- `Task` as the common business term above operational WorkItem and CRM-specific task implementations.
- `OperationalAlert` versus `OperationalException` versus `DelayCondition`.
- `AuditEntry` versus OperationalEvent, Timeline, application logs, and domain-specific audit tables.
- `Quotation` as the business name above the actor-specific `ExpertQuote` implementation.
- `Stakeholder` as the typed party relationship rather than treating payer/consignee/cargo owner as owners/users.
- `ProjectCode` versus `TrackingCode` versus opaque primary identifier.
- Status ownership categories and the prohibition on a global unowned status enum.

These definitions do not authorize new persistence or behavior.

### Duplicate concepts

| Duplicate/drift area | Existing forms | Canonical resolution |
|---|---|---|
| Execution unit | ShipmentTransportUnit, TrackingUnit, OperationalUnit, Unit | ExecutionUnit; legacy model remains adapter source |
| Execution shipment | OperationalShipment, ShipmentJob, Shipment | OperationalShipment |
| Document binary/context | CaseDocumentFile, File, Document, Attachment | DocumentArtifact + DocumentAttachment + DocumentVersion |
| Work queue action | WorkItem, Task, CRM Task | Task as umbrella; qualify bounded subtype |
| Exception | ExceptionCase, RouteException, Issue | OperationalException with typed specialization |
| Audit | OperationalAudit, DocumentAuditEvent, logs | AuditEntry as canonical accountability record; bridge specialized stores |
| Quote | ExpertQuote, Quote | Quotation |
| Public reference | tracking_number, tracking_code, PublicCode | TrackingCode, qualified by owning scope |

### Conflicting names

1. **Shipment:** ADR-016 uses Shipment broadly for durable workflow state, while ADR-003 formally selects OperationalShipment for the execution aggregate. Future formal work must use OperationalShipment; historical ADR-016 remains interpreted by its context.
2. **Project/Case:** Current case-document routes/models use “case” for ShipmentRequest context. ADR-017 defines Project as a new coordination boundary. Existing case identifiers must not be reinterpreted as Project IDs.
3. **Route/RoutePlan:** Business language often says Route while implementation owns revisioned RoutePlan. The catalog makes Route the business concept and requires revision qualification where technical precision matters.
4. **Status:** ShipmentRequest commercial status, OperationalShipment lifecycle, ExecutionUnit proposed lifecycle, route/checkpoint state, approval state, and document state are distinct. No universal status mapping is valid.
5. **Visibility:** Current unit updates use `is_customer_visible`; ADR-020 proposes multi-audience AttachmentVisibility. The boolean remains a legacy event/update field and must not become document visibility policy.

### Deprecated terminology

- `ShipmentJob` is already explicitly deprecated by ADR-003.
- `ShipmentTransportUnit`, `TrackingUnit`, and `OperationalUnit` are non-canonical after ADR-018.
- Generic `Case`, `File`, `Attachment`, `Request`, `Shipment`, `Unit`, `Activity`, `Log`, and unqualified `Status` are prohibited in new formal contracts where ambiguity exists.
- `attention_required` and `delayed` must not be introduced as canonical lifecycle statuses.

### Recommended corrections for future authorized work

No existing document is changed in this phase. When separately authorized:

1. Add a terminology note or catalog link to future ADRs/PDRs and API documentation.
2. Use full canonical names in new OpenAPI schemas and DTOs.
3. Document legacy `ExpertQuote` as Quotation compatibility rather than performing an immediate rename.
4. Document WorkItem as an OperationalTask implementation while retaining accepted control-tower semantics.
5. Qualify broad Shipment references in new time/session documentation as OperationalShipment when that is the intended owner.
6. Keep current `CaseDocumentFile` semantics explicit until an additive artifact/attachment migration is approved.
7. Prevent Project from inheriting legacy “case” identifiers or ShipmentRequest tracking codes silently.
8. Establish a later machine-readable vocabulary/lint rule only after Product and Architecture accept this catalog.

## Part 10 — Readiness Assessment

### Assessment

The platform now has a coherent canonical business language suitable for architecture review and long-term evolution at the documentation level. The catalog separates business coordination, commercial intake, execution, units, events, projections, alerts, documents, authorization, reporting, and AI concepts while preserving explicit compatibility with current models.

SLICE-001 governance reconciliation Accepted PDR-001 through PDR-004 and Deferred PDR-005, PDR-006, and PDR-010. Remaining PDRs retain their individual Proposed status. The catalog is ready to serve as the terminology gate once Product and Architecture accept its governance status; these decision transitions do not authorize a later slice.

### Mandatory terminology for future work

Every future ADR, PDR, migration, API, database change, backend/frontend feature, UI, report, document, and AI design must use or explicitly map to these terms:

- `Project`
- `ShipmentRequest`
- `OperationalShipment`
- `ExecutionUnit`
- `OperationalEvent`
- `Timeline`
- `OperationalStatus` qualified by owner
- `OperationalAlert`
- `OperationalException`
- `DelayCondition`
- `Route`
- `Checkpoint`
- `Milestone`
- `Task`
- `DocumentArtifact`
- `DocumentAttachment`
- `DocumentVersion`
- `DocumentRequirement`
- `AttachmentVisibility`
- `Approval`
- `Quotation`
- `Customer`
- `Organization`
- `Stakeholder`
- `User`
- `Role`
- `Permission`
- `ServiceLevelAgreement`
- `Report`
- `Dashboard`
- `Notification`
- `Comment`
- `AuditEntry`
- `ProjectCode`
- `TrackingCode`

Any deviation must cite the canonical object, explain whether the term is a bounded subtype, legacy alias, or reserved concept, and receive the required vocabulary governance approval.

### Readiness verdict

**Canonical vocabulary is complete for Phase 0.6 review. It is suitable as the single terminology reference after Product Owner and Architecture acceptance. Implementation remains paused and no prior ADR/PDR status is changed by this document.**

### Accepted logistics-network vocabulary extension

[PDR-016](PDR-016-logistics-network-foundation.md) and [ADR-025](adr/ADR-025-logistics-network-aggregate-boundaries.md) accept three deliberately separate terms: `LogisticsPointType` (Reference Data classification), `LogisticsPoint` (reusable Master Data place), and `ProjectLogisticsPoint` (Project configuration association). They are authorized but not implemented and must not be merged with Province/City, Customer, RoutePlan, Checkpoint, Milestone, or OperationalEvent.
