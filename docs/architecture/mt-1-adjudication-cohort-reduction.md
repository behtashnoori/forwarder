# MT-1 adjudication cohort reduction

## 1. Current real census facts

There are 135 UNRESOLVED, QUARANTINED rows, zero Organization candidates,
no mappings, and no authoritative ownership lineage. Readiness remains false.

## 2–3. Structural classification

| Entity | Rows | Class | Canonical parent | Parent row locally bindable? | Disposition inheritance | Organization inheritance | Review granularity |
|---|---:|---|---|---|---|---|---|
| ShipmentRequest | 13 | ROOT_DECISION | none | n/a | no | no | individual |
| Customer | 1 | ROOT_DECISION | none | n/a | no | no | individual |
| CustomerGamification | 6 | ROOT_DECISION | none | n/a | no | no | individual |
| ShipmentRequestLog | 13 | DERIVED_DESCENDANT | ShipmentRequest required | no parent IDs | structurally possible, not now | no | individual |
| ShipmentTracking | 6 | DERIVED_DESCENDANT | ShipmentRequest required | no | structurally possible, not now | no | individual |
| ShipmentTransportUnit | 6 | DERIVED_DESCENDANT | ShipmentTracking required | no | structurally possible, not now | no | individual |
| ShipmentTransportUnitUpdate | 11 | DERIVED_DESCENDANT | TransportUnit required | no | structurally possible, not now | no | individual |
| CaseDocumentRequirement | 2 | DERIVED_DESCENDANT | ShipmentRequest required | no | structurally possible, not now | no | individual |
| ExpertQuote | 3 | DERIVED_DESCENDANT | ShipmentRequest required | no | structurally possible, not now | no | individual |
| ExpertConsoleLog | 29 | DERIVED_DESCENDANT | ShipmentRequest required | no | structurally possible, not now | no | individual |
| ReferralAssignmentLog | 12 | DERIVED_DESCENDANT | ShipmentRequest required; rule optional | no | structurally possible, not now | no | individual |
| DocumentAuditEvent | 3 | CONDITIONAL_DESCENDANT | request/file nullable | no | only after consistent path proof | no | individual |
| ExpertConsoleNotification | 29 | CONDITIONAL_DESCENDANT | request nullable | no | only after parent proof | no | individual |
| ReferralAutoAssignState | 1 | PLATFORM_OR_SINGLETON_REDESIGN | none; singleton | n/a | no | no | individual redesign review |

## 4–5. Safe and unsafe cohorting

Safe multi-row cohorting requires identical entity class, exact authoritative
root, classification, quarantine state, disposition, and no competing/missing
path or row-specific evidence. Stable rows and two-person row-level expansion
remain mandatory. Grouping by type alone, assignee, adjacency, names, or a
theoretical parent is unsafe. Mixed roots, nullable-parent rows, and singleton
state cannot be combined. Cohorts never turn UNKNOWN into DETERMINISTIC.

## 6. Minimum projection

- Root rows: 20.
- Mandatory derived descendant rows: 82.
- Conditional descendant rows: 32.
- Independent legacy artifacts: 0.
- Redesign/singleton rows: 1.
- Safe multi-member cohorts with current sanitized evidence: 0.
- Fail-closed single-member cohorts: 135.
- Minimum human decision events now: 135.

## 7–9. Remaining human work and special rows

All 135 rows still require individual decisions. The 82 mandatory descendants
are eligible only for future disposition inheritance after exact parent IDs are
mechanically supplied and validated; Organization assignment never inherits.
ReferralAutoAssignState naturally permits REDESIGN_REQUIRED,
KEEP_QUARANTINED, or NEEDS_MORE_EVIDENCE, without selecting one. Orphan
Customer 1 safely permits KEEP_QUARANTINED, RETIRE_INACTIVE_LEGACY_ROW, or
NEEDS_MORE_EVIDENCE, again without selecting a decision.

## 10. Expansion controls

The validator requires exact original membership, one active cohort per row,
compatible roots for multi-member cohorts, no unvalidated cohort assignment,
complete review/expansion, two reviewers, current approval, evidence, row-level
decision IDs, and retained quarantine. It performs no production mutation.

## 11–12. Remaining work and readiness

A sanitized parent-link transfer is required before workload reduction can be
proven. Human review is not complete.

`MT1_OWNERSHIP_RESOLUTION_READY=false`

`AUTO_BACKFILL_ALLOWED=NO`

`QUARANTINE_MUST_REMAIN=YES`
