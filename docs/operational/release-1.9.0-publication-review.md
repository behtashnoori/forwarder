# Release 1.9.0 integrated publication review

## Boundary

Release 1.9.0 begins after annotated `v1.8.0` and includes the governed
Operational Execution foundation plus the subsequently promoted MDPM, OIP, and
Shipment Economics slices, opaque Shipment identity and integrated
certification repairs, and PostgreSQL runtime-driver closure. These changes all
remain on the 1.9.0 lineage; `package.json` has not advanced beyond 1.9.0 and no
repository decision authorizes or requires an invented intermediate version.

Earlier Operational Execution, MDPM, OIP, Economics, and PR-4 manifests remain
immutable historical evidence for their bounded candidates. They do not claim
to be the final publication manifest.

## Identity and migration boundary

The final publication source is the publication-preparation commit containing
this record, not superseded candidate `9bef5ee` and not dependency-closure commit
`db29d4c`. After human review it is the only intended target for annotated tag
`v1.9.0`.

Production remains application 1.6.1 at `20260809_cargo_catalog_items`. The
package migration head is `20260818_immutable_fx_provenance` and the manifest
records every intervening revision and file hash. The deployment type is
backend-frontend-migration. Seed/catalog apply is false and excluded.

## Rehearsal and dependency closure

A restored clone of the actual Production database passed the complete upgrade,
reported current=head with no pending migrations, returned readiness HTTP 200,
and preserved sampled counts for shipment requests, expert users, and customers.
Production was not changed. A separate clean-venv rehearsal exposed the missing
psycopg2 declaration; `psycopg2-binary==2.9.11`, matching Production runtime,
closed it and is now verified in both package metadata and the release-local
environment.

## Rollback boundary

Application rollback points to the actually deployed 1.6.1 release, not merely
published 1.7/1.8 artifacts. Database rollback is conditional before durable
facts and becomes restore-required across Shipment Economics or consequential
immutable FX provenance. Recovery must coordinate PostgreSQL and document
storage.

## Publication sequence

1. Commit this bounded publication preparation.
2. Re-run source, regression, build, security, dependency, and cleanliness gates.
3. Obtain human publication/tag authorization.
4. Create annotated `v1.9.0` on the exact preparation commit.
5. Build the frontend and immutable package from that clean tagged checkout
   through `scripts/build_release_package.py`.
6. Run `VERIFY-PACKAGE.ps1`, inspect the package, and record its manifest/hash.
7. Push commit/tag or deploy only under separate explicit authority.

This review prepares publication only. It authorizes no tag, push, Production
access, deployment, migration, service change, Seed, or catalog apply.
