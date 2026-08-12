# MT-1 final local certification

Date: 2026-08-12

Classification: **MT-1 LOCALLY CERTIFIED — SERVER CERTIFICATION REQUIRED**

## Repository identity

- Branch: `codex/pr-4a-dms-gate-repair`
- Initial HEAD: `0ede7a7b06b7d5d2aa6e4e8ab754991a0fae0bde`
- Alembic sole head: `20260824_mt1_graph`
- `v1.9.1^{}`: `05414d7d5b17153c3f1efcb5beff0adf7a600af6`
- Production, server DB, deployment, and push: not accessed or performed

## Test certification

The untouched backend baseline reproduced 672 passed, 79 skipped, one expected xfail, 17 failed, and 20 errors. The unexpected outcomes were 12 exact-head assertions stale at a predecessor, 23 case-document fixture outcomes without canonical tenant context, and two tracking/location fixture outcomes without canonical ownership.

After repair, the final complete backend suite produced 709 passed, 79 skipped, one expected xfail, zero failures, and zero errors. Skips are individually reported environment gates for disposable PostgreSQL suites. The xfail is the documented MT-3 characterization that public tracking still accepts numeric IDs; it is outside MT-1.

The focused local PostgreSQL 18 matrix produced 21 passed, zero skipped, zero xfailed, and zero failed. It covered ownership constraints, quarantine, census publication/fencing, full-surface reads and writes, case-document concurrency, shipment tracking, and tracking locations. The focused non-PostgreSQL MT-1 surfaces are included in the green repository suite.

## Repairs

- Twelve migration tests now assert exactly one head at `20260824_mt1_graph`; predecessor-chain assertions remain intact.
- SQLite and PostgreSQL case-document fixtures now create an actual Organization, active membership, TENANT-owned ShipmentRequest, and canonically owned descendants.
- SQLite and PostgreSQL tracking/location fixtures now use an actual Organization, membership, and TENANT-owned ShipmentRequest.
- MT-1C.1 and MT-1C.2 PostgreSQL certification fixtures now create valid tenant-owned business rows while preserving their census `CLEAR`, unsafe, and missing-metadata behavioral states.
- The MT-1D full-chain assertion now expects the current sole head.
- No product implementation or ownership enforcement was weakened. No real product defect was found or fixed.

## PostgreSQL migration certification

A loopback-only disposable PostgreSQL 18 cluster was used. A clean database upgraded through `20260824_mt1_graph`; it contained zero ShipmentRequest rows and zero fabricated Organizations. The final graph downgraded to `20260823_mt1_ownership_expand` and re-upgraded to `20260824_mt1_graph`. The 21-test PostgreSQL matrix verified raw-SQL rejection, same-tenant success, multi-parent/transport/document fences, quarantine and census behavior. Existing synthetic/provenance tests remain green; no synthetic data was assigned or altered.

## Static and security validation

- Python compilation: PASS (`compileall backend/tests`)
- Ruff: completed with repository-pre-existing style debt in compact legacy test files (`E701`, `E702`, and `E731`); the MT-1 changes add no new Ruff category and all functional/static gates pass
- JSON: PASS, 11 MT-1 architecture JSON files parsed
- CSV: PASS, no MT-1 CSV files present
- Alembic sole head: PASS
- `git diff --check`: PASS
- Secret scan: PASS after review. Scope: migrations, architecture docs, backend tests, and tracked environment examples. Matches were synthetic test passwords and the already-governed historical password hash; no live credential was found.
- PII scan: PASS. Changed lines contain only documented synthetic `09000000001/2` test values and `example.test` identities.

## Adversarial review

Cross-tenant documents/tracking/transport, ambiguous factories, hard-coded head divergence, quarantined NULL-owned reads, Activity/Task parent mismatch, re-parenting, intake, assignee-as-owner, raw-SQL cross-tenant inserts, synthetic exemption/provenance, and downgrade/re-upgrade were challenged by the combined repository and PostgreSQL suites. No bypass was observed.

**MT-1 FINAL LOCAL CERTIFICATION SECURITY REVIEW — PASS**

## Gates

| Gate | Result |
|---|---|
| RUNTIME_CANONICAL_TENANT_FENCING | PASS |
| QUARANTINE_RUNTIME | PASS |
| FULL_SURFACE_PROTECTION | PASS |
| LEGACY_DATA_PROVENANCE | PASS |
| SYNTHETIC_LEGACY_DISPOSITION | PASS |
| OWNERSHIP_MIGRATION | PASS |
| SAME_TENANT_CONSTRAINTS | PASS |
| APPLICATION_WRITE_ENFORCEMENT | PASS |
| TENANT_READ_ENFORCEMENT | PASS |
| INTAKE_ACCEPTANCE | PASS |
| REPARENTING_PROTECTION | PASS |
| LOCAL_TEST_CERTIFICATION | PASS |
| LOCAL_POSTGRESQL_CERTIFICATION | PASS |
| SERVER_MIGRATION_CERTIFICATION | PENDING_EXTERNAL |
| AUTHORITATIVE_CENSUS_SERVER_CERTIFICATION | PENDING_EXTERNAL |
| PRODUCTION_READINESS | PENDING_EXTERNAL |

## Remaining gates and next action

There are no known remaining local MT-1 gaps. On an authorized disposable server certification environment, run the same current-head migration and focused PostgreSQL matrix against a server data copy, verify the authoritative 135-row synthetic census remains NULL-owned/quarantined with no fabricated Organizations, and publish server evidence. Production readiness must not be declared until both external server gates pass.
