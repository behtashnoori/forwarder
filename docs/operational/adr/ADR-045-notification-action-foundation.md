# ADR-045: Durable notification and governed action foundation

- Status: ACCEPTED
- Date: 2026-09-16
- Owners: FWD-01 mission issuer; no undeclared human identity inferred
- Affected domain: Commercial quote events, notification actions, integration execution
- Authority: explicit Owner message “FWD-01 — ADR-045 Owner Acceptance and Autonomous Implementation”, 2026-09-16. ACCEPTANCE_SCOPE = FWD-01 IMPLEMENTATION ONLY.

## Context

The verified baseline is `38431da96c4f36ceaa07c550e594bf2d08d34e38`.
`backend/services/quote_service.py:create_quote_for_request` already creates an
`ExpertQuote`, sets its `ShipmentRequest` to `waiting_for_customer`, stages an
expert log and an `ExpertConsoleNotification`, and commits. Customer workflow
and public tracking projections already read quotes. This is an existing
commercial transition, not a proposed new quotation lifecycle.

`OperationalOutbox` and `_outbox` in `operational_service.py` already provide
database-backed intent in a caller-owned transaction with ownership-census
provenance. They do not provide notification attempts or external delivery
semantics. Existing expert-console notifications are an inbox contract, not
an external provider queue. Registration email currently logs a simulated
email and verification URL; it is not a safe reusable delivery adapter.

`assigned_work_authorization.authorize_work_action` re-reads actor, membership
and work root, and recognizes `request.quote`. It is the existing bounded
authorization building block. A new provider action must not infer authority
from a legacy `role=admin` field or a caller-supplied organization.

## Problem

Preserve a required action intent atomically with one real business event,
then process it independently of the browser through a provider-neutral,
revocable, tenant-scoped command boundary. New action ownership and
cross-module coordination trigger the project's named architecture gate.
The original proposal did not confer acceptance. The explicit named Owner
decision recorded below now satisfies that gate for FWD-01 only.

## Decision

### Ownership and transaction

1. Commercial remains SOR for quote/request state and valid transitions.
   Expose a narrow quote-availability query/event contract; retain its current
   lifecycle and API response shape. Explicitly authorize this bounded
   commercial compatibility seam under ADR-002; add no execution lifecycle
   to `ShipmentRequest`.
2. Reuse the existing outbox table and census-fenced emission pattern through
   a public application contract. Do not make notifications depend on a
   private operational helper or write another module's ORM rows directly.
3. The quote application coordinator stages the quote and durable event in
   one local SQLAlchemy transaction. An event failure rolls back that
   transaction. Provider execution never occurs inside it (LPAF C-01).
4. Notification capability owns explicit action-request and delivery-attempt
   records, policy selection, recipient intent, execution state, bounded
   retries and reconciliation. The event consumer creates one logical action
   per tenant/event/policy/channel with a database uniqueness constraint.
   Consumer replay cannot create another logical action. Event consumption
   and action creation commit together. Do not consume unrelated outbox
   types or mark them published on behalf of another consumer.
5. Integration adapters own provider translation and communication. Business
   modules import neither provider SDKs nor AI SDKs. FWD-01 uses only a
   deterministic fake adapter; no live messaging or external LLM execution.

### Proof policy and recipient contract

Use `commercial.quote.available.v1`, identifying the newly committed quote,
request, authoritative tenant and initiating actor. A fixed, versioned
`quote-available.v1` policy decides whether a notification action can be
prepared. One event identity denotes one quote availability fact; repeated
business requests creating distinct quotes are not falsely claimed to be
deduplicated unless the existing command has an explicit idempotency key.

The proposed first channel is EMAIL with a fake provider. Recipient lookup
must follow the exact request/customer relationship, current ownership-census
guards and verified email, with no global phone/email search or arbitrary
contact fallback. A global `CustomerGamification` ID alone is not tenant
authority. Require certified same-tenant relationship evidence; if unavailable
or ambiguous, persist a structured blocked action with no provider call.
Only synthetic qualified customer records may be used for proof. Do not
invent customer consent or general CRM contact selection. SMS, IN_APP and
WEBHOOK are representable future channel kinds, not implemented providers.

Existing expert inbox behavior is preserved separately. Missing or invalid
recipient/channel must not corrupt the commercial transaction: the durable
event remains, and processing persists the reason for non-execution.

### Controlled commands and authorization

Expose application commands, not arbitrary database or provider tools:

- PROPOSE: report bounded capability for authenticated actor/current tenant,
  target and state; no mutation or arbitrary destination parameter.
- PREPARE: bind event, actor, tenant, target, recipient reference, channel,
  template/policy/tool versions and effective-parameter digest to an action.
- APPROVE: explicitly record approval requirement/disposition; where required,
  bind the approver, exact digest and expiry. Caller text cannot grant approval.
  The automatic proof path uses only the fixed policy's explicit delegated
  authority; this ADR grants no general elevated capability.
- EXECUTE: resolve current authorization using the existing assigned-work
  evaluator and commercial precondition query. Revalidate actor activity,
  membership, current assignment, tenant, quote visibility/validity, recipient
  relationship and any approval digest/expiry. Changed scope or parameters
  fail closed. Do not substitute a privileged worker identity for the actor.
- RESULT: tenant-authorized structured result/attempt query and controlled
  provider-result application, never arbitrary business-state mutation.

The first implementation must define a linearization point for dispatch
authorization and locking against reassignment/revocation, using the actual
database and existing mutation paths. Tests must cover concurrent changes;
an earlier page load or prepared action never constitutes execution authority.
If this cannot be achieved within the slice, stop under FWD-01 condition 9/10.

### Execution and failure contract

A small explicit CLI/worker entry point scans durable pending work with a
bounded batch. No scheduler infrastructure is required. Claiming is atomic
and competitive workers cannot concurrently submit the same action. Record
an attempt and durable claim before external submission. Expired in-flight
claims become UNKNOWN and require reconciliation; never assume a crash means
the external side effect did not happen.

Provider outcomes distinguish ACCEPTED, SENT, DELIVERED, FAILED and UNKNOWN.
Only an adapter with evidence may report DELIVERED. Definitive retryable
failures use bounded backoff and attempt limits; terminal/exhausted failures
remain queryable. UNKNOWN is not an automatic retry: use the stable provider
idempotency/reference to reconcile, otherwise require explicit resolution.
Do not claim exactly-once external delivery.

Provider-result handling binds tenant, action, attempt and provider reference,
rejects mismatches, and applies duplicate/out-of-order results safely.
Future signed callbacks can call this boundary after authentication; no
webhook route or receipt infrastructure is required for the fake adapter.

Store structured reason codes, actor/system provenance, event identity,
policy/template versions, requested/attempted/result Instants, retry count and
next retry time. These support future Attention queries without log parsing.
Do not store message bodies, credentials, bearer tracking codes or model
chain-of-thought merely for audit completeness.

## Alternatives

- Direct provider call in quote code: rejected; couples business to delivery
  and loses reliability when the request/browser/process ends.
- Reuse expert inbox rows as a provider queue: rejected; wrong recipient and
  lifecycle semantics, no attempts or unknown-outcome reconciliation.
- New broker or microservice: deferred; local outbox and database are present.
- General workflow engine or autonomous agent: excluded by mission scope.

## Compatibility

Keep existing quote, customer response and expert inbox contracts. Do not
backfill historical quotes or send retrospective notifications. Do not
reinterpret legacy naive timestamps, rewrite assignment governance, implement
pending unrelated ADRs, or change existing public customer journeys.

## Migration impact

Proposed additive action/attempt schema is required because current outbox
and inbox lack execution-result ownership. Final columns/constraints follow
implementation discovery. Use one new Alembic revision on the existing sole
head, real explicit migration tooling, tenant inventory registration and
same-tenant references. No historical migration edits or production access.
All new event/attempt times are aware UTC Instants; quote `valid_until`
remains a Local Date; retry delay/lease length are Durations.

## Security/tenant impact

Server-derived tenant and certified request/quote/customer lineage precede
disclosure or mutation. Treat queued parameters as untrusted until validated;
pin approved intent but not authorization. No arbitrary destination or raw
provider payload in a future Agent Tool. Unknown ownership and revoked access
remain explicit denials. Add new models to the tenant ownership inventory
and appropriate census/side-effect contracts; no census bypass.

## Operational impact and rollback

Deployment is outside FWD-01. Qualification runs only on disposable databases.
Future rollout upgrades schema before enabling the producer/consumer. Stop
the consumer to pause dispatch; retain events/actions/attempts and their
history. Application rollback must not delete or resend pending/unknown work.
Rehearse upgrade, downgrade on empty disposable tables, re-upgrade and data
preservation on representative PostgreSQL. For nonempty action history,
prefer retain-schema/roll-forward; no destructive production downgrade.

## Validation required after acceptance

Prove atomic transition/event rollback, duplicate consumer and worker safety,
provider failure isolation, observable failed/unknown states, safe retries and
reconciliation, fake success persistence, invalid recipient/channel rejection,
and absence of sensitive log output. Exercise actual assigned EXPERT actors
in two tenants, same-tenant unassigned actors, revoked/inactive/ambiguous
memberships, changed assignment/target/precondition and stale approval.

Run affected quote/customer/inbox, authorization, census, tenant inventory,
architecture, migration and concurrency tests plus repository mandatory
gates. Browser UAT is NOT_APPLICABLE only if the final slice changes no user
journey. Bind results to the final candidate; no unexecuted gate is PASS.

## Supersedes / superseded by

- Supersedes: none. Complements ADR-001/002/006/010/011/015/016 and existing
  assigned-work authorization without replacing those contracts.
- Superseded by: none.

## Status history

- 2026-09-16: PROPOSED during FWD-01 discovery. No acceptance, implementation,
  migration, qualification, release or production claim is made.
- 2026-09-16: ACCEPTED by the explicit named Owner decision in this conversation,
  with the previously presented summary and bounds. This does not certify
  implementation/migration, permit real messaging/LLM/Production, authorize a
  general workflow engine, or change LPAF global status.

## Owner execution criteria (2026-09-16)

Reuse the existing outbox; consume only the named quote event atomically with
its action. Preserve distinct quote identity. Short claim transactions must
release locks before provider calls. Fence expired claims and late results;
UNKNOWN requires reconciliation, never blind resend. Bind preparation to
actor/tenant/quote/recipient/parameters/versions, revalidate at dispatch, and
prove revocation/reassignment ordering on disposable PostgreSQL. Fake execution
requires explicit test/qualification configuration and synthetic destinations;
simulation results cannot constitute real delivery evidence. Qualification
includes migration recovery, concurrency, negative tenant/authorization and
existing behavior. Commit/push only after mandatory gates pass; verify remote
HEAD and zero ahead/behind. Preserve both known historical/production gaps.

## FWD-01 implemented contract details

- `backend/services/outbox_service.py:record_event` is the public staging
  contract; the existing operational `_outbox` delegates without changing its
  signature or other event families. A partial unique index gives this event
  family one record per tenant/quote. Outbox ID is its persisted event identity.
- `quote_notification_contract.py` is the Commercial read seam. An eligible
  recipient requires the exact request's tenant-owned, active CRM `Customer`
  and exact linked, email-verified `CustomerGamification`, with matching email.
  This conservative intersection creates no global email-search permission.
  Missing/foreign/quarantined/mismatched links block the action. Ineligible
  historical/uncertified customers are not silently repaired or backfilled.
- `NotificationAction` and `NotificationAttempt` are owned by the bounded
  notification service. Same-tenant request/event/action FKs and unique logical
  action/attempt constraints are database-enforced. New side-effect writes use
  the existing census fence; they are not a parallel ownership census.
- The existing `published_at` had no runtime dispatcher writer at the starting
  baseline. The quote-only consumer uses it to mean “this notification action
  was persisted”, not “a provider delivered a message”. Other event families
  are neither selected nor marked. There is no multi-consumer framework.
- Effective intent binds actor and authority, tenant, request, quote, both
  recipient identities, recipient/quote digests, EMAIL, template, policy and
  tool version. Digests bind intent; they are not an anonymization guarantee.
  The automatic authority is exactly `quote-available.v1`, originating in the
  committed Commercial event, subject to current `request.quote` authorization.
  No general service/admin account or inferred human approval is introduced.
- Interactive PROPOSE/PREPARE/APPROVE_WHEN_REQUIRED/EXECUTE/RESULT functions
  resolve the existing authenticated context. They accept no actor ID,
  arbitrary recipient, raw provider request or approval boolean. The one
  policy explicitly delegates the synthetic action; human-required approval
  policies and HTTP/Agent Tool publication remain future work, not implied
  authority. Unexpected approval dispositions fail closed.
- Claim locks the action, actor, memberships/organizations, request, quote and
  linked customer rows. The actor/root FOR UPDATE locks conflict with FK
  key-share acquisition for a new membership/quote, respectively. Existing
  updates/reassignment serialize against locked rows. The successful short
  claim commit is the final dispatch-decision linearization point. Revocation
  committed before it is observed; a concurrent later revocation can commit
  immediately after it, including while the provider is running. No claim is
  made that an already-authorized external submission can be recalled.
- Each attempt has a UUID fence/reference and 60-second lease. No database
  lock survives into provider execution. Expiry, exception or uncertainty
  yields UNKNOWN, including a result arriving after expiry before a reaper.
  Late or duplicate results cannot advance a replaced/finished attempt.
  Reconciliation queries the provider; only a definitive retryable failure
  permits another attempt, after current authorization is checked again.
  Retry is capped at three attempts with 30/60-second delays. Batch size is
  bounded to 1..100, with due work filtering and expired-claim catch-up.
- `FakeEmailProvider` supports deterministic simulated outcomes only. Runtime
  selection requires TESTING plus `NOTIFICATION_PROVIDER=fake` and
  `NOTIFICATION_ENVIRONMENT=qualification`. Destinations must use
  `example.test` or `example.invalid`. No network transport is implemented.
  CLI requires `--fake-qualification` and an explicit loopback PostgreSQL
  `FWD01_QUALIFICATION_DATABASE_URL` whose database starts
  `forwarder_fwd01_test_`; `--reconcile ACTION_UUID` never sends again itself.
- Additive revision `20260916_fwd01_notifications` follows
  `20260908_governed_international_geography`. Empty downgrade is supported;
  populated action history refuses destructive downgrade. Retain schema and
  roll application forward/back with dispatch stopped instead. Existing
  historical migrations and frozen deployment artifacts remain unchanged.
- Browser UAT is NOT_APPLICABLE: no page, navigation, customer interaction or
  response shape changes. Existing quote HTTP entry and independent worker
  are covered by an authenticated API integration test. This does not certify
  a future real messaging journey or deployment.
