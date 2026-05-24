# Phase 6E: Customer Profile API Client Refactor

## 1. Scope

This phase only refactored frontend customer profile API usage into the centralized API client. It did not change backend code, OpenAPI files, routing, UI layout, styling, auth/security behavior, schemas, migrations, dependencies, public tracking, workflow reads, customer write flows, or unrelated frontend domains.

Target endpoint:

- `GET /api/customer/profile/<customer_id>`

## 2. Before

`src/pages/CustomerDashboard.tsx` called the customer profile endpoint directly:

- built the URL from `env.API_URL`
- interpolated `customerId` into `/api/customer/profile/${customerId}`
- called `fetch()` directly
- mapped any non-OK HTTP response to the existing "customer not found" toast
- mapped network/unexpected errors to the existing "fetch error" toast
- stored `customer_panel_id` in localStorage after successful profile loading

## 3. API Client Design

`src/lib/api.ts` now exposes:

- `fetchCustomerProfile(customerId)`
- `CustomerProfileData`
- `CustomerProfile`
- `CustomerProfileWorkflowStep`
- `CustomerProfileRecentRequest`
- `CustomerProfileHttpError`

The helper preserves the same endpoint shape:

- path: `/api/customer/profile/${customerId}`
- method: `GET`

The helper throws `CustomerProfileHttpError` for non-OK HTTP responses so `CustomerDashboard` can preserve its previous non-OK toast behavior. Network and unexpected fetch errors still surface as ordinary errors and continue to use the existing generic fetch-error toast.

## 4. Changes Made

| File | Change summary | Reason | Behavior impact |
| --- | --- | --- | --- |
| `src/lib/api.ts` | Added customer profile response types, `CustomerProfileHttpError`, and `fetchCustomerProfile(customerId)` | Centralize customer profile API access | No intended behavior change |
| `src/pages/CustomerDashboard.tsx` | Replaced direct `fetch` with `fetchCustomerProfile`; imported shared response type | Remove scattered raw API call | No intended behavior change |
| `docs/phase-6e-customer-profile-api-client-refactor.md` | Added phase documentation | Record scope, design, preservation, and verification | Documentation only |

## 5. Behavior Preservation

- Endpoint path remains `/api/customer/profile/<customer_id>`.
- HTTP method remains `GET`.
- Path parameter interpolation remains unchanged.
- Loading state still starts as `true` and is cleared in `finally`.
- Refreshing state still clears in `finally`.
- Successful responses still call `setData(customerData)`.
- `customer_panel_id` is still written to localStorage only after a successful response.
- Non-OK HTTP responses still show the existing "customer not found" toast.
- Network/unexpected errors still show the existing generic fetch-error toast.
- Rendering, Persian/English messages, layout, cards, badges, recent requests, recent activity, navigation, and refresh behavior were not changed.

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
- Customer workflow API client refactor.
- Customer complete-step API client refactor.
- Customer registration API client refactor.
- Admin API client refactor.
- Expert API client refactor.
- CRM API client refactor.
