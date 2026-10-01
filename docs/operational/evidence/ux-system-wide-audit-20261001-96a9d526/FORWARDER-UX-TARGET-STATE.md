# Forwarder UX Target State

Target model: **Forwarder Guided Operational Workspace**  
Experience qualities: **Clean + Guided + Progress-aware + Lightly gamified**  
Domain baseline: preserve all qualified Product truth and authority boundaries at canonical SHA `96a9d52602febc6ab1b9d29e92e83fe3eb7e8dd5`.

## Product experience promise

Forwarder should help each role answer, without exploration:

1. What has been completed?
2. Where am I now?
3. What is missing or needs attention?
4. What should I do now?
5. What happens after that?

The answer must come from Product state, permissions, ownership, policy, blockers, warnings, and completed work. It must never be decorative, hard-coded, or based on an invented value.

## Design laws

1. **One primary task per page.** One visually dominant action; other valid actions are secondary or on demand.
2. **Immediate state before detail.** Initial view contains essential state, essential context, current attention, and primary action.
3. **Progressive disclosure.** Provenance, revisions, audit payload, history, advanced configuration, and correction flows remain accessible but normally closed.
4. **Use the semantic visual model.** Ordered stages use process progress; independent responsibilities use a task list; past events use history/timeline.
5. **Exception first for operators.** Normal, current Shipments require less visual weight than stale, blocked, or actionable Shipments.
6. **Recognizable labels.** Human Shipment labels, customer, route, and stage lead; raw UUIDs/codes remain copyable metadata.
7. **Unknown stays unknown.** No progress, completeness, or gamification pattern may convert unknown to zero or imply unsupported certainty.
8. **Role-specific complexity.** Customers see outcomes; Experts see work; Organization Admins see tenant policy; System Admins see governed definitions.
9. **Safe completion feedback.** Completion indicators reward data quality and readiness, never speed, ranking, or volume of data entry.
10. **No foundation replacement.** Target UX is a projection over current qualified domain state, not a new workflow engine.

## Experience architecture

### Shared derived view model

Create one server-authoritative or consistently derived presentation contract for operational UX. The target contract should expose, without changing underlying domain ownership:

- `human_shipment_label`
- overall Shipment state
- current ordered operational stage and `completed/total`
- independent task statuses with applicability
- current attention items ranked by severity and actionability
- one recommended next action
- other valid actions
- blocker/warning counts
- latest meaningful update
- ETA or explicit unavailable reason
- closure readiness summary

This is a read projection, not a workflow-engine replacement. Every status and action links back to authoritative domain facts and preserves permissions.

## Global navigation

### Target behavior

- Show only destinations relevant to the active role.
- Use stable top-level workspaces: **Commercial**, **Operations**, **Customers**, **Configuration**; show **System Governance** only to Platform Admins.
- A dual-role user explicitly switches between Organization Configuration and System Governance; do not merge their controls into one tab wall.
- Preserve breadcrumbs or concise context when moving from queue → Shipment → task.
- Avoid persistent fourth/fifth navigation layers. On-demand details are drawers, dialogs, or expandable panels—not another navigation bar.

### What remains hidden

Low-frequency dashboards, builder tools, governed work queue internals, raw system catalogs, and advanced configuration can live under secondary navigation.

## Role Home

### Expert / Operations Home

The default Expert landing experience is a task queue, not a dashboard of cards. It answers:

- active Shipment count;
- attention count and severity;
- changes since the user's last acknowledged view, where the Product has reliable event data;
- the next Shipment to open and why;
- work ready to perform now.

Target composition:

1. One compact operational status strip: Active, Needs attention, Ready now, Stale.
2. Ranked exception/task queue with Shipment, route, stage, attention reason, last change, and direct action.
3. “Recently changed” secondary list, derived from meaningful domain events.
4. Commercial Request queue as a peer workspace or a clear segment—not a separate competing definition of “home.”

Do not add decorative charts when a queue answers the job better.

### Customer Home

Lead with current Request/Shipment items and their next customer action. Completed or inactive items remain searchable but visually quiet. Show current status, route, quote/shipment state, and the last meaningful update.

### Admin Home

Lead with setup groups and configuration health: missing prerequisites, unpublished changes, policy coverage, and recently changed configuration. Do not show operational Shipment actions.

## Shipment List

Use a responsive table on desktop and structured list rows on small screens.

### Essential columns

- human Shipment label;
- customer;
- route;
- current ordered stage;
- attention state/reason;
- last meaningful update;
- next action.

### Secondary

- owner;
- planned timing;
- task completion count.

### On demand

- raw UUID;
- project/source Request/Quote IDs;
- full provenance;
- old milestones and technical timestamps.

Default sorting is actionability/severity then freshness, with an explicit alternative for recency. The row itself opens Summary; the next-action control opens the exact task section.

## Shipment Header

The header persists across all Shipment sections and contains only:

- human Shipment identity, customer, owner;
- overall state;
- concise requested and operational route;
- current ordered stage;
- attention badge/count;
- copyable raw ID in secondary metadata.

The header does not repeat every Shipment fact or host domain forms.

## Shipment Summary

Summary is a decision page, not a detail page.

### Initial desktop view

1. **Header** — identity, customer, owner, overall state.
2. **Current operation** — current stage, latest meaningful position, ETA or reason.
3. **Process progress** — compact ordered stage strip.
4. **Task readiness** — concise X/Y plus only incomplete/attention tasks.
5. **Attention** — current blockers/warnings only, ranked.
6. **Next action** — one prominent state-derived CTA and one-sentence outcome preview.

Requested route and operational route appear in one compact comparison. Everything else links to the relevant section.

### Five-second comprehension rule

Without scrolling on common desktop viewports, an Expert must be able to identify Shipment, owner, current stage, overall attention, ETA/reason, task progress, and the recommended next action.

## Shipment Workspace

Preserve the qualified route-based information architecture:

- Summary
- Route & Execution
- Operational Stages
- Cargo & Allocation
- Documents
- Tracking & ETA
- Delivery
- Completion / Closure
- History

The active section represents one operational job. A section may have summary + primary work area + on-demand detail; it must not become a new mega-page.

### Section layout rule

`TASK HEADER → CURRENT STATE → PRIMARY ACTION/WORK AREA → ATTENTION → ON-DEMAND DETAIL`

Configuration actions do not sit beside routine operational actions. Correction/reopen/exceptional actions sit under an overflow or explicit maintenance area.

## Task List

The task list represents independent or partially ordered work. It is not a stepper.

Each row has:

- domain label;
- `DONE`, `IN_PROGRESS`, `NEEDS_ATTENTION`, `BLOCKED`, or `OPTIONAL`;
- one short reason;
- direct link to the relevant section;
- completion evidence, if useful, on demand.

Applicable domains: Route, Execution, Cargo, Allocation, Documents, Tracking, ETA, Operational Stages, Delivery, Closure. Applicability comes from Product/policy state. Optional tasks do not reduce required completion.

## Process Progress

Use the ordered Organization Shipment stages exactly as qualified:

`آماده‌سازی / بارگیری → خروج از مبدأ → در مسیر → رسیدن به مقصد → تخلیه`

- Completed: checkmark + completed timestamp on demand.
- Current: visually emphasized with text label, not color alone.
- Future: quiet and clearly incomplete.
- Blocked/late: explicit icon and reason; do not falsely advance progress.
- Summary shows compact progress; Stages section hosts start/complete controls and event details.
- Mobile uses a vertical or horizontally scrollable representation with the current stage brought into view.

## Next Action

### Selection rules

The recommended action is selected from all currently permitted actions, then ranked by:

1. hard blockers preventing the active lifecycle transition;
2. overdue/urgent operational exceptions;
3. current ordered-stage action;
4. required document/tracking/allocation/delivery work;
5. closure readiness/action;
6. optional hygiene tasks.

The projection must consider ownership, role permissions, policy applicability, prerequisites, warnings versus blockers, completed work, and Shipment state. It returns:

- one recommended action;
- destination route/section and anchored task;
- a short reason;
- what will become possible afterward;
- other valid actions as secondary.

Closed Shipments have no generic “next action.” They show a closed success state; permitted corrections or record completion are explicitly secondary maintenance actions.

## Attention and exceptions

- Standardize attention severity and reason labels across Role Home, Shipment List, Summary, Control Tower, and Work Queue.
- Collapse multiple technical reasons into a human primary reason with count and detail.
- Distinguish `BLOCKER`, `WARNING`, `STALE`, and `INFORMATIONAL` with text/icon as well as color.
- Use the same direct task link everywhere.
- The normal state is quiet. Positive empty state: “All active Shipments are current; no action is required now.”
- Keep evaluation freshness visible when stale, because absence of results is not proof of health.

## History

- Keep History strictly past-tense and append-only.
- Use chronological timeline rows grouped by day.
- Primary line: human event label and concise consequence.
- Secondary: actor, time, domain/category.
- On demand: raw code, source/revision IDs, replaced-event relationship, full quantity payload.
- Filters query the complete history dataset, not only the loaded page.
- Do not show future tasks or current action controls inside History.

## Route & Execution

### Primary

- active route/leg timeline;
- current execution and equipment;
- departure/arrival state;
- one current event action;
- active issue blocking the route.

### Secondary

- requested vs operational route;
- planned vs estimated vs actual times;
- route reference time/distance;
- current variance.

### On demand

- route revisions;
- old execution records;
- finance/reconciliation;
- project units;
- checkpoint configuration;
- technical identifiers and provenance.

Separate **Operate** from **Plan/Edit** and **Audit/Technical detail**. Use a route timeline rather than card-per-leg where possible.

## Cargo & Allocation

Provide one comparison matrix per cargo line:

`Requested | Planned | Actual Cargo | Planned Allocation | Actual Allocation | Delivered`

Unknown uses an explicit “نامشخص” state and is never displayed as zero. Differences receive a concise explanation and link to the exact corrective task. Editing/transfer/correction forms open only when invoked. UOM and destination remain consistent across the row.

## Documents

Use a table/list with:

`Document requirement | Required/Optional | Applicable | File state | Review/completeness | Action`

One contextual action appears per row. Prior versions, policy source, reviewer metadata, replace/link/remove, and exceptional controls are on demand. Empty state explains that no organization requirement applies or invites the first valid upload without implying an error.

## Tracking & ETA

The top summary combines:

- latest human position description and report time;
- structured route progress;
- ETA, confidence/state, or a human unavailable reason;
- one current action.

Report history, ETA ruleset/provenance, raw progress values, and correction/reopen controls are secondary. Free-text position remains descriptive and never drives ETA by itself.

## Delivery

Show Actual Cargo, Delivered, Remaining/Unknown, and final-delivery state in one comparison row. The primary action opens a focused form for partial or final delivery with structured destination and quantity. Prior deliveries use a compact list/timeline; correction/reopen and evidence details are on demand.

## Completion / Closure

The first element is an explicit `READY TO CLOSE` or `NOT READY` status, followed by:

- completed criteria X/Y;
- blockers, ranked and linked;
- warnings, visually separate and non-blocking;
- one normal closure action when ready;
- exceptional close as a clearly separated governed action;
- completed requirements collapsed by default.

The user never needs to interpret a policy paragraph to understand readiness. Effective policy/version remains available in detail.

## Customer experience

- Request Detail starts with status and the current customer action; request facts collapse into a concise summary.
- Quote discussion is a single focused work area, with old quote versions and full thread on demand.
- Shipment Detail starts with current status, latest position, ETA/reason, delivery/document attention, and a small timeline of customer-meaningful events.
- Internal ownership, work queues, source IDs, policy internals, and technical provenance remain hidden.

## Admin configuration

- Separate Organization Configuration from System Governance.
- Group configuration by job rather than implementation component.
- Each module shows scope, effective state/version, impact, primary save/publish action, and validation.
- History, raw codes, imports, aliases, and destructive controls are on demand.
- Use tables for repeated reference/document/location definitions.
- Provide safe defaults and explicit empty states; do not leak configuration controls into operational Shipment tasks.

## Professional gamification

Allowed patterns:

- stages completed out of five;
- applicable tasks completed out of total;
- document and closure readiness;
- active Shipments current out of total;
- subtle success confirmation after authoritative completion;
- positive empty states when the operation is current.

Rules:

- derived from authoritative facts;
- no points, ranks, badges, streaks, or employee competition;
- no reward for speed or number of entries;
- optional tasks excluded from required completion;
- blockers and unknown values cannot be hidden by a percentage;
- every aggregate opens its source facts.

## Responsive target

- Preserve the same information priority, not the same geometry.
- Tables become structured list rows; current stage and next action remain visible first.
- Ordered progress becomes vertical or scrollable with current step focused.
- Sticky mobile primary action is acceptable when it does not obscure content.
- Local navigation collapses to a section selector/overflow after the current section label.
- Drawers become full-height sheets and return focus to the invoking control.
- Long IDs remain copyable but truncated and LTR-isolated.

## Accessibility and interaction target

- Every input has a persistent label and error association.
- Status uses text/icon plus color.
- Buttons name the result: “ثبت خروج از مبدأ,” not generic “ثبت.”
- All drawers, dialogs, menus, and tooltips are keyboard and touch accessible.
- Focus moves to validation errors and returns after modal/drawer close.
- Dynamic next-action/attention changes are announced without excessive live-region noise.
- Persian text remains RTL; identifiers, dates where appropriate, and technical codes are isolated with `bdi`/direction handling.

## Measurable implementation targets

1. One visually dominant primary action per major task surface.
2. Shipment Summary understandable in approximately five seconds in moderated review.
3. Current operational stage visible on Summary and Shipment List without navigation.
4. Recommended next action visible without desktop scrolling.
5. Blockers and warnings distinguishable at a glance by label/icon, not color alone.
6. No raw internal enum as a primary UI label.
7. No raw technical ID as the primary entity label.
8. Ordered stage progress and independent tasks use visibly different models.
9. Optional detail is hidden by default on all major operational surfaces.
10. No card-within-card solely to group adjacent metadata.
11. Shipment List supports comparison of at least the seven essential fields without opening rows.
12. Closure readiness and X/Y completion are visible before policy explanation.
13. Document rows show no more than one primary action at a time.
14. History filters apply across the full available history, not only the loaded page.
15. Mobile retains visible current state and accessible primary action without horizontal overflow.

These are implementation acceptance targets, not invented analytics claims. Baseline and outcome should be verified through structured usability walkthroughs and UI assertions.

## Do not build now

- complex personalization or per-user dashboard composition;
- AI assistant or autonomous next-action agent;
- new workflow-engine replacement;
- advanced employee scoring, badges, leaderboards, streaks, or rewards;
- speed-to-close or volume-based performance scoring;
- new GIS/routing platform or route-optimization engine;
- unrelated analytics subsystem or dashboard expansion;
- new geography sources or broader country scope;
- document OCR/classification or legal-requirement inference;
- notification-platform rewrite;
- global typography redesign;
- native mobile application or full mobile redesign;
- new foundations for ETA, stages, closure, documents, allocations, delivery, or history.

The target is a clearer operational projection of qualified Product truth—not more Product surface area.

