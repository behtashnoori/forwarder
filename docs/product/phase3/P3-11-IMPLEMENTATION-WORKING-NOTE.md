# P3-11 retained implementation — partial, not integration-qualified

Date: 2026-09-26. Parent architecture acceptance:
`6259830f2a5fe94798bf4183d2643bf624529c26`.
Retained authority: P3-11-13-MISSION-AUTHORITY.md and the named acceptance addendum.
No restart, Product freeze, canonical integration or production access.

## Bounded unresolved source meaning

ADR-066 stores a movement pair and a stop/operation/wait pair per directional
route and mode. Neither the fields, the accepted ADR nor the current Product
Contract locates the stop before departure or after arrival. ADR-067 requires
only remaining operations and explicitly says that an endpoint does not prove
a stop complete. Therefore blindly adding every outgoing leg's stop to its
arrival can over-count the destination stop or omit an uncompleted anchor stop.

`DECISION_NEEDED: P311_STOP_PLACEMENT` was submitted to the Product Owner in this
chat: origin before departure, destination before continuation, or retain
unavailable whenever that unplaced duration is needed. This does not reopen DN04
or change the accepted architecture; it identifies a missing source adapter
meaning. The answer is still pending. No elapsed time is treated as approval.

The working implementation explicitly returns STOP_SCOPE_UNDEFINED for a
nonzero remaining stop rather than publishing the initial unproven arithmetic.
Positive movement tests use **explicitly configured** 0/0 stop references; null
is still unknown. Intermediate-node residual stop semantics, nonzero-stop
arithmetic, source-adapter coverage and complete browser/whole-suite qualification
remain unfinished. The draft must not integrate before that gap is resolved.

## Implemented draft boundary

Separate POST ensure and GET history; no materialization from lists/counts.
Per-Cargo/audience immutable snapshots and same-transaction sealed source links;
reference IDs and resolved outputs participate in fingerprints. Current sources
are read at SERIALIZABLE in PostgreSQL with bounded retries, and reread after
commit before a current result is returned. Operational SORs are not written.

Customer sources require current exact Cargo authorization/impact and governed
branch/participation. Internal milestone facts do not become Customer inputs.
UI opens per-Cargo ETA explicitly, clears on browser lifecycle events, and checks
authorization revision after delayed responses. Historical results retain their
pins and are reauthorized. No distance provider, GPS, AI, SLA or exact travel claim.

Draft migration: `20261010_phase3_cargo_eta`, parent
`20261009_phase3_route_time`; additive empty tables, populated downgrade refusal.
This is a worktree source head, **not canonical Alembic head**.

## Development checks (not final evidence)

- 13 focused backend cases passed with the nonzero-stop guard, plus explicit
  OpenAPI/runtime parity. This does not qualify the unresolved nonzero-stop behavior.
- 11 focused frontend and Customer regression cases passed; application TypeScript
  and changed-file ESLint passed.
- Owned PostgreSQL 18 run 2: 7 passed, covering new migration/empty rollback,
  immutable history, concurrent ensure convergence, a report-insert race,
  source preservation, and P3-06/07/08/09/10/DN10 regression tests. The initial run
  failed because its synthetic actor lacked report permission; the actor fixture
  was corrected without changing production authorization.
- Preliminary logs remain in `D:/1-webapp/forwarder-dev/p311-prequalification-pg-run2-20260926`.
  They describe a dirty development source, not an exact final Product SHA.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J02/J04/J07/J08/J09;
FWD-IPJ-02/03/04 evidence is stale for a future integrated candidate.
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING;
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN; RELEASE_READY=NO.
P3-14/P3-15 and global integrated qualification have not started.
