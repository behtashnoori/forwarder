# RFC-001: Multi-Execution Operational Project

- RFC ID: RFC-001
- Status: Draft
- Date: 2026-07-31
- Authors: Platform Delivery
- Reviewers: Product, Architecture, Operations, Security, Data, QA
- Primary capability: CAP-001 Project Management
- Supporting capability: CAP-003 Execution Management
- Decision authority: None. This RFC is non-authoritative and does not approve Product policy, architecture, implementation, or delivery.

## 1. Problem Statement

Forwarder can manage commercial intake through `ShipmentRequest` and operational execution through `OperationalShipment`, but it does not yet provide one governed operational coordination boundary for work that contains multiple independently progressing executions.

Real logistics work may begin from one or more commercial requests, produce several OperationalShipments, and require many road, rail, sea, air, warehouse, or customs ExecutionUnits to proceed concurrently. Today, users must interpret those records through request-level and shipment-level views. They cannot reliably answer, from one coherent operational context:

- what complete customer outcome is being coordinated;
- which OperationalShipments and ExecutionUnits contribute to it;
- which parts are not started, active, arrived, delivered, cancelled, stale, delayed, or exceptional;
- which obligations remain before the overall work can be considered complete;
- which alerts, documents, reports, and operational events apply to the whole body of work or to one execution within it; and
- which customer, stakeholder, and operational organization may see or act on each part.

Using ShipmentRequest as that boundary would mix commercial and operational truth. Using OperationalShipment would assume that one shipment represents the whole customer outcome. Treating a legacy `ShipmentTransportUnit` as only a tracking row does not provide an independent execution lifecycle. A new implementation cannot safely begin by guessing the missing business policies because those policies affect ownership, authority, identifiers, completion, visibility, reporting, legacy adoption, and acceptance.

RFC-001 therefore defines the problem, expected outcome, review boundaries, and candidate delivery progression for a **Multi-Execution Operational Project**. It does not decide how the capability will be implemented.

## 2. Business Motivation

Forwarder is evolving from shipment-request and quotation management into a logistics operating platform. Customers buy and evaluate an outcome that may span several commercial requests, shipments, modes, handoffs, and operational units. The business needs a stable coordination concept above individual executions so that commercial lineage, operational progress, customer accountability, and portfolio reporting remain traceable without becoming the same lifecycle.

The capability should enable the business to:

- coordinate a customer engagement as a whole while preserving the autonomy of its executions;
- represent multimodal and multi-party work without forcing it into one oversized shipment record;
- report progress and completion from evidence rather than manual interpretation;
- retain one recognizable customer context across operational handoffs;
- scale service offerings to consolidation, deconsolidation, warehousing, customs, and partner-assisted execution; and
- establish a governed context for later reporting, document collaboration, integration, and AI assistance.

Without this capability, growth increases manual coordination cost and makes operational and customer reporting progressively less trustworthy.

## 3. Operational Motivation

Operations needs independent teams and actors to update separate executions concurrently without losing the larger operational objective. A Project-level view must summarize rather than own the detailed truth of each OperationalShipment or ExecutionUnit.

Operators need to identify remaining work, partial progress, stale updates, delays, exceptions, incomplete evidence, and ownership at the correct scope. They also need to distinguish an operational lifecycle from an alert condition: a delayed or attention-required ExecutionUnit may still be in progress, and an administratively closed Project must not falsely appear delivered.

The intended outcome is a control context that supports coordinated decisions while preserving route, milestone, verification, event, and unit-level accountability.

## 4. Customer Motivation

Customers often understand their work as one project even when Forwarder executes it through several shipments and units. They need a coherent, permission-safe view of overall progress and the ability to inspect relevant detail without navigating unrelated internal records or receiving contradictory status messages.

A successful capability should give customers:

- a stable reference for the overall body of work;
- understandable progress across multiple executions;
- clear separation between completed, remaining, cancelled, and exceptional work;
- consistent visibility across modes and handoffs; and
- protection from internal notes, restricted documents, other customers' data, and operational details they are not authorized to see.

Customer access or public tracking is not assumed by this RFC. Its identity, visibility, and authorization policies remain subject to Product and Security approval.

## 5. Current Limitations

- No canonical operational Project currently coordinates multiple OperationalShipments and ExecutionUnits.
- ShipmentRequest is the commercial intake and decision record, not an execution or project aggregate.
- OperationalShipment owns one executable shipment and its route, checkpoints, milestones, and lifecycle; it is not an adequate multi-shipment coordination boundary.
- Legacy ShipmentTransportUnit behavior is coupled to request tracking and does not provide the proposed canonical ExecutionUnit ownership, lifecycle, concurrency, event, or reporting contract.
- Status and history are distributed across request logs, OperationalShipment state, milestones, unit updates, document audit, operational audit, and customer projections.
- There is no approved Project ownership, authority, identifier, completion, or legacy grouping policy.
- There is no approved canonical ExecutionUnit code or lifecycle mapping policy.
- Operational freshness, SLA, and alert thresholds are not approved as a versioned cross-mode policy.
- Existing customer and document access cannot be generalized to Project membership.
- Large Project payloads, batch actions, and exports do not yet have approved operational limits.
- Ambiguous legacy lineage cannot be safely inferred.

## 6. Business Examples

### Example A: Consolidated road movement

One customer engagement includes several ShipmentRequests accepted at different times. Operations creates multiple OperationalShipments for separate routes, each involving several trucks or trailers. Some units are delivered while others remain in progress. The customer needs one overall progress context; each operational team must continue to manage its own route and units independently.

### Example B: Multimodal import

A customer outcome moves by sea, then road, with a warehouse handoff and customs activity. Different OperationalShipments and ExecutionUnits progress on different schedules. A late container should raise an alert without rewriting the lifecycle of unaffected units or the commercial status of the original request.

### Example C: Partial completion with cancellation

A Project contains ten active ExecutionUnits. Eight are delivered, one remains in progress, and one is cancelled with recorded reason and history. The platform must not present the Project as wholly delivered while unresolved work remains, and it must not erase the cancelled unit from the customer or operational accounting permitted by policy.

### Example D: One commercial request, multiple executions

A single accepted ShipmentRequest requires separate OperationalShipments because cargo follows different routes or schedules. Commercial lineage remains attached to the request, while each execution advances independently and contributes to the Project summary.

### Example E: Multiple commercial requests, one outcome

Several ShipmentRequests belong to one broader customer program. The Project provides the coordination context, but does not merge the requests, quotations, or their commercial histories.

### Example F: Operational exception isolated to one unit

One ExecutionUnit has stale location evidence and a missing document. The unit remains in its valid lifecycle state while separate alerts identify the risks. Other units continue without being blocked or falsely marked delayed.

These examples illustrate the problem space only. They do not approve cardinality, transition, completion, transfer, split/merge, or visibility rules.

## 7. Non Goals

RFC-001 does not:

- approve ADR-017, ADR-018, ADR-019, or ADR-020;
- accept any PDR recommendation;
- define entities, tables, fields, schemas, repositories, services, or transactional design;
- design APIs, endpoints, payloads, error contracts, or public tracking mechanics;
- design frontend screens, workflows, or interaction details;
- change the meaning or lifecycle of ShipmentRequest or OperationalShipment;
- select a Project creation, conversion, grouping, transfer, completion, or cancellation policy;
- select an ExecutionUnit type model, code allocator, lifecycle transition model, or legacy mapping;
- authorize customer/public access, document sharing, bulk actions, exports, or AI actions;
- choose event storage, projections, jobs, infrastructure, deployment, or migration mechanisms;
- introduce accounting, ERP, BPM, WMS, customs-filing, or carrier-integration systems; or
- authorize implementation.

## 8. Success Criteria

RFC-001 is successful when Architecture Review can determine that:

1. the multi-execution coordination problem and affected users are unambiguous;
2. Project, ShipmentRequest, OperationalShipment, and ExecutionUnit remain distinct canonical concepts;
3. business, operational, customer, security, data, compatibility, and governance impacts are visible;
4. all Product decisions that block a first delivery slice are explicitly identified and remain owned by their PDR approvers;
5. no implementation choice, data model, API design, or architecture change is embedded in the RFC;
6. candidate slices express independently reviewable business outcomes and safe deferral boundaries;
7. backward compatibility and fail-safe behavior are mandatory constraints; and
8. the review can produce a clear disposition: revise, reject, or advance to the required ADR/PDR decision gates.

Capability success after future approved delivery would additionally require users to coordinate multiple executions from one Project context without loss of lineage, unauthorized disclosure, false completion, or regression of existing request and OperationalShipment workflows. Metrics and target values for that outcome remain to be approved.

## 9. Scope

This RFC covers the business need for:

- a Project-level coordination and customer-context capability;
- traceable relationships to commercial ShipmentRequests and executable OperationalShipments;
- multiple independently progressing ExecutionUnits within the coordinated outcome;
- aggregated, clearly qualified progress without replacing child sources of truth;
- Project-level discovery of alerts, exceptions, events, documents, and reports while their authoritative scopes remain distinct;
- permission-aware internal and, when separately approved, customer visibility;
- legacy coexistence and adoption without guessed lineage; and
- a phased decision and delivery path governed by accepted ADRs and PDRs.

Scope describes desired capability boundaries, not an implementation boundary.

## 10. Out of Scope

- Full event sourcing or replacement of specialized milestone, audit, outbox, or tracking records.
- Document artifact/attachment implementation, customer uploads, bulk ZIP, retention, purge, legal hold, or digital-signature verification.
- ExecutionUnit split/merge execution.
- Mode-specific specialist systems or independently modeled mode lifecycles.
- Financial settlement, invoicing, payment, or accounting truth.
- ERP, BPM, carrier, partner, warehouse, or customs integrations.
- Predictive control-tower ranking or autonomous operational decisions.
- Unrestricted public Project tracking.
- Physical deletion or destructive legacy contraction.
- Performance targets, quotas, SLAs, or alert thresholds not approved by their owners.

## 11. Backward Compatibility

Backward compatibility is mandatory by default.

- Existing ShipmentRequest commercial behavior, identifiers, and history remain valid.
- Existing OperationalShipment execution behavior, identifiers, route plans, milestones, and APIs remain valid.
- Existing ShipmentTransportUnit and tracking behavior remain available until a separately approved compatibility and deprecation path completes.
- Existing case-document scope is not silently reinterpreted as Project scope.
- Legacy statuses, timestamps, customer links, unit codes, and lineage are not guessed or broadly rewritten.
- Records that cannot be linked with evidence remain unadopted or quarantined under a future approved process.
- New capability introduction must be additive, cohort-controlled, observable, reversible at the application level, and compatible with the supported N/N-1 window.
- Rollback must preserve new information for reconciliation; it must not depend on deleting Project lineage or operational evidence.

The precise compatibility contract belongs to later approved design and release work.

## 12. Dependencies

### Governance dependencies

- Platform Constitution and Architecture Baseline ratification or an explicit Architecture Review determination of their authority for this RFC.
- Canonical Business Object Catalog terminology review.
- Architecture disposition of ADR-017 and ADR-018 before implementation.
- Architecture review of ADR-019 and ADR-020 for any slice that depends on unified timelines or scoped documents.
- Product acceptance of the PDR portions that block the selected slice.

### Business and operational dependencies

- Explicit owner and stakeholder cardinality policy.
- Project authority and sensitive-action policy.
- Project identity and customer/public reference policy.
- Completion and administrative-closure semantics.
- ExecutionUnit identity and lifecycle policy.
- Approved freshness/alert policy where alerts are claimed.
- Named Product, Operations, Security, Data, QA, and Architecture acceptance owners.

### Evidence dependencies

- Representative business scenarios across road, rail, sea, air, warehouse, and customs as applicable.
- Legacy data profiling for customer linkage, request-to-shipment lineage, unit codes, statuses, types, timestamps, and ambiguous records.
- Permission and customer-visibility scenarios, including negative cross-organization cases.
- Defined reconciliation expectations for any future legacy adoption.

These dependencies are decision and evidence gates, not implementation instructions.

## 13. Related Capability

### Primary capability

- **CAP-001 — Project Management:** provides the business coordination context whose problem is defined by this RFC.

### Direct supporting capabilities

- **CAP-002 — Shipment Management:** preserves ShipmentRequest and OperationalShipment meaning and lineage.
- **CAP-003 — Execution Management:** provides independently managed ExecutionUnits contributing to Project outcomes.

### Later dependent capabilities

- CAP-004 Timeline Platform
- CAP-005 Document Platform
- CAP-006 Reporting & Analytics
- CAP-007 Customer Portal
- CAP-008 Expert Workspace
- CAP-010 Security & Identity
- CAP-011 Integration Platform
- CAP-012 Notification Platform
- CAP-014 AI Platform

Capability references establish traceability only; they do not alter registry status or authorize delivery.

## 14. Related ADR

### Direct proposed architecture

- **ADR-017 — Operational Project Architecture:** proposes the Project coordination boundary and its relationship to requests, shipments, and units.
- **ADR-018 — Execution Unit Architecture:** proposes the canonical independently stateful execution concept.
- **ADR-019 — Unified Timeline Operational Event Model:** proposes cross-scope operational history and timeline projections for later slices.
- **ADR-020 — Document Attachment and Visibility Architecture:** proposes document scoping and visibility for later slices.

### Existing accepted constraints

- **ADR-001 — Modular Monolith:** preserves bounded modules unless later evidence authorizes extraction.
- **ADR-002 — Request/Operation Separation:** prohibits using ShipmentRequest as operational execution truth.
- **ADR-003 — OperationalShipment Terminology:** preserves the canonical execution-shipment name.
- **ADR-004 and ADR-009:** preserve route, milestone, verified evidence, and correction semantics.
- **ADR-006:** requires additive, backward-compatible evolution.
- **ADR-007:** separates commercial status, operational lifecycle, and derived conditions.
- **ADR-008:** keeps work queues and alerts as actionable projections, not operational truth.
- **ADR-010:** governs future sensitive retry and concurrency behavior without being designed by this RFC.
- **ADR-016:** preserves time semantics and the distinction between occurred and recorded facts.

No ADR status is changed by this RFC.

## 15. Related PDR

### Blocking for the first canonical Project/ExecutionUnit slice

- **PDR-001:** Project customer cardinality and party roles.
- **PDR-002:** Project creation, access, close, cancel, and transfer authority, with only the relevant slice portion required.
- **PDR-003:** Project internal, resource, and public identity policy.
- **PDR-004:** completion, partial delivery, cancellation, and administrative closure.
- **PDR-005:** ExecutionUnit code uniqueness, generation, and reuse.
- **PDR-006:** shared ExecutionUnit lifecycle and legacy mapping.
- **PDR-010:** stale-update and policy-version contract for any slice claiming freshness alerts.

### Deferred unless selected by a later slice

- **PDR-007:** ExecutionUnit split/merge.
- **PDR-008:** document visibility.
- **PDR-009:** customer document operations.
- **PDR-010:** executable bulk limits, full SLA catalog, and export limits beyond the selected slice.
- **PDR-011:** retention, legal hold, purge, and digital signatures.

Governance reconciliation on 2026-07-31 Accepted PDR-001 through PDR-004 and Deferred PDR-005, PDR-006, and PDR-010. PDR-007 through PDR-009 and PDR-011 remain Proposed. Recommendations for Deferred or Proposed records do not constitute acceptance.

## 16. Open Questions

### Product

- What event establishes a Project, and may a Project exist before it has an OperationalShipment?
- What are the approved Project-to-ShipmentRequest and Project-to-OperationalShipment cardinalities?
- May a ShipmentRequest or OperationalShipment move between Projects, and under what business conditions?
- Which customer organization owns the Project, and how do payer, consignee, cargo owner, and other stakeholders relate without gaining implicit access?
- Who may create, close, cancel, reopen, or transfer a Project?
- What exactly constitutes Project completion, partial delivery, cancellation, and administrative closure?
- What customer-visible language and progress representation are acceptable?

### Operations

- Which real-world workflows require separate OperationalShipments versus separate ExecutionUnits?
- Which unit types and external references are essential for the first business outcome?
- Which freshness, delay, and escalation policies are required, by mode and service?
- What minimum Project summary allows operators to act without loading every child execution?

### Security and compliance

- What internal, customer, public, partner, and stakeholder access models are acceptable?
- Which Project actions are sensitive and require reason, approval, or segregation of duties?
- What information must never appear in customer or public projections?
- When later document/event capabilities are selected, what visibility, classification, retention, and audit controls apply?

### Data and reporting

- What evidence is sufficient to adopt legacy records into a Project?
- What is the expected volume distribution for executions per Project?
- Which progress, completion, exception, and cancellation metrics must reconcile at Project level?
- How should ambiguous, incomplete, or conflicting legacy evidence be reported?

### Architecture review

- Which proposed ADRs must be accepted for each candidate slice?
- Does the selected first outcome preserve aggregate ownership and avoid cross-aggregate transactional assumptions?
- What additional RFC, ADR, or PDR is required if review changes the proposed boundary?

## 17. Risk Analysis

| Risk | Consequence | Required response before affected delivery |
|---|---|---|
| Project becomes a God aggregate | Concurrency bottlenecks, mixed lifecycles, fragile changes | Preserve independent source-of-truth boundaries through Architecture approval |
| Customer or party ownership is ambiguous | Cross-customer exposure or incorrect portfolio reporting | Accept PDR-001 and prove organization/resource scoping |
| Request, shipment, project, and unit terminology drifts | Incorrect behavior, reporting, and user expectations | Enforce Canonical Catalog review in all later artifacts |
| Completion policy is guessed | False delivery claims and operational obligations hidden | Accept PDR-004 with deterministic business examples |
| Legacy lineage is inferred incorrectly | Wrong Project membership and corrupted reporting | Require evidence-based adoption and quarantine ambiguity |
| ExecutionUnit lifecycle is overloaded with alerts | Incomparable states and false aggregation | Accept PDR-006 and keep lifecycle, alerts, and exceptions distinct |
| Project summaries drift from child truth | Conflicting screens and customer distrust | Require one governed derivation and reconciliation acceptance criteria |
| Unbounded child loading or bulk work | Poor performance and denial-of-service exposure | Approve scale assumptions and bounded behavior before the relevant slice |
| Project membership broadens visibility | Internal event or document leakage | Deny by default and review each subject/attachment authorization policy |
| Concurrent updates overwrite each other | Lost operational evidence | Preserve ADR-010 constraints in later designs |
| Rollout breaks legacy workflows | Operational disruption and unsafe rollback | Require additive compatibility, cohorts, observation, and fallback |
| Proposed decisions are treated as accepted | Unauthorized business or architecture change | Record explicit ADR/PDR status at every delivery gate |
| AI acts on incomplete or unauthorized context | Unsafe recommendation or mutation | Keep AI read/recommend only until action-specific policy is accepted |

## 18. Alternative Solutions

### A. Continue coordinating through ShipmentRequest

This minimizes conceptual change but is not recommended. It mixes commercial intake with operational execution, conflicts with ADR-002, and cannot cleanly represent several executions or independent lifecycles.

### B. Treat OperationalShipment as the whole Project

This works only when one customer outcome always equals one executable shipment. It does not cover multiple routes, schedules, or shipments and would overload the OperationalShipment aggregate.

### C. Treat each ExecutionUnit as an OperationalShipment

This provides independent concurrency but duplicates shipment route and commercial context, makes coordinated reporting harder, and loses the distinction between a shipment and a unit executing within it.

### D. Build only a reporting/dashboard projection over current records

A read-only coordination view could provide short-term visibility and may be a useful validation step. Alone, it cannot establish approved identity, ownership, membership, authority, lifecycle, or durable customer context. It is insufficient as the long-term capability.

### E. Use a generic case/workflow record

A generic container may appear flexible but would weaken canonical vocabulary and allow Project, commercial request, operational shipment, task, and document case meanings to collapse into one ambiguous concept.

### F. Use an external BPM, ERP, or microservice as the owner

External orchestration may later coordinate approved actions, but adopting it now would not resolve the domain decisions and would conflict with the current modular-monolith and source-of-truth principles absent a superseding ADR.

### G. Continue manual coordination outside the platform

Spreadsheets and messaging can bridge small volumes, but they fragment evidence, weaken authorization and audit, and do not produce reliable customer or operational truth.

## 19. Recommended Direction

Advance the **Multi-Execution Operational Project** as a governed capability proposal based on the following direction:

- use Project as the canonical coordination concept;
- preserve ShipmentRequest as commercial truth;
- preserve OperationalShipment as executable shipment truth;
- recognize the need for independently progressing ExecutionUnits;
- derive Project-level understanding from child evidence without overwriting child state;
- treat alerts, exceptions, timelines, documents, and work queues as distinct governed concerns;
- preserve existing behavior through additive adoption and explicit compatibility; and
- close the applicable ADR and PDR decisions before authorizing any implementation slice.

This is a recommendation to continue governance and discovery, not acceptance of the detailed architecture proposed by ADR-017/018 and not an implementation decision. Architecture Review may revise or reject it.

## 20. Phased Rollout

The following phases are governance and outcome gates. Their sequence is recommended for review and may be changed only through the applicable decision process.

### Phase 0 — Decision closure and evidence

Confirm business examples, volume assumptions, legacy data evidence, ownership, authority, identifiers, lifecycle, completion, permissions, and acceptance owners. Record explicit dispositions for the applicable ADRs and PDRs. No capability implementation is authorized by completing this phase.

### Phase 1 — Internal read-only validation

Validate whether an internal, non-authoritative Project-oriented view can correctly explain existing request, shipment, and unit relationships for a bounded cohort. It must be labeled provisional, grant no new access, create no canonical lineage by inference, and make no canonical completion claim while policies remain unresolved.

### Phase 2 — Governed internal coordination

Candidate outcome: authorized staff can coordinate an approved Project scope and inspect independently progressing executions using accepted rules. Entry requires accepted blocking decisions, approved design, compatibility plan, security review, tests, and rollback evidence.

### Phase 3 — Customer-safe visibility

Candidate outcome: authenticated customers can see an explicitly allowlisted Project summary and drill into authorized detail. Entry requires approved customer identity, visibility, non-enumeration, disclosure, and negative security tests. Public tracking remains separate and disabled unless specifically approved.

### Phase 4 — Extended operational capabilities

Candidate outcomes may include unified timeline, scoped documents, reports, bounded bulk work, and control-tower workflows. Each requires its own accepted ADR/PDR dependencies and may proceed independently where boundaries allow.

### Phase 5 — Integration and governed AI assistance

Candidate outcome: approved external integrations and AI assistants consume permission-filtered Project context and prepare evidence-backed actions. Execution remains subject to action-specific policy, human approval boundaries, idempotency, authorization, and audit.

At every phase, rollback means disabling the new capability path and preserving evidence for reconciliation, not destructive deletion.

## 21. Slice Candidates

These candidates describe reviewable business outcomes. They are not a committed sequence, technical design, or authorization to build.

### Slice Candidate 1 — Project context validation

An internal read-only cohort demonstrates whether known ShipmentRequests, OperationalShipments, and legacy units can be represented as one coherent candidate Project context using only proven lineage. Ambiguous records remain explicitly unresolved. No mutation, customer exposure, or canonical completion claim is included.

### Slice Candidate 2 — Canonical Project coordination foundation

Authorized internal users coordinate a bounded Project with explicitly approved ownership, membership, identity, authority, and progress semantics. This candidate is blocked by ADR-017/018 disposition and PDR-001 through PDR-006, plus the relevant PDR-010 portion.

### Slice Candidate 3 — Independent execution visibility

Operators inspect and filter multiple independently progressing ExecutionUnits and see clearly qualified lifecycle, latest evidence, and alerts without changing their state through the Project summary. Any mutation or batch action is separately scoped and governed.

### Slice Candidate 4 — Customer Project visibility

An authenticated customer sees a minimal allowlisted Project progress view for an approved cohort. No document access, partner access, public tracking, or internal-note exposure is implied.

### Slice Candidate 5 — Project timeline

Authorized users inspect a permission-filtered, paginated operational history spanning approved Project, OperationalShipment, ExecutionUnit, and later document scopes. This candidate requires ADR-019 acceptance and event visibility/retention decisions appropriate to its audience.

### Slice Candidate 6 — Project documents and reporting

Authorized users discover scoped documents and request bounded reports without Project membership broadening document access. This candidate requires ADR-020 and the applicable PDR-008 through PDR-011 decisions.

### Slice Candidate 7 — Controlled operational assistance

Operators receive evidence-backed recommendations or prepared actions across multiple executions. Human approval and existing domain-command authority remain controlling; autonomous execution is out of scope unless separately approved.

## 22. Acceptance Criteria

### RFC acceptance for Architecture Review

- [ ] The RFC describes a business problem rather than an implementation solution.
- [ ] All required sections are complete.
- [ ] Project, ShipmentRequest, OperationalShipment, and ExecutionUnit are used consistently and are not aliases.
- [ ] Current limitations and business examples demonstrate a genuine multi-execution need.
- [ ] Business, operational, and customer motivations are independently stated.
- [ ] Scope, out-of-scope, and non-goals prevent architecture, entity, API, or implementation decisions from being inferred.
- [x] ADR-017 is Accepted for SLICE-001; ADR-018 through ADR-020 remain explicitly Proposed and unchanged.
- [x] PDR-001 through PDR-004 are Accepted; PDR-005, PDR-006, and PDR-010 are Deferred; all other PDR entries remain Proposed.
- [x] SLICE-001 decision dispositions are traceable and no Deferred or Proposed recommendation is treated as approval.
- [ ] Backward compatibility, fail-safe behavior, and ambiguous-data quarantine are explicit constraints.
- [ ] Risks and alternatives include request-as-project, shipment-as-project, reporting-only, generic-case, external-orchestrator, and manual-coordination options.
- [ ] Recommended direction is suitable for review without authorizing implementation.
- [ ] Rollout phases and slice candidates are outcome-level proposals with explicit entry gates.
- [ ] Product, Architecture, Operations, Security, Data, and QA reviewers can identify their open decisions and evidence obligations.

### Preconditions before any future implementation authorization

- [ ] Architecture records a disposition for the ADRs required by the selected slice.
- [ ] Required PDR owners and approvers record explicit acceptance or rejection.
- [ ] Canonical vocabulary review passes.
- [ ] Representative business scenarios and data profiles support the selected scope.
- [ ] Authorization, organization/resource scope, customer visibility, and negative leakage criteria are approved.
- [ ] Compatibility, rollout, fallback, reconciliation, and release acceptance criteria are approved.
- [ ] The selected slice has a separate implementation design; this RFC is not used as that design.

---

Status:
Draft

Ready for Architecture Review
