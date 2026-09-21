# MT-3 Public Tracking Identity / Authorization Security Closure

- Date: 2026-09-21
- Starting canonical SHA: `7573cf7684804be564394316286ef4af23d8f394`
- Remediation branch: `codex/mt3-public-tracking-security-closure`
- Design/reference commit: `cf54a4b460116b74dfd18fe10b0ba8b31a1c8b29`
- Product/security commit: `34e96df2237b5ab16be445ac5adb917e6bc307f4`
- Governing decision: ADR-052

## A. LPAF Governance Gate

The mission was governed by LPAF v2.2, with v2.3 Product Integration and
`REFERENCE_IMPACT` applied as the Forwarder strong default. LPAF v2.4 was not
adopted and no generic LPAF files were changed.

- **Mission/outcome:** remove internal numeric database identity from the
  unauthenticated Request tracking authority boundary while preserving valid
  public tracking.
- **Scope/capability owner:** Customer Portal / Public Request Tracking; no
  Product Acceptance continuation, deployment, modularization, production
  access, Notification activation, or public-data expansion.
- **System and state of record:** `ShipmentRequest` and its governed ownership
  envelope; existing customer-visible unit tracking remains its bounded child
  projection.
- **Public actor/authority:** anonymous customer holding one exact versioned
  high-entropy bearer capability. The caller supplies no tenant, organization,
  Request, Shipment, or database identity.
- **Tenant/data scope:** the backend derives the Request's `TENANT` or governed
  `INTAKE` ownership and applies the current authority/quarantine check.
- **Resource identity:** `SR2-<22 base64url characters>`, generated from 16
  cryptographically secure random bytes.
- **Journey/reachability:** Command Center entry and
  `/customer/track/:requestCapability` reach the same public API boundary.
- **Upstream/downstream:** Request intake issues the capability; public API and
  UI consume only it; authenticated internal identity contracts are unchanged.
- **Module/public contract:** tracking route/service plus minimized DTO and
  public page; Project tracking remains a separate authority.
- **API/schema/compatibility:** breaking security correction for unsafe numeric
  and legacy Request links; no schema change or backfill.
- **Security/non-disclosure:** exact capability validation precedes lookup;
  invalid numeric, UUID, malformed, legacy, and unknown inputs share one 404
  envelope and restrictive cache/referrer/indexing policy.
- **Acceptance/negative authorization/release blocker:** the focused,
  PostgreSQL, browser, full-regression, and reference gates below are binding;
  any numeric resolution or private-field disclosure is a P0 failure.

Initial reference assessment was `UPDATE_REQUIRED`. ADR-052 and the affected
architecture, product, catalog, OpenAPI, inventory, and drift references were
reconciled before PASS.

## B. P0 Finding

The pre-MT-3 public service treated a decimal path value as
`ShipmentRequest.id`, and also accepted weak or historical Request tracking
codes. That made an enumerable internal primary key public authority and the
former response disclosed substantially more data than tracking required.

## C. Existing Unsafe Public Path

The removed path was:

```text
GET /api/public/track/<decimal>
-> ShipmentRequest.id == <decimal>
-> broad public serialization
```

Changing only frontend links would not have closed the defect, so the backend
numeric branch and weak-code acceptance were removed at the resolver boundary.

## D. Canonical Public Authority

The one Request-route authority is:

```text
SR2-<22 base64url characters>
```

It carries 128 random bits and has no deterministic or ID-derived fallback.
The existing unique `tracking_code` index supplies collision protection. Exact
shape validation occurs before database lookup.

## E. Numeric ID Removal / Fencing

Decimal values, signed/zero-padded numeric forms, known Request IDs, known
Shipment IDs, authenticated Request UUIDs, malformed inputs, unknown
capabilities, and legacy weak codes do not enter an ID lookup. They receive the
same status and public envelope. Authenticated internal resource lookups were
not changed.

## F. Tenant / Resource Resolution

The accepted order is:

```text
validate exact capability
-> exact unique Request tracking_code lookup
-> derive Request TENANT or governed INTAKE ownership server-side
-> apply current-authority/quarantine validation
-> emit the fixed public allowlist
```

There is no caller-controlled tenant/resource combination and therefore no way
to combine one valid capability with another resource's numeric identity.

## G. Public Projection / Data Minimization

The fixed allowlist contains only the opaque tracking number, commercial
status, creation time, shipping type, bounded route geography labels,
transport-intent presentation, assignment time, simple public workflow, and
the already customer-visible unit-tracking projection.

The response excludes database/tenant IDs, Customer identity/contact, exact
addresses, Cargo/value/instructions, Expert identity/contact, last-touch
metadata, Quote/history/discussion, Documents/storage/history, internal notes,
Notification state, and internal provenance. Both success and not-found use
`Cache-Control: no-store`, `Referrer-Policy: no-referrer`, and no-index policy.

## H. Legacy Compatibility

Unsafe compatibility was rejected. Numeric and legacy weak Request links fail
closed and are not redirected, translated, or tenant-guessed. Newly submitted
Requests receive the `SR2-` capability. Project public tracking and
authenticated internal resource lookup are unchanged and separately governed.

## I. Schema Decision

`ShipmentRequest.tracking_code` is already unique, indexed, nullable for
historical rows, and wide enough. Automatically backfilling historical rows
would grant public access without business authority and was not performed.

```text
MT3_SCHEMA_DECISION=NO_SCHEMA_CHANGE_REQUIRED
```

## J. Migration if Applicable

No migration was created. The graph remains exactly one head:

```text
ALEMBIC_HEAD_COUNT=1
ALEMBIC_HEAD=20260925_quote_communication
```

The disposable PostgreSQL qualification migrated from an empty database to
that existing head.

## K. Enumeration / IDOR Tests

`backend/tests/test_public_tracking_security.py` makes numeric lookup
reintroduction an explicit regression failure. It covers representative probes
including `1`, `2`, `3`, `10`, `100`, and `9999`; known same-tenant,
foreign-tenant, Request, and Shipment identities; malformed/unknown values;
exact-resource resolution; payload allowlisting; secure generation; and
uniform non-disclosure.

```text
NUMERIC_ENUMERATION_SUCCESS_COUNT=0
```

## L. PostgreSQL Evidence

The owned runner created a fresh local PostgreSQL 18 cluster under a generated
temporary directory, generated an ephemeral application secret, migrated from
zero to the canonical head, seeded two ownership scopes and known numeric
identities, ran the PostgreSQL security contract, and removed its runtime.

```text
MT3_POSTGRESQL_VERSION=18
MT3_ALEMBIC_HEAD=20260925_quote_communication
POSTGRESQL_SECURITY_TEST=1 passed
MT3_E2E_CLEANUP=PASS
```

No Production, shared UAT, or user development database was used.

## M. Browser Evidence

The real Vite frontend, real backend, PostgreSQL 18 data, and Chrome completed
four Playwright tests covering all five mandated journeys:

- valid opaque tracking on desktop RTL, including safe timeline, Dual Calendar,
  and Combined Transport presentation;
- guessed and known foreign numeric identity on mobile RTL with the same safe
  unavailable presentation;
- adjacent sequential enumeration with zero successful disclosures; and
- live public intake producing an `SR2-` link that opened successfully.

Result: `4 passed`; `MT3_BROWSER_QUALIFICATION=PASS`. The local run retained
three screenshots under
`test-results/mt3-public-tracking-security-e6846997194849f693531b6235e236a9`.
No unexpected console, page, or network errors were accepted by the spec.

## N. Link / QR Producers

Repository-wide producer inventory found the Command Center/LocationForm
navigation and Request intake response as the active Request link producers.
They now require/use the opaque capability and contain no numeric fallback.
No current QR producer was found. Dormant email/Notification delivery was not
activated. Journey E proves the live product-generated link.

## O. Cross-Capability Regression

The change preserves Customer-visible unit events, the four-step workflow,
Dual Calendar presentation, and Request-intent versus actual-route mode
separation. It removes Quote/Customer/Expert/Cargo data from the public DTO and
does not alter Quote commands, Documents, Cargo optionality, fixed Expert
ownership, Control Tower, or dormant Notifications. The retired tracking
creation/add-unit actions remain absent.

## P. Full Regression

All runtime suites were bound to product/security commit
`34e96df2237b5ab16be445ac5adb917e6bc307f4`. Subsequent changes in the closure
commit are reference/evidence-only, and the release/source/package/architecture
cohort was rerun after those documentation changes.

| Gate | Result |
|---|---|
| Focused public/security/Request suite | `48 passed` |
| Final focused security/reference/quote/timeline recheck | `58 passed` |
| Broader focused backend cohort | `103 passed, 6 skipped` |
| Full backend | `1336 passed, 102 skipped`, zero failures/xfail |
| Focused frontend | `3 files, 17 tests passed` |
| Full frontend | `72 files, 357 tests passed` |
| TypeScript | PASS |
| ESLint | PASS, zero errors; 13 pre-existing warnings |
| Production build | PASS; only existing browser-data/bundle-size advisories |
| Release/source/package/architecture cohort | `89 passed` |
| Python compile/determinism/repository structure | PASS |
| Diff whitespace validation | PASS; line-ending notices only |

## Q. Reference Re-check

Immediately before closure, the active LPAF v2.2 entry/framework and v2.3
Product Integration governance were reread, followed by ADR-052, tracking
authority, architecture baseline, FDD/FDM, Canonical Business Object Catalog,
Golden journeys, architecture drift report, MT-0 contract/plan, and the failed
Final Product Acceptance finding.

The reconciliation updates ADR-052 status and residual-risk wording; replaces
pre-MT-3 “current defect” statements in the MT-0 contract/plan; updates the
drift ledger to implemented/qualified; amends the Command Center consequence;
aligns the tracking authority matrix and catalog; and aligns OpenAPI and the
tenant ownership inventory. FDD-001 already carried the accepted `SR2-`
contract; FDM, architecture baseline, and Golden journeys required no change.

```text
REFERENCE_IMPACT_FINAL=NONE
```

## R. Release Blocker Closure

The P0 blocker is closed because internal numeric identity cannot reach a
public lookup, the only accepted Request authority is a high-entropy capability,
ownership is derived server-side, the response is minimized, and the negative
contract is enforced in unit, PostgreSQL, and real-browser tests.

```text
MT3_STATUS=CLOSED
MT3_P0_RELEASE_BLOCKER=CLOSED

PUBLIC_TRACKING_NUMERIC_DB_ID_AUTHORITY=NO
PUBLIC_TRACKING_NUMERIC_ID_ACCEPTED=NO
PUBLIC_TRACKING_OPAQUE_AUTHORITY_REQUIRED=YES

NUMERIC_ENUMERATION_SUCCESS_COUNT=0

PUBLIC_TRACKING_CROSS_TENANT_DISCLOSURE=NO
PUBLIC_TRACKING_INTERNAL_DB_ID_DISCLOSURE=NO
```

## S. Remaining Security Risks

Generalized rate limiting, capability rotation/revocation/expiry, hashed-at-rest
capability storage, attempt auditing, and generic infrastructure access-log
redaction are not present. They are separately governed defense-in-depth work.
The separate Project public route and future branded/host-resolved portals are
also outside this bounded Request-route closure. None restores numeric public
authority or expands the Request projection.

```text
PUBLIC_TRACKING_BUSINESS_SEMANTICS_CHANGED=NO
PUBLIC_TRACKING_PUBLIC_DATA_SCOPE_EXPANDED=NO

RETIRED_TRACKING_ACTION_REINTRODUCED=NO

CARGO_OPTIONALITY_CHANGED=NO
DOCUMENTS_BEHAVIOR_CHANGED=NO
QUOTE_COMMUNICATION_BEHAVIOR_CHANGED=NO
DUAL_CALENDAR_BEHAVIOR_CHANGED=NO
COMBINED_TRANSPORT_BEHAVIOR_CHANGED=NO
CONTROL_TOWER_BEHAVIOR_CHANGED=NO
NOTIFICATION_ACTIVATION_CHANGED=NO
EXPERT_OWNERSHIP_CHANGED=NO

PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
DEPLOYMENT_PERFORMED=NO
SECRETS_ACCESSED=NO
```

## T. Verdict

PASS — MT-3 PUBLIC TRACKING SECURITY CLOSURE COMPLETE
