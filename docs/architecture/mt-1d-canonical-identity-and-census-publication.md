# MT-1D canonical identity and census publication

**Status:** foundation implemented; MT-1C remains uncertified until its complete
runtime-surface suite is resumed and passes.

## Boundary

MT-1D adds identity and publication infrastructure only. It assigns no tenant,
does not resume the final MT-1 migration, does not add MT-2 request context, and
does not redesign MT-3 public tracking. The old MT-1C tables remain intact for
compatibility. Once a canonical scope exists, the canonical active-census path
takes precedence and fails closed; legacy fallback is available only for entity
types that have never entered a canonical census.

## Canonical resource identity

An identity is the tuple `(resource_type, resource_key_payload)`. The key payload
is canonical UTF-8 JSON with this exact versioned shape:

```json
{"components":[{"kind":"INTEGER","name":"id","value":"123"}],"version":1}
```

Components are ordered, named, and typed. `INTEGER` uses canonical arbitrary-
precision base-10 text, `STRING` preserves the exact value without trimming,
case folding, Unicode normalization, or numeric coercion, and `UUID` is accepted
only after strict parsing and is rendered as lowercase hyphenated text. Unknown
versions, shapes, kinds, duplicate names, non-canonical numbers, and overlong
values are rejected.

The lookup digest is SHA-256 over a canonical JSON envelope containing both
`resource_type` and the complete key. The exact payload is always retained and
compared on lookup, so the digest is not treated as an equality proof by itself.
Consequently `Customer:123` differs from `ShipmentRequest:123`, integer `123`
differs from string `"123"`, and ordered typed composite components cannot have
delimiter or concatenation collisions.

The 28 ambiguous resources comprise 27 integer-surrogate identities and one
composite identity. `project_party_relationship` is exactly:

1. `project_id / INTEGER`
2. `customer_id / INTEGER`
3. `party_role / STRING`

The analyzer retains its legacy human-readable `entity_id` for report
compatibility, but now emits `resource_identity` using the same serializer as
the publisher and runtime. Tracking codes, public IDs, and parent-scoped unique
keys are aliases, not canonical identities; a future resolver must declare the
alias kind explicitly and resolve it to the physical canonical identity. It
must not infer an integer identity with `isdigit()`.

## Ownership and enforcement state

Ownership classification and runtime enforcement are separate columns:

- classification: `DETERMINISTIC`, `CONFLICT`, `UNRESOLVED`, or
  `INVALID_LINEAGE`;
- enforcement: `CLEAR` or `QUARANTINED`.

`CLEAR` is legal only with `DETERMINISTIC`. Any classification may carry an
explicit `QUARANTINED` safety hold. Missing or malformed metadata is a fail-
closed condition, not a stored `UNKNOWN` classification. `QUARANTINED` is never
an ownership classification.

## Versioned census and immutable decisions

`ownership_census` is one complete analyzer publication. It records a monotonic
publication order, analysis version, source and canonical manifest fingerprints,
publisher identity, timestamp, and predecessor census. A census contains exact
per-resource-type counts and evidence fingerprints in
`ownership_census_scope`.

`ownership_decision` stores canonical identity, analysis census, monotonically
increasing per-resource decision version, classification, enforcement state,
evidence fingerprint, effective order/time, predecessor decision, and canonical
root identity. A new census appends decisions; it never updates old ones. ORM
guards reject history updates/deletes, and the PostgreSQL migration adds database
triggers that reject them independently. `ownership_census_activation` is the
append-only activation audit trail.

## Atomic publisher and concurrency

`publish_census()` is a privileged internal/CLI capability and is not imported
by a normal request endpoint. Obtaining its capability requires a constant-time
match against the deployment-only `MT1D_CENSUS_PUBLISHER_TOKEN` (minimum 32
characters) and a non-empty `MT1D_CENSUS_PUBLISHER_DATABASE_ROLES` allowlist.
PostgreSQL publication also verifies `current_user` against that allowlist in
the publishing transaction. The migration revokes mutation of all census tables
from `PUBLIC`. Deployment must keep table ownership outside the normal request
role and grant the required mutations only to the allowlisted internal publisher
role; without the token/allowlist the Python publisher fails closed.

The publisher validates the full manifest before opening its transaction. It
also checks exact database row cardinality for every mapped scope and verifies
that each declared root is reachable through the resource's actual current FK
lineage; an unrelated clear root cannot be declared to launder a child. For a
multi-parent resource, every populated parent other than the exact declared root
must also have a published, effectively clear local/root decision before the
child may be clear. This keeps the deny-any-parent mutation and read contracts
consistent while the declared root remains the live propagation path. In
PostgreSQL it then takes a transaction-scoped advisory lock and locks the
singleton active row. It verifies the expected predecessor and increasing
publication order; appends the census, scopes, and all decisions; validates
lineage membership and exact counts; writes an activation event; and changes the
singleton pointer and cache token in the same commit. Readers join through that
pointer, so they observe either the complete old census or complete new census.
An exception rolls back all rows and the pointer.

The same census ID and identical manifest is an idempotent no-op and does not
change the token. Reusing an ID with different content, replaying a historical
census, publishing against a stale predecessor, or using stale ordering is
rejected. Concurrent publishers sharing a predecessor serialize; the winner
commits and the loser then fails the predecessor check.

## Cache token

`ownership_active_census` carries both a monotonically increasing
`cache_version` and a new opaque UUID token. Every accepted activation changes
both in the pointer transaction, including transitions that keep the same
enforcement but change classification or evidence. Exact replay changes neither.
Staged work and rolled-back publication cannot affect them. MT-1C's
`decision_epoch_token()` consumes this authority when it exists and retains the
old aggregate token only before canonical adoption.

## Effective lineage state

Each decision points to a canonical root identity in the same active census.
`effective_quarantine(resource)` is denied when the local decision is denied,
the root is absent/mismatched, or the current root decision is denied. SQL ORM
predicates and canonical identity checks resolve the active local/root pair
instead of copying root quarantine flags into descendants. Thus a root change
immediately hides a clear descendant under the newly active census.

## Held-instance safety

SQLAlchemy's identity map can return an object without issuing a SELECT.
`assert_instance_current()` is therefore the reusable mandatory boundary for a
held object immediately before serialization/return, mutation, parent/reference
use, or download. It performs a current-authority query on every call and stamps
the instance only for diagnostics; the stamp is never trusted as authorization.
`refresh_guarded()` checks both before and after refresh. `before_flush` checks
dirty/deleted certified resources themselves and separately checks new/dirty
parent references. Existing query hooks retain ORM select and legacy bulk
update/delete filtering. Immutable platform reference models are outside this
policy.

Cross-process activation cannot safely invalidate arbitrary Python attribute
access already in memory. Accordingly services must not treat a raw held model
as an authorized DTO: they must call the guard at the output/side-effect boundary.
The publisher expires its own session identity map after activation.

## MT-1C resume and public tracking

MT-1C resume must publish a complete 28-resource census, route each of its 15
surfaces through canonical/effective-root checks, add explicit guards at held
read/mutation/reference/download boundaries, and certify real endpoint, job,
report, export, storage, CLI, cache, join, and monitoring flows. Association-table
enforcement must use all three canonical key components.

Public tracking retains its current response contract. A later MT-1C resume can
resolve the supplied tracking alias to a `ShipmentRequest` canonical physical ID
and consume the same effective-root guard. MT-1D does not change routing or the
public identifier design.

## Migration

Alembic revision `20260821_mt1d_canonical_census` builds on
`20260820_mt1c_quarantine_runtime`. It only creates platform security-control
tables, indexes, constraints, and PostgreSQL append-only triggers. It neither
alters nor backfills tenant ownership and preserves all MT-1C tables and data.
