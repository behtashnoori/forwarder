# Post-D2 Product Gap Review — 2026-09-20

Scope: product traceability, gap classification, and release planning only. This review changes no runtime product file, test, migration, database, release artifact, donor repository, notification activation, Production system, or canonical branch.

## A. Current Product Baseline

### Baseline gate

| Gate | Verified result |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Canonical branch before review | `integration/golden-controlled` |
| Canonical HEAD / review parent | `138510c77a0228bc2e5c4e55c13cf7e996465df3` |
| Canonical upstream | `github/integration/golden-controlled` |
| Fresh local/remote ahead/behind | `0/0` |
| Starting worktree | clean |
| D2 product ancestry | `4a090c78856fd85a3dc2cc503841056c4fb6d3c5` is an ancestor |
| D2 synchronization evidence | `138510c77a0228bc2e5c4e55c13cf7e996465df3` |
| Alembic heads | exactly one: `20260923_notification_lifecycle` |
| Review branch | `codex/post-d2-product-gap-review`, created directly from canonical HEAD |

All required stop-gates passed. The canonical branch was not moved, and this review branch was not pushed.

### Product state through D2

The recovered Golden application remains the sole product authority. Controlled integration has completed:

- executable Golden contract freeze (`953a67ff5820864c08bc8727f34f49ed66237527`);
- governed worldwide geography (`a503d7b6473b90b01ff9a11c6e751375ff9f2121`);
- shared numeric presentation (`b523cc0b18fd48d93101de0430ec91d56a438c12`);
- request-versus-actual-route transport summaries (`d1dd6b60abc27846d563816c34b9aa4de190161a`);
- canonical Expert request count/list scope (`02acad646e2349296653bf0cf0bc5fe38519fb98`);
- EUR quote support (`49e2ceecee6b6ddbead7ae735fe15ecb63ed4869`);
- retired tracking add-unit action removal (`b623f7fa7135caac69798def574556140f78191f`);
- private logistics-point selector reachability (`b783052beead6fb5fb69fc34f796991208737b15`);
- inactive notification foundation and lifecycle hardening (`2d36f35d37a24d817a21c4e263ee59b6f19d0966`, `2bbc369effb70ca428b1dfb23b987bd16b8634bf`);
- isolated Control Tower backend and Golden frontend integration (`d0f2c57602d5d00320bb550935f9b9930d71f172`, `4a090c78856fd85a3dc2cc503841056c4fb6d3c5`).

D2 qualification recorded 1,258 backend passes, 69 frontend files/322 tests, TypeScript, production build, lint, source/package checks, and a one-head/no-pending migration check. Environment-dependent PostgreSQL suites and the packaged real-process launcher were not all executed at D2 and remain final-release gates.

The remaining approved product work is bounded to documents, dual-calendar presentation, simplified combined-transport intent, and simple quote communication. Control Tower needs one cross-feature authorization proof, not a product authorization rewrite. Mandatory cargo and notification activation are explicitly deferred. Modularization begins only after those product gaps close.

## B. Original Feedback Closure Matrix

Status vocabulary is applied to the original A–L requirement as a whole. A related implementation is not treated as closure when an accepted user-visible behavior remains absent.

| Topic | Exact status | Original user need | Current implementation and evidence | Actual remaining gap | More product input? | Recommended next action |
| --- | --- | --- | --- | --- | --- | --- |
| A. Geography | **COMPLETE** | Broad governed countries/locations, including Italy, Norway, and materially broader Iran coverage, with usable selectors. | B1 added the governed 249-country/115,208-location catalog, bounded search/paging, stable identity, inactive preservation, and honest Persian fallback labels; `a503d7b...`. | No product gap. Environment application remains an explicit controlled data operation, not runtime incompleteness. | No | Preserve B1 contracts; repeat PostgreSQL performance/reconciliation proof before RC. |
| B. Transport | **PARTIAL** | Clear request-level transport choice, including combined transport, without confusing it with the actual route. | B3 completed one deterministic request summary and separately ordered actual route modes; `d1dd6b6...`. Existing scalar request fields and transport catalog remain. | `حمل ترکیبی` is not an intake/catalog option. The formerly contemplated enumeration of ordered combinations is superseded by the approved simplification. | No | Add one scalar combined option to the existing request catalog/intake and summaries; keep route legs authoritative for the real sequence. |
| C. Cargo specs | **DEFERRED_BY_PRODUCT_DECISION** | Decide/enforce any additional mandatory cargo/product data. | Golden keeps cargo fields optional and preserves legacy/draft behavior; Phase A `953a67f...` characterized that contract. | None for this release path. | No | Preserve current optional behavior; do not add validation or migration. |
| D. Thousands separators | **COMPLETE** | Consistent grouping for business quantities and money without corrupting identifiers. | B2 introduced the shared precision-safe formatter and protected IDs/codes/phones; `b523cc0...`. | No current acceptance gap. | No | Reuse the shared formatter in future surfaces. |
| E. Request summary transport | **COMPLETE** | Show the request transport consistently and distinguish it from actual shipment legs. | B3 projects current request transport to Customer, Expert, tracking, Shipment Detail, and Control Tower consumers; `d1dd6b6...`, preserved through D2. | No gap for existing values. Combined becomes visible automatically after topic B is implemented and localized. | No | Preserve the B3 projection and distinction. |
| F. Dates/localization | **PARTIAL** | Correct, understandable localized dates/times and assignment facts. | Golden preserves instant versus Local Date semantics, actual assignment time, occurred versus recorded time, and timezone tests; Phase A `953a67f...`, D1/D2. | User-facing business dates are inconsistent and generally show only the locale-default calendar. The approved Gregorian + Jalali presentation is absent. | No | Introduce one shared dual-calendar presentation contract and adopt it only on the governed user-facing surfaces in Section F. |
| G. New-request counter | **COMPLETE** | New-request counters and visible request rows must use the same scope and refresh together. | B4 uses one tenant/role/assignment/search population before counts and pagination; `02acad6...`. | No product gap. | No | Preserve the shared query and mutation/refresh tests. |
| H. Gregorian + Jalali and EUR | **PARTIAL** | Show both calendars and support EUR quotes. | EUR create/read/respond/presentation is complete through B5 `49e2cee...`; currency contract is IRR/USD/EUR. | Dual-calendar presentation remains absent. | No | Close with the shared calendar slice; do not alter currency storage or conversion. |
| I. Quote customer response / communication | **PARTIAL** | Customer can accept, request discussion with a message, or reject; Expert can see the communication and issue a revised official quote. | Golden has authorized, idempotent `accepted`/`declined`, response time, unread/audit facts, multiple quote rows, and EUR; Phase A/B5. | No `نیاز به گفتگو` state, customer message, Expert display/history, or explicit revised-quote journey. | No | Add one response state plus one bounded comment on the quote; retain the existing new-quote mechanism and avoid bargaining arithmetic. |
| J. Tracking | **COMPLETE** | Clear date/time timeline, understandable execution units, working update path, Customer-safe location/timeline, and removal of the broken add-section experience. | B6 removed the retired add-unit UI and kept the backend fail-closed; B7 made same-tenant private locations reachable; canonical event timelines and D1/D2 safe projections remain. Evidence: `b623f7f...`, `b783052...`, `d0f2c57...`, `4a090c7...`. | No tracking-domain gap. Dual-calendar adoption is a shared presentation gap, not a missing tracking model. | No | Preserve canonical execution-unit/event paths; include tracking surfaces in the dual-calendar gate. |
| K. Multiple document files | **PARTIAL** | One logical requirement can contain multiple files, append later, replace a wrong file without losing history, retry only failed files, and expose file-level metadata. | Golden already has multiple immutable `CaseDocumentFile` rows, active-file caps, append and replace endpoints, supersession/history, private storage, audit, and per-file transactions; Phase A `953a67f...`. | Current UI selects only one file and automatically replaces when any active file exists; replacement targets only the latest active row; upload time/uploader/status are not fully presented; no per-file batch result UI. | No for approved behavior | Reimplement the bounded FWD-07 UX against Golden; no schema migration for the approved scope. |
| L. Private logistics points | **COMPLETE** | Active same-tenant private points must be selectable while wrong-tenant/inactive points remain hidden and Customer projections remain safe. | B7 completes selector reachability, opaque identity round trip, immutable snapshots, and Customer-safe projection; `b783052...`. | No product gap. | No | Preserve B7 authorization and disclosure tests. |

Closure summary for A–L:

```text
COMPLETE = 6
PARTIAL = 5
NOT_STARTED = 0
DEFERRED_BY_PRODUCT_DECISION = 1
SUPERSEDED_BY_APPROVED_SIMPLIFICATION = 0 as a whole-topic status
NEEDS_VERIFICATION = 0
BLOCKED = 0
```

The ordered/permutation form of combined transport is superseded inside topic B, but topic B remains `PARTIAL` until the approved scalar combined option exists.

## C. Newly Approved Product Decisions

1. **Dual calendar:** show the Gregorian date plus the Persian/Jalali rendering in parentheses. Both render one authoritative stored fact; persistence, sorting, filtering, and comparison continue to use that fact.
2. **Cargo:** additional mandatory cargo/product data is deferred. Current optional Golden behavior does not block this release.
3. **Combined transport:** use one request-level intent, `حمل ترکیبی`. Do not enumerate permutations at intake. Actual transport remains the ordered route-leg sequence.
4. **Quote communication:** support `تأیید`, `نیاز به گفتگو` with one short Customer message, and `رد`. A later official revision is a new quote through the existing quote mechanism. No bargaining engine or automatic counter-offer arithmetic.
5. **Documents:** one logical requirement may have multiple active files; append and explicit replacement are distinct; replacement preserves history; successful per-file uploads survive partial failure; only known failed files need retry; file rows show understandable filename/type/time/uploader/status/version metadata.
6. **Notifications:** C1/C2 are preserved, but event mapping, recipients, channels, providers, templates, quiet hours, SMS/Email/Webhook, and notification UI remain inactive and deferred.
7. **Modularization:** begin only after the approved functional product gaps and their acceptance evidence are closed.

## D. Control Tower Remaining Gaps

### Responsible Expert -> Shipment Detail

Classification: **MINIMAL_TEST_ONLY**.

There is no current authorization defect requiring Phase F runtime work:

- `control_tower_scope` treats the currently assigned Expert on an accepted-quote request as that shipment's responsible Expert and uses `primary_responsible_expert_id` for a direct shipment.
- `operational_service.scoped_shipment` resolves the same tenant and calls `authorize_work_action(..., "shipment.read")`.
- `assigned_work_authorization` authorizes an accepted-quote child through the current request assignment and a direct shipment through current primary responsibility; it reloads persisted roots and revokes former Experts after reassignment.
- Existing tests separately prove Control Tower reassignment and Shipment Detail/current-root denial, but no single HTTP test follows the exact D1 `destination` from Control Tower into Shipment Detail for accepted-quote and direct sources.

The closure action is one cross-feature test/evidence slice: current responsible Expert receives the Control Tower card and HTTP 200 at its destination; former, unrelated, revoked, inactive, Platform Admin, and cross-tenant actors receive governed denial; reassignment transfers both card and detail authority. Runtime code changes are allowed only if that test exposes a real mismatch. Default detail fields and economics disclosure must remain unchanged.

### 100-shipment ceiling

Classification: **SCALABILITY GAP**, priority **P2 with a mandatory release-volume condition**.

The ceiling exists because the current read model must:

1. enumerate the complete authorized active population;
2. evaluate and aggregate all attention sources;
3. rank globally by attention level, due state/time, onset, and shipment reference;
4. apply the attention filter only after complete evaluation;
5. bind the signed cursor to the complete authority context and result ordering; and
6. revalidate the complete scope before disclosure.

Pagination therefore does not reduce evaluation work. The 100-row bound prevents unbounded application-memory/source evaluation and fails closed instead of silently truncating or leaking totals.

The preferred removal architecture is database-side search/ranking/windowing:

- keep tenant/actor/status authorization in SQL before any source evaluation;
- express normalized attention sources as bounded relational source queries, combine them with `UNION ALL`/CTEs, and select each shipment's primary reason with database ranking;
- apply attention/search filters and the stable rank tuple server-side;
- use a signed keyset cursor over `(attention rank, due bucket, due time, onset, shipment public id)` plus actor, tenant, filter, page size, and policy version;
- hydrate only the selected page's route/tracking/request facts in batches;
- revalidate authority immediately before emitting the page and fail that page closed on source/invariant failure;
- disclose no total unless it can be computed under the same complete governed query.

If current OIP/readiness logic cannot be represented safely at query time, the fallback is a versioned tenant-owned materialized Control Tower attention projection, updated from existing authoritative facts and guarded by freshness/health checks. That fallback would require a new schema and operations design; a simple higher Python limit is rejected.

The scaling implementation may follow initial release only if the release rehearsal proves every launch tenant's authorized active population remains below 100 with documented headroom and monitoring. If that condition cannot be proven, this item automatically becomes **P0 before deployment**.

### True D2 UX gaps

- No D2-specific functional UX defect was found: route, navigation, filters, continuation, loading/empty/auth/unavailable states, responsive semantics, and Shipment Detail destinations are implemented.
- D2 lacks a separately captured real-browser screenshot/UAT artifact. That is a final UAT evidence gap, not a product-code defect.
- Dual-calendar display on Control Tower timestamps remains part of the cross-product presentation slice.

## E. Documents Gap

### Golden capability

| Approved behavior | Golden today | Gap |
| --- | --- | --- |
| Multiple files | Schema/service allow multiple active files per `CaseDocumentRequirement`, bounded by `max_active_file_count`. | UI accepts only `files[0]` and does not expose multi-select. |
| Append | Existing `/files` endpoint creates an independent active immutable row. | UI switches to replacement whenever any active file exists, so append is unreachable from the normal requirement UI. |
| Replace | Existing `/replace` creates a new row, supersedes one old active row, preserves its bytes/metadata, and links `superseded_by`. | Endpoint implicitly chooses the latest active row; the user cannot choose the wrong file being replaced. |
| Version history | `version_number`, `status`, `superseded_at`, `superseded_by`, audit events, and `versions` projection exist. | UI history can duplicate active rows and does not clearly group the replacement chain. |
| Retry after partial failure | Each upload is already its own transaction, so prior successes survive a later failure. | No multi-file orchestration or per-file result list exists in Golden UI. |
| File-level metadata | Filename, extension/MIME, size, hash, version, status, upload time, uploader ID, supersession/deletion metadata exist. | Request-document serialization/UI omit a safe uploader display and UI omits upload time/status; current filename sanitization does not preserve useful Persian display names. |

### FWD-07 capability and limits

The donor implementation begins at `811bbbaed5d2eb48c5f713b88991ce73b80c20b8` and is qualified/documented through `a778bc8516e2d71b8665acd046191fbc5f0493e8`.

It adds sequential multi-selection, independent per-file saved/failed results, append reachability, an explicit separate “replace latest” control, safe Unicode display filenames, and mobile access. It adds no document schema or batch endpoint. Each selected file still calls the existing single-file API and commits independently.

It does **not** fully match the approved behavior because it:

- replaces only the latest active file rather than an explicitly chosen file;
- omits upload time/uploader/status from the main file presentation;
- cannot distinguish a definitive failure from a lost response after the server committed, so following its retry message can duplicate an append;
- leaves ADR-049 upload-operation recovery proposed and unaccepted; no recovery runtime exists at `a778bc8...`.

The newly approved retry rule is satisfied for known per-file success/failure by independent requests and frontend state. Ambiguous lost-response recovery is a separate P2 reliability decision; it is not required to deliver the approved known-failure retry behavior and must not be misrepresented as solved.

### Migration and donor disposition

```text
APPROVED_DOCUMENT_BEHAVIOR_REQUIRES_SCHEMA_MIGRATION = NO
EXISTING_ROWS_SUPPORT_MULTI_FILE_APPEND = YES
EXISTING_ROWS_SUPPORT_TARGETED_REPLACEMENT_HISTORY = YES
KNOWN_PARTIAL_FAILURE_RETRY_REQUIRES_BACKEND_BATCH_API = NO
AMBIGUOUS_LOST_RESPONSE_EXACTLY_ONCE_RECOVERY_REQUIRES_NEW_BACKEND_SUPPORT = YES, BUT P2/NOT APPROVED
```

| Donor piece | Classification | Reason |
| --- | --- | --- |
| Multi-select/per-file outcome and known-failed-only retry concepts/tests | **REIMPLEMENT_AGAINST_GOLDEN** | Current Golden pages/APIs have diverged; behavior is useful but shared files must not be copied wholesale. |
| Safe Unicode display filename semantics and focused API tests | **CONTROLLED_TRANSPLANT** | Bounded pure validation/metadata concept; storage keys remain generated and private. |
| Mobile Request Detail access repair and browser scenarios | **REIMPLEMENT_AGAINST_GOLDEN** | Reconfirm against the current Golden shell and responsive route. |
| Existing Golden schema, append endpoint, immutable file rows, supersession/history, authorization/storage/audit | **NOT_NEEDED** from donor | Golden already has the required foundation. |
| Donor “replace latest” behavior | **REJECT** as final behavior | Approved replacement must target the chosen wrong/current file. |
| ADR-049 recovery table/lifecycle and cumulative qualification scaffolding | **REJECT** for the current slice | It addresses ambiguous delivery, adds retention/recovery semantics, and is not an approved requirement. |
| Cumulative FWD branch/runtime, CI/environment, artifacts, screenshots | **REJECT** | Evidence/reference only; not a Golden product transplant. |

The documents implementation should remain one meaningful no-migration slice: explicit append versus targeted replace, multi-select, truthful per-file results, metadata/history clarity, Unicode filenames, mobile/RTL access, and full security/storage regressions.

## F. Date / Dual Calendar Gap

### Existing presentation seams

- `src/lib/localDate.ts` safely parses date-only values without turning them into instants, but formats only one locale-default calendar.
- `src/lib/localDateTime.ts` owns datetime-local input conversion and must remain an input/serialization utility, not a display formatter.
- Major pages contain distributed `Date`, `toLocaleDateString`, `toLocaleString`, and `Intl.DateTimeFormat` calls. In Persian locale, locale default can produce a Jalali rendering; in other locales it commonly produces Gregorian. No shared helper intentionally displays both.
- Backend timestamps and date-only values remain authoritative and must not change.

### Smallest shared contract

Add a display-only module with two explicit functions:

```text
formatDualCalendarDate(localDate, locale, fallback)
formatDualCalendarInstant(instant, locale, { timeZone, includeTime, timeZoneName, fallback })
```

Contract:

- Gregorian rendering uses an explicit Gregorian calendar; Jalali rendering uses an explicit Persian calendar.
- Output is `Gregorian (Jalali)` in the active UI language/digit policy; an instant's time and timezone are rendered once after the dual date.
- Instant formatting uses one explicit application timezone policy and the same parsed instant for both calendars.
- Local Date formatting uses the original year/month/day fields, never UTC conversion.
- Invalid/missing input returns the supplied fallback.
- Sorting, filtering, comparisons, request payloads, ISO timestamps, and database values remain unchanged.
- `datetime-local` inputs, machine/audit identifiers, file names, export timestamps, and protocol metadata do not use this display helper.

### Adoption ledger

| Surface | Dual date? | Notes |
| --- | --- | --- |
| Customer/Expert request lists and request detail cards | Yes | Created date, actual assignment date, workflow completion, visible messages. Never substitute creation for assignment. |
| Customer Dashboard and Public Tracking | Yes | Request/assignment, workflow, latest update, quote creation; preserve Customer-safe projection. |
| Quote validity | Yes, date-only helper | It is a Local Date and must not shift by timezone. |
| Quote response/creation instants | Yes | Show date pair plus one time where the surface exposes the instant. |
| Operational shipment list and Shipment Detail | Yes | Planned/projected/actual route times, milestones, recent events, conditions, work items. |
| Control Tower | Yes | Latest event occurred and recorded remain separate labels and separate dual-date instants. |
| Unified Shipment History and execution-unit/project/customer timelines | Yes | Keep occurred versus recorded semantics and event ordering. |
| Request and shipment document rows | Yes | Uploaded/recorded time; version/status remain separate metadata. |
| Economics facts visible to operations users | Yes | Effective and recorded times remain distinct. |
| Technical inputs (`datetime-local`) and conversion helpers | No | Preserve wall-clock-to-UTC behavior. |
| Authentication/admin last-login, internal diagnostic clocks, refresh-cycle time, generated export/audit metadata | Specialized | May retain concise locale/time display unless promoted to a primary business fact. |
| Notification Center relative-time labels | No for current scope | Notification activation/UI is deferred. |

Regression gates: explicit calendar assertions, valid/invalid/missing data, Local Date non-shift, Tehran and UTC process/browser zones, RTL/mobile wrapping, assignment-event truth, occurred/recorded labels, sorting/filtering unchanged, and no persistence/API delta.

## G. Combined Transport Gap

### Current model

- Request intent is stored in existing scalar `ShipmentRequest.domestic_transport_method` or `international_transport_method`, with `transport_method` as a legacy fallback.
- The public selector is driven by active `TransportMethod` catalog rows and sends the selected method name through the unchanged request payload.
- B3 projects the exact stored scalar and never derives it from route legs.
- Actual execution uses ordered `RouteLeg.transport_mode` values and already supports arbitrary/repeated road, rail, sea, and air legs.

### Minimal implementation

`حمل ترکیبی` can be represented without a schema migration:

1. define one canonical request value, recommended `Combined Transport`, with Persian label `حمل ترکیبی`;
2. add/reconcile one active transport-catalog row through an explicit idempotent data operation, making it available to both domestic and international selectors;
3. add the canonical presentation aliases to `transportLabel`/B3 tests;
4. preserve the existing payload and store the value only in the applicable scalar request field;
5. return/display it through the existing Customer, Expert, Public Tracking, request summary, Operational Shipment source, and Control Tower projections;
6. do not create request leg arrays, combinations, or automatic route legs.

```text
SCHEMA_MIGRATION_REQUIRED = NO
CONTROLLED_CATALOG_DATA_RECONCILIATION_REQUIRED = YES
API_SHAPE_CHANGE_REQUIRED = NO
HISTORICAL_VALUE_REWRITE_REQUIRED = NO
```

Historical request values remain readable and unchanged. A combined request may later have any governed real route, for example Road -> Rail -> Road -> Sea. Summaries must continue to label those as separate facts. The historical duplicate Rail catalog concern should be covered by deterministic option de-duplication/presentation, not by destructive row deletion in this slice.

## H. Quote Communication Gap

### Recommended minimal model

Use a new response state on the existing official `ExpertQuote`, not a generic negotiation engine and not an unrelated message record.

Recommended persisted contract:

- extend `ExpertQuote.customer_response` to allow `discussion` in addition to `accepted` and `declined`;
- add nullable `customer_response_comment` text to the quote;
- require a trimmed non-empty bounded comment for `discussion` (recommended maximum 1,000 characters);
- require the comment to be absent for accept/reject;
- retain one terminal Customer response per quote, current same-response replay, conflict handling, expiration, locking, tracking-code capability, tenant ownership, response time, unread flag, and audit fact;
- treat `discussion` as “this quote needs human follow-up,” not acceptance, rejection, or an automatic request-state transition;
- let the Expert publish a later official quote through the existing new-quote endpoint; each quote row retains its own response/comment/time.

This design requires one fresh migration after `20260923_notification_lifecycle` to alter the response check and add the comment column. The existing `String(10)` can hold the exact ten-character code `discussion`; no money/currency redesign is needed.

Reusing `ExpertConsoleMessage` for the Customer comment is rejected: it requires an Expert author and would misattribute Customer text. A separate conversation table is also unnecessary for one bounded response/comment per official quote. If future free-form back-and-forth is later approved, it should be a separate decision rather than expanding this slice.

The Expert request detail should expose a bounded quote history showing amount/currency, creation/validity, response, response time, and Customer comment. The Customer view should show the current response and comment sent. Older quote rows remain historical evidence after a revised quote becomes latest. Accepted quotes alone remain eligible for operational-shipment creation; EUR behavior remains unchanged.

Required gates include accepted/declined preservation, required/length-bounded discussion comment, same-response replay, conflicting response, expired quote, concurrent response, revised-quote history, current assignment/tenant/capability denial, audit/unread facts, no notification-action creation, economics/accepted-quote eligibility, PostgreSQL migration upgrade/downgrade/sentinel proof, and UI mobile/RTL/accessibility.

## I. Tracking Closure Review

| Tracking concern | Classification | Evidence and remaining work |
| --- | --- | --- |
| Date + time | **COMPLETE** for tracking semantics | Canonical events expose occurred and recorded instants; current timelines render date and time. The cross-product dual-calendar formatter will change presentation only. |
| Timeline clarity | **COMPLETE** | Unified history, canonical unit timelines, stable ordering, separate occurred/recorded labels, and D1/D2 latest-event projections exist. |
| Execution-unit/container confusion | **COMPLETE** | Canonical execution units support governed unit type/display/vehicle references; UI uses “execution unit/section” rather than assuming every item is a container. |
| Add-section error | **COMPLETE** | B6 removed the retired add-unit UI, directs users to canonical project/shipment unit creation, and leaves stale clients fail-closed with 409 and no row. |
| Customer timeline | **COMPLETE** | Public/Customer projections are read-only, ordered, visibility-allowlisted, and omit internal notes/private identities. |
| Location visibility | **COMPLETE** | B7 supports global references, same-tenant private points, immutable event-time snapshots, and safe public labels. |
| Canonical versus retired paths | **COMPLETE** | Canonical execution-unit/event writes are primary; only mapped historical compatibility updates remain, and unmapped/ambiguous writes fail closed. |

No FWD-06 migration is required. Its manual-time provenance and receipt work belongs to the retired compatibility path and would add complexity without closing an approved current gap.

## J. Notification Status

```text
FOUNDATION_COMPLETE=YES
LIFECYCLE_HARDENING_COMPLETE=YES
ACTIVATION_DEFERRED=YES
```

C1/C2 tables and internal lifecycle invariants remain dormant. No event mapping, outbox consumer, recipient/consent policy, channel/fallback policy, provider/credentials, templates, quiet hours, worker/scheduler, API, or UI may be added as part of product-gap closure.

## K. Modularization Readiness

Natural boundaries are already visible in services and tests:

- requests: intake, identity, Expert list/detail/count scope;
- shipments: operational creation, population, route/read models;
- tracking: execution units, tracking projection, unified history, locations;
- quotes: quote service, currency contract, Customer response;
- geography: catalog, reconciliation, location resolution;
- logistics: network/private/global points and snapshots;
- documents: case documents, storage, catalog/readiness, shipment documents;
- notifications: foundation models and lifecycle service;
- control_tower: route, scope, sources, read model, translation, frontend adapter/view.

The main shared hotspots still make an early modular refactor unsafe:

- `backend/models.py` (2,260 lines) and `backend/operational_models.py` (1,336) contain cross-domain persistence;
- `backend/services/operational_service.py` (1,403) and `backend/routes/operations.py` (959) join quote, request, shipment, route, tracking, document, and authorization concerns;
- `backend/routes/expert_console.py` (771) and `customer_gamification_service.py` (713) join request, quote, Customer workflow, message, and tracking behavior;
- `src/lib/api.ts` (4,237) and `src/i18n.tsx` (1,552) are shared change hotspots;
- `LocationForm.tsx` (2,006), `RequestDetail.tsx` (1,522), and `PublicTracking.tsx` (600) combine several remaining product gaps;
- authorization and identity relationships cross request -> quote -> shipment -> project/document/tracking roots.

The modular architecture assessment should begin only after documents, dual calendar, combined transport, quote communication, the minimal Control Tower authorization proof, and feedback acceptance closure are complete. First freeze those final contracts, then identify package ownership/dependency rules, extract in stages with no semantic change, and rerun full UAT after the refactor. Do not use modularization to implement product behavior implicitly.

## L. Remaining Migration Forecast

| Remaining phase | Migration expected? | Forecast |
| --- | --- | --- |
| Control Tower responsible-Expert proof | No | Test/evidence only unless a real mismatch is discovered. |
| Documents approved behavior | No | Existing requirement/file/version/supersession columns suffice. |
| Dual calendar | No | Presentation-only. |
| Combined transport | No schema migration | One explicit idempotent catalog-data reconciliation is required. |
| Quote communication | **Yes** | Fresh child of `20260923_notification_lifecycle`: allow `discussion`, add nullable bounded comment storage; preserve old rows. |
| Control Tower query-time scaling | No under preferred SQL/CTE design | A materialized-projection fallback would require a separate migration and design review. |
| Modularization | No product migration expected | Any proposed schema move requires separate evidence and one-head proof; do not rewrite released migrations. |
| Ambiguous document lost-response recovery (P2) | Yes if later approved | Dedicated operation/receipt persistence would be required; ADR-049 remains unaccepted. |
| Notification activation (deferred) | Unknown | Foundation exists, but future policy snapshots/templates/preferences may require additive schema only after product approval. |

Every new migration must be a fresh direct descendant of the then-current Golden head, preserve one head, run on owned disposable PostgreSQL from both the prior head and an empty database, preserve sentinels, and refuse destructive populated downgrade where history would be lost.

## M. Final Product Backlog

| ID | Remaining item | Status | Priority | Implementation phase | User decision required? |
| --- | --- | --- | --- | --- | --- |
| PG-01 | Control Tower destination -> Shipment Detail cross-feature authorization proof | MINIMAL_TEST_ONLY | **P0** | Closure gate 0 | No |
| PG-02 | Approved request-document multi-file/append/targeted-replace/history/retry/metadata UX | NOT_STARTED against approved contract | **P1** | Product slice 1 | No |
| PG-03 | Shared Gregorian (Jalali) presentation and bounded surface adoption | NOT_STARTED | **P1** | Product slice 2 | No |
| PG-04 | Scalar `حمل ترکیبی` request intent and catalog reconciliation | NOT_STARTED | **P1** | Product slice 3 | No |
| PG-05 | Quote `discussion` response, short comment, Expert/history presentation, revised quote journey | NOT_STARTED | **P1** | Product slice 4 | No |
| PG-06 | Remove Control Tower 100-shipment ceiling | KNOWN_SCALABILITY_GAP | **P2**, conditional P0 if launch population cannot be proven below ceiling | Scaling slice 5 or post-release | No |
| PG-07 | Original A–L acceptance closure plus role/mobile/RTL/two-timezone browser UAT | REQUIRED_RELEASE_GATE | **P0** | Acceptance phase 6 | No |
| PG-08 | Modular architecture assessment and staged behavior-neutral refactor | REQUIRED_AFTER_GAP_CLOSURE | **P1** | Architecture phase 7 | No |
| PG-09 | Full owned-PostgreSQL migration/integration qualification after final schema | REQUIRED_RELEASE_GATE | **P0** | Qualification phase 8 | No |
| PG-10 | Dependency/security advisory triage, including the previously recorded high advisories | REQUIRED_RELEASE_GATE | **P0** | Qualification phase 8 | Only if risk acceptance is proposed instead of remediation |
| PG-11 | Build and qualify the packaged runtime and canonical real-process launcher | REQUIRED_RELEASE_GATE | **P0** | Qualification phase 8 | No |
| PG-12 | Clean RC freeze, non-Production deployment rehearsal, then separately authorized Production deployment | REQUIRED_RELEASE_GATE | **P0** | Release phase 9 | Yes for final deployment authorization only |
| PG-13 | Exactly-once recovery for ambiguous/lost document-upload responses | NOT_APPROVED / OPTIONAL | **P2** | Post-release reliability | Yes |
| PG-14 | Additional mandatory cargo fields | DEFERRED_BY_PRODUCT_DECISION | **DEFERRED** | None | Yes before future activation |
| PG-15 | Notification event/recipient/channel/provider/template/UI activation | DEFERRED_BY_PRODUCT_DECISION | **DEFERRED** | None | Yes before future activation |

Priority counts for the backlog above:

```text
P0 = 6
P1 = 5
P2 = 2
DEFERRED = 2
```

P0 means release proof/safety, not necessarily a product-code defect. P1 items are the approved product-completeness work that should close before the feature-complete candidate. P2 items may follow the first release only under the explicit conditions above.

## N. Recommended Final Implementation Sequence

### 0. Control Tower authorization closure gate

- **Outcome:** prove the current responsible Expert can follow D2's destination into existing Shipment Detail and former/unrelated/revoked/cross-tenant actors cannot.
- **Scope:** cross-feature backend HTTP tests and evidence; runtime change only if a real failing contract is found.
- **Migration:** no.
- **Donor:** none; current Golden authorization is authoritative.
- **Regression gates:** D1 scope/API, assigned-work authorization, operational detail payload/economics disclosure, D2 destination integration, full backend if runtime changes.
- **User input:** no.

### 1. Documents completion

- **Outcome:** one logical requirement supports multi-file selection, later append, chosen-file replacement, preserved history, truthful per-file results/retry, and complete safe metadata on mobile/desktop.
- **Scope:** Golden request-document service/route projection and `CaseDocumentsTab`/Request Detail only; no generic DMS or lost-response recovery engine.
- **Migration:** no.
- **Donor:** FWD-07 `811bbba...` UX/Unicode concepts and `63f8431...`, `2f8f11d...`, `e5e9ff7...`, `a778bc8...` qualification findings as references; no merge/copy.
- **Regression gates:** request/tenant/assignment authorization, private storage/content/size/path validation, targeted replacement race, audit/history/download, known partial failure, mobile RTL/browser, PostgreSQL concurrency tests, full gate.
- **User input:** no.

### 2. Dual-calendar presentation

- **Outcome:** selected primary business dates show Gregorian (Jalali) consistently without changing facts.
- **Scope:** one shared helper and the Section F adoption ledger; no blanket timestamp rewrite.
- **Migration:** no.
- **Donor:** bounded FWD-04 presentation/time tests only; Golden helpers remain authoritative.
- **Regression gates:** Local Date/instant split, Tehran/UTC, assignment truth, occurred/recorded distinction, request/quote/document/tracking/Shipment Detail/Control Tower surfaces, sorting/filtering unchanged, mobile RTL, full frontend/type/build/lint.
- **User input:** no.

### 3. Simplified combined transport

- **Outcome:** Customer can select `حمل ترکیبی` as one request intent while real legs remain the actual sequence.
- **Scope:** controlled catalog row, intake selector, validation/presentation aliases, B3 summary consumers; no ordered intent JSON.
- **Migration:** no schema; controlled data reconciliation.
- **Donor:** FWD-03 tests only where they prove round trip and summary consistency; reject its ordered-intent migration/model.
- **Regression gates:** Customer/Expert/tracking/Control Tower round trip, legacy values, no duplicate/conflicting Rail option, route-leg distinction, data apply/no-op, full gate.
- **User input:** no.

### 4. Simple quote communication

- **Outcome:** Customer can accept, request discussion with a short message, or reject; Expert sees history and can issue a new official quote.
- **Scope:** one new response value/comment, authorized service/API/UI/history projection, existing new-quote path; no counter-offer arithmetic or notification activation.
- **Migration:** yes, one fresh additive/constraint revision.
- **Donor:** FWD-05 security/concurrency evidence (`700381c...`, `29630f9...`) as requirements only.
- **Regression gates:** response concurrency/replay/conflict/expiry, comment validation, quote history/revision, EUR, tenant/assignment/capability, accepted-only shipment creation, economics, notification inactivity, owned PostgreSQL, mobile RTL, full gate.
- **User input:** no.

### 5. Control Tower scaling decision/execution

- **Outcome:** remove the permanent 100-row ceiling or formally carry it as a monitored launch constraint.
- **Scope:** server-side reason ranking/filter/keyset pagination; no client-side truncation and no higher hard-coded cap.
- **Migration:** none for query-time design; possible new migration only for a separately reviewed materialized projection.
- **Donor:** D1/D2 performance, authorization, fail-closed, cursor, and disclosure tests.
- **Regression gates:** >100 authorized rows, all attention filters across pages, stable/no-duplicate continuation under change, query/time budget, authority revocation, failure semantics, no totals/leaks.
- **User input:** no unless materialized persistence changes retention/operations policy.

### 6. Product acceptance closure

- **Outcome:** A–L matrix becomes complete or explicitly deferred, with real-browser role/mobile/RTL/two-timezone evidence.
- **Scope:** evidence and defect fixes returned to their owning product slice; no architecture refactor here.
- **Migration:** none unless an owning slice failed to finish its approved migration.
- **Regression gates:** full backend/frontend/type/build/lint, all feature-focused suites, D2 browser journey, no unexplained skips/count loss.
- **User input:** no for the approved contract; acceptance sign-off is required.

### 7. Modular architecture assessment and staged refactor

- **Outcome:** explicit module ownership/dependencies and smaller shared hotspots with unchanged behavior.
- **Scope:** requests, shipments, tracking, quotes, geography, logistics, documents, notifications, and control_tower boundaries; extract in reviewable stages.
- **Migration:** none expected.
- **Donor:** none.
- **Regression gates:** frozen final product contracts after each extraction, architecture checks, full suites, API/schema compatibility.
- **User input:** only if the assessment proposes a product/API/schema change.

### 8. Full qualification and RC freeze

- **Outcome:** one clean, reproducible, deployable candidate.
- **Scope:** owned PostgreSQL, security/dependency triage, package build, packaged real-process launcher, full browser UAT, hashes/provenance, rollback and deployment rehearsal.
- **Migration:** final graph exactly one head; fresh and prior-head upgrades pass.
- **Donor:** certified Golden release tooling only.
- **Regression gates:** all Section O criteria.
- **User input:** explicit RC approval and later separate Production deployment authorization.

## O. UAT / Release Exit Criteria

### Before modularization is complete

- PG-01 through PG-05 are closed with evidence and no unresolved product decision.
- A–L is `COMPLETE` except explicitly deferred cargo.
- Notification activation remains absent.
- Final contracts and module ownership/dependency rules are recorded.
- Each staged refactor preserves API, schema, authorization, and user-visible behavior and passes full gates.

### Before full UAT

- Product-gap and modular-refactor branches are synchronized through explicit milestone checkpoints.
- Worktree is clean; one Alembic head exists; no stale donor/build artifact is used.
- Synthetic role/tenant data covers Customer, Expert, Organization Admin, Platform Admin denial, reassignment/revocation, direct and accepted-quote shipments, multiple documents, dual dates, combined transport, and all quote responses.
- All required services run in an owned non-Production environment.

### Before RC freeze

- All focused and full backend/frontend/type/build/lint/architecture gates pass with explained skips only.
- Owned PostgreSQL passes fresh upgrade and upgrade from the prior canonical head, constraints, concurrency, sentinel preservation, and rollback policy.
- Browser UAT passes desktop/mobile RTL and at least Tehran/UTC timezone starts, including D2 Control Tower -> Shipment Detail.
- Control Tower launch population is proven below 100 or PG-06 is fixed before RC.
- Dependency/security advisories are remediated or explicitly accepted by an authorized owner with bounded evidence.
- Release manifest names source commit, lockfile/dependencies, single migration head, evidence, hashes, and launcher identity.

### Before Production rehearsal

- RC source and artifact are frozen, clean, immutable, and reproducible.
- Packaged runtime and canonical Windows chain pass the real-process test: system `cmd.exe /d /c` -> explicit release environment/repository/cwd -> release-local Python -> approved cutover runtime -> release-local Waitress on the governed listener.
- Disposable non-Production rehearsal proves migration, application start, valid/invalid login, role boundaries, Control Tower 401/403/200, Customer journeys, rollback/failure injection, listener/process/release identity, and artifact integrity.
- No Production secret or endpoint is used for rehearsal.

### Before Production deployment

- RC and rehearsal evidence are approved; no unresolved P0 remains.
- Backup/restore, migration, rollback, monitoring, operator, maintenance window, and incident ownership are explicit.
- Required catalog data operations (geography and combined transport) are planned, checksummed, idempotent, and separately approved for the environment.
- Notification delivery remains inactive unless a later separately approved goal changes that decision.
- A separate explicit Production deployment authorization is issued. This review does not provide it.

## P. Deferred Items

- **Mandatory cargo:** additional required cargo/product fields and transition enforcement are deferred and do not block the current release path.
- **Notification activation/policy:** event mapping, recipients, consent/preferences, channel/fallback, SMS, Email, Webhook, provider, credentials, templates, quiet hours, worker/scheduler, and UI are deferred.
- **Safe post-release under stated conditions:** Control Tower >100 scaling may follow release only with proven launch headroom/monitoring; ambiguous document-upload lost-response recovery may follow as a separately approved reliability feature.
- **Compatibility cleanup:** destructive cleanup of historical transport/catalog values and retirement of compatibility endpoints are not required for product completion and must not be folded into the approved slices.

## Q. Verdict

**READY — FINAL PRODUCT GAP CLOSURE MAY BEGIN**

The remaining behavior is defined, bounded, dependency-ordered, and no longer blocked by product ambiguity. The release itself is not ready: approved product gaps, P0 qualification gates, modularization, UAT, RC, and deployment rehearsal still remain.

## R. Next Goal

```text
GOAL

Execute one Golden-controlled Documents Completion slice after this evidence
report is reviewed and its evidence commit is present in the synchronized
canonical lineage.

Required baseline:
- repository: D:\1-webapp\15-forwarder-golden-20260921
- canonical branch: integration/golden-controlled
- D2 product commit ancestor:
  4a090c78856fd85a3dc2cc503841056c4fb6d3c5
- post-D2 gap-review evidence commit ancestor: the unique commit containing
  docs/operational/evidence/post-d2-product-gap-review-20260920.md
- exactly one starting Alembic head:
  20260923_notification_lifecycle
- clean worktree and local/remote ahead/behind 0/0 before branching

First add the minimal cross-feature Control Tower destination regression inside
the slice's pre-change gate: for accepted-quote and direct shipments, the
current responsible Expert can open the supplied Shipment Detail destination;
former, unrelated, revoked, inactive, Platform Admin, and cross-tenant actors
remain denied. Do not change runtime authorization unless that test exposes a
real current mismatch.

Then implement only the approved request-document behavior against current
Golden:
- one logical CaseDocumentRequirement may contain multiple active files;
- expose explicit APPEND, including multi-select;
- expose explicit REPLACE of a user-selected active file, never implicit
  "replace latest";
- preserve superseded rows, bytes, audit, and understandable version history;
- commit each selected file independently and show a truthful per-file
  saved/failed result so only known failed files need reselection;
- show filename, safe type, upload time, governed uploader display where
  authorized, status, and version/history identity;
- preserve useful Unicode/Persian display filenames while retaining generated
  private storage keys and all content/extension/path/size validation;
- preserve mobile/RTL access from current Golden Request Detail.

Use FWD-07 commit 811bbbaed5d2eb48c5f713b88991ce73b80c20b8
and qualification history through
a778bc8516e2d71b8665acd046191fbc5f0493e8 only as semantic/test evidence.
Reimplement against Golden shared files. Do not merge or cherry-pick.

No schema migration is authorized for this slice. Do not implement ADR-049,
upload-operation receipts, ambiguous lost-response recovery, a batch
transaction, public/customer document access, preview/OCR/scanning, a generic
DMS, dual calendar, combined transport, quote communication, notifications,
Control Tower scaling, modularization, RC, deployment, or Production access.

Required gates: current document characterization before change; append up to
the configured cap; targeted replacement and concurrent-target conflict;
history/download/audit preservation; same-name and Unicode filename safety;
mixed success/failure with prior successes retained; retry of only known failed
files; authorization/reassignment/revocation/cross-tenant denial; storage fault
injection; owned PostgreSQL document concurrency/parity; mobile/desktop RTL
browser proof; Phase A/B1-B7/C1-C2/D1-D2 regressions; full backend/frontend,
TypeScript, build, lint, one-head/current/check, and no migration diff.

Finish with one bounded product commit and one evidence commit on a dedicated
Codex branch. Do not push or move canonical without a separate synchronization
goal.
```
