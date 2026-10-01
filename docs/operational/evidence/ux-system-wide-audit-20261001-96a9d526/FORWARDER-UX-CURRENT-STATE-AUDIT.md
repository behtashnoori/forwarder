# Forwarder UX Current-State Audit

Status: read-only Product / UX discovery  
Audit date: 2026-10-01  
Canonical Product SHA: `96a9d52602febc6ab1b9d29e92e83fe3eb7e8dd5`  
Canonical branch: `integration/golden-controlled`  
Ahead / behind after fetch: `0/0`  
Alembic head: `20261015_org_shipment_stages` (`HEAD_COUNT=1`)  
Governance: `LPAF v2.7 — ACTIVE / FROZEN / CANONICAL`

## Executive finding

Forwarder is functionally broad, operationally truthful, and already has the right domain foundations: explicit Request/Quote/Shipment separation, role and tenant boundaries, route and execution semantics, cargo/allocation/delivery distinctions, structured progress and ETA, document requirements, ordered organization stages, closure evaluation, exception monitoring, and unified history. The exact-SHA browser qualification proves these capabilities work together.

The present UX is nevertheless heavy because capability is often presented as a collection of equally prominent cards, paragraphs, forms, metadata, and actions. The system frequently exposes implementation truth before user task truth. The Expert can find most facts, but often cannot answer within five seconds: “where am I, what needs attention, and what do I do next?” The principal issue is not missing capability; it is hierarchy, progressive disclosure, and cross-domain state synthesis.

No audit finding prevents the qualified lifecycle from completing. This audit therefore records `BLOCKER=0`; the major findings are high-value UX gaps suitable for the next goal-based implementation mission.

## Audit boundary and method

- Read-only source inspection at the canonical SHA.
- Route and component inventory from `src/App.tsx`, page components, Shipment workspace components, role navigation, and admin configuration components.
- Visual review of all 58 PNG captures in the exact-candidate evidence set at `D:\1-webapp\forwarder-dev\final-human-walkthrough-hardening-20261001-96a9d526-browser-full`.
- Evidence covers desktop and limited mobile states for Customer, Expert, Organization Admin, System Admin, public tracking, commercial flow, operational monitoring, Shipment execution, cargo/allocation, documents, tracking/ETA, delivery, stages, closure, and history.
- Existing disposable qualification result confirms 22 Chrome packs passed against PostgreSQL 18 and migration head `20261015_org_shipment_stages` at the audited SHA.
- UI counts below are intentionally approximate. They describe initial cognitive load, not DOM-node precision. Shared/global navigation and transient toasts are excluded unless they materially affect the surface.
- No runtime was started, no database was opened or migrated, and the preserved Human Walkthrough was not accessed or mutated.

## Canonical-state gate

| Check | Result |
|---|---|
| Working tree before audit artifacts | Clean |
| Local canonical identity | `96a9d52602febc6ab1b9d29e92e83fe3eb7e8dd5` |
| `origin/integration/golden-controlled` | Same SHA |
| Ahead / behind | `0/0` |
| Migration graph | One head: `20261015_org_shipment_stages` |
| Product mutation during audit | None |
| Observable target movement | None; fetch-stable and clean |

The Codex task-inventory UI did not return during one bounded read-only check. The audit therefore does not claim an application-wide task census. It proceeded because the target repository itself was clean, fetch-aligned, unchanged throughout inspection, and no Product implementation process or canonical movement was observable.

## Route inventory

Forwarder declares 41 route entries: 38 substantive routes, two compatibility redirects, and one wildcard route. All were inventoried; 31 major user-facing surfaces were inspected in detail.

### Public and Customer

`/`, `/about`, `/contact`, `/customer`, `/customer/enroll`, `/customer/forgot-password`, `/customer/reset-password`, `/verify-email`, `/customer/requests`, `/customer/requests/new`, `/customer/requests/:requestId`, `/customer/shipments`, `/customer/shipments/:shipmentId`, `/customer/documents`, `/customer/profile`, `/customer/change-password`, `/customer/track/:requestId`, `/project/track/:trackingCode`.

### Expert and operations

`/expert`, `/expert/requests/:id`, `/crm`, `/customers`, `/operations`, `/operations/shipments`, `/operations/shipments/new`, `/operations/shipments/:id`, `/operations/shipments/:id/:section`, `/operations/work-queue`, `/operations/control-tower`, `/operations/intelligence/:id`, `/operations/projects/:projectId/units`, `/dashboards`, `/dashboards/:public_id`, `/dashboards/:public_id/edit`.

### Administration

`/admin`, `/admin/customers`, `/admin/customer-portal-accounts`, `/user-management`.

### Compatibility and fallback

`/customer/:customerId` and `/request/:requestId` redirect to canonical routes; `*` is the fallback.

## Role-based audit

### Customer

- Primary job: submit a freight request, reach a commercial agreement, and understand shipment status without seeing internal operational complexity.
- Common actions: create request; review status; respond to or accept a quote; open shipment/tracking; review/download documents and deliveries.
- Essential information: current request/shipment status, route, quote state, the one action currently available, latest meaningful position, ETA or a human reason for unavailability, delivery and document state.
- Overexposed: repeated request facts, long histories, technical timestamps, raw or semi-technical status labels, and full detail blocks before the current action.
- Buried: quote response/acceptance on long request detail; the latest meaningful shipment change; the difference between current state and historical reports.
- Navigation burden: request facts, quote thread, status, shipment, documents, delivery, and history are all reachable, but the user often scrolls rather than follows a task-oriented sequence.
- What the Product does not explain well: what changed, why an ETA is unavailable in plain language, and exactly what will happen after the current customer action.
- Safe to hide: source/provenance, internal identifiers, historical technical metadata, full route-leg detail, older reports, and completed actions.

### Expert

- Primary job: triage commercial and operational work, record authoritative facts, resolve exceptions, and advance each Shipment safely to closure.
- Common actions: assign/review Request; prepare/revise Quote; create Shipment; record route/stage/tracking/allocation/delivery facts; resolve document or closure blockers.
- Essential information: prioritized queue, current operational stage, current exceptions, owner, latest meaningful update, task readiness, and one state-derived next action.
- Overexposed: every provenance field, version, timestamp, source ID, all possible edit forms, policy explanations, reconciliation detail, and repeated summaries.
- Buried: the cross-domain next action, closure readiness, and the distinction between ordered stage progress and independent readiness tasks.
- Navigation burden: Expert Home, Operations Home, Shipment List, Control Tower, Work Queue, and nine Shipment-local destinations distribute one operational mental model across several surfaces.
- What the Product does not explain well: which Shipment should be opened first, what changed since the last visit, why one task blocks another, and what follows after a successful action.
- Safe to hide: raw UUIDs, route revision internals, inactive configuration, completed technical metadata, full audit fields, and non-actionable explanations.

### Organization Admin

- Primary job: configure tenant users, references, operational locations, route defaults, document policy, stages, SLA, and closure rules safely.
- Common actions: manage users/roles; activate reference data; maintain Organization Locations; set route time/distance; set document/stage/closure policy.
- Essential information: configuration scope, current effective value/version, affected organization, publication/effective state, validation problems, and the primary save/publish action.
- Overexposed: a flat grid of up to roughly 20 tabs, long explanatory blocks, full history and editing controls together, and System-level concepts mixed into the same landing space for dual-role users.
- Buried: the difference between organization-owned policy and governed base reference; the most common setup sequence; where a current operational behavior is configured.
- Navigation burden: one global admin destination opens a second large tab matrix, then cards/details/forms within the selected tab.
- What the Product does not explain well: configuration ownership, blast radius, effective version, and which settings are prerequisites for normal operation.
- Safe to hide: historical versions, raw reference codes, advanced fields, inactive entries, and destructive actions until explicitly requested.

### System / Platform Admin

- Primary job: govern base reference catalogs, geography, document-type definitions, and other cross-tenant foundations without impersonating tenant operations.
- Common actions: inspect/import/activate reference versions; manage catalog definitions; review global location/network data; validate governed values.
- Essential information: catalog/version identity, governance status, usage/impact, activation state, and validation outcome.
- Overexposed: Organization Admin tabs and tenant configuration when the same person has both roles; raw codes and editing controls before scope is established.
- Buried: a clear System workspace boundary and the downstream organization impact of changing a governed reference.
- What the Product does not explain well: “system definition” versus “organization activation/configuration.”
- Safe to hide: tenant-specific operational controls, full raw payloads, import diagnostics, and old versions until requested.

## Page-by-page inventory

Counts are approximate initial-view totals. `FC` = form controls, `VA` = visible actions, `TB` = major explanatory/text blocks.

| Route / page | Role | Primary user goal | Current primary action | Secondary actions | Visible information groups | Cards | FC | VA | TB |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| `/` landing/login | Public/Expert | Enter Product or understand service | Login / role entry | About, contact, tracking | Value, login, navigation | 1 | 2 | 2 | ~4 |
| Customer auth set | Customer | Enroll, login, recover access | Submit auth form | Switch/recover/verify | Credentials, validation, guidance | 1 | 2–6 | 1–2 | 2–4 |
| `/customer/requests` | Customer | Find a request | Open request / create request | Paging/filtering | Status, route, date, identity | ~3+ | 0–2 | 2–4 | ~6 |
| `/customer/requests/new` | Customer | Submit request | Create request | Edit cargo/route | Request, route, cargo, dates, instructions | ~2 | ~10 | ~2 | ~6 |
| `/customer/requests/:id` | Customer | Understand request and act commercially | Context-dependent quote action, below facts | Discuss, accept/reject, history | Status, route, cargo, schedule, instructions, quote, thread, history | ~10 | 0–6 | ~5 | ~23 |
| `/customer/shipments` | Customer | Find active shipment | Open shipment | Search/page | State, route, latest update | ~10 at page size | ~1 | ~9 links | ~30 |
| `/customer/shipments/:id` | Customer | Track shipment outcome | Context-dependent view/download | Anchor navigation | Summary, cargo, routes, reports, docs, deliveries, timeline | ~10 | 0–2 | ~5–9 | ~35 |
| `/customer/documents` | Customer | Find available documents | Open/download | Filter/page | Document identity, context, status | ~1 list shell | ~1 | ~3 | ~6 |
| `/customer/profile` + password | Customer | Maintain own account | Save | Change password | Identity/contact/security | 1 | 4–7 | 1 | 2–4 |
| `/customer/track/:id` | Public/Customer | Check request status safely | Track/open current state | None/minimal | Request state, public timeline | ~5 | 0–1 | ~1 | ~20 |
| `/project/track/:code` | Public | Check project tracking | Track | None/minimal | Project/status/milestones | ~3 | 1 | ~4 | ~9 |
| `/expert` | Expert | Triage commercial requests | Open/assign/start follow-up | KPI/filter/status tabs | KPI, filters, status buckets, request cards, next commercial action | ~18 | ~1 | ~8+ | ~19 |
| `/expert/requests/:id` | Expert | Complete commercial Request workflow | State-derived commercial action | Assignment, quote, CRM, documents, history | Status, customer, request, cargo, quote, CRM, shipment, audit | ~57 component/card uses | ~5 | ~9+ | ~40 |
| `/crm` + `/customers` | Expert/Admin | Find/link customer | Open/create/link | Search/edit | Customer identity, portal/link state | 0–3 | 0–3 | 1–4 | ~5 |
| `/operations` | Expert | See operational situation | Open attention item | Refresh/filter/open active shipment | KPIs, attention reasons, active shipments, last updates | ~12 | 0–2 | ~2+ | ~24 |
| `/operations/shipments` | Expert | Prioritize and open shipment | Open shipment | Filter, saved view, new operation | Seven filters, customer, route, dates, owner, latest update, project/source IDs, milestone/open items | 1 + card per row | 7 | 3+ | ~8 per row |
| `/operations/shipments/new` | Expert | Create explicit Shipment | Create Shipment | Source/quote/route/cargo/review actions | Source, customer, quote, route, cargo, review | ~5 | ~17 | ~6 | ~20 |
| Shipment `summary` | Expert | Understand Shipment now | Route-derived next action | Navigate to nine sections | UUID/customer/owner, routes, transport, last event, milestone/freshness, open items | ~4–6 | 0–2 | 1–3 | ~12 |
| Shipment `route` | Expert | Plan/execute route | Record departure/arrival or author route | Edit plan/execution/issues/actions/replan | Plan, legs, execution, references, actuals, issues, actions, project units, finance, reconciliation, checkpoints, exceptions | 10+ | ~32 across components | 20+ | 40+ |
| Shipment `stages` | Expert | Advance ordered operational stages | Start/complete eligible stage | Timestamp entry | Five-stage sequence, required/optional, status, audit cues | ~2 | ~1 | ~2 | ~8 |
| Shipment `cargo` | Expert | Reconcile cargo and allocation | Record/edit allocation or cargo fact | Transfer/correct/reopen | Requested/planned/actual cargo, planned/actual allocation, destination, differences | ~4–7 | ~15 | ~9 | ~25 |
| Shipment `documents` | Expert | Satisfy document requirements | Upload/apply current document action | Replace/link/review/approve/reject/verify | Requirements, applicability, upload, completeness, review state | ~7+ | ~6 | 15+ | ~25 |
| Shipment `tracking` | Expert | Record position/progress and understand ETA | Add report/progress | Correct/reopen/view provenance | Human description, structured progress, ETA, unavailable reason, report history | ~5–8 | ~14 | ~11 | ~30 |
| Shipment `delivery` | Expert | Record partial/final delivery | Create delivery | Correct/reopen/view evidence | Actual cargo, delivery quantity, destination, finality, prior deliveries | ~4+ | ~6 | ~9 | ~19 |
| Shipment `closure` | Expert | Decide and execute closure | Close normally/exceptionally when allowed | Refresh/follow blocker links | Criteria, blockers, warnings, completed checks, version/time metadata | ~4 | ~1 | ~5 | ~11 |
| Shipment `history` | Expert | Understand what happened | Filter/inspect event | Page/load more | Chronology, actor, stage, quantities, route revisions, relationships | ~1 shell + event rows | ~1 | ~4 | up to ~30/page |
| `/operations/work-queue` | Expert | Resolve governed work items | Open decision context | Claim/complete/open Shipment | Work item type, subject ID, status, assignee, due/legacy data | ~2 shells + card/row | ~2 | ~4+ | ~8/item |
| `/operations/control-tower` | Expert | Find most urgent shipments | Open shipment/exception | Attention filter, search, refresh | Attention, Shipment reference, requested/actual route, owner, reasons/times | card/item | ~1 | 2–5 | ~12/item |
| `/operations/intelligence/:id` | Expert | Decide an exception/action | Perform allowed decision | Inspect context | Situation, evidence, options, history | ~5 | ~2 | ~8 | ~15 |
| `/dashboards*` | Expert/Admin | View/build analytics | View/save dashboard | Add/configure widgets | Widget registry, filters, layout, query state | 2+ / builder-heavy | up to ~12 | up to ~12 | ~12 |
| `/admin` | Org/System Admin | Find and change configuration | Tab-specific save/publish | Select among up to ~20 tabs | Role summary, user/access, refs, locations, docs, SLA, stages, closure, networks | header + selected cards | selected form; up to ~12 | 10–20 tab choices + actions | 10+ |
| `/user-management` | Org Admin | Manage users/roles | Create/update user or role | Activate/deactivate/filter | Users, roles, permissions, status, forms | ~9 | ~20 | ~11 | ~19 |
| System reference/catalog surfaces | System Admin | Govern definitions | Import/activate/save definition | Alias, deactivate, inspect | Catalog version, codes, labels, hierarchy, usage | ~6–12 | 1–12 | 3–15 | 10–31 |

## Information-density classification

| Surface | Primary — remain visible | Secondary — quieter | On demand | Remove / merge from immediate view |
|---|---|---|---|---|
| Expert Home / Operations Home | Attention queue, active count, changed items, ready actions | Owner and route summary | raw evaluation/provenance | Merge duplicate operational homes and repeated KPI cards |
| Shipment List | Shipment label, customer, route, current stage, attention, latest meaningful update, next action | owner, planned dates | source IDs, project ID, full timestamps | Replace row cards and repeated paragraphs with one prioritized table/list |
| Shipment Summary | identity, customer, owner, overall state, requested/operational route, current stage, ETA/reason, attention, next action | task completion count, last update | provenance, full route/reconciliation details | Merge repeated state summaries; do not repeat section contents |
| Route & Execution | operational route, active leg, execution/equipment, current event action, issues | planned vs actual times, route-reference variance | revisions, finance, project-unit internals, old events | Separate execution task from configuration/reconciliation/history |
| Cargo & Allocation | six quantity concepts in one comparison, mismatch/unknown state, primary correction action | destinations/UOM | lineage, reopen/correction audit, transfer form | Merge multiple summary cards and duplicate quantities |
| Documents | requirement, required/optional, current completeness/review state, one applicable action | uploader/date | prior versions, policy provenance, all alternate actions | Replace card-per-document/action wall with rows and context action |
| Tracking & ETA | latest human position, structured progress, ETA or reason, report CTA | last report time, progress quality | ruleset/provenance, complete report history, technical timestamps | Merge repeated route/progress text |
| Delivery | delivered/actual relationship, remaining quantity, partial/final state, destination, create action | evidence note | historical corrections and internal links | Hide creation form until invoked; merge per-cargo summary cards |
| Closure | large READY/NOT READY verdict, blocker count/list, warning count, completed X/Y, one closure action | policy label/version | criteria provenance and evaluation timestamps | Collapse policy explanation and completed details by default |
| History | time, human event label, actor, concise consequence | category and affected domain | raw event code, revision relationship, quantity payload | Merge duplicated fields; keep history distinct from tasks |
| Admin | scope, current effective value/status, primary save/publish | concise impact and prerequisites | history, raw codes, advanced settings | Group tabs by workspace; remove flat all-concepts-at-once navigation |
| Customer Request | current status, quote/next action, concise request identity | route/cargo/date summary | full original instructions, history, technical metadata | Merge repeated fact cards and move commercial action above fold |
| Customer Shipment | overall state, route, latest position, ETA/reason, delivery/docs attention | cargo summary | full leg/report/document/delivery history | Keep a concise overview and disclose domain details by section |

## Card audit

### Card-overuse hotspots

1. Expert Request workspace: a very large component with roughly 57 card usages across commercial, CRM, Shipment, document, and history concepts.
2. Shipment Route & Execution: active plan, each leg, execution, reference time, actual route, issues, actions, finance, reconciliation, checkpoints, replan, and exceptions all compete in one section.
3. Customer Request Detail: about ten vertically stacked cards before the user reaches all commercial and historical context.
4. Customer Shipment Detail: separate cards for cargo, route, reports, documents, deliveries, and history create a long single-page reading task.
5. Expert Home / Operations Workspace: KPI cards plus multiple attention cards plus shipment/update cards; exceptions become a wall rather than a queue.
6. Admin: header/role card, large tab grid, selected configuration cards, nested details, and release identity.
7. Documents and cargo/allocation: repeated item cards carry similar fields and actions that would scan better as rows or compact comparison tables.

### Classification

| Current card concept | Classification | Reason |
|---|---|---|
| One Shipment identity/context header | JUSTIFIED | Creates stable workspace context if concise |
| KPI cards on role home | BETTER_AS_INLINE_SUMMARY | Three to four numbers can live in one status strip |
| Shipment list row cards | BETTER_AS_TABLE | Operators need cross-row comparison and prioritization |
| Attention item cards | BETTER_AS_LIST | Severity, reason, stage, and next action should scan vertically |
| Route legs | BETTER_AS_TIMELINE | Ordered spatial/temporal sequence is the semantic model |
| Ordered operational stages | BETTER_AS_TIMELINE | Past/current/future need a single process view |
| Independent Shipment domains | BETTER_AS_LIST | They are tasks with independent status, not process steps |
| Cargo quantity cards | BETTER_AS_TABLE | Requested/planned/actual/allocation/delivered need side-by-side comparison |
| Document requirement cards | BETTER_AS_ROW | Same fields/actions repeat per requirement |
| ETA provenance/ruleset card | BETTER_AS_ON_DEMAND_DETAIL | Supports trust but is not the current task |
| Closure blocker/warning summary | BETTER_AS_INLINE_SUMMARY | Readiness, counts, and next action must dominate |
| History event cards | BETTER_AS_TIMELINE | Chronology is primary; borders around every event add noise |
| Admin history/version cards | BETTER_AS_ON_DEMAND_DETAIL | Needed for governance, not normal configuration |

## Navigation audit

### Current hierarchy

Global/product navigation → role surface → operations navigation (up to eight destinations) → Shipment-local navigation (nine destinations) → section-local accordions/details/forms. On several screens this becomes four or five conceptual layers.

### Navigation-depth hotspots

- Shipment Route & Execution: global → operations → Shipment section → nested details/accordions → embedded action form.
- Admin: global → admin → up-to-20-tab grid → selected module → card/details/history/action.
- Expert commercial request: global → Expert queue → Request → internal tabs → nested quote/CRM/document actions.
- Customer Shipment mobile: customer navigation → shipment page → five fixed anchors → section/card detail.
- Dashboards: global → dashboards → selected dashboard → widget → widget configuration.

### Target depth rule

Use at most `Global context → Workspace context → Task`. A fourth layer is acceptable only as on-demand detail, not as another persistent navigation system.

## Action-hierarchy audit

| Surface | Primary action today | Competing actions / risk | Assessment |
|---|---|---|---|
| Expert Home | Open/assign/follow up a Request | KPI filters, eight status buckets, per-card actions | Primary queue action diluted |
| Operations Home | Open attention item | Refresh, several large attention cards, open Shipment | Exception reason is visible but priority is not concise |
| Shipment List | Open a Shipment | Seven filters, saved views, active toggle, new operation | Creation and triage compete; row action lacks next-task label |
| Shipment Summary | Route event/route authoring | Up to multiple leg actions; nine section links | State-derived but route-only and not always singular |
| Route & Execution | Record event | Author/edit route, execution, issues, actions, reconciliation, replan | Severe competition between operations and configuration |
| Documents | Upload/review/apply | Replace, link, remove, applicable, reject, approve, verify | More than three actions can compete per requirement |
| Delivery | Create delivery | Correct/reopen/evidence plus visible forms | Current task and historical maintenance compete |
| Closure | Close | Refresh/follow blockers/exceptional close | Readiness verdict should precede actions |
| Customer Request | Quote response/acceptance | Discussion, reject, navigation, history | Commercial action appears after extensive facts |
| Admin | Save/publish selected setting | Tab matrix, activate/deactivate, history, aliases | Configuration and navigation occupy equal emphasis |

Dangerous or exceptional actions generally exist behind permission and state checks—a strong foundation—but visual differentiation is inconsistent. Exceptional close, reject, deactivate, reopen, and correction should not share emphasis with the normal primary action.

## Next-action audit

The current Shipment “next action” implementation is genuinely state- and permission-derived for route authoring and route-leg departure/arrival events. That is a good foundation. It is not a Shipment-wide next-best-action engine: it does not synthesize cargo/allocation, documents, tracking/ETA, operational stages, delivery, or closure readiness, and may display more than one leg action.

`NEXT_ACTION_ACCURACY = 4/13 exact; 9/13 incomplete or absent at the Shipment-wide level.`

| Current Product state | Current next action | Expected next action | Match |
|---|---|---|---|
| Shipment created | Route authoring when no active plan | Define operational route | YES |
| Route missing | Route authoring component | Define/publish operational route | YES |
| Execution missing | No synthesized Shipment action; user explores Route | Add execution/equipment for active leg | NO |
| Allocation incomplete | Warning/detail in cargo domain | Complete/correct actual allocation | NO |
| Tracking missing | No synthesized Shipment action | Add first position report when operationally due | NO |
| Structured progress missing | No synthesized Shipment action | Record route progress or explain prerequisite | NO |
| ETA unavailable | Reason exists in tracking detail | Resolve actionable prerequisite; otherwise show non-actionable reason | PARTIAL / NO |
| Documents requiring attention | Requirement state and many local actions | One highest-priority document action | NO |
| Operational stage in progress | Start/complete action on Stages tab | Complete current stage | NO at Summary; YES locally |
| Final Delivery missing | Delivery area shows semantics/actions | Record final delivery after prerequisites | NO at Summary |
| Closure blockers | Closure list with source links | Open highest-priority blocker | PARTIAL / NO |
| Ready to close | Closure action exists on Closure tab | Close Shipment | NO at Summary; YES locally |
| Closed | “Correct and complete records” route-area framing | Show closed state; expose only permitted corrective maintenance on demand | NO |

Permissions are respected locally. Blocker explanations are often accurate, but multiple valid actions are not ranked. The target should select one recommended action and expose other valid actions as secondary.

## Process visibility

`PROCESS_VISIBILITY_CURRENT = PARTIAL.`

- The five ordered road stages exist and clearly support start/complete progression.
- Completed/current/remaining stage information is available on the dedicated `stages` route.
- The current stage is sometimes summarized elsewhere, but the full process is not visible from the Shipment Summary or list.
- No concise stage completion count or progress indicator is present in the primary Shipment context.
- An Expert cannot reliably understand ordered operational progress within five seconds without selecting the Stages section.

Recommended target: a compact five-stage strip on Summary and a current-stage cell on Shipment List; the detailed event controls remain on the Stages section.

## Task-list audit

`TASK_LIST_CURRENT = ABSENT AS A UNIFIED MODEL.`

The domain data needed for a useful checklist exists, but status is distributed across nine sections. A unified independent task list is valuable if it remains derived, concise, and never pretends that independent tasks are a linear process.

| Domain | Current evidence | Target status vocabulary |
|---|---|---|
| Route | Active/draft plan and leg state | DONE / IN_PROGRESS / BLOCKED |
| Execution | Means/equipment and leg execution state | DONE / NEEDS_ATTENTION / OPTIONAL |
| Cargo | Requested/planned/actual facts | DONE / IN_PROGRESS / NEEDS_ATTENTION |
| Allocation | Planned/actual allocation and mismatch | DONE / NEEDS_ATTENTION / OPTIONAL |
| Documents | Requirement/applicability/review/completeness | DONE / NEEDS_ATTENTION / OPTIONAL / BLOCKED |
| Tracking | Latest report/freshness | DONE / IN_PROGRESS / NEEDS_ATTENTION |
| ETA | Available or explicit reason | DONE / NEEDS_ATTENTION / BLOCKED / OPTIONAL |
| Operational stages | Current/completed stage sequence | IN_PROGRESS / DONE / BLOCKED |
| Delivery | Partial/final facts | IN_PROGRESS / DONE / BLOCKED |
| Closure | Criteria evaluation | BLOCKED / NEEDS_ATTENTION / DONE |

## Past, current, and future separation

- `WHAT HAPPENED`: Unified History exists and is the correct append-only source, but route revisions, quantities, actors, and technical relationships can dominate the event label.
- `WHERE I AM`: current Shipment state is distributed among header, latest event, current milestone, stage tab, tracking, ETA, and attention systems.
- `WHAT I NEED TO DO`: route-derived actions, work queue, attention cards, document actions, stage actions, delivery actions, and closure actions are separate.

These concepts are most mixed in Route & Execution, Customer Shipment Detail, Expert Request Detail, and the Operations Workspace. The target must not turn History into a task list; it should synthesize current state and future work separately from the chronology.

## Exception-based operations

### Shipment List

Current rows are two-column cards containing customer, route, planned dates, owner, latest update, project ID, source Request/Quote IDs, milestone, and open-item count. They omit a clear attention state, ordered stage, and explicit next action. Operators must read each card instead of compare rows.

- ESSENTIAL: Shipment human label, customer, route, current stage, attention reason/severity, latest meaningful update, next action.
- SECONDARY: owner, planned departure/arrival, completion summary.
- ON DEMAND: project ID, source Request/Quote IDs, raw UUID, route/source provenance.

### Operations Home / Control Tower

The Product has strong exception foundations: attention evaluation, freshness, severity filters, reasons, owners, Control Tower, and a governed work queue. The Operations Home renders too many large cards and technical reason fields; the Control Tower is closer to the target but still uses a full Shipment reference/UUID and card-per-item detail. Neither fully answers “which Shipment should I open now?” as a short ranked queue.

### Role Home

Expert Home is primarily a commercial Request console, while Operations Home handles operational attention. The split is domain-correct but creates two “homes.” No single landing experience answers active shipments, attention, changes since last visit, next Shipment, and ready work together.

## Shipment Summary against the requested target

| Target block | Current state | Finding |
|---|---|---|
| Header: identity/customer/owner/state | Present, but raw UUID is prominent and status/context span several blocks | PARTIAL |
| Route: requested/operational | Present | GOOD but could be more concise |
| Current operation: stage/latest position/ETA reason | Distributed; stage detail and ETA live on other routes | HIGH GAP |
| Progress: ordered stages + task readiness | No unified Summary presentation | HIGH GAP |
| Attention: only current blockers/warnings | Open items and external attention systems exist; Summary does not provide a concise prioritized set | HIGH GAP |
| Next action: one state-derived CTA | Route-derived and permission-aware, but incomplete and sometimes plural | HIGH GAP |

## Major Shipment surfaces

### Route & Execution

- PRIMARY: operational route, active leg, current execution/equipment, current departure/arrival state, operational issue, one event action.
- SECONDARY: requested route comparison, planned vs actual time, reference time/distance, active means details.
- DETAIL: revisions, finance, project-unit internals, historical actual-route events, full reconciliation, checkpoint/milestone configuration, exception history.
- Current problem: operational actions, authoring, configuration, reconciliation, finance, and history share one scroll surface. Raw IDs are sometimes secondary but remain too prominent.

### Cargo & Allocation

The data model correctly preserves Requested Quantity ≠ Planned Quantity ≠ Actual Cargo Quantity ≠ Planned Allocation ≠ Actual Allocation ≠ Delivered Quantity. The UI presents these across different cards, stages, and forms, so the user must remember values while scrolling. Unknown actual cargo is preserved correctly; the presentation needs one comparison matrix and action based on the first unresolved difference.

### Documents

Requirement, uploaded file, applicability, review, and completeness are correctly separate. Required/optional semantics exist. Current rows/cards expose too many simultaneous actions and policy/provenance detail. A requirement table with one state-derived action per row and an on-demand version/history drawer would materially reduce load.

### Tracking & ETA

Human position description, structured route progress, ETA calculation, and ETA-unavailable reason are correctly distinct—a major Product strength. Current presentation makes users parse reports, progress controls, timestamps, and provenance to find the latest truth. The newest human position, structured progress, and ETA/reason should form one top summary; ruleset/provenance belongs on demand.

### Delivery

Partial/final delivery, structured destination, quantity, evidence, and Actual Cargo separation are correctly modeled. Per-cargo cards and visible creation/correction controls increase density. The creation form should open from a single action, while a compact comparison row shows Actual Cargo, Delivered, Remaining/Unknown, and finality.

### Closure

The evaluation correctly distinguishes blockers from warnings and provides source links and normal/exceptional actions. The page lacks an immediate dominant `READY` / `NOT READY` verdict and concise X-of-Y completion. Users must interpret the criteria list and policy text before acting.

### Unified History

The chronology is coherent and domain-spanning. It is not the task list and should remain append-only. Technical fields—route revisions, replacement relationships, quantity payloads, source codes—make scanning harder. The category filter operates on the currently loaded page rather than querying the full history, so filtered results can appear empty even when older matching events exist. Grouping by day and concise human event summaries are warranted; raw payload remains on demand.

## Admin configuration UX

Admin tolerates more complexity than Expert workflows, but the current flat tab matrix exposes too much at once. A dual-role admin can see user/access, organization settings, operational policy, base references, geography, document definitions, SLA, stage configuration, route times, logistics networks, reasons, and other foundations in one navigation block.

Recommended grouping:

1. People & Access — users, roles, portal accounts.
2. Organization Operations — locations, route references, document policy, SLA, stages, closure.
3. Organization Data — activated references, cargo catalog, local network.
4. System Governance — base references, geography, document types, global networks, reason definitions.

System governance must remain a separate scope even when one person holds both roles. Configuration controls must not appear beside live operational actions; current leakage is primarily navigational/contextual rather than a violation of permission boundaries.

## Text and copy density

| Classification | Examples | Treatment |
|---|---|---|
| REQUIRED_CONTEXT | Unknown is not zero; closure blocker meaning; stale attention warning | Keep concise and adjacent to state |
| HELP_TEXT | What structured progress means; required vs optional documents | One sentence or contextual help |
| BETTER_AS_TOOLTIP | technical provenance, field definitions, route-reference variance | Reveal on focus/hover and remain keyboard accessible |
| BETTER_AS_EMPTY_STATE | no route, no reports, no documents, no deliveries | Explain why it matters and offer the valid first action |
| BETTER_AS_DOCUMENTATION | policy model, detailed ruleset explanation, import/reference mechanics | Link to admin/help documentation |
| REDUNDANT | repeated route/status/identity text and repeated “this is derived from…” paragraphs | Remove or merge |

Normal workflows currently require too much paragraph reading, especially Request Detail, Route & Execution, ETA, closure, SLA/admin, and attention monitoring.

## Visual density

- Vazirmatn typography is acceptable and should remain.
- Repeated white cards on a pale background flatten hierarchy because every concept gets the same border, radius, and spacing.
- Card-within-card and details-within-card patterns are common in route, cargo, documents, and admin.
- Large vertical gaps coexist with dense controls, producing long pages without improving comprehension.
- Heading density is high; many sections use label + heading + explanation + card title before the first actionable value.
- Tables/lists are underused where cross-item comparison is the real job.

## Mobile and small viewport

No BLOCKER or HIGH responsive defect was proven in the exact-SHA captures. Global and local controls generally wrap, mobile customer navigation is available, forms remain interactable, and no decisive horizontal overflow was observed.

The material medium issue is stacked density: long cards become much longer on mobile, primary actions can fall several screens below context, nine Shipment-local destinations require a compact scrollable/overflow pattern, and process progress needs a mobile vertical representation. Raw IDs and mixed RTL/LTR strings consume disproportionate space. This is a responsive adaptation requirement, not a separate mobile redesign.

## Practical accessibility and interaction

- Positive: semantic buttons/links, labels, alerts/status regions, `aria-current`, `aria-pressed`, visible focus-ring classes, and text labels usually accompany status color.
- Needs improvement: action names sometimes describe mechanics rather than outcome; dense action groups weaken keyboard discoverability; raw LTR identifiers inside RTL flow can wrap awkwardly; modal/drawer use is limited, leaving forms in the page; focus return and announcement should be specified for future drawers/modals.
- Status must continue to use icon/text/label as well as color.
- Tooltips must never be the only path to essential information and must work by keyboard and touch.

## Previous Human findings recheck

| Finding | Current classification | Evidence-based assessment |
|---|---|---|
| Page/card density | STILL_PRESENT | Major across Request Detail, Route, Customer Shipment, Operations Home, Admin |
| Too much explanatory text | STILL_PRESENT | Long help/provenance/policy text precedes actions on several surfaces |
| Giant-page/accordion problem | PARTIALLY_RESOLVED | Route-based Shipment IA exists; Route, Request, Customer Shipment, and Admin remain giant internal surfaces |
| Raw geography enum leakage | RESOLVED | Canonical location labels are used in audited primary flows |
| Raw transport enum leakage | PARTIALLY_RESOLVED | `transportLabel` exists, but values such as `customer_choice` still appear in evidence |
| Raw Execution IDs | PARTIALLY_RESOLVED | Semantic execution context exists; UUIDs/means identifiers still receive excessive prominence |
| English copy inside Persian UI | STILL_PRESENT | Technical statuses, seed labels, aliases/actions, and release/identity copy remain mixed in selected surfaces |
| Actual Cargo vs Actual Allocation clarity | PARTIALLY_RESOLVED | Correct semantics and labels exist but are distributed rather than instantly comparable |
| Delivery destination identity | RESOLVED | Structured destination is available and used; historical free text remains readable |
| ETA unavailable explanation | RESOLVED | Explicit reasons exist; hierarchy and concision still need improvement |
| Document foundation | RESOLVED | Policy, requirement, upload, review, and completeness exist; operational UX is dense |
| Closure foundation | RESOLVED | Exact blockers/warnings and actions exist; readiness presentation remains partial |
| Unified History | RESOLVED | Coherent domain history exists; technical noise/filter scope remain UX gaps |
| Shipment Workspace structure | PARTIALLY_RESOLVED | Nine route-based sections prevent one mega-page; local density remains high |
| Next Action | PARTIALLY_RESOLVED | State/permission-derived route actions exist; Shipment-wide derivation is incomplete |
| Operational Stage visibility | PARTIALLY_RESOLVED | Dedicated ordered stage surface exists; Summary/List lack immediate process visibility |

## Safe gamification opportunity audit

| Candidate | Classification | User behavior supported | Display pattern | Why it helps | Risk | Guardrail |
|---|---|---|---|---|---|---|
| Shipment stage completion | USEFUL | Accurate progression through ordered stages | `3 of 5` plus subtle stepper | Makes current stage and remaining path visible | Completing a stage prematurely | Derive only from authoritative stage events; no manual points |
| Independent task completion | USEFUL | Operational hygiene across domains | `6 of 9 tasks ready` checklist | Reduces recall and supports closure preparation | Treating optional tasks as failures | Policy/state-derived applicability; show optional separately |
| Operational readiness | USEFUL | Complete prerequisites before action | Readiness strip with blockers | Converts complexity into actionable state | Oversimplification | Always link to underlying evidence and preserve unknown |
| Daily update completeness | USEFUL | Keep active Shipments meaningfully current | `9 of 12 active shipments current` | Supports exception-based review | Incentive to submit low-quality updates | Count authoritative freshness, not number/speed of updates; no rewards |
| Document completeness | USEFUL | Meet explicit organization policy | `4 of 5 applicable requirements complete` | Clarifies required/optional progress | Inventing legal necessity | Derive only from effective policy/applicability |
| Closure readiness | USEFUL | Resolve exact blockers | `4 of 6 criteria complete` | Gives completion feedback without hiding blockers | Gaming quantities or finality | Never score speed; blockers remain explicit; unknown remains unknown |
| Exception resolution | USEFUL | Reduce active operational risk | `2 attention items remaining` with quiet success state | Encourages clean operations | Closing alerts without solving cause | Count only system-confirmed resolution; preserve audit trail |
| Quote throughput points | RISKY | Faster commercial response | Score/points | May look motivating | Incentivizes premature/inaccurate terms | Do not implement scoring; at most show neutral queue age |
| Closure speed streak | REJECT | Fast closure | Streak | Misaligned with freight accuracy | Strong false-data incentive | Never implement |
| Expert leaderboard/badges | REJECT | Competition | Ranking/badges | No direct operational value | Distorts teamwork and truth | Never implement |

## Current-state conclusion

Forwarder has sufficient Product truth and workflow breadth to support the requested target without replacement architecture. The next mission should focus on a shared derived UX projection—current state, process stage, independent tasks, attention, and ranked next action—then apply it to Role Home, Shipment List, Shipment Summary, and closure before simplifying lower-priority detail surfaces.

