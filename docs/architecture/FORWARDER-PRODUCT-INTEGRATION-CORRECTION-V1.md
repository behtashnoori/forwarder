# Forwarder Product Integration Correction v1

Date: 2026-09-07

## Canonical role model

Authorization authority has exactly three canonical values: `PLATFORM_ADMIN`, `ORGANIZATION_ADMIN`, and `EXPERT`. The legacy `ExpertUser.role` column is compatibility data, not an authority source. Current organization user management creates only canonical Experts and presents authority labels rather than legacy role labels. Expert activity is represented only by `can_handle_domestic` and `can_handle_international`; these are scopes, not roles.

## Legacy role inventory and disposition

| Value/concept | Location | Classification | Disposition |
|---|---|---|---|
| `PLATFORM_ADMIN` | `ExpertUser.authority` | CANONICAL | Platform control plane; no tenant dashboard grant from authority alone |
| `ORGANIZATION_ADMIN` | `ExpertUser.authority` | CANONICAL | Tenant admin with one active membership |
| `EXPERT` | `ExpertUser.authority` | CANONICAL | Operational user; Domestic/International are attributes |
| `admin` | legacy `role`, scripts, old docs | LEGACY_PERSISTED | Retained for compatibility/history; never proves platform authority and is not selectable |
| `crm_manager`, `supervisor`, `business_expert` | legacy `role`, old docs/UI | LEGACY_PERSISTED | Retained without destructive remapping; canonical presentation comes from `authority`; not selectable |
| مدیر سیستم، مدیر CRM، سرپرست، کارشناس بازرگانی | legacy UI/docs | OBSOLETE_UI_ONLY | Removed from current user-management choices |

Persisted production values were not queried or changed by this local task. Any account with missing/unknown authority or ambiguous active memberships remains fail-closed and requires owner disposition; no role-name inference or destructive migration is authorized.

## Product-surface correction

- Personal Dashboard entitlement is `personal_dashboard.read/manage`, independent of Shipment data entitlement.
- `/dashboards` is the normal discovery/index route and supports intentional loading, error, empty, list, create, open, and edit states.
- Control Tower remains an optional template source. Its clone action needs both Control Tower reachability and dashboard manage; reopening a personal copy does not need Control Tower.
- Shipment widgets still execute through live Semantic Analytics authorization and cannot use a stored definition as a data grant.
- Shared authenticated navigation supplies safe «بازگشت» and persona-appropriate «خانه». Public, authentication, customer-public, tracking-public, and modal-only surfaces are deliberately excluded.

## Migration safety

Migration `20260916_personal_dashboard_permissions` targets active users with canonical `ORGANIZATION_ADMIN` or `EXPERT` authority and exactly one active membership. It preserves all existing permission values, excludes Platform Admin, inactive and ambiguous memberships, and records only newly introduced grants. Downgrade removes only those recorded grants.

## Qualification status — 2026-09-08

- Full frontend qualification: 47 test files and 210 tests passed; build passed; lint reported zero errors and 13 pre-existing warnings.
- Full backend qualification after the corrective fixes: 994 passed, 92 skipped, 1 xfailed, and zero failed. The focused OpenAPI/API route contract suite also passed 19 tests and parsed the checked-in OpenAPI document successfully.
- Disposable PostgreSQL validation exposed and corrected an invalid SQLAlchemy auto-correlation in the new migration. Upgrade from `20260915_project_access_foundation`, grant-scope inspection, downgrade, and re-upgrade then passed on PostgreSQL 17. Existing permissions survived downgrade; only migration-introduced grants were removed.
- The local Personal Analytics UAT fixture was corrected to store bcrypt password hashes and to create explicit tenant-owned Customer roots. Provisioning and authenticated dashboard-list API access then passed on the disposable PostgreSQL database.
- A repository-local Playwright qualification harness now runs against an explicitly supplied disposable PostgreSQL database and launches the installed Chrome channel. All six authenticated browser journeys passed: personal dashboard lifecycle, dashboard-only authorization, Control Tower copy, Saved View snapshot rendering, canonical administration UI, and navigation/fallback behavior. The harness captured no page errors, failed requests, unexpected responses, or console errors in the final run.
- The previous `ERR_BLOCKED_BY_CLIENT` was isolated to the controlled-browser/client environment, not the application: the same local Vite and Flask origins were reachable from Playwright-launched Chrome. Playwright's bundled-browser download was unavailable from this environment, so the harness uses the installed Chrome channel without changing application behavior.
- Browser qualification exposed two separate application defects that were corrected and regression-covered: dashboard-only users could not load non-sensitive Semantic Registry metadata, and Saved View ROWSET snapshots using semantic contract v2 could not render. Semantic Registry access now accepts either dashboard-read or Shipment-read capability, while Analytics query execution remains Shipment-read protected.
- The checked-in OpenAPI file is authoritative documentation for its declared public endpoints, but it is not the project's sole or exhaustive contract source. Qualification therefore cross-checks it with Flask route registration, the centralized typed frontend client, and contract tests. The corrective dashboard, Saved View snapshot, and Semantic Registry routes and methods are aligned; no endpoint removal, rename, or payload drift was found.

`ARCHITECTURE_GAP_STATUS = CLOSED`. Migration safety, authenticated browser acceptance, API-route alignment, frontend/backend regressions, build, and lint gates are all satisfied for the bounded corrective slice.
