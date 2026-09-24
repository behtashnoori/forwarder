# Operational Workspace Phase 2 qualification evidence

Date: 2026-09-24

Branch: `codex/operational-workspace-phase-2`

Target baseline: `integration/golden-controlled` at `97edd38d752259f0babcf8f43867b028511c874d`

Migration head: `20260928_operational_workspace_phase2`

## Scope and safety

- Qualification used synthetic data in owned disposable local/UAT databases only.
- PostgreSQL 18 was the database engine for clean upgrade, downgrade/upgrade, and browser qualification.
- No production system was accessed or mutated and no deployment was performed.
- The repository-wide LPAF product-validation state remains `EVIDENCE_PENDING`; evidence for this bounded slice is complete.

## Migration evidence

- Clean PostgreSQL upgrade from base to the sole repository head: PASS.
- Exact database-head verification: PASS.
- Phase 2 downgrade to `20260927_customer_portal_account_lifecycle`: PASS.
- Re-upgrade to `20260928_operational_workspace_phase2`: PASS.
- Migration-specific automated tests, including pre-existing Action-row downgrade handling: 2 PASS.

## Browser product evidence

Command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-operational-workspace-phase2-e2e.ps1
```

Result: 8/8 journeys PASS in Google Chrome via Playwright against PostgreSQL 18. The runner created random credentials and an owned database, verified the exact Alembic head, then removed every server process and runtime database it created.

Covered journeys:

1. Organization Admin creates the missing Action SLA, versions the Exception SLA prospectively, and views audit history.
2. Non-admin/cross-tenant access to SLA management is denied.
3. Healthy, warning, and breached commitments are evaluated; the healthy commitment creates no false SLA-risk Attention.
4. Expert records Exception impact and evidence in the shipment workspace.
5. The new Exception becomes immediately selectable as Action context without a page reload.
6. Expert creates a fixed-owner Action, records a follow-up, records a mandatory result, resolves it, and sees preserved history; Exception resolution remains independent.
7. Workspace shows traceable and explainable Action/SLA Attention.
8. The live Control Tower response contains both `action_follow_up` and `sla_breach`, and the exact response is rendered as an actionable Control Tower card.
9. Phase 1 fixed-owner, tenant-isolation, empty/error, Customer Account, Public Tracking, and anonymous-request journeys remain green.

Artifacts:

- [SLA administration](browser/phase2-sla-administration.png)
- [Workspace SLA and Attention](browser/phase2-workspace-sla-attention.png)
- [Exception, Action, resolution, and history](browser/phase2-exception-action-history.png)
- [Control Tower](browser/phase2-control-tower.png)
- [Machine-readable browser result](browser/result.json)

## Automated qualification

- Full frontend: 78 files, 381 tests PASS.
- Focused Phase 2 backend and OIP compatibility: 5 tests PASS.
- Focused migration tests: 2 tests PASS.
- TypeScript project build: PASS.
- ESLint (`--quiet`): PASS.
- Production frontend build: PASS; the existing large-chunk advisory remains non-blocking.
- Repository structure check: PASS.
- `git diff --check`: PASS.
- Full backend regression: 1,369 passed, 106 skipped.

## Reference impact

`REFERENCE_IMPACT=UPDATE_REQUIRED`: the OpenAPI contract, tenant-ownership inventory, ADR index, Phase 1 browser harness compatibility, and migration-head assertions were updated for the new bounded capabilities.
