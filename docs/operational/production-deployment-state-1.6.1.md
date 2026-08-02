# Production Deployment State — Forwarder 1.6.1

- **Status:** Verified operational evidence record
- **Recorded:** 2026-08-02
- **Application release:** 1.6.1
- **Database head:** `20260809_cargo_catalog_items`
- **Production IIS path:** `C:\1-webapp\forwarder-production\release-v1.6.1-20260802`
- **Scope:** Factual deployment-state reconciliation only

## Verified evidence

| Check | Verified result |
| --- | --- |
| Production IIS release | `release-v1.6.1-20260802` |
| Application release | 1.6.1 exists in the deployed bundle |
| Database revision | `20260809_cargo_catalog_items` |
| Health endpoint | HTTP 200 |
| Cargo internal route without token | HTTP 401, confirming authentication boundary |
| Application-shell HTML caching | No-store/revalidation policy verified |
| Hashed asset caching | Immutable policy verified |
| Web manifest caching | Revalidation policy verified |

No secret, credential, connection string, or `DATABASE_URL` is recorded here.

## Backup evidence

- **Backup file:** `forwarder-before-v1.6.1-20260802-162204.dump`
- **SHA-256:** `4FDE95980C4FC4574C7822393C64D10EFAE24B7CCA045A15B750FF60585FBFFF`

This record preserves the supplied backup identity and checksum. It does not execute or independently restore the backup.

## Scheduled Task release binding

The Production Scheduled Task must reference the current release consistently in all three locations:

- WorkingDirectory
- `--repo`
- `PYTHONPATH`

A future release switch must update and verify all three; a mixed-release task configuration is invalid.

## Known limitations and exclusions

- Reference Data Seed was **not executed**.
- Application version metadata exists in the deployed bundle, but the UI does not currently display version 1.6.1 visibly.
- This record makes no claim that the UI visibly shows 1.6.1.
- This documentation closure performs no Production connection, change, seed, package, deployment, or Scheduled Task modification.
