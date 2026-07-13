# AI-READY-3A-G0 — In-Memory Advisory Proposal Prototype

## 1. Status and scope

- Baseline: `bdf7e015c60711c088ebf6cd0f61635b540d5c39`
- Governance authority: `AI_READY_3G_PROPOSAL_GOVERNANCE_DECISIONS.md`
- Capability: G0 missing-information and ambiguity review
- Execution: pure in-memory, deterministic, advisory only
- Provider: exact `deterministic_mock` mode only

This phase implements a narrow prototype for automated synthetic tests and human inspection. It does not approve a production feature or operational pilot.

## 2. Input boundary

The prototype accepts only the exact AI-READY-1 ShipmentRequest context contract version `1.0` and one explicit classification:

- `synthetic`; or
- `approved_deidentified`, with a bounded approval reference.

Values labeled real, operational, or production fail closed. The classification parameter is a governance assertion, not a de-identification engine. Callers remain responsible for creating synthetic data or completing the separately approved de-identification process before invocation.

The prototype does not read a ShipmentRequest, database, environment, file, email, attachment, network endpoint, or related record. The caller constructs the deterministic context first and passes the in-memory JSON object.

## 3. Output contract

`build_g0_proposal` returns a frozen `G0Proposal` containing:

- deterministic proposal and context fingerprints;
- input classification and optional approval reference;
- provider/mode provenance fixed to `deterministic_mock`;
- immutable missing-information and ambiguity findings;
- evidence field paths and source attribute references;
- explicit advisory/no-accept/no-bulk/no-apply/no-persist/no-write/no-send flags.

The output does not echo confirmed values, ambiguous candidate values, or the aggregate identifier. A missing-information finding cites schema absence. An ambiguity finding cites bounded source paths. Neither category proposes a replacement value, priority, commercial outcome, message, status, or action.

## 4. Deterministic behavior

The existing provider abstraction canonicalizes and fingerprints the complete context in memory. The deterministic mock performs no inference or I/O. The G0 service then projects only the allow-listed `missing` and `ambiguous` collections already produced by the deterministic context contract.

Finding IDs are hashes of category, field, reason, and evidence source paths. Proposal IDs additionally bind the context fingerprint, policy/schema versions, classification, approval reference, and finding IDs. No clock, randomness, database sequence, or process state is used.

## 5. Fail-closed validation

Execution is rejected when:

- input classification is not explicitly allowed;
- approved de-identified input lacks a valid approval reference;
- synthetic input incorrectly carries an approval reference;
- provider mode is not exactly `deterministic_mock`;
- context name, version, profile, mode, determinism, or classification differs;
- required context collections are missing or have the wrong type;
- field/evidence paths are malformed;
- missing or ambiguity reason is not allow-listed;
- ambiguity evidence is absent or inconsistent;
- findings exceed the bounded limit.

Errors do not include context values or rejected raw input.

## 6. Human review boundary

This prototype supports human inspection only. It has no reviewer identity, accept, reject, edit, approval, application, persistence, route, or UI API. This is intentional: AI-READY-3G states that acceptance has no effect and does not authorize a review workflow implementation in this phase.

Any future review lifecycle requires its own phase and must preserve evidence visibility, explicit human action, server-side authorization, staleness handling, idempotency, audit, and zero-effect failure semantics.

## 7. Prohibited behavior

The prototype has no path for:

- real customer or operational data;
- raw email or attachment content;
- real or local model provider;
- network, database, filesystem, environment, or configuration access;
- persistence, model, migration, route, or frontend behavior;
- external communication;
- automatic or bulk acceptance;
- proposal approval or application;
- canonical, status, quote, assignment, CRM, financial, or task mutation.

## 8. Test evidence

Synthetic tests verify:

- deterministic immutable output;
- exact G0 finding categories;
- absence of confirmed/candidate value echo;
- explicit synthetic/de-identified classification rules;
- exact deterministic-mock selection;
- contract/reason/evidence fail-closed validation;
- no database, network, environment, configuration, or file access;
- explicit no-accept/no-apply/no-write/no-send semantics.

Shared AI-READY-1/2/3A-G0 tests and the full backend suite remain the required local release gates for this phase.

## 9. Release boundary

Completion of AI-READY-3A-G0 does not authorize real data, a real provider, persistence, review UI, canonical effects, external sends, a controlled pilot, or deployment. Promotion beyond this synthetic in-memory prototype requires a new governance and release decision.
