# Forwarder UX Implementation Backlog

Source audit: canonical SHA `96a9d52602febc6ab1b9d29e92e83fe3eb7e8dd5`  
Target model: **Forwarder Guided Operational Workspace**  
This is a recommendation artifact only; nothing in this backlog was implemented by the audit mission.

## Prioritization rules

Priority favors lower cognitive load, reliable next action, immediate process understanding, fewer visible controls/cards/paragraphs, exception-based operations, and safe progress feedback. Product correctness, permissions, ownership, tenant boundaries, append-only history, and all Requested/Planned/Actual distinctions remain authoritative.

## P0 — RC / workflow blockers

`P0_COUNT=0`

No current UX finding blocks the already-qualified end-to-end lifecycle. Do not manufacture a release blocker from a presentation improvement.

## P1 — High-value UX

### P1.1 — Shared operational UX projection

- Gaps: UX-002, UX-003, UX-004; enables UX-001 and UX-009.
- Effort: L.
- Deliver: human Shipment label; ordered stage state; independent task statuses/applicability; ranked attention; one recommended action plus secondary valid actions; latest meaningful update; ETA/reason; closure readiness.
- Authority rule: projection only. Do not duplicate or replace route, stage, document, allocation, delivery, ETA, or closure authority.
- Acceptance:
  - permissions and ownership remove unauthorized actions;
  - blocker outranks warning;
  - unknown remains unknown;
  - closed Shipment has no false generic next action;
  - every aggregate links to source truth.

### P1.2 — Five-second Shipment Summary and header

- Gaps: UX-002, UX-003, UX-009.
- Effort: M after P1.1.
- Deliver: concise header; requested/operational route comparison; current operation; compact five-stage progress; task completion; current attention; one next action; readiness verdict.
- Acceptance:
  - identity, owner, stage, attention, ETA/reason, progress, and action visible without desktop scrolling;
  - no section content duplicated on Summary;
  - one visually dominant action.

### P1.3 — Prioritized Shipment List and Expert Home

- Gaps: UX-001, UX-004; include UX-016/017 as supporting scope.
- Effort: L.
- Deliver: essential Shipment table/list, severity/action sorting, compact role status strip, ranked queue, recently changed list, direct task links.
- Acceptance:
  - user can identify which Shipment to open and why;
  - source/project IDs are on demand;
  - stale attention evaluation remains explicitly visible;
  - empty state confirms when no action is required.

### P1.4 — Route & Execution task decomposition

- Gap: UX-005.
- Effort: L.
- Deliver: operate-first route timeline; current execution and event action; separate Plan/Edit; separate Audit/Technical detail; configuration and finance hidden by default.
- Acceptance:
  - no giant section regression;
  - route authority and event semantics unchanged;
  - current leg/action visible before revisions, reconciliation, or project detail.

### P1.5 — Request / Quote task hierarchy

- Gap: UX-007.
- Effort: M.
- Deliver: state/next commercial action first for Customer and Expert; concise request facts; quote thread/version/history progressive disclosure.
- Acceptance:
  - current quote action visible without reading full request;
  - discussion and accept/reject do not compete when state disallows them;
  - commercial conclusion, CRM linkage, and Shipment creation truth unchanged.

### P1.6 — Admin workspace grouping

- Gap: UX-006; supports UX-021.
- Effort: M.
- Deliver: People & Access, Organization Operations, Organization Data, and System Governance workspaces; explicit scope switch for dual-role admins; compatibility/deep-link plan.
- Acceptance:
  - user sees only relevant scope;
  - organization configuration and governed System definitions are not peers in one flat tab wall;
  - permissions remain unchanged.

### P1.7 — Human labels and localization contract

- Gap: UX-008.
- Effort: M; can begin early and support every other P1.
- Deliver: human Shipment/entity labels, complete business/status/transport/reason localization, secondary ID chip, consistent bidi handling.
- Acceptance:
  - no raw internal enum or technical ID is the primary label;
  - raw identity remains copyable for support/audit;
  - public/customer surfaces do not reveal internal identifiers.

### P1.8 — Closure decision summary

- Gap: UX-009.
- Effort: S–M using existing evaluation.
- Deliver: READY/NOT READY; X/Y applicable criteria; ranked blocker links; separate warnings; one normal close action; exceptional path separated.
- Acceptance:
  - readiness is understood without policy-paragraph interpretation;
  - warnings never become blockers;
  - unknown quantities remain unknown;
  - no closure criterion changes.

## P2 — Experience enhancement

### P2.1 — Cargo & Allocation comparison

- Gap: UX-011.
- Effort: M.
- Deliver six-column quantity comparison, explicit unknown/mismatch, and focused correction/transfer flows.

### P2.2 — Document requirement rows

- Gap: UX-012.
- Effort: M.
- Deliver table/list, one action per state, required/optional clarity, version and policy detail on demand.

### P2.3 — Tracking & ETA current-state summary

- Gap: UX-013.
- Effort: M.
- Deliver latest human position + structured progress + ETA/reason + one action; reports/provenance in history/detail.

### P2.4 — Delivery focused action

- Gap: UX-014.
- Effort: M.
- Deliver Actual Cargo/Delivered/Remaining/Final comparison and action-opened delivery form.

### P2.5 — History narrative and full-dataset filters

- Gap: UX-015.
- Effort: M.
- Deliver concise day-grouped timeline, category filters over full data, raw payload on demand.

### P2.6 — Operations Workspace, Control Tower, and Work Queue rows

- Gaps: UX-016, UX-017, UX-018.
- Effort: M.
- Deliver one shared human attention vocabulary and compact expandable queue rows.

### P2.7 — Guided New Operation

- Gap: UX-019.
- Effort: L.
- Deliver progressive steps for source, route, cargo, and review with preserved validation and explicit final review.

### P2.8 — Customer outcome-focused views

- Gaps: UX-010, UX-022.
- Effort: M.
- Deliver concise Request/Shipment rows and a customer-safe current Shipment overview.

### P2.9 — Layered help and responsive priority

- Gaps: UX-020, UX-023.
- Effort: M across affected work.
- Deliver concise help, task-specific empty states, mobile section selector, vertical progress, and action sheets. Implement with each surface; do not create a separate global mobile redesign.

### P2.10 — Configuration view/edit modes

- Gap: UX-021.
- Effort: M after P1.6.
- Deliver current effective state first, explicit edit/publish mode, history and advanced controls in detail.

## P3 — Future / polish

### P3.1 — Container simplification

- Gap: UX-024.
- Effort: S per surface.
- Reduce nested cards; use rows, dividers, whitespace, inline summary, and timelines based on semantics.

### P3.2 — Timestamp and metadata hierarchy

- Gap: UX-025.
- Effort: S.
- One meaningful time primary; precise dual-calendar and provenance detail on demand.

### P3.3 — Empty and success state library

- Gap: UX-026.
- Effort: S.
- Consistent positive empty states and subtle authoritative completion feedback.

### P3.4 — Outcome labels and RTL/LTR hardening

- Gap: UX-027.
- Effort: S.
- Name actions by result and standardize long identifier treatment.

### P3.5 — Heading and spacing rhythm

- Gap: UX-028.
- Effort: S.
- Remove repeated introductions and normalize task-section hierarchy.

## Suggested goal-based mission sequence

### Mission A — Operational decision layer

P1.1 + P1.2 + P1.8 + the bounded part of P1.7. This creates the authoritative derived UX contract, Summary, next action, progress, task readiness, and closure decision state.

### Mission B — Prioritization surfaces

P1.3 + P2.6. Apply the same decision layer to Expert Home, Shipment List, Operations Workspace, Control Tower, and Work Queue. Avoid building five independent interpretations.

### Mission C — Task surface simplification

P1.4 + P2.1–P2.5. Decompose Route & Execution and then simplify Cargo, Documents, Tracking/ETA, Delivery, and History using the common hierarchy.

### Mission D — Commercial, Customer, and Admin clarity

P1.5 + P1.6 + P2.8 + P2.10, followed by localized/responsive polish.

Each mission requires Product Owner-approved journey contracts and target-state examples before implementation, because the audit does not authorize Product changes.

## Quick-win package

The following can be included in the appropriate structural mission without opening independent projects:

1. Demote/copy-enable raw IDs and localize primary labels.
2. Add existing-data closure readiness summary.
3. Reduce document actions to the current valid action.
4. Move ETA/progress/current position above provenance.
5. Hide Delivery creation form until invoked.
6. Remove repeated explanatory paragraphs.
7. Demote duplicate timestamps/version fields.
8. Standardize positive empty/success states.
9. Outcome-name buttons and normalize bidi IDs.

## DO_NOT_BUILD_NOW

- complex personalization;
- AI assistant or autonomous agent;
- advanced employee scoring;
- leaderboards, badges, streaks, points, or rewards;
- speed-to-close incentives;
- deep workflow-engine replacement;
- new GIS, routing, or optimization platform;
- unrelated analytics/dashboard subsystem;
- new geography sources/country expansion;
- OCR/document intelligence or inferred legal requirements;
- notification-platform rewrite;
- global typography redesign;
- native mobile app or independent full mobile redesign;
- replacement foundations for Request, Quote, Shipment, Route, Execution, Cargo, Allocation, Tracking, ETA, Documents, Stages, Delivery, Closure, or History.

## Verification expectations for future implementation

- Focused component and derivation tests for state, role, permission, blocker/warning, optionality, and unknown values.
- Browser journeys for the affected role and Shipment states, including small viewport.
- Five-second moderated review of Shipment Summary with representative Experts.
- Assertions that the next action deep-links to the exact task and disappears after completion.
- No raw enum/ID primary-label scan for affected surfaces.
- No database/schema work unless a future Product mission proves the existing read models cannot support the accepted journey contract.
- Existing end-to-end Product lifecycle, tenant isolation, append-only history, and one Alembic head remain regression gates.

