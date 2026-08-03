# Forwarder 1.7.0 smoke test

## Public and cache

- Root and Command Center load; request and tracking routes refresh normally.
- Manifest-named JS/CSS assets return 200; no `/api/api` URL or stale asset reference occurs.
- HTML: `no-cache, no-store, must-revalidate`, `Pragma: no-cache`, `Expires: 0`.
- Hashed assets: `public, max-age=31536000, immutable`.
- Manifest/icons revalidate; `/api/*` is handled before SPA fallback and excluded from static cache rules.

## Backend and authentication

- `/api/health` returns 200 with database connected.
- A protected Logistics Network route returns 401 without a token, not 404.
- Admin: type and point list/create/update/lifecycle, governed geography, exact/probable duplicates.
- Project: select existing point, role, sequence, label, reorder, deactivate/reactivate; no free-text master creation.
- Unauthorized admin access is denied and foreign-tenant resources are not disclosed.

## Version and Seed

- Verify manifest/tag/commit and actual asset filenames. Version 1.7.0 is embedded but has no visible UI label.
- Basic health requires no Seed. LogisticsPointType-dependent flows require existing governed data or a separately authorized catalog apply.
