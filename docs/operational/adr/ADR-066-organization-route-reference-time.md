# ADR-066 — organization route reference time and explicit plan basis

- Status: ACCEPTED within the Product Owner's explicit P3-10 resume mission §§29–44.
- Date: 2026-09-26; LPAF v2.7 / rigor C; capability need Astra, not a runtime-model claim.
- Extends ADR-004/005/006/010/016/058; preserves ADR-054 SLA processes unchanged.
- Authority: P3-09-10-RESUME-AUTHORITY.md; Product Contract §19; approved UX §17.

## Entry, authority and decomposition

P3-09 Product `e499eb13fccc12734b21a09c1e2bfa1b92e983ee` and evidence/canonical
`e102ace12a741716442466d68140f632f1109bff` are integrated. Fresh github fetch
proved canonical clean, exact local/remote equality and 0/0. P3-01/P3-03 are
ancestors. New worktree `phase3-p3-10-route-reference-time` and branch
`codex/phase3-p3-10-route-reference-time` start at that actual canonical; P3-09
worktree remains preserved. Actual sole migration parent is
`20261008_phase3_cargo_delivery`. No historical migration is modified.

AUTHORIZED_PRODUCT_CHANGES: Organization Admin manages own route/mode reference
movement and stop ranges with effective/version history; Expert reads and explicitly
uses a reference as a planning basis; historical selection remains pinned.
DELEGATED_TECHNICAL_CHOICES: explicit domain persistence, UTC interval policy,
database integrity, same-tenant APIs, existing Persian UI, tests and authorized
qualified fast-forward integration. PROTECTED_OUT_OF_SCOPE_BEHAVIOR: all existing
Shipment/route/actual quantities, P3-01..09, SLA, accounts, Public Tracking, fixed
owner and historical evidence. DECISIONS_NEEDED: none within this bounded approval;
ETA confidence/algorithm DN04 remains outside scope. APPROVING_OWNER_OR_AUTHORITY:
Product Owner issuing the resume attachment; APPROVAL_REFERENCE: its §§29–44.

Work: domain/API and additive schema; Admin and Expert consumers; negative/history
and concurrency checks; exact-Product full backend/frontend, PG18 and Chrome;
reference reconciliation/evidence; clean controlled integration. No P3-11..15.

## Domain and effective history

OrganizationRouteTime owns an immutable directional key: organization, existing
CanonicalLocation endpoints with optional same-tenant LogisticsPoint identities,
and the already governed RouteLeg transport_mode vocabulary. The existing endpoint
resolver and stable location snapshots are reused; no new master data or seed.
Changing key means defining a distinct reference, not rewriting history.

OrganizationRouteTimeVersion is append-only. It stores separate optional movement
and stop/operation/wait pairs of integer elapsed minutes. At least one pair must
be supplied, each pair complete; movement positive, stop explicitly nonnegative,
minimum <= maximum, bounded at 525600 minutes. No average or combined duration.
Null means undefined, never zero. A version has actor, server recorded time and
aware effective_from. Values are exact inputs, not observed or predicted duration.

Versions increase monotonically, and effective starts strictly increase. An update
must be prospective (effective_from >= server now); the initial explicit effective
date may be historical. Validity is the derived half-open interval
[effective_from, next effective_from), with the last interval open-ended. No edit
to a previous row/end date is necessary. Future versions never overlap an earlier
version's applicable interval. Unique constraints, parent lock, expected version,
actor/payload-bound idempotency and PG trigger invariants protect concurrent writes.

## Plan consumption

The existing route page shows applicable reference separately from the plan's
chosen basis. Applicability uses planned departure when supplied, otherwise the
explicitly labelled current selection time. There is no inferred planned time.
The owning Expert may explicitly record a basis on a draft leg using existing
route_leg.manage authority. The command checks current leg version, selection
revision and the exact reference version the Expert reviewed before appending a
RouteLegTimeBasis row. Its immutable FK pins the version, time basis and exact leg
endpoint/mode/departure fingerprint. Replay returns the same selection.

Admin edits never modify a plan selection, planned timestamps or actual facts.
If an Expert subsequently edits the draft's key/departure, the earlier selection
stays in history and is visibly marked mismatched; an explicit fresh selection is
required to claim a matching basis. A new/replanned leg has no inherited selection
unless explicitly chosen. This adds no mandatory activation prerequisite and does
not change existing route commands or ETA/timeline reconciliation. Published plans
are read-only here. Missing applicable or selected reference is «تعریف نشده».

## Authority, compatibility and verification

Org Admin management derives one active tenant from the server; Expert, Customer,
Platform Admin and cross-tenant management deny. Expert reference use also requires
the existing fixed-owner Shipment/plan/leg boundary. IDs cannot grant authority.
No Customer/public DTO is expanded. No SLA process, commitment, ETA calculation,
distance provider, GPS, AI, lifecycle transition or automatic recomputation.

Three additive domain tables have tenant/parent FKs, immutable history, natural-key
uniqueness and indexes. Upgrade adds empty tables, no default/backfill. N-1 retains
its existing reads/writes; the new optional consumer is unavailable on N-1. Empty
downgrade/re-upgrade is safe; any recorded configuration/basis refuses downgrade
before DDL to prevent evidence loss. Production migration is not authorized.

DoD: ranges, missing reference, effective boundaries, stale/replayed/concurrent
commands, actor and tenant negatives, old/new basis, schema integrity and rollback;
normal Chrome Admin create/reopen → Expert select → future Admin update → old basis
unchanged and new planning sees new version; desktop/mobile and route/SLA/customer
regressions; all current references and exact-source evidence.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J06/J08/J09, FWD-IPJ-03/IPJ-04.
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING; INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN;
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN; RELEASE_READY=NO. Source freeze is not Product Freeze.
