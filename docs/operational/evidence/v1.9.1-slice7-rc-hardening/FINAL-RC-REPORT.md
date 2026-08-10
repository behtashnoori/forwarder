# Forwarder v1.9.1 Slice 7 RC hardening

## Gate result

`SLICE 7 CLOSED — GO FOR SLICE 8 RELEASE PUBLICATION`

All evidence is synthetic/local. Production was not accessed. No push, tag,
package, release, deployment, merge, reset, clean, stash, rebase, or history
rewrite occurred.

## A–B. Initial state and baseline

- Branch: `codex/pr-4a-dms-gate-repair`.
- Baseline HEAD: `5b144f7f5032a44ef60fde1065bb1a3b24e8bfa6`.
- Upstream: none configured; ahead/behind is therefore not computable.
- Tracked tree: clean. Alembic sole head:
  `20260819_v191_acceptance_corrections`.
- Pre-existing untracked content was preserved. It comprised `.codex/`, prior
  evidence under `docs/operational/evidence/`, and historical local
  `release-v*` directories, including the detailed Slice 6.3 run artifacts.
- Release state supplied for this gate: Production 1.9.0; candidate 1.9.1.

## C–E. Integrated regression

- Backend: **PASS**, final full run 642 passed, 65 PostgreSQL-dependent skips,
  0 failures in 122.04s. The skipped coverage was run explicitly against
  disposable PostgreSQL below.
- Frontend: **PASS**, 24 files / 125 tests; TypeScript PASS; ESLint PASS with
  0 errors and 12 warnings; production build PASS (1,886 modules).
- Chromium: **PASS**, run `P1B-UAT-20260810204106522379`. Fresh private
  PostgreSQL/backend/Vite/Chromium covered direct/quote permissions, list/detail,
  route/deep-link navigation, EN/FA and RTL/LTR, canonical locations, documents,
  MDPM, economics/FX, OIP, retries/idempotency, stale conflicts, and release
  identity MATCH/MISMATCH/unavailable states.

## F–I. PostgreSQL, locks, recovery, backup/restore

- v1.9.0 (`20260818_immutable_fx_provenance`) to v1.9.1 migration: **PASS**.
- Synthetic counts before/after: shipment requests 2/2, quotes 2/2,
  operational shipments 2/2; both historical rows preserved and backfilled as
  accepted-quote. A direct row with nullable request/quote lineage then passed.
- Constraints/FKs/indexes/source shape/canonical columns: **PASS**, including
  invalid source, duplicate lineage, and missing customer rejection.
- Measured migration duration: 0.147612s. WAL growth: 48,064 bytes.
- Lock observation: granted AccessShare, RowShare, RowExclusive, Share,
  ShareRowExclusive, ShareUpdateExclusive, and AccessExclusive locks were
  sampled; no ungranted/blocking lock was observed. Because AccessExclusive
  locks occur, an approved write-quiescence window remains required despite the
  short synthetic-data duration.
- Recovery classification: **conditional downgrade plus forward/restore
  fallback**. Populated testing proved safe downgrade when no v1.9.1-only facts
  exist and fail-closed guards for direct rows and canonical international
  location data. Forward fix is preferred; coordinated restore is required
  when a guard refuses downgrade.
- Database backup/restore: **PASS**. Custom dump 584,028 bytes restored to a
  fresh database at the exact head; restored request/quote/shipment counts were
  2/2/3 (two accepted-quote plus one direct).
- Document storage: repository uses private filesystem storage. Synthetic
  archive 197 bytes restored with identical SHA-256: **PASS**. Production
  cutover must coordinate the PostgreSQL backup and document-root snapshot as
  one consistency boundary.

## J–N. Security, tenancy, contracts, version, runtime

- Current tracked/untracked tree and this evidence: **PASS**, redacted scanner
  findings 0. Credential-policy checks 5 passed; scanner parser tests 2 passed.
- Authentication, authorization, permission boundaries, cross-organization
  denial, document privacy, error sanitization: **PASS** in the full backend,
  explicit PostgreSQL, and Chromium runs.
- Tenancy matrix: **PASS** for customer/project/quote selectors, operation
  direct/quote creation and list/detail, documents, MDPM, economics, OIP,
  lifecycle, and release-support identity. Backend denial—not UI hiding—was
  exercised.
- Canonical repository API contracts/OpenAPI tests: **PASS**. Targeted contract,
  selector, OIP/OpenAPI, location, persistence, identity, startup, and security
  run: 72 passed.
- Version consistency: **PASS**. Frontend/package lock/backend/runbooks/verifiers
  agree on 1.9.1 and head `20260819_v191_acceptance_corrections`; historical
  1.9.0 references remain only where they describe Production/rollback history.
- Startup/runtime safety: **PASS**. Migrations remain explicit; startup does not
  seed Production; build is reproducible; release identity mismatch/backend
  unavailable/identity unavailable behavior passed Chromium.

## O–P. Clean rehearsal and runbooks

- Clean/disposable RC rehearsal: **PASS** through the full UAT harness with a
  private PostgreSQL cluster, explicit migration/approved synthetic seed,
  backend, Vite, and Chromium. No undocumented runtime dependency blocked it.
- Release/runbook review: **PASS** after correction. Deployment, migration,
  rollback/recovery, smoke, package verification, and server verification now
  describe v1.9.1, direct/accepted-quote sources, canonical locations, backup,
  conditional downgrade, restore fallback, cutover checks, and release identity.

## Q–S. Defects and remediation

No Category 1 defect remains. All Category 2 defects found were fixed:

1. TypeScript generic selector and stale source fixture prevented `tsc`.
2. Phase 1B PostgreSQL fixtures lacked the newly mandatory canonical customer.
3. FE-2 migration gate asserted the obsolete v1.9.0 head.
4. v1.9.1 replay orchestration pre-applied head instead of starting at baseline.
5. Secret scanner flagged intentional test/placeholder values.
6. Active runbooks and package/server verifiers still described v1.9.0.
7. Quote expiry used UTC date and failed at the local-calendar midnight boundary.

Category 3 notes: 6,384 backend deprecation/legacy warnings; 12 ESLint warnings;
stale Browserslist data; and a large frontend chunk warning. None failed the
release gates. They should be handled as bounded follow-up maintenance.

## T–Z. Evidence, cleanup, identity

- Evidence path: `docs/operational/evidence/v1.9.1-slice7-rc-hardening/`.
- Cleanup: **PASS**. UAT Chromium/backend/Vite/private PostgreSQL stopped,
  disposable databases dropped, and ports 55511/57151/5255 are closed.
- Production untouched: **CONFIRMED**.
- Commits created: none. Push/tag/package/deploy: none.
- Final HEAD remains `5b144f7f5032a44ef60fde1065bb1a3b24e8bfa6`;
  the RC remediation/evidence is an uncommitted working-tree change set.
- Final classification: `SLICE 7 CLOSED — GO FOR SLICE 8 RELEASE PUBLICATION`.
