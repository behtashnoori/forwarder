# MT-1 completion readiness

## Verdict

`MT-1 BLOCKED — EXTERNAL ACTION REQUIRED`

The synthetic legacy branch is closed, but MT-1 itself is not complete. The
exact external action is an architecture/data-policy decision defining the
future canonical ownership model. Until that decision exists, a schema migration
would guess tenant ownership semantics and violate the fail-closed contract.

## Objective and repository completion criteria

MT-1 establishes unambiguous tenant ownership and mechanically enforces
same-tenant relationships. The tracked MT-0 contract requires MT-1 to resolve
ambiguous owners, backfill without assumptions, quarantine unresolved data, and
add non-null keys and same-tenant constraints
(`multi-tenant-architecture-contract.md`, phase dependencies). The workspace
master plan further defines the bounded-domain sequence as expand, resumable
backfill, shadow measurement, validate, and contract; a domain is done only when
ownership, constraints, consistency SLOs, and cutover are proven.

The current MT-1 migrations are:

- `20260820_mt1c_quarantine_runtime`: persistent quarantine/certification scope.
- `20260821_mt1d_canonical_census`: canonical identity and atomic census publication.
- `20260822_mt1c1_census_fence`: transaction/census fencing.

These migrations intentionally add no tenant key and perform no ownership
backfill. The models still lack canonical Organization ownership on roots such
as `ShipmentRequest`, `Customer`, `CustomerGamification`, `AssignmentRule`,
`ReferralRule`, `ReferralAutoAssignState`, and `Report`; `ExpertQuote` retains a
nullable key. Same-tenant constraints for the legacy graph therefore remain
unimplemented.

## MT-1 control map

| Slice/control | Classification | Repository evidence |
| --- | --- | --- |
| MT-0 architecture dependency | `COMPLETE_CERTIFIED` for the MT-1 contract boundary | `multi-tenant-architecture-contract.md`; `test_tenant_architecture_contract.py` |
| MT-1 initial integrity analysis | `COMPLETE_BUT_DOCUMENTATION_OPEN` | `mt-1-tenant-data-integrity.md` records the original no-go and required decisions; its unknown-provenance mapping premise is superseded only for this census |
| MT-1A ownership theory/analyzer | `COMPLETE_CERTIFIED` as fail-closed tooling | `mt1a_legacy_ownership_analyzer.py` and focused tests |
| MT-1B mapping/certification tooling | `COMPLETE_CERTIFIED` as infrastructure | mapping schema, quarantine matrix, analyzer evidence tests |
| MT-1C quarantine runtime | `COMPLETE_CERTIFIED` | `QUARANTINE_RUNTIME_CERTIFIED=true` |
| MT-1C.1 transaction/materialization foundation | `COMPLETE_CERTIFIED` | census fence migration and foundation tests |
| MT-1C.2 15-surface protection | `COMPLETE_CERTIFIED` | `mt-1c2-full-surface-certification.md`; `MT1C_FULL_SURFACE_CERTIFIED=true` |
| MT-1D identity/census publication | `COMPLETE_CERTIFIED` | canonical census migration, PostgreSQL evidence, and security-review PASS |
| 135-row provenance classification | `COMPLETE_CERTIFIED` | synthetic disposition manifest and hash-bound analyzer gate |
| 22-event tenant adjudication | `OBSOLETE_BY_SYNTHETIC_CLASSIFICATION` | `LEGACY_SYNTHETIC_ADJUDICATION_STATUS=NOT_APPLICABLE` |
| Real ownership mapping/backfill for these 135 rows | `NOT_APPLICABLE` | `SYNTHETIC_ONLY`; Organization assignment prohibited |
| Canonical ownership schema for future business rows | `NOT_STARTED` | root models have no canonical key; MT-1 control migrations explicitly avoid tenant assignment |
| Same-tenant FK/uniqueness contract | `NOT_STARTED` | only already-operational models have direct same-tenant constraints |
| Future-write/public-intake ownership policy | `BLOCKED_EXTERNAL` | `mt-1-tenant-data-integrity.md`, “Required decision/evidence to unblock” |
| Final ownership migration PostgreSQL certification | `BLOCKED_EXTERNAL` until design/implementation | no ownership migration exists to certify |

Historical status text saying MT-1C or MT-1D was blocked is retained as evidence
of the state at that time. Later MT-1C.2 and MT-1D certification evidence closes
those implementation blockers; it does not close the missing ownership schema.

## Synthetic legacy effect

The owner classified all 135 census rows as test/synthetic. Consequently:

- real-customer ownership adjudication and the projected 22 review events are
  not applicable;
- Organization IDs must not be invented and mapping/backfill is prohibited;
- `MT1_OWNERSHIP_RESOLUTION_READY=false` remains semantically honest and is not
  required to become true for this dataset;
- the separate, hash-bound provenance gate supersedes applicability of the real
  ownership gate only for this census;
- UNKNOWN, changed-hash, changed-row-count, and future real datasets fail closed.

This changes legacy transition work, not the product schema completion criteria.

## Gap analysis

### MT1-G01 — `EXTERNAL/HUMAN_APPROVAL_GAP` (priority 1)

- **Requirement:** approve canonical future ownership semantics: whether staged
  nullable roots are permitted while quarantined; how new public intake obtains
  or defers tenant ownership; whether assignment/referral/report/gamification
  roots are tenant or platform scoped; and how mixed document audit events gain
  a tenant envelope or split.
- **Current state/evidence:** unresolved in `mt-1-tenant-data-integrity.md`; the
  synthetic assertion answers none of these future-data questions.
- **Security consequence:** guessing permits cross-tenant attribution or creates
  a schema that cannot safely reach `NOT NULL`.
- **Local implementation:** no, not before the decision. Server/Production and
  destructive access: no. Dependency: none. Recommended order: first.

### MT1-G02 — `LOCAL_CODE_GAP` (priority 2, blocked by G01)

- **Requirement:** bounded expand migration and model contract for canonical
  ownership roots, followed by composite same-tenant constraints in dependency
  order.
- **Current state/evidence:** no such columns/migration; existing MT-1C/D
  migrations explicitly avoid tenant assignment/backfill.
- **Security consequence:** tenant ownership and parent/child agreement remain
  unproven outside quarantine controls.
- **Synthetic effect:** permits the 135 rows to stay null only under an approved
  staged-quarantine contract; does not remove the product requirement.
- **Local implementation:** yes after G01. No server/Production/destructive access
  is needed for the first expand slice. Dependencies: G01. Recommended order: second.

### MT1-G03 — `LOCAL_TEST_GAP` and `CERTIFICATION_GAP` (priority 3)

- **Requirement:** prove fresh install, v1.9.1 upgrade, idempotent transition,
  synthetic quarantine preservation, future explicit-owner writes, cross-tenant
  FK rejection, rollback safety, and no synthetic exemption leakage.
- **Current state:** current control tests pass, but no ownership migration exists
  to test. Synthetic classification does not change this.
- **Local implementation:** focused tests are local after G02. Disposable
  PostgreSQL certification is required afterward; Production is not required.
  No destructive real-data action is authorized.

### MT1-G04 — `SERVER_VALIDATION_GAP` (priority 4)

- **Requirement:** new PostgreSQL evidence for the actual ownership migration,
  including constraint validation, locks/capacity estimates, downgrade/re-upgrade,
  and backup/restore rehearsal required by the master plan.
- **Current state:** existing PostgreSQL evidence certifies quarantine, census,
  and full-surface controls—not a nonexistent ownership migration.
- **Synthetic effect:** removes real-row adjudication, not database certification.
- **Access:** requires a separately authorized disposable/local certification
  database or approved server environment; never Production by implication.

### MT1-G05 — `DATA_DISPOSITION_GAP` (non-blocking housekeeping)

`KEEP_QUARANTINED_SYNTHETIC` is a valid terminal MT-1 state. Cleanup, archive,
reset, retirement, or fixture regeneration requires separate approval but is not
an MT-1 security blocker. No repository contract requires deletion before MT-1
completion.

There is no distinct `PRODUCTION_VALIDATION_GAP` required to implement MT-1
locally. Production readiness remains a later milestone and must not be inferred
from local or disposable PostgreSQL evidence.

## Exact next slice

There is no safe local product-code slice before MT1-G01. The next action is the
external architecture decision enumerated there. Once approved, the next bounded
implementation is an additive canonical-ownership **expand** slice for the core
request/customer/quote domain that preserves quarantine, performs no synthetic
assignment, and introduces no destructive contract step.

This review adds only the explicit completion gate and machine-readable state;
it does not fabricate a migration to create activity.

## Completion state

| State | Result |
| --- | --- |
| Runtime tenant fencing | `FAIL` — quarantine fencing exists, canonical ownership constraints do not |
| Quarantine runtime | `PASS` |
| Full-surface protection | `PASS` |
| Legacy data provenance | `PASS` |
| Real legacy ownership | `NOT_APPLICABLE` for this census |
| Synthetic legacy disposition | `PASS` |
| Mapping/backfill | `NOT_APPLICABLE` for this census |
| Migration state | `FAIL` — ownership transition absent |
| Local test certification | `PASS` for implemented controls |
| Server certification | `PENDING_EXTERNAL` for the future ownership migration |
| Production readiness | `PENDING_EXTERNAL`; MT-2/MT-3 and later gates remain |

Machine-readable state: `mt-1-completion-state.json`.

## Adversarial completion review

The review attempted all required bypasses. UNKNOWN and mismatched datasets do
not receive the synthetic exemption; candidates/active mappings invalidate it;
classification does not assign ownership, clear quarantine, or flip
`MT1_OWNERSHIP_RESOLUTION_READY`; held, Core/raw-DML, descendant, endpoint,
download, cache, and full-surface controls retain their certified fail-closed
contracts; cleanup is not assumed; current PostgreSQL evidence is not described
as certifying a future migration; Production readiness is not claimed; migration
head and v1.9.1 integrity are independently rechecked.

The completion claim was disproved because the ownership schema is absent, and
the report remains blocked rather than weakening the gate.

`MT-1 COMPLETION SECURITY REVIEW — PASS`

This PASS certifies the accuracy and fail-closed nature of the completion review;
it does not classify MT-1 as complete.
