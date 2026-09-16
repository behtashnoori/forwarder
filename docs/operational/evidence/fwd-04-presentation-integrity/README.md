# FWD-04 presentation integrity evidence

## Governing identity and bounded contract

- Branch/start: `feature/fwd-04-presentation-integrity` from
  `d10f6e003a684626cdb382ba25d6f5bd329150f2` (FWD-03 ancestry retained).
- LPAF: v2.2 ACTIVE; v2.4 owner-approved pilot only, current SHA-256
  `217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397`,
  re-attested as semantic link-only relocation. Mother LPAF impact: NONE.
- Project architecture impact: UPDATE_REQUIRED; this evidence records the
  bounded shared-presentation adoption. No schema, migration, historical
  rewrite, authority, currency, unit, or canonical time contract changes.
- Shared presentation is a UI parser/formatter only. Commercial owns quote
  amount/currency/validity; Tracking/Timeline owns assignment and event facts.

## Fact and root-cause ledger

| Surface / field | Source fact and current contract | Root cause | Bounded fix / proof |
| --- | --- | --- | --- |
| Public request assignment | `timeline_service.get_assigned_at`: earliest assignment/referral log; initial assignment, not current reassignment | UI used host timezone and simple workflow substituted request creation when no assignment existed | Explicit fact stays absent when missing; display uses explicit `Asia/Tehran` instant rendering and shows Gregorian secondary value. Timestamp tests cover no substitution. |
| Request creation and time-bearing tracking fields | legacy request timestamps; RFC-3339 offset values only are safe presentation instants | ad-hoc `new Date()` formatting silently used browser timezone / accepted naive strings | shared `formatInstant` rejects missing-offset/invalid values and fixes display timezone. |
| Quote validity | `ExpertQuote.valid_until`, Local Date | local-date formatter constructed from host-local fields | UTC calendar-field anchor prevents host-zone date rollover; date is never made into an instant. |
| Quote amount | existing integer `ExpertQuote.amount` plus currency | UI removed commas then rounded; API `int()` could truncate fractions | shared parser accepts Latin/Persian/Arabic digits and supported separators; UI/API reject fractions rather than changing value; formatter groups quantities and keeps currency adjacent. |

`UNKNOWN/TIME_SEMANTICS_UNRESOLVED`: legacy naive `created_at` / historical
timestamp strings without offset are intentionally not interpreted as Instants.
They render as the honest fallback rather than acquiring an assumed timezone.

## Scope and boundaries

Customer public tracking, authenticated customer quote display, expert quote
display/input, and existing multi-unit summary counts are covered. IDs, tracking
codes, telephone numbers, location codes and vehicle/container references are not
passed through numeric formatting. Full product localization, deep operational
timeline screens, new quote decimal precision, date-picker replacement, timezone
policy configuration, and reassignment/current-assignee UI are out of scope.

The quote schema is integer-only (`ExpertQuote.amount`), so lossless decimal quote
entry requires a separately approved commercial/data-contract change; this slice
does not invent precision or round a submitted commercial value.

## Verification plan and results

- PASS — shared presentation focused tests: Persian/Arabic input normalization,
  grouping ambiguity rejection, zero/null/invalid distinction, explicit-zone
  timestamp, and independent dual-calendar output (21 frontend assertions with
  existing Local Date coverage).
- PASS — TypeScript no-emit check and production build exercise all changed consumers.
- PASS — 21 focused backend tests verify that request creation is never displayed
  as assignment and that large integral strings survive quote normalization while
  fractional/boolean inputs are rejected.
- PASS — lint with 0 errors / 12 pre-existing warnings; structure check passed.
- Browser UAT remains NOT_RUN in this evidence until a local authenticated and
  public test fixture is started; it is not inferred from unit/API results.

Known historical gaps retained unchanged:
`FORWARDER-HISTORICAL-REPLAY-001 = BLOCKED_MISSING_EXTERNAL_EVIDENCE` and
`PRODUCTION_IDENTITY = UNKNOWN`.

REAL_MESSAGES_SENT: NO

LLM_APIS_CALLED: NO

PRODUCTION_CHANGED: NO
