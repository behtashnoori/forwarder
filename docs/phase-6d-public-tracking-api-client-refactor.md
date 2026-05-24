# Phase 6D: Public Tracking API Client Refactor

## 1. Scope

This phase only refactored frontend public tracking API usage into the centralized API client. It did not change backend code, OpenAPI files, routing, UI layout, styling, auth/security behavior, schemas, migrations, dependencies, or unrelated frontend domains.

Target endpoint:

- `GET /api/public/track/<identifier>`

## 2. Before

The public tracking page called the backend directly from `src/pages/PublicTracking.tsx`:

- built the URL from `env.API_URL`
- encoded the tracking identifier inline
- called `fetch(url)` directly
- handled `200`, `404`, other HTTP errors, and network errors inside the page

## 3. API Client Design

`src/lib/api.ts` now exposes:

- `fetchPublicTracking(identifier)`
- `PublicTrackingData`
- `PublicTrackingWorkflowStep`
- `PublicTrackingNotFoundError`
- `PublicTrackingHttpError`

The helper preserves the same endpoint path and path-parameter encoding:

- path: `/api/public/track/${encodeURIComponent(identifier)}`
- method: `GET`

The helper intentionally keeps status information for the page:

- `404` throws `PublicTrackingNotFoundError`
- other non-OK HTTP statuses throw `PublicTrackingHttpError`
- network failures still surface as ordinary fetch errors

This lets the page keep its existing not-found and toast behavior.

## 4. Changes Made

| File | Change summary | Reason | Behavior impact |
| --- | --- | --- | --- |
| `src/lib/api.ts` | Added public tracking response types, status-specific errors, and `fetchPublicTracking(identifier)` | Centralize public tracking API access | No intended behavior change |
| `src/pages/PublicTracking.tsx` | Replaced direct `fetch` with `fetchPublicTracking`; imported shared response type | Remove scattered raw API call | No intended behavior change |
| `docs/phase-6d-public-tracking-api-client-refactor.md` | Added phase documentation | Record scope, design, preservation, and verification | Documentation only |

## 5. Behavior Preservation

- Endpoint path remains `/api/public/track/<identifier>`.
- HTTP method remains `GET`.
- The tracking identifier is still encoded with `encodeURIComponent`.
- Loading state still starts as `true` and is cleared in `finally`.
- Successful responses still call `setRequestData(data)`.
- `404` still sets `notFound` to `true`.
- Other HTTP errors still show the existing request-data error toast.
- Network/unexpected errors still show the existing server-connection error toast.
- Rendering, Persian/English messages, layout, cards, badges, timeline behavior, and navigation were not changed.

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
- Other scattered API calls.
- Customer API client refactor.
- Admin API client refactor.
- Expert API client refactor.
- CRM API client refactor.
