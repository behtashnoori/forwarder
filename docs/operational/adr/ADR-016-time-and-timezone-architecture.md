# ADR-016: Time, Timezone, and Session Continuity Architecture

## Status

Accepted. Business-policy implementation remains phased according to the
[decision register](../../architecture/time/time-business-decision-register.md)
and [implementation roadmap](../../architecture/time/time-implementation-roadmap.md).

## Core decisions

- Real events are UTC Instants in the backend and RFC 3339 values with `Z` or
  explicit offset at API boundaries.
- Local Dates such as `pickup_date`, `delivery_date`, and `valid_until` remain
  dates and are never converted through UTC midnight.
- Business local date-times require a wall-clock value, IANA timezone,
  business/Location owner, and explicit resolution to a UTC Instant.
- `occurred_at` and `recorded_at` are distinct Instants.
- Reporting-day boundaries are half-open `[start, end)` ranges in an explicitly
  selected business timezone.
- Legacy naive timestamps remain uninterpreted until each column has a proven
  source contract and a reversible migration plan.

## Session and Shipment invariant

```text
Shipment lifecycle is independent from authentication session lifecycle.
```

A Shipment is durable workflow state in the database. It is not owned by a
JWT, refresh token, browser tab, HTTP connection, or login session. Access or
refresh expiry, logout, revocation, browser closure, and reauthentication:

- do not cancel, close, expire, delete, roll back, or change Shipment status;
- do not remove committed timeline, document, event, or workflow data;
- may only interrupt the user's authorization to access that state;
- must allow an authorized user to return to the same internal Shipment route;
- must not terminate backend work because a browser connection disappeared.

The target authentication policy is a configurable 1-hour access token,
30-day idle refresh window, 90-day absolute login-session ceiling, and
60-second verification skew. The 90-day ceiling applies only to login.
Shipments may remain active for weeks or months and continue after login.

## Migration safety

No broad timestamp migration or historical backfill is part of Session
Continuity. Each future migration needs column-specific semantics, clone
testing, reconciliation, rollback rehearsal, and explicit production approval.

## Consequences

Authentication can expire safely without changing business state. The client
uses controlled single-flight refresh and a safe internal return path. Draft
recovery for unsubmitted sensitive forms is a separate bounded design item;
committed data already remains server-side.
