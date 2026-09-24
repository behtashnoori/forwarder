# Operational Monitoring Reliability Phase 2.5 — governed mission contract

- Date: 2026-09-24
- Baseline: LPAF v2.7 — `ACTIVE / FROZEN / CANONICAL`
- Lifecycle: M0 Mission through M6 Verify; no Release, deployment, Production, or Operate claim
- Rigor / routing: Level B (Product), Sol
- Owner / authority: Product Owner through the supplied mission `Forwarder — Operational Monitoring Reliability Phase 2.5`
- Candidate parent: `1df5e26475e3de44894c248c6bf74a602b008656`
- Branch / worktree: `codex/operational-monitoring-reliability-phase-2-5` / `D:\1-webapp\forwarder-dev\operational-monitoring-reliability-phase-2-5`

## Outcome, scope, and stop conditions

Outcome: make the accepted Phase 2 SLA, Exception, Action, and Attention evaluation dependable without an open browser. A missed run must catch up from current authoritative facts, retries and overlap must be safe, and Workspace plus Control Tower must disclose whether the derived Attention result is trustworthy.

In scope:

- reuse the existing externally schedulable `backend.operational_cli evaluate-sla` boundary;
- tenant-scoped catch-up from all eligible current facts and pinned commitments;
- stable Attention identity, idempotent repeated evaluation, and bounded run fencing;
- honest failure, abandoned-run recovery, last-attempt/last-success evidence, duration and count-level run evidence;
- clock-aware projection freshness using the already accepted absolute elapsed UTC semantics;
- bounded Workspace and Control Tower freshness presentation over one OIP health truth;
- operator status inspection and PostgreSQL 18/browser/regression qualification.

Out of scope: a new service or deployment topology, scheduler installation, Production access, deployment, Product cadence promises, business calendars or pauses, new SLA meanings/defaults/templates, Notification activation, AI, Finance, Customs redesign, Carrier/Driver portals, Phase 3, role/lifecycle changes, and Customer Account/Public Tracking/Quote behavior.

Stop the affected work if reliable evaluation requires a new independently deployed component, a business-calendar decision, a user-visible freshness commitment, or any protected Product behavior change.

Definition of Done: the required A–J qualification scenarios pass against owned synthetic data, PostgreSQL 18 and browser evidence; full backend/frontend/static/build/governance gates pass; the candidate is committed in bounded commits and the worktree is clean.

## LPAF v2.7 journey impact and acceptance boundary

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`.

The affected existing journeys are Transport Expert Workspace, Attention
consumption, and Control Tower operational attention/freshness. Phase 2.5 adds
no actor or primary workflow; it changes the reliability and freshness behavior
visible inside those already-approved journeys.

The rebased Product candidate requires a candidate-bound Slice Journey rerun.
Whole-Product integrated journeys and the authorized Human Product Walkthrough
remain separate pre-release gates and are not part of this canonical integration
mission. Therefore this mission preserves:

- `INTEGRATED_PRODUCT_JOURNEYS=NOT_YET_RUN_PRE_RELEASE`;
- `HUMAN_PRODUCT_WALKTHROUGH=NOT_YET_RUN_PRE_RELEASE`;
- `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`;
- `RELEASE_READY=NO`.

## FACT / ASSUMPTION / UNKNOWN / DECISION_NEEDED

`FACT`:

- canonical and approved remote are aligned at `1df5e26475e3de44894c248c6bf74a602b008656`; the sole Alembic head is `20260928_operational_workspace_phase2`;
- Phase 2 already supplies organization-owned no-default SLA rules, pinned commitments, bounded Action, Exception, stable OIP identity, tenant-scoped reconciliation CLI, and OIP health states `FRESH`, `STALE`, `REBUILDING`, `DEGRADED`;
- the current CLI is browser-independent and guarded by explicit organization plus `--confirm`;
- the current source watermark observes row counts/maxima but not a time threshold crossing; a due time can pass with no persisted source mutation while health still reports `FRESH`;
- the current run writes `REBUILDING` before work and rejects every later run while that state remains; process loss after the start commit can therefore strand recovery;
- Workspace reads persisted health but Control Tower does not expose the shared Attention evaluation health;
- current health history has run identity and transition time but no count/duration detail.

`ASSUMPTION`:

- the existing host scheduler remains the accepted invocation mechanism; this mission supplies a reliable idempotent job command but does not install or promise a cadence;
- a PostgreSQL session advisory lock held for the whole evaluation is the least-complex existing-database fence; loss of the process releases it;
- projection freshness can be exact without inventing a cadence by persisting the earliest already-governed time boundary that can change derived output;
- one additive migration extending existing OIP health persistence is necessary for trustworthy time freshness and recoverable run metrics.

`UNKNOWN`:

- Production scheduler cadence, Production configuration, and Production runtime identity are unknown and not inspected;
- global LPAF Product validation remains `EVIDENCE_PENDING`.

`DECISION_NEEDED`: none for the bounded implementation. Business calendars, pauses, Product freshness promises, new SLA processes, and any new runtime service remain deliberately unresolved and unimplemented.

## Product Authority Record

`AUTHORIZED_PRODUCT_CHANGES`:

- reliable browser-independent evaluation of existing SLA/Action/Attention facts;
- idempotent retry and catch-up;
- evaluation health/freshness visibility;
- bounded Workspace and Control Tower stale/degraded indication;
- operator-safe evaluation and status inspection.

`DELEGATED_TECHNICAL_CHOICES`:

- evaluation service structure, PostgreSQL fencing, health persistence, clock-boundary calculation, CLI/status shape, internal failure handling, tests, and synthetic fixtures.

`PROTECTED_OUT_OF_SCOPE_BEHAVIOR`:

- Organization Admin remains the owner of organization SLA configuration and no default SLA duration is inferred;
- Exception remains distinct from Shipment status; Action remains bounded follow-up rather than generic task management; Attention remains derived;
- fixed Shipment owner remains `OperationalShipment.primary_responsible_expert_id`;
- Control Tower remains read-only and consumes domain/OIP truth rather than becoming a SOR;
- Request and Shipment remain separate; Customer Account, Public Tracking, Quote, lifecycle and role behavior remain unchanged;
- no business calendar, AI, Finance, Customs redesign, Notification activation, Carrier/Driver portal, Phase 3, Production access, deployment, or new Production service.

`DECISIONS_NEEDED`: business-calendar semantics and any user-visible freshness service commitment remain open and are not required by this implementation.

`APPROVING_OWNER_OR_AUTHORITY`: Product Owner through the supplied Phase 2.5 mission; LPAF v2.7 for governance and authority boundaries.

`APPROVAL_REFERENCE`: the supplied `Forwarder — Operational Monitoring Reliability Phase 2.5` mission, the accepted Phase 2 contract/evidence, `FORWARDER-OPERATIONAL-MODEL-V1-FA.md`, and `FORWARDER-OPERATIONAL-WORKSPACE-PRODUCT-DESIGN-V1-FA.md`.

## Existing background foundation disposition

| Foundation | Disposition | Evidence / boundary |
| --- | --- | --- |
| OIP reconciliation | `EXTEND` | Existing `oip_service.reconcile` remains the single evaluator; add full-run fencing, abandoned-run recovery, honest metrics and clock-aware health. |
| Scheduler hooks | `REUSE` | The accepted external host scheduler invokes the CLI; this mission installs no scheduler and makes no cadence promise. |
| Background workers / startup jobs | `NOT_APPLICABLE` | No accepted worker/daemon exists and none is introduced. Application startup remains free of evaluation work. |
| Operational CLI | `EXTEND` | Keep tenant-targeted `evaluate-sla --organization-id ... --confirm`; add read-only evaluation status. |
| Outbox processing | `NOT_APPLICABLE` | Existing outbox is not the Phase 2 evaluation owner and is not repurposed. |
| Retry utilities | `ADAPT` | Retry is safe by stable identities, transactions and the external next invocation; no unbounded in-process retry loop. |
| OIP projection health | `EXTEND` | Reuse exactly `FRESH`, `STALE`, `REBUILDING`, `DEGRADED`; add precise time-boundary freshness and run evidence. |
| Watermark / freshness | `EXTEND` | Replace aggregate maxima with an exact ordered identity/version fingerprint and persist the next governed time boundary. |
| Locking / claim fencing | `EXTEND` | Keep per-identity and transaction locks; add one PostgreSQL session advisory guard held for the complete organization run. |
| Idempotency | `REUSE` | Source commitment uniqueness plus tenant/subject/condition identity and signal watermark remain authoritative deduplication. |
| Health / readiness diagnostics | `ADAPT` | OIP status remains the canonical Attention health boundary; Workspace, Control Tower and CLI consume the same sanitized tenant-level contract. Global process readiness is not redefined. |

## Ownership, SOR, time, and recovery

- Operational facts, SLA rules/commitments, Exception and Action remain their existing SORs. OIP is a derived read model; Workspace and Control Tower are consumers.
- One run targets exactly one organization and never returns tenant counts or identities outside that target.
- Occurred/start/due/completed times remain source facts. `evaluated_at` and first detection remain the actual later observation time during catch-up; no historical observation is fabricated.
- A full-run database advisory fence rejects a live overlap. If the prior process disappeared, the released fence permits a later run to record the abandoned attempt as degraded and recover.
- A failure rolls back the derived transaction, persists a sanitized degraded result in a separate recovery transaction, and exits non-zero. No automatic retry storm is added.

## Verification and reference impact

Required evidence is candidate-bound: focused unit/integration tests, PostgreSQL 18 clean upgrade and downgrade/re-upgrade, concurrent execution, failure/retry, catch-up and tenant isolation, full backend/frontend regressions, TypeScript, ESLint, production frontend build, architecture/structure/governance checks, `git diff --check`, and browser evidence for current Attention plus Workspace and Control Tower stale/degraded behavior.

Provisional reference impact:

- canonical LPAF v2.7: `NONE`;
- Forwarder project architecture and Phase 2 reliability contract: `UPDATE_REQUIRED` for the bounded health/fencing decision and final evidence;
- OpenAPI and tenant/migration inventories: `UPDATE_REQUIRED` only where the implemented response/persistence contract changes.
