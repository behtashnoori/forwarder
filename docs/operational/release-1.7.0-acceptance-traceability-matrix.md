# Release 1.7.0 Acceptance Traceability Matrix

| Requirement | Evidence | Test/document reference | Status |
| --- | --- | --- | --- |
| Migration parent and single head | Current/head `20260810_logistics_network`; pending=no | `backend/tests/test_logistics_network.py` and Final RC Review | Pass |
| Fresh PostgreSQL chain | Disposable PostgreSQL 18 migrated to head | RC Gap Closure Report | Pass |
| Geography contract | Required governed Country; optional governed Province/City; `region_name` deferred | ADR-026 | Pass |
| Duplicate constraints | Exact duplicate rejected; probable duplicate required explicit confirmation | Browser evidence and focused backend tests | Pass |
| Required indexes | PostgreSQL catalog evidence and corrected migration | `20260810_logistics_network.py` | Pass |
| Tenant isolation constraints | Composite tenant FKs and organization-first services | Focused backend and authenticated browser security checks | Pass |
| OpenAPI requests/responses/errors/auth | Parsed 18 operations; runtime/documented path sets equal 12/12 | `docs/openapi/openapi.yaml` | Pass |
| Cross-tenant detail/update/lifecycle/association | Seven API attempts return non-disclosing 404; browser foreign Project returns `Project not found` | `test_cross_tenant_and_unauthenticated_commands_are_non_disclosing`; Final RC Review | Pass |
| Admin Point Types | Authenticated list/create/update/immutable code/lifecycle at desktop; responsive evidence | Browser UAT evidence index | Pass |
| Admin Logistics Points | Authenticated list/search/create/update/governed geography/immutable code/duplicates/lifecycle | Browser UAT evidence index | Pass |
| Project Logistics Network | Existing point, role, sequence, label/notes, create, lifecycle/reactivation, canonical name | Browser UAT evidence index | Pass |
| Free-text master creation absent | Only governed existing-point selection is exposed | Browser DOM and frontend acceptance test | Pass |
| Mixed-state reorder | Active rows renumbered 1–5; inactive association preserved | Browser reorder screenshot and focused frontend test | Pass |
| No automatic operational graph | RoutePlan, OperationalCheckpoint, OperationalEvent counts remained zero | Disposable database introspection | Pass |
| Responsive browser behavior | Exact 1440×900, 390×844, 412×915; no overflow | Final RC Review browser matrix | Pass |
| Persian/English | Persian RTL authenticated flows and English LTR supported representative screen | Browser UAT evidence index | Pass |
| Accessibility | Named/labeled primary controls, native selects, keyboard-focusable actions; no blocker | Final RC Review | Pass |
| Backend regression | 5 focused; 546 passed/20 skipped full | Final RC Review | Pass |
| Frontend regression | 3 focused; 96 full; ESLint/build/TypeScript pass | Final RC Review | Pass |
| Cleanup | Servers stopped, disposable DB dropped, credentials deleted | Final RC Review | Pass |
| Quote regression classification | Isolated/full suite pass; exception not invoked | Baseline exception review | Pass |
