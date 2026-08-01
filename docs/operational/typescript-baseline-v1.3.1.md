# TypeScript Differential Baseline — Forwarder 1.3.1

- **Release:** 1.3.1 — Central Route Scroll Restoration
- **Comparison date:** 2026-08-01
- **Exact command:** `npx tsc -b --pretty false --force`
- **Baseline:** annotated tag `v1.3.0`, commit `a9879515aad25ef332ff8087062388851d7b3435`, checked out in an isolated detached worktree
- **Candidate:** commit `a9879515aad25ef332ff8087062388851d7b3435` plus the uncommitted Central Route Scroll Restoration working-tree changes

## Normalization and comparison

Primary diagnostics were normalized as `file path | line | column | TypeScript error code | message`. A second comparison ignored line and column while retaining file, code, and message so that diagnostics changed only by shifted source lines could be classified separately.

| Classification | Count |
| --- | ---: |
| Baseline errors | 79 |
| Candidate errors | 79 |
| Pre-existing errors | 79 |
| Removed errors | 0 |
| New errors | 0 |
| Changed errors | 0 |
| Changed only by shifted lines | 0 |

No diagnostic occurs in `src/App.tsx`, `src/components/RouteScrollManager.tsx`, or `src/tests/components/RouteScrollManager.test.tsx`. No existing error became more severe.

## Files containing pre-existing debt

- `src/components/AdvancedSearch.tsx`
- `src/components/DocumentDefinitionsTab.tsx`
- `src/components/LocationsAdminTab.tsx`
- `src/i18n.tsx`
- `src/lib/api.ts`
- `src/pages/PublicTracking.tsx`
- `src/pages/RequestDetail.tsx`
- `src/tests/components/CaseDocumentsTab.test.tsx`
- `src/tests/components/DocumentDefinitionsTab.test.tsx`
- `src/tests/components/LoadingSpinner.test.tsx`
- `src/tests/pages/CommandCenter.test.tsx`
- `src/tests/pages/CRMDashboard.test.tsx`
- `src/tests/pages/ExecutionUnitPages.test.tsx`
- `src/tests/pages/OperationalPages.test.tsx`
- `src/tests/pages/OperationalShipmentDetail.behavior.test.tsx`

## Conclusion and expiry

The 1.3.1 Scroll patch introduces zero new TypeScript errors and does not alter the repository's existing diagnostics. The patch therefore satisfies the differential TypeScript gate.

This exception applies only to Release 1.3.1. It is release evidence, not a permanent waiver of repository-wide TypeScript debt, and expires when the 1.3.1 closure decision is complete.
