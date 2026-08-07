# MDPM-1 Candidate Evidence

- Candidate: `CAND-FWD-MDPM-1-001`
- Base: `b3a4340` (`codex/release-1.9-next-rc` evidence-custody tip)
- Candidate branch: `codex/mdpm-1-document-readiness`
- Decision IDs: MDPM-D01–MDPM-D15; ADR-030
- Migration: `20260813_mdpm_readiness` → `20260812_operational_execution`
- Migration SHA-256: `893E983364189BC2B16CF0BE06A7B96A1BFDF31F2BF8214B59048E8968B44459`
- OpenAPI SHA-256: `1B4795EFED6CEEA04261C01CF0690448A090EFEE28CB13B536AC4AC340B26764`

## Test evidence

| Gate | Result |
|---|---|
| Alembic heads | PASS — one head, `20260813_mdpm_readiness` |
| Fresh disposable PostgreSQL 18 explicit-runner upgrade | PASS |
| Empty MDPM downgrade to Release 1.9 parent | PASS |
| Re-upgrade/current check | PASS — head/current synchronized, pending=no |
| Disposable cluster stop | PASS |
| Backend full suite | PASS — 566 passed, 20 explicit environment skips |
| MDPM readiness/assessment/conditional/override tests | PASS |
| OpenAPI/runtime v2 path parity | PASS |
| Frontend full suite | PASS — 111 passed |
| Production frontend build | PASS |
| ESLint | PASS — zero errors; 12 pre-existing warnings |
| `git diff --check` | PASS |

## Security evidence

The service resolves organization membership before shipment/requirement/artifact identity, returns opaque MDPM/file identities, requires distinct read/manage/assess/verify/override permissions, restricts association to the shipment's source request and matching definition, rejects inactive/deleted/miscellaneous/mismatched versions, and never relies on frontend permission hiding. Negative cross-tenant and permission behavior continues through the existing `require_permission`/membership boundary. The full backend regression suite passed.

## Concurrency and idempotency evidence

Shipment and milestone expected versions are checked; transition, requirement, association, assessment projection, applicability, and override rows are locked in the transition transaction. Replacement, assessment, applicability, and override consumption are serialized against transition evaluation. Existing Release 1.9 transition semantics remain the mutation boundary. MDPM mutation endpoints use optimistic versions where aggregate state changes; the current slice does not add a new durable generic idempotency table.

## Browser/UAT evidence

Automated component UAT passed and validates that the UI renders server-returned blockers. A live authenticated browser UAT was not completed because no disposable seeded authenticated application stack was active after the PostgreSQL rehearsal, and creating a new reusable UAT identity/seed was outside the smallest safe closeout. No production or persistent environment was accessed.

## Known limitations

- One configured requirement binds to one milestone type/target status; multi-binding is deferred.
- Cross-request artifact reuse is not enabled; MDPM-1 allows only the shipment source request.
- Existing storage upload/replace remains in the request document UI; operational UI associates its opaque artifact ID rather than duplicating upload/storage.
- The minimal override UI asks for the target milestone opaque ID; the API validates the exact requirement/type/status relation.
- Live browser UAT and dedicated PostgreSQL race tests remain outstanding; automated policy, full backend, frontend, build, OpenAPI, and disposable migration gates passed.
- The stopped disposable data directory remains at `instance/mdpm_pg_rehearsal_20260807` because the execution safety layer rejected recursive cleanup. It contains only the task-created stopped disposable cluster and is not tracked by Git.

## Framework Delta

**PROJECT RESULT:** MDPM readiness remains a parallel deterministic projection and atomically constrains selected operational transitions.

**FRAMEWORK DELTA:** PATTERN CANDIDATE. No enterprise philosophy or standard is changed.
