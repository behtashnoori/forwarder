# Expert Workload Semantics

Status: governed behavior-preserving projection

## User-facing definition

`بار کاری فعلی` is the unweighted count of tenant-owned `ShipmentRequest` rows
currently assigned to an active expert with an active membership in the current
organization and status `assigned` or `in_progress`. Each request contributes
exactly one. The projection is live and informational, not historical.

Included statuses: `assigned`, `in_progress`.

Excluded statuses: `new`, `quoted`, `waiting_for_customer`, `won`, `lost`, and
`closed`. There is no separate paused status. A reopened request contributes
when its current status returns to `assigned` or `in_progress`; its history does
not add weight. Cancelled/rejected/completed are not current ShipmentRequest
status values; terminal equivalents `lost` and `closed` are excluded.

## Assignment, capacity, and ordering

The displayed workload does not control default assignment. Default referral
uses time-based round robin: the expert with the oldest last-assignment time is
selected, with no-history and expert-ID tie breaks.

Existing referral `least_workload` and `max_active_assignments_per_expert`
compatibility behavior counts `assigned`, `in_progress`, `quoted`, and
`waiting_for_customer`. This broader engine count is deliberately distinct from
the displayed operational count. Changing it, capacity behavior, or fairness
guarantees requires an Accepted ADR. The legacy `assignment_engine.py` also has
workload-based paths and is not made canonical by this read projection.

## Tenant and performance behavior

The organization comes only from authenticated organization context. Request
ownership, active membership, active expert state, and organization identity
are enforced in the query. A multi-organization user receives an independent
count for each organization. List views aggregate all experts in one grouped
request query after one membership query; they do not issue one request-count
query per expert.

## Examples

- Two `assigned`, one `in_progress`, one `quoted`: displayed workload is 3;
  referral compatibility active count is 4.
- A `closed` request remains assigned historically but contributes zero.
- Default round robin may select an expert whose displayed workload is higher;
  the displayed count is not the default ordering score.
