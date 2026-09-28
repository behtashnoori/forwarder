# Shipment owner authorization hardening — final evidence

Date: 2026-09-28
LPAF baseline: 2.7
Product SHA: `8b83247c3a00433db60cc858c244199274034eb6`
Branch: `codex/human-walkthrough-shipment-owner-auth-hardening`

## Result

`PASS — SHIPMENT OWNER AUTHORIZATION HARDENING QUALIFIED`

The exact Product SHA above was qualified in an owned disposable local/UAT
PostgreSQL 18 environment and real Chrome. No Production system was accessed or
mutated, no deployment was performed, and no release was created.

The consolidated machine-readable run is preserved outside the repository at:

`D:\1-webapp\forwarder-dev\human-walkthrough-shipment-owner-auth-hardening-evidence-20260928-r2\result.json`

SHA-256:
`B6D238699323BAC0F31FE7EC0E8C6E3C902269BF92FE442C702F507105F855AC`

## Root cause and bounded repair

- The existing walkthrough Shipment persisted the correct current owner.
- Shipment summary and command authorization both resolve that same persisted
  owner user identity; no user-id/membership-id mismatch exists.
- The standard active Expert baseline included `execution_unit.create` and
  `execution_unit.update` but omitted the prerequisite
  `execution_unit.read` capability used by both Route/Execution panel reads.
- Those reads failed before the current-owner predicate ran. The UI's generic
  403 mapping therefore displayed an owner-denial sentence even though owner
  identity was correct.
- The bounded Product repair adds `execution_unit.read` to the standard active
  Expert baseline. Shipment ownership, Request assignment, tenant fencing,
  non-owner denial, Admin boundaries and P3-13 transfer semantics are unchanged.
- Existing active Expert memberships are repaired only through the existing
  additive, idempotent governed reconciliation command. No raw business-record
  update, owner transfer, Shipment recreation, history rewrite or migration is
  required.

## Qualification summary

- Focused authorization, execution, allocation, transfer and operational
  vertical-slice tests: 60 passed.
- Full backend regression: 1,576 passed, 121 classified skips, 0 failures.
- Full frontend regression: 99 files and 472 tests passed.
- TypeScript: PASS.
- ESLint: PASS with zero errors and 14 retained advisory warnings.
- Production-mode frontend build: PASS; 2,584 modules transformed.
- OpenAPI YAML parse: PASS.
- Architecture governance, structure, backend determinism and Python compile:
  PASS.
- Current-tree secret scan: PASS, zero findings. Reachable-history scan retained
  the same 46 redacted historical findings; this Product commit introduces no
  secret finding.
- PostgreSQL 18 base-to-head migration chain: PASS.
- Phase 3 PostgreSQL 18 suite: 15 passed.
- Public Tracking PostgreSQL regression: 1 passed.
- P301 through P314, MT3, IPJ01, IPJ02/IPJ03, Phase 2, monitoring,
  P315-CORE, HW-COMMERCIAL and IPJ04 real-Chrome journeys: PASS.
- Alembic head: `20261012_phase3_cargo_eta`; head count: 1.
- Migration required for this change: NO.

## Evidence file hashes

- `postgresql-phase3.log`:
  `49E5F1F24DB75292758E7BE3E0CF59AD63E8E9A5BFDC45AC12F4296F29351EDE`
- `public-tracking-postgresql.log`:
  `9C961CAD9416849BD4C7F6BBEA8F050B6A588D0FCAB9D704C207715E82FEA675`
- `P304/browser.log`:
  `61AAFA2DF7F507C94A68F22B654F103C2470563AFA7E141394B90695CF07B846`
- `P313/browser.log`:
  `E6C6151200AE2AE5A9DAE18B5ED8999DEC34B1B4DFF103D210ECC1DA8A105CF8`
- `IPJ04/browser.log`:
  `DCB5A053B6626077E127DEAE514E9EA27DFE95F9CC6DF8A26406054B976EFE2E`

The first attempted consolidated run stopped safely at P301 because the
isolated worktree could not resolve its installed Playwright dependency.
PostgreSQL migration, Phase 3 and Public Tracking had passed in that diagnostic
run. Dependency resolution was corrected without a source change; the accepted
run above then started from a fresh owned PostgreSQL runtime and passed every
gate. Only the `-r2` directory is candidate evidence.

## Walkthrough and release boundary

This evidence qualifies the Product candidate for controlled integration. It
does not self-pass the Human Product Walkthrough. After integration, the same
preserved walkthrough database and Shipment must be reopened read-only first,
the governed Expert-baseline reconciliation applied if needed, and the
Route/Execution form availability verified without creating or revising an
execution on behalf of the Product Owner.

```text
HW_SHIPMENT_AUTH_001=QUALIFIED_FOR_INTEGRATION
SHIPMENT_OWNER_READ_WRITE_PARITY=PASS
P3_04_TRANSPORT_EXECUTION_REGRESSION=PASS
P3_05_ALLOCATION_REGRESSION=PASS
P3_13_OWNER_GUARD_PRESERVED=PASS
REQUEST_TO_SHIPMENT_OWNER_SEMANTICS=PASS
DIRECT_SHIPMENT_OWNER_SEMANTICS=PASS
MIGRATION_REQUIRED=NO
ALEMBIC_HEAD=20261012_phase3_cargo_eta
ALEMBIC_HEAD_COUNT=1
FULL_BACKEND_REGRESSION=PASS
FULL_FRONTEND_REGRESSION=PASS
SLICE_JOURNEYS=PASS
INTEGRATED_PRODUCT_JOURNEYS=PASS
AUTOMATED_PRODUCT_JOURNEYS=PASS
PRODUCT_SHA=8b83247c3a00433db60cc858c244199274034eb6
HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS
RELEASE_READY=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_MUTATED=NO
DEPLOYMENT_PERFORMED=NO
RELEASE_CREATED=NO
```
