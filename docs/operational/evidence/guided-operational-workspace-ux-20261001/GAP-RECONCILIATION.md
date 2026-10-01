# Current → Implemented UX Gap Reconciliation

Source audit: `docs/operational/evidence/ux-system-wide-audit-20261001-96a9d526/`

This comparison is limited to evidence produced by the guided operational workspace mission. It does not claim that every system-wide UX gap is resolved.

## High gaps

| Gap | Result | Current → Implemented evidence |
|---|---|---|
| UX-001 — Role Home / Operations Home | RESOLVED | The Expert Console now opens with a compact operational status strip and ranked Shipment queue above the commercial request workspace. The full Operations Workspace uses the same projection and adds actionable/attention counters. |
| UX-002 — Shipment Summary | RESOLVED | The Summary now presents human identity, current ordered stage/progress, independent task readiness, attention, current position, ETA or explicit unavailability reason, and one primary action. |
| UX-003 — Shipment Next Action | RESOLVED | A server-authorized, deterministic Shipment-wide projection ranks one primary navigation action, explains why it is next, deep-links to the owning section, and bounds secondary suggestions to three. Closed or unauthorized Shipments receive no recommendation. |
| UX-004 — Shipment List | RESOLVED | The card grid became a responsive priority-row queue with human label, state, route, stage/progress, readiness, top issue, last change, and one action. Metadata and UUID are secondary disclosure. PostgreSQL ordering prioritizes critical/open work without leaking work-item state to callers lacking `work_item.read`. |
| UX-005 — Route & Execution | RESOLVED | The explicit Route surface is operate-first, ranks only the first valid route action, separates Route/Stages/Cargo/Documents/Tracking/Delivery/Closure/History, and collapses reference-time, execution detail, finance, reconciliation, revisions, and technical history behind task-specific disclosure. Domain commands and authorities are unchanged. |
| UX-006 — Admin navigation | RESOLVED | Navigation is grouped into Overview & Reporting, People/Access/Assignment, Organization Operations, Organization Data/Network, and visually distinct Platform Governance. Existing tab values and authority guards remain compatible. |
| UX-007 — Request / Quote workspace | DEFERRED_WITH_REASON | The operational access card now uses semantic Shipment identity, route, stage, and next action, but the full Customer/Expert commercial Request and Quote workspace was not restructured. That work was outside the mission's five authorized priority slices and needs its own customer/commercial journey evidence. |
| UX-008 — Entity labels / localization | PARTIALLY_RESOLVED | Changed operational surfaces use a human Shipment label first, move UUIDs under “technical ID”, use `bdi` for IDs, humanize admin labels, and remove a false direct-Shipment fallback. A system-wide raw-enum/i18n inventory was not authorized or completed; legacy surfaces still contain technical terms. |
| UX-009 — Closure | RESOLVED | Closure begins with a dominant READY/NOT READY verdict, X/Y completion, blocker/warning counts, ranked blockers, separate warnings, collapsed completed criteria, one normal close action, and a distinct exceptional-admin path. |

`HIGH_GAPS_START=9`

`HIGH_GAPS_RESOLVED=7`

`HIGH_GAPS_REMAINING=2` (UX-007 deferred; UX-008 partial)

## Medium gaps touched

- UX-013 — Tracking & ETA: current location and ETA/reason are summarized before provenance/detail.
- UX-016 — Operations Workspace: adds compact actionable/attention counts and projected next action on active Shipment cards; the pre-existing attention cards remain.
- UX-020 — Help/copy density: changed Summary, Route, List, Closure, and Admin surfaces use shorter contextual copy and progressive disclosure.
- UX-022 — Request and Shipment collections: Shipment collection changed to a responsive comparison queue; Request collections were not changed.
- UX-023 — Small viewport: priority order, vertical row adaptation, compact scrollable section navigation, and no-horizontal-overflow evidence were added.

## Polish gaps touched

- UX-024 — Container simplification on the Shipment list, priority overview, Summary guidance, Closure, and Admin navigation.
- UX-025 — exact IDs, projection sources, and freshness are disclosed on demand; one meaningful operational time remains primary.
- UX-027 — outcome-oriented action labels and secondary `bdi` UUID treatment on changed surfaces.
- UX-028 — reduced repeated heading/copy layers and established task-first section rhythm on changed surfaces.

## Semantics preserved

- No schema or migration was added; repository head remains `20261015_org_shipment_stages`.
- The projection stores no workflow state and is rebuilt on request from authorized current facts.
- Existing write endpoints, transitions, permissions, ownership, fixed Shipment responsibility, tenant scope, customer/public payloads, and closure rules remain authoritative.
- Missing data stays unknown; it is never coerced to readiness or success.

