# ADR-068: Versioned closure checklist and explicit Shipment closure

- Status: ACCEPTED
- Date: 2026-09-26
- Owners: Architecture; Operational Shipment; Organization policy; Security; Data
- Affected domain: closure configuration, terminal state, historical decision
- Product authority: [P3-11..13 mission](../../product/phase3/P3-11-13-MISSION-AUTHORITY.md), retained source §§26–47
- Acceptance date: 2026-09-26
- Acceptance authority: Product Owner, explicit named acceptance and completed-only predecessor decision in the [architecture acceptance mission](../../product/phase3/P3-11-13-ARCHITECTURE-ACCEPTANCE.md)
- Implementation authority: bounded P3-12 implementation authorized; qualification and controlled integration gates remain mandatory

## Context and problem

Canonical OperationalShipment permits planned/in_progress/completed/cancelled;
there is no CLOSED state. `completed` cannot be silently renamed. P3-08 delivery
records never close the Shipment. ADR-030/061/064 own exact document readiness,
context and delivery evidence. OperationalException and OperationalWorkItem own
independent current states. Closure policy and a retained closure decision are
missing, even though the Product boundary is explicitly approved.

## Accepted decision

1. Add organization-owned ClosurePolicy, append-only ClosurePolicyVersion and
   typed ClosurePolicyCriterion rows, plus Shipment-owned ClosureDecision.
   Only the same-tenant Organization Admin configures policy. Stable code-defined
   criterion families map to explicit domain read adapters, never executable
   expressions, arbitrary JSON rules, SQL, or a second source of operational facts.
2. Versions have actor, recorded time and effective-from Instant; intervals are
   [start,next-start). Changes are prospective and serialized using expected policy
   version and actor/payload-bound idempotency. No checklist or criterion is seeded.
   The assessment selects the policy effective at its explicit assessment instant;
   the closure command re-resolves applicability and rejects an unexpected version.
   The closure decision pins the exact version forever.
3. Compose GENERAL plus each applicable mode's criteria as an explicit union.
   Preserve origin/mode and each stable criterion ID; do not discard overlapping
   conditions. If a shared criterion is selected in multiple scopes, retain all
   contributing scopes and enforce mandatory if any applicable selection is
   mandatory. Applicable modes derive only from governed Shipment route/execution
   facts, including its relevant multimodal stages; missing mode information is
   an explicit applicability gap, not an invented mode or discarded requirement.
4. Approved adapter families are delivery/final-state facts, known authoritative
   Cargo operational quantities, current required document readiness, configured
   blocking operational Exceptions and configured required WorkItems/follow-ups.
   Explicit criterion options must name the exact existing field/status, scope,
   comparison and unknown result. Do not infer final delivery from a lifecycle
   label, turn excess delivery into a new universal hard failure, or infer loss/
   cancellation from a quantity difference. A family without an authoritative fact
   cannot be advertised as an executable criterion. No HS criterion is registered.
5. No applicable policy returns «قواعد بستن پرونده تعریف نشده است» and cannot
   produce a governed closure command, including a reason-only fake assessment.
   Optional failures remain visible; normal closure requires every mandatory
   applicable criterion to pass and applicability to be determinate. Unknown is
   never PASS. The UI shows remaining requirements first and links to their source.
6. Add the minimum explicit `closed` terminal Shipment state and one immutable
   ClosureDecision recording previous state, normal/exception type, actor, reason,
   committed version, policy version, current assessment and missing-fact snapshot.
   Existing arrival, delivery and `completed` remain separate and are never
   backfilled as closed. No reopening route or generic state machine is introduced.
   Both NORMAL and EXCEPTIONAL closure permit only `completed -> closed`.
   `planned`, `in_progress`, and `cancelled` cannot close through either command.
   Exceptional Admin closure bypasses mandatory checklist failures only; it never
   bypasses lifecycle progression. Any other predecessor requires a future,
   separate Product Owner decision outside P3-12.
7. Normal close is an owning-active-Expert command. Exceptional close is a
   same-tenant Organization Admin command with explicit capability and mandatory
   reason. The Admin must review current missing/unknown items. Commit rechecks
   actor, tenant, Shipment version, policy version and all current source facts.
   Do not treat an earlier frontend assessment as authority.
8. Use one local transaction with a documented fixed lock order. Policy edits and
   source writes that can affect the assessment must participate in an explicit
   serialization contract with closure; absent-row inserts need fencing too.
   A Shipment lock alone is insufficient where a document/Exception/WorkItem
   writer does not take it. Inventory and adapt those bounded write paths without
   changing their Product semantics, or use a proven serializable retry boundary.
   Reauthorization after waiting and expected assessment/source identity prevent
   the stale-read command from closing after a required fact changed.
9. Closure changes only Shipment terminal state, version and its closure/audit
   facts. Never resolve an Exception, complete a WorkItem/Action, close SLA, delete
   Attention, fabricate delivery or mark a missing document ready. The historical
   missing snapshot remains even if those independent objects later change.

## Closed-state boundary

Protect the terminal state against ordinary status overwrite and implicit reopen.
Assess post-closure commands individually against their accepted contract; there
is no blanket 'all writes denied' middleware. Already-authorized historical
correction and independent Exception/WorkItem lifecycles must be considered
separately from ordinary operational progression. Before integration, produce a
command-level allow/deny matrix with exact authority. If an existing correction
has no defined post-closure meaning, record that narrow ambiguity and stop only
its affected design; this proposal does not silently decide it. No Customer
internal checklist, Admin reason or private missing-item disclosure is added.

The matrix must record COMMAND, ALLOWED_AFTER_CLOSED, DENIED_AFTER_CLOSED,
AUTHORITY and REASON. A genuinely undefined Product meaning is DECISION_NEEDED
for that narrow command; it is not an implicit blanket denial or new permission.

## Security and time

Current tenant comes from authenticated active membership. Ordinary Expert,
non-owner Expert, Platform Admin and foreign-tenant Admin cannot use exceptional
closure. IDs, stale pages and role labels alone grant nothing. Internal history
uses current read authority; Customer receives only separately authorized safe
status. All effective/assessment/decision times are UTC Instants serialized with
offset and rendered through ADR-016 helpers; no new Local Date/calendar policy.

## Alternatives and consequences

Reject automatic closure on arrival/delivery, reinterpretation of completed,
copied operational state, universal defaults/HS, generic expressions and hidden
Expert bypass. Reuse MDPM readiness instead of file-count heuristics. Snapshot
only the decision basis; normal assessment reads the current SOR. The cost is
bounded policy/history persistence and transaction coordination; the benefit is
an explainable decision without rewriting unfinished operational work.

## Compatibility, migration and rollback

One additive migration follows the actual then-current canonical head; P3-11 is
not a dependency. Extend the status constraint without rewriting legacy rows; add
empty typed tables and parent/tenant FKs with immutable decision/history guards.
No seed or fabricated closure. Empty downgrade/re-upgrade must pass PostgreSQL 18;
populated policy/decision history or closed rows must prevent destructive downgrade.
An N-1 application lacking closed semantics is not a supported rollback after
first use. Keep data and fail closed pending a separately governed compatible
roll-forward; never erase decisions or reopen records to make downgrade pass.

## Operational impact and validation

No scheduler/deployment or production action. Assessment failures distinguish
missing policy, source unknown, stale version and authorization failure. Read
cost follows bounded source summaries; no unbounded copied facts or analytics.

Mission cases A–L: GENERAL/mode/multimodal union; Expert success and denied bypass;
Admin reason and retained missing facts; policy V1/V2; no auto-close from delivery;
no auto-resolve/complete; stale facts between assessment and command including
concurrent inserts; duplicate command replay and competing closures; all role/
tenant negatives. Prove PostgreSQL 18 upgrade/rollback/locks; Chrome Expert/Admin
normal navigation/reopen/missing-first dialog and history; P3-06/07/08, Customer,
Workspace/Tower, SLA/Exception/Action plus the mission's complete regression gates.

## Supersedes / superseded by and status history

Supersedes none. Extends ADR-007/010/016/030/054/
061/064 only for explicit closure and policy; it changes neither their historical
truth nor their independent source lifecycles. Superseded by: none.
2026-09-26: PROPOSED; named architecture acceptance pending. DN01's bounded
closure decision and the policy authority are resolved; DN05 remains open only
for future specific HS policy. No runtime implementation or qualification.

2026-09-26: ACCEPTED by the named acceptance/resume mission with the explicit
completed-only predecessor for both normal and exceptional closure.
`DN01_CLOSURE_STATUS=RESOLVED_FOR_P3_12`;
`DN05_GENERAL_CLOSURE_RULE=NOT_IMPLEMENTED`;
`DN05_STATUS=OPEN_FOR_FUTURE_SPECIFIC_POLICY`.
Original proposal evidence is retained at review commit
`081f73a3d84c6aa6136e7f1fd4268f57bac497cf`.
