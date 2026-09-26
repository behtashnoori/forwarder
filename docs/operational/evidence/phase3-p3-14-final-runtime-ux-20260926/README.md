# P3-14 — final runtime and UX integration

LPAF v2.7, governance level B. Product authority is recorded in
`docs/product/phase3/P3-14-15-MISSION-AUTHORITY.md`. The qualified Product SHA
is `c9347815746c25d3e943e1a00bc2d3cab87958ee`, based on the clean and aligned
Phase 3 P3-01..13 canonical entry
`835d46f7008bbc374168d1f5eba415b444574f7f`.

## Completed Product behavior

- The existing governed OIP Attention fact now carries one opaque,
  deterministic parity proof into both Workspace and Control Tower. The proof
  binds the same Shipment, situation, policy/version, rank and source
  watermark; its time is canonical UTC. It does not discover work, alter
  rank, or create a second source of truth.
- Organization Admin can reach the existing Customer Portal account-support
  workflow through normal Admin navigation. The page discards late obsolete
  list responses, so an initial load cannot overwrite a newer search.
- Operational Shipment Detail has a keyboard skip link, sticky section
  navigation, clearer current-milestone/freshness context, progressive
  disclosure and closure placement after the operational facts it evaluates.
- Customer Shipment Detail has a five-target, 44-pixel mobile section
  navigator and preserved tenant/Cargo-owner privacy.
- Recovery is exercised only through the authorized safe local delivery
  adapter. Real external email evidence remains a release-UAT requirement.

No schema, migration, attention-ranking rule, lifecycle, public tracking
capability, release, deployment or Production action was added.

## Exact-source qualification

| Gate | Final result |
| --- | --- |
| Complete backend | PASS — 1,561 passed, 121 environment-dependent skips, zero failures |
| Complete frontend | PASS — 447 passed in 94 files |
| PostgreSQL 18 Control Tower relational/count/query-bound proof | PASS — 1 passed; current head `20261012_phase3_cargo_eta` |
| Real Chrome | PASS — Expert parity/detail, Organization Admin support/recovery, and Customer 390px privacy/navigation; 3 passed |
| TypeScript | PASS — app and Node projects |
| ESLint | PASS — zero errors; 14 retained warnings |
| Production frontend build | PASS — advisory Browserslist/chunk warnings only |
| Architecture / structure / backend determinism / diff | PASS |
| Alembic | PASS — exactly one head, `20261012_phase3_cargo_eta` |

`final/result.json` binds the owned PostgreSQL and Chrome run to the clean
Product SHA with `dirty_source=false`, stopped processes, and no Production
access or mutation. `backend-full.log`, `frontend-full.log`, and `static/`
retain the other exact-source gate outputs.

An earlier intentionally retained `contended-attempt/` ran the performance
test concurrently with the complete backend and frontend suites. All logical
counts completed, but its first measured page took 35.894 seconds against the
30-second isolation threshold. It is not accepted as qualification. After the
parallel suites stopped, the unchanged Product SHA passed the isolated owned
PostgreSQL run and Chrome run in `final/`. No threshold or assertion was
weakened.

## P3-14 disposition

```text
LPAF_BASELINE=2.7
PHASE3_P3_14=PASS
FORWARDER_VISUAL_DNA_PRESERVED=PASS
RUNTIME_UX_INTEGRATION=PASS
SHIPMENT_DETAIL_INTEGRATION=PASS
WORKSPACE_SINGLE_TRUTH=PASS
CONTROL_TOWER_SINGLE_TRUTH=PASS
WORKSPACE_TOWER_PARITY=PASS
ATTENTION_RANKING_CHANGED=NO
ADMIN_NORMAL_NAVIGATION=PASS
FWD_DEC_02_STATUS=RESOLVED
CUSTOMER_NORMAL_NAVIGATION=PASS
CUSTOMER_MOBILE_UX=PASS
P3_14_MIGRATION_REQUIRED=NO
P3_14_PRODUCT_HEAD=c9347815746c25d3e943e1a00bc2d3cab87958ee
P3_14_EVIDENCE_HEAD=IDENTIFIED_BY_CONTROLLED_INTEGRATION_RECEIPT
P3_14_CANONICAL_INTEGRATION=PENDING
PHASE3_P3_15=NOT_STARTED
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
RELEASE_READY=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_MUTATED=NO
DEPLOYMENT_PERFORMED=NO
RELEASE_CREATED=NO
```
