# AI-READY-3 — Proposal and Human Review Boundary

## 1. Status and scope

- System: Forwarder freight-forwarding management system
- Branch baseline: `forwarder-14050324-ver-13` at `05dc42e5bf62ccf95c57f7ae15de77edac8d7c36`
- Phase: architecture and documentation only
- Decision: **design approved for a future implementation phase; no runtime capability is introduced here**

This document defines how a future AI-generated proposal may cross into human review without acquiring authority over Forwarder's canonical records. It extends:

- AI-READY-0: architecture and safety audit;
- AI-READY-1: deterministic read-only `ShipmentRequest` context;
- AI-READY-2: disabled-by-default, offline provider abstraction.

AI-READY-3 does **not** implement proposal storage, database models, migrations, routes, frontend components, provider connectivity, email, configuration, or deployment. Every schema, state, endpoint, permission, UI element, and transaction described below is conceptual unless explicitly listed as current repository behavior.

## 2. Multi-agent Codex design process

The Lead/Coordinator assigned five read-only specialist roles:

1. Domain and Workflow;
2. Backend and Transaction;
3. Authorization and Audit;
4. Frontend Interaction;
5. Test and Release.

The specialists were constrained to repository analysis and prohibited from editing. Their execution transports did not return complete summaries after bounded retries. The Lead therefore re-checked the requested scopes directly, resolved the design from repository evidence, produced this single document, and preserved the design-only boundary. The transport limitation is not product validation evidence and does not change the design decision.

## 3. Repository truth versus future design

### 3.1 Implemented today

- `shipment_context_service.py` builds a deterministic, read-only, classified snapshot and excludes sensitive or non-authoritative fields.
- `ai_provider_service.py` defaults to `disabled`; its only executable mode is an offline deterministic mock with advisory, no-write, no-send output.
- `ShipmentRequest` is the canonical operational anchor.
- Expert request detail already presents shipment facts, timeline, messages, and latest quote.
- Existing services enforce some admin/assigned-expert access and perform shipment status, quote, message, CRM customer-link, activity, and task writes.
- CRM customer create-from-request has a read-only preview followed by a separate reviewed create action.
- CRM customer linking records structured audit data and a console timeline event.

### 3.2 Not implemented today

Forwarder has no proposal aggregate, proposal item, review decision, evidence reference, proposal version, aggregate version check, expiry worker, proposal API, proposal UI, or AI-specific permission. It has no generic atomic application boundary that combines a review decision, domain write, audit record, and resulting event. AI-READY-2 does not generate real findings and cannot apply any effect.

The future state names and contracts below must not be used by callers until a separately approved implementation phase creates and tests them.

## 4. Core authority boundary

The only safe flow is:

```text
canonical read snapshot
  -> provider request
  -> advisory proposal
  -> persisted review candidate (future)
  -> authorized human decision
  -> fresh validation and staleness check
  -> existing domain application service
  -> canonical effect plus durable audit, atomically
```

Non-negotiable rules:

1. A proposal is never a canonical shipment fact, status, quote, message, CRM record, task, activity, or approval.
2. Generation and review are separate operations. Generation has zero domain-write authority.
3. Acceptance records human intent but does not bypass current domain validation or authorization.
4. The reviewed value, not a newly regenerated value, is the only value eligible for application.
5. Every effect is executed through a named application/domain service; models and provider adapters never write canonical tables directly.
6. Rejection, expiry, supersession, conflict, and provider failure produce zero canonical effects.
7. A proposal cannot send a message or email. Draft approval and external sending require separate future capabilities and separate explicit actions.
8. Proposal metadata, confidence, and model output never grant authority.

## 5. Conceptual proposal contract

### 5.1 Proposal envelope

A future proposal envelope should contain:

| Field group | Required meaning |
|---|---|
| Identity | opaque proposal ID and immutable proposal version |
| Target | aggregate type, aggregate ID, and captured aggregate/context version |
| Capability | allow-listed operation such as a field suggestion, missing-information finding, or draft next action |
| Provenance | context fingerprint, provider interface/mode, output schema, policy/schema versions, and generation timestamp |
| Lifecycle | current proposal state, expiry, superseding proposal ID, and terminal reason |
| Safety | advisory authority, human-review required, write/send flags fixed false until application is separately authorized |
| Items | bounded, typed proposal items with evidence and validation metadata |

Do not place raw secrets, tokens, unrestricted prompts, full logs, or arbitrary executable instructions in the envelope.

### 5.2 Proposal item

Each item should carry:

- stable item ID and type;
- exact target field or named future application command;
- proposed value in a versioned strict-JSON schema;
- optional reviewer-edited value stored distinctly from generated value;
- evidence references to authorized snapshot paths or immutable source spans;
- confidence/calibration metadata, never treated as permission;
- ambiguity, missing-information, contradiction, and abstention indicators;
- validation status and non-sensitive validation messages.

Items must be independently reviewable. Partial acceptance is permitted only when the capability contract defines item independence and the transaction cannot leave an invalid aggregate.

### 5.3 Evidence contract

Evidence must be sufficient for the reviewer to compare source, current canonical value, proposed value, and reviewer-edited value. Evidence references must be immutable, access-controlled, bounded, and tied to the exact context/provider run. Missing or inaccessible evidence makes an item non-approvable; it must not silently degrade to an ungrounded suggestion.

## 6. Conceptual lifecycle

### 6.1 States

| State | Meaning | Canonical write allowed? |
|---|---|---|
| `pending_review` | Complete candidate awaits an eligible reviewer | No |
| `in_review` | Reviewer has opened/claimed a specific version | No |
| `accepted` | Human approved the exact reviewed payload; application is not yet proven | No |
| `applying` | Short-lived internal transaction state, if required by implementation | Only through the governed application transaction |
| `applied` | One authorized domain effect and audit committed successfully | Already applied exactly once |
| `rejected` | Human rejected with a reason code | No |
| `superseded` | A newer proposal/version replaced the candidate | No |
| `expired` | Review window or underlying validity elapsed | No |
| `conflict` | Aggregate/context changed or application preconditions failed | No |
| `failed` | Generation or controlled application failed safely | No new effect; retry rules apply |
| `cancelled` | Authorized administrative withdrawal before application | No |

`accepted` and `applied` must remain distinct. A UI must never report success merely because a reviewer clicked Accept.

### 6.2 Allowed transitions

```text
pending_review -> in_review -> accepted -> applying -> applied
       |              |           |          |
       +-----------> rejected     +-------> conflict/failed
       +-----------> superseded
       +-----------> expired
       +-----------> cancelled
```

Terminal proposals are immutable except for append-only audit annotations. Reopening creates a new version or new proposal; it does not rewrite the old decision.

### 6.3 State invariants

- One proposal version has at most one effective terminal review decision.
- One accepted proposal item produces at most one canonical effect.
- A proposal cannot review or approve itself; provider/service identities are never reviewers.
- The reviewer acts on the exact version displayed.
- Generated and reviewer-edited values are both retained for accountability.
- Rejection requires a bounded reason code; optional comments are redacted and length-limited.
- Expiry and supersession never auto-accept or auto-apply.
- A stale proposal must be re-reviewed against a fresh snapshot.

## 7. Human review decision boundary

A future review command should include:

- proposal ID and version;
- selected item IDs;
- decision per item;
- exact reviewed values, including explicit edits;
- reviewer identity derived server-side from the authenticated session;
- reason code and bounded comment where required;
- expected target/context version and idempotency key;
- client correlation ID for diagnostics, not authorization.

The server must ignore any client-supplied actor, role, authority, applied flag, provider identity, or audit timestamp. It must reload the proposal, reviewer, target, and current canonical state inside the transaction.

Review must display and preserve four distinct concepts:

1. immutable source/evidence;
2. current canonical value;
3. generated proposed value;
4. reviewer-edited value.

## 8. Backend and transaction boundary

### 8.1 Future application service

One application/use-case boundary should own acceptance and application. Its order is:

1. authenticate an access-token session;
2. authorize reviewer role and target visibility;
3. lock or otherwise protect the proposal/version;
4. verify lifecycle, expiry, capability allow-list, evidence availability, and idempotency;
5. reload the target and compare the expected version/fingerprint;
6. validate the reviewed payload using current domain rules;
7. invoke exactly one named domain command or an explicitly atomic command group;
8. append review decision, before/after audit, and operational event;
9. mark the proposal item applied;
10. commit all effects together, or roll all of them back.

Current services often call `db.session.commit()` internally. A future implementation must first define transaction ownership so nested service commits cannot make proposal application partially durable.

### 8.2 Idempotency and concurrency

- Generation idempotency should be based on capability, target, context fingerprint, policy/schema version, and provider-run identity.
- Review/application idempotency must use a server-enforced unique key scoped to proposal version and reviewer command.
- Repeating an already successful command returns the original result without another write, notification, message, task, or audit effect.
- Conflicting decisions for the same item/version return a conflict and preserve the first committed decision.
- Optimistic version comparison or row locking must prevent acceptance against changed shipment state.
- Unknown transaction outcome is reconciled by idempotency lookup; it is never blindly retried as a new command.

### 8.3 Failure semantics

- Validation/authorization/staleness failure: zero writes.
- Domain or audit failure: full rollback.
- Post-commit notification failure: recorded separately and retried only if notification is an explicitly authorized effect; it must not replay the domain mutation.
- Provider failure: no review candidate unless a complete, validated envelope exists.
- Logs and error payloads must not echo context bodies, evidence text, reviewed secrets, tokens, or provider inputs.

## 9. Authorization and separation of duties

Current hierarchical roles are broad and are not an AI-review permission model. A future implementation needs capability permissions, for example:

- view proposal metadata;
- view sensitive evidence;
- claim/release review;
- edit a proposed value;
- reject;
- approve a specific capability;
- apply a specific domain effect;
- cancel/supersede administratively;
- view/export proposal audit.

Authorization must be evaluated server-side against role, shipment assignment/visibility, capability risk, data classification, and current target state. Admin hierarchy alone must not imply blanket approval of every AI capability.

High-impact capabilities such as quotes, shipment status changes, customer linking, external communication, financial terms, or destructive actions require their own policy. Some may require a second reviewer or must remain out of scope entirely. Self-review of a proposal generated or materially edited by the same actor may be forbidden by capability policy; where permitted, the audit must make it explicit.

Provider adapters, background jobs, and service identities may create candidates but cannot hold human-review permissions.

## 10. Audit contract

Every lifecycle transition should append a durable structured event containing:

- event ID/type/schema version and timestamp;
- proposal/item/version and target identifiers;
- actor type, authenticated user ID, effective role, and capability decision;
- old/new lifecycle state and bounded reason code;
- hashes or redacted snapshots of generated, reviewed, and applied values as appropriate;
- context/evidence/provider/policy provenance identifiers;
- expected and observed target versions;
- idempotency/correlation identifiers;
- application service/command and resulting canonical record IDs;
- success, conflict, rejection, rollback, or failure classification.

Audit is append-only and access-controlled. Human-readable console timeline entries may reference the structured event but cannot replace it. Never log raw tokens, API keys, full private correspondence, unrestricted context, or sensitive attachment bodies. Retention, deletion, legal hold, and export access require explicit policy before real operational data is used.

## 11. Frontend interaction design

The future review surface belongs in the existing expert request detail experience, not in a parallel AI operations application. It should:

- label all content as advisory and identify generated versus human-edited values;
- show evidence, current canonical value, proposal, conflicts, and missing information together;
- support explicit accept, edit-and-accept, reject, and defer actions per independent item;
- require confirmation for material effects and show the exact effect before submission;
- disable action controls while submitting and use an idempotency key for retries;
- distinguish `accepted`, `applying`, `applied`, `conflict`, and `failed` visibly;
- refresh stale canonical data before allowing re-review;
- never apply on navigation, refresh, keyboard focus, double-click, or optimistic UI alone;
- sanitize untrusted content and never render raw provider/email HTML;
- preserve Persian/English directionality, accessible labels, keyboard operation, focus management, and non-color-only status cues;
- hide sensitive evidence only as a usability aid; server authorization remains decisive.

Bulk acceptance should be absent initially. Drafting a message is not sending it; any future send action must have a separate confirmation, authorization, idempotency key, delivery audit, and release phase.

## 12. Test strategy for a future implementation

### 12.1 Contract and unit tests

- proposal schemas reject unknown capabilities, malformed values, oversized content, missing evidence, and unsafe authority flags;
- generation creates zero canonical writes;
- rejection, expiry, supersession, conflict, and cancellation create zero canonical effects;
- accepted and applied remain distinct;
- reviewer edits are retained separately from generated values;
- authorization is capability- and target-specific;
- error and audit serialization is redacted.

### 12.2 Transaction and integration tests

- concurrent acceptance attempts yield one effect and one effective decision;
- retry after timeout returns the original result without duplicate effects;
- stale target/context versions force conflict and re-review;
- domain write, structured audit, operational event, and applied state commit or roll back together;
- existing domain validation still rejects invalid reviewed values;
- cross-shipment and cross-role access is denied;
- PostgreSQL uniqueness/locking and migration downgrade/upgrade behavior are proven, not inferred from SQLite.

### 12.3 Frontend and browser tests

- evidence/current/proposed/edited values remain visually distinct;
- controls follow lifecycle and permission state;
- refresh, back navigation, double-click, retry, and two-tab races do not duplicate application;
- stale/conflict/error states preserve reviewer work safely;
- keyboard, screen-reader, RTL/LTR, and responsive behavior pass;
- untrusted markup is displayed as inert text.

### 12.4 Security and release tests

- access tokens, not refresh tokens, are required for review actions;
- provider/service identities cannot approve;
- audit tampering and unauthorized export are denied;
- logs contain no context bodies, secrets, tokens, or sensitive evidence;
- dependency, secret, static-analysis, container, and migration gates pass;
- a kill switch can stop generation and application independently;
- rollback and incident procedures are rehearsed with synthetic data.

## 13. Release gates

AI-READY-3 authorizes no implementation or deployment. A future proposal implementation remains **NO-GO** until all of these are approved:

1. capability-specific product policy and risk classification;
2. concrete schema and migration review;
3. transaction ownership and PostgreSQL concurrency proof;
4. server-side permission matrix and separation-of-duties decision;
5. structured audit, redaction, retention, and incident policy;
6. evidence/provenance and stale-context contract;
7. frontend review usability/accessibility acceptance;
8. deterministic synthetic test corpus and thresholds;
9. independent security review;
10. deployment, rollback, monitoring, and kill-switch plan.

A first implementation should support one low-risk, read-oriented capability with synthetic/de-identified data, no bulk approval, no external send, and no autonomous canonical write.

## 14. Explicit non-goals

This design does not approve or define implementation details for:

- real AI providers, SDKs, keys, endpoints, or environment selection;
- email ingestion, attachments, outbound communication, or delivery tracking;
- autonomous agents or tool use;
- proposal database tables or migrations;
- API routes or frontend components;
- direct provider-to-database access;
- automatic shipment, CRM, quote, task, activity, message, or status changes;
- vector databases, embeddings, queues, local models, or deployment.

## 15. Unified decision

Forwarder's safe boundary is a **proposal, decision, and application separation**:

- provider output is advisory and inert;
- human review is explicit, evidence-based, version-bound, and attributable;
- acceptance is not application;
- application is a separately authorized, idempotent, stale-safe transaction through existing domain services;
- audit and canonical effects are atomic;
- all non-success terminal states are zero-effect.

This is the required architecture baseline for any later proposal persistence or review UI phase. No such implementation exists at the end of AI-READY-3.
