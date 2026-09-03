# DP.1 operator runbook — S7-RC-a257669-rg1-frozen

This package is an RC-specific deployment and validation control package.  It
does not contain the application archive and cannot authorize, contact, or
change Production by itself.

## Immutable application identity

| Field | Value |
|---|---|
| Release ID | `S7-RC-a257669-rg1-frozen` |
| Source commit | `a2576690364fcaf58ca7ddc6c57143c3084bbb00` |
| Application ZIP SHA-256 | `aca7a147cad97edf0e3f03d763c63471c283f62021a23a4e6a47b5e59aa88534` |
| Target Alembic head | `20260908_governed_international_geography` |
| Rollback rule | Keep upgraded DB; roll back only application/runtime |

## Controlled execution order

1. Independently verify this deployment ZIP's manifest and SHA-256.
2. Verify the application ZIP and its frozen release manifest exactly match
   the identity above.  Stop on any mismatch.
3. Run `preflight_a257669.ps1` on the governed host.  It is read-only and must
   capture IIS binding/path, scheduled task action/status, listener/process
   ownership, config shape (secrets redacted), and—when a credential-safe psql
   path is supplied—read-only database identity and `international_city`
   duplicate/malformed-UN/LOCODE readiness.
4. Require explicit approval of the preflight evidence, a tested backup,
   exact rollback application release, target path, and maintenance window.
5. Run `deploy_a257669.ps1` with both `-Execute` and `-ConfirmDeployment`.
   Its `PRECHECK_COMPLETE` and `READY_FOR_FIRST_MUTATION` markers are the
   two-person mutation boundary. The current DP.1 script intentionally stops
   there: a production mutation implementation requires a separately reviewed
   authorization and host-specific preflight evidence.
6. After a reviewed mutation implementation has completed, run
   `validate_a257669.ps1` against the approved canonical base URL. It checks
   one listener/process, health, canonical CORS allow, legacy CORS deny, and
   unknown-origin deny before it can report `DEPLOYED_AND_VERIFIED`.

## Stop / fallback controls

Stop before mutation for identity, evidence, backup, target-path, listener,
IIS, task, CORS, database-revision, or international-city readiness failure.
After a migration, never attempt DB downgrade: preserve the upgraded database,
restore only the known-good application/runtime release, and revalidate health
and CORS. A post-migration application incompatibility, failed smoke check, or
loss of singular ownership triggers that fallback.

## Evidence to retain

Deployment package hash and manifest, application package hash and manifest,
read-only preflight JSON, backup identity/restore drill result, mutation log,
post-deploy validation JSON, and final release identity record.
