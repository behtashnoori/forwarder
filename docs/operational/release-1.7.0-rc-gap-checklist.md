# Release 1.7.0 RC Gap Checklist

- **Release:** 1.7.0 — Logistics Network Foundation
- **Initial verdict:** NOT READY / HOLD
- **Closure verdict:** RELEASE 1.7.0 RC APPROVED FOR COMMIT
- **Finding source:** RC findings supplied with the bounded gap-closure request on 2026-08-03. No separate RC Validation Report artifact exists in the repository as of `bc46e3c`.
- **Scope authority:** [Release 1.7.0 Logistics Network Slice Contract](release-1.7.0-logistics-network-slice-contract.md)

This checklist was established before implementation changes. Every action below is validation, test, or documentation work for an already accepted Release 1.7.0 contract. It does not authorize new Logistics Network capability, Production access, deployment, packaging, tagging, seeding, staging, or committing.

| RC finding | Closure action | 1.7.0 scope confirmation | Planned evidence | Status |
| --- | --- | --- | --- | --- |
| PostgreSQL migration evidence missing | Exercise fresh upgrade, upgrade from `20260809_cargo_catalog_items`, downgrade, and re-upgrade on disposable PostgreSQL; verify one head and zero seed rows | Required by slice contract §10–11; validation only | Command/result record and database introspection | Closed |
| Geography handling uncertain | Compare service and database enforcement with the governed Country/optional Province/City contract | Existing data contract verification; no GIS or model redesign | ADR-026 and focused tests | Closed — `region_name` deferred |
| Duplicate constraints uncertain | Verify organization-scoped exact duplicate key and null-safe geography behavior | Existing duplicate contract only; no fuzzy search | PostgreSQL constraint checks and API tests | Closed for implemented geography |
| Index coverage uncertain | Inspect PostgreSQL indexes against contract access paths and active-sequence uniqueness | Existing physical contract only | Catalog/introspection record | Closed |
| Tenant isolation uncertain | Verify composite tenant FKs and organization-first service behavior | Required security acceptance; no authorization framework change | PostgreSQL FK inspection and negative API tests | Closed |
| OpenAPI contract incomplete | Complete schemas, errors, auth/authz descriptions, and existing filter/sort parameter descriptions | Documentation of existing APIs only | OpenAPI validation and contract tests | Closed |
| IDOR evidence incomplete | Add focused cross-tenant detail, update, lifecycle, association, and unauthenticated tests; compare non-disclosing responses | Explicit slice security acceptance | Focused backend test results | Closed |
| Frontend acceptance evidence incomplete | Add/execute tests for existing admin CRUD/lifecycle/duplicates and Project selection/role/sequence/lifecycle/no-free-text behavior; execute responsive browser checks | Existing UI behavior only; no redesign | Frontend tests and browser evidence | Closed — authenticated Chromium passed all exact viewports |
| Quote regression unclassified | Reconfirm `test_expired_quote_cannot_be_answered` and compare Release 1.7.0 source attribution | Release regression gate only; unrelated logic changes prohibited | Isolated/full results and baseline review | Closed — passes; exception not invoked |
| Release closure evidence missing | Produce RC Gap Closure Report and Acceptance Traceability Matrix | Required release evidence only | Two reviewed documents | Closed |

## Guardrails

- Disposable PostgreSQL only; never use or modify Production.
- No schema change unless a concrete accepted-contract violation is demonstrated.
- Any required design choice is documented explicitly before implementation.
- No GIS, reporting, dashboard, optimization, allocation, customer search, inventory relationship, workflow, seed, deploy, package, tag, push, stage, or commit action.
