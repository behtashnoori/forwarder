# MT-1C.1 transaction and materialization foundation

**Status:** Foundation ready. Full 15-surface certification remains MT-1C.2.

## Consistency contract

Each Flask request, ordinary long-lived SQLAlchemy Session, and explicit
background `census_unit_of_work` pins one
immutable `CensusContext`: census ID, publication order, monotonic cache
version, and opaque cache token. PostgreSQL units acquire the shared form of
the MT-1D publisher advisory lock before resolving the active pointer. The
publisher takes the exclusive form of the same transaction lock. Therefore a
request or side-effect transaction finishes entirely on N, and N+1 cannot
activate until that transaction ends.

If a logical request/job crosses a commit, its expected context remains N.
The next transaction reacquires the shared lock and compares the active
pointer. A mismatch raises `CensusTransitioned` and requires a clean retry; it
never silently repins. Missing active authority after a canonical scope exists
raises `CensusUnavailable` and fails closed.

All ORM filters, held-instance checks, relationship loads, bulk DML, cache
keys, and final materialization use the pinned census ID directly. Immutable
MT-1D decisions make finishing a read response on N safe. Flask runs a final
identity-map guard before normal JSON, streaming chunks, and download response
bytes. Response headers expose only the version/token used, not ownership
classification.

## Side effects and outbox

Certified mutations, assignments, notifications, audit records, and outbox
rows require the same-session transaction fence during flush and commit. The
guard no longer consults Flask's global session for a custom SQLAlchemy
Session. Operational outbox payloads carry reserved `_ownership_census`
provenance with census ID, version, and token. Business mutation, audit, and
outbox creation retain their existing single-transaction atomicity. There is
no outbox dispatcher in this repository, so dispatch is not claimed as
certified. Core/text DML against side-effect tables is rejected because it
cannot expose mapped parents to the eligibility check; mapped repository and
service writes are the only accepted path.

## Core composite resource

`project_party_relationship` remains a Core association table with canonical
identity `(project_id INTEGER, customer_id INTEGER, party_role STRING)`. A new
append-only normalized component table is populated by the atomic publisher.
The session statement hook detects the association in direct selects, joins,
updates, and deletes and correlates all typed components plus the local/root
CLEAR decisions under the pinned census. Integer database keys are formatted
as canonical decimal text; caller strings are never parsed or coerced.

## External exception policy

`QuarantinedResource` maps to nondisclosing 404 for public and authenticated
resource boundaries. Existing permission failures for visible resources
remain 403 and business-state conflicts remain 409. Public tracking maps its
local catch-all boundary to the exact ordinary not-found payload, so conflict,
lineage, quarantine reason, candidates, and internal identity are not exposed.
The MT-3 numeric/global tracking expected failure is unchanged.

## Certification boundary

Focused SQLite tests cover request/list materialization, held instances,
multi-statement count plus rows, explicit job transition abort, public
exception equivalence, Core composite SELECT/update/delete, ordinary CLEAR
behavior, actual notification mutation, Core side-effect bypass rejection,
and outbox provenance. Disposable loopback PostgreSQL 18 tests prove
that a pinned reader/mutator blocks N+1 activation through commit, count/page
and Core rows stay on N, held mutation commits under N, new readers see N+1,
and denied composite update/delete affect zero rows. Relevant MT-1D rollback,
publisher concurrency, immutable history, and cache-token tests also pass.

The matrix keeps every full-surface `pass` flag false. `FOUNDATION_READY=true`
means only that the shared architectural boundary is ready for MT-1C.2 real
surface certification.

No Production access, deployment, push, Legacy Census, MT-1, MT-2, or MT-3
redesign occurred. The next permitted recommendation is:

`RESUME MT-1C.2 FULL SURFACE CERTIFICATION`
