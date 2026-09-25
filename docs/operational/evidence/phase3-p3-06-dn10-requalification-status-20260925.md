# P3-06 — DN10 requalified; controlled canonical integration authorized

Date: 2026-09-25. LPAF v2.7; rigor C; capability need Astra, without claiming a
runtime model setting. Authority: [five-stage Product Owner mission](../../product/phase3/P3-06-10-MISSION-AUTHORITY.md),
DN10 §§3–16 and [ADR-062](../adr/ADR-062-explicit-customer-entitlement.md).

- Product SHA: `0e65fd89882e23453d7c3bfe4d520cd7f44a6c32`.
- Canonical base: `bd3610c4016cf643b6243fb0490260ac49a8b92d`.
- Evidence SHA: this evidence-only descendant, identified by the integration receipt.
- Branch: `codex/phase3-p3-06-contextual-documents`.
- One Alembic head: `20261006_customer_entitlement` →
  `20261005_phase3_contextual_documents` → `20261004_phase3_cargo_allocation_trace`.
- Original P3-06 migration and all historical canonical migrations are unchanged.

## Result and behavior

`P3_06_QUALIFICATION=PASS`. The earlier blocked candidate/evidence remains
historical and is not reused as the qualification of this changed runtime.
This record authorizes the already-requested controlled fast-forward from the
verified canonical base, followed by github push/fetch and clean 0/0 verification.
The exact evidence/canonical commit identities and remote alignment are recorded
by the integration receipt and the next mission entry/final delivery record;
no self-referential commit SHA is invented here.

Portal Account and CRM Customer remain separate. An active same-organization
Admin alone manages explicit many-to-many grants. Names, email, telephone,
Request pairing and Cargo ownership alone confer no Portal access. Each grant
and revocation retains actor/time; regrant creates a new fact. Account locking,
unique current relationships and command keys serialize commands. An old grant
replay cannot reactivate access and an old revoke cannot revoke a later grant.

The Customer query rechecks the live grant, active principal/organization/CRM,
actual own Cargo, typed context, permitted visibility and exact active file
version before rows, pagination and download. Responses are no-store. Browser
back/focus/reopen clears and reloads the view. Independent explicit non-Cargo
sharing keeps its separate policy. Replacement preserves history and starts its
new exact version INTERNAL; access to that version must be set separately.
Org Admin and Customer gain no operational document management authority.

## Exact-Product evidence

Recoverable logs, results, source/build identities, screenshots and SHA-256
manifest are in [the evidence bundle](phase3-p3-06-dn10-20260925/qualification.json).

| Gate | Result |
| --- | --- |
| Full backend | PASS: 1,416 passed, 114 skipped, 0 failed; 967.46 seconds. Skips remain explicit environment-dependent exclusions. Required PostgreSQL proofs ran separately. |
| Full frontend | PASS: 86 files / 408 tests; 243.82 seconds. |
| PostgreSQL 18 DN10/context | PASS: 2 tests; legacy no-backfill, empty downgrade/re-upgrade, populated rollback refusal, same-tenant constraints, concurrent grant/revoke and replay. |
| PostgreSQL P3-01..05 | PASS: 5 separate migration/runtime regression tests. |
| Normal Chrome P3-06/DN10 | PASS: upload/reopen, Admin grant, Customer A own-Cargo exact byte download, Customer B denial, revoke, mobile back/reopen and direct-link denial, history and replacement. |
| Adjacent Chrome | PASS: P3-05, P3-04, P3-03, P3-02 and P3-01 on this Product runtime and current schema. |
| Visual inspection | PASS: readable Admin navigation and Customer mobile 390×844 layout; retained screenshots. |
| TypeScript / ESLint / production frontend build | PASS; 0 lint errors, 13 existing warnings; existing build chunk-size advisory. |
| OpenAPI route parity / tenant inventory / architecture / structure / determinism / diff | PASS. |
| Changed-scope secret scan | PASS: 71 changed files, no findings; no secret values printed. |

All final runs used the frozen Product and owned synthetic data. Environment:
Python 3.13.9, Node 24.11.0, PostgreSQL 18.0, Chrome 154.0.8037.57.
There was no Production access, data/secret use, migration, deployment or release.

Diagnostic attempts are retained externally and do not count as final PASS.
An initial frontend run was interrupted; another had five timing failures under
load, followed by 27/27 isolated passes and successful fresh full runs. The first
full backend had 26 obsolete repository-head assertions; updating their expected
head retained single-head and historical ancestry checks. This Product contains
that correction and its fresh full backend run passed. No failure was waived.

## References, journeys and limits

Current architecture/ADR/decision indexes, tenant inventory, OpenAPI, document
contract and Phase 3 mission references are reconciled. Historical ADR bodies,
PDRs and prior evidence are unchanged.

`REFERENCE_RECONCILIATION=PASS`; `REFERENCE_IMPACT=NONE` within this slice.
`DN10_STATUS=RESOLVED`; `DN10_EXPLICIT_ENTITLEMENT=PASS`;
`DN10_AUTO_LINK=NO`; `DN10_ORG_ADMIN_MANAGED=PASS`;
`DN10_REVOCATION=PASS`; `CUSTOMER_OWN_CARGO_DOCUMENT_ACCESS=PASS`.
`DN02_DOCUMENT_VISIBILITY_STATUS=RESOLVED_FOR_P3_06`;
`DN02_OWNER_TRANSFER_PORTION=OPEN_FOR_P3_13`; `DN09_STATUS=OPEN`.

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`:
FWD-J02, FWD-J04, FWD-J08, FWD-J09, FWD-IPJ-03, FWD-IPJ-04.
These are slice-boundary proofs. `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`;
`INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN`; `HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN`;
`RELEASE_READY=NO`. P3-07..10 implementation has not started at this record;
their next starts remain dependency-gated. P3-11..15 are excluded.

## Cleanup

Final owned backend/frontend children and PostgreSQL clusters stopped; their
temporary directories are confirmed absent. Candidate/canonical clean state is
rechecked after this evidence commit and at integration.

Automatic host approval rejected deletion of the already-stopped development
directory `C:/Users/pc/AppData/Local/Temp/forwarder-dn10-owned-2210e7c9f66f43d3a8e0de226b0e26f1`
with reason `blocked by policy`. A later read-only `pg_ctl status` confirmed no
server running. That directory remains; no bypass or alternative deletion was attempted.
