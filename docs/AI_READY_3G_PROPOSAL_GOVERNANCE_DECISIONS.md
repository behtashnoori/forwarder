# AI-READY-3G — Proposal Governance Decisions

## 1. Decision record

- System: Forwarder freight-forwarding management system
- Baseline: `forwarder-14050324-ver-13` at `23c64cfb1718e6ec46212514d95493a930be1187`
- Status: **governance decisions approved; implementation remains not authorized**
- Parent architecture: `AI_READY_3_PROPOSAL_HUMAN_REVIEW_BOUNDARY.md`
- Scope: documentation and governance only

This record closes the governance choices left open by AI-READY-3. It does not create a proposal feature, permission, state machine, database object, route, user interface, provider integration, or operational approval process. All controls below are requirements for a separately approved future phase.

If this record conflicts with optional wording in AI-READY-3, this record governs. Existing application behavior and permissions remain unchanged.

## 2. Governance objective

Forwarder may use future machine-generated output only as bounded, attributable, evidence-backed assistance. Governance must prevent generated content from becoming operational truth or causing an effect merely because it was produced, displayed, scored highly, or accepted in a user interface.

The controlling separation is:

```text
generation != review
review != acceptance
acceptance != application
application != external send
```

Every boundary requires its own authorization, validation, idempotency, audit, and release decision.

## 3. Final capability classification

Every future proposal capability must be assigned exactly one tier before design or implementation begins.

| Tier | Meaning | Examples | AI-READY-3G decision |
|---|---|---|---|
| G0 — advisory observation | Read-only finding with no command payload | missing-information flag, ambiguity, contradiction, evidence-linked summary | Eligible for a future synthetic prototype |
| G1 — internal draft | Editable draft that still has no effect | draft next action, draft internal note | Not authorized; requires a separate capability decision |
| G2 — canonical mutation | Changes a Forwarder system-of-record value | shipment field/status, CRM link, task/activity, quote | Not authorized |
| G3 — external or high-impact effect | Communicates externally or creates financial/legal commitment | customer/partner message, email send, quote dispatch, destructive action | Prohibited until an independent governance and security phase explicitly reclassifies it |

Confidence, provider identity, reviewer seniority, urgency, or admin role cannot lower a capability tier.

### Decision G-01 — first eligible capability

The only capability class eligible for a future AI-READY-4 proposal is **G0 missing-information and ambiguity detection** against synthetic or de-identified shipment context.

That future capability may identify:

- a context field that is absent;
- two authorized context values that appear contradictory;
- a bounded clarification question for a human reviewer;
- evidence paths from the exact read-only snapshot.

It may not propose or infer a replacement canonical value, prioritize a shipment, recommend a commercial outcome, draft a customer message, or apply any effect.

This is eligibility for a future design/implementation proposal, not authorization to implement it in AI-READY-3G.

## 4. Human authority decisions

### Decision G-02 — human accountability

Only an authenticated natural-person user may make a review decision. Provider adapters, background jobs, service accounts, automation tokens, and generated identities may create or process candidates in a future system but can never accept, reject on behalf of a human, approve, apply, or override a decision.

The actor identity must be derived server-side from an access-token session. Client-supplied actor IDs, roles, timestamps, authority flags, or approval labels are non-authoritative.

### Decision G-03 — reviewer eligibility

For the first eligible G0 capability, a future reviewer must:

1. be an authenticated active user;
2. already be authorized to view the target shipment through current server-side rules;
3. be the assigned expert, or an admin acting within an explicitly audited supervisory review path;
4. be able to view every evidence reference required for the decision.

The current role hierarchy is not itself a proposal approval matrix. No new permission is implied or implemented by this document.

### Decision G-04 — self-review and separation of duties

For G0 advisory observations, the assigned expert may review an automatically generated candidate because review produces no canonical or external effect.

For any future G1, G2, or G3 capability, the person who materially authors or edits the proposed effect may not be its sole approver. At least one independently authorized human must approve under a capability-specific matrix. Admin status does not waive this rule.

There is no break-glass, emergency self-approval, or silent override in the initial governance model. A future emergency policy requires its own decision record, expiry, reason, notification, and post-event review before implementation.

### Decision G-05 — no delegated or inferred consent

Opening a proposal, leaving a page, inactivity, keyboard focus, a default selection, or a prior approval never constitutes review or consent. Each decision must be an explicit action against the exact displayed proposal version.

## 5. Decision and effect rules

### Decision G-06 — accepted is not applied

`accepted` records a human judgment about the exact reviewed content. It grants no database-write, status-change, CRM, quote, task, activity, message, email, or notification authority.

For G0, acceptance may only record the future review outcome; it has no canonical application step. For any later effect-bearing tier, application must be a separate authorized transaction through an allow-listed domain application service.

### Decision G-07 — no automatic or bulk acceptance

Automatic acceptance, threshold-based acceptance, timeout acceptance, and bulk acceptance are prohibited. The initial future review experience must decide each independent item explicitly.

Batch review may be considered only after production evidence shows that item independence, evidence visibility, error recovery, and per-item audit remain intact. It requires a new governance decision.

### Decision G-08 — reviewer edits create a distinct value

Generated value, reviewer-edited value, and any applied value are distinct audit concepts. An edit never rewrites the generated record. A material edit to an effect-bearing proposal creates a new review subject and must follow the capability's separation-of-duties rule.

### Decision G-09 — stale, superseded, expired, or conflicted proposals

These states are fail-closed and have zero canonical effect. They cannot be reopened in place. A fresh candidate/version and a fresh explicit review are required.

No state transition may silently copy an earlier acceptance to a newer proposal or context snapshot.

### Decision G-10 — rejection

Rejection is final for the reviewed version and has zero canonical effect. It requires an allow-listed reason code. Optional comments must be length-limited, access-controlled, and redacted from general logs.

Rejection data may support aggregate quality evaluation, but it may not be used as unreviewed operational truth or automatically alter shipment workflow.

## 6. Evidence and provenance decisions

### Decision G-11 — evidence is mandatory

Every reviewable item must cite bounded evidence from the exact authorized context snapshot or a separately governed immutable source. A proposal with missing, changed, inaccessible, or unauthorized evidence is non-approvable.

G0 missing-information findings may cite the versioned schema expectation plus the absence of the path. They must not manufacture a source span for absent data.

### Decision G-12 — minimum provenance

A future candidate must record at least:

- target type and ID;
- proposal and item IDs/versions;
- context fingerprint and schema version;
- capability and policy version;
- provider interface and mode;
- generation timestamp and run identifier;
- evidence references;
- lifecycle state and terminal reason;
- reviewer identity and decision timestamp when reviewed.

Provider/model metadata is provenance, not authority or proof of correctness.

### Decision G-13 — no secret or raw-content duplication

Proposal and audit records must minimize data. They may store bounded structured values, identifiers, hashes, classifications, and authorized evidence references. They must not duplicate tokens, credentials, unrestricted prompts, entire context bodies, raw private correspondence, or attachment bodies.

## 7. Real-data and retention decisions

### Decision G-14 — synthetic/de-identified data only

AI-READY-3G does not authorize real operational correspondence or unrestricted production shipment data for proposal generation. The first future prototype must use synthetic or approved de-identified context.

Use of real operational data remains NO-GO until data classification, lawful basis, access, processing location, provider retention, deletion, legal hold, incident response, and partner/customer notice requirements are approved in writing.

### Decision G-15 — retention is a release blocker

No arbitrary retention duration is selected in this phase because the repository does not establish the applicable legal and contractual schedule. Before real data is used, the Product Owner and accountable privacy/legal authority must approve a data-class-specific retention and deletion schedule.

Until that approval exists, real-data persistence is prohibited. Synthetic prototype artifacts must be disposable, access-controlled, and removed according to the prototype plan; they must not become a shadow operational archive.

## 8. Ownership and exception decisions

### Decision G-16 — named governance owners

The future capability proposal must name accountable human owners for:

- Product Owner: business purpose, tier, allowed outcome, and release decision;
- Domain Owner: operational vocabulary, evidence sufficiency, and unsafe inference rules;
- Security/Privacy Owner: data use, threats, redaction, retention, and provider boundary;
- Engineering Owner: transaction, authorization, observability, rollback, and kill switches;
- Quality Owner: evaluation corpus, thresholds, regression evidence, and release report.

One person may temporarily hold multiple owner roles in a small team, but each approval must be recorded by responsibility. Combining roles never removes the independent-approval requirement for G1–G3 effects.

### Decision G-17 — exceptions are fail-closed

There are no standing exceptions to capability tier, human authority, evidence, no-auto-accept, no-self-approval for effects, or real-data restrictions.

A requested exception requires a new versioned decision record that identifies scope, owner, reason, risk, compensating controls, start/end dates, monitoring, revocation, and post-event review. Absence or expiry of that record means the exception is denied.

## 9. Evaluation and release decisions

### Decision G-18 — success criteria for the first future G0 prototype

Before any controlled pilot, the future G0 capability must be evaluated on a versioned synthetic/de-identified corpus. The release proposal must report at least:

- missing-information precision and recall;
- contradiction/ambiguity precision and recall;
- evidence-path validity;
- unsupported-claim rate;
- abstention behavior;
- cross-shipment leakage rate;
- reviewer disagreement and edit/rejection rate;
- latency and deterministic failure behavior.

No numeric threshold is silently invented here. Thresholds must be proposed with the corpus and approved before implementation release. Any cross-shipment leakage, secret exposure, unauthorized effect, or external send is a release-blocking failure.

### Decision G-19 — independent gates

Generation and application require independent kill switches. Because the first eligible G0 capability has no application effect, its initial future release must keep every canonical-write and send path absent, not merely disabled in the UI.

Promotion to another capability or data class is a new release decision. Good G0 results do not authorize G1, G2, G3, real providers, real correspondence, or production writes.

## 10. Explicitly deferred decisions

The following are not silently approved; each requires a future decision record with repository and operational evidence:

- concrete persistence schema and migration;
- API and frontend contracts;
- new proposal permissions or role changes;
- real provider, model, SDK, key, endpoint, or environment selection;
- real-data classification and retention schedule;
- G1 internal drafts;
- any G2 canonical mutation;
- any G3 external or high-impact effect;
- bulk review;
- emergency/break-glass handling;
- numeric evaluation thresholds;
- production pilot, deployment, or rollback plan.

## 11. Governance acceptance checklist

A future phase may claim alignment with AI-READY-3G only if its proposal answers yes to every applicable item:

- [ ] The capability has one approved tier and cannot exceed it.
- [ ] Current behavior and future behavior are explicitly separated.
- [ ] The authorized human and target visibility rules are server-side.
- [ ] Evidence and provenance are complete and accessible.
- [ ] Acceptance and application remain separate.
- [ ] Automatic, timeout, and bulk acceptance are absent.
- [ ] Stale/conflict/expiry/supersession paths are zero-effect.
- [ ] Idempotency and concurrent-decision behavior are specified.
- [ ] Audit is structured, append-only, minimized, and redacted.
- [ ] Data class and retention authority are approved.
- [ ] Evaluation corpus, thresholds, and release blockers are approved.
- [ ] Kill switch, incident, rollback, and owner responsibilities are named.
- [ ] The phase does not introduce an unapproved provider, send path, or domain mutation.

Any unchecked applicable item is a NO-GO.

## 12. Final governance decision

AI-READY-3G approves a conservative governance baseline, not a feature:

- only G0 missing-information and ambiguity detection is eligible for a future synthetic/de-identified proposal phase;
- generated output remains advisory and evidence-bound;
- only authenticated humans may review;
- acceptance has no effect;
- auto, bulk, timeout, and effect self-approval are prohibited;
- real operational data, canonical mutation, and external communication remain NO-GO;
- exceptions are explicit, versioned, time-bounded, and fail-closed.

No implementation or deployment is authorized at the end of AI-READY-3G.
