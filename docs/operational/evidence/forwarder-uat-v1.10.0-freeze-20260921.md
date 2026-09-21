# New Forwarder UAT Version Freeze — Forwarder UAT v1.10.0

## A. LPAF Governance Gate

Active baseline: LPAF v2.2 and its mandatory Agent Entry Protocol. The reviewed
LPAF v2.3 Product Integration and `REFERENCE_IMPACT` controls are applied as a
strong default; v2.4 is not adopted. Rigor is Level B — Product/Release.

Mission: create one immutable, reproducible, versioned Forwarder UAT release
for the Customer session. Release owner: the Forwarder release authority.
Outcome: a package-bound UAT release, browser qualification, rehearsal, tag,
operator handoff, and exact-byte evidence. Product/reference source of truth:
the active LPAF tree and current Forwarder product references. Product version
source of truth: `package.json` plus the equal `backend.__version__` assertion.

Actors are Customer, Transport Expert E1, Transport Expert E2, Admin/Manager,
and Public Tracking visitor. Data scope is synthetic, owned, disposable UAT
data only. API, database, package, runtime, recovery, acceptance, and blocker
contracts are the current repository contracts and this freeze record.

Facts: the accepted baseline and remote canonical were equal and clean before
change. Assumption: the approved, checksum-pinned Windows runtime remains a
valid dependency carrier; package qualification verifies it. Unknowns become
blockers rather than guessed values. Human-reserved Production decisions are
outside authority.

`REFERENCE_IMPACT=NONE`: the release changes version/release identity, UAT
packaging, handoff, and evidence only. It does not change Product/reference
truth or accepted behavior.

## B. Accepted Product Baseline

`ACCEPTED_PRODUCT_BASE_SHA=a742628293359379cb476b782a2fe27e61a8db1f`

The canonical branch was `integration/golden-controlled`; fetched remote
`github/integration/golden-controlled` resolved to the same SHA with
`AHEAD_BEHIND=0/0` and a clean worktree. The historical immutable baseline tag
`golden-controlled-customer-demo-acceptance-final-20260921` is referenced only
as its exact historical identifier; it is not the name of this release.

The Final Product Acceptance evidence records PASS, zero required pre-release
feature gaps, zero P0/P1 blockers, and an established behavioral freeze.

## C. Version Discovery Sources

- `package.json` and `package-lock.json` recorded `1.9.5.1`.
- `backend.__version__` recorded `1.9.5.1` and the repository consistency test
  required equality with `package.json`.
- Git history records `1.9.3.1` and `1.9.5.1` as bounded hotfix identities.
- Repository release history advances feature releases through `1.6.0`,
  `1.7.0`, `1.8.0`, `1.9.0`, and later product releases.
- Release notes and reviews call the repository convention SemVer and use a
  MINOR increment for a new accepted product capability release.
- Product release tags use a `v` formatting prefix; the new UAT stage adds the
  governed `forwarder-uat-` stage qualifier.

## D. Previous Product Version

`PREVIOUS_PRODUCT_VERSION=1.9.5.1`

## E. New Product Version and Policy Decision

`NEW_PRODUCT_VERSION=1.10.0`

`VERSION_SOURCE_OF_TRUTH=package.json + backend.__version__ equality gate`

`VERSION_POLICY_APPLIED=Repository SemVer; next accepted capability release advances MINOR and resets subordinate components`

The new accepted product baseline contains multiple qualified capabilities
after `1.9.5.1`; it is not a hotfix of that release. The immediate governed
feature-release successor is therefore `1.10.0`. No existing tag or metadata
reuses that identity.

```text
VERSION_NUMBER_INVENTED=NO
VERSION_NUMBER_SKIPPED=NO
VERSION_CONFLICT_COUNT=0
```

## F. Release Identity

```text
PRODUCT_NAME=Forwarder
RELEASE_STAGE=UAT
RELEASE_ID=Forwarder-UAT-v1.10.0
RELEASE_TAG=forwarder-uat-v1.10.0
MANIFEST_VERSION=1.10.0
PACKAGE_VERSION=1.10.0
RELEASE_METADATA_VERSION=1.10.0
TAG_VERSION=1.10.0
UI_VERSION=1.10.0
VERSION_IDENTITY_CONSISTENT=YES
```

The UI version value is updated because the existing build already embeds and
exposes `package.json` through its governed release-identity surface; no new UI
version display was added.

## G. Source / Git Identity

```text
RELEASE_FREEZE_COMMIT=e36ee7cee157657c97dc42a539eaf1909f510a33
RELEASE_SOURCE_SHA=e36ee7cee157657c97dc42a539eaf1909f510a33
APPLICATION_COMMIT=e36ee7cee157657c97dc42a539eaf1909f510a33
FINAL_CANONICAL_SHA=SELF
```

The release source commit contains version metadata, source release manifest,
UAT package tooling, handoff, and this freeze record only. Accepted product
behavior is unchanged. A later commit may update only evidence/attestation.
`SELF` denotes the evidence-only commit containing this final attestation; its
exact resolved SHA is reported after commit and canonical synchronization.

## H. Release Tag / Target

```text
RELEASE_TAG=forwarder-uat-v1.10.0
TAG_TARGET_SHA=e36ee7cee157657c97dc42a539eaf1909f510a33
```

The annotated tag remains on the exact package source commit.

## I. Database Head

```text
DATABASE_HEAD=20260926_fixed_shipment_responsible_expert
ALEMBIC_HEAD_COUNT=1
```

Qualification uses only owned disposable loopback PostgreSQL 18 databases.
The supported migration path, current/check, no-pending, and one-head gates are
recorded after package qualification. The fixed-owner migration remains
fail-closed; it is not weakened for UAT.

## J. Package Build

The source-contained `scripts/build_forwarder_uat_release.py` extends the
repository's approved immutable ZIP, checksum catalog, governed Windows
runtime, manifest, clean-commit, extracted-package verification, and secret
scan patterns. It removes old pinned Product/Production candidate identities
and builds only this non-Production UAT release from the clean release commit.

```text
PACKAGE_FILENAME=Forwarder-UAT-v1.10.0-e36ee7cee157.zip
PACKAGE_PATH=D:\1-webapp\forwarder-uat-releases\Forwarder-UAT-v1.10.0-e36ee7cee157.zip
BUILD_DATE=2026-09-21T18:00:41.965149+00:00
FRONTEND_BUILD_ID=e5a90e80d5344253
RUNTIME_ENTRYPOINT=START-UAT.ps1
```

## K. Package SHA / Inventory

```text
PACKAGE_SHA256=3b07ed63d0b2634c84ecaff373b0708322b28c83033862615046b3a1c8d2d5ba
PACKAGE_SIZE=23351536
PACKAGE_INVENTORY=PACKAGE-INVENTORY.json + SHA256SUMS.txt
PACKAGE_IMMUTABLE=YES
PACKAGE_SHA256_RECORDED=YES
PACKAGE_SOURCE_SHA_VERIFIED=YES
```

The package excludes virtual environments, `node_modules`, local databases,
temporary test data, screenshots, secrets, Production configuration, and
developer caches. It contains the exact frozen backend/contracts, built
frontend, checksum-pinned Windows runtime, release manifest, verifier, and
bounded UAT start/stop gateway.

## L. UAT Data / Personas

Only deterministic synthetic data is used. Personas are Customer, Transport
Expert E1, Transport Expert E2, Admin/Manager, and Public Tracking visitor.
The approved fixture runners create runtime-only credentials and record only
persona usernames/identifiers in an owned local fixture file. Operators obtain
the generated password from the invoking UAT session; no secret is committed
or copied into evidence.

Representative data covers zero and multiple Cargo, Combined Transport,
official/revised/accepted/rejected Quote paths, fixed-owner Shipment,
Documents/history, tracking/events, private logistics points where applicable,
Control Tower, opaque Public Tracking, and Dual Calendar presentation.

## M. Customer Storyboard

The product-oriented order is Request, transport intent and optional Cargo,
official Quote, Needs Discussion, Expert message review, revised official
Quote, Customer acceptance, resulting Shipment and fixed owner, Documents,
tracking timeline, Control Tower and Shipment drilldown, opaque Public
Tracking, and Gregorian (Jalali) presentation. The operator handoff contains
the executable short form.

## N. Frozen Release Runtime

```text
ENVIRONMENT_IDENTITY=owned loopback PostgreSQL 18 + Forwarder-UAT-v1.10.0-e36ee7cee157 package bytes
RELEASE_SOURCE_SHA=e36ee7cee157657c97dc42a539eaf1909f510a33
DATABASE_HEAD=20260926_fixed_shipment_responsible_expert
BROWSER_RESULT=PASS
```

The actual `START-UAT.ps1` launcher was qualified on the owned
`forwarder_uat_release_e36ee7c` database at backend `5110` and gateway `8110`;
health and frontend returned success, and `STOP-UAT.ps1` stopped both ports.
Browser cohorts then used the same extracted package's bundled Python runtime,
Waitress backend, built `dist`, and `uat_gateway.py` on those ports. The source
tree supplied only safety-scoped test drivers and deterministic fixture setup;
no source development server served the application.

## O. Customer Smoke

`CUSTOMER_SMOKE=PASS`

## P. Expert Smoke

`EXPERT_SMOKE=PASS`

E1 must issue Quotes, own the resulting Shipment, use Documents/Tracking and
Control Tower. E2 must not gain that Shipment after Request assignment changes.

## Q. Admin/Manager Smoke

`ADMIN_MANAGER_SMOKE=PASS`

Admin/Manager oversight includes Control Tower, Shipment detail, and governed
read-only Documents with no forbidden mutation controls.

## R. Public Tracking Smoke

`PUBLIC_TRACKING_SMOKE=PASS`

Only a product-generated `SR2-` opaque capability may succeed. Numeric/internal
IDs fail and the public projection excludes Quote discussion, Documents,
internal IDs, and owner metadata.

## S. Documents / Quote / Control Tower Smoke

```text
DOCUMENTS_SMOKE=PASS
QUOTE_SMOKE=PASS
CONTROL_TOWER_SMOKE=PASS
```

## T. RTL / Mobile

`RTL_MOBILE_SMOKE=PASS`

Representative Persian/RTL desktop and mobile coverage must preserve readable
Gregorian (Jalali) dates with no blocking layout regression.

## U. Notifications Dormant

`NOTIFICATION_ACTIVATION_CHANGED=NO`

No provider, Email, SMS, Webhook, worker, or delivery activation is included.

## V. Reset / Rehearsal

The reset strategy drops and recreates only the owned `forwarder_uat_*`
database, clears only its owned document storage, reapplies migrations, and
reruns the approved fixtures. Manual row editing is prohibited.

`CUSTOMER_UAT_REHEARSAL=PASS`

One complete package-bound scripted rehearsal campaign followed the Customer
story across the deterministic fixed-owner, Quote, Documents, Combined
Transport, Cargo, and opaque Public Tracking cohorts. The campaign used fresh
owned databases, scripted fixtures, and 19 passing browser tests; no manual
database row editing was used.

## W. Release / Package / Version / Secret Checks

```text
SOURCE_RELEASE_TESTS=PASS (78 release/source/package tests; 8 focused metadata/builder tests)
FULL_BACKEND_TESTS=PASS (1333 passed, 106 skipped)
FULL_FRONTEND_TESTS=PASS (72 files, 357 tests)
TYPESCRIPT=PASS (zero diagnostics)
ESLINT=PASS (zero errors, 13 existing warnings)
PRODUCTION_FRONTEND_BUILD=PASS (2547 modules; existing advisories only)
ARCHITECTURE_SOURCE_CHECKS=PASS
SECRET_SCAN=PASS
PACKAGE_INVENTORY_VALIDATION=PASS
SHA_VERIFICATION=PASS
TAG_TARGET_VERIFICATION=PASS
```

## X. UAT Release Blocker Classification

Findings are classified as P0 UAT release blocker, P1 UAT release blocker, UAT
environment issue, post-UAT engineering, or maintenance. Product defects are
not repaired inside this freeze.

```text
P0_UAT_RELEASE_BLOCKER_COUNT=0
P1_UAT_RELEASE_BLOCKER_COUNT=0
```

Two qualification interruptions were classified as UAT fixture issues: the
Request Cargo browser database initially lacked its exact governed UOM fixture,
and a clean rerun initially omitted its transport/location fixture. The owned
database was recreated and seeded through deterministic scripts; the complete
Cargo cohort then passed `3/3`. No product change or blocker resulted.

## Y. Operator Handoff

`docs/operational/Forwarder-UAT-v1.10.0-handoff.md`

It records identity, package/checksum, database head, start/stop, loopback URL,
personas, credential-provisioning method, storyboard, reset, and deferrals
without secrets.

## Z. Deferred Engineering

Modular Architecture Assessment, Staged Modularization, notification
activation, Mandatory Cargo, generalized Customer Documents, exactly-once
Document upload recovery, retention/purge/DMS, personalized dashboards,
extended public-tracking hardening, and Production migration adjudication remain
separately governed work.

## AA. Reference Re-check

Final Product Acceptance, MT-3 closure, ADR-047 closure, the current Forwarder
Architecture Baseline, Architecture Drift Report, version sources, release
history, package patterns, LPAF v2.2, and reviewed v2.3 controls are re-read
before verdict.

The active LPAF v2.2 framework and entry protocol, reviewed v2.3 controls,
Final Product Acceptance evidence, MT-3 closure, ADR-047 closure, Forwarder
Architecture Baseline, Architecture Drift Report, version sources, current
package tooling, and release-tag history were re-read immediately before this
verdict. No Product/reference truth change is required.

`REFERENCE_IMPACT_FINAL=NONE`

## AB. Verdict

`PASS — NEW FORWARDER UAT VERSION FROZEN`

```text
FORWARDER_UAT_VERSION_STATUS=FROZEN
UAT_RELEASE_READINESS=READY
PREVIOUS_PRODUCT_VERSION=1.9.5.1
NEW_PRODUCT_VERSION=1.10.0
VERSION_SOURCE_OF_TRUTH=package.json + backend.__version__ equality gate
VERSION_POLICY_APPLIED=Repository SemVer; next accepted capability release advances MINOR and resets subordinate components
VERSION_NUMBER_INVENTED=NO
VERSION_NUMBER_SKIPPED=NO
VERSION_CONFLICT_COUNT=0
VERSION_IDENTITY_CONSISTENT=YES
ACCEPTED_PRODUCT_BASE_SHA=a742628293359379cb476b782a2fe27e61a8db1f
RELEASE_FREEZE_COMMIT=e36ee7cee157657c97dc42a539eaf1909f510a33
RELEASE_SOURCE_SHA=e36ee7cee157657c97dc42a539eaf1909f510a33
FINAL_CANONICAL_SHA=SELF
RELEASE_TAG=forwarder-uat-v1.10.0
TAG_TARGET_SHA=e36ee7cee157657c97dc42a539eaf1909f510a33
DATABASE_HEAD=20260926_fixed_shipment_responsible_expert
ALEMBIC_HEAD_COUNT=1
BEHAVIORAL_FREEZE_BASELINE=PRESERVED
P0_UAT_RELEASE_BLOCKER_COUNT=0
P1_UAT_RELEASE_BLOCKER_COUNT=0
PACKAGE_IMMUTABLE=YES
PACKAGE_SHA256_RECORDED=YES
PACKAGE_SOURCE_SHA_VERIFIED=YES
FROZEN_RELEASE_RUNTIME_SMOKE=PASS
CUSTOMER_UAT_REHEARSAL=PASS
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
PRODUCTION_DEPLOYMENT_PERFORMED=NO
NOTIFICATION_ACTIVATION_CHANGED=NO
MODULARIZATION_STARTED=NO
DEFERRED_ENGINEERING_PRESERVED=YES
```
