# D2-R1 — Database URL Validation Repair

## Evidence and root cause

The transferred D2 `final2` package correctly stopped before mutation with
`VALIDATION_RESULT=NO_GO`; no Production repair was attempted. Prior P0-R3
evidence establishes that the runtime uses the supported SQLAlchemy form
`postgresql+psycopg2://`.

The D1 gate used a generic .NET `Uri` scheme check before normalizing the
SQLAlchemy driver-qualified URL. That parser-based boundary rejected a valid,
repository-supported PostgreSQL form rather than applying the repository's
database-driver contract.

## Repair

The gate now uses a narrow, case-insensitive allowlist:

- `postgresql://`
- `postgresql+psycopg2://`

Only the latter is normalized to `postgresql://` for safe .NET connection
component handling. This does not accept arbitrary `postgresql+driver` forms.
MySQL, SQLite, MSSQL, malformed, absent, and unknown-driver URLs remain
fail-closed. Output contains only presence, engine, and driver classification;
it never includes the raw URL, user, or password.

The read-only database-name and Alembic-head verification remain unchanged, and
no migration/DDL/DML path is added. The old `D2-VALIDATION-S7-RC-f11f2ab-final2`
package is historical evidence only. D2-R1 is the current validation package.

`PRODUCTION_ACCESS=NO`

`PRODUCTION_CHANGE=NO`

`DEPLOYMENT_PERFORMED=NO`
