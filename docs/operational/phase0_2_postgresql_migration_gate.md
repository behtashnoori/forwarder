# Phase 0.2 PostgreSQL migration gate

## Scope and decision

This gate validates Alembic, disposable PostgreSQL, migration reversibility, runtime startup safety, the migration CLI, and health/readiness behavior. It does not add an operational model, endpoint, frontend workflow, CRM/quote feature, or business logic. Production, deployment branches, server services, production credentials, and production databases are out of scope.

The validated repository base is `2eae172c52b41acd2bdb6c59264f2d16ab434172`. The expected and observed sole Alembic head is `20260728_add_quote_customer_response`; the root is `20240917_initial_schema` and all 42 revisions are reachable.

## Gate summary

| Gate | Result | Evidence |
|---|---|---|
| Fresh empty upgrade | PASS | PostgreSQL 18, base to sole head, one version row |
| Head/previous/head | PASS WITH IRREVERSIBLE MIGRATION NOTE | schema fingerprint identical after re-upgrade; populated response values would be dropped |
| Existing synthetic data | PASS | `site_setting` sentinel preserved |
| Catalog constraints | PASS WITH NOTES | 42 tables, 96 FKs; entry-port/province each have one FK |
| Metadata comparison | NOTE | `alembic check` reports broad historical metadata drift |
| Startup safety | PASS | app factory and `skip_startup=True` do not write schema |
| Migration CLI | PASS | current=0, check pending=2, unconfirmed upgrade=2, confirmed=0 |
| Health/readiness | PASS | ping is DB-free; health checks connectivity; ready checks revision/tables |
| Idempotency | PASS | repeated upgrade/check/readiness leave schema unchanged |
| Concurrency | PASS WITH NOTE | concurrent reads pass; dual upgrade produced explicit 1/0, no corruption |

Fresh schema catalog totals were 42 application tables, 140 indexes, 96 foreign keys, 21 unique constraints, 44 check constraints, and 42 primary keys. Migration `20260726_seed_iran_tracking_reference` intentionally creates 66 reference rows during an explicit Alembic upgrade. This is migration-owned reference data, not an automatic startup seed; normal and `skip_startup` app creation created no rows.

## Findings and limitations

The two requested `shipment_request` entry columns each have one official FK in a fresh schema. A semantic catalog scan reports 11 duplicate FK shapes elsewhere; these are historical schema facts and are not modified by a speculative migration in this phase. `alembic check` reports extensive historical differences between ORM metadata and migration output, so metadata equality is not claimed.

The head downgrade is executable but drops its two response columns and would lose values if populated. The tracking-reference seed revision has a no-op downgrade and is intentionally data-irreversible. A full downgrade to base is not approved as a normal operational path; only the required head-to-previous cycle was used for the pass decision.

No production system was contacted or changed. No deployment, production migration, history rewrite, force push, tag, merge, or OperationalShipment implementation was performed.

## Cleanup confirmation

The exact temporary database was dropped, the isolated cluster was stopped cleanly, and its verified OS-temporary data directory was deleted. The cluster-owned temporary role ceased to exist with that disposable cluster. Temporary state, fingerprint, and log files were removed. Post-cleanup checks found no PostgreSQL process for the temporary data directory; the pre-existing `postgresql-x64-18` service remained running and unchanged.
