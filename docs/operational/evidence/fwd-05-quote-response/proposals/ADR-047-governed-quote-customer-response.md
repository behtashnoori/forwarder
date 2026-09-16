# ADR-047: Governed quote currency, revision and customer response

- Status: PROPOSED — NO IMPLEMENTATION AUTHORITY
- Date: 2026-09-16
- Owners: FWD-05 mission issuer for explicit Product/Architecture acceptance;
  Commercial for quotation/response; Authorization for scoped customer authority;
  Notification for delivery; Provider Adapter for transport. No human identity inferred.
- Affected domain: Commercial quotation (existing `ExpertQuote` compatibility
  model), customer visibility/action, expert inbox, bounded notification policies.

## Context

Verified root: `D:\1-webapp\forwarder-dev`; start branch
`feature/fwd-04-presentation-integrity`; start HEAD
`98a0364a6b6f97daf70152c7d3a5cefbb242cac0`; clean worktree; origin is
`https://github.com/behtashnoori/forwarder.git`. FWD-01/02/03 are ancestors.
FWD-05 branch was absent locally/remotely and is created from that exact HEAD.

`quote_service.create_quote_for_request` publishes a new row, moves the request
to `waiting_for_customer` and emits `commercial.quote.available.v1`. Multiple
rows are allowed. There is no quote public identity/revision/immutable content
contract. Money is integral BIGINT; currency is unconstrained text; the UI has
IRR/USD only and incorrectly labels IRR as toman. No authoritative Commercial
currency catalog was found; Economics is not quotation authority.

`customer_gamification_service.record_quote_response` accepts accepted/declined
with a tracking code, locks the request, selects the latest quote at processing,
and writes one mutable response plus naive `responded_at`. It does not receive
the observed quote/version, check a separate write grant, or check request state.
Identical response replays, conflicting response conflicts. The schema excludes
negotiation. It marks unread and logs but creates no customer-response inbox item.
Existing public tracking is a visibility contract, not certified customer identity.
ADR-038 expressly preserves tracking semantics and does not approve write authority.

TIME-BIZ-003/004 already approve next-local-day expiry with customer/market zone,
issuer-organization fallback, applied-policy snapshot and system receipt time.
The current response and FWD-01 eligibility code instead use `date.today()`.
No authoritative customer/market or issuer-organization quote timezone field was
found in the inspected models. FWD-04 presentation timezone is not domain authority.

## Problem

Baseline §2 and CODEX-DEVELOPMENT-GATE require named acceptance for changed
authority, storage/time contracts and cross-domain writes. The product prompt
does not accept this ADR. PDR-019 separately proposes business decisions below.
No general identity/OTP, negotiation, workflow, financial or notification engine
is requested. No runtime/schema implementation occurs before acceptance.

## Decision

All paragraphs below are proposals, not current behavior or accepted policy.

### Ownership, money and effective quotation

1. Extend the existing Commercial-owned `ExpertQuote`; do not create a parallel
   Quote aggregate. UI/API/future authorized Agent consume the same Commercial
   command/query. Agent PREPARE never commits the customer's decision.
2. Commercial owns a bounded versioned supported-code contract IRR/USD/EUR,
   exposed by a read query used by the UI and validated by the publish command.
   This is a proposed catalog owner, not an existing catalog falsely claimed.
   Preserve stored codes/values and never convert toman/rial. Show exact code;
   do not assert an unknown historical unit. Existing unknown currency remains
   verbatim readable and is not assigned a default or made newly selectable.
3. Preserve integral nonnegative BIGINT money: canonical ASCII integer string
   input, exact range 0..9223372036854775807, string output on the new contract.
   FWD-04 parser handles Persian/Arabic/grouped UI input before submission;
   backend rejects noncanonical strings, booleans, fractions, unsafe JSON numbers,
   malformed currency/date and overflow. No rounding, FX or multi-currency sum.
   Keep legacy numeric read shape where required; new response UI uses exact strings.
4. New publications have immutable UUID v4 public quote identity, revision 1
   and effective-content digest covering amount, currency, note, Local Date,
   validity-zone/policy snapshot. Corrections publish a new row with explicit
   replacement linkage, never edit old published content. Effective quote is
   selected deterministically by (created_at, id) with replacement linkage;
   a later publication supersedes the prior effective row under the request lock.
   Response sequence/version is separate from immutable content revision.
5. For new publication require valid_until and an authoritative zone. Implement
   only the issuer-organization fallback where no certified customer/market zone
   exists: a narrow Organization Admin command sets the organization's quotation
   validity IANA timezone, auditable and nullable until explicitly configured.
   Ordinary experts cannot change that configuration in a quote payload.
   Snapshot its value/source and TIME-BIZ-003 version in the quote; refuse publish
   if no valid source exists. This is not a general timezone configuration engine.
   A later configured value does not alter previously published expiry.
6. Resolve expiry once as start of following local calendar day in that snapshot
   zone, using domain timezone helpers and an explicit DST resolution (first valid
   instant at/after next-day start if midnight is skipped; earliest occurrence if
   ambiguous). Store the resolved UTC deadline alongside policy evidence.
   Respond only when database system receipt Instant < deadline. Browser/server
   timezone and artificial UTC midnight are never substitutes. Reuse this
   Commercial eligibility query in affected FWD-01 dispatch checks.

### Scoped customer authority

7. Tracking GET remains read-only; tracking code, numeric IDs, phone/email or body
   tenant cannot authorize a new decision. Retire the unsafe tracking-code POST
   for writes with a uniform action-unavailable response; do not leave a bypass.
   This deliberate compatibility restriction needs Owner acceptance.
8. Propose a bounded quote-response capability, not a customer login system.
   It is bound to tenant/request/quote/content revision/digest and the exact
   certified recipient relationship used by FWD-01 (active same-tenant Customer
   plus exact linked email-verified CustomerGamification with matching email).
   If missing/ambiguous, publish may succeed but capability delivery is BLOCKED;
   do not search globally or invent a customer/consent relationship.
9. Reuse existing token cryptography with a separate issuer/audience/type and
   signing purpose. Persist an opaque grant ID, effective claims/token digest,
   key version, recipient references, issue/expiry/revocation Instants; never raw
   bearer tokens. The bounded delivery adapter derives the signed token from
   fixed persisted claims at dispatch using a purpose-separated server key.
   Internal access/refresh JWTs are rejected and cannot act for a customer.
   No endpoint returns the capability to experts/admins or allows destination
   override. Staff authority permits publication/delivery only, not response.
   Key provisioning/rotation and cryptographic separation must pass Security
   review; if existing facilities cannot support this safely, stop, not build
   a general Identity system. Existing internal signing secrets are not exposed.
10. A capability link uses a fragment, not query/path logging. The customer UI
    sends it in a dedicated Authorization scheme; it is not cookie authentication.
    No token in localStorage, analytics, logs, public reports or Git. Customer
    may retain their private delivered link for reopen. Set no-referrer/no-store,
    restrict CORS to explicit allowed origins, require JSON plus authorization
    header on POST; reject cookie-only/internal-token requests. No GET, preview,
    provider callback or automatic page action records a decision.
11. Grant allows quote/history reads for 30 days after the later of publication
    or quote expiry; new writes stop at quote expiry, supersession, revocation,
    recipient-link change, inactive organization or prohibited request state.
    Authorized reissuance delivers only to that currently certified recipient
    and revokes the previous grant; old receipts remain in SOR. Every read/write
    rechecks current scope/census and grant/recipient status. A final response
    does not itself revoke receipt reads. A revoked grant cannot replay success.
    Bearer forwarding/theft is a residual risk: this is delegated possession,
    not proof of a named human or non-repudiation. Staff cannot obtain/forge the
    grant through product routes, but stolen bearer possession cannot identify
    a staff impersonator. Stronger customer identity is a separate Owner decision.

### Customer response and transaction

12. Propose stored codes `accepted`, `negotiation_requested`, `declined`, with
    nullable/no-response unchanged. Negotiation may proceed to accepted/declined
    on the same still-eligible quotation; no counteroffer/chat is included.
    Accepted/declined are terminal on that row; no reopen or rewrite.
    Preserve append-only response facts (opaque ID, tenant/root/quote, content
    identity/digest and exact money/date/zone snapshot, grant/subject provenance,
    prior/new response, sequence, system response_received_at/recorded_at and
    bounded reason code). Existing quote response columns become a controlled
    latest-response compatibility projection, not a second SOR.
13. New POST targets quote public ID and expected content revision/digest plus
    expected response version; it requires Idempotency-Key. Scope identity is
    grant/actor + tenant + quote/content version + key. Stored request digest
    covers response, expected response version, reason and all effective inputs.
    Same key/different digest => 409; same key/same digest retrieves its exact
    receipt after live authorization, without new effects. Keep receipts/keys
    as business history; no automated expiry/purge in this slice.
14. Serialize publish/replacement/response and grant revoke/recipient-link change
    against the same request/root and required authority rows using a documented
    consistent lock order. Re-read after locks; verify target is still effective,
    content/state/version unchanged, grant scope valid and deadline not reached.
    Incompatible concurrent decisions: one commits, the other returns 409.
    After checking a stored operation replay, a new operation with stale response
    version conflicts. New identical-response operation at current version is a
    no-op receipt referencing the prior fact, never a new fact/event/inbox item.
15. One caller-owned local transaction stages response, compatibility projection,
    version, audit, idempotency receipt and durable response event/inbox intent
    through owner contracts. Failure rolls all back. Provider calls occur only
    after commit; delivery failure/UNKNOWN never undo a business response.
    Receiving customer time is optional evidence only and cannot replace system
    receipt time. No operational Shipment, payment, won/lost, booking or transport
    starts from this command; ShipmentRequest.status stays unchanged.

### Behavior table (all allowed rows require current scoped grant)

| Effective quote/content; current response | Input and preconditions | Result | Quote effect | Request effect | Notification/history |
| --- | --- | --- | --- | --- | --- |
| Current/unexpired; none | accepted / negotiation_requested / declined; correct versions | ALLOW | append fact; update response/version only | status unchanged; unread current assignee | one response event/inbox intent; exact snapshot |
| Current/unexpired; negotiation_requested | accepted / declined; correct versions | ALLOW | append terminal fact; version +1 | status unchanged; unread current assignee | one new response event/inbox intent; negotiation retained |
| Any response | identical persisted key/digest; live read/replay authority | REPLAY | none | none | exact prior receipt; no new event |
| Current/unexpired; existing response | same response, new key, current response version | NO-OP | none | none | receipt refers to prior fact; no new event |
| accepted / declined | different response, including negotiation | DENY 409 FINAL_RESPONSE | none | none | no business effects |
| Old revision/digest/response version or superseded quote | any new response | DENY 409 QUOTE_CHANGED / RESPONSE_CONFLICT; refresh | none | none | no business effects; never retarget latest |
| Expired, missing policy/identity, legacy-only or request not waiting_for_customer | any new response | DENY 409 QUOTE_NOT_ELIGIBLE | none | none | history readable within authorized scope |
| Missing/foreign/revoked/invalid grant; tracking/internal token only | any response/read protected details | DENY uniform unavailable/not-found | none | none | bounded redacted security evidence only |

### Visibility and notification reuse

16. Commercial query shows current response and exact history to the current
    authorized assignee and Organization Admin within existing assigned-work
    policy; former assignees cannot read fresh details even via retained inbox IDs.
    Inbox recipient resolution is live assignment + active membership/permission,
    not quote creator. New response event `commercial.quote.customer-response.v1`
    has one identity per tenant/response fact. It is NOT quote.available.
17. Reuse outbox and existing expert inbox via narrow owner contracts, with
    database dedupe by tenant/response/recipient. On reassignment, pending response
    attention routes to the new valid assignee; old entries cannot reveal fresh
    content. Resolve/revalidate at consumption/query and serialize assignment
    changes at the chosen notification decision point. No parallel Attention engine.
18. Extend Notification only with named fixed quote-capability delivery policy
    and current-expert response policy. Response business event contains references
    and structured facts, no raw tokens/contact/body. Any optional fake external
    expert delivery requires a certified synthetic expert destination; otherwise
    persist structured BLOCKED, with the valid expert inbox as primary evidence.
    Quote.available keeps its publication-only semantics; add neither duplicate
    availability events nor multi-consumer infrastructure. Fake capability delivery
    is a bounded adapter of the existing notification path, not logged registration
    URLs or a public token-fetch test endpoint. Test artifact is private/outside Git.

## Alternatives

Tracking-code POST/implicit latest: rejected for wrong authority/stale intent.
General customer Identity/OTP and negotiation engine: deferred, outside mission.
In-place quote edits/last-write-wins/mutable response history: rejected.
Direct provider call/new queue/worker business authority: rejected.
Requiring a replacement quote after every negotiation: valid business alternative
but not recommended; PDR-019 explicitly requests same-quote finalization acceptance.

## Consequences

Adds bounded grant/history/version/policy storage and deliberate legacy POST
restriction. Improves traceability/retry safety; delivery is still separate from
commercial success. Requires signing-purpose lifecycle and protected delivery
material. Bearer compromise/forwarding remains a documented risk. Missing recipient
or configured domain zone must be visible, not repaired by a guessed value.

## Compatibility

Preserve old amount/currency, quote rows, request statuses and tracking GET.
No historical response inference or token issuance/backfill. Legacy responses
remain labeled legacy evidence without invented actor/version/time snapshots;
historical rows without sufficient policy/identity cannot accept new decisions.
New publication provides the governed path. Legacy POST is intentionally disabled
for writes. N-1 must not retain that unsafe writer; rollback requires write shutdown.

## Migration impact

Additive migration after actual sole head `20260916_fwd03_transport_intent`;
do not reserve a guessed revision ID. Add nullable quote identity/content/expiry
snapshots, response version, explicit replacement linkage, bounded grant and
append-only response/idempotency structures and organization quote-zone policy.
Expand response constraint/length only as needed. All new Instants are aware UTC;
valid_until stays DATE. Same-tenant parent FKs, positive-version/uniqueness checks,
tenant inventory and census fences apply. No rewriting historical migrations,
bulk catalog population, inferred history or broad drift repair.

## Security/tenant impact

Tenant derives from validated grant and fenced exact parent, never body/identifier.
Internal actors cannot call customer decision with staff JWT or issue arbitrary
recipient grants. Apply rate/abuse limits and size bounds using existing facilities;
prove cross-origin/cookie/IDOR/replay behavior, digest mismatch and live revoke.
No raw capabilities, customer data, sessions or provider credentials in evidence.

## Operational impact

Qualification only: existing FWD-04 fixture/launcher/timezone runner, extended for
valid FWD-03 intake, certified synthetic recipient, actual assignment/publication
and customer capability delivery. Explicit TESTING + fake + qualification;
synthetic example.test/invalid only. Disposable PostgreSQL native cluster, own
data directory/loopback port, never existing colleague/service DB. No real sender,
Production, deploy, release, external LLM or broad process shutdown.

## Rollback

Stop governed writes/dispatch, retain schema/history/grants/keys/events. Never
re-enable tracking-code writes as rollback. Downgrade only empty new structures
with transactional refusal before DDL if any decision/grant/policy history exists;
otherwise use retain-schema application rollback/roll-forward. Do not delete
legitimate decisions or regenerate identities; issuance revocation is audited.

## Validation

After acceptance: domain/API amount/currency/date/version/state/authority tests;
same-key mismatch/retry, final/no-op semantics; exact snapshot/history/reopen;
live assignment/revoke/recipient/tenant/census negative tests; existing FWD-01
failure/UNKNOWN/reconciliation and publication-only regressions. Real PostgreSQL
concurrent incompatible decisions, retries, replacement/revoke/expiry races and
final persisted assertions; migration upgrade/empty roundtrip/data preservation/
safe populated refusal/application recovery. No mock concurrency claims.

Browser: actual synthetic expert login/assignment/EUR publication, scoped customer
read/negotiation/final receipt, expert inbox, leave/reopen both, expiry/stale refresh,
read-only tracking denial, desktop/mobile RTL and UTC/America-New_York contexts.
Expected independently from fixture/contract, not copied from product output.
Mandatory backend/frontend/structure/architecture/tenant/secret/diff gates before
commit/push; no absent UAT promoted to PASS. Historic replay/Production gaps stay.

## Supersedes / superseded by

- Supersedes: none while PROPOSED. If accepted, explicitly replaces only legacy
  tracking-code response-write authority/latest-target selection and mutable-only
  response contract; complements ADR-001/002/006/007/010/011/015/016/038/045/046.
  ADR-045's accepted FWD-01 scope is not retroactively widened; new policy authority
  would come from this separately accepted ADR only.
- Superseded by: none.

## Status history

- 2026-09-16: PROPOSED from inspected Candidate. PDR-019 business choices also
  require explicit acceptance. Product/schema/customer authority work STOPPED.

## Open Owner decisions

Accept or amend this exact ADR and PDR-019: bearer delegation/residual risk and
legacy POST restriction; same-quote negotiation-to-final and no request-status
effect; Commercial currency ownership/exact-code display; narrow Organization
Admin validity-zone fallback; grant read duration/key purpose/delivery scope.
Confirm the authoritative replacement/mapping for the missing `D:\1-webapp\28-AI-Rules`
reference before Build; the discovered Engineering Framework folder is not silently
promoted to that authority. Runtime crypto/delivery feasibility is a technical
validation gate, not permission to invent a general authentication service.
