# P3-11 — current explainable arrival ETA contract

Authority: [explicit resume Product decision](P3-11-RESUME-AUTHORITY.md),
retained request SHA-256 `a4321e57babe6766750453b731f92862969c7567651b6845a93211a811b701cc`.
Architecture: ACCEPTED ADR-067. This replaces only the pending stop-placement
disposition; the original working note and blocked/proposal history stay intact.

P311_STOP_PLACEMENT=ARRIVAL_POINT_BEFORE_NEXT_MOVEMENT.
DN04_STATUS=RESOLVED_FOR_P3_11.

## Meaning and source adapters

For A→B→C, arrival ETA(B) is movement(A→B). Arrival ETA(C) is movement(A→B)
+ the whole remaining stop(B) + movement(B→C). Stop(C) is after final arrival
and is excluded. Arrival ETA never claims delivery, unloading, customs completion
or operational closure. The incoming leg owns the stop at the current node; an
outgoing leg's arrival stop is never moved backwards to its origin.

If arrival at B is established, stop(B) stays fully required until explicit
completion. Two elapsed hours do not turn 4–8 hours into 2–6. The calculation
uses the occurred instant and whole remaining reference components; recorded
time is audit only. No fraction, speed, map, wall-clock subtraction or text parsing.
Explicit 0/0 is valid zero; either missing bound is unknown. Only missing
components required by that target make it unavailable. Thus a missing later
movement or stop can leave next available and final unavailable.

Governed proof uses existing source contracts:

- Current effective departure/arrival MilestoneEvent, including explicit inherited
  revision lineage, or an exact planned-leg RouteTraversalFact with matching endpoints.
- An applicable P3-07 structured LOCATION report resolves an unambiguous Cargo-path
  node. CARGO, stage, explicit Shipment impact or whole-unit participation must
  prove this Cargo/path. It is position evidence, not an operation-completion fact.
- Existing `checkpoint_processing_complete` after explicit checkpoint arrival is
  a completion fact. All noncancelled configured checkpoints at that incoming
  leg's exact canonical arrival must have a valid completed occurrence; a blocked,
  partial or unlocated/facility-ambiguous checkpoint cannot prove aggregate stop
  completion. Checkpoint status text alone is not proof. The last required
  completion occurrence anchors continuation. Effective corrections remain authoritative.
- A governed departure of the next movement proves its prior stop consumed.
  Private milestones, traversal and checkpoint operations never become Customer
  inputs or explanations. Customer continuation can therefore honestly retain a
  stop that an internal estimate knows completed.

The latest applicable occurred-time observation is used; equal-time conflicting
positions, future observations, invalid correction chains and ambiguous split
participation fail closed. A unit spanning multiple candidate stages is not
arbitrarily assigned to the latest stage. One partial allocation is not whole-Cargo
progress. At origin, position alone cannot establish departure and returns
`DEPARTURE_UNDEFINED` («زمان شروع حرکت هنوز مشخص نیست.»).

## Immutable result, provenance and authorization

`CargoEtaSnapshot` stores tenant, Shipment, Cargo, audience, route revision and
destination branch, occurred/recorded anchor, calculation instant, ruleset,
component/reference basis, exact source fingerprint, and independent next/final
results. `CargoEtaInput` seals relational source links in the snapshot transaction.
Snapshots and input links cannot be updated/deleted. P3-10 references are selected
at the exact captured calculation instant and pinned; existing plan selections
are never rewritten. Meaningful A→B→A changes append three snapshots, even when
the first and last range match. Identical concurrent ensures converge through a
per-Cargo lock, consistent PostgreSQL source reads and bounded retries. Sources
and current authorization are checked again before the response is returned.

Internal authorization is the current existing Shipment read authority, including
P3-13 transfer. Customer authorization is Portal Account → current DN10 → CRM
Customer → own Cargo → safe route/progress, checked before calculation/history.
Customer DTO fields are allowlisted; no private notes, causes, source IDs,
fingerprint or internal provenance. Private occurrence-only source versions do
not generate Customer history. History is reauthorized and source-inaccessible
results are masked. Responses are private/no-store; the browser clears delayed,
hidden, revoked and previously selected Cargo results before reuse.

POST `/api/operational-shipments/{shipment_id}/cargo/{cargo_id}/eta/ensure` and
POST `/api/customer/shipments/{shipment_id}/cargo/{cargo_id}/eta/ensure` explicitly
materialize the derived snapshot. Empty body only: callers supply no dates,
anchors, durations, actor IDs or result. Matching GET `.../eta/history` is pure,
paged at 20 rows. Unrelated lists/counts never create snapshots. Source churn
returns 409, denied/foreign Cargo fails closed; there is no stale fallback.
The exact shapes and errors are in `docs/openapi/openapi.yaml`.

Next-point scope is the next governed arrival on the Cargo branch. An internal
in-leg checkpoint without a fractional reference basis makes that next ETA
unavailable. Customer sees its approved safe route-stage target. Final is the
Cargo terminal destination. A reported terminal arrival produces
`DESTINATION_REACHED` rather than a fabricated future estimate.

Planned distance is «تعریف نشده» / null: the inspected RouteLeg, RouteTraversalFact
and P3-10 reference contract has no governed numeric route-distance source.
Reported points do not supply actual path evidence; actual travelled distance
is not emitted. No provider, AI, GPS, SLA, ranking or operational source write.

## Migration and qualification boundary

New revision `20261012_phase3_cargo_eta` follows
`20261011_phase3_owner_transfer`. It preserves the schema intent of the
never-canonical `20261010_phase3_cargo_eta` draft at `198d2bf`, using a new ID and
actual current parent. The old draft bytes remain in Git history. P3-12/P3-13
migrations are unchanged. One head, two empty additive tables, no seed/history
backfill. Empty downgrade/re-upgrade is supported; populated downgrade refuses
before deleting evidence. No Production migration is authorized.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J02/J04/J06/J07/J08/J09 and
FWD-IPJ-02/03/04. Required slice cases A–P and the complete exact-source checks
are defined in the retained request. Current implementation checks are preliminary
until a clean Product SHA and its evidence descendant are recorded.
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING; INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN;
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN; RELEASE_READY=NO.
