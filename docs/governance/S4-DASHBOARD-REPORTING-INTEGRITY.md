# S4 Dashboard / Reporting Integrity

## Authorized contract

ADR-044 records the ADR-043 companion decision. Organization Admin reporting
is server-derived from exactly one active membership; Platform Admin reporting
is platform-wide or narrowed by a validated `organization_public_id`; Experts
are denied. The request path is `AdminPanel` → `fetchAdminDashboard` →
`GET /api/admin/dashboard` → `admin_dashboard_service` over `ShipmentRequest`
and `Province`.

## Reproduction fixture and expected matrix

The S4 API fixture contains Organizations A, B, and an empty organization.
A has four requests: `new/road` at one hour, `assigned/air` at 25 hours,
international `won/sea` at six days without province, and `lost/road` at eight
days. B has `in_progress/rail` at two hours and international `closed/road` at
nine days without province. A therefore returns total 4; status counts 1 each;
transport `road=2, air=1, sea=1`; rolling 24 hours 1; rolling seven days 3;
unassigned 1; and Tehran 3. B returns 2, platform returns 6, and platform
filtered to A equals A exactly.

## Semantics and findings

Storage and calculations use naive UTC timestamps. Dashboard windows are rolling
24 hours and rolling seven 24-hour periods, not business-day periods. The UI
labels match those rolling windows. `top_provinces` intentionally counts only
requests with an origin Province: the inner join omits valid international or
null-province requests without changing any total, status, or transport metric.
Valid zero-data tenants receive HTTP 200 and zero/empty structures.

The prior HTTP 403 was `DOMAIN_BEHAVIOR_CORRECT` while the companion decision
was pending. S4 replaces that temporary gate with approved tenant/platform
enforcement. It also fixes `FRONTEND_ERROR_STATE_DEFECT`: failed dashboard
requests now render a retryable Persian error state rather than the valid-empty
state.

## Related reporting and residual risk

Overview, assignment summary, and XLSX export use the same authorization scope;
the service receives the derived context before querying or generating output.
No migration, data mutation, package change, or Production access is involved.
The dashboard uses several aggregate queries but has no per-row materialization
or N+1 loop. Future requirements for calendar-local reporting or a province
"unknown" bucket require a separate product decision.
