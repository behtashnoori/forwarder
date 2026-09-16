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

## Browser UAT attempt — 2026-09-16

Environment identity: loopback-only Flask fixture from the existing
`scripts/uat/fwd02_browser_fixture.py`, served at `127.0.0.1:5052`, with the
existing Vite development UI at `127.0.0.1:8080`.  It used only the fixture's
synthetic tenant, synthetic expert, request `SR-FWD02X`, and synthetic quote.
No production endpoint, customer data, message provider, or real credential
was used. Candidate commit was
`ed4026c1f07c54da1980fcea1cabcb4c1a5e289f` on
`feature/fwd-04-presentation-integrity`; `origin` matched before the run.

| UAT | Actor / journey / result | Status |
| --- | --- | --- |
| Customer/public | Opened the normal public tracking route with the synthetic tracking code. It showed no assignment date where the fixture has no assignment log (rather than substituting request creation). After the expert saved a synthetic quote, reopening the same public route showed `۱۲٬۳۴۵ IRR` and the Local Date `۲۶ دی ۱۴۰۸`. | PASS (applicable fixture coverage) |
| Expert | Signed in through the normal expert login with the fixture's synthetic expert, navigated console → request detail → quote form, pasted Persian digits `۱۲٬۳۴۵`, set Local Date `2030-01-15`, saved, and observed the grouped amount and Jalali Local Date after reload. The fixture has no real assignment/referral log, so it cannot prove the positive assignment-timestamp branch. | BLOCKED (missing synthetic assignment-fact fixture) |
| Timezone | The browser harness exposes responsive viewport control but no timezone override; a second controlled browser timezone could not be run. This is not inferred from formatter/unit tests. | BLOCKED (UAT_ENV_D) |
| RTL desktop | At 1280×800 the public tracking page was `dir=rtl`, showed the mixed Persian/Latin amount/currency, and had no horizontal overflow (`scrollWidth=1274`, `innerWidth=1280`). | PASS |
| RTL mobile | At 390×844 the same page remained RTL with no horizontal overflow (`scrollWidth=385`, `innerWidth=390`); the visible quote card was readable. | PASS |

Supporting evidence was direct rendered-browser accessibility/DOM state, not
screenshots alone. No product defect was established: the missing assignment
timestamp is correct for this fixture because no assignment fact exists.
The remaining qualification is blocked, not passed, until a standard
loopback/disposable fixture provides a genuine assignment fact and a browser
harness permits a second timezone execution.

## Reusable fixture and timezone closure — 2026-09-16

This supersedes only the two blocked rows above. The earlier FWD-02 fixture was
**A: the real Candidate backend with a disposable SQLite DB and synthetic
users**, not an API mock; its scope is retained as `UI_ON_FIXTURE`. The new
FWD-04 fixture is likewise a real loopback backend, but creates its assignment
through the normal authenticated assignment API rather than seeding a log.
There is no browser route interception, mocked assignment response, production
endpoint, customer record, real credential, or external-message delivery.

Candidate tested: `5994253b82e31f24dd6ec68db9c601c2aec9d7f1`.

| Gate | Evidence and result |
| --- | --- |
| Assignment provenance | Synthetic tenant → synthetic Organization Admin → real `POST /api/expert/requests/{id}/assign` → real SQLite persistence → regular synthetic expert UI. The request creation instant was `2026-09-16T08:40:26Z`; the persisted assignment fact was later (`2026-09-16T08:40:41Z`). `timeline_service.get_assigned_at` read the resulting `ExpertConsoleLog` fact. **PASS**. |
| Positive assignment UI | The public route rendered the assignment’s Persian primary calendar plus independent Gregorian secondary value and literal `Asia/Tehran`; the normal expert login navigated console → assigned request detail. The discovery-run defect was repaired: legacy UTC-naive assignment facts had been serialized without an offset, and an explicit-field date format collided with default `dateStyle`/`timeStyle`. The bounded repair serializes assignment facts as RFC-3339 UTC and makes explicit format fields mutually exclusive with the defaults. **PASS**. |
| Missing fact | A same-tenant synthetic request without an assignment/referral log returned `assigned_at: null`; both browser contexts rendered it unresolved, without a fabricated creation-time assignment. **PASS**. |
| Browser timezones | Fresh Playwright Chromium contexts requested and observed `UTC` and `America/New_York` through `Intl.DateTimeFormat().resolvedOptions().timeZone`. In both, the independently computed Gregorian oracle and product output were `16 Sept 2026, 12:10` in application display timezone `Asia/Tehran`; browser timezone changed, product policy did not. **PASS**. |
| Local Date | The ordinary expert UI saved quote amount `۱۲٬۳۴۵ IRR` with Local Date `2030-01-15`; after reopening public tracking it rendered `۲۶ دی ۱۴۰۸` in both browser contexts. This proves no browser-zone rollover for the Local Date. **PASS**. |
| Responsive RTL | Fresh 1280×800 and 390×844 contexts reported `dir=rtl` and `scrollWidth == clientWidth` for the affected public surface. **PASS**. |

The runner’s JSON evidence is written outside the repository to the caller’s
temporary directory and contains no credentials or browser storage. Focused
regression results: `17` backend timestamp/public-tracking tests and `4`
frontend presentation tests passed. The previous Persian-digit paste evidence
is `REUSED_WITH_IMPACT_REVIEW`: it was already executed against a real,
disposable backend; the new run exercised the same quote save/reopen path on
the FWD-04 fixture.

Reproducible PowerShell command (it securely prompts for a synthetic password,
owns only its two loopback processes, and tears them down):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uat\run-fwd04-browser-uat.ps1
```

Application changes: assignment Instant serialization and safe explicit-date
formatting. Test-harness changes: disposable real-backend fixture, Playwright
timezone runner, and local setup/teardown command. No schema, migration,
assignment meaning, authority, or workflow change was made.

Known historical gaps retained unchanged:
`FORWARDER-HISTORICAL-REPLAY-001 = BLOCKED_MISSING_EXTERNAL_EVIDENCE` and
`PRODUCTION_IDENTITY = UNKNOWN`.

REAL_MESSAGES_SENT: NO

LLM_APIS_CALLED: NO

PRODUCTION_CHANGED: NO
