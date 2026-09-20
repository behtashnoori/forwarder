# Phase B — Slice 2 — Shared Numeric Presentation — 2026-09-20

## A. Starting State

| Item | Verified value |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Required starting branch | `codex/phase-b1-governed-geography` |
| Slice branch | `codex/phase-b2-shared-numeric-presentation` |
| Starting HEAD / B1 commit | `a503d7b6473b90b01ff9a11c6e751375ff9f2121` |
| Required parent | `953a67ff5820864c08bc8727f34f49ed66237527` |
| Starting cleanliness | clean |
| Golden application provenance | `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4` |
| Engineering base | `b48e51c8d0eda00bcc7582b68da85528b14547d2` |
| Database head | `20260921_shipment_evidence_ownership` |

The Phase A Markdown/JSON freeze evidence, the Phase B1 geography evidence, and the controlled integration plan were present and read before implementation. The repository had exactly one Alembic head. A disposable SQLite database already stamped at that head returned `current=20260921_shipment_evidence_ownership`, `heads=20260921_shipment_evidence_ownership`, and `pending=no`. No prerequisite differed and no stop condition was triggered.

## B. Numeric Formatting Inventory

| Classification | Existing implementation / consumer | Decision |
| --- | --- | --- |
| `SHARED_FORMATTER_CANDIDATE` | `src/lib/formatQuantity.ts` cargo helper | Retained as the authoritative module and expanded into the single shared contract. |
| `SHARED_FORMATTER_CANDIDATE` | Inline measurement/money formatters and quote display in `RequestDetail.tsx` | Reconciled to the shared formatter. |
| `SHARED_FORMATTER_CANDIDATE` | Quote amounts and numeric tracking summaries in `PublicTracking.tsx` | Reconciled to the shared formatter. |
| `SHARED_FORMATTER_CANDIDATE` | Quote amount in `CustomerRequestDetail.tsx` | Reconciled to the shared formatter. |
| `SHARED_FORMATTER_CANDIDATE` | Raw economics amount strings in `ShipmentEconomicsSection.tsx` | Reconciled without changing stored fractional digits or currencies. |
| `SHARED_FORMATTER_CANDIDATE` | Cargo catalog shipment usage and allocation quantities | Reconciled to the shared quantity contract. |
| `KEEP_SPECIALIZED` | `AdminPanel.tsx` count-only `Intl.NumberFormat(locale)` | Already has correct grouping and locale semantics; no rewrite for architectural purity. |
| `KEEP_SPECIALIZED` | `DashboardWidgets.tsx` analytics widget formatter | Retains its explicit analytics display policy and existing two-decimal cap; this slice does not change dashboard semantics. |
| `KEEP_SPECIALIZED` | Chart-library tooltip formatting | Component-library behavior remains untouched. |
| `IDENTIFIER_DO_NOT_FORMAT` | Database IDs, request/shipment/public IDs, UUIDs, tracking codes, unit codes, vehicle/container references, phones, postal/document/reference/route codes | Kept outside every numeric formatter. Numeric-looking examples have explicit regressions. |
| `OUT_OF_SCOPE` | `Number(...)` / `parseFloat(...)` used for controlled form submission or arithmetic | Input and API semantics remain unchanged. |
| `OUT_OF_SCOPE` | `Date.toLocaleString` / `Intl.DateTimeFormat` | Date, timezone, and calendar policy are unchanged. |

The bounded search covered `Intl.NumberFormat`, `toLocaleString`, manual grouping, `Number(...)`, `parseFloat(...)`, amount/quantity helpers, and numeric-looking identifier fields. It did not trigger a codebase-wide refactor.

## C. FWD-04 Donor Analysis

The approved donor commits were inspected read-only in `D:\1-webapp\forwarder-dev`:

- `ed4026c1f07c54da1980fcea1cabcb4c1a5e289f` — primary implementation donor;
- `5994253b82e31f24dd6ec68db9c601c2aec9d7f1` — qualification/correction donor;
- `98a0364a6b6f97daf70152c7d3a5cefbb242cac0` — closure evidence.

Numeric-specific files inspected were `src/lib/presentation.ts`, `src/lib/presentation.test.ts`, `backend/tests/test_fwd04_quote_amount_contract.py`, and the FWD-04 evidence README. Reused semantics are: one shared presentation seam, grouping of domain quantities/amounts, zero distinct from missing, invalid-input fallback, locale-aware output, and explicit exclusion of identifiers.

The donor's direct `Number(string)` conversion was rejected because it can lose precision for large API numeric strings. Donor date/time helpers, dual-calendar behavior, quote normalization, backend changes, and browser-timezone changes were explicitly rejected as outside this slice. No merge, cherry-pick, cumulative runtime copy, or donor write occurred. The donor worktree already contained unrelated untracked evidence before inspection; it was not changed.

## D. Shared Numeric Contract

- **Integer:** values already classified by the caller as business numbers are grouped with the requested application locale's digits and separators.
- **Decimal:** significant fractional digits are never rounded. General business numbers and money preserve supplied fractional digits. Cargo quantities retain the approved Golden behavior of trimming storage-only trailing zeroes.
- **Zero:** `0` and numeric string `"0"` render as zero.
- **Missing:** `null`, `undefined`, and the empty string use the caller/surface fallback. Existing cargo semantics continue to use `0` for a missing quantity; general and money display default to `—`.
- **Money:** only the amount presentation is grouped. The currency token is appended unchanged; no currency is introduced, converted, inferred, or renamed.
- **Numeric strings:** strict plain-decimal API strings are formatted directly as strings, without `Number(...)` coercion. Values beyond JavaScript's safe integer range therefore retain every digit.
- **Very large numbers:** finite JavaScript numbers written in exponential notation are expanded for ordinary business display; exact large values should continue to arrive as API strings.
- **Invalid input:** non-finite numbers and non-decimal strings return the configured invalid fallback. The helper does not parse human grouping separators or guess ambiguous input.

The API is intentionally named `formatBusinessNumber`, `formatQuantity`, and `formatMoney`. Calling code must first know the field's domain meaning; digit-only strings are not discovered or formatted automatically.

## E. Identifier Exclusion Contract

Protected categories are database IDs, request numbers, shipment identifiers, UUID/public IDs, tracking codes, container IDs, vehicle references, phone numbers, postal codes, document/reference/invoice strings, route codes, unit codes, and other opaque business identifiers.

Regression coverage includes:

- a numeric-looking phone value submitted unchanged by `LocationForm.destination.test.tsx`;
- a numeric tracking code displayed without grouping by the same request flow test;
- a numeric unit code and leading-zero vehicle reference displayed unchanged by `ExecutionUnitPages.test.tsx`;
- a UUID passed unchanged to operational calls;
- a numeric tracking route token passed unchanged to public tracking calls;
- existing opaque IDs/reference values in cargo, request, shipment, and economics components remain direct strings and are never passed to the formatter.

## F. Product Changes

| Runtime file | Reason |
| --- | --- |
| `src/lib/formatQuantity.ts` | Extends the existing authoritative cargo helper into the single locale-aware, string-precision-safe numeric contract. |
| `src/components/ShipmentCargoItems.tsx` | Uses the shared quantity display for tracking allocations while leaving form values and identifiers untouched. |
| `src/components/CargoCatalogAdminTab.tsx` | Groups shipment counts and applies approved quantity trailing-zero semantics to usage rows. |
| `src/components/ShipmentEconomicsSection.tsx` | Groups projection/history/preview money without changing currency or stored scale. |
| `src/pages/RequestDetail.tsx` | Reconciles cargo measurements/value, quote amount, and allocated quantity displays. |
| `src/pages/PublicTracking.tsx` | Reconciles customer-visible quote, unit counts, and progress display. |
| `src/pages/CustomerRequestDetail.tsx` | Reconciles customer-visible quote amount display. |

No backend runtime, database model, migration, API serialization, quote lifecycle, geography, date/time, notification, or Control Tower file changed.

## G. Surface Acceptance

- **Cargo:** large total, allocated, remaining, catalog usage, and tracking-allocation quantities are grouped; significant decimals survive and storage-only trailing zeroes are trimmed.
- **Request/shipment summary:** weight, volume, declared value, latest quote, and allocated cargo values use the shared contract; missing fallbacks remain surface-specific.
- **Economics/quote amounts:** Expert operational economics and customer/public quote views group large amounts while keeping the currency token and recorded fractional digits unchanged.
- **Operational/customer/Expert views:** the changed detail and tracking surfaces share the same presentation logic. Existing correctly grouped Admin summary cards remain compatible through their specialized `Intl` formatter.

## H. Input / API Integrity

Formatting is display-only. No `input` type, form state, `Number(...)` / `parseFloat(...)` submission conversion, API request payload, API response type, backend storage, or serialization was changed. Direct tests retain the source payload after formatting, and request-flow tests prove phone/location payload identity. Existing numeric `<input type="number">` controls do not receive grouping separators.

## I. Date/Time Isolation

No date/time/calendar helper or runtime consumer was changed. FWD-04 date/time code was not imported. The focused `localDate`, `localDateTime`, timestamp, and Operational Shipment Detail tests passed, and the full suites passed.

```text
DATE_TIME_BEHAVIOR_CHANGED=NO
```

## J. Phase B1 Preservation

Phase B1 catalog, reconciliation, search/paging, stable identity, inactive-record, fallback-label, request round-trip, selector, and route-authoring tests passed. No geography/catalog runtime or evidence file was changed.

```text
GEOGRAPHY_B1_REGRESSED=NO
```

## K. Tests

| Gate | Result |
| --- | --- |
| Pre-change focused backend Golden baseline | PASS — 51 tests |
| Pre-change focused frontend Golden baseline | PASS — 5 files, 58 tests |
| Numeric/identifier/date focused frontend | PASS — 6 files, 42 tests |
| Final focused backend Golden + B1 | PASS — 96 tests |
| Final focused frontend numeric + Golden + B1 | PASS — 13 files, 117 tests |
| Full backend suite | PASS — 1,050 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failures |
| Full frontend suite | PASS — 58 files, 291 tests |
| TypeScript | PASS — `npx tsc --noEmit` |
| Production build | PASS — 2,537 modules; output directed to a disposable directory; no tracked `dist` delta |
| ESLint | PASS — 0 errors, 13 unchanged historical warnings |
| Alembic graph/current/check | PASS — one expected head; `pending=no` |
| Migration and compiled-output delta | PASS — zero migration files and zero tracked `dist` files changed |

Phase B1 recorded 1,050 backend passes and 286 frontend tests. This slice retains the backend count and adds five frontend tests, for 291 total. The 93 PostgreSQL/environment-dependent skips and one expected xfail are unchanged and are not represented as newly executed PASS.

## L. Database Contract

```text
DATABASE_HEAD =
20260921_shipment_evidence_ownership

MIGRATION_ADDED =
NO

MIGRATION_MODIFIED =
NO

PENDING_MIGRATION =
NO
```

## M. Golden Contract Status

```text
GCF-A-003 = PASS
GCF-A-005 = PASS
GCF-A-008 = PASS
GCF-A-011 = PASS
GCF-A-012 = PASS
```

## N. Scope Integrity

```text
GEOGRAPHY_B1_REGRESSED=NO
DATE_TIME_BEHAVIOR_CHANGED=NO
CURRENCY_SEMANTICS_CHANGED=NO
QUOTE_LIFECYCLE_CHANGED=NO
CONTROL_TOWER_IMPORTED=NO
OTHER_FWD_FEATURE_IMPORTED=NO
PRODUCT_MIGRATION_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO
```

No Production endpoint, environment, database, process, task, credential, or secret was accessed. No deploy, push, merge, cherry-pick, or RC operation occurred.

## O. Remaining Risks

- Semantic classification remains a caller responsibility: a formatter cannot infer whether an arbitrary digit-only string is a quantity or an identifier. The governed names, bounded adoption, and exclusion tests reduce but cannot eliminate misuse by future callers.
- Exact values already delivered as JavaScript `number` cannot recover precision lost before presentation. Exact large API numeric values remain safe when serialized as strings, which the shared formatter handles without coercion.
- Some intentionally specialized or out-of-scope numeric displays remain distributed. Future slices, including Control Tower, must adopt this contract for actual business quantities/amounts instead of creating a competing formatter.

## P. Verdict

PASS — SHARED NUMERIC PRESENTATION COMPLETE

## Q. Next Goal

Execute exactly one separate approved slice: **Phase B — Slice 3 — Existing Transport Summary**.

- Start from the clean Phase B2 commit and preserve the shared numeric contract.
- Reconcile only presentation/summary of the existing Golden scalar transport fields and actual operational route legs.
- Do not choose or introduce multimodal request semantics, ordered-leg intake, schema changes, mandatory cargo policy, quote/EUR changes, date/time changes, notifications, documents, or Control Tower.
- Inventory current request, customer, Expert, and operational transport summaries; select bounded FWD-03 tests/semantics only where they preserve Golden.
- Add focused summary compatibility tests, keep request/API payloads unchanged, run relevant Phase A/B1/B2 regressions plus full qualification, add no migration, and finish in one separate attributable commit.

This next goal was derived from the controlled integration plan and was not executed here.
