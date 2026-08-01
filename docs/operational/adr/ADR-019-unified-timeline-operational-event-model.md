# ADR-019: Unified Timeline and Operational Event Model

- Status: Accepted
- Date: 2026-07-31
- Acceptance date: 2026-07-31

## 1. Context

Operational history is currently distributed across request logs, expert logs/messages, ShipmentTransportUnitUpdate, MilestoneEvent, document audit, operational audit/outbox, and projections. The records have different visibility, correction, idempotency, and ordering semantics. Projects spanning several shipments and units need a consistent timeline contract without forcing every aggregate into full event-sourced persistence.

## 2. Decision

Adopt a unified append-only **OperationalEvent** envelope and timeline projection. This is lightweight event sourcing: important operational facts are immutable events and selected projections are rebuildable, while aggregate persistence may continue to store canonical current state and relational invariants.

The event catalog includes at least status changed, assignment changed, document uploaded/replaced/verified, location/checkpoint updated, delay reported, exception opened/resolved, shipment split/merged, unit created/deactivated, customer-visible update published, report submitted, approval recorded, and references to payment/financial events where appropriate. Financial values and ledgers remain owned by a future finance boundary; timeline events reference them without becoming the accounting source of truth.

## 3. Domain definitions

- **OperationalEvent:** immutable fact envelope with event type, identity, scope, time, actor/source, visibility, payload, and provenance.
- **Scope:** one primary subject among `project`, `shipment`, `execution_unit`, or `document`; additional related subjects are explicit references.
- **Occurred at:** UTC instant when the business fact happened.
- **Recorded at:** UTC instant when the system durably accepted the event.
- **Actor:** authenticated human/service/agent principal responsible for the command.
- **Source:** manual UI, API client, partner integration, system rule, migration, or AI-assisted approved action.
- **Timeline projection:** ordered, permission-filtered read model assembled from events.
- **Audit:** security record of decision/action; related to but not replaced by the customer/operational timeline.

## 4. Invariants

- Every event has an opaque immutable `event_id`, stable `event_type` and schema version, primary scope type/public ID, organization ID, occurred/recorded instants, actor/source, visibility, classification, correlation ID, and payload.
- Scope identifiers use the Project, OperationalShipment, ExecutionUnit, and Document public IDs from ADR-017, ADR-018, and ADR-020.
- `recorded_at` is assigned by the trusted backend and never precedes transaction acceptance; `occurred_at` may be earlier and must obey source/policy bounds.
- Customer message and internal note are separate fields. Visibility never derives from message presence.
- Allowed visibility is explicit; classification may further restrict it.
- Events are append-only. Correction creates a new event with reason and `supersedes_event_id`; original history remains.
- Sensitive create/transition commands use idempotency keys and payload hashes. Duplicate key/same payload replays; changed payload conflicts.
- Correlation ID groups one business workflow; batch ID groups fan-out outcomes. Each child event remains independently identifiable.
- Metadata is JSON following a versioned event-type schema; core security, identity, ordering, and scope fields are columns/contracts rather than arbitrary metadata.
- Ordering is deterministic by business ordering policy using occurred time, recorded time, source precedence where approved, and event ID as final tie-breaker. Arrival order alone is not truth.
- Aggregate expected version prevents lost updates. Out-of-order facts are accepted or quarantined per event policy and trigger deterministic projection reconciliation.

## 5. Security implications

Timeline reads filter by organization, subject access, visibility, classification, and stakeholder relationship before serialization. Internal notes and restricted metadata are absent from unauthorized projections, not merely hidden in UI. Actor identities may be redacted in customer views. Event correction, publication, approval, and financial references require explicit permissions. Agent-originated events record agent identity, human approver/policy, evidence, and explanation. Audit events are retention-protected and cannot be deleted through business APIs.

## 6. Data and migration implications

Future implementation adds a canonical event envelope and projection checkpoints additively. Existing MilestoneEvent remains authoritative for milestone verification under ADR-009; it may emit/link a unified event rather than being destructively replaced. ShipmentTransportUnitUpdate, logs, messages, document audit, and outbox records are bridged or backfilled only with source labels and preserved identifiers. Unknown occurred times are not fabricated. No migration occurs in this phase.

## 7. API implications

Provide paginated timeline queries by Project, Shipment, ExecutionUnit, or Document with cursor/keyset pagination, event-type/time/visibility filters, and stable schemas. Writes are explicit action endpoints owned by aggregates; a generic “post any event” endpoint is prohibited for untrusted callers. Responses include event IDs, aggregate versions, and emitted event references. Existing milestone and tracking endpoints remain compatible while emitting/bridging canonical events behind feature flags.

## 8. UI implications

UI presents a unified timeline with scope/type filters, source/verification badges, occurred versus recorded time where relevant, correction chains, and customer/internal preview. Large projects load pages lazily. Batch operations show one correlation plus per-unit outcomes. UI cannot override server visibility decisions.

## 9. AI-native implications

Events form traceable evidence for recommendations and explanations. AI reads a permission-filtered event projection and cites event/document IDs. Proposed actions include reason, evidence, expected versions, and predicted effects. Approved agent actions execute through business commands and record agent, policy, approver, correlation, and outcome. Autonomous action is disabled until an explicit policy authorizes the exact event/action class.

## 10. Alternatives considered

- Keep separate timelines indefinitely: rejected because semantics and leakage controls would drift.
- Full event sourcing for every aggregate: rejected as unnecessary migration and operational complexity.
- One generic mutable activity table: rejected because correction, provenance, schema, and concurrency would be weak.
- Use audit log as customer timeline: rejected because audit and business visibility have different retention and disclosure purposes.
- Order only by occurred_at: rejected because ties, late events, and source precedence require deterministic reconciliation.

## 11. Consequences

Operational history becomes queryable, explainable, and rebuildable across scopes. Existing specialized event models can coexist through links/adapters. Costs include schema governance, projector operations, retention volume, and careful visibility testing.

## 12. Risks

- Event-type proliferation without ownership/schema review.
- PII or internal details inside metadata.
- Projection lag or duplicate emission.
- Incorrect ordering of late or corrected events.
- Confusing audit, outbox, event, and projection responsibilities.
- Retention growth for large projects.

## 13. Backward compatibility

Current logs, ShipmentTransportUnitUpdate, MilestoneEvent, OperationalAudit, OperationalOutbox, and DocumentAuditEvent remain intact. Compatibility projections preserve existing API shapes. Canonical events are introduced through additive emission/bridging and shadow comparison; no immediate breaking API change is required.

## 14. Rollout strategy

Approve event catalog and schemas; add envelope and projector; emit from one low-risk unit command; verify atomic event/outbox/audit behavior; backfill a bounded cohort; expose internal read-only timeline; compare legacy/canonical projections; expand event producers; then enable customer timeline per cohort.

## 15. Rollback strategy

Disable new emitters/projectors and route reads to legacy timelines. Preserve canonical events and projector checkpoints for reconciliation. Do not delete duplicate-looking events before idempotency and causation analysis. Business aggregate rollback remains owned by its command policy, not by deleting timeline events.

## 16. Open questions

- Product Owner/Security: stakeholder visibility matrix and customer publication workflow.
- Data Owner: event retention and archive policy by classification.
- Architecture: synchronous projection requirements versus acceptable lag.
- Operations: source precedence and lateness windows by integration.
- Compliance: which actor fields must be redacted in customer views.
- Finance: approved financial reference events and prohibited payload fields.

## 17. Acceptance criteria for approving the ADR

- Event envelope, scopes, identity, occurred/recorded semantics, correction, ordering, and concurrency are approved.
- Audit, outbox, specialized domain events, and timeline projection responsibilities are distinct.
- Visibility tests guarantee zero internal-note leakage.
- Metadata schemas are versioned and prohibit uncontrolled sensitive data.
- Projection rebuild is deterministic under duplicate, late, and corrected events.
- Existing MilestoneEvent invariants from ADR-009 remain authoritative and compatible.
- AI read/recommend/action traceability satisfies governance requirements.
