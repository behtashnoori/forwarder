# Operational Workspace Phase 2 — governed mission contract

- Date: 2026-09-24
- Baseline: LPAF v2.6 — `ACTIVE / FROZEN / CANONICAL`
- Lifecycle: M0 Mission through M6 Verify; no Release, deployment, Production, or Operate claim
- Rigor / routing: Level B (Product), Sol
- Owner / authority: Product Owner through the supplied mission `Forwarder — Operational Workspace Phase 2`
- Candidate parent: `97edd38d752259f0babcf8f43867b028511c874d`
- Branch / worktree: `codex/operational-workspace-phase-2` / `D:\1-webapp\forwarder-dev\operational-workspace-phase-2`

## Outcome, scope, and stop conditions

Outcome: let an Organization Admin configure explicit organization SLA rules for supported existing processes, and let the responsible Transport Expert understand deterministic, source-linked SLA, Exception, Action, and Attention facts in the existing Workspace. Existing Control Tower reads the same governed truth without becoming a writer or parallel System of Record.

In scope:

- prospective, organization-owned SLA rules with no default durations;
- SLA binding only for `EXCEPTION_RESPONSE` and `ACTION_FOLLOW_UP`, whose start and completion facts already exist and are unambiguous;
- durable rule-version binding and deterministic elapsed-time evaluation;
- evolution of existing Exception and WorkItem models for bounded impact/evidence/follow-up information;
- OIP extension for SLA risk and Action follow-up Attention;
- Workspace Phase 2 presentation and bounded Control Tower read integration;
- tenant, fixed-owner, and source-permission enforcement;
- one additive migration and candidate-bound tests/evidence.

Out of scope: every protected behavior in the supplied mission, including role/lifecycle changes, automatic Shipment creation, customer/portal/CRM/Quote/Public Tracking changes, finance, AI, Carrier/Driver portals, Customs workflow, generic task management, official Event catalog, new deployment service, Production, deployment, and Phase 3.

Stop the affected work for any new role, lifecycle state, external-party identity/workspace, Customs/finance/Event meaning, protected behavior change, or independently deployed scheduler/service.

Definition of Done: required journeys and tenant/fixed-owner boundaries pass in an owned synthetic PostgreSQL/browser environment; full regressions/static/build/migration/governance gates pass; every material behavior is reconciled to authority; commits are bounded and the worktree is clean.

## FACT / ASSUMPTION / UNKNOWN / DECISION_NEEDED

`FACT`:

- `OperationalException` is the current exception truth and preserves create/resolve timestamps, governed reason, optional milestone context, actor, version, and audit.
- `OperationalWorkItem` is the existing bounded follow-up truth, but currently supports only route/milestone-generated work.
- OIP provides stable tenant-scoped Situation identity, evidence links, human interaction history, source watermarks, freshness, rebuild, and idempotent reconciliation.
- Workspace Phase 1 is a request-time authorized projection; Control Tower is a read model over domain-owned facts.
- `ExpertUser.sla_response_work_minutes` and `ShipmentRequest.sla_due_at` are legacy per-expert/request behavior with a mandatory default and are not organization SLA rules.
- `OipThresholdPolicy` governs only existing OIP overdue/staleness signal tolerances and is not a complete organization SLA rule.
- the repository has an explicit restart-safe reconciliation CLI; no independently deployed scheduler service exists.

`ASSUMPTION`:

- prospective effective-time rules and pinned commitments are the least-surprising history-preserving interpretation: a rule applies only to a process starting at or after its effective time; later edits/disablement do not rewrite already bound commitments.
- absolute elapsed UTC minutes are sufficient for this bounded slice; business calendars, pause clocks, and template catalogs remain unimplemented rather than inferred.
- the existing operator-scheduled reconciliation command is an accepted deployment mechanism; this slice adds no service or topology.

`UNKNOWN`:

- global LPAF Product validation remains `EVIDENCE_PENDING`.
- actual Production scheduler cadence and organization values are not known and are not configured by this mission.

`DECISION_NEEDED`: none at entry for this bounded slice. Unsupported SLA processes, calendars/pauses/templates, external assignees, new roles or lifecycle meanings remain stopped pending a future explicit decision.

## Product Authority Record

`AUTHORIZED_PRODUCT_CHANGES`:

- organization-managed SLA framework and evaluation against recorded facts;
- governed Exception experience;
- lightweight operational Action/follow-up;
- stronger deterministic Attention;
- Workspace Phase 2 presentation;
- bounded Control Tower read integration.

`DELEGATED_TECHNICAL_CHOICES`:

- internal modules/services, additive persistence shape, transaction structure, prospective effective-time/version pinning, absolute elapsed-time evaluation, CLI reconciliation, read projections, tests, and synthetic fixtures.

`PROTECTED_OUT_OF_SCOPE_BEHAVIOR`:

- all items in mission section 5 and 22;
- fixed Shipment owner remains `OperationalShipment.primary_responsible_expert_id`;
- Request/Shipment separation, existing lifecycle/status meaning, customer/tenant authorization, and current adjacent product behavior remain unchanged;
- existing legacy request deadline and OIP threshold behavior remain compatible but do not become Phase 2 SLA truth.

`DECISIONS_NEEDED`: none for the two supported processes; all unsupported SLA process bindings and listed stop conditions remain future decisions.

`APPROVING_OWNER_OR_AUTHORITY`: Product Owner through the supplied Phase 2 mission; LPAF v2.6 for governance and authority boundaries.

`APPROVAL_REFERENCE`: the supplied `Forwarder — Operational Workspace Phase 2` mission, `FORWARDER-OPERATIONAL-MODEL-V1-FA.md`, and `FORWARDER-OPERATIONAL-WORKSPACE-PRODUCT-DESIGN-V1-FA.md`.

## Foundation disposition

| Foundation | Disposition | Reason |
| --- | --- | --- |
| `OperationalException` | `EXTEND` | Keep its identity/lifecycle; add bounded impact/evidence fields and expose linked Action/SLA facts. |
| `OperationalDelay` | `REUSE` | Remains a separate existing Attention source; delay is not made a lifecycle status or automatically reclassified as Exception. |
| `OperationalWorkItem` | `EXTEND` | Add one `FOLLOW_UP` type and bounded context/result/history fields; do not create a generic task domain. |
| OIP Situation/Signal/Fact/Attention | `EXTEND` | Add approved `ACTION_FOLLOW_UP` and `SLA_COMMITMENT_RISK` families; preserve stable identity, history, freshness, recovery, and no mutation authority. |
| `OipThresholdPolicy` | `REUSE` for its existing signals only | It remains the configured tolerance for existing overdue/stale signals; it is not relabeled as organization SLA. |
| `ExpertUser.sla_response_work_minutes` / `ShipmentRequest.sla_due_at` | `DO_NOT_USE` for Phase 2 | Mandatory per-expert default and legacy request deadline semantics conflict with organization-owned, no-default SLA rules. Preserve compatibility. |
| document readiness / milestone and route timing | `REUSE` as existing Attention facts | No new SLA binding is invented for them in this slice. |
| `operational_cli` reconciliation | `ADAPT` | Add tenant-scoped SLA/Attention evaluation to the restart-safe, externally schedulable existing command boundary. |
| Workspace Phase 1 projection | `EXTEND` | Consume authorized OIP/SLA/Exception/Action facts and expose reasons/freshness. |
| Control Tower read model | `EXTEND` | Read the same Action and SLA sources; never own or mutate them. |

## Supported SLA process catalog

| Process code | Start fact | Completion fact | Subject / owner | Rule applicability |
| --- | --- | --- | --- | --- |
| `EXCEPTION_RESPONSE` | `OperationalException.occurred_at` | `OperationalException.resolved_at` | related Shipment / fixed responsible Transport Expert | organization rule active and effective no later than the start fact |
| `ACTION_FOLLOW_UP` | `OperationalWorkItem.created_at` for `FOLLOW_UP` | `OperationalWorkItem.resolved_at` | related Shipment / fixed responsible Transport Expert | organization rule active and effective no later than the start fact |

No configured rule means `SLA تعریف نشده`; no fallback or inferred duration is applied. Rule edit/disable is prospective. A created commitment pins rule identity, version, duration, warning configuration, start, and deadline so later configuration does not rewrite history.

## Ownership, SOR, data scope, and chains

- Organization SLA rule SOR: `OrganizationSlaRule`; Organization/Tenant Master data; Organization Admin write authority.
- Applied SLA commitment SOR: `OperationalSlaCommitment`; transactional/historical evidence binding one rule version to one existing process fact.
- Exception SOR: existing `OperationalException`; Action SOR: existing `OperationalWorkItem` with `FOLLOW_UP`.
- Attention SOR: none; OIP is the durable derived projection/history over the above sources.
- Workspace and Control Tower remain read models and reapply current authorization.

Domain chain:

`Organization Admin -> tenant-scoped rule command -> versioned rule + audit -> eligible existing process fact -> pinned SLA commitment -> deterministic evaluation -> OIP fact/signal/situation -> authorized Workspace / Control Tower -> source drilldown`.

Action chain:

`fixed-owner authorized Shipment -> bounded FOLLOW_UP command -> WorkItem + audit -> OIP Attention -> Workspace / Control Tower -> follow-up/result command -> WorkItem audit/history -> factually cleared Attention`.

## Time evaluation and recovery contract

- Command: tenant-scoped `evaluate-sla --organization-id ... --confirm` on the existing operational CLI boundary.
- Scheduling: external host scheduler invokes the idempotent command; no browser, new worker, queue, daemon, or service is introduced.
- Catch-up: every run discovers all eligible source processes and reevaluates all pinned open commitments, so missed runs and restarts recover on the next invocation.
- Retry: a failed transaction rolls back; rerunning the same tenant/time produces no duplicate commitment or logical Attention identity.
- Deduplication: database uniqueness for source commitment plus OIP tenant/subject/condition identity and signal watermark.
- Freshness/observability: evaluation timestamps, source/rule versions, OIP projection health, last success/failure, and explicit stale/degraded UI state.
- Production cadence/configuration remains an operator/release concern and is not changed here.

## Authorization and user journeys

- SLA management requires authenticated `ORGANIZATION_ADMIN` plus exactly one server-derived active tenant membership. Platform Admin without that authority/membership is denied. Client organization IDs are ignored as authority.
- Transport Expert reads/mutates only fixed-owner authorized Shipments. Action assignment in this slice is pinned to that same fixed owner; no external or independent assignment authority is introduced.
- Attention is filtered by the authorized Shipment population before counts, ordering, pagination, and disclosure, then by the underlying source permission.
- Control Tower reapplies its existing authorization-first population and only reads governed source facts.

Journeys:

1. Organization Admin: login -> Admin -> SLA rules -> create/edit/disable own rule -> history visible -> foreign tenant denied.
2. Transport Expert healthy: login -> Workspace -> applicable commitment is within time -> SLA shown, no false Attention.
3. Transport Expert warning/breach: configured rule + recorded fact -> scheduled evaluation -> explainable source-linked Attention.
4. Exception: Shipment -> create/view impact/evidence -> optional Action -> resolve -> history preserved; no implicit Shipment/Action/SLA completion.
5. Action: Shipment/Exception -> create fixed-owner follow-up -> record latest follow-up -> resolve with result; no generic task taxonomy.
6. Control Tower: same Action/SLA signal appears as a read-only reason and drills into Shipment truth.

## Reference impact

| Reference | Result |
| --- | --- |
| canonical LPAF v2.6 | `NONE` — applied unchanged |
| Forwarder Product references | `NONE` expected — mission implements already approved meaning |
| Forwarder architecture | `UPDATE_REQUIRED` — ADR-054 records the bounded SLA/Action/OIP extension |

