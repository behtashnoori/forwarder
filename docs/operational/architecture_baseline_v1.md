# Forwarder Platform Architecture Baseline v1

- Architecture Baseline Version: 1.0
- Status: Proposed
- Date: 2026-07-31
- Scope: Forwarder platform architecture and governance entry point
- Audience: Developers, architects, Product, Operations, Security, Data, QA, and AI agents
- Change authority: Architecture governance with Product decision references where behavior changes

This document is the official proposed entry point and index for Forwarder architecture. It introduces no new domain or architecture decision. It organizes existing rules, Accepted ADRs, Proposed Phase 0.5 ADRs/PDRs, operational documentation, release governance, and the Canonical Business Object Catalog into one governed reading and delivery baseline.

## 1. Mission

### Platform mission

Forwarder coordinates commercial shipment intake and operational logistics execution with secure customer visibility, traceable decisions, controlled documents, actionable operational monitoring, and a safe path toward AI-assisted operations.

### Business vision

The platform is intended to evolve from request and quotation management into a multimodal logistics operating platform in which a customer Project can coordinate multiple OperationalShipments and independently managed ExecutionUnits. Commercial truth, execution truth, customer visibility, operational evidence, and governance remain distinct but traceable.

### Product scope

The established and proposed architecture covers:

- commercial ShipmentRequest intake, assignment, Quotation, and customer response;
- operational execution through OperationalShipment, Route, Checkpoint, Milestone, and verified events;
- Project-level coordination and aggregation as proposed by ADR-017;
- independently concurrent ExecutionUnits as accepted by ADR-018;
- permission-filtered operational history and event projections as accepted by ADR-019;
- document artifact, attachment, version, requirement, visibility, and audit foundations as proposed by ADR-020;
- operational alerts, exceptions, tasks/work queues, reports, dashboards, public/customer visibility, security, audit, migration, deployment, and release controls;
- AI observation, recommendation, preparation, explanation, and later policy-controlled actions.

### Out of scope for this baseline

This baseline does not authorize or implement:

- code, API, database, migration, UI, build, deployment, or release changes;
- automatic acceptance of Proposed ADRs or PDRs;
- microservice extraction without a separate evidence-based ADR;
- full ERP, BPM, accounting/financial settlement, warehouse-management, or customs-filing systems;
- unrestricted partner/customer document access;
- autonomous AI actions without an explicit policy, permission, approval boundary, and audit;
- destructive legacy replacement or big-bang migration.

Reserved future concepts are cataloged in the [Canonical Business Object Catalog](canonical_business_object_catalog.md) and remain intentionally unimplemented.

### Long-term evolution goals

- Preserve stable business language while implementation evolves.
- Extend road, rail, sea, air, warehouse, customs, and multimodal execution without redefining core objects.
- Keep commercial and operational lifecycles separate and traceable.
- Scale Project views from tens to hundreds of ExecutionUnits through projections and pagination.
- Make events, documents, permissions, and actions explainable and auditable.
- Adopt new data and APIs additively with safe rollback and legacy compatibility.
- Progress AI capability from read/recommend to controlled action only through approved policies.
- Integrate ERP/BPM/partners through explicit adapters, APIs, identities, events, idempotency, and outbox seams.

## 2. Architecture Principles

This section summarizes existing decisions and links to their authoritative sources. It does not replace them.

| Principle | Baseline summary | Authoritative references |
|---|---|---|
| Modular Monolith | Maintain one deployable with bounded modules and explicit ownership/import contracts until extraction evidence justifies change | [ADR-001](adr/ADR-001-modular-monolith.md) |
| Domain separation | Keep ShipmentRequest commercial intake separate from OperationalShipment execution; never treat Project, Request, Shipment, and ExecutionUnit as synonyms | [ADR-002](adr/ADR-002-request-operation-separation.md), [ADR-003](adr/ADR-003-operational-shipment-terminology.md), [ADR-017](adr/ADR-017-operational-project-architecture.md) |
| Domain-driven architecture | Business objects, aggregates, lifecycle owners, actions, and invariants govern technical design | [Domain Dictionary](phase0_domain_dictionary.md), [Target Domain Model](../forwarder_target_domain_model.md), [Canonical Catalog](canonical_business_object_catalog.md) |
| Route and evidence model | OperationalShipment owns revisioned routes, legs, checkpoints, milestones, and verified append-only evidence | [ADR-004](adr/ADR-004-route-leg-milestone-model.md), [ADR-005](adr/ADR-005-canonical-location.md), [ADR-009](adr/ADR-009-milestone-verification.md) |
| Backward compatibility | Preserve legacy behavior through additive models, adapters, shadow reads, feature flags, and deprecation gates | [ADR-006](adr/ADR-006-additive-migration.md), [Migration Sequence](phase0_migration_sequence.md) |
| Additive migration | Expand → migrate → verify → switch → contract; migrations are explicit, independently executed, validated, and rollback-ready | [ADR-006](adr/ADR-006-additive-migration.md), [ADR-011](adr/ADR-011-explicit-migration-execution.md), [Runtime Migration Safety](phase0_1_runtime_migration_safety.md) |
| Security first | Deny by default, enforce authorization in backend, scope by organization/resource, protect files, prevent enumeration, and audit sensitive actions | [Permission Matrix](phase0_permission_matrix.md), [Security Rule](../../../28-AI-Rules/08-Security-and-Audit-Standard.md), [ADR-015](adr/ADR-015-repository-secret-scanning.md) |
| Documentation first | Architecture, Product policy, migration, compatibility, version, deployment, rollback, and acceptance criteria precede implementation | [AI Engineering Standard](../../../28-AI-Rules/01-AI-Engineering-Standard.md), [Documentation Standard](../../../28-AI-Rules/11-Documentation-Standard.md) |
| AI-ready architecture | Expose stable read and explicit action contracts; record evidence, permission, explanation, approval, and audit; no autonomous action without policy | [AI Native Standard](../../../28-AI-Rules/02-AI-Native-Application-Architecture.md), [Agent Governance](../../../28-AI-Rules/03-Agent-Governance.md), [AI Provider ADR documentation](../AI_READY_2_AI_PROVIDER_ABSTRACTION.md) |
| Canonical vocabulary | Use the catalog as the terminology gate; legacy aliases are compatibility terms, not new primary names | [Canonical Catalog](canonical_business_object_catalog.md) |
| Status ownership | Commercial, operational, verification, task, document, approval, and alert states have distinct owners | [ADR-007](adr/ADR-007-commercial-operational-status.md), [State Matrix](phase0_state_transition_matrix.md), [Canonical Status Vocabulary](canonical_business_object_catalog.md#part-4--canonical-status-vocabulary) |
| Operational event model | Important facts are immutable and selected projections rebuildable; this is lightweight event sourcing, not mandatory full event sourcing | [ADR-009](adr/ADR-009-milestone-verification.md), [ADR-019](adr/ADR-019-unified-timeline-operational-event-model.md) |
| Document architecture | Separate immutable binary artifact from scoped attachment/version/visibility; never copy a binary merely for multiple scopes | [ADR-020](adr/ADR-020-document-attachment-visibility-architecture.md) |
| Control tower | Alerts/exceptions/tasks are actionable projections; work queues do not become operational truth | [ADR-008](adr/ADR-008-control-tower-work-queue.md) |
| Concurrency and retry safety | Sensitive creates/events/transitions use idempotency; aggregate mutations use expected versions and atomic audit/outbox | [ADR-010](adr/ADR-010-idempotency-locking.md) |
| Time correctness | Distinguish Instant, Local Date, and business local datetime; keep occurred and recorded times separate | [ADR-016](adr/ADR-016-time-and-timezone-architecture.md) |
| Deterministic runtime and deployment | Startup has no schema writes; use canonical entrypoint, controlled environment, quality gates, immutable release identity, and manifest | [ADR-011](adr/ADR-011-explicit-migration-execution.md), [ADR-012](adr/ADR-012-versioned-backend-entrypoint.md), [Release Governance](../../../28-AI-Rules/06-Version-Release-Deployment-Governance.md) |
| Human approval boundaries | AI and automation may read/recommend/prepare; sensitive execution and approval remain governed explicit actions | [Operational Workshop](operational_architecture_workshop.md#5-ai-readiness), [PDR](phase0_5_product_decision_register.md) |

ADR-017 through ADR-019, PDR-001 through PDR-006, and PDR-010 are Accepted as of 2026-07-31. ADR-020 and PDR-007 through PDR-009/PDR-011 remain `Proposed`. Inclusion in this index does not change any individual status.

## 3. Architecture Map

```text
AI Rules
   ↓
Architecture Baseline
   ↓
Canonical Business Object Catalog
   ↓
Architecture Decision Records (ADR)
   ↓
Product Decision Register (PDR)
   ↓
Decision Workshop
   ↓
Implementation Design and Slices
   ↓
Release and Version Governance
   ↓
Production Operations and Evidence
```

### Layer purposes

| Layer | Purpose | Must not be used as |
|---|---|---|
| AI Rules | Organization-wide engineering, AI, data, API, version, migration, security, testing, environment, and documentation standards | Project-specific domain decision |
| Architecture Baseline | Entry point, index, reading order, governance gate, and maturity snapshot | Replacement for source ADR/PDR/runbook |
| Canonical Catalog | Stable names, definitions, aliases, status ownership, and terminology governance | Approval of Proposed Product behavior |
| ADR | Records architecture decisions, alternatives, consequences, compatibility, rollout, and rollback | Product policy approval unless Product explicitly owns/approves it |
| PDR | Records business options, recommendation, owner, required approvers, blockers, and fail-safe behavior | Technical implementation specification |
| Workshop | Facilitates explicit cross-functional decision closure | New ADR/PDR or silent acceptance mechanism |
| Implementation | Implements only accepted scope with contracts, tests, migration/rollback design, and traceability | Place to invent unresolved business policy |
| Release | Applies SemVer, immutable release identity, manifest, quality gates, deployment plan, and rollback | Substitute for architecture review |
| Operations | Runs, observes, backs up, restores, responds, and preserves evidence under approved runbooks | Source of undocumented schema/domain changes |

Governance flows downward; evidence and newly discovered constraints flow upward through review. A lower layer cannot silently override an upper-layer rule.

## 4. Reading Order

### 4.1 New developer

1. This baseline.
2. [README](../../README.md) and [System Architecture](../SYSTEM_ARCHITECTURE.md).
3. [Canonical Business Object Catalog](canonical_business_object_catalog.md).
4. ADR-001, ADR-002, ADR-003, ADR-006, ADR-007, ADR-010, ADR-011, ADR-012, ADR-016.
5. ADR-017 through ADR-020, noting their current status.
6. [PDR](phase0_5_product_decision_register.md) and [Workshop](operational_architecture_workshop.md).
7. Relevant phase contract, permission, state, test, migration, and runbook documents for assigned work.

### 4.2 Backend developer

1. This baseline and Canonical Catalog.
2. ADR-001 through ADR-012 and ADR-016; then ADR-017 through ADR-020 for the proposed future boundary.
3. [Domain Dictionary](phase0_domain_dictionary.md), [State Matrix](phase0_state_transition_matrix.md), [Permission Matrix](phase0_permission_matrix.md), and [API Contract Draft](phase0_api_contract_draft.md).
4. [Migration Sequence](phase0_migration_sequence.md), ADR-011, [Database Revision Runbook](phase0_1_database_revision_runbook.md), and relevant phase migration/rollback documentation.
5. Relevant Phase 1A/1B API, domain, permission, and test contracts.
6. Release/version and quality-gate sources before implementation completion.

### 4.3 Frontend developer

1. This baseline and Canonical Catalog.
2. ADR-002, ADR-003, ADR-007, ADR-008, ADR-016, and proposed ADR-017 through ADR-020.
3. PDR and Workshop sections governing labels, visibility, actions, status, pagination, documents, and AI approval.
4. OpenAPI/current API contract and relevant UI/browser UAT documentation.
5. Security/permission matrices; UI guards are not authorization.
6. Acceptance criteria and frontend quality gates.

### 4.4 Product Owner

1. Mission and architecture map in this baseline.
2. Canonical Catalog Parts 1, 2, 4, 5, and 10.
3. ADR-002, ADR-003, ADR-007, and proposed ADR-017 through ADR-020.
4. PDR-001 through PDR-011.
5. Operational Architecture Workshop, especially Business Model, Governance, Decision Matrix, and Readiness Assessment.
6. Relevant acceptance criteria and release/version impact before approving implementation scope.

### 4.5 Operations

1. This baseline and Canonical Catalog operational objects/statuses.
2. ADR-004, ADR-005, ADR-007, ADR-008, ADR-009, ADR-010, ADR-016, and proposed ADR-017 through ADR-019.
3. PDR-002, PDR-004, PDR-006, PDR-007, PDR-010, and PDR-011.
4. State, permission, SLA/threshold, test, backup/restore, migration, deployment, and UAT runbooks relevant to the release.

### 4.6 Security

1. AI Rules for Security/Audit, Agent Governance, API integration, environment, and release governance.
2. This baseline and Canonical Catalog identity/authorization/document/AI vocabulary.
3. ADR-006, ADR-009, ADR-010, ADR-011, ADR-014, ADR-015, ADR-016, and proposed ADR-017 through ADR-020.
4. Permission Matrix, PDR security impacts/fail-safe behavior, and Workshop Governance/AI sections.
5. Authentication/session, secret remediation, document storage, public allowlist, and negative authorization tests for the affected release.

### 4.7 AI agent

1. All AI Rules in `D:\1-webapp\28-AI-Rules`.
2. This baseline.
3. Canonical Catalog, especially Parts 3, 5, 7, and 8.
4. Applicable Accepted ADRs, then Proposed ADRs with status explicitly preserved.
5. Applicable PDRs and fail-safe behaviors; unresolved Proposed decisions must not be inferred.
6. Permission, API, migration, version/release, test, and deployment sources relevant to the requested action.
7. Repository state and user constraints before any mutation.

An AI agent must ask or remain fail-safe when a required Product decision is unresolved. It must never treat workshop recommendations as accepted decisions.

## 5. Repository Governance

### 5.1 Authoritative locations

| Information | Location | Authority/use |
|---|---|---|
| Organization-wide AI/engineering rules | `D:\1-webapp\28-AI-Rules\` | Mandatory before development/architecture work |
| Architecture baseline | `docs/operational/architecture_baseline_v1.md` | Entry point and index |
| Canonical vocabulary | `docs/operational/canonical_business_object_catalog.md` | Terminology reference |
| ADRs | `docs/operational/adr/` | Architecture decisions; status in each document |
| Product Decision Register | `docs/operational/phase0_5_product_decision_register.md` | Product decisions/blockers/fail-safe behavior |
| Decision workshop | `docs/operational/operational_architecture_workshop.md` | Decision facilitation and readiness review |
| Operational architecture and phase docs | `docs/operational/` | Contracts, matrices, migration, UAT, evidence, runbooks |
| System/current/target architecture | `docs/SYSTEM_ARCHITECTURE.md`, `docs/forwarder_current_architecture_inventory.md`, `docs/forwarder_target_domain_model.md` | Architecture context and inventories |
| OpenAPI contract | `docs/openapi/openapi.yaml` and `docs/openapi/README.md` | Machine-readable API documentation |
| Migration source | `backend/migrations/` | Canonical Alembic path; changes require authorization |
| Version/release rules | `D:\1-webapp\28-AI-Rules\06-Version-Release-Deployment-Governance.md` | SemVer, release identity, immutable deployment, manifest |
| Release history/identity | `docs/RELEASE_NOTES.md` and release `release-manifest.json` | Release decision/history and immutable identity evidence |
| Deployment documentation | `DEPLOYMENT.md`, `docs/operational/phase0_1_deployment_runbook_windows.md`, relevant phase runbooks | Controlled deployment; context-specific authority |
| Quality/security gates | `.github/workflows/quality-gates.yml`, `.github/workflows/secret-scan.yml` | CI gates; do not replace manual architecture/security review |

### 5.2 Precedence and non-duplication

- AI Rules govern organization-wide mandatory practice.
- Accepted ADRs govern architecture within their scope.
- Accepted PDRs govern Product behavior within their scope.
- The Canonical Catalog governs terminology, subject to explicitly accepted more-specific decisions and its update process.
- Phase contracts/matrices/runbooks govern their named phase/release and must conform to higher-level decisions.
- This baseline indexes and explains precedence; it does not duplicate full rules.
- If sources conflict, stop implementation, record the conflict, identify owners, and resolve through ADR/PDR/catalog governance. Do not choose silently.

## 6. Platform Evolution Roadmap

```text
Phase 0 — Architecture and Governance
   ↓
Phase 1 — Core OperationalShipment Foundation
   ↓
Phase 2 — Project and ExecutionUnit Scale
   ↓
Phase 3 — Unified Timeline and Operational Events
   ↓
Phase 4 — Document Platform and Visibility
   ↓
Phase 5 — Reporting, Export, and Control-Tower Scale
   ↓
Phase 6 — AI Assistants and Controlled Actions
   ↓
Phase 7 — ERP/BPM/Partner Integration
```

### Phase intent

| Phase | Intent | Stable principles carried forward |
|---|---|---|
| 0 | Freeze vocabulary, decisions, ownership, governance, compatibility, security, and readiness | Documentation first; explicit status/owners; no silent policy |
| 1 | Maintain and harden core OperationalShipment route/milestone/event execution | Request/operation separation, idempotency, verification, organization scope |
| 2 | Introduce accepted Project/ExecutionUnit foundations and scalable internal UX | Canonical vocabulary, independent aggregates, additive migration, pagination |
| 3 | Unify event envelope and permission-filtered timeline projections | Append-only correction, occurred/recorded times, deterministic rebuild |
| 4 | Introduce artifact/attachment/version/visibility architecture | Private storage, deny-by-default, no binary duplication, retention/audit |
| 5 | Scale reports, XLSX/ZIP jobs, alerts, exceptions, tasks, and dashboards | Bounded workloads, policy versions, reproducible reports, per-item authorization |
| 6 | Progress from AI read/recommend to prepare and policy-controlled execution | Explicit APIs/actions, human approval boundaries, evidence/explanation/audit |
| 7 | Integrate ERP, BPM, carriers, partners, and external data | Stable identities/contracts, adapters, idempotency, outbox, source provenance |

Phase names, contents, and sequencing may evolve through governance. The core object meanings, aggregate ownership, backward-compatibility discipline, security model, event provenance, document separation, human approval boundaries, and release controls remain stable unless superseded through accepted ADR/PDR/catalog updates.

This roadmap is directional, not implementation authorization or a release promise.

## 7. Development Readiness Checklist

Before implementation starts, every item must be answered with evidence or marked not applicable with rationale.

### Architecture and Product

- [ ] This architecture baseline was reviewed.
- [ ] Canonical Business Object Catalog was reviewed and terminology mapped.
- [ ] Applicable Accepted ADRs were identified and reviewed.
- [ ] Applicable Proposed ADRs were not treated as Accepted.
- [ ] Applicable PDRs were reviewed; blocking decisions are Accepted.
- [ ] Workshop recommendations were not used as silent approval.
- [ ] Aggregate, lifecycle, identifier, and transactional ownership are explicit.
- [ ] Acceptance criteria are traceable to ADR/PDR/test IDs.

### Compatibility, data, and migration

- [ ] Current architecture/model/API behavior was inventoried.
- [ ] Backward-compatibility and N/N-1 requirements were evaluated.
- [ ] Database impact was evaluated.
- [ ] Additive migration/backfill/quarantine/data gates were designed where required.
- [ ] Canonical Alembic path and explicit migration execution rules are preserved.
- [ ] Rollback/fallback preserves data and was rehearsed proportionate to risk.
- [ ] No legacy identity/status/time/location value is guessed during backfill.

### Security and operations

- [ ] Authentication, authorization, organization/resource scope, IDOR, and mass-assignment impacts were evaluated.
- [ ] Public/customer projections use explicit allowlists and negative leakage tests.
- [ ] Sensitive actions have permissions, reasons, versions, idempotency, approvals, and audit as required.
- [ ] Document/file visibility, storage, download, retention, and malware/signature assumptions were evaluated where applicable.
- [ ] Scalability limits, pagination, background jobs, rate limits, SLOs, and observability were evaluated.
- [ ] Deployment, environment, backup/restore, restart, readiness, and rollback impacts were evaluated.

### Version, release, quality, and AI

- [ ] Current and proposed versions, SemVer change type, and rationale were recorded.
- [ ] Release identity/manifest impact was evaluated.
- [ ] Backend, frontend, migration, contract, security, smoke, performance, and regression tests are defined.
- [ ] AI read/recommend/prepare/execute/approve boundaries were evaluated.
- [ ] AI context uses canonical vocabulary and permission-filtered evidence.
- [ ] AI actions, if any, use explicit authorized APIs and complete audit; no direct database action.
- [ ] Documentation and operational runbooks are updated within the authorized scope.

Implementation is not ready if a blocking item is unknown, unresolved, or supported only by an unapproved assumption.

## 8. Governance Responsibilities

| Role | Primary responsibilities | Required evidence/gates |
|---|---|---|
| Product Owner | Own business outcomes, customer/party behavior, lifecycle semantics, acceptance criteria, priorities, and PDR decisions | Accepted blocking PDRs, explicit alternatives/reasons, approved scope/UX behavior |
| Architecture | Steward aggregates, boundaries, vocabulary consistency, ADRs, compatibility, integration seams, and baseline | ADR review/status, catalog alignment, dependency/consistency review, architecture readiness verdict |
| Backend | Implement accepted domain actions, invariants, authorization, idempotency, transactions, events, projections, persistence, and contracts | Code/tests mapped to accepted decisions; migration/rollback/API evidence |
| Frontend | Implement canonical labels, scalable projections, safe action UX, customer/internal separation, conflict/error handling, and accessibility | API/permission alignment, UI acceptance/browser tests, no client-only authorization assumptions |
| Security | Own threat analysis, authentication/authorization policy, least privilege, sensitive actions, file/public access, secrets, and AI boundaries | Permission matrix, negative tests, audit requirements, approval/break-glass policy, security sign-off |
| Operations | Own operational workflow validity, roles, SLAs/thresholds, control-tower actions, deployment/runbooks, monitoring, backup/restore, and incident response | Operational scenarios/UAT, approved thresholds, deployment and recovery evidence |
| Data | Own identifiers, cardinality profiling, data quality, schema/migration review, backfill/reconciliation, lineage, retention data requirements, and reporting semantics | Data profile/gates, migration validation, duplicate/orphan checks, reconciliation and rollback evidence |
| QA | Own traceability, test strategy, critical path/regression, authorization, migration, performance, browser/UAT, and release quality gates | Test matrix/results, defect closure, flaky-test control, release recommendation |
| AI | Use canonical vocabulary, observe only allowed context, identify assumptions, cite evidence, respect PDR/ADR status, and act only through approved permissions/APIs | Explanation/evidence, policy and human approval references, idempotency/correlation, action audit |

### Shared accountability

- No role may silently accept another role’s decision.
- Product and Architecture jointly protect domain meaning.
- Security and Data may block unsafe ownership, visibility, identifier, migration, retention, or AI-action designs.
- Operations validates that accepted models represent real workflows.
- QA verifies claims but does not redefine acceptance policy.
- AI has no independent authority to approve architecture, Product decisions, releases, or sensitive actions.

## 9. Architecture Freeze

### Official reference statement

Upon Architecture acceptance, this baseline becomes the official architecture entry point for the Forwarder platform. Until then, its status remains `Proposed`. Existing source documents retain their individual statuses and authority.

### Change control

Any future change affecting one or more of the following requires an ADR or an explicitly scoped superseding ADR:

- canonical business objects or their meanings;
- aggregate ownership or transactional boundaries;
- vocabulary and aliases;
- status ownership, values, or transitions;
- operational events, ordering, correction, or projections;
- document artifact/attachment/version/visibility architecture;
- permissions, organization/resource ownership, public access, or sensitive actions;
- lifecycle, completion, cancellation, reopen, split/merge, retention, or purge semantics;
- integration ownership or source-of-truth boundaries;
- AI execution/approval authority.

Changes affecting Product behavior must also reference the relevant Accepted PDR or introduce a new PDR. A technical ADR cannot silently decide unresolved business behavior.

Terminology changes must update the Canonical Business Object Catalog through its governance process. Existing Accepted historical documents are not silently rewritten; supersession, compatibility, and deprecation are explicit.

Implementation plans, migrations, APIs, UI, reports, and releases must cite the governing ADR/PDR/catalog entries. Emergency remediation may follow incident policy but must not create undocumented permanent architecture.

## 10. Consistency Review

### Scope reviewed

- ADR-001 through ADR-020 present in `docs/operational/adr/`.
- Phase 0/1 operational architecture, contracts, matrices, migration, UAT, evidence, and runbooks.
- Phase 0.5 Product Decision Register.
- Operational Architecture Workshop.
- Canonical Business Object Catalog.
- General system/target/current architecture, OpenAPI, release notes, deployment, CI, and AI Rules references.

No existing document was modified during this review.

### Cross-reference matrix

| Concern | Primary authority/index | Supporting sources | Status observation |
|---|---|---|---|
| Modular architecture | ADR-001 | System Architecture, current inventory | ADR Accepted |
| Request vs execution | ADR-002/003/007 | Domain Dictionary, target model | ADRs Accepted |
| Route/milestone/location | ADR-004/005/009 | Phase 1A/1B domain/API/state/test docs | ADRs Accepted; implementations documented |
| Migration/runtime/release safety | ADR-006/011/012/014/015/016 | Migration sequence, runbooks, AI Rules, CI | ADRs Accepted |
| Project architecture | ADR-017 | PDR-001–004, Workshop, Catalog | ADR Accepted; PDR-001–004 Accepted for SLICE-001 |
| ExecutionUnit | ADR-018 | PDR-005–007/010, Workshop, Catalog | ADR Accepted; PDR-005/006/010 Accepted for Release 1.2.0 |
| Unified events/timeline | ADR-019 | ADR-009/010/016, Workshop, Catalog | ADR Accepted; preserves specialized events |
| Document platform | ADR-020 | PDR-008/009/011, Workshop, Catalog | ADR Proposed; later-slice decisions Proposed |
| Vocabulary | Canonical Catalog | All ADR/PDR/workshop sources | Catalog draft; proposed for authority |
| Human/AI approval | AI Rules + PDR/Workshop | AI-ready docs, Permission Matrix | Principles established; action policies not broadly accepted |
| Version/release | AI Rule 06, Release Notes, manifests | Deployment/runbooks/CI | Existing controls; version sources require release-by-release consistency |

### Broken references

- No broken relative Markdown reference was identified among ADR-017 through ADR-020, the PDR, Workshop, and Canonical Catalog because those documents contain few/no direct relative links.
- Existing ADR-016 links to the time decision register and roadmap under `docs/architecture/time/`; those targets exist in the repository inventory.
- The broader repository contains historical prose references and phase-local paths that require release-specific validation; this baseline does not certify every link in all historical/evidence files.
- The AI Rules are outside this repository at `D:\1-webapp\28-AI-Rules`; portability depends on that governed workspace path. This is an external-reference dependency, not a broken local link.

### Duplicate documents

- `phase0_architecture_freeze.md` is the historical Phase 0 design freeze; this file is the platform-level v1 baseline/index. Their purposes overlap but are not duplicates.
- Current inventory, target domain model, operational gap analysis, and phase documents intentionally describe different viewpoints/times.
- Phase 1A/1B API, permission, state, migration, UAT, and evidence documents are phase-specific records, not alternate architecture baselines.
- No second Canonical Catalog, PDR, or Phase 0.5 Workshop was found.

### Missing references/index gaps

- Before this file, no single role-based architecture entry point/index connected AI Rules, Catalog, ADR, PDR, Workshop, implementation, release, and operations. This baseline fills that index gap.
- Existing primary README/System Architecture documents do not yet reference this new baseline/Catalog/PDR/Workshop because modification was prohibited. A future authorized documentation-maintenance task should add entry-point links after baseline acceptance.
- ADR-017 through ADR-020 reference related decisions mainly by prose; they do not provide a uniform Related Documents section linking PDR/Workshop/Catalog. This is an indexing gap, not a semantic contradiction, and must not be corrected by editing them without authorization.
- Proposed Product decisions have not yet been recorded as Accepted outcomes; Slice 1 therefore remains blocked as documented by the PDR/Workshop.

### Circular references

- No semantic decision cycle was identified: AI Rules govern practice; ADRs/PDRs govern decisions; Workshop facilitates closure; Catalog governs names; this Baseline indexes them.
- Future links may be bidirectional for navigation, but navigation cycles do not imply authority cycles. Source decision status and scope always control.

### Naming inconsistencies

The Canonical Catalog records the complete alias analysis. Material current inconsistencies are:

- `Shipment` used broadly where ShipmentRequest or OperationalShipment is intended.
- `Case` used for legacy ShipmentRequest/document context while Project is the new coordination boundary.
- `ShipmentTransportUnit`, `TrackingUnit`, and `OperationalUnit` versus canonical ExecutionUnit.
- `ExpertQuote`/Quote versus canonical Quotation.
- `WorkItem` and CRM Task versus canonical Task with bounded subtype.
- `File`, `Document`, and `Attachment` used without distinguishing DocumentArtifact, DocumentAttachment, and DocumentVersion.
- `attention_required` and `delayed` used as legacy aggregate/unit statuses although the proposed canonical model treats them as alerts/conditions.
- Multiple specialized audit/log terms versus canonical AuditEntry.

These are compatibility/documentation findings, not authorization to rename code, schema, API, or existing documents.

### Consistency verdict

The architecture sources are structurally consistent when document status and historical context are respected. ADR-017 through ADR-019, PDR-001 through PDR-006, and PDR-010 are Accepted; ADR-020 and the remaining PDRs retain Proposed status. Workshop outcomes, Catalog authority, and this Baseline retain their documented statuses.

## 11. Architecture Readiness Assessment

### Maturity assessment

| Dimension | Assessment | Evidence | Remaining condition |
|---|---|---|---|
| Architecture maturity | High for documented boundaries and operational foundation | Accepted ADR-001–019, Phase 0/1 contracts and evidence; Proposed ADR-020 | Reconcile remaining decisions before their affected later slices |
| Governance maturity | High structure, medium closure | AI Rules, ADR/PDR process, permission/state/test matrices, release governance | Record explicit Product/Architecture approvals and link them to implementation |
| Documentation maturity | High breadth, medium discoverability before baseline | Extensive operational docs, runbooks, evidence, Catalog, Workshop | Accept baseline and add future authorized links from README/System Architecture |
| AI readiness | High for principles/read/recommend; low-to-medium for execution authorization | AI Rules, provider/context docs, event/audit/permission foundations, Workshop boundaries | Accept action-specific policies; keep sensitive/autonomous execution disabled |
| Developer onboarding readiness | High after proposed baseline review | Role-based reading paths, repository index, checklist, vocabulary | Baseline acceptance and maintenance ownership |
| Product evolution readiness | Medium-to-high | Proposed Project/ExecutionUnit/Event/Document architecture and PDR/workshop | Accept Slice 1 blockers; preserve deferred fail-safe behavior |
| Data/migration readiness | High discipline, feature-specific readiness pending | Additive migration ADRs/runbooks/tests and prior migration evidence | Feature-specific profiling, migration design, data gates, backup/rollback rehearsal |
| Security readiness | High principles, feature-specific approval pending | Permission matrix, security rules, token/session, secret scanning, allowlist patterns | Threat model and negative tests for each new public/document/bulk/AI surface |
| Release/operations readiness | High governance, release-specific evidence required | SemVer/release manifest rules, deployment/runbooks/CI/backup plans | Per-release version consistency, manifest, tests, deployment and rollback evidence |

### Overall baseline status

The Forwarder platform has a mature documented architecture and governance system suitable for long-term evolution. Its current operational implementation and Accepted ADRs provide a strong foundation. The proposed Project, ExecutionUnit, unified event, and document architecture is internally aligned but not yet approved for implementation because the corresponding ADRs/PDRs and this baseline remain Proposed.

The platform is ready for Architecture Review and Product decision closure. It is not automatically ready for Slice 1 implementation until blocking PDRs and governing Proposed ADRs are explicitly accepted, acceptance criteria are frozen, and the Development Readiness Checklist passes.

---

Architecture Baseline Version: 1.0
Status: Proposed
Ready for Architecture Review
