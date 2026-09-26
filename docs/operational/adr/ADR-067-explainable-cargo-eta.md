# ADR-067: Explainable Cargo ETA with immutable calculation snapshots

- Status: ACCEPTED
- Date: 2026-09-26
- Owners: Architecture; Operational Shipment/Route; Security; Data
- Affected domain: derived ETA, temporal provenance, Customer projection
- Product authority: [P3-11..13 mission](../../product/phase3/P3-11-13-MISSION-AUTHORITY.md), §§3–25 of its retained source
- Acceptance date: 2026-09-26
- Acceptance authority: Product Owner, explicit named acceptance with clarification in the [architecture acceptance mission](../../product/phase3/P3-11-13-ARCHITECTURE-ACCEPTANCE.md)
- Implementation authority: bounded P3-11 implementation authorized; qualification and controlled integration gates remain mandatory

## Context

At canonical `368cd736cbffce3d62c33336868738d9086e8306`, ADR-058 owns
RoutePlan/RouteLeg and RouteCargoDestination; ADR-063 owns scoped reports and
corrections; ADR-065 provides a live authorized private projection. ADR-066 owns
OrganizationRouteTimeVersion and immutable RouteLegTimeBasis selections.
`route_time_service.applicable` selects a version for an explicit instant;
changing that reference never rewrites a plan's selected basis.

The operational models also provide milestone occurrence and actual traversal.
P3-07 PROGRESS text alone is not a structured completed-stage fact; a LOCATION
report can be manual or structured. Existing route propagation is not itself an
approved Cargo ETA. No governed route distance source was found in the inspected
route/reference models and services. This is a bounded source finding, not a claim
that every repository file or external system lacks distance data.

## Problem

Add reproducible next/final estimates without creating a second route engine,
inventing progress, mixing Customer branches or rewriting source/reference history.
DN04 is already resolved. The new snapshot boundary and temporal input contract
require architecture acceptance before Build.

## Accepted decision

1. Keep all source SORs unchanged. Add a tenant/Shipment/Cargo-owned derived
   `CargoEtaSnapshot` and relational input references. A snapshot stores route
   revision, terminal branch, anchor identity/type/occurrence/record time, source
   revisions, per-segment reference-version IDs, next/final results or bounded
   unavailable reasons, calculation instant, `ETA_RULESET_V1`, and canonical input
   fingerprint. It is immutable history, not new operational truth or event sourcing.
2. Resolve the Cargo destination in the active governed RoutePlan; traverse only
   that destination's ancestor path using the existing route topology. Missing,
   cyclic, unrelated or revision-incompatible paths are unavailable. Do not fall
   back to another Cargo, newest ExecutionUnit or an obsolete plan.
3. Eligible anchors must prove both progress position and applicability to this
   Cargo/path. Use effective unsuperseded occurred-time facts from the existing
   milestone/actual-traversal contracts; a P3-07 structured location is usable only
   when its identity unambiguously resolves a relevant operational point and its
   context/participation proves this Cargo's progress. Free text and generic
   PROGRESS/EFFECT descriptions do not establish movement fractions or completion.
   Preserve multiple active execution contexts; a fact about only one split part
   cannot establish whole-Cargo progress. If no consistent whole-Cargo anchor is
   established, return an explicit unavailable result for that Cargo.
4. Select latest valid applicable occurrence, excluding corrected originals.
   Recorded time explains late entry and audit; it is never substituted for travel
   time. Equal-time incompatible progress is unavailable, not arbitrarily chosen.
   A newer ambiguous applicable observation must not be silently hidden behind an
   older reassuring estimate. Replan does not infer a mapping of old progress.
5. For each remaining fully identified stage, resolve currently applicable P3-10
   reference version at the captured calculation instant and pin it in the new
   estimate. This dynamic ETA basis is distinct from the immutable P3-10 planning
   selection, which remains readable and unchanged. Future effective versions
   cannot be consumed early; future recalculation may use a newer effective version.
6. Sum the required remaining movement and stop/operation ranges independently:
   lower = anchor occurred instant + sum(minima); upper = anchor occurred instant
   + sum(maxima). Include only operations not already proven complete. An absent
   required duration is unknown, never zero. A known movement endpoint does not
   prove a stop completed. Never prorate a stage by distance, location text or speed.
   Define the next point using the next applicable governed milestone/checkpoint
   on that path; final uses the Cargo's terminal destination. If a next target is
   ambiguous, label it unavailable. Evaluate the two paths independently, so a
   missing later reference can leave next available and final unavailable.
7. Current P3-07 effect text has no approved numeric-duration field. Do not parse
   it. Use only an existing duration with proven applicability, explicit source
   semantics and non-overlap with the anchor/reference interval; otherwise state
   that the effect is unquantified. An effect invalidating remaining-path meaning
   makes that estimate unavailable. No new hold input model is included here.
8. Compute on consistent source reads, using the existing aggregate lock order
   for source mutations and a single per-Cargo projection serialization point.
   The application/domain service explicitly exposes idempotent
   `ENSURE_CURRENT_ETA` (or `REFRESH_CURRENT_ETA`) for compare-and-append of a
   current derived snapshot. Historical/read lookup remains pure. The public
   Product may present an ordinary ETA read experience, but its endpoint/service
   contract must declare when it invokes ensure/recalculate; a generic pure GET
   must not silently acquire write semantics. Unrelated list/count queries must
   never trigger materialization. This is an internal architecture clarification,
   not a new Product capability or mandatory user action. Ensure cannot accept
   client-supplied results, durations, anchors or grants. Source fingerprint
   equality reuses the current snapshot; an A→B→A sequence appends the return to A
   rather than erasing the meaningful intervening B. Concurrent identical reads
   converge through compare-and-append under the lock. Recheck source identity and
   authorization before return; errors never return the previous estimate as current.
9. Historical pages remain bounded/paginated without deleting meaningful history.
   New reports, correction, applicable reference changes or path changes produce
   a new fingerprint even where the resulting range happens to be equal. Preserve
   old estimates and their exact source versions without backfilling estimates.

## Security/tenant impact

Composite tenant/Shipment/Cargo/route references fail closed. Internal reads use
current Shipment authority. Customer computation first applies live DN10 and
ADR-065 own-Cargo scope, then the existing safe location/branch gates. Private
anchor details cannot become an indirect Customer ETA input or explanation.
Customer output is a separate allowlist: own target, range, safe basis/as-of and
bounded missing reason; no private effect cause, other branch, raw input IDs or
internal actor/note. Historical estimates carry no historical-access grant.
Use existing no-store, authorization-revision and delayed-response protections.

## Time and Product surface

All anchor/calculation/reference Instants use aware UTC, timestamptz and RFC3339.
Ranges are integer elapsed-minute Durations; fingerprints are not Product labels.
Use ADR-016 dual-calendar helpers, minute-level output and explicit range wording.
Show occurred as-of and recorded information separately, with age but no new
fresh/stale threshold. Existing OIP fingerprint health keeps its own meaning.

Internal Shipment and Customer own-Cargo cards explain basis, next/final and
missing data; read adapters may reuse the same result where their current UI
contract supports it. No Tower ranking, SLA, Action or Exception change.
Planned distance is «تعریف نشده» pending a proven governed source; ETA may still
be available. No actual travelled distance, AI, GPS or contractual certainty.

## Alternatives

Rejected: second route engine, latest-unit Shipment location, average/speed/AI,
default-zero ranges, overwriting one mutable estimate and map-provider integration.
Deferred: event sourcing, inferred fractional progress, new numeric hold capture.
Using the old plan pin forever would prevent the approved current-reference
recalculation; changing the plan pin would violate P3-10. Separate estimate pins
preserve both contracts.

## Consequences and operational impact

The design trades unavailable results for auditable inputs when progress is
ambiguous. Snapshot volume grows with meaningful changes; bounded SQL pages and
indexed Cargo/sequence queries limit reads. Projection failure is visible and
never mutates operational sources. No new worker, external provider or scheduler.

## Compatibility, migration and rollback

An additive empty migration `20261012_phase3_cargo_eta` follows the verified
canonical `20261011_phase3_owner_transfer`. The never-canonical earlier draft is
preserved at `198d2bf`; no canonical P3-12/P3-13 migration is modified. Preserve all historic migrations and
P3-10 selections. One head, no seed/backfill. New DTO fields are additive and
legacy tracking remains separate. Upgrade and empty downgrade/re-upgrade require
PostgreSQL 18 proof. Populated downgrade refuses before deleting history.
Application rollback may disable ETA while retaining schema/history; it must not
relabel old estimates as current or restore revoked Customer visibility.

## Validation

Mission cases A–J: next/final range arithmetic and missing final reference;
occurred versus late recorded; corrections; reference effective boundaries and
old pins; A/B branches; multiple/split units; ambiguous progress; no distance/GPS;
unknown effects; A→B→A history; concurrent identical recalculations; revocation
and negative/cross-tenant cases. Add PostgreSQL integrity/rollback, Chrome Expert
and Customer normal navigation/reopen/mobile, Workspace/Tower and P3-03/07/09/10
regressions plus all common exact-source gates from the mission record.

## Supersedes / superseded by

Supersedes: none. Extends ADR-004/005/006/010/016,
ADR-029/058/063/065/066 only for this derived consumer. Existing source meaning,
OIP health and authorization remain unchanged. Superseded by: none.

## Status history

2026-09-26: PROPOSED for named architecture acceptance. Build and qualification
NOT_RUN; Product Owner DN04 decision retained as already resolved.

2026-09-26: ACCEPTED by the Product Owner's named acceptance/resume mission,
with explicit idempotent ensure versus pure historical/read lookup semantics.
Original proposal evidence remains at review commit
`081f73a3d84c6aa6136e7f1fd4268f57bac497cf`; acceptance does not claim implementation.

## Current resumed implementation — 2026-09-26

The Product Owner explicitly resolved
`P311_STOP_PLACEMENT=ARRIVAL_POINT_BEFORE_NEXT_MOVEMENT`. The
[current implementation contract](../../product/phase3/P3-11-ETA-CONTRACT.md)
defines arrival-only next/final arithmetic, origin boundary, whole remaining
stops, existing completion adapters and Customer-safe provenance. Preserved
work at `198d2bf` is resumed in its original branch after merging P3-13.
Full [exact-source qualification](../evidence/phase3-p3-11-eta-status-20260926.md)
passed on Product `c0e35a7845f9749ec574a3e29ed5ec81ada87979`. Preliminary attempts are
retained separately. Controlled canonical integration requires the final clean,
ancestry, reference and push/fetch receipt; no global Product or human PASS follows.
