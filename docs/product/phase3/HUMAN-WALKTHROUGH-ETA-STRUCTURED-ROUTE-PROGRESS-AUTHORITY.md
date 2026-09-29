# Human Walkthrough — structured route progress and ETA authority

Status: IMPLEMENTATION AUTHORIZED by the Product Owner mission dated 2026-09-29.
Baseline: LPAF v2.7, rigor C, capability tier Sol. Canonical entry SHA:
`95af46867c2900c9e832018e3e53ee8bb5d862ab`.

## Mission contract and Product Authority Record

| Field | Governed value |
| --- | --- |
| OUTCOME | ETA can consume an auditable structured progress observation on the exact active RoutePlan revision and RouteLeg while human position text remains descriptive only. |
| SCOPE_IN | Organization route baseline distance; immutable RoutePlan basis; one remaining-distance progress representation; exact RouteStageExecution binding; ETA v2 calculation and history; minimum report-form change; focused, PostgreSQL 18, backend, frontend and architecture qualification; controlled integration; preserved walkthrough runtime update without database reset. |
| SCOPE_OUT | Shipment page redesign; GPS/maps/traffic/weather/provider integration; free-text parsing; historical repair/backfill; Production; deployment; release; unrelated UX findings. |
| AUTHORIZED_PRODUCT_CHANGES | Organization Admin may version an optional planned distance with the existing route-time reference. Expert plan selection pins that version. The owning Expert may report remaining distance on a selected active stage execution. ETA may prorate only the current leg's pinned movement range from this observation. The report form exposes the structured field contextually and identifies the route stage in human language. |
| DELEGATED_TECHNICAL_CHOICES | Additive schema, immutable one-to-one progress evidence, decimal representation, API shape, ETA ruleset versioning, database constraints, tests, evidence packaging and controlled fast-forward integration. |
| PROTECTED_OUT_OF_SCOPE_BEHAVIOR | Operational route and customer-requested destination remain distinct; existing reports and ETA snapshots remain immutable; requested/planned/actual Cargo and Allocation meanings stay unchanged; permissions, tenant isolation, customer allowlists, route/time history, cargo participation, P3-01..15 behavior and all Production data remain unchanged except for the specifically authorized additive capability. |
| DECISIONS_NEEDED | None for the bounded foundation. A live routing provider, traffic-aware ETA, checkpoint segment-time model, or alternative progress mechanism requires a later Product decision. |
| APPROVING_OWNER_OR_AUTHORITY | Product Owner, through the attached “FORWARDER — ETA & STRUCTURED ROUTE PROGRESS FOUNDATION” mission. |
| APPROVAL_REFERENCE | User mission received 2026-09-29, sections 1–20. |

Facts: `OrganizationRouteTimeVersion` owns organization route reference values;
`RouteLegTimeBasis` immutably binds a selected version to one exact leg; reported
facts are append-only; `RouteStageExecution` already binds tenant, Shipment,
RoutePlan, RouteLeg and ExecutionUnit; `CargoEtaSnapshot` is immutable.

Unknowns remain unknown. No baseline is inferred from endpoints, free text or
transport mode. No progress is inferred from a human description. Existing
manual location reports receive no structured progress row.

## Journey and reference impact

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`

Affected journeys: `FWD-J02`, `FWD-J04`, `FWD-J06`, `FWD-J07`, `FWD-J08`,
`FWD-J09`, `FWD-IPJ-02`, `FWD-IPJ-03`, `FWD-IPJ-04`.

Required reruns: the P3-07 report slice, P3-10 route-reference slice, P3-11 ETA
slice, P3-14 Shipment runtime slice, the affected integrated journeys, and the
preserved Human Product Walkthrough on the exact integrated candidate. The human
result remains `IN_PROGRESS`; an agent cannot grant PASS.

LPAF reference impact: `NONE`; the mission applies v2.7 without changing it.
Forwarder architecture impact: `UPDATE_REQUIRED`; ADR-074 records the additive
model and calculation contract. Product Contract and Journey Pack identities are
preserved; this record adds the affected-rerun mapping rather than changing the
critical set.

## Definition of done and stop conditions

The capability is Engineering Complete only when one forward migration leaves
one Alembic head; invalid tenant/revision/leg/execution/cargo bindings fail closed;
free text never qualifies ETA; valid structured progress deterministically
qualifies ETA from pinned baseline values; replan and ETA history remain immutable;
focused PostgreSQL 18, affected frontend, full backend and governance checks pass;
and controlled integration reports exact Product/evidence/canonical identities.

Stop for a Product decision if an external routing provider, a second progress
mechanism, a new route owner, or a major route rewrite becomes necessary. Never
access or mutate Production, deploy, or create a release.
