# Phase 1B Local Database Rollback Runbook

## Status and authority

Rollback capability is retained, but rollback is not automatic after closure.
It may occur only under a separate change decision with explicit operator
approval, an approved local maintenance window, and independent validation.

This document records controls and decision gates only. It intentionally
contains no executable rollback command.

Rollback database:

`forwarder_db_legacy_20260727_222328`

Current active database:

`forwarder_db` at `20260801_route_exception`

## Mandatory preconditions

Before any future rollback activity, all of the following must be independently
approved and recorded:

1. A concrete rollback reason and incident/change owner.
2. Confirmation that the retained legacy database and both backups still
   exist and match their recorded identities.
3. Verification of the evidence SHA-256 manifest.
4. A new backup of the then-current active database under a separate gate.
5. A connection and maintenance-window plan.
6. An independently reviewed validation plan for database identity, revision,
   integrity, and application behavior.
7. Explicit operator confirmation immediately before any mutation.

Failure of any precondition is a No-Go.

## Required rollback decision sequence

The future approved operator must:

1. freeze local writes using the independently approved maintenance plan;
2. identify, without changing, `forwarder_db` and
   `forwarder_db_legacy_20260727_222328`;
3. revalidate backup and evidence references;
4. execute only the separately reviewed database-name transition;
5. validate database identity and application behavior before reopening writes;
6. retain the displaced database, all backups, and all evidence;
7. record a new rollback evidence set and closure decision.

No step in this sequence is authorized by this document alone.

## Prohibitions

- Rollback must not start without a separate decision and explicit approval.
- Rollback is not automatic.
- Final Cutover must not be rerun.
- `forwarder_db_legacy_20260727_222328` must not be deleted or renamed before
  an approved rollback transition.
- The retained legacy database must not receive a raw Alembic upgrade, stamp,
  archived migration, or manual `alembic_version` edit.
- Backups must not be deleted.
- The evidence archive or manifest must not be deleted or modified.
- Restore or rollback must not proceed without independent validation.
- The active database displaced by rollback must not be dropped.
- No server or Production action is authorized.

## Recovery assets

Pre-cutover backup:

`D:\1-webapp\_db_backups\15-forwarder\20260727_222328\forwarder_db_before_phase1b_cutover_20260727_222328.dump`

SHA-256:
`8b5e7b1ba21da3a51189701529386e19777649c1f9acf1caf17ae06355c8bfa4`

Final backup:

`D:\1-webapp\_db_backups\15-forwarder\20260727_222328\forwarder_db_final_20260727_222328.dump`

SHA-256:
`5166d13972582f770786d65fcf495da5b9ec3f22bbb11c7c21d4737897719408`

Evidence archive:

`D:\1-webapp\_db_backups\15-forwarder\20260727_222328\evidence`

Evidence manifest:

`D:\1-webapp\_db_backups\15-forwarder\20260727_222328\evidence\evidence-sha256-manifest.json`

## Validation and stop conditions

Independent validation must confirm the expected database identity,
application connectivity, integrity, and explicitly approved revision state.
Any identity ambiguity, missing asset, hash mismatch, connection ambiguity,
integrity failure, or application validation failure stops the rollback.

Do not improvise, retry Final Cutover, run migrations, delete a database, or
continue to server/Production.

## Server and Production boundary

Local rollback availability is not a server rollback plan. Server and
Production require an independent architecture, authorization, backup,
validation, deployment, and rollback process.

```text
ROLLBACK_AVAILABLE=True
ROLLBACK_AUTOMATIC=False
ROLLBACK_REQUIRES_EXPLICIT_APPROVAL=True
FINAL_CUTOVER_RERUN=FORBIDDEN
RAW_LEGACY_ALEMBIC_UPGRADE=FORBIDDEN
SERVER_CUTOVER=NOT_STARTED
PRODUCTION=UNTOUCHED
```
