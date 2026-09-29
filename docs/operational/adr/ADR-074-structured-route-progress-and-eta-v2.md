# ADR-074 — pinned route distance, structured progress and ETA ruleset v2

- Status: ACCEPTED within the 2026-09-29 Product Owner mission.
- Baseline: LPAF v2.7; rigor C; extends ADR-058, ADR-059, ADR-063, ADR-066 and ADR-067.
- Product Authority Record: `docs/product/phase3/HUMAN-WALKTHROUGH-ETA-STRUCTURED-ROUTE-PROGRESS-AUTHORITY.md`.

## Decision

`OrganizationRouteTimeVersion` remains the organization-owned reusable route
reference. A version may additionally define `planned_distance_km` as a positive
decimal value. Null means unknown. `RouteLegTimeBasis` continues to pin the exact
immutable version selected for a draft leg; later reference versions and replans
cannot rewrite that basis.

There is one structured in-leg progress representation:
`DISTANCE_REMAINING_KM`. It is append-only evidence attached one-to-one to a
P3-07 reported event and binds the exact organization, Shipment, RoutePlan,
RouteLeg, RouteStageExecution and ExecutionUnit. If the leg had a matching pinned
basis when observed, the progress row also pins that basis and its distance. A
missing basis remains missing for that observation. Human location text is an
independent optional snapshot and is never parsed or converted into progress.

Only `PROGRESS` reports may carry structured progress. The selected stage must
belong to the current active plan, its exact leg and Shipment, and its execution
must be the report target. Distance is non-negative and cannot exceed the pinned
planned distance when one exists. Corrections append a new report and progress
row; old evidence is never updated or deleted.

## ETA v2 calculation

ETA ruleset `ETA_RULESET_V2` preserves ADR-067 component ordering and stop
semantics. A valid latest structured progress observation becomes the anchor on
its leg. Cargo applicability still uses the existing exact actual-allocation
participation proof; split or ambiguous participation fails closed.

For the active leg only:

```text
remaining_fraction = distance_remaining_km / planned_distance_km
remaining_movement_min = ceil_to_second(reference_movement_min * remaining_fraction)
remaining_movement_max = ceil_to_second(reference_movement_max * remaining_fraction)
ETA bound = occurred_at + active remaining movement + later full movement/stop components
```

The pinned basis must supply planned distance and both movement bounds. Values
are Decimal; the fraction is constrained to `[0,1]`; each duration is rounded up
to the nearest second before timestamp addition. No speed, elapsed wall-clock,
coordinates, traffic, weather, GPS or textual heuristic participates. A zero
remaining distance is position at the leg destination, not proof that arrival
operations or the following stop are complete.

State precedence is deterministic:

1. no applicable Cargo route: `ROUTE_UNDEFINED`;
2. structured progress exists but its pinned distance/time basis is incomplete:
   `ROUTE_BASELINE_UNDEFINED`;
3. no usable structured/node progress: `PROGRESS_UNDEFINED` (or the existing
   ambiguity reason when conflicting/partial evidence exists);
4. valid progress and every required later reference component: ETA available.

Free-text-only reports remain in state 3. Missing later-leg reference components
use `ROUTE_BASELINE_UNDEFINED`. Old v1 snapshots retain `ETA_RULESET_V1`; new
materializations use v2 and append immutable history.

## Ownership, visibility and history

Organization Admin owns reusable reference versions. The Shipment-owning Expert
selects the plan basis and records progress through existing report authority.
Customer visibility remains the existing explicit Cargo-impact allowlist plus
current Cargo authorization; internal identifiers, exact progress values and
provenance remain private. Customer ETA may consume the safe result but receives
no new private source fields.

One additive migration adds the optional reference distance and immutable progress
table, changes only the ETA ruleset check to permit v1 history plus v2, creates no
rows and performs no backfill. Populated downgrade refuses before evidence loss.
