# ADR-054 — Organization SLA, bounded Action, and deterministic Attention extension

- Status: ACCEPTED for the Product-approved Phase 2 mission
- Date: 2026-09-24
- Owners / authority: Product Owner (mission); Organization Admin (tenant SLA values); Architecture/Security controls from LPAF v2.6
- Extends: ADR-008, ADR-031, ADR-032, ADR-043, ADR-047, ADR-051

## Context

The accepted product model separates Status, Event, Exception, Action, and Attention. Existing runtime has suitable Exception, WorkItem, OIP, Workspace, and Control Tower foundations, but no organization-owned no-default SLA rule, no pinned applied SLA commitment, and no manual bounded follow-up Action. Existing per-expert request deadlines and OIP threshold policies have different ownership and meaning and cannot be relabeled.

## Decision

1. Add `OrganizationSlaRule` as the tenant-owned configuration SOR. Only the two code-defined existing processes `EXCEPTION_RESPONSE` and `ACTION_FOLLOW_UP` are supported. Admin chooses duration, optional warning-before-breach, name, and active state; start/completion references and responsible fixed Shipment expert are code-defined and not customizable in this slice.
2. Add `OperationalSlaCommitment` to pin the effective rule version and timing to one existing source process. Rules are prospective; later edits/disablement do not rewrite a bound commitment.
3. Extend `OperationalWorkItem` with one `FOLLOW_UP` type and bounded fields for stable public identity, optional Exception/process context, expected result, latest follow-up, creator, and update time. It remains Shipment-rooted and fixed-owner scoped.
4. Extend `OperationalException` with optional impact/evidence summaries. Its open/resolved lifecycle and history remain unchanged; resolving it never completes another object.
5. Extend OIP with `ACTION_FOLLOW_UP` and `SLA_COMMITMENT_RISK`. OIP retains stable logical identity, evidence, history, freshness, rebuild, and advisory-only behavior. Source resolution factually clears Attention.
6. Adapt the existing operational reconciliation CLI for tenant-scoped catch-up/retry. No new service or deployment topology is introduced.
7. Workspace and Control Tower consume the same source/Attention facts after their existing authorization-first Shipment population. They cannot write SLA, Exception, Action, or Shipment truth.

## Time and status semantics

- Duration and optional warning are absolute elapsed minutes in UTC.
- Business calendars, pauses, exception clocks, templates, and mandatory defaults are unsupported and not inferred.
- Commitment evaluation states are `WITHIN`, `WARNING`, `BREACHED`, and `MET`.
- `WARNING` and `BREACHED` produce Attention only while the source process remains open. Completion preserves final evaluation/history and clears current Attention.
- Missing rule is represented as `NOT_CONFIGURED` / `SLA تعریف نشده`, never as healthy or zero duration.

## Authorization and transaction boundary

- Rule commands: exact Organization Admin authority, one active server-derived membership, current tenant only; optimistic version check and tenant-scoped audit.
- Action/Exception commands: existing Shipment authorization/capability plus fixed-owner scope. Action assignee is the Shipment's fixed responsible expert.
- Rule update, Action mutation, and Exception mutation are local database transactions with audit. Evaluation is an idempotent tenant transaction; OIP is a derived consumer.
- Platform Admin receives no implicit tenant operational management authority.

## Consequences

- One additive migration is required after `20260927_customer_portal_account_lifecycle`.
- Existing legacy SLA/request deadline and OIP threshold behavior is preserved and explicitly separate.
- Existing WorkItem route constraints are broadened only for `FOLLOW_UP`; all earlier route/milestone invariants remain intact.
- OIP and Control Tower gain approved source families but no operational mutation authority.
- Operator scheduling cadence must be configured through existing deployment operations; this candidate does not deploy or create a scheduler.

## Rejected

- relabeling `ExpertUser.sla_response_work_minutes`, `ShipmentRequest.sla_due_at`, or `OipThresholdPolicy` as the organization SLA SOR;
- browser-triggered-only evaluation;
- a new worker/service/queue topology;
- a separate Action or Attention v2 system;
- external-party assignee accounts, generic task management, hidden scores, AI, inferred durations, or retroactive rule rewriting.

