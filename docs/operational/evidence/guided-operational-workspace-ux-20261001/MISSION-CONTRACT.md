# Guided Operational Workspace — Mission Contract and Product Authority Record

## Governance entry

- **Mission date:** 2026-10-01
- **Repository:** Forwarder
- **Governed baseline:** LPAF v2.6 (frozen canonical baseline named by the repository `AGENTS.md`)
- **Baseline discrepancy:** The task brief names LPAF v2.7. That reference is non-governing for this mission because repository authority explicitly names v2.6. The brief remains authoritative for product intent and acceptance scope where it does not redefine the frozen baseline.
- **Entry level / route:** Level B product change, Sol route
- **Canonical product start SHA:** `96a9d52602febc6ab1b9d29e92e83fe3eb7e8dd5`
- **Audit evidence source:** `docs/operational/evidence/ux-system-wide-audit-20261001-96a9d526/`
- **Known validation state at entry:** Product validation = `EVIDENCE_PENDING`

## Outcome

Turn Forwarder into a clean, guided, progress-aware operational workspace that lets an expert understand a shipment in five seconds, exposes one justified next action, separates process stages from task readiness, and prioritizes operational exceptions without changing business semantics.

## In scope

- A shared, additive, read-only operational projection assembled from existing authoritative facts.
- Shipment identity, state, requested and operational route, process stages, task readiness, attention items, one recommended action, current operation, ETA/reason, latest update, and closure readiness.
- Expert home and shipment list priority/exception views using the same projection.
- Shipment detail summary-first hierarchy and reduced prominence of technical identifiers.
- Operate-first route/execution presentation with planning, finance, lifecycle, history, and technical detail under progressive disclosure.
- Human-facing labels and semantically grouped administration navigation.
- Closure verdict, progress, blockers, warnings, completed items, and a single dominant permitted close action.
- Focused automated, build, governance, and disposable-environment journey evidence.

## Out of scope

- New domain workflow, lifecycle status, transition, business fact, ranking authority, or source of truth.
- Schema or migration changes.
- Permission, role, tenant, ownership, or authorization-policy changes.
- Mutation of the preserved human-walkthrough runtime or database.
- Production operations, deployment, release publication, or release approval.
- Reinterpretation of historical governance records as current normative authority.

## Product Authority Record

### AUTHORIZED_PRODUCT_CHANGES

The user's 2026-10-01 mission brief authorizes the concrete UX transformation described above and the five stated priorities:

1. Shared operational projection, next action, and task readiness.
2. Five-second shipment summary.
3. Expert home and shipment list as priority exception queues.
4. Route/execution decomposition.
5. Administration information architecture and human-facing labels.

It also authorizes the supporting closure, responsive, accessibility, testing, evidence, controlled-integration, and push/fetch-verification work specified in the brief.

### DELEGATED_TECHNICAL_CHOICES

- Additive service and API shape for the read projection.
- Pure derivation and ranking from existing, server-authorized facts.
- Component boundaries, progressive-disclosure structure, responsive presentation, and copy within approved meaning.
- Test selection, fixture construction, disposable database use, and evidence packaging.
- Commit and controlled-integration mechanics after qualification.

### PROTECTED_BEHAVIORS

- Existing authentication, role, tenant, assignment, ownership, and capability enforcement.
- Existing domain lifecycle, legal transitions, route, cargo, document, tracking, delivery, exception, finance, and closure semantics.
- Existing system-of-record ownership and persisted data meaning.
- Existing write endpoints and server-side action authorization.
- Historical/audit evidence and the preserved walkthrough environment.
- Migration head `20261015_org_shipment_stages` and all database schema.
- Production, deployment, and release state.

### Derived-read-model controls

- The projection is not a source of record and persists no duplicated business truth.
- Every projected field names or is traceable to an existing authoritative source.
- The contract exposes projection version, calculation time, freshness/lag information, source inventory, and limitations.
- Rebuild semantics are on-request recomputation from source facts; no backfill is required.
- Server-side authorization scopes the shipment before facts are composed.
- A missing or unknown fact remains explicit and is never coerced to success, zero, or readiness.
- Closed shipments receive no actionable recommendation.

## Actors and authority boundaries

- **Expert:** sees and acts only within existing assigned-work authorization.
- **Operations/admin reader:** sees only the population permitted by existing capabilities; read access does not imply mutation access.
- **Customer:** remains outside internal operational surfaces and retains existing customer-safe projections.
- **Server:** remains the authorization boundary for reads and writes; the UI is not a security boundary.

## Journey impact declaration

- Impacted internal journeys: expert work queue, shipment discovery, shipment summary, route/execution, stage recording, supporting operational tasks, closure readiness, and administration configuration discovery.
- Existing write journeys are presented through new guidance but are not semantically changed.
- Customer/public journeys and their payload contracts are protected.
- Critical-journey membership is not expanded by this mission; changed internal journeys require focused regression and browser evidence.

## Definition of done

- A shared server-authorized projection drives the changed expert and operations surfaces.
- Shipment detail exposes human identity, process progress, task readiness, attention, current operation, and one next action without hiding important uncertainty.
- Home/list ordering makes urgent exceptions and stale work discoverable.
- Route and closure surfaces demonstrate clear operating hierarchy and progressive disclosure.
- Admin navigation is grouped by operational meaning and labels are human-readable.
- Focused tests, type checking, build, lint/governance checks, and disposable browser journeys are recorded truthfully.
- No protected behavior, schema, walkthrough state, production state, or release state is changed.
- Controlled integration occurs only after the qualification gate passes.

## Stop / escalate conditions

Stop and request product authority if implementation would require a new lifecycle state, persistence model, write authorization, business-rule interpretation, or priority rule not grounded in the mission brief and current domain truth. Stop integration if required evidence fails or if the canonical remote moves incompatibly during the mission.

## Entry decision

`AUTHORIZED_TO_PROCEED_WITHIN_SCOPE`

No product decision is outstanding at entry. The LPAF version discrepancy and known product-validation gap remain explicit evidence items; neither is silently normalized.
