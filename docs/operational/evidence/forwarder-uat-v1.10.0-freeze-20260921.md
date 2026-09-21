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
VERSION_IDENTITY_CONSISTENT=RESOLVED_AFTER_PACKAGE_BUILD
```

The UI version value is updated because the existing build already embeds and
exposes `package.json` through its governed release-identity surface; no new UI
version display was added.

## G. Source / Git Identity

```text
RELEASE_FREEZE_COMMIT=RESOLVED_AFTER_RELEASE_COMMIT
RELEASE_SOURCE_SHA=RESOLVED_AFTER_RELEASE_COMMIT
APPLICATION_COMMIT=RESOLVED_AFTER_RELEASE_COMMIT
FINAL_CANONICAL_SHA=RESOLVED_AFTER_EVIDENCE_COMMIT
```

The release source commit contains version metadata, source release manifest,
UAT package tooling, handoff, and this freeze record only. Accepted product
behavior is unchanged. A later commit may update only evidence/attestation.

## H. Release Tag / Target

```text
RELEASE_TAG=forwarder-uat-v1.10.0
TAG_TARGET_SHA=RESOLVED_AFTER_RELEASE_COMMIT
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
PACKAGE_FILENAME=RESOLVED_AFTER_PACKAGE_BUILD
PACKAGE_PATH=RESOLVED_AFTER_PACKAGE_BUILD
BUILD_DATE=RESOLVED_AFTER_PACKAGE_BUILD
FRONTEND_BUILD_ID=RESOLVED_AFTER_PACKAGE_BUILD
RUNTIME_ENTRYPOINT=START-UAT.ps1
```

## K. Package SHA / Inventory

```text
PACKAGE_SHA256=RESOLVED_AFTER_PACKAGE_BUILD
PACKAGE_SIZE=RESOLVED_AFTER_PACKAGE_BUILD
PACKAGE_INVENTORY=PACKAGE-INVENTORY.json + SHA256SUMS.txt
PACKAGE_IMMUTABLE=RESOLVED_AFTER_PACKAGE_BUILD
PACKAGE_SHA256_RECORDED=RESOLVED_AFTER_PACKAGE_BUILD
PACKAGE_SOURCE_SHA_VERIFIED=RESOLVED_AFTER_PACKAGE_BUILD
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
ENVIRONMENT_IDENTITY=RESOLVED_AFTER_PACKAGE_RUNTIME
RELEASE_SOURCE_SHA=RESOLVED_AFTER_RELEASE_COMMIT
DATABASE_HEAD=20260926_fixed_shipment_responsible_expert
BROWSER_RESULT=RESOLVED_AFTER_PACKAGE_RUNTIME
```

The browser is run against extracted package bytes through its actual
`START-UAT.ps1` runtime, not a source development server.

## O. Customer Smoke

`CUSTOMER_SMOKE=RESOLVED_AFTER_PACKAGE_RUNTIME`

## P. Expert Smoke

`EXPERT_SMOKE=RESOLVED_AFTER_PACKAGE_RUNTIME`

E1 must issue Quotes, own the resulting Shipment, use Documents/Tracking and
Control Tower. E2 must not gain that Shipment after Request assignment changes.

## Q. Admin/Manager Smoke

`ADMIN_MANAGER_SMOKE=RESOLVED_AFTER_PACKAGE_RUNTIME`

Admin/Manager oversight includes Control Tower, Shipment detail, and governed
read-only Documents with no forbidden mutation controls.

## R. Public Tracking Smoke

`PUBLIC_TRACKING_SMOKE=RESOLVED_AFTER_PACKAGE_RUNTIME`

Only a product-generated `SR2-` opaque capability may succeed. Numeric/internal
IDs fail and the public projection excludes Quote discussion, Documents,
internal IDs, and owner metadata.

## S. Documents / Quote / Control Tower Smoke

```text
DOCUMENTS_SMOKE=RESOLVED_AFTER_PACKAGE_RUNTIME
QUOTE_SMOKE=RESOLVED_AFTER_PACKAGE_RUNTIME
CONTROL_TOWER_SMOKE=RESOLVED_AFTER_PACKAGE_RUNTIME
```

## T. RTL / Mobile

`RTL_MOBILE_SMOKE=RESOLVED_AFTER_PACKAGE_RUNTIME`

Representative Persian/RTL desktop and mobile coverage must preserve readable
Gregorian (Jalali) dates with no blocking layout regression.

## U. Notifications Dormant

`NOTIFICATION_ACTIVATION_CHANGED=NO`

No provider, Email, SMS, Webhook, worker, or delivery activation is included.

## V. Reset / Rehearsal

The reset strategy drops and recreates only the owned `forwarder_uat_*`
database, clears only its owned document storage, reapplies migrations, and
reruns the approved fixtures. Manual row editing is prohibited.

`CUSTOMER_UAT_REHEARSAL=RESOLVED_AFTER_PACKAGE_RUNTIME`

## W. Release / Package / Version / Secret Checks

```text
SOURCE_RELEASE_TESTS=RESOLVED_AFTER_QUALIFICATION
ARCHITECTURE_SOURCE_CHECKS=RESOLVED_AFTER_QUALIFICATION
SECRET_SCAN=RESOLVED_AFTER_QUALIFICATION
PACKAGE_INVENTORY_VALIDATION=RESOLVED_AFTER_QUALIFICATION
SHA_VERIFICATION=RESOLVED_AFTER_QUALIFICATION
TAG_TARGET_VERIFICATION=RESOLVED_AFTER_TAG
```

## X. UAT Release Blocker Classification

Findings are classified as P0 UAT release blocker, P1 UAT release blocker, UAT
environment issue, post-UAT engineering, or maintenance. Product defects are
not repaired inside this freeze.

```text
P0_UAT_RELEASE_BLOCKER_COUNT=RESOLVED_AFTER_QUALIFICATION
P1_UAT_RELEASE_BLOCKER_COUNT=RESOLVED_AFTER_QUALIFICATION
```

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

`REFERENCE_IMPACT_FINAL=RESOLVED_AT_FINAL_RECHECK`

## AB. Verdict

`PENDING — PACKAGE BUILD, PACKAGE-BOUND QUALIFICATION, TAG, AND CANONICAL SYNC`

The final verdict is emitted only after exact package bytes and the frozen
runtime pass all required gates.
