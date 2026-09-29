# Route Reference country-only canonical geography apply

Date: 2026-09-29. Governing baseline: LPAF v2.7 (`ACTIVE / FROZEN /
CANONICAL`). Qualification rigor: C. Product SHA:
`645630b63110b2556b4dda3c589cd16d7150e3d9`.

## Authorized scope and implementation

The Product Owner authorized a governed `COUNTRY_ONLY` apply against the
approved FWD-02 catalog checksum
`sha256:b3e71f12f7c9cc8a9c5061a9df0ed67f085636bc84bd7120400694adab2d48ca`.
The implementation adds an explicit country-only plan/apply scope and keeps the
full catalog behavior unchanged. Country-only apply can insert only missing
exact ISO alpha-2 `Country` identities. It does not scan, map, update, reactivate,
or delete `InternationalCity` rows. The successful seed-run audit is committed
in the same database transaction as the Country inserts; a failed apply rolls
back those inserts and records a sanitized failed-run receipt separately.

The Route Reference location API now supports a canonical-only selector view.
New non-Iran Route References request that view, and the service rejects any
legacy `InternationalCity` without a matching country-prefixed UN/LOCODE.
Historical reads remain available. Geography type labels remain localized and
raw enum values are not rendered in the form.

## Plan/apply receipts

The pre-apply full plan proved 249 source countries, 12 existing countries, 237
missing countries, and 51 same-country legacy location-name conflicts. The
country-only plan was conflict-free because locations are outside that scope.

- First apply: `CHANGED`, 237 countries created, 12 unchanged, zero updated,
  zero conflicts. Audit run
  `61971c46-9c71-4a9f-aa0a-308daefbc6f3`, status `succeeded`.
- Second apply: `UNCHANGED`, zero created, 249 unchanged, zero updated, zero
  conflicts. Audit run `c971a68e-216f-4291-8e37-3b3542ca2f5f`, status
  `succeeded`.
- Post-plan: `UNCHANGED`, 249 countries, zero missing, zero conflicts.
- Integrity: zero duplicate codes and zero malformed Country codes.

The authorized catalog-conflict set is 51 rows. The preserved database contains
56 total rows with no UN/LOCODE; all 56 are excluded from new Route Reference
selection. Their complete-row fingerprint is identical before and after the
apply. No mapping package was inferred or created.

## Preserved walkthrough runtime

Before apply, a fresh PostgreSQL custom-format backup was written to
`D:\1-webapp\forwarder-human-walkthrough-runtime\pre-country-only-apply-20260929.dump`.
Its SHA-256 is
`1F9CEB3449FC1F4D7C6FE6F1AEC04C56683D370B94C8FB953F818B9B2A02BD92`.

Complete-row fingerprints were captured for every public table before apply,
after apply, and after the final runtime restart. Only these tables changed:

- `country`: 12 to 249;
- `reference_data_seed_run`: append-only governed audit receipts.

All other table counts and complete-row hashes are identical, including
`international_city`, `canonical_location`, Request, both Quotes, Shipment,
Cargo, RoutePlan, RouteLeg, ExecutionUnit, allocations, CRM, event/report
context, structured progress, Route Reference/version/basis, and ETA snapshots.
The existing cargo facts remain requested/planned 100, actual unknown, with
current PLANNED/ACTUAL allocations 100/95. Structured progress, Route Reference,
RouteLegTimeBasis and ETA_RULESET_V2 counts remain zero. Three older
ETA_RULESET_V1 snapshots remain unchanged.

The same preserved PostgreSQL 18 data directory was retained; it was not reset
or replaced. The runtime manifest records the Product SHA, checksum, both audit
run IDs, 249 active countries, 51 authorized conflicts, 56 total unbound legacy
rows, the backup identity, and `COUNTRY_ONLY_APPLIED_IDEMPOTENT`. Backend health
and readiness and the frontend returned 200. No Isfahan-to-Bandar Abbas Route
Reference was created.

## Exact-Product qualification

- Country-only focused backend: 5 passed.
- Route/ETA focused backend: 20 passed.
- Combined affected backend: 67 passed.
- Affected frontend: 5 files / 41 tests passed; Route Reference component: 7
  passed, including the canonical-only selector request and localized rendering.
- Full backend: 1,635 passed, 124 environment-gated skipped.
- Full frontend: 99 files / 475 tests passed.
- PostgreSQL 18 owned runtime: 9 Phase 3 tests, P3-01 through P3-05 (5 tests),
  and Public Tracking (1 test) passed; owned qualification cluster stopped.
- TypeScript, production build, architecture governance, repository structure,
  backend determinism, and diff checks passed.
- Lint passed with zero errors and 16 pre-existing warnings.

The live preserved runtime landing surface was also opened read-only after
restart; no credentials were entered and no form was submitted. Form behavior
is proven by the exact-Product frontend integration suite and backend selector
and service tests, while the live database and runtime checks prove the applied
249-country state.

## Governance disposition

Product validation evidence is complete for this authorized country-only apply.
Production was not accessed or mutated. No deployment or release occurred.
Human Product Walkthrough remains `IN_PROGRESS`; Release Ready remains `NO`.

Verdict: `PASS — COUNTRY-ONLY CANONICAL GEOGRAPHY APPLY COMPLETE — ROUTE
REFERENCE WALKTHROUGH READY`.
