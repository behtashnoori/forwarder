# Phase 6F: Customer Workflow API Client Refactor

## 1. Scope

This phase only refactored frontend customer workflow API usage into the centralized API client. It did not change backend code, OpenAPI files, routing, UI layout, styling, auth/security behavior, schemas, migrations, dependencies, public tracking, customer profile behavior, customer write flows, or unrelated frontend domains.

Target endpoint:

- `GET /api/customer/workflow/<customer_id>`

## 2. Before

`src/pages/CustomerRequestDetail.tsx` called the customer workflow endpoint directly:

- built the URL from `env.API_URL`
- interpolated `customer` into `/api/customer/workflow/${customer}`
- appended the existing `?request_id=${requestId}` query string
- called `fetch()` directly
- mapped any non-OK HTTP response to the existing request-not-found toast
- mapped network/unexpected errors to the existing generic fetch-error toast

## 3. API Client Design

`src/lib/api.ts` now exposes:

- `fetchCustomerWorkflow(customerId, requestId)`
- `CustomerWorkflowData`
- `CustomerWorkflowStep`
- `CustomerWorkflowHttpError`

The helper preserves the same endpoint and query shape:

- path: `/api/customer/workflow/${customerId}?request_id=${requestId}`
- method: `GET`

The helper throws `CustomerWorkflowHttpError` for non-OK HTTP responses so `CustomerRequestDetail` can preserve its previous non-OK toast behavior. Network and unexpected fetch errors still surface as ordinary errors and continue to use the existing generic fetch-error toast.

## 4. Changes Made

| File | Change summary | Reason | Behavior impact |
| --- | --- | --- | --- |
| `src/lib/api.ts` | Added customer workflow response types, `CustomerWorkflowHttpError`, and `fetchCustomerWorkflow(customerId, requestId)` | Centralize customer workflow API access | No intended behavior change |
| `src/pages/CustomerRequestDetail.tsx` | Replaced direct `fetch` with `fetchCustomerWorkflow`; imported shared response type | Remove scattered raw API call | No intended behavior change |
| `docs/phase-6f-customer-workflow-api-client-refactor.md` | Added phase documentation | Record scope, design, preservation, and verification | Documentation only |

## 5. Behavior Preservation

- Endpoint path remains `/api/customer/workflow/<customer_id>`.
- HTTP method remains `GET`.
- Query string remains `?request_id=<request_id>`.
- Loading state still starts as `true` and is cleared in `finally`.
- Refreshing state still clears in `finally`.
- Successful responses still call `setRequestDetail(data)`.
- Non-OK HTTP responses still show the existing request-not-found toast.
- Network/unexpected errors still show the existing generic fetch-error toast.
- Workflow step rendering was not changed.
- Latest quote rendering was not changed.
- Assigned expert rendering was not changed.
- Layout, cards, badges, Persian/English messages, navigation, and refresh behavior were not changed.

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
- Customer complete-step API client refactor.
- Customer registration API client refactor.
- Customer email verification API client refactor.
- Admin API client refactor.
- Expert API client refactor.
- CRM API client refactor.
