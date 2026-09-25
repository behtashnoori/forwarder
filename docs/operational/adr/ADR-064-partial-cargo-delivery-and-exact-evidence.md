# ADR-064 — partial Cargo delivery and exact-version evidence

- Status: ACCEPTED within the Product Owner's explicit P3-08 decision: a
  minimal real Delivery SOR and extension of the existing typed document context.
  The acceptance scope is mission §§31–44; it is not inferred from tests or
  completion and confers no human walkthrough or Release approval.
- Date: 2026-09-26 (Asia/Tehran). LPAF v2.7; rigor C / Astra capability need,
  without claiming a runtime model setting.
- Authority: [five-stage Product Authority Record](../../product/phase3/P3-06-10-MISSION-AUTHORITY.md).
- Verified start: canonical/local/fetched github
  `682e83ed3a51badb3938d66dbd337e8e10e57797`, clean, ahead/behind 0/0.
  P3-07 Product `cd83f21ca1ac0db6e940475fcd9067713831a581` qualified and integrated.
  P3-02/03/05/06 dependencies are present. P3-07 is not a functional dependency.
  Actual sole migration parent: `20261007_phase3_reported_facts`.
- Affected decisions: ADR-010/022/030/047/050/057/058/060/061/062.

## Product authority and domain boundary

AUTHORIZED: actual positive partial deliveries per existing Cargo; independent
Customer progress in a shared Shipment; append corrections; exact file-version
evidence; nonblocking discrepancy with known actual; owning Expert commands.
The Product Owner explicitly requires a real minimal Delivery persistence and
the DELIVERY document context. This record fixes their bounded representation
before build. It introduces no other owner, lifecycle, inference or business rule.

PRESERVED: OperationalShipment remains the tenant and owning-Expert root;
ShipmentCargoItem owns Customer lineage, UOM and requested/planned/known-actual
quantities; RoutePlan owns the route; CaseDocumentFile/private storage own bytes
and immutable versions; MDPM owns readiness. No source quantities, allocations,
route events, Shipment status, Exception, Action, Attention or SLA are mutated.
No delivery is inferred from an old delivered/completed lifecycle label.
Customer full Shipment/delivery projection belongs to P3-09; P3-08 provides only
the required secure capability support. Public Tracking is unchanged.

DELEGATED technical details: normalized relational facts, same-parent/tenant
constraints, transaction locks, existing retry ledger, immutable correction
links, narrow API and progressive Persian section in the existing Shipment page.
DECISIONS_NEEDED: none within the explicit Product outcome. Closure (P3-12),
owner transfer (P3-13), inferred loss/cancellation and UOM conversion are excluded.
Protected behavior remains UNKNOWN until exact-candidate qualification.

## Facts, time and concurrency

`CargoDelivery` is an immutable downstream operational fact with an opaque
public ID, mandatory Shipment/Cargo/tenant, positive Decimal(18,6) quantity,
the Cargo's existing immutable UOM identity/label snapshot, explicit destination
text, occurred and recorded Instants, actor, revision and optional correction
reason. Customer identity follows persisted Cargo ownership; no header Customer,
Request or Portal identity is guessed. A legacy Cargo with no proven same-tenant
CRM owner cannot acquire an inferred owner through a Delivery command. Existing
historical Cargo/UOM facts remain usable without inventing current catalog data.

Occurred time requires an explicit timezone and supports late entry. Backend
UTC owns recorded time. PostgreSQL stores timestamptz; API serialization uses
the existing UTC Instant formatter and the UI uses the existing dual calendar.
No new business-local timezone or ETA semantics are introduced.

A correction names the current predecessor and expected revision, appends a
new complete fact and preserves the original actor/times/location/quantity and
evidence. Same-Cargo predecessor FK, unique successor and immutable database/ORM
guards prevent history rewriting or a correction fork. New deliveries use
expected revision zero; different commands may legitimately record distinct
events. Shipment/Cargo locks and the existing OperationalIdempotency namespace
serialize commands and prevent duplicate replay. A replay returns its original
fact even after correction; changed payload with the same key conflicts.

Current delivered total sums only unsuperseded facts for each Cargo. Known
actual remains independently nullable. A partial sum shows a nonnegative
remaining quantity when actual is known; an excess shows a prominent warning
with the exact difference. Unknown actual stays unknown, and no quantities are
converted or rewritten. Example: 100 actual, 60+35 delivered gives 95/5; correcting
60 to 58 gives 93/7; a genuine total 102 is accepted with an excess warning of 2.
Another Customer's Cargo and Shipment lifecycle remain unchanged.

## Document capability and history

Extend OperationalDocumentContext with a real DELIVERY FK, constrained to the
same Shipment/tenant and exact-one-target rule. No second file store is created.
`CargoDeliveryEvidence` is an immutable association of Delivery and an exact
CaseDocumentFile ID, with actor/time and same-parent constraints. Upload/context
attachment appends the evidence association in the existing transaction. An
explicit command may also associate an already-current Cargo/Delivery document
belonging to that same Cargo; broad unrelated Shipment files are not guessed in.

Original evidence associations remain after correction, replacement, deletion
state or context changes. They are historical evidence, never independent read
authority or automatic MDPM readiness. A correction may explicitly select an
eligible exact version; it does not silently copy history into current evidence.
Replacement still preserves the prior version and begins the new version INTERNAL.

P3-08 concurrency review reproduced a stale-file defect in the existing context
revision command: if replacement committed after its route loaded an active file,
the command could still reclassify that now-superseded file and add evidence.
The bounded repair serializes context revision with upload/replacement and Delivery
at the same Shipment lock, then locks and refreshes the exact file before context.
It rechecks owning-Expert authority after waiting. This preserves the existing
current-version rule and standardizes lock order; it grants no new mutation right.
The PostgreSQL regression first failed against the prior command with DID NOT RAISE,
then requires a 404 with unchanged context/version and no new evidence association.

INTERNAL remains private. CARGO_OWNER may apply to DELIVERY through its actual
Cargo and the current live DN10 grant; EXPLICIT_SHARED is unavailable for private
Cargo/Delivery contexts. Other pre-existing explicit sharing keeps its policy.
List/count/page/download apply current context, exact active version, live
account/tenant/CRM entitlement and Cargo ownership before disclosure. A retained
historical evidence link never reopens an old Customer download. Owning Expert
alone manages; Admin oversight is read-only and Customer/Public gain no commands.

This extends only ADR-061's deliberately deferred Delivery target and Cargo-owner
context restriction. ADR-061's historical body remains unchanged; ADR-062's live
entitlement and all ADR-050 exact-version/management boundaries remain authoritative.

## Migration, references and verification

One additive migration follows the verified actual parent above. It creates no
Delivery backfill and preserves old file/context values. Empty downgrade/re-upgrade
is supported; populated rollback refuses to erase Delivery/evidence facts. Old
application versions do not understand DELIVERY, so application rollback after
its use is unsupported without a separately governed reconciliation. No Production
access, deployment or release is authorized.

Current architecture/decision indexes, tenant inventory, OpenAPI, document context
contract, mission record and plan require reconciliation before integration.
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J02/J04/J08/J09, FWD-IPJ-04.
Required proof: A/B partial delivery, correction and exact evidence; nonblocking
excess; no upstream/lifecycle mutation; invalid/unknown/cross-tenant/non-owner
denials; replay and concurrent create/correct; legacy/incomplete data; PostgreSQL
18 migration/constraints/rollback; normal Chrome/reopen; P3-05/P3-06 regressions;
full backend/frontend and all common static/contract/security gates.
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING; INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN;
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN; RELEASE_READY=NO.
