# Phase 5K: Customer Gamification Characterization

## Route Inventory

| Endpoint | Method | Auth | Responsibility | Read/Write | Side effects | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `/api/customer/register` | POST | public | register customer and issue verification token | write | customer insert, email-send attempt, commit | high |
| `/api/customer/verify-email` | GET | public | verify token and award points | write | customer mutation, workflow step insert, commit | high |
| `/api/customer/profile/<customer_id>` | GET | public | read profile, recent steps, recent requests | read | none | medium |
| `/api/customer/workflow/<customer_id>` | GET | public | read request workflow and latest quote | read | none | medium |
| `/api/customer/complete-step` | POST | public | complete workflow step and award points | write | workflow insert/update, points mutation, commit | high |
| `/api/customer/leaderboard` | GET | public | read verified customer ranking | read | none | low |

## Current Behavior Map

Characterization tests lock:

- registration required fields, invalid email, invalid phone, duplicate email, success shape, normalization, and token creation
- email verification missing/invalid token and success point/workflow effects
- profile missing customer and success response shape
- workflow missing/invalid request id, ownership 404, success response shape, latest quote, and workflow summary fields
- complete-step missing fields, success points, duplicate completion behavior
- leaderboard verified-only behavior, ordering, limit, ranks, response shape, and anonymous fallback

## Existing Coverage

Before this phase, direct `/api/customer/*` coverage was not present. Related public tracking tests covered timeline helpers but not these customer gamification endpoints.

## Added Coverage

Added:

- `backend/tests/test_customer_gamification_contract.py`

## Risk Notes

- All endpoints are public.
- Several write endpoints mutate loyalty points and workflow rows.
- Email verification uses a request-less workflow step with `shipment_request_id=0`.
- `leaderboard.total_customers` currently reflects the limited result count, not total verified customers.

## First Extraction Candidate

The lowest-risk first extraction is `GET /api/customer/leaderboard`.
