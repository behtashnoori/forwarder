# ADR-063 — scoped reported operational facts and safe customer effects

- Status: ACCEPTED within the explicit Product Owner P3-07/DN06/DN07 authority
  and delegated bounded implementation choices in the five-stage mission.
- Date: 2026-09-25. Baseline: LPAF v2.7; rigor C / Astra capability need.
- Authority: [mission record](../../product/phase3/P3-06-10-MISSION-AUTHORITY.md),
  attached mission §§17–30. This is not a human walkthrough or Release approval.
- Verified start: canonical `13c0fed2d5971907d93f23860cc5689c7ebe33f8`,
  pushed/fetched at 0/0 after P3-06 Product
  `0e65fd89882e23453d7c3bfe4d520cd7f44a6c32` qualified. Actual migration parent:
  `20261006_customer_entitlement`. New isolated P3-07 worktree/branch.

## Product authority and preservation

AUTHORIZED: explicit operational reports scoped to Shipment, Route Stage,
ExecutionUnit or Cargo; occurred/recorded separation; late reports; source
classification; retained corrections; safe customer effects on explicitly
impacted Cargo. Owner Expert commands; existing authorized oversight reads.
DELEGATED: normalized typed context/impact relations, transactional locking,
idempotency, additive migration, allowlisted DTO and current UX components.
PRESERVED: existing event/location SOR, Request/public tracking, P3-01..06,
route/execution/allocation, Exception/Action/SLA/Workspace/Tower mechanisms.
UNKNOWN until qualification: preservation evidence on this new candidate.
DECISIONS_NEEDED: none within the explicit bounded authority. GPS, confidence
score, automatic Exception/Attention/Action/SLA and full Customer Shipment page
remain excluded. The latter belongs to P3-09.

## Model and transaction

Reuse `OperationalEvent` for identity, actor, source, occurred/recorded instants,
customer message, internal note, idempotency fingerprint and supersession.
Reuse its immutable `OperationalEventLocationEvidence` for explicit structured
or manual reported location. A one-to-one `OperationalEventReportContext`
contains only typed scope, primary Shipment/tenant, report kind, safe effect and
correction reason. It is not an independent event stream and has no duplicate
actor/time/message identity. An immutable impact relation names same-Shipment
Cargo affected by the event; relational tenant/parent constraints apply.

The envelope gains a non-null organization key. Existing rows copy only the
already mandatory ExecutionUnit.organization_id through the proven FK; missing
ownership aborts migration. This materializes existing authority, not inferred
reporting history. A composite FK requires unit and event tenant equality; the
typed context also binds its event and Shipment to that tenant. Thus no optional
unit reference becomes an optional ownership path. Legacy event payloads, actor,
times and location snapshots remain unchanged. A database insert bridge allows
the old Unit-bound writer shape to obtain only that mandatory Unit's tenant;
an explicit mismatched tenant still fails its composite FK. No identity guess
or report context is created. Application rollback after new reports exist is
unsupported because old public readers lack the new family exclusion; populated
schema downgrade is refused. This is local qualification, not deployment.
Current code is tested against
the current schema; historical migration tests retain their original revisions.

ExecutionUnit becomes nullable only for the dedicated reported fact event type,
so Shipment/Stage/Cargo facts do not create or guess a physical execution. Old
event rows remain unchanged and receive no inferred report context or source.
Shipment row locking plus the existing `OperationalIdempotency` boundary
serializes commands. A correction names the still-current original event; it
appends a new envelope/context/impacts and retains the original. One successor
is enforced for this event family; no original fact is overwritten or deleted.
An explicit occurred instant with timezone is required; recorded time is trusted
backend UTC. Location ordering excludes superseded facts and uses occurred,
recorded and event ID deterministically. No last-unit-to-whole-Shipment collapse.
History is paginated in SQL; latest per-scope locations use a separate ranked
query and do not change with the selected history page. A retained inactive
ExecutionUnit remains a valid target for late reporting/correction, clearly
labelled as inactive history; the report never reactivates the unit.

## DN06 and DN07

Sources: CARRIER_REPORT (گزارش شرکت حمل), DRIVER_REPORT (گزارش راننده),
INTERNAL_EXPERT (ثبت کارشناس), OTHER_OPERATIONAL_SOURCE (منبع عملیاتی دیگر).
No confidence metric or GPS assertion. Bounded report kinds distinguish
location, progress, transport change and operational effect.

The raw report envelope stays internal. Its separately authorized derived
Customer effect projection filters explicit impacts through current DN10 and
actual Cargo ownership before pagination/serialization. It uses only supplied
safe Customer text or the approved fixed generic text:
«در روند حمل این محموله یک تغییر عملیاتی ثبت شده است.»
For explicitly recorded DELAY:
«به دلیل شرایط عملیاتی، حرکت محموله با تأخیر مواجه شده است.»
No text is synthesized from internal notes, other Customers, private Cargo,
Carrier details or causes. No impact means no Customer message. A B-scoped fact
affecting A may supply only A's safe effect, not B's identity or location.
Location requires a LOCATION fact plus own Cargo scope, relevant destination
ancestry for a Route Stage, or current positive ACTUAL own-Cargo participation
for an ExecutionUnit. An explicit impact alone cannot reveal another unit's
location. This conservative read gate may hide historical unit location after
own Cargo leaves; its safe effect remains available. Cargo-scoped own history
retains the reported location. EFFECT facts never disclose internal location.
The reserved event type is rejected by the legacy command and migration aborts
if a legacy row already uses it; there is no silent reclassification.

Legacy unit timeline and tracking projections exclude this new event family;
they cannot publish new scoped data through their broader old unit authority.
The new Expert projection resolves the recorded Shipment scope. No new Public
Tracking or Customer page is introduced. No unit location/status/attention cache,
Exception, Action or SLA state is mutated by a report or correction.

## Migration, evidence and references

Additive migration from the verified current head; preserve legacy rows, prove
empty downgrade/re-upgrade, and refuse populated rollback to retain facts.
Qualify two disagreeing units, all sources, late entry, correction/reopen,
safe explicit/fallback/no-impact behavior and A/B privacy; concurrency, negative
authorization, PostgreSQL 18, Chrome and protected/full regression gates apply.
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J01/J04/J05/J07/J08/J09,
FWD-IPJ-02/IPJ-04. Current indexes, OpenAPI, tenant inventory, Phase 3 status and
architecture are reconciled before integration. Historical ADRs are preserved.
Global Product validation EVIDENCE_PENDING; integrated journeys/human walkthrough
NOT_RUN; RELEASE_READY=NO. No Production, deployment or release.
