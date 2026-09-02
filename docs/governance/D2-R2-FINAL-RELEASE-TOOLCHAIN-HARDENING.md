# D2-R2 — Final Release Toolchain Hardening

## Production validation history

Both Production ValidateOnly attempts stopped before mutation and did not affect
Production. The first rejected the SQLAlchemy PostgreSQL URL due to a generic
URI-scheme boundary. D2-R1 added the correct driver allowlist but the packaged
execution still rejected the URL because the env-file parser passed leading
whitespace and surrounding quotes through unchanged.

P0 evidence classified the real value as `postgresql+psycopg2`; it was not a
database-engine failure. Previous fixtures used unquoted LF-only values and so
did not exercise the actual env-file representation.

## Hardening

`Env-Map` now trims whitespace, removes a UTF-8 BOM from the first key, and
unwraps matching single or double quotes before the narrow database URL
allowlist. Only `postgresql://` and `postgresql+psycopg2://` are accepted.
The latter is normalized only for .NET connection-component parsing. Unknown
drivers and non-PostgreSQL/malformed values remain fail-closed.

The exact packaged operator workflow is exercised using Windows PowerShell,
the copied package scripts, CRLF env content, quoted realistic driver-qualified
URL, and percent-encoded fake credential characters. It reaches ValidateOnly
success without printing the credential, extracting a release, changing config,
or crossing `MUTATION_BOUNDARY_REACHED`.

The deployment path was also audited: identity/manifest checks precede any
write; the mutation boundary precedes rollback-state capture; rollback restores
the prior environment bytes, Scheduled Task definition and IIS path; and
post-activation verification checks release identity, listener, health,
canonical/legacy/unknown CORS, database and Alembic continuity. No migration,
DDL or DML command exists.

`PRODUCTION_ACCESS=NO`

`PRODUCTION_CHANGE=NO`

`DEPLOYMENT_PERFORMED=NO`
