# A1 safe execution log

Command: python -B -m pytest -q -p no:cacheprovider backend/tests/test_fwd05_signing_feasibility.py
First reviewer execution: 18 passed, 1 existing backend/monitoring.py utcnow warning, 0 skip/XFAIL, 0.41s. Ambient app/staff signing configuration was not explicitly overridden; no values were inspected or printed.
Authoritative repeat: process-local SECRET_KEY and JWT_SECRET_KEY explicitly set to synthetic reviewer-only values before imports. Same command: 18 passed, 1 existing backend/monitoring.py utcnow warning, 0 skip/XFAIL, 0.40s.

Read-only in-memory experiment (only ephemeral random quote key, synthetic fixed claims):
PYJWT_VERSION 2.13.0
REORDERED_PERSISTED_JSON_EXACT_TOKEN_EQUAL False
LIBRARY_ACCEPTS_NONSTRICT iat str
LIBRARY_ACCEPTS_NONSTRICT nbf bool
LIBRARY_ACCEPTS_NONSTRICT revision bool
LIBRARY_ACCEPTS_NONSTRICT aud list

No token/key values output. Library _encode_payload source shows compact JSON dumps without sorted payload keys; source hash in manifest. No safe probe changed product/code/config/input files; bytecode/cache creation disabled for reviewer test invocation. Only reviewer artifacts subsequently written under explicitly authorized A1 output directory.
