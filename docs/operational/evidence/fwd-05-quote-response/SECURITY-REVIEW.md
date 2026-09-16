# FWD-05 pre-Build security review package

Date: 2026-09-16. Candidate start: `98a0364a6b6f97daf70152c7d3a5cefbb242cac0`.
Decision authority: ADR-047/PDR-019 ACCEPTED as explicitly amended, FWD-05 only.

## Exact retained gate

ADR-047 Decision §9: “Key provisioning/rotation and cryptographic separation must
pass Security review”. Owner continuation §3 preserves every ADR safeguard and
§10 requires secure grant/signing/delivery feasibility first. Product/architecture
acceptance and the reference-28 deferral do not record this Security review result.

FACT: the installed PyJWT library is already used in `backend/security.py`.
`SecurityManager.generate_token` creates staff access/refresh claims using the
shared `JWT_SECRET_KEY`; `verify_token` accepts that key with staff verification
skew and no quote issuer/audience/header-type contract. The existing revocation
service only accepts access/refresh tokens. Directly reusing those helpers is
insufficient for the accepted customer authority.

FACT: `FakeEmailProvider.send(reference, recipient, template)` carries no protected
message payload or private capture. It requires TESTING/fake/qualification and
restricts synthetic destinations. Registration currently logs the verification
URL; it is not successful delivery or a safe capability adapter.

ASSUMPTION: bounded extensions around this installed library/provider can safely
support the accepted capability. Primitive feasibility is supported by the probe;
complete key lifecycle and confidential delivery have not yet been implemented.

UNKNOWN: reviewed provisioning/rotation disposition and full runtime security
evidence. No existing acceptance/review record for this purpose was found in the
proposal, preserved discovery evidence or supplied continuation. No actual secret
values were inspected or recorded.

## Concrete design to review within accepted scope

1. Reuse PyJWT HS256; fixed verifier algorithm, issuer `forwarder.quote-response.v1`,
   audience `forwarder.quote-customer.v1`, header type `quote-response+jwt`, claim
   token_type `quote-response`; require iss/aud/iat/nbf/exp/sub/jti. No staff skew.
   No handmade cryptography, token-selected key URL or algorithm negotiation.
2. Purpose-exclusive server key ring plus configured active key version. Reject
   absent/placeholder/short key material and reuse of staff/app signing keys.
   Qualification injects ephemeral random material outside Git, no startup fallback.
   `kid` selects only an explicitly configured quote-purpose key. Provisioning
   material never enters DB, logs, traces, response payloads or reports.
3. Rotation: newly issued grants use active version; outstanding fixed-claim grants
   retain their signing version while configured for their existing read horizon.
   A removed key fails closed; compromise uses explicit audited revocation, never
   reactivates old grants. No retention/purge/automatic read-horizon extension.
4. Authorization owns persisted grant ID, immutable exact scope/recipient/claims,
   token digest, key version, read/write bounds and revocation. Commercial never
   returns raw tokens to staff. Adapter reconstructs fixed signed claims only at
   authorized dispatch and uses a fragment URL, with private fake capture outside
   Git. Capture cannot expose a staff HTTP token-fetch endpoint.
5. Delivery stays on existing FWD-01 outbox/action/attempt/results path. Dispatch
   revalidates originating actor/current assignment and exact recipient through
   Commercial/Authorization contracts, commits its short decision, then calls
   adapter. No worker authority substitution. UNKNOWN follows existing reconciliation.
6. Root/content/recipient/grant re-read under consistent documented locking;
   provisioning/rotation is not a substitute for live DB grant authorization.
   Existing actor/membership/organization/root/quote/recipient dispatch order must
   be reconciled with response/replacement/revoke paths before Build. PostgreSQL
   proves ordering, recipient changes, expiry and revocation; SQLite does not.
7. Customer token stays in page memory/fragment; dedicated Authorization scheme,
   JSON + Idempotency-Key, explicit same-origin/allowed-origin controls, no-store/
   no-referrer, no cookie-only/staff token writes. GET/preview/callback do no writes.
   Tracking POST and any other old writer are disabled at their command boundary.
8. Remove verification-link log only in the used connection. There is no complete
   certified real onboarding/delivery proof: DELIVERY/ONBOARDING_DEPENDENCY_OPEN.
   Staff readiness query exposes only state/reason and current assignee follow-up.

These are bounded implementation selections for the already accepted contract,
not a general Identity/key service, new product decision or deployment proposal.

## Probe result and limits

`backend/tests/test_fwd05_signing_feasibility.py`: 18 PASS. Checks installed-library
deterministic reconstruction/exact claims, distinct key rejection, signed wrong
issuer/audience/purpose/type, missing mandatory claims, expiry/not-before with zero
skew, wrong algorithm/unsigned/malformed tokens; explicit fake runtime selection
and synthetic destination rejection. No keys/tokens are printed or persisted.

This is a feasibility probe, not a production signer, grant command, private message
delivery, migration, PostgreSQL concurrency, browser journey or Security approval.
Gate status: SECURITY_REVIEW_EVIDENCE_PENDING. The interpretation used here is
that a required review result needs a traceable review disposition; no human
Security approver or approval is inferred from the main Agent's probe.

Review disposition needed: traceable Security review of the above provisioning/
rotation/separation approach, or explicit clarification of the authorized review
process. No renewed acceptance of D01–D06/reference deferral is requested.

## Phase A1 disposition and bounded repair contract

Actual separate reviewer `/root/security_reviewer` returned DESIGN_SECURITY_REVIEW
FAIL in [run A1](runs/20260916-A1/SECURITY-REVIEW-RESULT.md). That result is retained.
The following main-agent repairs address A01/B01/C01/D01/E02/E03/G01; they do not
change accepted ADR/PDR bytes, D01–D06, bearer risk acceptance, or claim runtime PASS.
IMPLEMENTATION_SECURITY_VERIFICATION = NOT_RUN; PRODUCTION_SECURITY = NOT_RUN.

### Exact signer and key admission

Authorization owns the quote-purpose signer, verifier and bounded key-policy
metadata. Trusted configuration contains a complete quote-only keyring, active
version and policy epoch; never SECRET_KEY/JWT_SECRET_KEY fallback. Each key is
strict canonical base64 of 64 bytes generated by the standard `secrets` CSPRNG
in qualification, or by authorized operational provisioning outside this mission.
Length cannot prove entropy: predictable human-selected material is prohibited.
Reject missing, malformed, placeholder, short, duplicate decoded material, or
material equal to normalized app/staff signing keys. Compare in memory without
logging values or key fingerprints. Operational secrets are not inspected here.
Kids match ASCII `[A-Za-z0-9_-]{1,32}` and resolve only this trusted mapping;
duplicate kids/config entries and multiple active keys are invalid. Invalid quote
configuration disables all quote issuance/verification/dispatch, not generic staff
authentication. No handmade cryptography, remote lookup, algorithm negotiation,
library monkeypatch, or startup default. Pin verified PyJWT behavior/version;
changed library/serialization requires reconstruction regression and review.

Header is exactly alg=HS256, typ=quote-response+jwt, kid=stored version. Reject
unsupported header keys (including crit/jku/x5u), missing/type-invalid/unknown kid,
wrong alg/typ, malformed or >4096-byte token before authority lookup. Claims are
exactly iss, aud, token_type, v, sub, jti, iat, nbf, exp, tenant, request, quote,
revision, content_digest. No unknown/missing claims. iss/aud/token_type equal the
fixed strings in §1; aud is one string, never an array. v=1 and revision=1 in this
slice, integers excluding bool. sub/jti/tenant/request/quote are canonical lower
UUID strings (subject is an opaque grant subject, not a claim of human identity).
content_digest is 64 lowercase ASCII hex characters. iat/nbf/exp are positive
integer Unix seconds excluding bool, within Python UTC datetime range; nbf=iat,
exp>iat. PyJWT fixed HS256/issuer/audience/strict_aud/required claims/zero leeway
validates registered claims in addition to this strict schema. Verify every claim
against persisted immutable grant and current exact fenced parents, recipient,
content and horizon; compare exact bearer SHA256 in constant time before authority.
Signature/schema alone never authorize. Duplicate/noncanonical signed encodings
cannot match the server's canonical stored exact-token digest.

### Key lifecycle, restart and compromised pending delivery

Key states are ACTIVE, VERIFY_ONLY, RETIRED, REVOKED, COMPROMISED. Only ACTIVE
creates a new grant. VERIFY_ONLY may verify and reconstruct ONLY an already
persisted fixed grant created while that version was ACTIVE, within its original
read horizon, with matching exact digest and live authority; this dispatch is
redelivery of existing authority, not new issuance. A normal rotation marks old
ACTIVE as VERIFY_ONLY and selects the new ACTIVE. RETIRED/absent/unknown keys deny
all use; retiring early can end access early and never extends it. REVOKED and
COMPROMISED deny read/write/dispatch immediately, including replay and pending
delivery; no retention-for-availability exception. A quarantined version cannot
return to ACTIVE/VERIFY_ONLY. Reissue requires a new active version and the current
certified recipient, revokes the old grant, preserves commercial facts/receipts
and the original horizon. No tracking-code recovery or automatic grant reissue.

Bounded Authorization policy metadata stores only version/state/epoch/audit,
never material. An explicitly authorized local policy command changes this
metadata transactionally; startup never initializes or modifies it. Every quote
operation obtains the policy serialization row before authority locks and checks
trusted configuration epoch/version/state against current DB metadata. A worker
with stale/missing configuration fails closed, so an old process cannot silently
retain a compromised key. All qualification processes inject the same synthetic
keyring/epoch; restart reloads it from their private environment. Rotation uses
an explicit policy transition and matching configuration rollout; mismatch causes
temporary denial, not fallback. No generic KMS or Identity service is introduced.
Pending PREPARED/retry dispatch rechecks policy/grant before each short claim;
revoked/compromised/stale actions become structured BLOCKED on their next claim,
without new authority or delivery. UNKNOWN only reconciles its original provider
reference, never sends/reissues. A dispatch committed before later revocation may
have sent its old link; customer consumption still rechecks live revocation.
Adapter checks current policy again immediately before reconstruction/send; a
revocation after that dispatch decision cannot be called physically unsent.

### Persisted deterministic reconstruction

At issuance, construct the strict flat JSON-compatible claim set once, using
integer UTC epochs and immutable IDs, no datetime/float objects in stored JSON.
Encode a new dictionary ordered by sorted claim names with PyJWT HS256 and the
fixed header. Persist those exact claims, kid and SHA256 of the resulting ASCII
token, never the token. Reloaded JSON/JSONB mapping order is untrusted: reconstruct
the same sorted dictionary, validate its schema, reuse stored iat/nbf/exp/jti and
stored kid, then sign with that key and compare exact token digest. Mismatch is
BLOCKED, not a digest update or renewed grant. Retry/restart/normal rotation never
uses the new active version for an existing grant. The isolated probe must prove
JSON serialization/deserialization with reversed/sorted mapping order, integer
epochs and exact identical token/digest. Actual DB reload/worker restart/rotation
and malformed stored claims remain Phase B requirements.

### Dedicated browser and exact origin mechanism

Use a dedicated `quote-response.html` customer entry, not staff App/router/API
helpers. Its dependency-free bootstrap reads the bounded fragment into a private
closure, immediately calls history.replaceState with the same clean path and no
query/hash, then dynamically imports the customer renderer. Invalid input is
cleared too; never put the capability in an error/URL/React Router/history state,
query key/cache, analytics, screenshot/trace, storage or staff helper. Reload of
the cleaned URL has no authority; reopening the private delivered link captures
it again. No automatic response POST; explicit human button sends JSON, dedicated
`QuoteCapability` Authorization and Idempotency-Key. No staff credential/cookies
or destination overrides. Use fetch credentials=omit, cache=no-store and
referrerPolicy=no-referrer. Render all quote text as escaped text; no raw HTML.
Generic global error handlers/providers, dev inspectors and telemetry do not
mount on this entry; errors and reason codes never include token or request headers.

Customer HTML has no third-party resources/scripts/fonts or service worker;
customer HTML/API use Cache-Control:no-store, Referrer-Policy:no-referrer and
X-Content-Type-Options:nosniff. Shell CSP: default-src 'none'; script-src 'self';
style-src 'self'; connect-src 'self' plus exact trusted qualification API origin;
img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'.
No inline script/style or unsafe-eval. Static serving must enforce shell headers;
local fixture proves them, Production serving is NOT_RUN. Tests/screenshots run
only after fragment clearing; no browser trace/video/HAR of private delivered URL.

Capability routes use a separate exact trusted QUOTE_CAPABILITY_ALLOWED_ORIGINS
scheme/hostname/port list, independent of generic dev localhost/wildcard CORS.
Reject unknown/null Origin, malformed/multiple Origin and cross-site fetch metadata
on writes, before grant command; absent Origin may be used by nonbrowser clients
with the same token/schema controls, never cookie-only authority. Allowed browser
origins may be the same origin or explicit isolated fixture origins. Purpose-route
after-request handling must not be broadened by generic CORS hooks. OPTIONS has
no business effects and permits exactly GET/POST/OPTIONS and Authorization,
Content-Type, Idempotency-Key for an exact allowed origin; no allow-credentials.
POST requires application/json (no form/text content), bounded body and dedicated
scheme; reject legacy/internal/refresh tokens. GET/preview/provider callback cannot
write response facts. Existing limiter/size facilities protect these routes;
redacted purpose-route exception responses never serialize DB exception input.
Private synthetic adapter capture uses fixture memory/private outside-Git file
with owner-only access, reference-keyed and erased at fixture teardown; no staff
HTTP retrieval. Provider persists only allowlisted reason codes/reference/outcome.

### Concrete serialization order and Phase B ownership

Total order: existing Notification action then attempt (worker-only); Authorization
key-policy serialization row; actor IDs ascending; membership IDs ascending;
organization IDs ascending; request/root IDs ascending; quote IDs ascending;
CRM customer IDs ascending; verified gamification IDs ascending; grant IDs
ascending; existing response facts/receipts. Fresh reread uses populate_existing
after locks. Unlocked IDs are only hints; changed issuer/assignee/parent/recipient
hints cause clean rollback and bounded retry (maximum three, then stable conflict),
never acquiring an earlier-order row after a later lock. Multi-root paths acquire
ALL roots sorted before any customers. Customer writes do not grant staff authority
to a customer; actor hints establish serialization, not customer authentication.

Commercial publish/replacement/response and Authorization revoke/reissue use this
shared helper and exact root. CRM link/unlink/create-from-request take relevant
authority then root then affected sorted customers; email/status/verification
updates that lock only a customer must acquire no later root/actor/policy locks.
Their row update serializes against the held customer lock; subsequent commands
reread recipient. Assignment/membership/org changes serialize on the locked
authority/root rows; audit their actual paths during Build. No root/grant-held
writer locks or updates a pre-existing Notification action/outbox event. It only
stages NEW events/inbox intents in its caller-owned transaction; consumer runs
after commit. Grant revoke/reissue does not touch pending action rows; their next
claim rejects stale grants. Worker retains action-first order, then the shared
authority order and commits short dispatch decision before any provider call.
Reconciliation/result locks action→attempt only, never business roots. Receipt
replay performs live policy/grant/parent checks before returning old success.

Main implementer owns Phase B code and executed evidence. Same separate reviewer
checks affected code/config/tests against this contract before final Commit/Push.
Required evidence: strict schema/key admission; DB JSON reconstruction; actual
restart/rotation/compromise/pending dispatch; API/log/outbox/private capture leakage;
real browser fragment/history/storage/cache/origin/GET behavior; PostgreSQL concurrent
response/replacement/revoke/recipient/assignment races and final persisted outcomes;
all ADR migration/tenant/regression/UAT gates. No runtime PASS inferred from probes.

### Phase A2 recipient-authority generation repair

[Actual A2](runs/20260916-A2/SECURITY-REVIEW-RESULT.md) is FAIL for F01: current
equality plus locks does not prevent change-away/change-back resurrection. Keep
A1/A2 findings unchanged. The following main-agent selection closes that precise
design gap, subject to A3 review; runtime remains NOT_RUN.

Add nonnegative monotonic `quote_recipient_generation` metadata to ShipmentRequest
(Commercial relationship owner), Customer (CRM email/status owner) and
CustomerGamification (registration email/verification owner). Initial generation
zero is an admission baseline, not reconstructed historical identity/change evidence.
No historical grant is issued or backfilled. New grant records snapshot all three
generations immutably alongside their exact root/customer/verified-customer IDs and
normalized email hash. These snapshots are DB authority metadata, not extra bearer
claims or a new identity system. Every read, write, receipt replay and dispatch
compares snapshots to fresh locked live rows; any mismatch permanently denies that
grant even if IDs/email/status later return to their former values. Reissue to the
currently certified recipient creates fresh snapshots and revokes prior grant,
without moving the original read horizon or deleting facts/receipts.

PostgreSQL BEFORE UPDATE triggers, installed explicitly by the additive migration,
own counter increments: root customer_id/gamification_customer_id changes; CRM
effective normalized email or status changes; gamification effective normalized
email or is_email_verified changes. Each actual relevant transition increments
OLD generation by one, including reversion; unrelated fields and same-value no-op
do not increment. Triggers reject caller counter override/decrement/reset and
counter overflow fail-closed. Root/CRM/registration application contracts never
accept this field from API input. Direct SQL/ORM/bulk updates cannot bypass the
PostgreSQL trigger. SQLite unit fixtures use owner-controlled application counter
updates for command semantics only, without a direct-SQL or PostgreSQL concurrency claim. Refresh
trigger-generated values after mutation; do not compare cached ORM snapshots.

Recipient-generation changes share the existing row locks and G01 order. A
customer-only update touches its own row/counter only, never subsequently locks
roots/policy/grants/actions. Link/unlink/relink/create-from-request acquire all
relevant roots before customers. Existing grants reference parents with RESTRICT
deletion, so deleting/recreating a parent cannot reset a referenced identity.
No automatic destructive grant invalidation history/purge is used. Phase B must
execute change-away/back tests independently for root link, CRM email/status,
verified email/verification, for read/write/replay and pending dispatch; test SQL
counter tamper/overflow, same-value and unrelated-field no-op; exercise trigger
and competing recipient/response/reissue races on disposable real PostgreSQL.
