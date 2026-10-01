# Guided Operational Workspace — Mission Contract and Product Authority Record

## Governance entry

- **Mission date:** 2026-10-01 (Asia/Tehran)
- **Repository:** Forwarder
- **Governed baseline:** `LPAF v2.7 — ACTIVE / FROZEN / CANONICAL`
- **Authority resolution:** tracked `AGENTS.md` at candidate `ce96e09753028cf370ef717544dfe700b540462c` names v2.7; the canonical workspace index and v2.7 acceptance record agree. The former v2.6 statement in this evidence pack was caused by stale/untracked checkout input and is corrected here.
- **Entry level / route:** Level B product change, Sol capability route
- **Canonical Product start SHA:** `96a9d52602febc6ab1b9d29e92e83fe3eb7e8dd5`
- **Qualified continuation candidate:** `ce96e09753028cf370ef717544dfe700b540462c` (`4 ahead / 0 behind` at entry)
- **Audit evidence source:** `docs/operational/evidence/ux-system-wide-audit-20261001-96a9d526/`
- **Known validation state at entry:** global LPAF Product validation = `EVIDENCE_PENDING`; Forwarder Human Product Walkthrough = `IN_PROGRESS`

## Outcome and bounded scope

Close only the two remaining HIGH Product UX gaps while preserving the seven previously qualified HIGH-gap changes:

1. `UX-007` — make the current Customer and Expert Request/Quote workspaces clean, guided, progress-aware, and led by one state-derived commercial action.
2. `UX-008` — remove primary raw enum, raw ID, obvious English-copy, native file-control, unit, status, date, and bidi leakage from substantive current routes.

Then requalify the complete candidate and, only if all nine HIGH gaps pass, fast-forward the complete candidate through the controlled canonical integration process.

## Facts, assumptions, unknowns, and decisions

### FACT

- The continuation worktree was clean at `ce96e097`; the three qualified candidate commits plus the worktree snapshot remain exactly four commits above canonical.
- Existing Request commercial truth already provides immutable Quote history, Customer responses, localized Request state, and an Expert next-action projection.
- Customer Quote actions are already bounded by current Quote response/expiry/terminal state and server authorization.
- Accepted Quote does not create a Shipment automatically; the existing separately authorized create-from-accepted-Quote command remains explicit.
- Existing i18n, dual-calendar, quantity, money, semantic-label, and localized file-input utilities are available; no new localization platform is needed.
- The audit inventory covers 38 substantive routes and identifies Request/Quote hierarchy plus selected raw identity/enum/English leakage as the remaining HIGH findings.

### ASSUMPTION

- The supplied mission is the Product Owner approval reference for the exact UX-007 and UX-008 presentation changes named below.
- Semantic labels may replace primary technical values while codes/IDs remain available only in explicit technical/detail contexts.

### UNKNOWN

- Final exact-candidate automated and browser results remain unknown until qualification runs.
- Remote canonical stability remains unknown until the pre-integration fetch.
- Human Product Walkthrough result remains `IN_PROGRESS`; an agent cannot convert it to PASS.

### DECISIONS_NEEDED

- `NONE` for the bounded implementation.
- Stop if a change would alter Request/Quote/Shipment lifecycle, assignment/ownership, Quote immutability, authorization, persisted identifiers, timezone semantics, or the critical-journey set.

## Product Authority Record

### AUTHORIZED_PRODUCT_CHANGES

- Add concise commercial progress/readiness presentation for Customer and Expert Request workspaces.
- Rank and visually emphasize one current commercial action when the current actor can perform it; show an explicit waiting/concluded state otherwise.
- Reduce Request/Quote density through concise summaries and progressive disclosure for detailed facts, technical metadata, Quote versions, and history.
- Replace primary raw enum/code/ID and obvious English UI leakage with existing semantic Persian labels; localize units/status/date display and isolate LTR technical values.
- Preserve technical identifiers where operationally useful as secondary/on-demand metadata.
- Correct this evidence pack's stale LPAF v2.6 reporting defect.
- Add focused regression, label inventory, and browser evidence; integrate the complete candidate only after `HIGH_GAPS_REMAINING=0`.

### DELEGATED_TECHNICAL_CHOICES

- Component boundaries, derived presentation helpers, tabs/details disclosure, copy, responsive layout, and semantic-label mapping.
- Reuse and extension of existing i18n, date, quantity, and localized-file-input utilities.
- Focused test fixtures, disposable PostgreSQL 18 browser runtime, evidence packaging, commit boundaries, and fast-forward integration mechanics.

### PROTECTED_OUT_OF_SCOPE_BEHAVIOR

- `Request != Shipment`; accepted Quote does not automatically create Shipment.
- Request assignee remains distinct from Shipment owner.
- Quote/negotiation history remains immutable and auditable.
- Customer, Expert, organization, tenant, role, capability, and server-side permission boundaries remain unchanged.
- Persisted enum/code/ID values, state transitions, write APIs, SOR ownership, schema, and migration head remain unchanged.
- The seven previously qualified HIGH gaps, their product behavior, and their evidence remain preserved.
- Human Walkthrough database/history and all business facts remain unchanged; business actions performed against it must remain zero.
- Production, deployment, and release state remain untouched.

### APPROVING_OWNER_OR_AUTHORITY

Forwarder Product Owner through the supplied 2026-10-01 mission; LPAF v2.7 governs delivery and acceptance boundaries.

### APPROVAL_REFERENCE

User mission: `FORWARDER — CLOSE THE FINAL TWO HIGH UX GAPS — Preserve the qualified Guided Operational Workspace candidate`.

## Owners, SORs, actors, and boundaries

- **Request/Quote owner and SOR:** existing Request and Quote domain models/services and their immutable event/history records.
- **Shipment owner and SOR:** existing Operational Shipment domain; only the explicit create-from-accepted-Quote command may create it.
- **Presentation labels:** existing UI i18n/presentation helpers; they do not alter stored truth.
- **Expert:** current assigned-work and command authorization only.
- **Customer:** current authenticated customer projection and Quote-response authorization only.
- **Server:** remains authoritative for reach/use permission and every mutation.

## Journey impact and verification contract

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`

Affected journey-pack areas: Customer Request/Quote response and return; Expert Request triage, detail, Quote revision, commercial conclusion, and explicit Shipment creation; current operational/admin journeys where primary labels change. The Product Owner-controlled critical-journey set is not expanded or removed.

Required evidence on the exact final Product candidate:

- focused Request/Quote component and backend commercial-state regressions;
- permission/negative, terminal, waiting, discussion/revision, history, and explicit Shipment-creation checks;
- system-wide static label inventory classified `RESOLVED`, `INTENTIONALLY_TECHNICAL`, or `DEFERRED_POLISH`;
- frontend tests, TypeScript, production build, lint, governance checks;
- normal-navigation browser journeys on runner-owned disposable PostgreSQL 18, with no preserved-runtime business actions;
- regression of the seven qualified HIGH gaps;
- exact candidate/source, schema, environment, and evidence identities.

## Definition of done and stop conditions

- `UX-007=RESOLVED`; Customer and Expert see identity, Customer/assignee, current commercial state, Quote state, progress/readiness, history, and one meaningful action without a card wall.
- `UX-008=RESOLVED`; no HIGH raw ID, raw enum, or unlocalized primary copy remains on substantive current routes.
- `HIGH_GAPS_RESOLVED=9`, `HIGH_GAPS_REMAINING=0`, and previous-seven regression = `NO`.
- No protected behavior, schema, preserved data, production, deployment, or release state changes.
- Controlled integration proceeds only after required automated/browser evidence passes and the fetched canonical target remains compatible.
- `HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS` and `RELEASE_READY=NO` remain truthful.

## Entry decision

`AUTHORIZED_TO_PROCEED_WITHIN_SCOPE`

PDA-07 entry reconciliation: planned observable changes are `AUTHORIZED`; named semantics, permissions, history, seven qualified gaps, and runtime data are `PRESERVED`; no known `VIOLATION` or `UNKNOWN` remains in the implementation scope.
