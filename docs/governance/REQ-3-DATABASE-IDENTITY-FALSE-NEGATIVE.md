# REQ-3 — Database identity false-negative repair

## Scope and safety

This was a Development-only forensic repair. Production database and Alembic
identity were accepted as independently proven correct. No Production access,
connection, mutation, deployment, artifact transfer, push, or merge occurred.
The frozen application RC and its hashes were not changed.

## Production evidence acknowledged

- Expected and actual database: `forwarder_prod_20260728_161711` — PASS.
- Expected and actual Alembic head: `20260907_direct_shipment_responsibility` — PASS.
- R5 nevertheless failed PRECHECK 44 with the combined database/Alembic message.

## Exact root cause and reproduction

R5 invoked `psql -Atc` with `BEGIN ...; SELECT ...; COMMIT;` and then evaluated
only `($result | Select-Object -First 1)`. Under Windows PowerShell 5.1 the
native command output is pipeline-enumerated as `System.String` records. The
first record is the transaction status `BEGIN`, not the scalar identity record.
The exact R5 expression was reproduced with `BEGIN`, the correct joined identity,
and `COMMIT`; it returned false. Thus the correct values never reached the
comparison. R5 also did not test `$LASTEXITCODE`.

For the reproduced correct values, both expected and actual values are
`System.String`: database length 31 and Alembic length 41. There was no value
difference; the database comparison operand was the wrong output record and the
Alembic value was never independently compared.

## Systemic correction and psql output contract

The command now uses `-X -q -v ON_ERROR_STOP=1 -Atc` in a read-only transaction.
It emits tagged rows `DATABASE=<value>` and `ALEMBIC=<value>`. The validator:

1. requires exit code zero;
2. accepts exactly one row for each tag;
3. rejects zero, empty, or multiple tagged rows;
4. trims only the scalar payload and compares ordinal strings;
5. reports expected/actual value, runtime type, length, and equality result;
6. emits independent `DATABASE_IDENTITY` and `ALEMBIC_IDENTITY` gates.

Unrelated stdout (`BEGIN`/`COMMIT`) is ignored by tag, while stderr is not part of
the captured identity pipeline. Query errors remain fatal. Arrays are never cast
to a comparison string.

## Packaged baseline contract

The deployment entrypoint now reads the package-local
`expected-production-baseline.json` supplied by the package wrapper. Both
`database` and `alembic_head` must be non-empty scalar JSON strings. The packaged
values are exactly the Production values above. A quoted value is a literal and
fails identity comparison; a UTF-8 BOM is handled by PowerShell JSON decoding.
The package manifest protects the baseline bytes and hash.

## Identity and failure matrix

Correct/correct passes. Wrong database, wrong Alembic, both wrong, empty database,
empty Alembic, multiple database rows, multiple Alembic rows, and nonzero psql
exit all return governed NO_GO. CRLF and surrounding scalar whitespace normalize
deterministically. Object-array output containing transaction records is parsed
by tag. A stderr notice does not contaminate identities. No unhandled tooling
exception was observed and every ValidateOnly case remained before the mutation
boundary.

## Qualification

Windows PowerShell reference runtime: `5.1.26100.9278`.

Development qualification passed 18 source-level REQ-3/regression tests. The
final immutable package qualification, exact ZIP hashes, full precheck count,
ten-run result, simulated deployment/rollback, and provenance are recorded in
the final mission report after the single build and extracted-package run.

## Residual risks

The local qualification uses a deterministic native-command fixture rather than
a real PostgreSQL server, while exercising the real non-Simulation parser and
comparison path. Production remains uncontacted by design. The next authorized
step is a read-only Production ValidateOnly run of R6; R5 must remain historical
and must not be deployed.
