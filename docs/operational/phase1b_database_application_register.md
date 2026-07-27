# Phase 1B Database Application Register

## Final application register (2026-07-27)

| Change group | Implemented | Disposable validated | UAT readiness | Browser/Mobile UAT | Persistent applied |
|---|---|---|---|---|---|
| Core Phase 1B | YES | YES | YES | YES | NO |
| Replan | YES | YES | YES | YES | NO |
| Timeline | YES | YES | YES | YES | NO |
| Exception | YES | YES | YES | YES | NO |
| UAT seed | YES | YES | YES | YES | NO |
| Runtime/config | YES | YES | YES | YES | NO |
| Phase 1B UI | YES | YES | YES | YES | NO |
| Shipment list dedup | YES | YES | YES | YES | NO |
| UAT DB-name contract | YES | YES | YES | YES | NO |
| Reporter permission alignment | YES | YES | YES | YES | NO |
| Milestone correction authorization | YES | YES | YES | YES | NO |
| Reporter semantic fixture selection | YES | YES | YES | YES | NO |
| Vite target precedence | YES | YES | YES | YES | NO |
| Operator UAT harness | YES | YES | YES | YES | NO |
| Browser runner route contract | YES | YES | YES | YES | NO |

Production/public PostgreSQL was untouched. The remaining register is historical chronology; its prior Browser/Mobile UAT values are superseded.

## Historical chronology

This control register does not authorize or apply a migration. Repository and runbook review found no conclusive, non-sensitive evidence that either Phase 1B revision was applied to a persistent target. Status: `MIGRATION_NOT_KNOWN_APPLIED_TO_PERSISTENT_ENVIRONMENT`.

| Change | Migration revision | Implemented | Disposable PG validated | Persistent target applied | Target environment | Applied at | Verification | Rollback evidence | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Multi-leg RoutePlan schema | `20260730_multileg_route` | YES | YES | NO | Not selected | — | Prior disposable PG18 gate | Populated fail-closed guard | Historical revision not rewritten |
| OperationalCheckpoint | `20260730_multileg_route` | YES | YES | NO | Not selected | — | Prior disposable PG18 gate | Populated fail-closed guard | — |
| CheckpointDependency | `20260730_multileg_route` | YES | YES | NO | Not selected | — | Prior disposable PG18 gate | Populated fail-closed guard | — |
| RouteException/work-item scope | `20260730_multileg_route` | YES | YES | NO | Not selected | — | Prior disposable PG18 gate | Populated fail-closed guard | Exception-backed work-item model |
| Scoped idempotency | `20260730_multileg_route` | YES | YES | NO | Not selected | — | Prior disposable PG18 gate | Populated fail-closed guard | — |
| RouteLeg projected timestamps | `20260730_multileg_route` | YES | YES | NO | Not selected | — | Prior delay gate | Populated fail-closed guard | — |
| Timeline reconciliation timestamp | `20260730_multileg_route` | YES | YES | NO | Not selected | — | Prior delay gate | Populated fail-closed guard | — |
| Trigger/constraint changes | `20260730_multileg_route` | YES | YES | NO | Not selected | — | Prior integrity gate | Populated fail-closed guard | Includes open uniqueness |
| Resolution source, occurrence count, reconciliation time | `20260801_route_exception` | YES | YES | NO | Not selected | — | PostgreSQL 18 exception lifecycle/concurrency gate | Transition-history fail-closed guard | Follow-up revision because application status of the historical revision is unproven |
| Idempotent reconciliation and manual-resolution response | `20260801_route_exception` | YES | YES | NO | Not selected | — | Focused replay/conflict tests and PostgreSQL 18 gate | Guard precedes removal | Public commands require a scoped idempotency key |

| Manual resolve / automatic reconciliation race | `20260801_route_exception` | YES | YES | NO | Not selected | — | Four direct PostgreSQL scenarios, 10 iterations each | Populated fail-closed guard | Barrier-based independent transactions; no persistent application |
| Replan / exception reconciliation race | `20260801_route_exception` | YES | YES | NO | Not selected | — | Direct PostgreSQL race, 10 iterations | Populated fail-closed guard | One active revision, no mixed-revision mutation or target exception clone |

## Safe downgrade validation

| Change | Implemented | Disposable PG validated | Safe downgrade validated | Persistent applied |
|---|---|---|---|---|
| Core Phase 1B schema | YES | YES | YES | NO |
| Multi-leg/replan | YES | YES | YES | NO |
| Timeline projected fields | YES | YES | YES | NO |
| Exception reconciliation | YES | YES | YES | NO |
| Migration `20260730_multileg_route` | YES | YES | YES | NO |
| Migration `20260801_route_exception` | YES | YES | YES | NO |

Safe-downgrade validation used only disposable PostgreSQL 18 databases. Downgrade-only guards in both Phase 1B revisions were tightened after direct evidence found uncovered lossy state. Because persistent application status is unknown, no upgrade schema was rewritten and no persistent target was touched.

Persistent application requires separate target approval, backup/restore readiness, official runner execution, post-migration schema/data verification, reconciliation, and an application smoke test.

## UAT readiness status

| Change group | Implemented | Disposable validated | UAT readiness | Browser/Mobile UAT | Persistent applied |
|---|---|---|---|---|---|
| Core Phase 1B | YES | YES | YES | NO | NO |
| Replan | YES | YES | YES | NO | NO |
| Timeline | YES | YES | YES | NO | NO |
| Exception | YES | YES | YES | NO | NO |
| UAT seed | YES | YES | YES | NO | NO |
| Localhost runtime | YES | YES | YES | NO | NO |
| Phase 1B UI | YES | YES | YES | NO | NO |
| Milestone correction authorization | YES | YES | YES | NO | NO |

Readiness validation used only token-scoped disposable PostgreSQL 18 databases
and localhost application processes. It did not apply a migration to any
persistent environment. Browser/Mobile UAT remains `NO` until its separate full
gate is executed.

Local SQLite runtime storage was externalized to the platform user-data
directory; no persistent schema migration was applied. Every `Persistent
applied` value remains `NO`.

## Direct PostgreSQL regression replay (2026-07-25)

| Evidence | Disposable validated | UAT readiness | Browser/Mobile UAT | Persistent applied |
|---|---|---|---|---|
| Direct PG regression replay: Phase 1A, Phase 1B, exception races, safe downgrade | YES | PENDING | NO | NO |
| Local backend/frontend smoke: fresh PG18, migration, seed, loopback stack, Chromium | YES | YES | NO | NO |

The replay used five isolated databases in a new token-scoped PostgreSQL 18.0
UTF8 cluster bound only to loopback. Results were 1, 1, 2, and 2 passed
respectively, with zero skips and failures. All current-token resources were
removed. This disposable validation did not authorize or perform persistent
migration application.

The final local smoke used a separate token-scoped PostgreSQL 18.0/UTF8 cluster
and real loopback-only backend/frontend processes. Chromium validated the Phase
1B shipment, multi-leg, timeline, exception, work-item, role-action, refresh,
and direct-reload surfaces with zero fatal console errors or unexpected 5xx and
production requests. Startup schema side effects and SQLite use were zero, and
cleanup left zero current-token resources. UAT readiness is therefore `YES`;
Browser/Mobile UAT and every persistent-applied value remain `NO`.

## Final full-UAT disposable admission run (2026-07-26)

Four fresh canonical PostgreSQL 18.0/UTF8 databases were migrated through the
official runner to `20260801_route_exception` and seeded through the official
Phase 1B UAT command. Shipment deduplication passed, while the Reporter and
correction-authorization prechecks failed before browser admission because the
Reporter report returned HTTP 409 rather than 200. These databases were
disposable only. No persistent target was selected or changed; persistent
applied remains `NO`.
