# Forwarder Rollback Runbook

Status: restore-based recovery certified against repair commit `61b68c0a0a8f2310ee19b2934f8c985dfea4a7b2` on disposable PostgreSQL 18; the procedure is incorporated unchanged into final certified Release Candidate `85fbd78b46a544367ab40144fdf8d51d422f8dcc`.

## Rollback triggers

Rollback or abandon deployment when migration fails, readiness is not HTTP 200, required smoke fails, cross-tenant access regresses, data integrity differs unexpectedly, repeated HTTP 500s occur, or the release owner declares the operational impact unacceptable.

## Decision point

1. Stop new deployment traffic according to the authorized maintenance procedure.
2. Preserve logs and the failed database for investigation where operationally safe.
3. Confirm the certified pre-deployment backup is readable.
4. Decide separately:
   - application/configuration rollback; and
   - database recovery.

Do not equate application rollback with database downgrade.

## Application and configuration rollback

1. Restore the retained previous application/frontend artifact.
2. Restore the previous approved configuration reference without exposing values.
3. Confirm the previous application is compatible with the current database schema.
4. If compatibility is not explicitly proven, keep traffic stopped and use database restore.

## Database recovery

Blind `alembic downgrade` must not be used. The migration chain contains guarded/fail-closed downgrades and later data may not be representable in an earlier schema. The certified recovery method is restore from the verified pre-deployment backup.

Using approved placeholders:

```powershell
$env:PGPASSWORD = '<APPROVED_DATABASE_PASSWORD>'
pg_restore --list '<BACKUP_PATH>\forwarder-predeploy.dump'
createdb -h '<DB_HOST>' -p '<DB_PORT>' -U '<DB_USER>' '<CLEAN_RECOVERY_DB>'
pg_restore --no-owner --no-privileges -h '<DB_HOST>' -p '<DB_PORT>' -U '<DB_USER>' -d '<CLEAN_RECOVERY_DB>' '<BACKUP_PATH>\forwarder-predeploy.dump'
```

Use the database-owner-approved switch/rename procedure; do not overwrite the failed target until evidence retention and recovery ownership are agreed.

## Verification

Verify:

- Alembic revision;
- representative table counts and relationships;
- organization ownership and memberships;
- request, project, shipment and ExecutionUnit public identities;
- tracking codes and UTC events;
- document associations and exact versions;
- external references and tenant ownership;
- `/api/health` and `/api/health/ready` return 200;
- minimal authenticated smoke and cross-tenant denial.

If restore or verification fails, keep traffic stopped and escalate to the database owner, release owner and application owner. Do not retry destructive operations against the only recovery copy.
