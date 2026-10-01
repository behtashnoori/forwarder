# Forwarder UX Gap Analysis

Current Product: canonical SHA `96a9d52602febc6ab1b9d29e92e83fe3eb7e8dd5`  
Target: **Forwarder Guided Operational Workspace**  
Method: read-only current → target comparison under LPAF v2.7.

## Result

| Severity | Count |
|---|---:|
| BLOCKER | 0 |
| HIGH | 9 |
| MEDIUM | 14 |
| POLISH | 5 |
| Total | 28 |

The qualified workflow remains completable; no RC/workflow blocker was found. High findings describe serious operator comprehension or task-prioritization gaps, not loss of Product correctness.

## High gaps

| GAP_ID | Role | Surface | Current state | Target state | User impact | Root cause | Severity | Effort | Dependencies | Recommended pattern |
|---|---|---|---|---|---|---|---|---|---|---|
| UX-001 | Expert | Role Home / Operations Home | Commercial Request console and Operations Workspace provide separate “home” concepts; neither alone answers active Shipments, attention, changes, next Shipment, and ready work. | One role landing experience with a compact status strip and ranked commercial/operational queues. | Expert must inspect multiple pages and choose work by recall. | Navigation mirrors subsystems rather than the operator’s daily prioritization job. | HIGH | L | Shared attention/task projection; meaningful-event feed | Task-oriented role home / exception queue |
| UX-002 | Expert | Shipment Summary | Identity, routes, last event, milestone, and open items exist, but stage progress, independent task readiness, ETA/reason, prioritized attention, and one next action are not synthesized. | Five-second Summary containing current stage, ordered progress, task readiness, attention, ETA/reason, and one CTA. | Shipment state cannot be understood at a glance. | Each domain renders itself; no cross-domain presentation projection. | HIGH | L | Derived task/attention/next-action contract | Decision summary with progressive disclosure |
| UX-003 | Expert | Shipment Next Action | Route authoring/departure/arrival actions are state/permission-derived, but other domains are absent and multiple leg actions may compete. | One ranked Shipment-wide next action with reason, direct deep link, expected outcome, and secondary valid actions. | User explores tabs and may work on a lower-priority task. | Next Action is implemented inside the route page rather than across lifecycle state. | HIGH | L | UX-002 projection; permission and policy inputs | Next Best Action |
| UX-004 | Expert | Shipment List | Card grid shows customer, route, dates, owner, project/source IDs, milestone, and open-item count; lacks concise attention, stage, and next action. | Sortable priority table/list with seven essential fields and on-demand metadata. | Cross-Shipment comparison is slow; identifiers displace actionable state. | Detail-card presentation chosen for a comparison task. | HIGH | M | Attention/stage/action projection; human Shipment label | Exception-based table/list |
| UX-005 | Expert | Route & Execution | Planning, active route, execution, event controls, references, actuals, issues, project units, finance, reconciliation, revisions, checkpoints, and exceptions share one long section. | Operate-first surface; planning/edit and audit/technical detail disclosed separately. | Primary operational action is buried among configuration and history. | Route-based IA fixed the outer mega-page but not inner task boundaries. | HIGH | L | Preserve route/execution authority; deep links | Task header + route timeline + drawers |
| UX-006 | Org/System Admin | Admin navigation | A dual-role admin can see roughly 20 flat tabs spanning people, organization policy, reference data, and system governance. | Separate People & Access, Organization Operations, Organization Data, and System Governance workspaces. | Admins struggle to locate configuration and understand scope/blast radius. | Components and permissions are exposed as peer navigation items. | HIGH | M | Existing role permissions; route/tab compatibility | Role/scoped configuration navigation |
| UX-007 | Customer/Expert | Request / Quote workspace | Large fact/card stacks precede or surround the current commercial action; discussion, accept/reject, assignment, CRM, Shipment, and history compete. | Status and one state-derived commercial action first; facts summarized; thread/history on demand. | Customer and Expert may miss the action or read extensively before acting. | Record-centric detail page grew across the full lifecycle. | HIGH | M | Existing commercial next-action truth | Task-oriented request workspace |
| UX-008 | All roles | Entity labels / localization | Raw UUIDs, technical statuses/reasons, `customer_choice`, source IDs, seed-like English labels, and some English actions remain prominent in Persian UI. | Human labels and localized terms primary; raw IDs/codes copyable secondary metadata. | Recognition and trust decrease; mobile scanning suffers. | Technical identity/provenance is rendered directly where human display contracts are incomplete. | HIGH | M | Human Shipment label/display contract; i18n inventory | Display-name contract + metadata drawer |
| UX-009 | Expert | Closure | Exact blockers/warnings/actions exist, but no dominant READY/NOT READY verdict or concise X/Y completion precedes policy/criteria detail. | Readiness verdict, completion count, ranked blockers, separate warnings, and one close action. | Operator must interpret policy output to decide if closure is possible. | Backend evaluation is exposed as criteria detail rather than a decision summary. | HIGH | M | Existing closure evaluation only | Readiness summary / checklist |

## Medium gaps

| GAP_ID | Role | Surface | Current state | Target state | User impact | Root cause | Severity | Effort | Dependencies | Recommended pattern |
|---|---|---|---|---|---|---|---|---|---|---|
| UX-010 | Customer | Customer Shipment | Cargo, route, reports, documents, deliveries, and timeline are a long card page with overlapping current/history content. | Concise outcome-focused overview with domain details and older history on demand. | Tracking requires scrolling and interpretation. | Internal domain topology leaks into customer presentation. | MEDIUM | M | Customer-safe projection | Overview + anchored details |
| UX-011 | Expert | Cargo & Allocation | Correct Requested/Planned/Actual Cargo/Planned Allocation/Actual Allocation/Delivered values appear in separate cards/forms. | One comparison matrix per cargo line with unknown/mismatch state and exact action. | User must remember values and can confuse cargo truth with allocation. | Presentation follows write models rather than comparison task. | MEDIUM | M | Existing cargo lineage/quantity APIs | Comparison table |
| UX-012 | Expert | Documents | Requirements and completeness are correct, but card-per-item/action groups can show upload, apply, replace, link, remove, review, approve, reject, and verify choices together. | Requirement rows with one current action; versions/policy/exception actions on demand. | High action competition and slower scanning. | All lifecycle controls are rendered adjacent to state. | MEDIUM | M | Existing permissions and document state | State-specific action row |
| UX-013 | Expert | Tracking & ETA | Human position, structured progress, ETA, unavailable reason, reports, timestamps, and provenance are all visible across dense blocks. | Current tracking truth and one action first; history/ruleset/provenance on demand. | ETA state takes too long to interpret. | Trust metadata is not visually separated from operational state. | MEDIUM | M | Existing ETA reason/progress model | Status summary + history drawer |
| UX-014 | Expert | Delivery | Accurate partial/final and structured destination semantics are presented with per-cargo cards and visible creation/correction controls. | Quantity/finality comparison row; focused create form opened by one action; history compact. | Current delivery task competes with maintenance detail. | Creation and historical maintenance share the same initial view. | MEDIUM | M | Existing delivery authority | Comparison summary + action sheet |
| UX-015 | Expert/Admin | Unified History | Coherent timeline contains extensive actor/stage/quantity/revision/replacement metadata; category filter applies only to loaded page. | Human event summary, day grouping, full-dataset filters, raw payload on demand. | Scanning is slow and filtering can misleadingly appear empty. | Audit payload and operational narrative share one level; client-side page filter. | MEDIUM | M | History query/filter support | Timeline + server-side filters |
| UX-016 | Expert | Operations Workspace | KPI cards plus multiple large attention cards and technical reason fields create a wall. | Compact counters plus ranked, human-readable exception rows. | Expert reads every exception instead of triaging. | Monitoring output is rendered as detail cards rather than a queue. | MEDIUM | M | Shared attention labels; UX-001 | Exception list |
| UX-017 | Expert | Control Tower | Better prioritization than Workspace, but each item is still a detailed card led by Shipment reference/UUID and many facts. | Concise priority rows; stage/reason/action visible; detail expands on demand. | Dense records reduce multi-Shipment scanning. | Operational detail and triage view are combined. | MEDIUM | M | Human label; shared attention projection | Expandable priority table |
| UX-018 | Expert | Work Queue / OIP | Work items often lead with technical subject type/public ID and “decision context.” | Human subject label, action reason, due/owner, and outcome-oriented action. | User must translate system objects before deciding. | Governance identifiers are primary labels. | MEDIUM | S | Display-name resolver | Humanized work-item rows |
| UX-019 | Expert | New Operation | Source, quote, route, cargo, and review logic live in a large component with many controls. | Guided multi-step creation with persistent summary and validation. | High initial cognitive load and error discovery late in the flow. | Entire creation model is exposed at once. | MEDIUM | L | Preserve creation API/validation | Progressive form stepper |
| UX-020 | All | Help/copy density | Explanatory paragraphs often precede values/actions; provenance language repeats. | One-line contextual help, tooltips for definitions, docs for policy detail, task-specific empty states. | Users read more than required for routine work. | Copy compensates for weak hierarchy and mixed concepts. | MEDIUM | S | Content inventory; no domain change | Layered help |
| UX-021 | Org Admin | Configuration modules | Forms, current policy, explanatory copy, history, and activate/deactivate actions frequently coexist. | Effective-state summary and primary edit/publish action first; history/advanced controls collapsed. | Admins can misread current versus editable state. | Read, edit, and audit modes are not separated. | MEDIUM | M | UX-006 grouping | View/edit mode + version drawer |
| UX-022 | Customer/Expert | Request and Shipment collections | Card-per-record layouts scale vertically and make comparison/filtering weak. | Compact rows/table with role-specific essential fields and explicit empty/filter states. | Finding an item gets slower as volume grows. | Detail-card pattern reused for collection tasks. | MEDIUM | M | Responsive row component | Responsive data list |
| UX-023 | All | Small viewport | Controls wrap and remain usable, but long cards, local navigation, raw IDs, and below-fold actions become disproportionately expensive. | Current state and CTA first; vertical progress; compact section selector; detail sheets. | Mobile tasks require excessive scrolling. | Desktop content order collapses without reprioritization. | MEDIUM | M | Implement alongside affected surfaces | Responsive priority layout |

## Polish gaps

| GAP_ID | Role | Surface | Current state | Target state | User impact | Root cause | Severity | Effort | Dependencies | Recommended pattern |
|---|---|---|---|---|---|---|---|---|---|---|
| UX-024 | All | Visual containers | Repeated border/radius/background cards and nested cards flatten hierarchy. | Cards only for true standalone objects; rows, dividers, and whitespace for related metadata. | Interface feels heavier than its information volume requires. | Card is the default container primitive. | POLISH | S | Component tokens | Container simplification |
| UX-025 | All | Time/metadata display | Multiple precise dual-calendar timestamps and version/source fields remain visible together. | One meaningful time primary; exact dual time and provenance on demand. | Visual noise and slower reading. | Audit precision shown in operational view. | POLISH | S | Shared date component | Primary/secondary timestamp pattern |
| UX-026 | All | Empty/success states | Empty states are accurate but inconsistent in tone/action; completion feedback is limited. | Positive, action-aware empty and completion states. | Product feels less guided after success or when no work exists. | States implemented per component. | POLISH | S | Shared state patterns | Empty/success state library |
| UX-027 | All | Interaction labels / bidi | Some buttons use technical/generic wording; long LTR IDs wrap inside RTL content. | Outcome-named actions and consistent `bdi`/truncate/copy treatment. | Minor comprehension and layout friction. | Local copy and identifier handling vary. | POLISH | S | i18n/copy pass | Outcome labels + ID chip |
| UX-028 | Expert/Admin | Heading and spacing rhythm | Label + heading + paragraph + card title often repeat before data; large gaps coexist with dense controls. | One page title, one task heading, concise metadata rhythm. | Page length and perceived complexity increase. | Independent components each render introductory hierarchy. | POLISH | S | Surface-by-surface composition pass | Shared task-section rhythm |

## Quick wins

`QUICK_WIN_COUNT=9`

| ID | Quick win | Why bounded |
|---|---|---|
| UX-008 | Demote raw IDs/codes and localize remaining primary labels | Display-only mapping and hierarchy work; no domain change |
| UX-009 | Add closure READY/NOT READY header and X/Y derived from existing evaluation | Existing authoritative closure output is sufficient |
| UX-012 | Show one contextual document action and move alternatives to overflow/detail | Existing state and permission rules already exist |
| UX-013 | Put current position/progress/ETA reason above provenance | Recomposition of existing facts |
| UX-014 | Collapse delivery form until “Record delivery” | Existing form and mutation stay unchanged |
| UX-020 | Remove/relocate repeated explanatory paragraphs | Copy/hierarchy only |
| UX-025 | Demote duplicate timestamps/version metadata | Shared presentation rule |
| UX-026 | Standardize positive empty/success states | Shared component/content pattern |
| UX-027 | Outcome-name actions and normalize RTL/LTR ID treatment | Localized copy and display utility |

Quick wins do not replace the structural work and should not be presented as a complete redesign.

## Structural gaps

`STRUCTURAL_GAP_COUNT=8`

| ID | Structural reason |
|---|---|
| UX-001 | Requires role-level prioritization model across commercial and operations |
| UX-002 | Requires a cross-domain Shipment presentation projection |
| UX-003 | Requires ranking valid actions across domains |
| UX-004 | Depends on shared stage/attention/action data in collection results |
| UX-005 | Requires inner Route/Execution task decomposition |
| UX-006 | Requires admin information-architecture grouping and compatibility plan |
| UX-011 | Requires normalized quantity comparison projection across cargo domains |
| UX-015 | Requires history query/filter behavior beyond local presentation |

## Root-cause synthesis

The gaps have four recurring causes:

1. **Component/domain projection instead of task projection.** Each subsystem is truthful, but the user must synthesize it.
2. **Cards as the universal container.** Repetition hides hierarchy and prevents cross-row comparison.
3. **All controls visible.** Normal, exceptional, corrective, historical, and configuration actions share the first view.
4. **Technical trust data presented as operational content.** IDs, provenance, versions, and timestamps are valuable but overexposed.

## Recommended implementation dependency order

1. Define human labels, shared status vocabulary, attention taxonomy, task applicability, and action-ranking contract.
2. Implement the Shipment derived UX projection without changing authoritative domain models.
3. Apply it to Shipment Summary, header, and closure.
4. Apply the same projection to Shipment List and Expert/Operations Home.
5. Decompose Route & Execution, then Cargo, Documents, Tracking/ETA, and Delivery.
6. Regroup Admin navigation and module view/edit/detail modes.
7. Simplify Customer and collection pages; finish visual/copy polish.

## Decision

The target can be reached with evolutionary presentation and query/projection work. A new workflow engine, new operational foundation, new analytics platform, or gamification economy is neither required nor justified.

