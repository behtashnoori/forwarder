# Forwarder 1.8.0 smoke test

## Public and cache

- Root loads and normal refresh works without Disable Cache; manifest-named JS/CSS return 200 with no stale references.
- HTML: `no-cache, no-store, must-revalidate`, `Pragma: no-cache`, `Expires: 0`.
- Hashed assets: `public, max-age=31536000, immutable`; manifest/icons revalidate.
- API rewrite precedes SPA fallback and API paths are excluded from static/SPA cache rules.

## Backend and authentication

- `/api/health` returns 200 with database connected.
- An unauthenticated protected Project Configuration route returns 401, not 404.
- Unauthorized configuration access is denied; cross-tenant data is not disclosed.

## Authenticated Project Configuration

- Services: list, create/update, primary/required flags, conflict behavior, activate/deactivate.
- Documents: governed `DocumentDefinition` selector; REQUIRED/OPTIONAL/CONDITIONAL; conditional description; create/update/lifecycle.
- Milestones: governed `MilestoneType` selector; sequence; duration; optional `ProjectLogisticsPoint`; reorder; lifecycle; no operational milestone auto-creation.
- Existing Project Logistics Network continues to work.
- Numeric `DocumentDefinition` IDs are absent from new API/UI payloads.

## Reference Data administration and version

- With an empty governed catalog, verify the administration page remains usable and an authorized administrator can create the first Reference Data record. Do not run or prompt for Seed/catalog apply; basic health must pass with zero records.
- Verify actual JS/CSS filenames. Version 1.8.0 is embedded in the build but is not visibly rendered in the UI.
