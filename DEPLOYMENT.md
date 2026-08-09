# Forwarder 1.9.0 deployment preparation

This runbook prepares an authorized future deployment; it does not authorize
one. Production remains application 1.6.1 at database revision
`20260809_cargo_catalog_items`.

1. Verify the immutable package, annotated `v1.9.0` tag, source commit/tree,
   package hash, requirements hash, and ten migration hashes.
   Package secret verification permits only the byte-exact immutable 2024
   credential migration when the byte-exact mandatory remediation revision is
   present in this release's declared upgrade path; every other match fails.
2. Copy `release-v1.9.0-20260809` to a new immutable server directory.
3. Create a release-local `.venv` and install only `requirements.txt`; do not
   rely on global packages.
4. Run `VERIFY-PACKAGE.ps1`; confirm the release-local environment imports
   `psycopg2-binary 2.9.11` before any service switch.
5. Record current IIS and backend Scheduled Task paths without exposing secrets.
6. Confirm current Production revision `20260809_cargo_catalog_items`, database
   activity, storage capacity, and approved quiescence plan.
7. Take coordinated PostgreSQL and document-storage backups, record SHA-256
   evidence and custody, and complete the authorized restore-confidence gate.
8. Run migration `current` and `check`; review the exact ten-revision path in
   `MIGRATION-PREFLIGHT.md`.
9. During the authorized window, quiesce writes as approved and explicitly
   upgrade to `20260818_immutable_fx_provenance`.
10. Confirm current/head equality, `pending=no`, critical tables ready, and no
    missing tables before switching application processes.
11. Update the backend Scheduled Task WorkingDirectory, `--repo`, and
    `PYTHONPATH` consistently to the immutable 1.9.0 directory; restart only
    under separate deployment authority.
12. Verify local backend liveness/readiness and release-local driver identity.
13. Switch IIS to the immutable 1.9.0 directory and verify HTTPS, same-origin
    API routing, cache headers, frontend assets, and authenticated smoke tests.
14. Observe authentication, documents, Operational Execution, MDPM, OIP,
    Economics/FX, database, and storage signals through the approved window.
15. Capture all source, tag, package, backup, migration, smoke, operator, and
    timestamp evidence before release closure.

Reference Data and OIP policy/threshold initialization are separate authorized
administrator actions. No Seed or catalog apply occurs during package build,
migration, startup, health verification, or basic deployment acceptance.
