# Time Business Decision Register

This register records business time policies separately from the technical
principles in [ADR-016](../../operational/adr/ADR-016-time-and-timezone-architecture.md).
Acceptance here authorizes design and phased implementation; it does not
authorize an unreviewed legacy timestamp migration.

## Status vocabulary

- `Accepted`: the approved policy answers the decision question exactly.
- `Pending technical validation`: the supplied policy does not completely
  answer the existing decision question or needs a technical contract.
- `Rejected`: the option was explicitly rejected.
- `Deferred`: work is postponed until a named trigger.

## Decisions

| ID | Topic | Status | Recorded policy |
| -- | -- | -- | -- |
| TIME-BIZ-001 | SLA Policy | Accepted | Initial expert response is due after the per-expert working-minute duration managed exclusively by an admin (default 120 minutes), from successful assignment, using the responsible unit's timezone, working hours and holidays. Policy/version must be auditable. |
| TIME-BIZ-002 | SLA Reassignment | Accepted | Ordinary reassignment does not reset SLA. Only a formal organizational responsibility transfer with reason and audit may recalculate it. |
| TIME-BIZ-003 | Quote Validity Zone | Accepted | `valid_until` remains a Local Date. Validity ends at the start of the following local day in the customer/market timezone, falling back to issuer-organization timezone. Snapshot the applied policy; never use `23:59:59.999`. |
| TIME-BIZ-004 | Quote Response Meaning | Accepted | System receipt time is authoritative and should become `response_received_at`. A customer-stated time may be stored separately and never replaces receipt time. |
| TIME-BIZ-005 | CRM Due Type | Accepted | Support Local Date `due_date` and Instant `due_at`. Never turn the date-only value into UTC midnight. |
| TIME-BIZ-006 | CRM Due Ownership | Pending business clarification | Proposed only: `due_date` is a Local Date without timezone. Exact `due_at` ownership, approving authority, approval/effective dates, scope, and recorded decision evidence remain unresolved. This decision is limited to CRM due-date ownership and does not govern expert SLA. |
| TIME-BIZ-007 | Tracking Event Zone | Accepted | Use the actual event Location's IANA timezone. If Location is unknown, require explicit timezone. Browser timezone is not authoritative. Override requires permission, reason and audit; preserve occurrence, recording time, source and provenance. External timestamps require an offset. |
| TIME-BIZ-008 | Operational Departure Zone | Accepted | Resolve and display departure in the canonical origin Location timezone; store UTC Instant plus IANA timezone snapshot. Override requires reason and audit. |
| TIME-BIZ-009 | Operational Arrival Zone | Accepted | Resolve and display arrival in the canonical destination Location timezone; checkpoints use their own Location timezone. Store UTC Instant plus IANA timezone snapshot. |
| TIME-BIZ-010 | Reporting Company Day | Accepted | Internal company reporting uses `Asia/Tehran`; branch/customer/user/operation/SLA reports use their named business timezone; comparisons use UTC or an explicit zone. APIs must eventually expose boundary metadata. |
| TIME-BIZ-011 | Tracking fallback | Accepted | Without a known Location, explicit timezone selection is mandatory; no browser/server-zone guess is allowed. |
| TIME-BIZ-012 | Session expiry | Accepted | Access lifetime is 1 hour, refresh idle lifetime 30 days, absolute session lifetime 90 days, and clock skew 60 seconds. All are configurable. Session expiry never expires a Shipment. |

## Confirmed policies without a matching register question

These policies are confirmed, but no new synthetic decision ID was introduced:

- `ready_at` means workflow readiness; future design separates
  `workflow_ready_at`, cargo readiness and `sla_started_at`.
- Customer touch is a real customer interaction. Future design separates
  `occurred_at` from `recorded_at`, and derives `last_customer_touch_at`.
- `pickup_date` and `delivery_date` are planned Local Dates; confirmed and
  actual instants will be separate.

No schema change or historical backfill is authorized by this record.
