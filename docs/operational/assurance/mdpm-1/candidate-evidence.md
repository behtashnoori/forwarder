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

## Final validation gate — 2026-08-07

- Environment: disposable PostgreSQL 18 cluster `instance/mdpm_validation_20260807_2215/pgdata`, loopback `127.0.0.1:55449`, database `forwarder_phase1b_uat_mdpm_20260807_2215`. The retained cluster was restarted on `55449` because the host denied rebinding its former `55439` socket.
- Seed lineage: `phase1b_uat + mdpm_validation_seed:v1`; synthetic organization A, authenticated admin/no-permission users, Project `MDPM-UAT`, shipment, `MDPM_GATE` milestone, three requirements, and six synthetic artifact versions. The retrievable identity manifest is `instance/mdpm_validation_20260807_2215/seed-lineage.json`.
- Migration: current/head `20260813_mdpm_readiness`, pending `no`; SHA-256 unchanged at `893E983364189BC2B16CF0BE06A7B96A1BFDF31F2BF8214B59048E8968B44459`.
- Authenticated browser/API UAT: server-derived blockers passed for missing, unapproved, approval-insufficient-for-verification, replacement, rejection, and conditional `UNRESOLVED`/`NOT_APPLICABLE`; approved + verified + not-applicable became ready; exact scoped override made the rejected requirement ready; no-permission override returned 403. Evidence is retained in `instance/mdpm_validation_20260807_2215/browser-api-evidence.json` and `unauthorized-override-evidence.json`.
- Browser UI: Persian RTL rendered and the English switch was present; MDPM projections showed opaque UUID identities only. The final live page showed the replacement artifact as `REJECTED`, the verification artifact as `VERIFIED`, the conditional requirement as `NOT_APPLICABLE`, and readiness as `Ready for READY` under the exact override.
- Browser mutation rerun: PASS for association/replacement, assessment/rejection, stale-version surfacing, exact controlled override, and transition consumption through real authenticated UI controls after replacing unsupported prompts with explicit fields. Runtime direction checks passed for Persian RTL and English LTR; console errors were zero. Evidence is retained under `docs/operational/assurance/mdpm-1/browser-uat-20260807/`.
- Browser limitation: the pre-existing Release 1.9 shipment-detail route still exposes its legacy numeric shipment identifier (`/operations/shipments/1`). MDPM APIs and controls use only opaque UUID identities, but the containing route prevents an unqualified pass for the full "no visible numeric internal IDs" UI contract.
- PostgreSQL concurrency/race suite: PASS — `13 passed` on PostgreSQL 18 using per-test cloned databases and real transactions/locks. All thirteen required scenarios, idempotency outcomes, and organization isolation are covered in `backend/tests/test_mdpm_races_postgresql.py`; summary evidence is `postgresql-races-20260807.md`.
- Regression after bounded fixes: focused MDPM/Release 1.9/OpenAPI tests `11 passed`; full backend `566 passed, 33 skipped`; frontend `111 passed`; production build passed; lint passed with zero errors and 12 existing warnings; migration current/head synchronized with pending=no; `git diff --check` passed.
- Migration SHA-256 remains `893E983364189BC2B16CF0BE06A7B96A1BFDF31F2BF8214B59048E8968B44459`; current OpenAPI SHA-256 is `CF063631981B8F367CE340454BBF212958A6080407A34F452C9AC71E426C4430`.
- Candidate identity remains the mutable branch tip `09aee0c015cb9a2b2016877602d9195a3339b720`; no immutable candidate was created because the legacy numeric containing-route limitation prevents the complete Browser UAT contract from passing.
- Promotion decision: **MDPM-1 VALIDATED WITH EXPLICIT LIMITATIONS**.

## Opaque shipment route final promotion gate — 2026-08-07

- Defect: canonical operational navigation used internal `OperationalShipment.id`, exposing `/operations/shipments/1`.
- Remediation identity: existing `OperationalShipment.public_id`; no schema, migration, aggregate identity, or MDPM domain change.
- Routing: list, create completion, and work queue generate `/operations/shipments/<public_id>`. Detail loading uses `GET /api/operational-shipments/by-public-id/<uuid>` and resolves organization membership before the public identifier.
- Security tests: direct authorized opaque lookup passed; cross-organization lookup of the same UUID returned indistinguishable `RESOURCE_NOT_FOUND`/404.
- Browser closeout: authenticated list navigation emitted `/operations/shipments/668da312-87de-4933-afd9-c23a2aeef993`; direct deep link and refresh retained it; MDPM readiness rendered `Ready for IN_PROGRESS`; Persian RTL remained intact; clean proof-tab console errors were zero. Prior English LTR and controlled-override mutation evidence remains applicable and passed.
- Targeted routing/browser tests: `18 passed` frontend and `9 passed` backend.
- PostgreSQL race gate: `13 passed` in 20.48 seconds. The clone fixture now measures the append-only template event baseline, proving one new event without deleting evidence-custody history.
- Full regression: backend `566 passed, 33 skipped`; frontend `111 passed`; production build PASS; lint PASS with zero errors and 12 existing warnings; OpenAPI/runtime parity PASS; disposable migration current/head `20260813_mdpm_readiness`, pending `no`; `git diff --check` PASS.
- Migration SHA-256: `893E983364189BC2B16CF0BE06A7B96A1BFDF31F2BF8214B59048E8968B44459`.
- OpenAPI SHA-256: `CF063631981B8F367CE340454BBF212958A6080407A34F452C9AC71E426C4430`.
- Remaining bounded MDPM limitations are unchanged: one transition binding per requirement, source-request-scoped artifact reuse, and association rather than binary duplication. Explicit milestone UUID entry for overrides is a bounded UX limitation, not a contract/security promotion blocker.
- Framework delta: **PATTERN CANDIDATE** — opaque external identity applies consistently across API and UI navigation boundaries. EAAF philosophy is unchanged.
- Legacy numeric containing-route limitation: **CLOSED** after authenticated browser proof.
- Promotion decision: **MDPM-1 PROMOTION CANDIDATE READY**.
