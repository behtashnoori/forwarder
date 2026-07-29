# Time Architecture Implementation Roadmap

No phase below authorizes production migration merely by appearing here.

| Phase | Prerequisites | Likely modules | Migration | Main risks | Required tests | Rollback | Dependencies |
| -- | -- | -- | -- | -- | -- | -- | -- |
| 1 — Session Continuity | Existing AuthSession and protected routes | `backend/security.py`, `backend/services/auth_session_service.py`, `src/lib/api.ts`, protected routing/login | None | refresh replay/loops, unsafe redirect, lost unsubmitted input | access expiry, concurrent 401, refresh failure, reauth return, logout/revocation and long-running Shipment regression | revert client/session-policy code; existing DB records remain compatible | TIME-BIZ-012 and Shipment invariant |
| 2 — SLA | Current Tehran work schedule; calendar owner, Holiday Provider, and reason taxonomy remain Roadmap work | assignment service and SLA service; calendar/policy ownership, persisted policy version/start history, and formal transfer recalculation/audit are future work | Current increment stores expert duration and request deadline only; policy version and SLA start history are not persisted | incorrect deadlines and reassignment reset | timezone boundaries, injected holidays, outside-hours pause, reassignment preservation; formal transfer audit remains future work | revert SLA calculation wiring while retaining additive values | TIME-BIZ-001/002 |
| 3 — Tracking Time Provenance | Canonical Location timezone and external contract | tracking service/routes/models, Location master | Yes, additive `occurred_at`, `recorded_at`, source, zone and audit | false historical interpretation, double UTC conversion | offset contract, missing Location, override permission, ordering | dual-write off; retain legacy fields | TIME-BIZ-007/011 |
| 4 — Quote and CRM | Resolve TIME-BIZ-006 ownership | quote/CRM models, services, forms and reminders | Yes, additive response/due/zone snapshot fields | changed expiry or reminders | local-day boundary, fallback zone, reassignment preserves Instant | feature flags and read fallback | TIME-BIZ-003–006 |
| 5 — Operational Planning | Canonical timezone-bearing Locations | operational route-leg models/services/UI | Yes, additive IANA snapshot fields | DST ambiguity, origin/destination mix-up | gap/overlap, leg duration, checkpoint zone, override audit | read legacy UTC values; disable new writes | TIME-BIZ-008/009 |
| 6 — Reporting | Stable zone contracts from earlier phases | admin reports, exports, cache keys, reporting APIs | Usually no data backfill; contract change | inconsistent “today”, cache contamination | each report basis, `[start,end)`, metadata and export parity | API version/feature flag | TIME-BIZ-010 and phases 2–5 |
| 7 — Historical Migration | Clone, per-column evidence, approved mappings and rollback rehearsal | Alembic migrations, reconciliation scripts, observability | Yes, controlled backfill | irreversible time shifts and silent corruption | sampled provenance, before/after totals, ambiguous quarantine, restore drill | database snapshot and rehearsed downgrade/restore | all preceding contracts |

## Phase 1 completion and residual work

Implemented: configurable access/idle/absolute/skew policy, server-side rotation,
single-flight client refresh, one retry, safe internal route restoration, and
regression coverage for the absolute ceiling.

Draft recovery was not implemented. A follow-up should inventory the Tracking
Update, Shipment Request, Quote, Operational Planning, and CRM Activity forms;
classify sensitive fields; then use a scoped encrypted/server draft or approved
session storage keyed by user and Shipment with TTL and successful-submit
cleanup. This must not become a general localStorage dump.
