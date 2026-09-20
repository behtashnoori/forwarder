# Dual Calendar Build Evidence — 2026-09-20

## A. LPAF Governance Gate

This slice is governed by the active LPAF v2.2 Agent Entry and Architecture
Framework, with the LPAF v2.3 Product Integration `REFERENCE_IMPACT` gate used
as the Forwarder strong default. The mission is a presentation-only capability:
show selected user-facing business dates as Gregorian followed by Jalali in
parentheses, without changing the authoritative temporal fact.

The implementation preserves the existing capability owners, systems of
record, authorization, tenant scope, journeys, module boundaries, public API,
negative/error behavior, and recovery model. Calendar formatting grants no new
access and does not create a new business fact.

`REFERENCE_IMPACT=NONE`

Rationale: ADR-016, TIME-BIZ-013, PDR-019, the architecture baseline, the
post-D2 journey contract, and the post-D2 gap review already contain the exact
approved presentation contract and implementation seam. No authoritative
reference needed to be changed by this build.

## B. Starting Canonical State

- Part A starting Documents build: `7f2446226d222028fce2e6e609ba5bb254041718`.
- Required Documents design parent `da63d3ef32f0fb16edb7f7cba0bfc484de655eae`
  and reference ancestor `ed6d0d9954b273f35f8f4ebc8f9ec5008cd82d6f`
  were verified in the lineage.
- `integration/golden-controlled` was fast-forwarded to `7f244622...`, pushed
  to `github`, and verified at ahead/behind `0/0`.
- Annotated tag `golden-controlled-documents-multifile-20260920` points exactly
  to `7f244622...` and was pushed without overwriting any tag.
- Part A verdict: `PASS — DOCUMENTS CANONICAL SYNCHRONIZATION COMPLETE`.
- Dual Calendar branch: `codex/dual-calendar-build`, created from exact current
  canonical `7f2446226d222028fce2e6e609ba5bb254041718`.

## C. Temporal Surface Inventory

The inventory was completed before formatter adoption. The implementation did
not apply one global formatter indiscriminately.

| Class | Temporal fields / surfaces | Disposition |
| --- | --- | --- |
| A. `BUSINESS_DATE_DUAL_DISPLAY` | Request/Shipment/Control Tower cards whose existing value is a user-visible business date | Adopt the shared dual display at the existing density. |
| B. `BUSINESS_TIMESTAMP_DUAL_DISPLAY` | Request creation/assignment/workflow events; Shipment list/detail, milestones, conditions, economics, cargo latest event; Work Queue and OIP; execution-unit/project/customer tracking; Control Tower occurred/recorded values; Documents upload/association/history | Render both calendar dates from the same parsed instant and render time once. |
| C. `LOCAL_DATE_DUAL_DISPLAY` | Quote `valid_until`, pickup date, delivery date, and other ISO date-only business values | Parse civil fields without timezone conversion, then render Gregorian and Jalali. |
| D. `TECHNICAL_TIMESTAMP_KEEP_EXISTING` | Security last-login metadata, Control Tower analytics refresh-cycle time, internal runtime/log timing | No adoption; these are technical rather than governed business facts. |
| E. `NOT_USER_FACING` | Raw API RFC 3339 values, request payloads, database columns, hidden machine values, sort/filter operands | Unchanged. |
| F. `SPECIALIZED_FORMAT_KEEP_EXISTING` | Relative Notification Center age labels and `datetime-local` input/serialization utilities | Unchanged; notifications remain dormant and input serialization is not display formatting. |

The inventory specifically reviewed Customer request lists/details and public
tracking; Expert request/work surfaces; Shipment lists/details, operational
events, economics and cargo; Documents; Quote display; Control Tower;
manager/admin operational oversight; and shared timelines/cards/tables.

## D. Instant vs Local Date Contract

`formatDualCalendarInstant` parses one instant once, formats both calendars in
the same resolved display timezone, and preserves the current surface timezone
policy. Time-of-day and timezone name, when requested, are appended once rather
than duplicated.

`formatDualCalendarDate` uses `parseLocalDate`, constructs a stable civil-date
container, and formats with UTC calendar fields. A Local Date is never passed
through local midnight or shifted by timezone. Null, absent, and malformed
values return the caller's fallback and cannot crash a page.

`occurred_at` and `recorded_at` remain separate labels and separate instants.
The formatter changes only their presentation.

## E. Shared Presentation Design

One small shared module, `src/lib/dualCalendar.ts`, owns the capability:

- `formatDualCalendarDate(value, locale, fallback, dateStyle)`;
- `formatDualCalendarInstant(value, locale, options)`.

It uses the platform `Intl.DateTimeFormat` with explicit `gregory` and
`persian` calendars. The invariant is `Gregorian (Jalali)`. Existing surface
density controls `short`, `medium`, or fuller date styles. The implementation
does not change serialization helpers or create page-specific conversion
algorithms.

## F. Localization / RTL

Both calendar renderings use the active locale's established language and
digit policy while fixing the calendar explicitly. Persian surfaces therefore
remain readable in RTL and English surfaces retain English Gregorian output
with an understandable Jalali counterpart. Parentheses are visible rather than
tooltip-only, and time is not repeated. Desktop and mobile RTL browser journeys
verified wrapping and reachability.

## G. Implemented Surfaces

- Customer: Customer Dashboard, Customer Request Detail, public Request detail,
  request cards/workflow, Public Tracking, assignment and quote timestamps,
  quote validity, pickup/delivery Local Dates, unit tracking timelines.
- Expert: Expert Console, Request Detail, operational Work Queue, OIP detail,
  Shipment list/detail, operational conditions/execution/economics/cargo,
  execution-unit and project timelines.
- Shared Shipment history: occurred and recorded values remain separately
  visible with dual-calendar presentation.
- Documents: current upload time, recorded/associated time, current file rows,
  historical version rows and reopen flows.
- Control Tower: latest event occurred and recorded instants, with D1/D2
  projection and authorization semantics unchanged.
- Admin/manager: governed cargo-catalog Shipment usage dates and the existing
  operational oversight surfaces above.

## H. API / Persistence Contract

No backend route, response shape, request shape, model, database column,
business fact, authorization rule, or tenant boundary changed. Jalali values
are derived locally at render time. Machine values remain the sole operands for
sorting, filtering, searching, comparison, and persistence.

## I. Calendar Correctness Tests

`src/lib/dualCalendar.test.ts` contains 20 deterministic tests covering:

- known Gregorian/Jalali boundary dates, including 20/21 March 2026;
- Jalali New Year, Gregorian New Year, leap day, and month/year boundaries;
- UTC and Asia/Tehran near-midnight instant behavior;
- Local Date invariance across process timezone changes;
- one parsed instant and one rendered time-of-day;
- English and Persian/RTL locales;
- null, absent, and malformed input fallbacks.

Representative component/page assertions additionally bind Request, Shipment,
Control Tower, Tracking/timeline, Quote, and Documents to the shared formatter.

## J. Product Regression

- Full frontend rerun: `71` files, `349` tests passed. One first-run five-second
  timeout in the unchanged LocationForm test passed immediately in isolation
  (`6/6`) and the subsequent isolated full rerun passed `349/349`.
- TypeScript: PASS.
- ESLint for all changed TypeScript/TSX and browser specs: PASS with zero
  errors.
- Production build: PASS; `2547` modules transformed. Existing stale
  Browserslist and large-chunk warnings remain non-blocking and unchanged.
- Full backend on an owned PostgreSQL 18 cluster, migrated from zero to current
  head: `1297 passed, 98 skipped, 1 xfailed` in `681.73s`.
- Release/source/package/architecture cohort: `115 passed, 1 xfailed`; the
  xfail is the already-known expected contract.
- Cargo browser regression proved zero-Cargo, multi-Cargo precision/order, and
  invalid voluntary rows. Cargo optionality and payloads are unchanged.
- Quote currency/lifecycle component coverage, including EUR, passed. Quote
  Communication was not implemented.
- Control Tower tests and browser acceptance preserved the D1/D2 read model,
  fail-closed behavior, and current `>100` safeguard.
- Notifications C1/C2 remain dormant; no provider, worker, recipient mapping,
  channel, UI, or delivery path was activated.

## K. Documents Regression

The Documents component tests and real browser qualification re-proved current
and historical timestamps, append, targeted replacement, partial retry,
history grouping, Unicode filenames, download, owning-Expert controls,
same-scope read behavior, Admin read-only behavior, denied direct Admin
mutation, and responsive mobile/RTL reachability. Calendar formatting did not
change file identity, version authority, storage, or history semantics.

## L. Browser Evidence

All browser work used three fresh, loopback-only, disposable PostgreSQL 18
databases migrated to repository head. No Production system was accessed.

| Journey | Result | Calendar/product assertions |
| --- | --- | --- |
| Customer Request / Cargo | `3 passed` | Normal create, confirmation, dashboard reopen, visible parenthetical dual date; zero/multiple/invalid Cargo preserved; console/network clean. |
| Expert Documents | `3 passed` | Desktop owner lifecycle and reopen, mobile RTL reachability and dual timestamp, Admin read-only/403 mutation; downloads and history preserved. |
| Shipment / Work Queue / Control Tower | `3 passed` | Normal login/navigation to Shipment list and detail with dual dates; denied Work Queue actor remains fail-closed; Control Tower shows distinct occurred/recorded dual dates without technical-code leakage; console/network clean. |

Browser total: `9 passed`. Representative desktop and mobile RTL layouts kept
parentheses readable with no observed overlap or broken directionality.

## M. Database / Migration Contract

The repository was verified with exactly one Alembic head:
`20260924_request_cargo_items`. A fresh owned PostgreSQL database migrated from
zero to that head before the full backend qualification. No migration file was
added or modified, and no schema change is required by this presentation slice.

## N. Performance / Dependency Impact

No dependency was added. Conversion uses local deterministic `Intl` support:
no API request, external conversion service, server round trip, calendar
service, or persistence lookup is performed per date. The shared helper creates
only the formatters required for the rendered value; no large per-row model or
new bundle framework was introduced.

## O. Reference Re-check

Immediately before Freeze, the LPAF v2.2 Agent Entry and Architecture
Framework, the v2.3 Product Integration gate, ADR-016, TIME-BIZ-013, PDR-019,
the current architecture baseline, S6 Golden Business Journeys, and the
post-D2 gap review were re-checked against code, tests, database behavior, and
browser evidence.

They agree: the UI displays Gregorian then Jalali from one Local Date or
Instant; no duplicate persistence, timezone inference, reordered fact,
collapsed occurred/recorded meaning, API change, or reference drift exists.

`REFERENCE_IMPACT_FINAL=NONE`

## P. Scope Integrity

```text
DUAL_CALENDAR_PRESENTATION_ENABLED=YES
DUAL_CALENDAR_PATTERN=GREGORIAN_THEN_JALALI
ONE_AUTHORITATIVE_TEMPORAL_FACT=YES

JALALI_PERSISTED_SEPARATELY=NO
DUAL_CALENDAR_SCHEMA_CHANGE_REQUIRED=NO

TIMEZONE_SEMANTICS_CHANGED=NO
LOCAL_DATE_TIMEZONE_SHIFT_ALLOWED=NO
SORTING_SEMANTICS_CHANGED=NO
FILTERING_SEMANTICS_CHANGED=NO

MIGRATION_ADDED=NO
MIGRATION_MODIFIED=NO

DOCUMENTS_BEHAVIOR_CHANGED=NO
CARGO_OPTIONALITY_CHANGED=NO
QUOTE_LIFECYCLE_CHANGED=NO
CONTROL_TOWER_SEMANTICS_CHANGED=NO
NOTIFICATION_ACTIVATION_CHANGED=NO
EXPERT_OWNERSHIP_CHANGED=NO

PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
```

## Q. Remaining Risks

- Browser/OS `Intl` data controls localized month spelling and digits; explicit
  calendar selection and deterministic tests protect semantic correctness.
- The existing frontend large-chunk and stale Browserslist warnings remain
  repository-level maintenance items; this slice added no package or material
  bundle subsystem.
- Security/audit timestamps, analytics refresh time, relative notification age,
  and raw API/export values intentionally remain outside the selected
  business-facing adoption ledger.
- Combined Transport intent, Quote Communication, Control Tower scaling, and
  Notification activation are later goals and were not started.

## R. Verdict

PASS — DUAL CALENDAR PRESENTATION COMPLETE
