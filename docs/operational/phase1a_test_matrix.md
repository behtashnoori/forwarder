# Phase 1A test matrix

| Gate | Coverage |
|---|---|
| Service/API | creation, idempotency, transitions, versions, permissions, isolation, envelopes/statuses |
| PostgreSQL | migration, constraints, append-only, concurrency, partial uniqueness |
| Runtime | no startup migration/seed; read-only probes |
| Frontend | loading/data/filters, duplicate submit, detail/timeline, queue/resolve, accessibility |
| Security | current/tracked/untracked scans and scanner/setup regressions |
| Browser | real login, flow, isolation, permissions, conflict, 360/390/768 layouts |

## Closure results — `P1A-UAT-20260723125334`

| Gate | Result |
|---|---|
| Backend targeted regression | 8 passed |
| Frontend behavioral regression | 10 passed |
| Frontend lint | 0 errors, 12 warnings |
| Frontend build | PASS |
| Browser desktop | 20 scenarios complete across accepted desktop and closure runs |
| Mobile 360/390/768 | PASS; exact viewport, media-query, PNG, overflow and interaction evidence |
| UAT-20 unavailable/retry | PASS; owned process stop, bounded error, health recovery and in-page Retry |
| Cleanup | PASS; zero Phase 1A temp resources |

Final closure regression: frontend 10 passed; lint 0 errors and 12 warnings;
build PASS; backend targeted 8 passed; backend full 318 passed and 7 expected
feature-specific PostgreSQL skips. Earlier unverified Browser completion and
screenshot claims are superseded.
