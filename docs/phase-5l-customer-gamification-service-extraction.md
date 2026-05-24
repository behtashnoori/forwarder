# Phase 5L: Customer Gamification Service Extraction

## Scope

Only `GET /api/customer/leaderboard` was extracted.

Out of scope:

- registration
- email verification
- profile read
- workflow read
- workflow completion
- points mutation

## Service Design

Added `backend/services/customer_gamification_service.py` with:

- `list_leaderboard_payload()`
- `build_leaderboard_entry(customer, rank)`

## Behavior Preserved

The service preserves:

- `CustomerGamification.is_email_verified == True`
- ordering by `loyalty_points desc`
- limit `20`
- rank starting at `1`
- anonymous name fallback: `کاربر ناشناس`
- response shape: `{"leaderboard": [...], "total_customers": len(customers)}`
- route-level 500 payload: `{"message": "خطا در دریافت جدول امتیازات"}`

## Route After

`get_leaderboard` now only calls the service, `jsonify`s the returned payload, and preserves the existing error handling.

## Tests

`backend/tests/test_customer_gamification_contract.py` locks the leaderboard contract before and after extraction.

## Deferred Items

- profile read service extraction
- workflow read service extraction
- any write-flow extraction
- changing `total_customers` semantics
