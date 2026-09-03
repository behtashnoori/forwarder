# Production deployment preflight — S7-RC-a257669-rg1-frozen

## Authority and result

- Mode: `READ_ONLY_PREFLIGHT`
- Governing baseline: LPAF v2.2 (ACTIVE)
- Rigor: B — Product / Production
- Applicable stages: M6 Verify, M7 Release, M8 Operate, M9 Improve
- Authority boundary: inspect only; no Production file, DB, IIS, Scheduled Task,
  process, configuration, or service mutation.
- Verdict: **STOP**

## Frozen candidate reconfirmation

| Field | Value |
| --- | --- |
| Release ID | `S7-RC-a257669-rg1-frozen` |
| Application source | `a2576690364fcaf58ca7ddc6c57143c3084bbb00` |
| ZIP size | `1323912` bytes |
| ZIP SHA-256 | `aca7a147cad97edf0e3f03d763c63471c283f62021a23a4e6a47b5e59aa88534` |
| Sidecar SHA-256 | `e826468900d11408a4c7f8c01da45f9f86dff8f19e25155ed840080d5cf8a613` |
| Frozen evidence SHA-256 | `843d19f89658410ce376b28fe7866120367de1a83f9a5d88ff7deade8e760f16e` |
| Target Alembic head | `20260908_governed_international_geography` |

All local identities matched the frozen record.

## Read-only Production evidence

`samand.forwarderet.ir` resolved to `130.185.77.25`. The following non-mutating
HTTPS checks passed:

| Check | Result |
| --- | --- |
| `/` | 200 |
| `/api/health` | 200 |
| `/api/health/ping` | 200 |
| Canonical-origin GET and OPTIONS | allowed |
| `https://server.logisticmarket.ir` GET and OPTIONS | no ACAO header |
| Unknown-origin GET and OPTIONS | no ACAO header |

No authenticated, governed read-only host channel was available for IIS,
Scheduled Task, listener/process, runtime path, Production configuration, or
PostgreSQL/Alembic inspection. These values are **UNKNOWN**, not inferred from
historical evidence.

## Deployment-runbook review

The available deployment entrypoints are bound to the superseded candidate
`S7-RC-f11f2ab`, its ZIP name, source SHA, target path, and Alembic head
`20260907_direct_shipment_responsibility`. They cannot safely deploy this RC.

The repository graph does contain the direct path:

```text
20260907_direct_shipment_responsibility
  -> 20260908_governed_international_geography
```

The target migration is additive columns plus a country/UN-LOCODE uniqueness
constraint and format check. Its downgrade refuses when governed provenance
exists. Therefore application rollback after migration is
`SAFE_WITH_CONSTRAINTS`: restore the previous application/IIS/task runtime while
retaining the upgraded database; do not automate Alembic downgrade.

## Required future deployment contract

1. Read-only precheck of exact current IIS, Scheduled Task, listener, runtime,
   release, DB identity/Alembic, config-key presence, rollback path, and target
   path collision.
2. Capture DB backup/snapshot identity, config backup/reference, IIS/task
   metadata, listener identity, and rollback artifact identity.
3. Transfer frozen ZIP; verify Production-side SHA equals the frozen SHA before
   extraction.
4. Extract to a previously absent target path; validate manifest and package
   secret policy.
5. Run the explicit migration only after data-readiness checks prove the new
   uniqueness constraint is satisfiable.
6. Activate candidate, prove singular listener ownership, IIS/task target,
   health, canonical CORS allow, legacy/unknown CORS reject, DB/Alembic target,
   and runtime identity.

The first future mutation is **creating the approved backup/staging or target
release location**, after a printed `PRECHECK_COMPLETE` and separate human
deployment authorization.

## Blockers

| Priority | Finding | Required resolution |
| --- | --- | --- |
| P1 | No RC-specific deployment/validation package exists; available scripts are bound to `f11f2ab`. | Build and qualify an `a257669`-specific deployment package/runbook without changing the frozen application bytes. |
| P1 | Current host/IIS/task/listener/runtime/config/DB/Alembic/rollback identity has not been read-only verified. | Provide a governed read-only host preflight channel and record the exact observations. |
| P1 | Production data readiness for the new unique constraint is unproven. | Run only read-only duplicate/null/prerequisite queries through that approved channel. |
| P2 | Lint retains 12 pre-existing warnings; npm reported dependency advisory/engine warnings during local build. | Record acceptance or remediate separately; neither invalidated RC qualification. |

## Mutation matrix

| Action | Mutates Production | Gate |
| --- | --- | --- |
| HTTP/DNS/IIS/task/listener/DB read | No | precheck |
| Backup capture | Yes | deployment-time |
| Copy/extract ZIP | Yes | deployment-time |
| Alembic upgrade | Yes | deployment-time |
| IIS/task/process switch | Yes | deployment-time |
| Health/CORS verification | No | post-deployment |

## Safety statement

`PRODUCTION_ACCESSED=YES` (public read-only HTTPS only).
`PRODUCTION_FILES_CHANGED=NO`; `PRODUCTION_DATABASE_CHANGED=NO`;
`PRODUCTION_IIS_CHANGED=NO`; `PRODUCTION_SCHEDULED_TASK_CHANGED=NO`;
`PRODUCTION_PROCESS_STATE_CHANGED=NO`; `PRODUCTION_CONFIG_CHANGED=NO`.
`ARTIFACT_STAGED_ON_PRODUCTION=NO`; `MIGRATION_EXECUTED=NO`;
`DEPLOYMENT_PERFORMED=NO`; `ROLLBACK_PERFORMED=NO`.
