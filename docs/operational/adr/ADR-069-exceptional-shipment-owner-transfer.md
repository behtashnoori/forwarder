# ADR-069: Audited exceptional Shipment owner transfer with database fencing

- Status: ACCEPTED
- Date: 2026-09-26
- Owners: Architecture; Security; Operational Shipment; Data
- Affected domain: Shipment ownership and current authorization
- Product authority: [P3-11..13 mission](../../product/phase3/P3-11-13-MISSION-AUTHORITY.md), retained source §§48–69
- Acceptance date: 2026-09-26
- Acceptance authority: Product Owner, explicit named acceptance with corrected security trust boundary in the [architecture acceptance mission](../../product/phase3/P3-11-13-ARCHITECTURE-ACCEPTANCE.md)
- Implementation authority: bounded P3-13 implementation authorized; database privilege proof, qualification and controlled integration gates remain mandatory

## Context and problem

ADR-047 fixes `OperationalShipment.primary_responsible_expert_id` as the owner
SOR, independent of Request assignment. The canonical model has an ORM
`before_update` guard and migration `20260926_fixed_shipment_owner` installs a
database trigger rejecting ordinary changes. Current document management reloads
the persisted Shipment owner and active membership at use time. ADR-050/061 keep
Admin oversight separate from owning-Expert management; ADR-065 keeps Customer
entitlement independent. The mission approves the exceptional transfer boundary
and DN09, but no named ADR has yet accepted its database implementation.

## Accepted decision

1. Retain the current owner column and ordinary ORM write prohibition. Add one
   append-only ShipmentOwnerTransfer relation: tenant, Shipment, old/new owner,
   actor, non-empty reason, occurred/recorded Instants, sequence, previous/next
   Shipment versions and idempotency identity. Same-tenant/parent integrity and
   unique sequence/version constraints prevent impossible chains. Preserve actor
   display snapshots for the transfer without modifying existing historical actors.
2. Expose one dedicated internal Organization Admin command. Authenticate and
   derive current organization server-side; require exact Admin authority and
   its explicit transfer capability. Validate expected owner/version and an
   active, same-organization, currently eligible Transport Expert target.
   No Customer, Expert, Platform Admin, ordinary edit or Request command can call it.
3. In one transaction, lock Shipment and recheck actor/target memberships in a
   stable order; validate expected owner/version and actor/payload-bound idempotency.
   Reserve and persist exactly one transfer, update current owner and increment
   Shipment version atomically with audit/outbox. Repeat of the same authorized
   command returns its recorded result; a different payload conflicts. A→B and
   concurrent A→C cannot both pass the same predecessor/version.

## Accepted database mechanism and trust boundary

Use a narrow PostgreSQL SECURITY DEFINER transfer routine owned by a dedicated
NOLOGIN role. This is a database execution role, not a new Product persona.
The normal application role is not its member and cannot SET ROLE to it; PUBLIC
execution is revoked; grant only minimum explicit EXECUTE to the trusted service
role. The function has a fixed safe search_path, fully qualified schema/table names,
no dynamic SQL, no caller-selected actor/tenant authority beyond the authenticated
service's validated inputs, and no alternate bulk/general owner-update operation.

The routine independently validates structural eligibility of the supplied
same-tenant active Admin identity and active eligible same-tenant target Expert,
locks the predecessor row, checks expected owner/version, writes immutable history,
and updates only the matching owner/version. The owner trigger permits that
change only under the dedicated function-owner role AND with the matching current
transaction's transfer row and exact old/new/version chain; all ordinary raw owner
UPDATEs still fail. Trigger code itself must not elevate to that role. No session
GUC, global bypass flag, disabled trigger or generic request parameter is used.

Normal runtime DML cannot insert/update/delete transfer history or a permit row;
only the narrow routine can create the transfer. Application generic ORM owner
assignment remains denied; the authorized service invokes the routine then expires
and reloads the ORM state. SQLite tests may use a dialect-specific bounded command
adapter but cannot substitute for PostgreSQL proof. No new external service or
database password is required by the proposed role separation.

The database routine trusts the already authenticated application service for
binding session actor identity; it is not a replacement authentication system.
The normal application database credential is inside that trusted application
service boundary. Application authentication binds the real human identity;
application authorization proves the request actor is the authenticated
Organization Admin authorized for `TRANSFER_OWNER` before invoking the routine.
PostgreSQL does NOT independently authenticate the human Admin. It validates the
supplied actor's existence, active membership/role/tenant, target eligibility,
Shipment tenant, current owner/version, transfer chain, idempotency identity,
immutable history and atomic owner/version transition. A malicious holder of
the trusted app DB credential supplying a structurally valid Admin identity is
not distinguishable from that human request by this routine. No independent DB
identity-binding mechanism or separate identity credential is authorized here.
No raw SQL endpoint is introduced. Migration/schema administrators remain trusted
infrastructure authorities, not ordinary Product actors. Qualification must use a
restricted application role, not merely a schema-owner connection, and prove
ordinary owner writes, history fabrication, role switching and function misuse
fail in their intended boundaries. If role privileges cannot establish this
boundary, this design fails closed; do not fall back to a shared bypass flag.

Qualification reports these separate guarantees, without collapsing them into
database authentication of a human:

| Claim | Required evidence |
| --- | --- |
| A: structural DB owner invariant | Direct ordinary raw UPDATE of owner and generic ORM assignment denied |
| B: transfer-history integrity | Direct raw history INSERT/UPDATE/DELETE denied |
| C: invalid structural routine use | Foreign/inactive Admin, invalid target, wrong owner, stale version and invalid chain denied; PUBLIC EXECUTE and SET ROLE to function owner denied |
| D: human actor binding | Application authentication and authorization responsibility, proven at the request/service boundary |

Trigger code cannot elevate itself; no global/session bypass, caller-controlled
generic bypass flag, trigger disabling, dynamic SQL or bulk owner update is allowed.
If repository/database privileges cannot establish this design, STOP P3-13 with
an architecture/security blocker; do not weaken the fence to make tests pass.

## Current access and independent assignments

After commit every read/command/download follows persisted current authority.
The new owner gets existing normal owning-Expert capabilities; no extra privilege.
The former owner loses ownership-derived access. A separately valid current
permission may remain only within its own action/data contract. Historical owner
or transfer actor records never authorize current access.

Document bytes, exact versions and actors are preserved. The new owner manages
Shipment documents; old owner loses that owner-derived management. Request-owned
document authority continues through its existing Request parent; transfer does
not reinterpret that boundary. Transfer Admin gains no upload/replace privilege.

No transfer command changes WorkItem/Action assignee, Request assignee, Quote
issuer, SLA commitment responsibility, Cargo customer or DN10 grants. Do not call
a general reconciliation routine if it would silently reassign independent work.
Show the former owner's remaining open-work count to authorized Admin as an
informational warning only. It neither blocks transfer nor grants full Shipment
authority to any WorkItem assignee. Audit current background reconciliation paths
as well as the command so later refresh cannot silently perform the forbidden
reassignment. Any previously granted independent WorkItem permission remains
bounded by its existing contract; this ADR creates no new former-owner role.

Invalidate/refetch current owner-dependent lists/detail/Workspace/Tower data and
in-flight responses; server authorization remains authoritative even for an old
open tab or cached link. Keep ADR-065 Customer authorization-revision protections;
Customer payloads receive no transfer reason/history and no changed entitlement.

## History and time

The first transfer records its provable predecessor owner; it does not fabricate
an earlier ownership event/time. Existing creation/audit evidence remains the
source for initial ownership where available; mark legacy unknown provenance
honestly. Every subsequent transfer references the current chain. Preserve all
old audit/document/event rows unchanged. Server committed transfer occurred and
recorded times are distinct stored UTC Instant fields, not backdated user input;
API RFC3339 and ADR-016 display apply. No new duration/calendar contract.

## Alternatives and consequences

Rejected: removing the write-once guard; a reusable bypass flag; trusting UI-only
permissions; automatic WorkItem/Request reassignment; granting former-owner access;
moving document bytes; tenant-wide generic ownership update.
The narrow routine costs privilege/migration maintenance but keeps raw ordinary
owner mutation denied and makes each permitted change inseparable from history.
Security qualification of the routine/role/trigger combination is mandatory.

## Compatibility, migration and rollback

Create the migration only from actual canonical head when P3-13 starts; P3-11/12
are not Product dependencies. Add empty history and replace only the current
owner guard through a new migration; never edit the historical migration. Verify
existing owners and old audits remain byte/meaning-preserved. No guessed initial
owner backfill. N-1 generic writers must still fail on owner changes.

Empty downgrade restores the original unconditional guard and removes only empty
new structures/owned routine privileges. Nonempty transfer history refuses
downgrade before DDL. Do not 'roll back' by assigning old owners or deleting audit.
An old application may not correctly reconcile transferred access/assignments;
after first transfer, require a separately qualified compatible rollback or
roll-forward, with schema/history retained. No deployment/production role change
is authorized by this proposal or mission.

## Operational impact and validation

No worker or external service. Transaction failure leaves neither partial owner
state nor history. Idempotency resolves lost responses. Record sanitized conflict/
denial diagnostics without reasons/PII in general logs. Recheck membership after
lock waits, including concurrent target deactivation and Admin revocation.

Mission cases A–O plus restricted-role raw SQL/role/history attacks, rollback
injection, stale identity-map refresh, delayed browser responses, independent
WorkItems assigned to old owner and another Expert, and subsequent background
evaluation without reassignment. PostgreSQL 18 must prove ordinary ORM/raw owner
mutation denied, authorized transfer allowed, one concurrent winner, replay once,
history immutable and populated downgrade blocked. Chrome normal Admin transfer,
old/new Expert requests/download/Workspace/Tower and unchanged Customer projection
must pass, alongside P3-06/P3-09/fixed-owner and complete mission regressions.

## Supersedes / superseded by

Scoped supersession of ADR-047's absolute
no-transfer rule and ADR-050's no-transfer assumption ONLY for this explicit
exceptional command and current owner-based document authority. Creation, ordinary
write protection, Request separation, tenant boundaries and immutable history
remain. ADR-061/062/065 current visibility and Customer policies remain unchanged.
Superseded by: none.

## Status history

2026-09-26: PROPOSED for named Architecture/Security acceptance. DN02 transfer and
DN09 are already resolved by the Product Owner. Implementation, privilege proof,
tests and browser evidence are NOT_RUN, not presumed safe from the proposal.

2026-09-26: ACCEPTED by the named acceptance/resume mission after explicitly
separating application human authentication/authorization from DB structural
validation and documenting the trusted app-credential boundary.
`DN02_OWNER_TRANSFER_PORTION=RESOLVED_FOR_P3_13`;
`DN09_STATUS=RESOLVED_FOR_P3_13`. Original proposal evidence remains at
`081f73a3d84c6aa6136e7f1fd4268f57bac497cf`; privilege proof remains required.

## Implementation candidate record — 2026-09-26

The [P3-13 working note](../../product/phase3/P3-13-IMPLEMENTATION-WORKING-NOTE.md)
records actual entry from integrated P3-12 `c2e6140`. Migration
`20261011_phase3_owner_transfer` implements the accepted mechanism;
`owner_transfer_service` binds live session identity and refuses PostgreSQL
schema-owner/elevated application runtimes, including TESTING. Preliminary
restricted LOGIN proofs cover raw/ORM/history denial, privilege misuse, concurrent
winner and same-command replay, revocation waits, stale cached owner mutation,
atomic rollback, empty downgrade and populated downgrade denial. Final exact-source
qualification and controlled integration remain pending; this paragraph grants
no Product/global validation, Human Walkthrough or Release PASS.

## Final source qualification — 2026-09-26

Product `c0914906af6675c016d5b77d51ecc8a0c05c0b72` passed the
[complete bounded qualification](../evidence/phase3-p3-13-owner-transfer-status-20260926.md),
including actual restricted LOGIN, structural misuse/role denial, concurrent
transfer and revocation waits, immutable history, transaction rollback and
current browser/document authority. Application human identity binding remains
distinct from database structural validation. Controlled integration has a
separate receipt; global Product validation, Human Walkthrough and Release
remain unclaimed. No prior proposal or preliminary record is rewritten.
