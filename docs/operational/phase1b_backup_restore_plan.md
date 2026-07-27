# Phase 1B backup and restore plan

## Current readiness

No backup was taken in this planning gate. Target-specific backup/restore readiness is **BLOCKED** because no persistent target, owner, destination, capacity evidence, retention policy, RPO/RTO, or restore rehearsal has been approved.

| Control | Status | Required evidence | Blocker |
|---|---|---|---|
| Backup owner | MISSING | Named accountable operator/team | YES |
| Backup destination | MISSING | Sanitized storage class/location and access boundary | YES |
| Capacity | UNKNOWN | Free capacity greater than estimated backup plus restore workspace and safety margin | YES |
| Encryption | UNKNOWN | At-rest and in-transit controls with key owner | YES |
| Backup method | PLANNED | PostgreSQL `pg_dump` custom format; production may also require managed/physical snapshot | YES until approved |
| Restore method | PLANNED | Restore into isolated disposable verification database | YES until rehearsed |
| Restore tested | NO EVIDENCE | Dated successful restore and integrity report | YES |
| Retention | MISSING | Approved retention and deletion policy | YES |
| RPO/RTO | MISSING | Business-approved objectives | YES |

## Proposed backup execution gate

The later execution gate must record the selected target fingerprint, PostgreSQL version, database-size class, owner approvals, destination capacity, encryption/key ownership, expected duration, maintenance impact, retention, and exact restore-test destination. Raw DSNs and credentials must never enter command logs or evidence.

Preferred sequence:

1. Confirm the selected fingerprint and read-only inventory.
2. Confirm owner, change ticket, maintenance window, RPO/RTO, destination, capacity, and encryption.
3. Quiesce or otherwise establish the approved consistency boundary.
4. For PostgreSQL, create a custom-format logical backup with `pg_dump` using an approved secret injection mechanism. For production, coordinate an additional managed/physical snapshot when required by the database owner.
5. Record tool/server versions, start/end times, sanitized size, exit status, and an artifact hash or custom-archive listing verification.
6. Restore into an isolated disposable database using a role policy that cannot affect the source.
7. Verify restoration: expected schemas/objects, Alembic revision, encoding, aggregate catalog counts, constraints/indexes, and bounded integrity aggregates.
8. Destroy the disposable verification database under its separately approved cleanup procedure; retain only sanitized evidence.
9. Obtain database-owner acceptance before the migration application gate.

## Restore and recovery decision

Database restore is preferred over downgrade when a downgrade guard rejects, when Phase 1B-only data exists, when migration behavior is partially applied or uncertain, or when application/schema compatibility cannot be guaranteed. Restore requires traffic isolation, a defined recovery point, reconciliation of writes after that point, and explicit business/database-owner approval.

Alembic downgrade may be considered only when the exact revision transition has passed a disposable rehearsal, the backup is verified, the guard permits it, data-loss analysis is accepted, and post-downgrade schema/application verification is prepared. A fail-closed downgrade guard is not a substitute for backup.

## Acceptance criteria

Backup/restore readiness passes only when all table controls are complete, a recent restore rehearsal succeeds within the approved RTO, the recovery point satisfies RPO, and named owners accept the evidence. Until then, migration application is prohibited.
