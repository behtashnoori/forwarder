# گزارش Authenticated Read-only Verification دیتابیس forwarder_db

## نتیجه تکمیلی inventory تأییدشده

خروجی read-only تأییدشده بعدی، `transaction_read_only=on` و پایان `ROLLBACK`،
PostgreSQL 18.0/UTF8، revision برابر `54ea21ea0d9f`، تعداد 32 table، 321 column،
252 constraint، 48 index، اندازه 10,794,687 bytes، connectionهای خارج از session
بازرسی برابر صفر و long transaction برابر صفر را ثبت کرد. تغییری در دیتابیس رخ
نداد. revision در graph اجرایی Alembic شناخته‌شده نیست؛ بنابراین نتیجه بعدی گیت
`UNKNOWN_REVISION` و توقف Phase A است.

`PHASE_1B_LOCAL_PERSISTENT_MIGRATION_GRAPH_BLOCKED`

## Canonical blocked-evidence record

- Target: `127.0.0.1:5432/forwarder_db`
- Source revision: `54ea21ea0d9f`
- Expected active head: `20260801_route_exception`
- Active graph: source revision absent; archive reference is evidence only and is not execution authorization.
- Migration classification: `UNKNOWN_REVISION`
- Go/No-Go: `LOCAL_PHASE1B_MIGRATION_GO=NO`
- Backup executed: `NO`; restore database created: `NO`
- Migration attempt count: `0`; seed executed: `NO`
- Persistent applied local/server: `NO` / `NO`
- Server access/deploy: `NO` / `NO`
- Credential or DSN recorded: `NO`
- Prohibited without an independent gate: Alembic stamp, raw Alembic upgrade, archived migration execution, manual `alembic_version` editing, and schema repair.

## نتیجه Gate

مالک، اتصال دستی احرازشده به `127.0.0.1:5432/forwarder_db` با Role برابر `postgres` را تأیید کرده است؛ `current_database=forwarder_db` و نسخه Server برابر 18.0 گزارش شده و Credential افشا نشده است.

محیط اجرای Codex امکان پاسخ تعاملی به `psql -W` را ندارد. طبق دستور Gate، Credential recovery یا روش جایگزین انجام نشد و Full Gate ادامه پیدا نکرد. هیچ Query دیتابیس توسط Codex اجرا نشد.

## Target

- Host: `127.0.0.1`
- Port: `5432`
- Database: `forwarder_db`
- PostgreSQL: 18.0 (manual confirmation and endpoint binary/service evidence)
- Encoding: UNKNOWN؛ اجرای Operator لازم است
- Read-only: NOT VERIFIED؛ اجرای Operator لازم است
- Credential source: interactive operator input
- Credential exposed: NO
- Project match: UNKNOWN؛ Metadata خوانده نشد

## Script دقیق Operator

Script موقت باید در `%TEMP%\phase1b-forwarder-db-readonly.sql` با محتوای زیر ساخته شود:

```sql
\set ON_ERROR_STOP on
\pset pager off

BEGIN READ ONLY;

SET LOCAL statement_timeout = '30s';
SET LOCAL lock_timeout = '5s';

SELECT
    current_database() AS database_name,
    current_setting('server_version') AS server_version,
    current_setting('server_encoding') AS server_encoding,
    current_setting('port') AS server_port,
    current_setting('TimeZone') AS timezone,
    current_setting('transaction_read_only') AS transaction_read_only;

SELECT
    current_setting('default_transaction_read_only')
        AS default_transaction_read_only;

SELECT
    schema_name
FROM information_schema.schemata
WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
ORDER BY schema_name;

SELECT
    table_schema,
    table_name
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
  AND table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;

SELECT count(*) AS application_table_count
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
  AND table_schema NOT IN ('pg_catalog', 'information_schema');

SELECT count(*) AS application_column_count
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema');

SELECT constraint_type, count(*) AS constraint_count
FROM information_schema.table_constraints
WHERE constraint_schema NOT IN ('pg_catalog', 'information_schema')
GROUP BY constraint_type
ORDER BY constraint_type;

SELECT count(*) AS application_index_count
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');

SELECT to_regclass('public.alembic_version') IS NOT NULL
       AS alembic_version_table_exists
\gset

\if :alembic_version_table_exists
SELECT version_num AS current_revision
FROM public.alembic_version
ORDER BY version_num;
\else
SELECT 'VERSION_TABLE_MISSING' AS current_revision;
\endif

SELECT pg_database_size(current_database()) AS database_size_bytes;

SELECT
    count(*) FILTER (WHERE state = 'active') AS active_connections,
    count(*) FILTER (WHERE state = 'idle') AS idle_connections,
    count(*) FILTER (
        WHERE xact_start IS NOT NULL
          AND now() - xact_start > interval '5 minutes'
    ) AS long_transactions
FROM pg_stat_activity
WHERE datname = current_database();

SELECT extname
FROM pg_extension
ORDER BY extname;

ROLLBACK;
```

SHA-256 محتوای Script ساخته‌شده و بررسی‌شده: `0871ABEC1E543823290BAC1D9692B39208BCF08FBFE6535F0C17AD0A54F31357`.

Command دقیق PowerShell:

```powershell
$PSQL = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$TEMP_SQL = Join-Path $env:TEMP "phase1b-forwarder-db-readonly.sql"
$TEMP_OUT = Join-Path $env:TEMP "phase1b-forwarder-db-readonly-output.txt"

& $PSQL `
  -X `
  -v ON_ERROR_STOP=1 `
  -h 127.0.0.1 `
  -p 5432 `
  -U postgres `
  -d forwarder_db `
  -W `
  -f $TEMP_SQL |
  Tee-Object -FilePath $TEMP_OUT
```

Password فقط در Prompt وارد شود. خروجی باید قبل از انتقال Secret-free تأیید و سپس هر دو فایل موقت حذف شوند.

## Migration

- Current revision: UNKNOWN
- Expected head: `20260801_route_exception`
- Pending revisions: UNKNOWN
- Classification: `UNKNOWN_REVISION` pending operator output
- Multiple heads: NO در graph محلی؛ Target نامعلوم

## Schema Drift

| Group | Expected | Target | Missing | Unexpected | Result |
|---|---:|---:|---:|---:|---|
| Tables | Pending contract extraction | UNKNOWN | UNKNOWN | UNKNOWN | NOT ASSESSED |
| Columns | Pending contract extraction | UNKNOWN | UNKNOWN | UNKNOWN | NOT ASSESSED |
| Primary keys | Pending contract extraction | UNKNOWN | UNKNOWN | UNKNOWN | NOT ASSESSED |
| Foreign keys | Pending contract extraction | UNKNOWN | UNKNOWN | UNKNOWN | NOT ASSESSED |
| Unique constraints | Pending contract extraction | UNKNOWN | UNKNOWN | UNKNOWN | NOT ASSESSED |
| Indexes | Pending contract extraction | UNKNOWN | UNKNOWN | UNKNOWN | NOT ASSESSED |
| Check constraints | Pending contract extraction | UNKNOWN | UNKNOWN | UNKNOWN | NOT ASSESSED |

## Runtime

- Database size class: UNKNOWN
- Active connections: UNKNOWN
- Long transactions: UNKNOWN
- Application active: UNKNOWN

## Backup/Restore

- Candidate destination: NONE APPROVED
- Encrypted: NO suitable verified destination found
- Outside repository: required
- Capacity/Writable: UNKNOWN for a secure destination
- pg_dump/pg_restore: PostgreSQL 18.0 present
- Restore verification possible: NOT YET
- Backup/Restore executed: NO / NO

## Isolation

- Database changed: NO
- Migration/Seed executed: NO / NO
- Server accessed: NO
- Deploy/Commit/Push: NO / NO / NO
- Persistent applied: NO
- Credential artifact: 0
- `.backend-port`: `57065`

PHASE_1B_LOCAL_READONLY_OPERATOR_EXECUTION_REQUIRED
