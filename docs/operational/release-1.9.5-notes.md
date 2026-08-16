# Forwarder v1.9.5 release notes

Forwarder v1.9.5 adds exact Organization hostname routing and runtime tenant fencing for automatic referral assignment.

- Active normalized hostnames resolve public submissions to one active Organization; unknown or inactive mappings remain unowned `INTAKE`.
- Tenant-bound referrals consider only active experts with exactly one active operational membership in the request Organization, an active Organization, and current role/capability eligibility.
- Direct rules, pool candidates, global fallback, and the final assignment write are independently fenced.
- Stale, inactive, duplicate-membership, and cross-tenant expert references fail closed; stopped rules leave the request unassigned.
- Alembic revision `20260827_org_hostname` is additive and creates no mappings, ownership records, or backfill.

This release does not create the Samand hostname mapping, modify DNS/IIS/TLS, deploy, seed, backfill, or access Production.
