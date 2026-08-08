# OIP-1 — Operational Intelligence Architecture & Contract Slice

**Status:** Proposed for human approval  
**Date:** 2026-08-07  
**Scope:** Architecture, contracts, examples, and acceptance scenarios only  
**Authority boundary:** OIP is derived, explainable, reversible intelligence. Operational truth remains in its owning domain.

## Evidence baseline and notation

This contract revalidates the current repository rather than assuming a blank platform. Primary evidence is `backend/operational_models.py`, `backend/mdpm_models.py`, the corresponding operational/MDPM services and tests, `docs/operational/FDD-001-forwarder-data-dictionary.md`, `docs/operational/phase1b_multileg_route_orchestration.md`, `docs/operational/mdpm-1-document-readiness-slice-contract.md`, ADR-019, ADR-029, ADR-030, and the AI-READY-1/2/3 contracts. Legacy Task, Activity, Message, and Notification evidence is in `backend/models.py` and their services.

Contract keywords are **MUST**, **MUST NOT**, **SHOULD**, and **MAY**. Public IDs are opaque. A “version identity” may be a native source version, immutable event ID, or a documented source fingerprint; it is not necessarily an integer.

## 1. Executive OIP-1 Summary

The authoritative flow is:

`FactReference → Signal → Situation → AttentionItem → DecisionContext → Recommendation → Existing Authorized Action → Outcome`

Each concept stays separate:

| Concept | Owns | Does not own |
|---|---|---|
| FactReference | immutable pointer and observed source identity | copied domain truth |
| Signal | deterministic derivation result | attention lifecycle |
| Situation | durable intelligence identity and attention lifecycle | shipment, milestone, readiness, delay, exception, or action truth |
| AttentionItem | work-queue projection | independent status or identity |
| DecisionContext | immutable, version-bound read projection | write authority |
| Recommendation | advisory proposal and human disposition | domain mutation or approval |
| Action reference | link to an already-authorized command | generic action engine |
| Outcome observation | measured facts and qualified interpretation | unsupported causality |

OIP-0's fit verdict remains valid, with material refinements now confirmed in the repository:

- `OperationalEvent` is an append-only ExecutionUnit evidence envelope with public ID, occurred/recorded time, correlation, supersession, visibility, and optional threshold-policy version.
- `MilestoneEvent` is specialized append-only milestone history with correction/supersession and verification semantics; it is not interchangeable with `OperationalEvent`.
- `OperationalDelay` and `OperationalException` are now explicit tenant-bound operational truth with active state represented by absent `resolved_at`.
- `OperationalWorkItem` supports four deterministic work types, partial open uniqueness, automatic/manual/supersession resolution, reopen through reconciliation, occurrence count, audit, and outbox. It is a strong compatibility projection but a poor universal Situation aggregate.
- MDPM has versioned operational requirements, artifact associations, append-only assessments/audit, transition overrides, and deterministic readiness. OIP may read its results but never recalculate or change readiness.
- Task and Activity remain legacy CRM models without an explicit operational organization key. Expert-console Message and Notification are shipment-request scoped and similarly lack the canonical OIP tenant envelope.
- `OperationalAudit` and `OperationalOutbox` are specialized command/integration records, not business facts or a universal event store.
- AI remains advisory-only, disabled-by-default capable, write/send prohibited at generation, evidence-bound, version-bound, and subject to explicit human review. OIP-1 detection and ranking require no AI.

No implementation is authorized by this document.

## 2. Fact Reference Contract

### 2.1 Technology-neutral shape

| Field | Cardinality | Contract |
|---|---:|---|
| `source_domain` | 1 | Governed domain code, e.g. `OPERATIONAL_EXECUTION`, `MDPM` |
| `source_type` | 1 | Canonical source aggregate/event/read-result type |
| `source_public_id` | 1 | Opaque public identity; adapter identity only where admitted |
| `subject_type` | 1 | OIP subject type: shipment, milestone, checkpoint, route plan, execution unit |
| `subject_public_id` | 1 | Opaque canonical subject identity |
| `organization_id` | 1 | Canonical tenant resolved server-side |
| `occurred_at` | 1 | Business-effective time; for current-state facts, the state’s effective/change time |
| `recorded_at` | 0..1 | Source persistence/observation time |
| `source_version` | 1 | Native version, immutable event public ID, or named fingerprint scheme |
| `correlation_id` | 0..1 | Existing correlation identity if supplied by source |
| `evidence_reference` | 1..n | Authorized locator plus evidence kind; never an unrestricted URL or copied sensitive body |
| `validity` | 1 | `CURRENT`, `SUPERSEDED`, `MISSING`, `INACCESSIBLE`, or `UNKNOWN` |
| `resolved_at` | 1 | When OIP resolved this reference during the projection |

`source_domain + source_type + source_public_id + source_version` identifies a fact version. `organization_id` is an invariant, not an identity shortcut. A mutable aggregate version and each immutable event are distinct fact versions.

### 2.2 Rules

- OIP MUST resolve the tenant from the source’s trusted relationship; client-supplied tenant data is not authoritative. The subject and source MUST resolve to the same organization.
- A FactReference is immutable after emission. Corrections create references to corrected and superseding versions; they do not edit the old reference.
- OIP MUST evaluate current truth from the source’s correction/supersession rules. It MAY retain old references as derivation history but MUST label them superseded.
- If a referenced source disappears, becomes inaccessible, or cannot be tenant-validated, dependent intelligence becomes `SOURCE_UNAVAILABLE` or stale. OIP MUST NOT silently substitute cached truth.
- Missing required facts yield no positive Signal. They may appear as `missing_information` in DecisionContext. Absence becomes a Signal only where the owning domain explicitly defines absence as authoritative state.
- Source staleness is evaluated against source-specific freshness policy. A stale source may preserve a historical Situation while preventing a “current” assertion.
- Evidence access is re-authorized at read time. A reference does not grant visibility.
- Adapters MUST publish their identity, tenant-resolution, correction, and version rules before admission.

## 3. Initial Signal Catalog

Only the following seven Signal types are admitted to MVP. Signal instances have opaque ID, catalog ID, policy version, organization, subject, `observed_at`, `active`, severity inputs, source FactReferences, evidence references, and deterministic dedup key.

### SIG-OIP-001 — Next milestone overdue

- **Meaning/subject:** the next actionable milestone of an OperationalShipment is incomplete after its authoritative effective due time and allowed tolerance; subject is shipment, dimensioned by milestone.
- **Sources:** active shipment/plan, ordered milestone, lifecycle/verification, planned/projected time, relevant MilestoneEvents.
- **Derivation:** select the next non-terminal applicable milestone under execution policy; compare evaluation time with the authoritative effective time plus governed tolerance; never infer ordering when sequence/plan applicability is unresolved.
- **Threshold/severity inputs:** overdue tolerance; elapsed overdue; milestone blocked state; active delay/exception; authoritative service criticality if present.
- **Dedup:** organization + shipment public ID + `NEXT_MILESTONE_OVERDUE` + milestone public ID + policy major identity.
- **Clear/reopen:** clears when milestone is no longer overdue/next/applicable or source plan is superseded; reopens if the same identity becomes true after resolution. A different next milestone is new.
- **Evidence:** milestone state/time/version, active plan/version, event references, evaluation time/policy.
- **Limitations:** no invented promised-delivery SLA; projected-versus-planned precedence requires human-approved policy.

### SIG-OIP-002 — Checkpoint overdue

- **Meaning/subject:** an active-plan checkpoint has not reached its required arrival/departure state by its effective due time; subject is checkpoint.
- **Sources:** active RoutePlan, OperationalCheckpoint planned/projected/actual times, status, verification, timeline reconciliation evidence.
- **Derivation:** existing route-exception reconciliation semantics, separated by due dimension where policy requires.
- **Threshold/severity inputs:** overdue tolerance, elapsed overdue, checkpoint type, downstream blocking, active exception.
- **Dedup:** organization + checkpoint stable public/adapter identity + due dimension + policy major identity. Until checkpoint public identity is available, the admitted adapter uses active route-plan public identity + checkpoint ID and marks portability limitation.
- **Clear/reopen:** clears on required actual/state, cancellation, or plan supersession; reopens if the same active-plan condition returns.
- **Evidence/limits:** effective timeline and state/version; current checkpoints lack native public IDs, requiring a governed adapter.

### SIG-OIP-003 — Route dependency blocked

- **Meaning/subject:** a successor checkpoint cannot progress because an explicit active-plan dependency is unsatisfied; subject is successor checkpoint, dimensioned by dependency edge.
- **Sources:** active RoutePlan, RouteDependency, predecessor/successor checkpoint states and actuals.
- **Derivation:** evaluate only explicit graph edges using current domain dependency semantics; no inferred causal edges.
- **Threshold/severity inputs:** operational blocking, number of unsatisfied explicit edges, elapsed block, downstream due pressure.
- **Dedup:** organization + active plan + successor checkpoint + dependency type + predecessor checkpoint + policy major identity.
- **Clear/reopen:** clears when edge is satisfied, removed through supersession, or successor becomes terminal; reopens if the same edge blocks again.
- **Evidence/limits:** edge and endpoint versions/states. Multiple edges may roll up to one Situation only under the identity rules below.

### SIG-OIP-004 — Replan required

- **Meaning/subject:** the existing deterministic route policy says an active-plan checkpoint condition requires replan consideration; subject is route plan/shipment, dimensioned by triggering checkpoint.
- **Sources:** active RoutePlan, checkpoint effective timeline/state, existing reconciliation result/work item.
- **Derivation:** reuse the current local 24-hour reconciliation rule as a versioned local policy; OIP does not reinterpret it as enterprise authority.
- **Threshold/severity inputs:** local replan threshold, elapsed over threshold, blocking scope, active exception.
- **Dedup:** organization + active route-plan identity + trigger checkpoint + `REPLAN_REQUIRED` + policy identity.
- **Clear/reopen:** clears when existing domain reconciliation clears it, plan is superseded, or triggering condition ends; recurrence after clear reopens only for the same plan/checkpoint identity.
- **Evidence/limits:** work-item/reconciliation and source graph evidence. The current numeric threshold is local, not approved OIP policy.

### SIG-OIP-005 — Next transition blocked by required documents

- **Meaning/subject:** MDPM says the next attempted/eligible milestone transition is blocked by required-document readiness; subject is milestone/shipment, dimensioned by transition target and requirement set.
- **Sources:** MDPM readiness result, active operational requirements, current associations/artifact versions, latest assessment decisions, active overrides, milestone version.
- **Derivation:** consume the authoritative MDPM readiness decision and blocker codes; OIP MUST NOT independently assess documents.
- **Threshold/severity inputs:** no time threshold required; number of required blocking dimensions, transition due pressure, active exception. Document count alone is not severity.
- **Dedup:** organization + shipment + milestone + target status + readiness policy version. Requirement changes are material evidence changes, not automatically new Situations.
- **Clear/reopen:** clears when MDPM reports ready, transition becomes inapplicable/terminal, or a valid override is consumed under MDPM rules; reopens if the same transition is blocked again.
- **Evidence/limits:** readiness snapshot/fingerprint, blocking requirement/artifact/assessment references. Unresolved applicability must remain explicit.

### SIG-OIP-006 — Active delay or exception

- **Meaning/subject:** an authoritative OperationalDelay or OperationalException is active; subject is shipment or linked milestone.
- **Sources:** the Delay/Exception aggregate, governed reason, versions, started/occurred/resolved timestamps.
- **Derivation:** `resolved_at` absent and source is tenant-valid; Delay and Exception remain distinct signal dimensions.
- **Threshold/severity inputs:** source class/reason, duration, milestone blocking, repetition; no severity inferred from free-text note.
- **Dedup:** organization + source type + source public ID + policy identity.
- **Clear/reopen:** clears when the source resolves. If the same aggregate could validly become active again, reopen; otherwise a new source public ID is a new Situation.
- **Evidence/limits:** source and reason references. Financial/compliance/customer impact cannot be inferred from reason text.

### SIG-OIP-007 — Active ExecutionUnit stale

- **Meaning/subject:** an active, non-terminal ExecutionUnit has no sufficiently recent authoritative operational observation; subject is ExecutionUnit.
- **Sources:** ExecutionUnit lifecycle/is_active/last_event_at/version and latest OperationalEvent occurred/recorded identity.
- **Derivation:** compare the policy-selected freshness anchor to evaluation time. Clock, late-arrival, and occurred-versus-recorded rules are policy inputs.
- **Threshold/severity inputs:** stale-unit threshold, elapsed staleness, lifecycle, attention/delayed authoritative flags, blocked shipment context.
- **Dedup:** organization derived through Project + unit public ID + `EXECUTION_UNIT_STALE` + policy major identity.
- **Clear/reopen:** clears on a qualifying new event, terminal/inactive unit, or correction invalidating the stale calculation; reopens if the same unit later crosses the threshold again.
- **Evidence/limits:** unit/version and latest-event reference. No current authoritative stale threshold exists; Signal must remain disabled until approved.

## 4. Threshold Model

| Threshold/input | Classification | Evidence and governance consequence |
|---|---|---|
| checkpoint/replan 24-hour rule | EXISTING BUT LOCAL | Implemented in route reconciliation; may be adapted only with explicit local policy identity, pending human ratification |
| milestone/checkpoint effective projected timeline | EXISTING AUTHORITATIVE | Domain reconciliation owns calculated times; OIP reads them |
| MDPM required assessment level/applicability/transition policy | EXISTING AUTHORITATIVE | Versioned MDPM/project requirement and ADR-030 policy |
| active Delay/Exception (`resolved_at` absent) | NOT REQUIRED | State predicate, not a threshold |
| active/non-terminal ExecutionUnit predicate | NOT REQUIRED | State predicate; freshness still requires a threshold |
| overdue tolerance | NEW HUMAN POLICY REQUIRED | No general authoritative tolerance found; zero is not assumed |
| stale-unit threshold | NEW HUMAN POLICY REQUIRED | No authoritative duration found |
| repetition window | NEW HUMAN POLICY REQUIRED | Needed only if repetition influences priority/metrics |
| escalation age | NEW HUMAN POLICY REQUIRED | Needed before escalation or aging bands are enabled |
| projection freshness maximum | NEW HUMAN POLICY REQUIRED | Must be source class specific |
| acknowledgement aging | NEW HUMAN POLICY REQUIRED | Needed only if it affects urgency |
| customer/service criticality | NOT REQUIRED | Ranking input only if a future authoritative classification exists |
| financial/compliance exposure thresholds | NOT REQUIRED | Excluded from MVP |

Threshold policies MUST have owner, scope, semantic version, effective interval, clock/time-zone rule, comparison boundary, missing-input behavior, and change approval. No number is supplied by OIP-1.

## 5. Situation Model

### 5.1 Canonical contract

| Field | Contract |
|---|---|
| `public_id` | stable opaque identity, never derived from display data |
| `organization_id` | mandatory tenant invariant |
| `subject` | type + public identity + optional admitted adapter identity |
| `situation_type` | catalog-governed type |
| `identity_dimensions` | canonical, non-sensitive dimensions used for dedup |
| `status` | lifecycle below |
| `severity` | condition magnitude class plus explanation |
| `urgency` | time-pressure class plus explanation |
| `priority` | queue ordering class plus explanation |
| `first_detected_at` | first active evaluation for this identity |
| `last_changed_at` | last material Situation change, not every evaluation |
| `last_observed_at` | most recent successful evaluation |
| `due_at` | authoritative exposure/due time when applicable; nullable |
| `owner_queue` / `assignee` | derived queue reference and optional user; `UNASSIGNED` valid |
| `signal_references` | current causal signals plus historical occurrence linkage |
| `evidence_references` | current evidence set |
| `occurrence_count` | count of inactive→active episodes, starting at one |
| `policy_version` / `projection_version` | reproducibility identities |
| `resolution` | reason, source, actor/reference, and time; does not assert recovery |
| `reopen_history` | append-only prior resolution and reopen entries |
| `freshness` | source checkpoint, projected-at, freshness status and reason |
| `superseded_by` | optional Situation reference |

### 5.2 Lifecycle

OIP-1 needs `OPEN`, `ACKNOWLEDGED`, `IN_PROGRESS`, `SNOOZED`, `RESOLVED`, and `DISMISSED`.

- `OPEN` means active and not acknowledged.
- `ACKNOWLEDGED` proves a human saw/claimed attention; it does not prove action.
- `IN_PROGRESS` is required only when an authorized action/task link or explicit human mark shows work began.
- `SNOOZED` suppresses queue prominence until a bounded time while condition evaluation continues; reason, actor, and expiry are mandatory.
- `RESOLVED` means the deterministic condition cleared or the governing source was superseded. It does not mean operational recovery.
- `DISMISSED` is a human disposition with reason while preserving the Signal; a persisting condition may return to OPEN under reopen policy.

`EXPIRED` is not an initial general lifecycle state. Expiration is type-specific resolution reason (`NO_LONGER_APPLICABLE` or policy expiry) unless humans later approve distinct reporting semantics. Plan/source supersession is a resolution reason and linkage, not a user workflow state.

Creation occurs on first active Signal for an identity. Dedup updates the same Situation. A material change is a severity/urgency/priority class change, lifecycle/ownership change, due-time change, causal signal membership change, source validity/freshness change, or evidence change that alters the explanation/available decision. Routine `last_observed_at` updates are not material.

Resolution is automatic only when deterministic clear or authoritative supersession is observed. Human dismissal never changes source truth. Reopen appends history, increments occurrence count, clears stale resolution fields, and recomputes rank. Supersession links old to new and prevents evidence from crossing plan/tenant boundaries.

## 6. Situation Identity / Deduplication Model

Canonical identity key:

`organization + subject identity + situation_type + required dimensions + policy identity class`

Policy identity is the **major semantic identity**, not every patch version. A policy correction that preserves the meaning updates the Situation; a policy change that changes the population/meaning supersedes it and creates a new Situation.

| Type | Required dimensions |
|---|---|
| next milestone overdue | shipment + milestone |
| checkpoint overdue | checkpoint + arrival/departure dimension |
| route dependency blocked | active plan + successor + predecessor + dependency type |
| replan required | active plan + triggering checkpoint |
| documents block transition | milestone + target status |
| active delay/exception | source type + source public ID |
| ExecutionUnit stale | unit public ID |

Classification rules:

- **Same Situation:** condition never cleared; repeated evaluation, evidence refresh, increasing elapsed time, assignee/rank change, or blocker-set membership change within the same semantic identity.
- **Reopened Situation:** the same semantic identity was RESOLVED/DISMISSED and becomes active again within its retained identity horizon; occurrence count increments. Snooze expiry while still active is a lifecycle return, not recurrence.
- **New Situation:** different tenant, subject, situation type, required identity dimension, non-compatible policy meaning, newly created Delay/Exception aggregate, or successor plan whose identity is distinct.
- A superseded route plan never shares an actionable Situation with its replacement. The old Situation resolves as superseded; a target-plan condition is new, with correlation linkage.
- Concurrency requires one effective identity owner and atomic upsert/compare semantics in OIP-2; this is a contract, not a schema prescription.

## 7. Severity / Urgency / Priority Model

The three axes are distinct:

- **Severity** describes the operational condition’s magnitude from authoritative inputs: `INFO`, `WARNING`, `MAJOR`, `CRITICAL`, or `UNKNOWN`.
- **Urgency** describes time pressure: `NONE`, `WATCH`, `DUE_SOON`, `OVERDUE`, `IMMEDIATE`, or `UNKNOWN`.
- **Priority** is the deterministic queue band: `P0`, `P1`, `P2`, `P3`, or `UNRANKED`.

OIP-1 defines no arbitrary weights. Ranking is a versioned lexicographic decision table approved by humans. Candidate ordered factors are: authoritative hard-blocking state; severity class; urgency class; authoritative service criticality; active exception; number of independent blocking dimensions; recurrence within an approved window; age without acknowledgement; then deterministic tie-breakers.

Rules:

1. Unknown inputs never default upward or downward; they appear in the explanation and may yield `UNRANKED`.
2. “Everything red” is prohibited: CRITICAL/P0 require an approved predicate, not merely elapsed time.
3. Free text, customer name, cargo value, or AI output cannot influence rank.
4. Manual intervention count may influence priority only when an authoritative, consistently recorded fact exists; current data is insufficient.
5. Priority explanation contains policy version, final band, ordered decisive factors, ignored/missing factors, and tie-break values.
6. Within a band, sort by urgency boundary/time-to-due, severity, unacknowledged age, first detection, subject public ID, Situation public ID. Null due times sort after known equivalent urgency; opaque IDs ensure stable ordering.

The exact decision table and critical predicates require human approval before OIP-2.

## 8. Ownership Model

- **Owner queue/team** is the accountable operational queue derived from an approved mapping and authoritative source responsibility.
- **Situation owner** is the queue, not necessarily a person.
- **Assignee** is the current human responsible for attention handling; null is represented as `UNASSIGNED`.

Current evidence is only partially sufficient. OperationalMembership supplies organization permissions; WorkItem has nullable assignee; Checkpoint has free-text `responsible_party`; ShipmentRequest has `assigned_to`. These do not form an approved, canonical organization-to-queue mapping. Therefore OIP-1 MUST allow `UNASSIGNED`; it MUST NOT parse free text or infer owner from the last actor.

Commands and permissions:

| Operation | Effect | Minimum authorization |
|---|---|---|
| assign | authorized dispatcher sets eligible assignee | tenant visibility + situation assignment capability |
| reassign | changes assignee with reason/audit | assignment capability; source owner mapping unchanged |
| claim | eligible member atomically assigns self if unassigned | queue membership + claim capability |
| acknowledge | records actor/time/version seen | situation visibility + acknowledge capability; assignment not implied unless combined explicitly |

Every command is tenant-bound, version-aware, attributable, and audited. OIP permissions do not grant permissions to domain actions.

## 9. AttentionItem / WorkQueue Model

**Decision: B — introduce Situation and retain/evolve OperationalWorkItem as its compatible queue projection.**

Why: OperationalWorkItem already provides deployed queue compatibility, deterministic uniqueness, occurrence/reopen behavior, resolution, assignee, audit, and outbox. But its four constrained types, internal numeric identity, two-state lifecycle, shipment requirement, and milestone/checkpoint-specific ownership make it unsuitable as the universal durable Situation. Replacement would break compatibility; extending it into both truth and projection would merge concepts.

AttentionItem is a replaceable read projection keyed by Situation public ID. Initially, existing work items may be adapted as legacy AttentionItems while OIP Situations cover all seven types. The projection MUST NOT accept independent lifecycle mutations; commands target Situation or an existing WorkItem command and reconcile deterministically.

| Field | Meaning |
|---|---|
| subject | safe display reference and canonical public identity |
| situation | public ID, type, status, occurrence count |
| priority | band plus explanation reference |
| owner | queue and assignee or UNASSIGNED |
| age | derived from first detection; never stored as truth |
| due/exposure | authoritative due time and bounded risk statement; no financial inference |
| reason | deterministic human-readable explanation |
| evidence | authorized FactReferences |
| next recommended decision | optional advisory recommendation reference |
| available actions | permission-filtered existing command targets |
| status | Situation lifecycle projection |
| freshness | current/stale/failed and projected-at |

## 10. DecisionContext Contract

DecisionContext is an immutable, access-controlled snapshot identified by opaque ID and `created_at`. It includes:

- Situation identity/version, lifecycle, rank explanations, owner, and freshness;
- current resolved FactReferences and source validity;
- authoritative MDPM readiness result and policy/fingerprint, never an OIP recalculation;
- active explicit blockers and their source identities;
- bounded timeline summary with occurred/recorded distinction;
- evidence references and access classifications;
- viewer permissions and action-specific authorization results evaluated at creation;
- available existing command targets with target version/preconditions;
- missing, inaccessible, contradictory, and stale information;
- source versions/fingerprints, Signal policy, projection version, and context fingerprint;
- expiry/staleness predicate.

It grants no write authority. Before any action, the owning command boundary re-authenticates, re-authorizes, reloads source state, and validates expected versions. Human and future AI receive the same versioned facts, but sensitive evidence is filtered per principal.

## 11. Recommendation Contract

Minimum immutable recommendation version:

`public_id`, `version`, `organization_id`, `situation_public_id`, `decision_context_id/fingerprint`, `recommendation_type`, structured `proposed_action` or decision option, `reason`, evidence references, `basis` (policy/human/AI identity), calibrated `confidence` or `NOT_APPLICABLE`, `missing_information`, permission-filtered command targets, `created_by`, `created_at`, expiry predicate, and human disposition.

Lifecycle is deliberately small: `PROPOSED → ACCEPTED | REJECTED | EDITED | NO_ACTION | EXPIRED | SUPERSEDED`. `EDITED` creates a new human-authored version linked to the generated version; it does not overwrite provenance. Acceptance is not execution. Disposition records actor, time, exact version, reason where required, and optional resulting action reference. A stale/expired context cannot be accepted without regeneration/review.

Deterministic recommendations are permitted; AI is not required. Confidence means declared basis/calibration, never permission. No Decision Engine is introduced.

## 12. Existing Action Mapping

| Situation | Existing authorized boundary | Task/Activity/Notification | WorkItem handling | True gap |
|---|---|---|---|---|
| next milestone overdue | report/correct/verify or governed milestone transition where state permits | legacy objects only through admitted adapter; notification optional existing capability | current overdue item auto-resolves on verification | no universal situation acknowledgement/assignment yet |
| checkpoint overdue | existing checkpoint arrival/departure reporting and reconciliation | same limitation | existing route item automatic/manual resolution | action catalog must expose exact permitted checkpoint command |
| dependency blocked | satisfy predecessor via its existing command; no direct “unblock” mutation | optional notification/task after tenant-safe adapter | existing item reconciles | no generic direct action; correctly remains contextual |
| replan required | existing authorized route replan command | Activity may record follow-up only if separately authorized | source-plan item resolves on supersession | recommendation-to-replan review link |
| documents block transition | upload/associate document, record assessment, authorized override/transition commands under MDPM | existing notification possible; legacy safety applies | no current WorkItem type | Situation/Attention projection; no new document action needed |
| active delay/exception | existing resolve Delay/Exception commands when condition truly resolved; milestone commands as applicable | optional follow-up | no current WorkItem type | queue projection and action catalog mapping |
| ExecutionUnit stale | existing create OperationalEvent/update through governed unit command | optional notification/task | no current WorkItem type | approved freshness policy; exact “request update” communication may be absent |

Completing a Task/Activity/Notification never resolves a Situation unless the deterministic source condition clears. “No current action” is valid; OIP must not manufacture one.

## 13. Outcome Contract

Outcome is an observation envelope, not a causal claim:

`outcome_id`, organization, Situation/occurrence, outcome_type, observed_at, source FactReferences, related recommendation/action references, measurement basis/version, confidence qualifier, and correlation IDs.

Types distinguish:

- `SITUATION_RESOLVED`: deterministic condition cleared;
- `OPERATIONAL_RECOVERED`: authoritative operational target/state recovered under an approved definition;
- `ACTION_COMPLETED`: owning action boundary reports completion;
- `RECOMMENDATION_DISPOSITIONED`: accepted/rejected/edited/no-action;
- `REPEATED`: same identity reopened within governed recurrence rules;
- `EXPIRED`, `DISMISSED`, `IGNORED_NO_ACTION`, and `ESCALATED` as qualified attention outcomes.

These events can coexist and must not imply each other. “Action completed” can precede a still-open Situation; “Situation resolved” may occur without any accepted recommendation.

Metric timestamps:

- MTTA = first acknowledgement − first detection;
- time-to-decision = first terminal recommendation/human decision − DecisionContext/review-ready time (the chosen start requires policy approval);
- time-to-action = authoritative action-start or action-command-accepted − accepted decision, reported with its chosen semantic;
- time-to-recovery = authoritative recovery fact time − first detection;
- recurrence rate = reopened occurrences / eligible resolved occurrences within an approved cohort/window.

Metrics are computed from immutable timestamps and source references. Missing timestamps yield “not measurable,” never zero. Causality language is allowed only where an approved causal design/evidence supports it; otherwise use “associated with” or chronological wording.

## 14. Control Tower Workspace Contract

This is an Operational Intelligence Workspace, not a dashboard. Its primary surface is **ATTENTION QUEUE**.

Each row answers: what requires attention (type/subject); why (explanation); how urgent (severity, urgency, priority); who owns it; since when; what is at risk using only authoritative exposure; what evidence supports it; what decision is suggested; which authorized actions are currently available; and whether intelligence is fresh.

Required queue behavior: deterministic ordering; filters that do not alter rank; visible UNASSIGNED/UNKNOWN/STALE states; non-color status cues; occurrence marker; no hidden criticality inference; and evidence/action access filtered server-side.

The secondary detail surface shows Situation lifecycle and history, current evidence, operational status, MDPM readiness, bounded timeline, Recommendation/version/disposition, existing actions with fresh authorization, and outcome/follow-up. KPI charts, BI aggregates, autonomous action, and customer-facing exposure are excluded.

## 15. Projection / Rebuild / Freshness Model

- Each admitted source has a checkpoint strategy: monotonic outbox/event cursor where reliable; otherwise `(updated/recorded time, stable ID)` plus reconciliation watermark and periodic bounded scan.
- Projection records `projection_name`, semantic `projection_version`, Signal `policy_version`, per-source checkpoint, `projected_at`, `source_observed_through`, and reconciliation status.
- Rebuild creates a separate versioned generation from authoritative sources, validates counts/identity/freshness, then atomically promotes it. It never writes source domains.
- Replay is idempotent by fact version and Signal/Situation identity. Late facts and corrections are processed according to source ordering/supersession semantics.
- Reconciliation compares source population/checkpoints with projection coverage, repairs derivable drift, and records discrepancies. It does not mutate source truth.
- Freshness states are `CURRENT`, `LAGGING`, `STALE`, `REBUILDING`, `FAILED`, and `UNKNOWN`, evaluated per source and workspace as the worst decision-relevant state.
- Failed source partitions are quarantined with last success, failed checkpoint, error classification, retry state, and affected tenant/scope. Other tenants may progress independently.
- A stale/failed projection displays its state and “as of” time in queue and detail, suppresses claims that require currentness, and blocks Recommendation acceptance/action handoff when policy demands freshness.
- Retention and maximum freshness durations require human policy; no silent default is permitted.

## 16. Correlation Model

Minimum correlation chain:

| Layer | Required linkage |
|---|---|
| Fact | source correlation if present + source fact/version + subject + tenant |
| Signal | derivation run ID + policy version + causal FactReferences |
| Situation | stable Situation ID + occurrence number + current Signal IDs |
| Attention | Situation ID + projection version |
| Recommendation | Situation occurrence + DecisionContext fingerprint/version |
| Action | existing command/result ID + Situation/Recommendation correlation metadata where the boundary permits |
| Outcome | Situation occurrence + action/recommendation/source FactReferences |

Use existing specialized event, audit, idempotency, and outbox records. Propagate a bounded `correlation_id` where supported; otherwise store an OIP correlation edge referencing public/adapter identities. Never overload idempotency keys as correlation IDs. No universal event store is proposed, and OperationalAudit/Outbox do not become business timelines.

## 17. Tenant / Legacy Source Admission Matrix

Admission requires authoritative tenant resolution, stable subject identity, version/correction semantics, visibility enforcement, and evidence access rules.

| Source | Classification | Reason / required adapter |
|---|---|---|
| OperationalShipment, RoutePlan | OIP-SAFE | explicit organization and governed versions/public shipment identity |
| Milestone | OIP-SAFE | explicit organization, public ID, version, governed lifecycle |
| MilestoneEvent | OIP-SAFE-WITH-ADAPTER | organization is nullable for lineage; adapter must resolve through milestone/shipment and reject mismatch/missing tenant |
| OperationalCheckpoint, RouteDependency | OIP-SAFE-WITH-ADAPTER | tenant derives through active plan/shipment; checkpoint/edge lack public ID |
| OperationalEvent/ExecutionUnit | OIP-SAFE-WITH-ADAPTER | strong public/version/event identity; organization derives through Project and visibility must be enforced |
| OperationalDelay/Exception and reason catalogs | OIP-SAFE | explicit organization/public/version and same-org constraints |
| OperationalWorkItem | OIP-SAFE-WITH-ADAPTER | explicit tenant but internal IDs and narrow semantics; projection source only |
| MDPM operational requirement/association/assessment/override/audit | OIP-SAFE | tenant/public/version or append-only identities and governed service; DecisionContext still filters visibility |
| OperationalAudit | OIP-SAFE-WITH-ADAPTER | useful command evidence, not operational fact; entity IDs are internal and polymorphic |
| OperationalOutbox | OIP-SAFE-WITH-ADAPTER | ingestion/correlation transport, not truth; payload schema/version coverage must be cataloged |
| ShipmentRequest | OIP-SAFE-WITH-ADAPTER | tenant only through linked Project/OperationalShipment; legacy rows without resolvable organization are rejected |
| Task | NOT-YET-OIP-SAFE | no organization, public ID, version, or canonical operational subject requirement |
| Activity | NOT-YET-OIP-SAFE | same issue; optional CRM/request links are insufficient |
| ExpertConsole Message | NOT-YET-OIP-SAFE | request-scoped legacy visibility and no canonical tenant/version envelope |
| ExpertConsole Notification | NOT-YET-OIP-SAFE | recipient/request scoped; no canonical OIP tenant/evidence contract |
| Case Document legacy state | NOT-YET-OIP-SAFE | OIP must consume MDPM operational readiness/associations, not reinterpret legacy files directly |

Cross-tenant joins fail closed and create projection diagnostics, never shared intelligence. Tenant is checked at ingestion, identity lookup, context construction, recommendation, action handoff, and evidence retrieval.

## 18. Impossible Intelligence Registry

| Prohibited intelligence | Missing authoritative fact | Why unsafe | Future source needed |
|---|---|---|---|
| carrier responsiveness/reliability | governed carrier identity, request/response obligations and outcomes | messages/events are incomplete and attribution is ambiguous | carrier aggregate plus normalized obligation/response facts and policy |
| financial exposure | authoritative charge, currency, liability, contract, and realized-loss facts | cargo/request estimates are not financial truth | finance-owned ledger/exposure contract |
| high-cost trend | comparable authoritative cost series and classification | selection/currency/time bias would mislead | finance-owned normalized cost facts |
| compliance exposure/scoring | obligations, jurisdiction, assessment, violation and disposition | documents/readiness do not equal compliance | compliance-owned case/decision facts |
| predictive delay/risk | governed outcome labels, observation windows, quality/lineage | current facts do not validate prediction/calibration | approved analytical dataset and monitoring governance |
| customer criticality | explicit service/customer criticality classification and effective dates | priority/value/free text are inconsistent legacy hints | authoritative commercial/service classification |
| network capacity optimization | capacity, booking, constraints, commitments | route topology is not capacity truth | capacity/booking domain facts |
| causal action effectiveness | counterfactual/causal evidence | temporal sequence is not causation | approved experiment or causal methodology and qualified data |

The registry is deny-by-default. New intelligence requires named authoritative facts, owner, tenant/version semantics, validation, and human admission.

## 19. AI Decision-Support Contract

AI is optional and disabled without affecting detection, Situation creation, ranking, queue, or outcomes. It may receive only an authorized DecisionContext, evidence references/content permitted for the reviewer, current Situation, and permission-filtered allowed-action catalog.

AI may produce a bounded summary, explanation, options, Recommendation draft, or missing-information questions. Every output records provider/model/prompt-policy/schema identity, context fingerprint, creation time, evidence citations, missing/contradictory information, and advisory-only authority.

AI MUST NOT create/alter facts, Signals, authoritative priority, operational state, MDPM readiness, evidence, action authorization, overrides, Situation lifecycle/resolution, or outcomes; execute/send actions; approve itself; or invent unavailable evidence. It cannot turn unknowns into facts. Human review is mandatory and acceptance remains separate from action. Existing AI-READY proposal/version/staleness/redaction/audit constraints apply.

## 20. Worked Acceptance Scenarios

### 20.1 Overdue milestone

- **Facts:** active shipment/plan; next milestone M1 incomplete; authoritative effective time passed; policy P permits evaluation.
- **Signal:** SIG-OIP-001 active with M1/time/version evidence.
- **Situation/Attention:** one OPEN Situation keyed by shipment+M1; queue row shows elapsed overdue and freshness.
- **DecisionContext/Recommendation:** current timeline, blockers, MDPM, permissions; deterministic suggestion to verify evidence and use an allowed milestone command.
- **Action/Outcome:** authorized user reports/verifies via existing command. `ACTION_COMPLETED` is recorded; only source clear produces `SITUATION_RESOLVED`; recovery is separately measured.

### 20.2 Document readiness blocked

- **Facts:** MDPM readiness for M2→COMPLETED is BLOCKED with two required blocker references.
- **Signal:** SIG-OIP-005 consumes that decision without inspecting files independently.
- **Situation/Attention:** one Situation for M2+target, even if blocker membership changes.
- **DecisionContext/Recommendation:** shows readiness fingerprint, accessible evidence, missing approval; suggests existing association/assessment action if authorized.
- **Action/Outcome:** assessment is recorded through MDPM. Recommendation acceptance is not readiness; readiness turning ready clears the Situation.

### 20.3 Active operational exception

- **Facts:** tenant-valid OperationalException E1 has no `resolved_at`.
- **Signal:** SIG-OIP-006 keyed to E1.
- **Situation/Attention:** one OPEN exception Situation; rank uses governed reason/state, not note text.
- **DecisionContext/Recommendation:** active milestone/plan and exact permitted commands; may recommend investigation.
- **Action/Outcome:** resolving E1 through its command clears the Situation; shipment recovery remains a separate fact.

### 20.4 Stale ExecutionUnit

- **Facts:** active non-terminal U1; last qualifying event precedes approved freshness threshold.
- **Signal:** SIG-OIP-007 only after threshold approval, referencing U1 and last event.
- **Situation/Attention:** UNASSIGNED is allowed; age and stale duration shown separately.
- **DecisionContext/Recommendation:** latest unit timeline and missing update; suggests an existing update/event action only if allowed.
- **Action/Outcome:** a qualifying OperationalEvent clears staleness; it does not prove delivery/recovery.

### 20.5 Repeated evaluation / deduplication

- **Facts:** same overdue checkpoint remains true across ten runs; elapsed time and evidence timestamps change.
- **Signal:** evaluations resolve to the same deterministic Signal identity/policy.
- **Situation/Attention:** one Situation and one Attention row; `last_observed_at` advances, rank may change, occurrence remains 1.
- **DecisionContext/Recommendation/Action/Outcome:** versions may refresh; no duplicate recommendation/action/outcome is implied.

### 20.6 Resolved then reopened

- **Facts:** dependency clears, then the same admitted identity becomes blocking again without plan change.
- **Signal:** inactive then active.
- **Situation/Attention:** existing Situation moves RESOLVED→OPEN, occurrence becomes 2, resolution/reopen history retained.
- **DecisionContext/Recommendation/Action/Outcome:** new context/recommendation versions bind to occurrence 2; `REPEATED` outcome records recurrence without rewriting occurrence 1.

### 20.7 Stale intelligence projection

- **Facts:** source checkpoint stops advancing beyond approved freshness maximum.
- **Signal/Situation:** last known derivation is retained but marked STALE; no false clear or new current assertion.
- **Attention/DecisionContext:** conspicuous “as of” and affected source; currentness-dependent recommendations/actions disabled.
- **Recommendation/Action/Outcome:** no fresh recommendation or handoff; projection failure diagnostic is not an operational outcome.

### 20.8 No owner available

- **Facts:** valid Situation but no approved queue mapping/eligible assignee.
- **Signal/Situation/Attention:** detection proceeds; owner is UNASSIGNED and may influence attention only under approved policy.
- **DecisionContext/Recommendation:** missing ownership explicit; AI cannot invent it.
- **Action/Outcome:** authorized dispatcher may assign/claim; assignment is an attention event, not recovery.

### 20.9 Recommendation rejected

- **Facts through DecisionContext:** valid active Situation and fresh context.
- **Recommendation:** reviewer chooses REJECTED with reason.
- **Situation/Attention:** remains based solely on Signal; no automatic dismissal/resolution.
- **Action/Outcome:** no action executes; `RECOMMENDATION_DISPOSITIONED=REJECTED`; later source clear independently resolves.

### 20.10 Action completed, recovery not achieved

- **Facts:** replan command completes and new active plan exists, but a checkpoint remains blocked.
- **Signal/Situation:** old-plan Situation resolves by supersession; new-plan blocking condition creates a correlated new Situation.
- **Attention/DecisionContext/Recommendation:** queue shows the new current condition and action history.
- **Action/Outcome:** `ACTION_COMPLETED` is true; `OPERATIONAL_RECOVERED` is absent. The system must not label shipment recovered.

## 21. Architectural Guardrails

1. **No Dashboard First:** the attention queue and decision detail precede aggregation/BI.
2. **No Alert Flood:** deterministic identity, atomic dedup, clear/reopen, and one actionable projection are mandatory.
3. **No Everything-Is-Red:** critical bands require explicit approved predicates; unknown is visible.
4. **No AI Authority:** AI is advisory, human-reviewed, and non-executing.
5. **No Duplicate Operational Truth:** FactReferences point to owners; OIP never rewrites their state.
6. **No Generic Rule Engine:** only seven versioned deterministic policies are admitted.
7. **No Workflow Engine:** lifecycle is attention handling, not BPMN/domain orchestration.
8. **No Signal Without Evidence:** every active Signal has source/version/policy/evidence.
9. **No Situation Without Identity:** creation fails closed without complete canonical identity.
10. **No Priority Without Explanation:** every band is reproducible; missing inputs are named.
11. **No Action Without Existing Authority:** available actions are existing, permission-filtered command targets.
12. **No Outcome Without Measurable Fact:** dispositions, completion, resolution, and recovery remain distinct.
13. **No Stale Intelligence Without Warning:** staleness is explicit and can block decision/action handoff.

## 22. OIP Decision Register

| ID / question | Options and evidence | Recommendation / trade-off | Human? / deferral impact |
|---|---|---|---|
| OIP-D16 Situation lifecycle | minimal vs extended; existing WorkItem has open/resolved, OIP needs attention handling | approve six states; treat expiry/supersession as reasons | Yes; blocks lifecycle implementation |
| OIP-D17 WorkItem relationship | extend, projection, replace | choose B: Situation durable, WorkItem/Attention projection; more mapping, least compatibility risk | Yes; blocks persistence/API design |
| OIP-D18 identity/policy version | exact version vs semantic-major identity | semantic-major plus dimensions; prevents floods while allowing meaning changes | Yes; blocks uniqueness/concurrency design |
| OIP-D19 overdue effective-time precedence | planned vs projected vs domain decision | consume domain-authoritative effective time; approve per signal | Yes; overdue detection disabled where unresolved |
| OIP-D20 threshold authority | retain local vs central governed policies | ratify/replace local 24h; approve owners for tolerance/stale/repetition/escalation | Yes; affected Signals/rank disabled |
| OIP-D21 rank semantics | numeric score vs lexicographic decision table | lexicographic bands without arbitrary weights | Yes; queue may be UNRANKED |
| OIP-D22 critical predicates | broad elapsed rules vs explicit blockers/classes | explicit allow-list only | Yes; P0/CRITICAL unavailable until decided |
| OIP-D23 owner derivation | assignment, responsibility text, governed queues | governed mapping; UNASSIGNED otherwise | Yes; auto-routing deferred safely |
| OIP-D24 freshness | one global vs source-specific | source-specific maximum plus worst decision-relevant state | Yes; cannot claim CURRENT without it |
| OIP-D25 retention/reopen horizon | indefinite vs governed type-specific | retain audit/history; approve type/privacy horizons | Yes; storage/recurrence design blocked |
| OIP-D26 Recommendation lifecycle | overwrite vs immutable versions | minimal immutable lifecycle in §11 | Yes; recommendation implementation blocked |
| OIP-D27 outcome measurement start points | several legitimate timestamp semantics | publish metric semantic names and denominators before use | Yes; metrics/claims deferred |
| OIP-D28 legacy admission | implicit joins vs fail-closed adapters | approve matrix; no Task/Activity/Message/Notification ingestion yet | Yes; protects tenant isolation |
| OIP-D29 MDPM source boundary | recalculate vs consume readiness | consume authoritative MDPM output/fingerprint only | Yes confirmation; prevents duplicate truth |
| OIP-D30 projection ingestion | outbox-only vs hybrid checkpoint/reconcile | hybrid per-source strategy, no universal event store | Yes; implementation topology blocked |
| OIP-D31 manual dismissal/reopen | suppress forever vs condition-aware reopen | reasoned dismissal; persisting/recurring condition reopens by policy | Yes; prevents hidden risk |
| OIP-D32 AI initial scope | detection/rank vs decision support | exclude AI from detection/rank; future Decision Support only | Yes confirmation; hard OIP-2 gate |

## 23. Human Decisions Required

Before implementation, humans must approve D16–D32, particularly: the six-state lifecycle; WorkItem-as-projection relationship; identity dimensions and semantic policy version behavior; effective time precedence; policy owners and values for overdue/stale/repetition/escalation/freshness; lexicographic rank bands and critical predicates; queue/owner derivation; retention/reopen horizons; recommendation dispositions; exact metric semantics; tenant admission adapters; MDPM boundary; projection strategy; and AI exclusion.

Decisions may be staged. A Signal whose threshold/source identity/admission is unresolved remains disabled. OIP-2 must not compensate with guessed defaults.

## 24. OIP-2 Entry Criteria

Implementation may begin only when:

- the exactly seven-Signal catalog and enablement status are accepted;
- Situation lifecycle, status transition permissions, and resolution/dismissal semantics are accepted;
- threshold ownership, values, effective-time rules, and policy versioning are approved;
- per-type identity, dedup, reopen, supersession, and concurrency semantics are approved;
- severity/urgency/priority decision table, critical predicates, explanation, and ties are approved;
- tenant/legacy admission matrix and required adapter contracts are accepted;
- Situation/OperationalWorkItem/AttentionItem relationship is accepted;
- ownership queues, UNASSIGNED behavior, and assignment permissions are accepted;
- DecisionContext and Recommendation version/staleness/human-review contracts are accepted;
- existing action catalog and genuine gaps are confirmed by domain owners;
- outcome definitions, metric timestamps/denominators, and non-causality language are accepted;
- projection checkpoints, rebuild, reconciliation, failure isolation, freshness, and retention requirements are accepted;
- security/privacy/evidence visibility and correlation/audit requirements are approved;
- AI is explicitly excluded from initial detection and ranking and can be disabled end-to-end;
- architecture acceptance scenarios are converted into implementation acceptance tests without weakening their assertions.

## 25. Framework Delta

### PROJECT FINDING

Forwarder has sufficient authoritative operational/MDPM facts and proven work-item reconciliation to support an OIP layer, but not enough governed thresholds, queue ownership, legacy tenant identity, or business classifications to implement every proposed behavior safely. The Situation/WorkItem separation is the principal architecture refinement.

### FRAMEWORK DELTA

| Classification | Finding |
|---|---|
| CONFIRMS EAAF | derived intelligence must remain outside authoritative domains; versioned evidence, tenant isolation, human authority, audit/outbox separation, and stale-safe projections confirm existing principles |
| REFERENCE EXAMPLE CANDIDATE | Forwarder’s `FactReference → Signal → Situation → AttentionItem` separation and resolved-versus-recovered outcome example |
| PATTERN CANDIDATE | deterministic Situation identity with semantic policy version, reopen history, and one queue projection |
| ENTERPRISE PATTERN CANDIDATE | impossible-intelligence registry plus fail-closed source admission matrix for derived intelligence |
| NO FRAMEWORK CHANGE | OIP-1 requires no immediate change to 29-lpaf/EAAF; candidates require separate cross-project review before promotion |

No files in `D:\1-webapp\29-lpaf` are modified by OIP-1.

## 26. Final Verdict

OIP-1 CONTRACT READY FOR HUMAN APPROVAL

