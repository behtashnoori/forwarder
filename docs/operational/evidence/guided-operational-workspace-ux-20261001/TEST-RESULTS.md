# Qualification Results

## Environment and boundary

- Governed repository baseline: LPAF v2.6, as required by repository `AGENTS.md`.
- Task-brief discrepancy: the supplied brief names LPAF v2.7; it was not treated as normative.
- Canonical product start: `96a9d52602febc6ab1b9d29e92e83fe3eb7e8dd5`.
- Product implementation commit: `501fcad9a646045c4f9df636188a2ed664682701`.
- Migration head: `20261015_org_shipment_stages`.
- Browser database: runner-owned PostgreSQL 18 cluster/database on loopback, migrated from base to exact head, seeded with synthetic fixtures, then stopped and removed.
- Preserved Human Walkthrough: not accessed or mutated.
- Production/deployment/release systems: not accessed.

## Automated evidence

| Gate | Result |
|---|---|
| Focused projection/workspace backend tests | 9 passed |
| Affected backend matrix | 196 passed |
| PostgreSQL-ordering correction regression | 38 passed |
| Governance/migration/browser-contract tests | 16 passed |
| Architecture governance script | PASS |
| Full frontend suite | 102 files, 483 tests passed |
| Final focused Shipment UI regression | 2 files, 35 tests passed |
| TypeScript `tsc --noEmit` | PASS |
| Production Vite build | PASS; only bundle-size and stale Browserslist advisories |
| ESLint | PASS with 0 errors and 16 pre-existing warnings |
| Disposable PostgreSQL + Chrome journeys | 9 passed |
| Disposable runtime cleanup | PASS |

## Browser journeys

The final Playwright run covered:

1. Expert Home operational priority and exception queue.
2. Shipment priority queue at desktop and 390 px mobile widths, including horizontal-overflow assertion.
3. Five-second Summary with semantic identity, process progress, task readiness, attention, location, ETA reason, and exactly one primary action.
4. Route/execution operate-first hierarchy.
5. Closure readiness without issuing a close command.
6. Organization Admin semantic IA and absence of Platform Governance for an organization-only admin.
7. Fixed Shipment owner and cross-tenant isolation.
8. Customer Account request/quote/recovery regressions.
9. Capability-only Public Tracking and anonymous intake regression.

Machine-readable result: `browser/result.json`.

## Evidence files

- `browser/guided-expert-home-priority.png`
- `browser/guided-shipment-priority-queue-desktop.png`
- `browser/guided-shipment-priority-queue-mobile.png`
- `browser/guided-shipment-five-second-summary.png`
- `browser/guided-closure-readiness.png`
- `browser/guided-admin-semantic-ia.png`
- `browser/workspace-overview.png`
- `browser/shipment-context-history.png`
- `browser/workspace-empty.png`

## Qualification interpretation

The authorized guided operational workspace slices meet their mission Definition of Done and preserve product semantics. However, two audit HIGH gaps remain outside or only partly inside this mission (UX-007 and UX-008). The truthful system-wide verdict is therefore partial, and the controlled-integration gate remains closed.

The repository-level known evidence state remains `Product validation = EVIDENCE_PENDING`; this mission evidence does not silently redefine that global status.

