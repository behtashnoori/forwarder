# Phase 6H: Customer Registration API Client Refactor

## 1. Scope

This phase reviewed frontend customer registration API usage. No runtime code was changed because no active frontend call site for `POST /api/customer/register` was found.

The phase did not change backend code, OpenAPI files, routing, UI layout, styling, auth/security behavior, schemas, migrations, dependencies, public tracking, customer profile behavior, customer workflow behavior, customer email verification behavior, customer complete-step behavior, or unrelated frontend domains.

Target endpoint:

- `POST /api/customer/register`

## 2. Before

Searches were run across `src` for:

- `/api/customer/register`
- `customer/register`
- `registerCustomer`
- `CustomerRegister`
- direct customer API `fetch()` usage

No frontend file currently calls `POST /api/customer/register` directly. No `CustomerRegister` page/component was found under `src`.

The only customer gamification frontend API calls currently found are:

- public tracking, now centralized in `src/lib/api.ts`
- customer profile, now centralized in `src/lib/api.ts`
- customer workflow, now centralized in `src/lib/api.ts`
- email verification, now centralized in `src/lib/api.ts`

## 3. API Client Design

No `registerCustomer(payload)` function was added in this phase because there is no active frontend registration call site to replace.

Adding an unused API helper would create a new frontend API surface without reducing scattered usage, so it is deferred until a registration UI exists or a concrete call site is identified.

Future helper shape, when needed, should be based on the backend/OpenAPI contract for:

- path: `/api/customer/register`
- method: `POST`
- body: current registration payload
- response: current registration response shape
- error handling: preserve current frontend behavior once a frontend caller exists

## 4. Changes Made

| File | Change summary | Reason | Behavior impact |
| --- | --- | --- | --- |
| `docs/phase-6h-customer-registration-api-client-refactor.md` | Added phase documentation and no-op decision | Record that no frontend registration usage exists to refactor | None |

## 5. Behavior Preservation

- Endpoint path was not changed.
- HTTP method was not changed.
- Request body shape was not changed.
- Success rendering was not changed.
- Validation/error rendering was not changed.
- Duplicate customer behavior was not changed.
- Email-send failure handling was not changed.
- Loading behavior was not changed.
- Navigation/redirect behavior was not changed.

Because there is no frontend registration call site, all behavior remains exactly as it was before this phase.

## 6. Verification

| Command | Result |
| --- | --- |
| `npm.cmd run lint` | Passed with existing warnings |
| `npm.cmd run build` | Passed with existing Browserslist/chunk-size warnings |
| `npm.cmd run check:structure` | Passed |
| `python -m pytest -q` | Passed |
| `git diff --check` | Passed with existing CRLF warnings |

## 7. Deferred Items

- Generated OpenAPI client.
- Customer registration API helper when an actual frontend caller exists.
- Customer complete-step API client refactor if a frontend caller exists.
- Admin API client refactor.
- Expert API client refactor.
- CRM API client refactor.
- Frontend warning cleanup.
