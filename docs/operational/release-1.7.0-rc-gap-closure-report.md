# Release 1.7.0 RC Gap Closure Report

- **Release:** 1.7.0 — Logistics Network Foundation
- **Date:** 2026-08-03
- **Final outcome:** **RELEASE 1.7.0 RC APPROVED FOR COMMIT**

## Closure summary

ADR-026 is Accepted. Disposable PostgreSQL migration evidence, composite tenant constraints, required indexes, exact-duplicate enforcement, OpenAPI completeness, IDOR behavior, and the mixed active/inactive reorder correction remain valid. Authenticated browser UAT now closes the sole remaining gate.

The UAT used a fresh loopback-only PostgreSQL 18 database and candidate version 1.7.0. The supported `manage.py create-admin` mechanism was verified; the temporary admin, memberships, and representative graph were created atomically through the direct test-only fixture pattern used by `backend/tests/test_logistics_network.py` and the current bcrypt hash service. Representative data covered two organization boundaries, an admin, expert, outsider, two Projects, four initial active point types, five Organization-A points (one inactive), and five Organization-A associations (one inactive). No Production reference-data Seed was applied.

## Authenticated browser evidence

- Desktop 1440×900 Persian: point-type list/create/update/immutable code/lifecycle and point list/search/create/update/immutable code/lifecycle passed.
- Duplicate handling: exact duplicate rejected; probable duplicate displayed an explicit confirmation action and succeeded only after confirmation.
- Project network: governed existing-point selection, bounded role, sequence, optional label/notes, create, deactivate/reactivate, canonical name, and no-free-text master creation passed.
- Mixed-state reorder: active order became INTERMEDIATE 1, ORIGIN 2, CUSTOMS_PROCESSING 3, DESTINATION 4, STORAGE 5; the inactive STORAGE association remained inactive and separately rendered.
- Mobile 390×844 Project and mobile 412×915 Admin representative screens had `scrollWidth == clientWidth`.
- Persian RTL and English LTR representative screens rendered without horizontal overflow or console errors.
- Primary controls had accessible names; labeled native selects/inputs and keyboard-focusable buttons/dialog actions were observed.
- Security: foreign point absent, foreign Project direct navigation non-disclosing, non-admin `/admin` access redirected.
- RoutePlan, OperationalCheckpoint, and OperationalEvent row counts remained zero.

See [browser UAT evidence index](evidence/release-1.7.0-browser-uat/index.md).

## Regression and cleanup

Focused backend: 5 passed. Full backend: 546 passed, 20 skipped. Focused frontend: 3 passed. Full frontend: 96 passed. ESLint: zero errors/12 existing warnings. Production build passed. TypeScript emitted zero diagnostics. OpenAPI parsed to 18 operations with exact 12/12 runtime path parity. Migration current/head was `20260810_logistics_network`, pending=no. `git diff --check` passed and the current-tree secret scan reported zero findings.

The browser session and local servers were closed, the disposable database was dropped, and temporary credentials/runtime files were removed. Production was not accessed or changed.

## Recommendation

Stage the bounded RC closure files and commit with `fix(logistics-network): close release 1.7.0 rc gaps`. Do not push, tag, package, deploy, run a Production migration, or apply Production Seed.
