# PR-5 PostgreSQL runtime-driver dependency closure

## Finding

The frozen PR-4D source candidate did not declare a PostgreSQL driver in the
deployable root `requirements.txt`, although Production configuration selects
SQLAlchemy's `postgresql+psycopg2` driver. Production continued to work only
because `psycopg2-binary 2.9.11` was already installed in its Python runtime.

A clean isolated rehearsal environment reproduced the deployment failure as
`ModuleNotFoundError: No module named 'psycopg2'`. Installing
`psycopg2-binary==2.9.11`, matching the existing Production runtime, closed the
failure; migration inspection, the rehearsed Production-clone upgrade, and
application readiness then passed. Production itself was not changed.

## Closure

Both repository dependency contracts now declare
`psycopg2-binary==2.9.11`. Package verification requires the exact declaration,
server verification imports the driver and checks its installed distribution
version from the release-local virtual environment, and a focused regression
test protects the source contracts.

This removes reliance on an accidental global installation without changing
`DATABASE_URL` semantics, SQLAlchemy driver selection, application version
`1.9.0`, database schema, or migration head
`20260818_immutable_fx_provenance`.

The prior candidate `CAND-FWD-INTEGRATED-RC-PR4D-001` at product commit
`9bef5eebab710b94cc49fd5af0380ccba9e53c32` remains immutable historical
evidence and is superseded for deployment by the release-hardening commit that
contains this closure. A deployment package must bind its manifest to that new
commit; no existing tag or artifact may be relabeled.
