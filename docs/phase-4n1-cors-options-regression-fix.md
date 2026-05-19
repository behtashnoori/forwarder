# Phase 4N.1: CORS OPTIONS Regression Fix

## Scope

Phase 4N.1 is limited to the failing CORS OPTIONS checks in
`backend/tests/test_cors.py`.

No application feature, business endpoint behavior, database model, schema,
migration, authentication, role logic, or frontend code was changed.

## Before

Baseline verification before the fix:

- `python -m pytest backend/tests/test_cors.py -q`: 2 failed
- `python -m pytest backend/tests/test_api.py::TestAPIEndpoints::test_cors_headers -q`: 1 passed
- `python -m pytest -q`: 66 passed, 2 failed

Both failures were:

- `test_options_provinces_returns_cors_headers`
- `test_options_transport_methods_returns_cors_headers`

The OPTIONS responses returned HTTP 200 but did not include
`Access-Control-Allow-Origin`.

## Root Cause

The two failing tests sent structurally valid preflight requests:

- `Origin` was present.
- `Access-Control-Request-Method: GET` was present.

However, the origin used by the tests was `http://130.185.77.25:8080`.
Current CORS policy does not allow that origin in testing/development by
default. Non-production defaults allow localhost and 127.0.0.1 development
origins, plus explicitly configured HTTP origins. Production remains limited to
explicit configured origins.

Because the test origin was not allowed, the CORS preflight helper correctly did
not add `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, or related
CORS response headers.

## Fix Applied

The test origin in `backend/tests/test_cors.py` was changed to an allowed
non-production origin:

- From `http://130.185.77.25:8080`
- To `http://127.0.0.1:8080`

The assertions were kept meaningful and were tightened to verify that the
preflight response includes `GET` in `Access-Control-Allow-Methods`.

## CORS Contract Decision

The CORS contract remains:

- A valid preflight request from an allowed origin receives CORS headers.
- A valid preflight request from a disallowed origin must not be treated as
  allowed.
- Development and testing may use localhost and 127.0.0.1 origins.
- Production may use only explicitly configured CORS origins.

## Production Safety

Production CORS was not opened or relaxed.

No wildcard origin, allow-all production behavior, or production localhost
allowance was added.

## After

Post-fix verification:

- `python -m pytest backend/tests/test_cors.py -q`: 2 passed
- `python -m pytest backend/tests/test_api.py::TestAPIEndpoints::test_cors_headers -q`: 1 passed
- `python -m pytest -q`: 68 passed
- `npm.cmd run lint`: passed with existing warnings, 0 errors
- `npm.cmd run build`: passed
- `npm.cmd run check:structure`: passed
- `git diff --check`: passed

## Deferred Items

No CORS implementation changes were required for Phase 4N.1.

Existing warnings from pytest are outside this phase and remain deferred.
