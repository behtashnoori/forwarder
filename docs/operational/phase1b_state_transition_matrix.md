# State transitions

| Aggregate | Allowed transitions |
|---|---|
| Route plan | draft → active/cancelled; active → superseded/cancelled |
| Route leg | planned → ready/in_progress/blocked/cancelled; in_progress → completed/blocked |
| Checkpoint | planned/approaching → arrived → processing → ready_to_depart → departed/completed |

Checkpoint milestone lifecycle is `planned -> reported -> verified`; correction moves a verified milestone back to `reported` until independent re-verification.

Invalid checkpoint transitions return HTTP 409 with `INVALID_CHECKPOINT_TRANSITION`. Stale route commands return `STALE_ROUTE_VERSION`; stale checkpoint milestone commands return `STALE_MILESTONE_VERSION`. A reporting/correcting actor cannot verify the same current event; this returns HTTP 403 with `REPORTER_CANNOT_VERIFY_OWN_EVENT`. Correction requires a reason and only applies to a verified milestone. Until re-verification, the milestone and corresponding checkpoint actual are null/non-current.

Route exception/work-item lifecycle is `open -> resolved -> open`. Automatic resolution records `CONDITION_CLEARED` with source `automatic`; manual resolution requires a reason and records source `manual`. If the condition remains or recurs, reconciliation reopens the same historical row, increments its occurrence count and version, and leaves exactly one actionable open item for the plan/checkpoint/type scope. Superseded plans are not reconciled and their history is retained.

Atomic replan is a specialized transition: `active source -> superseded` and `draft target -> active` occur together after clone validation. A replan-specific stale version returns `STALE_ROUTE_PLAN_VERSION`; a superseded/cancelled/non-current source returns `ROUTE_PLAN_NOT_ACTIVE`. Any failure rolls both transitions back.

Timeline reconciliation is not a lifecycle transition. It updates only derived projected values on the active plan. Effective timestamp precedence is `actual → projected → planned`; planned and verified actual values remain unchanged. A changed reconciliation increments the route-plan version, while a no-op/replay creates no additional audit or outbox event.

Exception reconciliation consumes that calculated active-plan timeline without triggering timeline recalculation. `CHECKPOINT_OVERDUE`, `ROUTE_DEPENDENCY_BLOCKED`, and the existing 24-hour `REPLAN_REQUIRED` rule open or reopen one scoped actionable row; a cleared condition resolves it atomically. Manual resolution is optimistic and idempotent, and a persisting condition is deliberately reopened on the next reconciliation.

Direct PostgreSQL race evidence confirms the transition ordering under concurrency. Manual resolve and automatic reconciliation serialize on the scoped exception row: a cleared condition ends resolved, while a persisting condition ends either coherently open with one actionable row or resolved under the explicit suppression outcome. Replan and exception reconciliation serialize through the active plan: reconciliation either completes on the source before atomic supersession, or observes the new active revision and applies only that revision's state. Source exceptions are historical/non-actionable after replan and are never cloned to the target.
