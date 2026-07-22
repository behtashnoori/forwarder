# ADR-015: Repository secret scanning

## Status

Accepted

## Decision

Tracked files and pull requests must pass a redacted secret scan. Real credentials are forbidden in source, fixtures, documentation, and examples. Scanner output may contain only metadata and non-reversible fingerprint prefixes.

## Operational controls

The CI job uses read-only repository permission, no production secrets, no deployment, a bounded timeout, and no report artifacts. Full-history scans are operator-run because known rotated material can remain reachable until a separately authorized history decision is executed.
