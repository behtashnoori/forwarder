# Phase 6G: Customer Email Verification API Client Refactor

## 1. Scope

This phase only refactored frontend customer email verification API usage into the centralized API client. It did not change backend code, OpenAPI files, routing, UI layout, styling, auth/security behavior, schemas, migrations, dependencies, public tracking, customer profile behavior, customer workflow behavior, customer write flows, or unrelated frontend domains.

Target endpoint:

- `GET /api/customer/verify-email`

## 2. Before

`src/pages/VerifyEmail.tsx` called the email verification endpoint directly:

- built the URL from `env.API_URL`
- appended `?token=${encodeURIComponent(token)}`
- called `fetch()` directly
- parsed JSON for both OK and non-OK responses
- used backend `message` when available
- navigated to `/customer/<customer_id>` on successful verification
- showed the existing invalid/expired-token or server-error messages otherwise

## 3. API Client Design

`src/lib/api.ts` now exposes:

- `verifyCustomerEmail(token)`
- `CustomerEmailVerificationResponse`
- `CustomerEmailVerificationResult`

The helper preserves the same endpoint and query behavior:

- path: `/api/customer/verify-email?token=${encodeURIComponent(token)}`
- method: `GET`

The helper intentionally returns `{ ok, data }` instead of throwing for non-OK HTTP responses. This preserves the previous page behavior, where invalid or expired tokens can still display the backend-provided response message.

## 4. Changes Made

| File | Change summary | Reason | Behavior impact |
| --- | --- | --- | --- |
| `src/lib/api.ts` | Added email verification response types and `verifyCustomerEmail(token)` | Centralize email verification API access | No intended behavior change |
| `src/pages/VerifyEmail.tsx` | Replaced direct `fetch` with `verifyCustomerEmail` | Remove scattered raw API call | No intended behavior change |
| `docs/phase-6g-customer-email-verification-api-client-refactor.md` | Added phase documentation | Record scope, design, preservation, and verification | Documentation only |

## 5. Behavior Preservation

- Endpoint path remains `/api/customer/verify-email`.
- HTTP method remains `GET`.
- Token query parameter still uses `encodeURIComponent(token)`.
- Missing token still sets `error` status and the existing invalid-link message without making a request.
- Loading behavior still sets `status` to `loading` before the request.
- Successful verification still requires `ok && data.customer_id`.
- Success rendering and message fallback were not changed.
- Successful verification still navigates to `/customer/<customer_id>` with `{ replace: true }`.
- Invalid/expired token behavior still uses `data.message` when present, otherwise the existing fallback message.
- Network/unexpected errors still show the existing server-connection message.

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
- Admin API client refactor.
- Expert API client refactor.
- CRM API client refactor.
