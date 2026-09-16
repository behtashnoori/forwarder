# ADR-046: Ordered commercial request transport intent

- Status: ACCEPTED — FWD-03 bounded implementation only
- Date: 2026-09-16
- Owners: mission issuer (no undeclared human identity inferred); Commercial module
- Affected domain: request intake, transport intent, compatibility projections

## Context

FWD-03 starts at `1714118340943f1dbbf99e4b25edc9ef41f817e6` after FWD-01/FWD-02.
`ShipmentRequest` has scalar legacy, international and domestic transport fields.
It has no ordered arbitrary transport intent. `normalize_shipment_payload` ignores
an incoming sequence. `RouteLeg` belongs to `OperationalShipment -> RoutePlan`
and requires canonical endpoints and planned departure/arrival. ADR-002 rejects
adding operational legs to the request; ADR-004 owns operational route planning.
Neither permits silently treating an intake preference as an executable route.

## Problem and approval requested

Approve a bounded Commercial-owned ordered value on ShipmentRequest for customer
transport intent, expressly distinct from operational legs. This changes the
persisted request contract and its legacy precedence. Baseline section 2 and the
Codex development gate require named acceptance before implementing that change.
No new aggregate owner, operational route engine, AI or provider is requested.

## Decision (accepted for FWD-03)

1. Add nullable JSON `transport_intent` to ShipmentRequest, versioned as
   `{"version":1,"steps":[{"mode":"road"},{"mode":"sea"},{"mode":"road"}]}`.
   Array position is authoritative. Preserve repeated modes, including adjacent
   repetitions. Steps have no vehicle, terminal, endpoint, schedule or execution
   status. These are preliminary customer wishes, never operational commitments.
2. Commercial owns validation, supported-mode alias mapping and Persian labels.
   Initial supported modes are road, rail, air and sea. Existing catalog records
   remain authoritative for available choices; do not delete, renumber, merge or
   reinterpret them. Unknown historical strings remain verbatim readable. Unknown
   custom catalog semantics must be investigated, not guessed into a standard mode.
3. Classify intent as single-mode when its nonempty sequence uses one distinct
   supported mode, combined when it uses at least two. This classification never
   deduplicates the stored sequence. A chosen combined input requires at least two
   distinct modes; otherwise return a field error and preserve form state.
4. `customer_choice` requires an explicit nonempty intent on the new UI path.
   `forwarder_suggestion` may leave it null; do not fabricate a choice. Reject
   malformed shape, unsupported version/mode, or contradictory transport inputs
   with stable reason codes and field errors. Never silently discard intent.
5. New clients use the structured value. Old scalar submissions remain accepted
   when valid under the supported catalog contract, without inventing an order
   between international and domestic fields. Null intent means no recorded
   ordered intent, not an empty operational route. On reads, a non-null intent is
   primary; otherwise show historical scalar fields with their original scopes.
   Do not project a combined sequence into one false legacy mode.
6. Creation, validation and persistence remain in Commercial's application command
   and existing transaction. Revalidate current references and applicable authority
   at actual submission. UI uses the owner contract; future clients use the same
   command. Preparing a request confers no submission authority.
7. Request creation and reading do not emit `commercial.quote.available.v1`.
   FWD-01 notification ownership and approved quote transition remain unchanged.

## Alternatives

- Reuse the two scalar fields: rejected; cannot represent road/sea/road or order.
- Use free text/special instructions: rejected; loses structured identity.
- Reuse RouteLeg: rejected; confuses intent and execution and demands unknown data.
- Child aggregate/table: deferred; the ordered value has no independent lifecycle.
- Add only a combined label: rejected; cannot round-trip a customer's choice.

## Consequences

One small schema addition supports a lossless customer/expert chain. Every summary
must use the same projection. Old clients cannot fully display new combined intent;
this compatibility limitation must be explicit and tested, never hidden as single
mode. Existing unknown catalog semantics remain a bounded discovery item.

## Compatibility

No backfill, enum deletion, identifier changes, historical rewrite or new Draft
state. Opening incomplete requests never mutates them. Required cargo description
applies to new final submission (already explicitly authorized by FWD-03), not
historical reads. No invented weights, units or packaging requirements.

## Migration impact

Add one nullable JSON column after the actual sole head
`20260916_fwd01_notifications`. Historical migrations remain untouched. Explicit
upgrade only; no startup migration or geography import. Verify upgrade, downgrade
and re-upgrade on disposable representative PostgreSQL and preserve legacy rows.
Downgrade must refuse while non-null intent exists unless an separately authorized
export/removal decision is supplied; ordinary application rollback retains column.

## Security/tenant impact

Keep existing public intake authority: server-resolved hostname yields TENANT,
otherwise INTAKE. Body organization identifiers never authorize ownership. Customer
tracking capability is not authenticated customer ownership; preserve its existing
boundary and do not claim stronger isolation than tested. Authenticated expert and
admin reads use current assigned-work/tenant policy. Test reassignment, membership
revocation and cross-tenant denial without introducing a new permission model.

## Operational impact and rollback

No deployment, real message, paid API or Production mutation is authorized. Deploy
sequencing, if separately authorized later, requires schema before new writes.
Roll back application code while retaining column/data; do not erase combined
intent to satisfy an older client. Recovery evidence uses synthetic disposable DBs.

## Validation required after acceptance

- Direct command/API: sequence round-trip including road/sea/road, single mode,
  suggestion, malformed/unsupported values, blank cargo and field errors.
- Duplicate rail options from synthetic catalog; historical IDs remain readable.
- Customer submit/leave/reopen and expert read, RTL mobile/desktop real-role UAT.
- New-count/list equality on status=new with identical current authorized scope;
  one request remains one row despite multiple steps or quotes; refresh after writes.
- FWD-02 geography IDs, lifecycle, scope, and FWD-01 event/dedup regression.
- Tenant/actor negatives and revocation at actual commands; legacy incomplete reads.
- Migration and recovery proof, mandatory architecture/security/build/test gates.

## Supersedes / status history

- Supersedes: none. Clarifies commercial intent without superseding ADR-002/004.
- 2026-09-16: PROPOSED for FWD-03; awaiting explicit named Owner acceptance.

## Explicit acceptance history

- 2026-09-16: The mission issuer explicitly accepted named ADR-046 in
  “MISSION CONTINUATION: FWD-03 — ADR-046 Acceptance and Autonomous Completion”.
  Accepted proposal SHA256, verified before this lifecycle edit:
  `17511D21BB275EBB6D4B9088B3608141AB842ECD2E154883D4B798E7198E71F3`.
- Source: user-supplied `pasted-text.txt`, attachment
  `1f4cc6a6-52b9-4018-8661-47147d6b51ec`, this continuation conversation.
  Full execution constraints are preserved in the mission evidence acceptance brief.
- Scope: Commercial-owned ordered intent only; server-enforced new contract,
  scope-aware legacy compatibility, cargo validation, shared reads, bounded
  qualification, commit/push. No operational route, new aggregate/workflow,
  authority redesign, destructive history, real messaging, model API or Production.
- Acceptance is independent of implementation/test status. LPAF mother unchanged;
  v2.2 globally ACTIVE, v2.4 limited pilot only.
