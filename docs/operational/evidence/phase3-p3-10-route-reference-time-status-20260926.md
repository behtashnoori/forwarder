# P3-10 — organization route reference time qualified

LPAF v2.7 / rigor C. Product Owner resume §§29–44 and ADR-066 authorize this bounded
extension. Entry canonical `e102ace12a741716442466d68140f632f1109bff` was the freshly aligned clean P3-09 integration.
Worktree and branch are independent; P3-09 work and historical evidence remain intact.

- Product SHA: `6d88c2a157e6d2ba81efa72d8bf0b4bcc779819d`. Source identity freeze is not global Product Freeze.
- Evidence SHA: this evidence-only descendant, identified exactly in the integration receipt.
- Branch: `codex/phase3-p3-10-route-reference-time`.
- Migration: `20261009_phase3_route_time`, actual parent `20261008_phase3_cargo_delivery`, one head.

## Product and authority

Organization Admin defines its own directional governed endpoints/mode reference.
Movement and stop/operation/wait have independent optional integer-minute ranges;
at least one complete pair is explicit, and null remains undefined. Existing
canonical locations, tenant LogisticsPoint identities and RouteLeg modes are reused.
No new geography master, default seed, backfill, assumed speed or duration is created.

Immutable versions retain old/new ranges, effective start, actor and recorded time.
Their derived intervals are [start,next-start). Updates are prospective and serialized
with expected version plus actor/payload-bound idempotency. Expert explicitly pins an
applicable version on its own draft leg. Admin changes cannot rewrite that selection,
planned timestamps, actual facts or quantities. Later draft edits visibly invalidate
the matching claim while retaining selection history. Published plans are read-only.
New planning explicitly selects the newer applicable version; no automatic rebinding.

Admin configuration is tenant-only. Expert cannot configure; Customer sessions confer
no access; disabled membership fails closed; Platform Admin has no implicit tenant
authority. Plan consumption preserves the existing fixed-owner permission boundary.
Five allowlisted API operations have strict documented response schemas and no-store.
This is reference input, neither OrganizationSlaRule/process commitment nor ETA.

## Fresh qualification of the exact Product

| Gate | Evidence |
| --- | --- |
| Full backend | 1490 passed, 118 environment-dependent skipped, 0 failures, 0 errors; 1404.541 seconds |
| Full frontend | 425 passed in 90 files |
| PostgreSQL 18 | 12 passes: P3-10 + P3-09/08/07/DN10/06, P3-01..05 and Public Tracking |
| Real Chrome | 13 tests: P3-10, P3-09, P3-03, P3-01, P3-08, P3-07, P3-06 and public security |
| Static | App/node TypeScript, lint, build, architecture, structure, backend determinism, diff and one-head checks PASS |
| Visual | Fresh desktop and 390px mobile, old pin/new applicable ranges, Admin version history and undefined state inspected; no horizontal overflow |

PostgreSQL proof upgrades existing prior-head synthetic data without rewriting it,
proves empty downgrade/re-upgrade, rejects populated destructive downgrade, denies
SQL history mutations/cross-tenant references, converges duplicate commands and
admits only one competing stale-version update. No historical migration was edited.

The Chrome positive path uses normal Admin/Expert login and Product UI; initial-draft
detail is opened by its ordinary authenticated URL as in existing P3-03 qualification,
because legacy list/Workspace populations intentionally require an active route envelope.
Admin saves/reopens Khorgos→Aktau Rail (20–24h movement, 4–8h stop); Expert pins v1;
Admin adds future v2 (25–30h movement); old plan remains v1 and new plan selects v2.
Undefined Road reference disables selection. Expert/foreign/Platform writes deny.
Full regressions cover existing route authoring, SLA, accounts, documents, deliveries,
Customer revocation and separate Public Tracking within recorded coverage.

Preliminary fixture/selector failures and the superseded two stale-head assertion
failures remain diagnostic in prior-attempts.json; they
are not final passes. Final Product and assertions were not changed during its runs.
All final local synthetic runtime resources stopped and were removed. Raw full-suite
logs/JUnit have absolute paths and hashes; selected logs, screenshots and manifests
are retained in the adjacent evidence directory. Existing warnings are disclosed.
One interrupted superseded run's synthetic temporary directory is retained because
automatic approval review rejected its deletion (blocked by policy). Its processes
and listeners are verified stopped; the exact path is recorded in prior-attempts.json.

## Reconciliation and boundary

AUTHORIZED: new reference/version/basis domain, APIs, Admin/Expert UI and additive
migration. DELEGATED: relational integrity, explicit pinning, elapsed-minute bounds,
prospective interval policy, locked/idempotent commands and test harness. PRESERVED:
Shipment SOR, Cargo, historical route timestamps, actual facts, SLA, existing account
and document permissions, Public Tracking, fixed Expert owner, P3-01..09 evidence.
No new reserved decision is required; DN04/ETA remains outside scope.

Architecture baseline, ADR index/066, tenant inventory, OpenAPI, implementation plan,
resume authority and ADR-016 surface ledger are reconciled. Twenty-six existing
current-head tests advance to the new exact head; historical parent checks remain.
PRODUCT_AUTHORITY_RECONCILIATION=PASS; REFERENCE_RECONCILIATION=PASS; REFERENCE_IMPACT=NONE.
Framework normative documents, Product Contract, Journey Pack and approved UX need
no behavior redefinition. This source-bound slice gate is not integrated Product or
human acceptance: GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING;
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN; HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN; RELEASE_READY=NO.

P3-11..15 have not started. No production access/data/secrets/migration, deployment,
release, authentication workaround or credential search. Only clean fast-forward
canonical integration and approved github branch push/fetch are authorized next.
