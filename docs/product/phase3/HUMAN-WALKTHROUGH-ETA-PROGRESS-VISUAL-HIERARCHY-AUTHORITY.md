# Human Walkthrough — ETA progress entry and visual hierarchy authority

Status: IMPLEMENTATION AUTHORIZED by the Product Owner mission dated 2026-10-03.
Baseline: LPAF v2.7, rigor B, capability tier Sol. Canonical entry SHA:
`b0e82ba825536d33188b3b85318ec9851f452a67`.

## Mission contract and Product Authority Record

| Field | Governed value |
| --- | --- |
| OUTCOME | An owning Expert can discover and append the existing `DISTANCE_REMAINING_KM` fact from Shipment → Tracking & ETA, while shared navigation and content hierarchy use a restrained light enterprise presentation. |
| SCOPE_IN | A dedicated expandable route-progress section backed by the existing reported-fact API/model; remaining-distance, execution/leg, occurred-at and optional-note inputs; post-arrival occurrence guard; existing progress history; shared navigation color tokens, heading hierarchy, form grouping, entity-card and CTA presentation; focused backend/frontend/PostgreSQL 18/browser qualification; controlled canonical integration and preserved-runtime refresh. |
| SCOPE_OUT | ETA math, Route Reference ownership, Shipment/Cargo/Allocation/Request/Quote/Document/Closure/History/RBAC/geography architecture, new workflow or design system, GPS/OCR/AI, Production, deployment and release. |
| AUTHORIZED_PRODUCT_CHANGES | The existing structured-progress capability receives a clear Expert entry point. Once authoritative Arrival exists, a new structured in-leg progress command is refused, including a retroactive occurrence time, because this scope grants no historical-repair authority. Active navigation becomes a light-blue selected surface with a non-color indicator. Shared headings, simple form groups, cards and CTA variants receive restrained hierarchy corrections. |
| DELEGATED_TECHNICAL_CHOICES | Component factoring, labels, shared CSS tokens/classes, validation presentation, focused tests, evidence packaging and controlled fast-forward integration. |
| PROTECTED_OUT_OF_SCOPE_BEHAVIOR | `ETA_RULESET_V2` calculation and input precedence; one append-only route-progress SOR; tenant/owner authorization; exact plan/leg/execution/basis binding; historical facts and snapshots; font family; brand logo; user accent choice; every preserved Human Walkthrough business row, especially the ETA-test Shipment with no Arrival and no structured progress. |
| DECISIONS_NEEDED | None. A second progress model, ETA formula change, schema migration, route model change, new theme system or broader information-architecture redesign requires a later Product decision. |
| APPROVING_OWNER_OR_AUTHORITY | Product Owner through “FORWARDER — STRUCTURED ETA PROGRESS + VISUAL HIERARCHY / COLOR SYSTEM PASS”. |
| APPROVAL_REFERENCE | User mission received 2026-10-03, sections 1–31. |

## Facts, assumptions and stop conditions

Facts: ADR-074 already defines one immutable `DISTANCE_REMAINING_KM` row linked
one-to-one to a reported event and the exact organization, Shipment, active
RoutePlan, RouteLeg, RouteStageExecution, ExecutionUnit and optional pinned time
basis. The API, validation, ETA consumer and history exist. The current UI hides
the input behind the generic “new report” form and a `PROGRESS` selection. The
current shared navigation token renders active items as a saturated blue block.

Assumption to verify: no migration is required. Stop if the existing persistence
model cannot express the authorized entry, if ETA math must change, or if a
second subsystem or migration becomes necessary.

## Journey and evidence impact

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`.

Affected journeys: `FWD-J02`, `FWD-J04`, `FWD-J06`, `FWD-J07`, `FWD-J08`,
`FWD-J09`, `FWD-IPJ-02`, `FWD-IPJ-03`, `FWD-IPJ-04`. Required evidence includes
focused report/ETA authorization and state tests, PostgreSQL 18 ETA matrix,
frontend component tests, type-check/build/lint/structure, desktop and narrow RTL
browser checks, representative Product surfaces, preservation comparison and
exact-candidate identity. Human Product Walkthrough remains `IN_PROGRESS`; this
mission cannot grant human PASS or Release Ready.

LPAF v2.7 reference impact: `NONE`. Forwarder architecture impact: `NONE`; this
mission reuses ADR-074 and the existing shared UI library without changing SOR,
domain ownership or Product architecture.
