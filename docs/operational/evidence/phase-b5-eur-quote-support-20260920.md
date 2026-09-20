# Phase B — Slice 5 — EUR Quote Support — 2026-09-20

## A. Starting State

| Item | Verified value |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Required starting branch | `codex/phase-b4-request-count-list-invariant` |
| Slice branch | `codex/phase-b5-eur-quote-support` |
| Starting HEAD / B4 commit | `02acad646e2349296653bf0cf0bc5fe38519fb98` |
| Required parent / B3 commit | `d1dd6b60abc27846d563816c34b9aa4de190161a` |
| Starting cleanliness | clean |
| Golden application provenance | `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4` |
| Phase A commit | `953a67ff5820864c08bc8727f34f49ed66237527` |
| B1 geography commit | `a503d7b6473b90b01ff9a11c6e751375ff9f2121` |
| B2 numeric commit | `b523cc0b18fd48d93101de0430ec91d56a438c12` |
| B3 transport commit | `d1dd6b60abc27846d563816c34b9aa4de190161a` |
| B4 count/list commit | `02acad646e2349296653bf0cf0bc5fe38519fb98` |
| Database head | `20260921_shipment_evidence_ownership` |

The required Phase A Markdown/JSON evidence, B1/B2/B3/B4 evidence, and controlled integration plan were present and read before implementation. The exact required branch, HEAD, parent, clean state, one-base/one-head migration graph, and disposable `pending=no` result matched. The slice branch was created directly from the required starting HEAD.

## B. Existing Currency Architecture

| Classification | Existing / resulting seam | Contract |
| --- | --- | --- |
| `AUTHORITATIVE_CURRENCY_SOURCE` | `contracts/quote-currencies.v1.json` | The single bounded quote set is now IRR, USD, EUR, with IRR retained as the default and existing Persian selector labels preserved. |
| `VALIDATION` | `backend/services/quote_currency.py` and `quote_service.normalize_quote_payload` | The backend loads the same contract used by the UI and accepts only exact canonical codes. Missing/blank currency retains the Golden IRR default; arbitrary codes are rejected with HTTP 400. |
| `PERSISTENCE` | `ExpertQuote.currency` | Existing non-null `String(10)` storage already represents `EUR`; quote amounts retain the existing integer `BIGINT` contract. No schema change is needed. |
| `SERIALIZATION` | `quote_service.build_quote_payload`, Expert detail/latest quote, Customer workflow, tracking, and accepted-quote economics | Existing serializers already copy the persisted code unchanged. No serializer, response shape, or API lifecycle was redesigned. |
| `PRESENTATION` | `QuoteModal`, `RequestDetail`, `CustomerRequestDetail`, `PublicTracking`, and `formatQuantity.formatMoney` | The selector consumes the authoritative contract. Existing read surfaces append the unchanged currency code to the B2-formatted amount. |
| `OUT_OF_SCOPE` | Shipment economics `CURRENCIES`, FX facts, and conversion paths | Economics is a separate broader currency domain that already includes EUR. No exchange rate or conversion path was added or invoked by quote creation/read/response. |

Before this slice, the quote selector locally listed IRR/USD while backend quote creation accepted any string. Persistence and downstream serializers could already retain EUR. The bounded change establishes one quote-specific source of truth, aligns backend validation with it, and adds EUR to the existing selector.

## C. FWD-05 Donor Analysis

Read-only inspection used implementation commit `92f14a08e544fb79961c2021addbf97c13ea5b1f` and the EUR/currency-relevant deltas in qualification commits `700381c42072a10bd8a7ce7a0e36db6252454ff7` and `29630f9ee255b9b0189124b4d41fb262422e53f9`.

Exact donor files inspected for currency semantics were:

- `backend/services/governed_quote_service.py`
- `backend/services/quote_service.py`
- `backend/models.py`
- `backend/migrations/versions/20260916_fwd05_quote_response.py` (inspection only; rejected)
- `backend/tests/test_fwd05_runtime.py`
- `backend/tests/test_fwd05_http_boundary.py`
- `backend/tests/test_fwd05_postgresql.py`
- `src/components/QuoteModal.tsx`

Reused semantics were the bounded IRR/USD/EUR set, canonical `EUR` code, exact supported-code validation, and a normal Expert selector option. Rejected semantics were decimal/exact-money redesign, quote settings endpoints, `negotiation_requested`, publication/replacement lifecycle, capability grants, response receipts, notification delivery, donor authorization rewrites, and the donor migration. Golden's integer amount, accepted/declined response, opaque tracking capability, request-state behavior, and existing authorization remain authoritative.

No donor branch was merged or cherry-picked. No donor file was copied wholesale, and neither donor repository was modified.

## D. EUR Product Behavior

An assigned and tenant-authorized Expert can select `یورو (EUR)` in the existing quote modal. Submission sends the canonical `EUR` code through the unchanged quote endpoint. Backend validation accepts it, `ExpertQuote.currency` stores it unchanged, and both the create response and later Expert latest/detail reads return `EUR` with the original integer amount.

The existing Customer workflow and public quote projections return the same persisted `EUR` value. Customer Request Detail renders the amount and `EUR`, and the existing accept/decline endpoint handles it without a currency-specific branch. Repeated reads after creation and response retain `EUR`.

## E. Validation

`contracts/quote-currencies.v1.json` is the only supported-quote-currency allowlist. `backend/services/quote_currency.py` validates that contract at import time and exposes its default and immutable code set. `quote_service.normalize_quote_payload` accepts only `IRR`, `USD`, or `EUR`; exact uppercase project convention is required. Missing/blank currency continues to default to IRR for existing clients. Unsupported `JPY` is proven to return HTTP 400 and create no quote.

The UI does not maintain a second allowlist: it imports the same contract and renders its three entries.

## F. Persistence

The existing `ExpertQuote.currency` column is `String(10)`, non-null, with no currency enum/check restriction. Focused tests create `amount=1234567, currency=EUR`, read the ORM row, Expert endpoint, Customer workflow, response payload, and refreshed Expert endpoint, and receive the same amount/code at every step. There is no normalization to another currency and no amount mutation.

Historical rows with other currency strings remain readable; this slice bounds only new quote creation and does not rewrite history.

## G. Presentation

The Expert selector clearly labels EUR as `یورو (EUR)`. Expert Request Detail and Customer Request Detail continue to call the B2 `formatMoney` helper. Focused role-consistency coverage proves both render `1,234,567 EUR` for the same API value and do not substitute IRR or USD.

No number formatter was added. No symbol is inferred, no alternate-currency amount is shown, and no FX/conversion service is called.

## H. Customer Response Integrity

Focused EUR coverage executes both outcomes:

- EUR quote -> `accepted`
- EUR quote -> `declined`

For each, the same-response replay returns 200 and remains idempotent; the opposite response returns 409; `responded_at`, unread, and one audit fact are recorded; and the request remains in the exact status it held before the response (`waiting_for_customer` in the create-to-response journey). The existing Golden characterization in which a pre-existing `quoted` request remains `quoted` also passed unchanged. Expired EUR quotes remain non-responsive with HTTP 400. No response state or request transition was added.

## I. Authorization

Quote creation/read still uses the existing assigned-Expert/admin check plus tenant-resource and active membership enforcement. The focused test proves a foreign-organization Expert cannot create or read the EUR quote. Customer response still requires the existing opaque tracking code; an unrelated code returns the same 404 behavior. No role, tenant, assignment, or capability boundary changed.

## J. Product Changes

| Runtime file | Reason |
| --- | --- |
| `contracts/quote-currencies.v1.json` | Single IRR/USD/EUR quote-currency source shared by backend and frontend. |
| `backend/services/quote_currency.py` | Loads and fail-fast validates the authoritative contract; exports the default and supported set. |
| `backend/services/quote_service.py` | Routes new quote currency through the bounded validation set and reuses the contract default in serialization. |
| `src/components/QuoteModal.tsx` | Renders the shared contract, adding EUR without a second UI allowlist. |

Focused coverage was added in:

- `backend/tests/test_phase_b5_eur_quote_support.py`
- `src/tests/components/QuoteModal.test.tsx`
- `src/tests/pages/QuoteCurrency.role-consistency.test.tsx`

No quote response service, request status service, model, migration, notification, geography, transport, count/list, tracking, document, date/time, Control Tower, or economics runtime file changed.

## K. Regression Status

```text
GCF-A-002 = PASS
GCF-A-003 = PASS
GCF-A-005 = PASS
GCF-A-008 = PASS
GCF-A-011 = PASS
GCF-A-012 = PASS

PHASE_B1_GEOGRAPHY = PASS
PHASE_B2_NUMERIC = PASS
PHASE_B3_TRANSPORT_SUMMARY = PASS
PHASE_B4_REQUEST_COUNT_LIST = PASS
```

The named regression selection passed 78 backend tests and 75 frontend tests. Full suites passed with exact expected count increases and no unexplained reduction.

## L. Tests

| Gate | Exact result |
| --- | --- |
| Pre-change quote/auth/customer/economics backend baseline | PASS — 48 passed |
| Pre-change presentation frontend baseline | PASS — 3 files, 10 tests |
| Final focused quote/auth/customer/economics backend | PASS — 54 passed |
| Final focused EUR/B2 frontend | PASS — 5 files, 12 tests |
| Focused Phase A + B1/B2/B3/B4 backend regression | PASS — 78 passed |
| Focused Phase A + B1/B2/B3/B4 frontend regression | PASS — 11 files, 75 tests |
| Full backend suite | PASS — 1,059 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failed |
| Full frontend suite | PASS — 64 files, 301 tests |
| TypeScript | PASS — `npx tsc --noEmit` |
| Production build | PASS — 2,539 modules transformed; isolated output outside the repository; no tracked `dist` delta |
| ESLint | PASS — 0 errors, 13 unchanged historical warnings |
| Migration/runtime focused suite | PASS — 32 passed |
| Alembic graph/current/check | PASS — 97 revisions; one base; one expected head; disposable current equals head; `pending=no` |
| Migration delta | PASS — zero files changed under `backend/migrations` |
| Diff integrity | PASS — `git diff --check`; only Git line-ending notices |

B4 recorded 1,053 backend passes and 299 frontend tests. This slice adds six backend tests and two frontend tests, producing 1,059 backend passes and 301 frontend tests. The 93 environment-dependent/PostgreSQL skips and one expected xfail are unchanged and are not represented as executed PASS.

## M. Database Contract

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

The authoritative proof used a disposable SQLite database stamped at the repository head. Both `current` and `check` reported `current=20260921_shipment_evidence_ownership`, `heads=20260921_shipment_evidence_ownership`, and `pending=no`.

During the initial prerequisite probe, a PowerShell path-conversion error caused a stamp-only command to target the user-local development SQLite database. Tool output exposed its prior marker (`20240919_add_code_to_province`); that exact marker was immediately restored before work continued. No upgrade, schema DDL, or application-data operation ran, and that database was not used as qualification evidence. Production and Production configuration were never accessed.

## N. Scope Integrity

```text
EUR_SUPPORTED=YES
CURRENCY_CONVERSION_ADDED=NO
QUOTE_RESPONSE_STATES_CHANGED=NO
REQUEST_STATUS_SEMANTICS_CHANGED=NO
NOTIFICATION_WORK_IMPORTED=NO
GEOGRAPHY_REGRESSED=NO
NUMERIC_PRESENTATION_REGRESSED=NO
TRANSPORT_BEHAVIOR_CHANGED=NO
REQUEST_COUNT_LIST_REGRESSED=NO
CONTROL_TOWER_IMPORTED=NO
OTHER_FWD_FEATURE_IMPORTED=NO
PRODUCT_MIGRATION_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO
```

No deploy, push, merge, cherry-pick, RC build, Production endpoint, Production environment, Production database, process, task, credential, or secret was accessed or changed. No second Phase B slice was started.

## O. Remaining Risks

- Golden quotes store integer amounts for every supported currency. EUR therefore follows the existing IRR/USD integer contract and does not support cents; adding fractional quote money would require a separately approved model/schema and lifecycle-compatible design.
- Historical quote rows can contain currency strings outside the newly bounded creation set because the database deliberately remains generic. They stay readable for compatibility; this slice does not reinterpret or clean historical evidence.
- Runtime packaging must continue to include `contracts/quote-currencies.v1.json`. The existing release builder already packages the `contracts` tree, and the production build proves the frontend embeds the same contract.

## P. Verdict

PASS — EUR QUOTE SUPPORT COMPLETE

## Q. Next Goal

Execute exactly one separate approved slice: **Phase B — Slice 6 — Retired Tracking-Action Removal**.

Start from the clean B5 commit. Remove/hide only the retired legacy add-unit action from current UI reachability while preserving the canonical execution-unit/event path, tracking authorization, safe Customer projection, occurred/recorded timestamps, location snapshots, and all Phase A/B1–B5 contracts. Use bounded FWD-06 scenarios only as test/semantic evidence; do not import its migration, manual-time provenance, receipts, cumulative pages, notification work, Control Tower, or another Phase B slice. Add no migration, run focused tracking and prior-slice regressions plus the full gate, and finish in one separately attributable commit. This next goal was derived from the controlled integration plan and was not executed here.
