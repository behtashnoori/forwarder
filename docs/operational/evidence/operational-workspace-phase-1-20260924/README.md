# Operational Workspace Phase 1 — governed mission and evidence

- Date: 2026-09-24
- Baseline: LPAF v2.6 — `ACTIVE / FROZEN / CANONICAL`
- Rigor / routing: Level B (Product), Sol; deterministic reconnaissance and verification may be decomposed with explicit handoff
- Owner / authority: Product Owner through the supplied mission `Forwarder — Operational Workspace Phase 1`
- Mission type: product-approved bounded reimplementation; no Production

## Entry gate and candidate identity

The implementation parent was revalidated before this worktree was created:

- Golden ancestor: `0837172e04ef8cafa0098f0935999fe73569bb85` on `integration/golden-controlled`
- verified safe parent: `D:\1-webapp\forwarder-dev\customer-account-governed-remediation`
- safe parent branch / HEAD: `codex/customer-account-governed-remediation` / `fbc0c1156eb08ac8f2b287320dda67df8ee4c9bd`
- parent state: clean; Golden ancestry proven; exactly two governed Customer Account commits above Golden
- Alembic state: one head, `20260927_customer_portal_account_lifecycle`
- isolated worktree: `D:\1-webapp\forwarder-dev\operational-workspace-phase-1-clean`
- implementation branch: `codex/operational-workspace-phase-1-clean`
- donor: `D:\1-webapp\15-forwarder`, read-only reference only; no donor history merge or wholesale file replacement

## Mission contract

Outcome: let a Transport Expert enter a normal Operational Workspace, understand the current authorized active-Shipment picture and bounded existing follow-ups, open an existing Shipment detail/history, and return to the Workspace.

In scope:

- live authorized Workspace snapshot and active-Shipment filtering;
- existing open operational follow-ups as explainable Attention signals;
- existing reliable route/current/latest-update context;
- `/operations` entry, navigation, loading/empty/error/denied states, Shipment navigation and return;
- fixed responsible Transport Expert display from the Shipment-owned field;
- preservation regressions for Customer Account and Public Tracking.

Out of scope:

- Request/Shipment lifecycle redesign, automatic Shipment creation, role or status redesign;
- new SLA thresholds, scoring, background evaluation, AI, Control Tower expansion, finance, carrier/driver portal, or generic task management;
- database/schema/migration change, Production, deployment, release, push, or Phase 2.

Stop conditions: unproven source lineage; a required schema/migration change; a new or changed PDA-01 behavior; a conflict with fixed Shipment ownership; inability to prove tenant-safe current authorization; or missing required browser evidence.

Definition of Done: all mission flags have candidate-bound evidence; the normal target-role browser journey and negative authorization cases pass on an isolated synthetic PostgreSQL environment; full regressions/static checks pass; Product Authority reconciliation has no `VIOLATION` or `UNKNOWN`; worktree is committed and clean.

## FACT / ASSUMPTION / UNKNOWN / DECISION_NEEDED

`FACT`:

- Request and Operational Shipment are separate; Customer acceptance does not create a Shipment automatically; one Request may lead to multiple Shipments.
- `OperationalShipment.primary_responsible_expert_id` is the immutable Shipment owner SOR. Request reassignment neither changes that owner nor grants the new Request assignee Shipment access.
- current collection authorization is expressed by the server-side governed Operational Shipment population and current assigned-work authorization.
- `OperationalWorkItem` already represents bounded operational follow-up facts; `MilestoneEvent` and authoritative operational reads already provide event history.
- Customer Account, anonymous Request, private Quote workspace/recovery, CRM separation, and ADR-052 Public Tracking are present in the safe parent and protected.

`ASSUMPTION`:

- a request-time, non-persistent projection composed from the authorized Shipment population, existing open WorkItems, and existing event reads can provide Phase 1 value without creating a parallel SOR.
- `planned` and `in_progress` are the current non-terminal Shipment lifecycle statuses; `completed` and `cancelled` are terminal for the bounded active filter.

`UNKNOWN`:

- global LPAF Product validation remains `EVIDENCE_PENDING`; this mission can complete evidence only for this bounded Forwarder slice.

`DECISION_NEEDED`: none at entry. If implementation needs a schema change, an invented SLA/urgency rule, Request-derived Shipment ownership, or adjacent Product redesign, stop that affected work.

## Product Authority Record

`AUTHORIZED_PRODUCT_CHANGES`:

- implement Operational Workspace Phase 1 exactly within the supplied mission: normal expert entry, today overview, active authorized Shipments, bounded existing-fact Attention, current Shipment context, existing detail/history navigation, and return to Workspace.

`DELEGATED_TECHNICAL_CHOICES`:

- read-projection/service shape, query composition, response contracts, component composition, loading/empty/error presentation, bounded refactoring, synthetic fixtures, test organization, and evidence capture, provided all protected behavior and architecture contracts remain unchanged.

`PROTECTED_OUT_OF_SCOPE_BEHAVIOR`:

- Request and Shipment remain separate; Customer acceptance creates no Shipment automatically; one Request may create multiple Shipments.
- fixed Shipment ownership remains `OperationalShipment.primary_responsible_expert_id`; mutable Request assignment does not transfer it.
- current roles, lifecycle/status meaning, write authority, Customer Account, anonymous Request, private Customer Request/Quote behavior, password lifecycle/recovery, organization-scoped account administration, Public Tracking privacy, CRM/portal identity separation, Quote authority, existing detail/history, Control Tower, and Work Queue permission semantics remain unchanged.
- no Production, schema/migration, SLA engine, AI, finance, carrier/driver portal, or Phase 2.

`DECISIONS_NEEDED`: none at entry; future carrier/driver, customs, finance, official event catalog, SLA templates/thresholds, and deeper data-ownership decisions remain open and are not resolved here.

`APPROVING_OWNER_OR_AUTHORITY`: Product Owner; LPAF v2.6 governs authority and evidence boundaries.

`APPROVAL_REFERENCE`: supplied mission `Forwarder — Operational Workspace Phase 1 — Clean Reimplementation on the Accepted Current Product Base`, plus the approved product references added under `docs/product/`.

## Ownership, SOR, data scope, and chain

- Shipment identity/status/fixed owner/customer: `OperationalShipment` and its current authorized graph; transactional organization data.
- route/current context: active `RoutePlan`, ordered `RouteLeg`, `Milestone`, and existing authoritative occurrence projections; transactional organization data.
- latest/history facts: `MilestoneEvent` and existing event views, preserving occurred-at versus recorded-at.
- bounded follow-up fact: open `OperationalWorkItem`; the Workspace adds no independent lifecycle or mutation.
- Workspace projection: request-time, versioned, non-persistent read composition; current authorization is reapplied on every request; no cache, snapshot table, or background job.

Domain chain:

`authenticated active actor -> exactly one current tenant context -> operational_shipment.read -> authorized Shipment population -> active lifecycle filter -> existing WorkItem/Event facts -> bounded Workspace response -> Shipment detail/history`.

All counts, ordering, and returned rows must be derived only after the same current authorization scope. Client input cannot select organization, owner, or hidden population.

## Product journey and authorization contract

Target actor: Transport Expert.

Normal journey:

`login -> /operations -> today overview -> attention/active Shipment -> /operations/shipments/{opaque-id} -> existing context/history -> return to /operations`.

Required states: loading, honest empty, generic error with retry, denied, current snapshot time/limitations, and safe return. Absence of follow-ups is not presented as SLA health.

Authorization chain:

`UI visibility -> authentication -> current authority/membership -> operational_shipment.read -> tenant + fixed-owner/current governed scope -> API authorization -> source Shipment/WorkItem/Event facts`.

UI visibility grants no authority. Known identifiers, WorkItem assignment, Request reassignment, cached responses, and old navigation state grant no Shipment access.

## Reference impact

| Reference | Result | Action |
| --- | --- | --- |
| canonical LPAF v2.6 | `NONE` | apply unchanged; do not modify canonical workspace |
| Forwarder product references | `UPDATE_REQUIRED` | add the approved Operational Model and Workspace Product Design without changing their meaning |
| Forwarder architecture baseline / ADRs | `NONE` expected | reuse existing Shipment, fixed-owner, authorization, WorkItem, event, and projection contracts; no ownership/SOR/boundary change |
| repository agent entry | `UPDATE_REQUIRED` | add minimal `AGENTS.md` naming v2.6 and PDA-01 through PDA-08 |

## Verification plan

- focused backend: authentication/permission denial, tenant isolation, fixed-owner scope, Request-reassignment preservation, active filter, route/latest update, open-follow-up derivation, empty/validation cases;
- focused frontend: route/login/nav, loading, populated/empty, error/denied/retry, active list, detail/history navigation and return;
- preservation: Customer Account, anonymous Request, private Quote/history/response/recovery/admin scope, CRM/portal separation, and ADR-052 Public Tracking;
- complete backend and frontend suites; lint; TypeScript; production build; compile/static checks; sole Alembic head; architecture governance; `git diff --check`; changed-scope secret scan where available;
- isolated synthetic PostgreSQL migration/runtime and normal browser journey, including empty, unauthorized, cross-organization, fixed-owner, Customer Account and Public Tracking preservation.

## Implemented bounded slice

- Added authenticated, permission-gated `GET /api/operational-workspace`, implemented as a non-persistent request-time projection over the currently authorized Shipment population.
- The Workspace defaults to active Shipments and supports the strictly validated `active=true|false` filter. It exposes only minimized route/current context, latest authoritative event facts, and bounded open WorkItems that the actor may read.
- Attention entries are stable, explainable links to existing source facts. The projection creates no new SLA, urgency score, task lifecycle, background evaluation, or SOR.
- Fixed Shipment ownership is read only from `OperationalShipment.primary_responsible_expert_id`. Request reassignment neither transfers ownership nor grants Shipment visibility.
- Added the protected `/operations` entry, normal Transport Expert login fallback, Workspace navigation, overview, active/all Shipment view, Shipment context/history navigation and safe return, plus honest loading, empty, denied, and retryable error states.
- Existing Shipment list/detail behavior is preserved and now displays the fixed owner and latest update without changing write authority.
- No database model, schema, migration, Product Decision Authority behavior, Production system, or adjacent Control Tower/AI/finance/carrier scope was changed.

Candidate identity:

- approved product-reference commit: `e7590a7e776a8b4c4261862acc1d3d2f2457087b`
- exact implementation candidate: `1c93abb375c59bae650bbc11fb70b8cf4b3ecc9f`
- candidate parent: `fbc0c1156eb08ac8f2b287320dda67df8ee4c9bd`

## Product Authority reconciliation

| Classification | Candidate result | Evidence / disposition |
| --- | --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | `PASS` | Workspace endpoint/UI, active Shipment view, bounded fact-based Attention, fixed-owner display, existing Shipment context/history navigation, and return journey were implemented within the approved mission. |
| `DELEGATED_TECHNICAL_CHOICES` | `PASS` | Request-time projection, additive response contract/components, isolated synthetic fixtures, and candidate-bound tests remain within delegated implementation authority. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | `PASS` | Request/Shipment separation, fixed Shipment owner, authorization/tenant boundaries, Customer Account, anonymous Request, Public Tracking, CRM/portal separation, Control Tower and Work Queue semantics are preserved. |
| `VIOLATION` | `NONE` | No protected behavior, SOR, ownership, role, lifecycle, schema, or Production boundary was changed. |
| `UNKNOWN` for this slice | `NONE` | All bounded mission acceptance claims have candidate-bound automated and browser evidence. Global LPAF Product validation remains independently `EVIDENCE_PENDING`. |
| `DECISIONS_NEEDED` | `NONE` for Phase 1 | Carrier/driver, customs, finance, official event catalog, SLA templates/thresholds, and deeper data ownership remain deliberately open for a separately approved Phase 2. |

## Candidate-bound qualification evidence

| Gate | Result | Candidate evidence |
| --- | --- | --- |
| full backend regression | `PASS` | `1362 passed, 106 skipped`; zero failures; executed after the final route-minimization change on candidate `1c93abb375c59bae650bbc11fb70b8cf4b3ecc9f` |
| focused backend preservation | `PASS` | 89 tests passed across Workspace/fixed-owner, Customer Account, recovery, gamification, Quote, and Public Tracking contracts; affected Workspace/vertical-slice rerun: 26 passed |
| full frontend regression | `PASS` | 76 files / 377 tests passed on the final application code |
| focused frontend qualification | `PASS` | 9 files / 65 tests passed for routing, auth continuity, Workspace states, Shipment list/detail, and protected regressions |
| lint / type safety / build | `PASS` | ESLint: zero errors (13 pre-existing warnings); application TypeScript: pass; node TypeScript: pass; production build: pass |
| static / architecture | `PASS` | Python compileall, architecture-governance script, architecture-governance pytest, and repository structure check passed |
| migration contract | `PASS` | one exact Alembic head: `20260927_customer_portal_account_lifecycle`; migration diff from safe parent is empty |
| changed-scope secret scan | `PASS` | mission diff has zero findings with redaction enabled; two redacted fingerprints in production scripts are identical pre-existing safe-parent findings and were not touched |
| browser product journey | `PASS` | 5 Playwright/Chrome scenarios passed in 40.3 s against owned disposable PostgreSQL 18, migrated to the exact head, with cleanup `PASS` |
| database / Production boundary | `PASS` | synthetic data only; no schema/migration change; Production was neither accessed nor mutated; no deployment or release performed |

Browser artifacts:

- `browser/workspace-overview.png` — normal expert overview and explainable Attention.
- `browser/shipment-context-history.png` — authorized Shipment context with loaded existing history.
- `browser/workspace-empty.png` — honest permission-limited/empty state.
- `browser/result.json` — machine-readable candidate, runtime, migration, privacy, and journey result.

The browser proof covers: expert login and Workspace entry; overview/Attention; Shipment context and actual history; safe return and active/all filter; Request reassignment without owner transfer; same-organization and cross-organization denial; empty and injected temporary-error states; Customer Account private Request/Quote history/response/recovery/organization administration; capability-only minimized Public Tracking; numeric-ID rejection; and anonymous Request creation.

## Final qualification state

- Engineering Complete: `PASS`
- Product Complete for this bounded slice: `COMPLETE`
- Release Ready: `NOT_APPLICABLE` — no release authority
- Release Complete: `NOT_APPLICABLE` — no Production/deployment authority
- Product Authority reconciliation: `PASS`; no `VIOLATION` or slice-local `UNKNOWN`
- Global LPAF Product validation: `EVIDENCE_PENDING` (unchanged; not silently redefined by this slice)
- Database/migration change: `NO`
- Reference impact: `UPDATE_REQUIRED`, satisfied by adding the approved product references and v2.6 repository entry instructions on the correct line
- Phase 2: `NOT_STARTED`

## Successor compatibility status — Phase 2

This is a current successor-status addendum, not a rewrite of the historical Phase 1 evidence above. The original Phase 1 candidate, migration head, test counts, reference result, and `Phase 2: NOT_STARTED` statement remain the facts recorded when Phase 1 was qualified.

- Historical Phase 1 candidate: `1c93abb375c59bae650bbc11fb70b8cf4b3ecc9f`.
- Current qualified Phase 2 Product HEAD: `4129badaad5bb4a425cd4685b6a15c81db11f5e1`.
- Current sole migration head: `20260928_operational_workspace_phase2` (head count `1`).
- The current Phase 1 runner and seed retain their original owned `forwarder_workspace_phase1_*` boundary and also permit the Phase 2 runner's owned `forwarder_workspace_phase2_*` database so the same protected journeys can be re-used without changing their meaning.
- The combined Google Chrome qualification on 2026-09-24 re-executed all five Phase 1 scenarios against the exact Phase 2 Product HEAD and PostgreSQL 18; fixed Shipment owner, tenant isolation, empty/error states, Customer Account, Public Tracking, Request/Shipment separation, numeric-ID rejection, and anonymous Request creation all passed.
- `PHASE1_COMPATIBILITY_REFERENCE_STATUS=CURRENT`.
