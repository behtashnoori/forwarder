# ADR-047: Governed quote currency, revision and customer response

- Status: ACCEPTED — AS_EXPLICITLY_AMENDED; bounded FWD-05 development and qualification
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
authority, storage/time contracts and cross-domain writes. The original discovery prompt did not accept this ADR. The 2026-09-16
continuation explicitly accepts ADR-047 and PDR-019 as amended below.
No general identity/OTP, negotiation, workflow, financial or notification engine
is requested. No runtime/schema implementation occurred before acceptance. Security feasibility
and the retained Security review gate remain prerequisites for protected Build.

## Decision

The proposal was explicitly accepted with amendments on 2026-09-16. The reconciled decision below is development authority, not implementation or qualification evidence. Original proposal bytes are preserved in ../evidence/fwd-05-quote-response/proposals/.

### Ownership, money and effective quotation

1. Extend the existing Commercial-owned `ExpertQuote`; do not create a parallel
   Quote aggregate. UI/API/future authorized Agent consume the same Commercial
   command/query. Agent PREPARE never commits the customer's decision.
2. Commercial owns a bounded versioned supported-code contract IRR/USD/EUR,
   exposed by a read query used by the UI and validated by the publish command.
   This is the accepted bounded catalog owner, not a pre-existing catalog falsely claimed.
   Preserve stored codes/values and never convert toman/rial. Show exact code;
   do not assert an unknown historical unit. Existing unknown currency remains
   verbatim readable and is not assigned a default or made newly selectable.
3. New money contract `quote-major.v1`: EUR euro and USD dollar, at most two
   fractional digits; IRR integral rial, no toman conversion. Canonical ASCII
   decimal string API input/output, nonnegative 0..9223372036854775807 major
   units (including fractions below that ceiling), no rounding or binary float.
   Null, booleans, JSON numbers, signs, exponent, grouping, NaN/Infinity and
   overprecision are rejected before persistence. Zero is allowed explicitly.
   Storage selection: additive nullable `amount_exact NUMERIC(21,2)` plus
   `money_contract VARCHAR(24)` on ExpertQuote; existing BIGINT amount/currency
   remain unchanged for historical rows. New legacy amount must be nullable for
   fractional publications: never round/truncate or invent zero. Legacy numeric
   field is null with explicit `legacy_money_supported=false` and client-upgrade
   explanation when new exact amount cannot be represented safely; new clients
   consume exact string and contract. Historical values/codes remain verbatim,
   labeled `legacy-unspecified`; major/minor semantics are unknown without evidence.
   FWD-04 parsing/formatting is reused with bounded precision extensions. Digest,
   response snapshot, template and read projections include contract/exact string.
4. New publications have immutable UUID v4 public quote identity, revision 1
   and effective-content digest covering amount, currency, note, Local Date,
   validity-zone/policy snapshot. Corrections publish a new row with explicit
   replacement linkage, never edit old published content. Effective governed quote is the unique unreplaced row in its explicit chain;
   created_at sorting never grants supersession. Publish must explicitly match
   predecessor/effective quote under the same root lock as response. Accepted
   predecessor blocks replacement in this slice; declined may be replaced by
   the current authorized expert in an eligible request state. Negotiation may
   finalize on the same quote or be replaced by new immutable content. Prior
   final response remains; new response starts empty. Accepted correction/cancel
   needs future scope.
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
   This deliberate compatibility restriction is explicitly accepted by Owner.
8. Use a bounded quote-response capability, not a customer login system.
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
    and revokes the previous grant; old receipts remain in SOR. Reissue retains
    the original max(publication, expiry)+30-day horizon and cannot revive
    an expired grant using tracking code. Superseded grants read only their own
    quote/receipt, never replacement details; they lose write authority. Every read/write
    rechecks current scope/census and grant/recipient status. A final response
    does not itself revoke receipt reads. A revoked grant cannot replay success.
    Bearer forwarding/theft is a residual risk: this is delegated possession,
    not proof of a named human or non-repudiation. Staff cannot obtain/forge the
    grant through product routes, but stolen bearer possession cannot identify
    a staff impersonator. Stronger customer identity is a separate Owner decision.

### Customer response and transaction

12. Use stored codes `accepted`, `negotiation_requested`, `declined`, with
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
New publication is required to provide the governed path; implementation is not yet qualified. Legacy POST is intentionally disabled
for writes. N-1 must not retain that unsafe writer; rollback requires write shutdown.

## Migration impact

Selected additive migration contract after actual sole head `20260916_fwd03_transport_intent`;
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

- Supersedes: explicitly replaces only legacy
  tracking-code response-write authority/latest-target selection and mutable-only
  response contract; complements ADR-001/002/006/007/010/011/015/016/038/045/046.
  ADR-045's accepted FWD-01 scope is not retroactively widened; new policy authority
  would come from this separately accepted ADR only.
- Superseded by: none.

## Status history

- 2026-09-16: PROPOSED from inspected Candidate. PDR-019 business choices also
  require explicit acceptance. Product/schema/customer authority work STOPPED.

## Original proposal decision gate (historical)

The original proposal required named acceptance of D01–D06 and reference-28
mapping before Build. Its complete original language remains in the preserved,
hash-verified proposal. The 2026-09-16 continuation closes D01–D06 as amended
and explicitly defers access to reference 28 only for this pilot. Mapping stays
NOT_PROVEN. Technical feasibility and the Security review specified in Decision
§9 are retained, not waived by product/architecture acceptance.

## Explicit amended acceptance — 2026-09-16

DECISION_TYPE: ACCEPT_AS_EXPLICITLY_AMENDED. Decision authority: mission Owner,
no undeclared person/title inferred. Source: preserved owner-amended-acceptance.txt,
attachment 58dcf3a3-6fe2-4d7a-b261-9812c5934e9d. Verified original proposal SHA256:
229A22FEC79C5556BB349348A54EC0A60A2BA3DEC8C4BB1613E7393AAC174AFC.
The preserved original is historically PROPOSED; this lifecycle entry does not
rewrite it as originally approved. Exact amendments require no renewed acceptance.

Additional binding amendments: admin validity-zone setting is usable through
existing organization settings, audited, IANA validated; no startup defaults.
Missing setting blocks publication with Persian reason guiding expert to admin.
Recipient readiness distinguishes publication, ready/queued, simulated sent,
failed/unknown and BLOCKED; current assignee owns follow-up. Offer a remediation
link only if an actually complete authorized path exists. Otherwise record
DELIVERY/ONBOARDING_DEPENDENCY_OPEN. Synthetic verified fixture is permitted by
test contract and never proves real onboarding. Remove verification-link logging
in the used connection; removal never proves delivery. No staff token fetch,
forged verification or arbitrary recipient override.

Response read projections, related counters and inbox consume Commercial owner
query; request status and quote response are separate axes. Do not keep displaying
waiting for customer after response or introduce another display-status SOR.
Authorization owns grant validity; Notification owns delivery intent/attempts;
adapter owns private fake transport. Existing outbox/inbox contracts are reused.
Agent preparation never executes customer decisions or creates approval.

Missing reference disposition: NOT_PROVEN; access requirement deferred only for
FWD-05 pilot by explicit Owner decision; content/mapping unapproved. Review at
FWD-05 end or before actual release, whichever earlier. Mother LPAF unchanged.
Full security/crypto feasibility, PostgreSQL/migration/browser/regression gates
remain required. Historical replay missing evidence and Production identity UNKNOWN
remain open. No real messages, LLM API, Production, main merge or release.

## Reconciled Owner decision status

D01–D06 are CLOSED within the explicit amended scope. The original Open Owner
Decisions section above is retained as proposal history, not a current gate for
these exact decisions. Fresh consequential scope or active MUST conflicts still
return to Owner. Runtime feasibility and qualification are technical gates.

## Pre-Build security review material

See [security review package](../evidence/fwd-05-quote-response/SECURITY-REVIEW.md).
The isolated installed-library probe passed 18 checks. This proves primitive
feasibility and fake-provider gating only. It does not implement or certify grant
issuance, provisioning/rotation, recipient revalidation, private payload delivery,
transaction locking, browser controls or runtime revocation. No Security approval
record was found in the preserved proposal/evidence/continuation. Security review
status is EVIDENCE_PENDING under Decision §9, separately from ACCEPTED status.

## Selected schema and compatibility before Build

- ExpertQuote: additive nullable amount_exact NUMERIC(21,2), money_contract
  VARCHAR(24); existing amount BIGINT becomes nullable solely for new fractional
  rows, with a check requiring legacy amount for legacy rows and exact amount for
  quote-major.v1. Historical amount/currency are never updated. NUMERIC(21,2) holds
  the full 19-digit historical positive BIGINT domain plus two fractional digits;
  explicit nonnegative/BIGINT-major ceiling and currency-scale checks apply.
- New input is a canonical ASCII string: `0` or nonzero-leading integer, optional
  dot and 1–2 digits only for EUR/USD; IRR dot forbidden. At most 22 characters.
  Currency required and exactly supported; note/date bounded and strictly typed.
  Reject null/bool/number/empty/sign/exponent/grouping/leading-zero/NaN/Infinity,
  excessive scale, negative and overflow before any DB insert. Zero is valid.
  Exact decimal parse occurs only after lexical validation; no float conversion.
- New output amount_exact is canonical fixed scale 2 for EUR/USD and scale 0 for
  IRR, with money_contract=quote-major.v1 and explicit major-unit label. Legacy
  amount is numeric only when integral and safe in JavaScript's integer domain;
  otherwise null with legacy_money_supported=false and CLIENT_UPGRADE_REQUIRED.
  Never round/truncate or substitute zero. Legacy stored amount may remain exact
  integral BIGINT for integral new rows, but is not the new money SOR.
- Legacy read returns original stored string/code and money_contract=legacy-
  unspecified. Unit is unknown; no fabricated major/minor/rial/toman semantics.
  Response-history snapshots and content digest include exact contract/value/code,
  revision, note, Local Date, zone/policy/deadline. Notification templates/read UI
  must consume that projection instead of the old numeric field.
- Add opaque quote/content identity, publication Instant, revision/digest,
  predecessor/superseded linkage, UTC expiry, IANA zone/policy, response version;
  same-tenant constraints/unique effective chain checked in migration and service.
  Add bounded grant, response fact and idempotency receipt structures; register
  tenant inventory/census side effects and protected parent linkage. Grants/facts/
  receipts use exact quote/root references, immutable snapshots and UTC Instants.
- Organization nullable quotation zone plus audited existing admin command;
  no hidden startup configuration or expert policy payload. Deadline resolves
  TIME-BIZ-003 start-of-following-local-day with declared gap/overlap policy.
- Sole actual migration head remains 20260916_fwd03_transport_intent. No migration
  revision is created/reserved before retained Security gate. Populated downgrade
  refuses before DDL; application rollback retains schema/history and disables
  all old/new writers/dispatch. Empty roundtrip and retained-data recovery must
  be proved on disposable PostgreSQL before commit/push.

These selections are within Owner's explicit additive ExpertQuote authority.
They are unimplemented contracts, not tested runtime behavior or Security approval.
