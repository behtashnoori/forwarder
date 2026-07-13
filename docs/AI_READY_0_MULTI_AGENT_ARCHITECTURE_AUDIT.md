# AI-READY-0 — Multi-Agent Codex Architecture Audit

**System:** Forwarder freight-forwarding management system

**Branch audited:** `forwarder-14050324-ver-13`

**Audit date:** 2026-07-13

**Phase:** Architecture, boundaries, readiness, and technical-debt analysis only

## 1. Executive decision

Forwarder is **partially ready for architecture work, but not implementation-ready for real email ingestion or AI-assisted operational processing**.

The repository has valuable foundations: `ShipmentRequest` is a clear operational anchor; expert request detail already combines shipment, customer, route, timeline, messages, and quotes; CRM activities/tasks can receive approved operational outcomes; role checks protect the main internal surfaces; and the CRM customer preview/link flow demonstrates review-before-write and structured audit behavior.

The safe future direction is therefore **not** a parallel AI workflow and **not** an autonomous runtime agent. AI assistance should be a bounded proposal layer around the existing shipment workflow:

`external correspondence → immutable source → extraction run → grounded proposals/findings → human review → existing domain service → canonical record + audit`

No model output may directly change shipment facts or status, create or link CRM records, create tasks/activities, issue quotes, send messages, or publish reports.

Current release decision:

- Architecture/design work using synthetic or de-identified examples: **GO**.
- Runtime AI agent implementation inside Forwarder: **OUT OF SCOPE / NO-GO**.
- Real mailbox connection, attachment processing, or model processing of operational correspondence: **NO-GO** until the P0 gates in this report are closed.

## 2. Audit method and scope control

The Lead/Coordinator used specialized Codex software-development roles for architecture/domain, backend/data, frontend/integration, test/quality, and security/audit/release review. Work was read-only except for this Lead-owned report. Two specialist streams experienced repeated transport failures before returning their summaries; the Lead independently re-checked those scopes against repository evidence. No application code, model, migration, dependency, or runtime configuration was changed.

Git preflight established:

- current branch: `forwarder-14050324-ver-13`;
- branch tracks `origin/forwarder-14050324-ver-13`;
- no local commits existed in `origin/forwarder-14050324-ver-13..HEAD`;
- the initial status reported no working-tree changes.

## 3. Repository truth

### 3.1 Current bounded contexts

| Context | Current evidence | Future AI relationship |
|---|---|---|
| Shipment operations | `ShipmentRequest` contains route, cargo, contact, assignment, SLA, priority, status, and optional CRM linkage (`backend/models.py:218`). | Canonical operational aggregate; proposals may target it but never write directly. |
| Expert operations | Expert list/detail, assignment, status, quote, message, notification, and timeline services/routes (`backend/routes/expert_console.py`; `backend/services/expert_request_detail_service.py:66`). | Primary review surface for shipment-specific findings, drafts, history summaries, and next-action proposals. |
| CRM | Customer, contact, opportunity, activity, task, report, and shipment-customer link flows (`backend/models.py:467`, `:559`, `:590`, `:620`). | Approved outcomes should reuse Activity/Task/linking services rather than create AI-specific duplicates. |
| Public/customer | Shipment request creation, tracking, customer workflow/profile (`backend/routes/shipment_request.py`; `backend/routes/public_tracking.py`). | Must not expose internal model output, confidence, private correspondence, or partner data. |
| Administration/reporting | Admin request reads, dashboards, reports, XLSX export, users, rules, and settings (`backend/routes/admin_panel.py`). | Management drafts may reuse report read models, but must remain labeled drafts with evidence and period definitions. |
| Platform/security | Flask app factory, JWT/RBAC, logging, monitoring, migrations, Docker, CI. | Must provide identity, isolation, provenance, redaction, observability, and safe release controls before AI work. |

### 3.2 What exists and should be reused

- `ShipmentRequest` is the correct operational anchor. International values currently live as nullable scalar fields on the same row (`backend/models.py:251`), which is adequate for the current maturity level but not a complete international-operations model.
- Request detail is already the closest thing to a shipment operational read model: it returns shipment facts, route, cargo, dates, timeline, messages, and latest quote (`backend/services/expert_request_detail_service.py:66`, `:150`, `:169`).
- `ExpertConsoleMessage` already associates internal/customer messages with a shipment and author (`backend/models.py:397`). It is not an email-ingestion model.
- CRM `Activity` includes email/follow-up concepts and next action; `Task` can relate to a shipment/customer/opportunity (`backend/models.py:559`, `:590`). These are the correct destinations for human-approved outcomes.
- CRM create-from-request preview is the strongest human-in-loop precedent. The UI loads suggested fields, lets the user edit them, exposes duplicates, requires confirmation, and then invokes a separate create call (`src/pages/RequestDetail.tsx:306`, `:341`, `:1034`). The API contract explicitly represents `operation: "preview"`, `preview_only: true`, and whether creation is allowed without review (`src/lib/api.ts:970`).
- CRM linkage has the strongest structured audit pattern: actor, role, source, reason, snapshots, IP, and a matching console timeline record (`backend/models.py:357`; `backend/services/crm_customer_link_service.py:188`).
- Existing frontend routes already separate expert, CRM, admin, customer detail, request detail, and public tracking (`src/App.tsx:81`).

### 3.3 What does not exist

Repository inspection found no mailbox connector, provider webhook, IMAP/MIME ingestion, external message identity, thread model, attachment quarantine, extraction run, prompt/model registry, evidence span, proposal/approval lifecycle, idempotency key, or AI implementation. Future email/AI work is a new integration boundary, not a small extension of `ExpertConsoleMessage`.

## 4. Target architecture boundaries

### 4.1 Non-negotiable principles

1. **One operational system:** Forwarder remains the system of record. Do not create a second AI shipment state machine, inbox, task list, CRM, or reporting database.
2. **Source is not truth:** Email and attachments are immutable evidence. Extracted values are proposals until reviewed.
3. **Model has no authority:** The model receives no database, outbound-email, filesystem, credential, or arbitrary-network tools.
4. **Human-controlled effects:** Every canonical write or external send is a distinct authorized action through an existing or explicitly governed application service.
5. **Grounded output:** Each proposed fact, ambiguity, risk, or next action must cite immutable evidence. Unsupported output must abstain.
6. **Versioned and reproducible:** Source hash, parser, schema, model, prompt, and policy versions must be recorded for every run.
7. **Least data:** Only the minimum authorized shipment context may be sent to a parser/model provider.

### 4.2 Proposed component model

The future design should introduce bounded components, not runtime autonomous agents:

- **Correspondence gateway:** connects an approved mailbox/provider and receives events with a least-privilege service identity.
- **Immutable source store:** records mailbox/provider identity, external message/event ID, thread ID, headers, parties, timestamps, content hash, raw-object reference, attachment metadata, retention classification, and ingestion state.
- **Quarantine/parser boundary:** validates content, limits size/expansion, scans attachments, isolates parsers, and produces normalized text without executing active content.
- **Extraction orchestration:** records input hash, parser/model/prompt/schema versions, timing, status, cost, errors, and supersession. It has no domain-write authority.
- **Proposal/finding store:** stores target aggregate/field/action, proposed value, confidence, evidence references, ambiguity/missing-information/risk category, and lifecycle (`pending`, `accepted`, `rejected`, `superseded`, `expired`).
- **Review application service:** performs authorization, evidence display, reviewer edits, stale-version checks, approval/rejection, and atomic invocation of domain services.
- **Existing domain services:** remain the only path to `ShipmentRequest`, status, message, CRM, task/activity, quote, and report effects.
- **Operational event/read model:** presents one chronological shipment history across assignments, status, messages, quotes, CRM activity, approved proposals, and partner correspondence without replacing the source tables.

### 4.3 International freight boundary

Do not prematurely build a generic logistics platform. Before expanding the data model, validate real operating procedures with the small international team and external partners. Likely future concepts are:

- partner organization/contact and responsibility;
- correspondence thread linked to a shipment or held as unlinked/ambiguous;
- shipment legs and operational milestones;
- required documents and document status;
- exception/ambiguity/missing-information records;
- next action, owner, due date, and resolution.

These should be introduced only when operational vocabulary and ownership are stable. Adding more unrelated nullable fields to `ShipmentRequest` would increase ambiguity and make extraction less reliable.

## 5. Frontend and integration decision

Future assistance belongs inside current work surfaces:

- **Expert request detail:** an “assistance” section beside canonical facts, messages, and timeline. It should show missing information, ambiguities, risk/next-action suggestions, evidence, confidence, and explicit accept/edit/reject controls.
- **Message area:** drafts can be prepared from a shipment, but must be visually labeled as drafts and require an explicit send confirmation. Navigation, refresh, retry, or double-click must never send.
- **Admin reports:** draft narrative summaries may sit beside existing deterministic report data; facts and metrics must continue to come from server-side report read models.
- **CRM:** approved customer/follow-up proposals should call the current preview/create/link/activity/task contracts, not introduce AI-only CRM records.

The frontend currently stores the expert token in `localStorage` (`src/lib/api.ts:169`) and request detail contains its own large interface plus operational/CRM UI (`src/pages/RequestDetail.tsx:57`, `:667`). Before adding sensitive correspondence:

- resolve the authentication/session P0 issues in section 8;
- define generated API schemas instead of duplicating large handwritten types;
- add proposal-specific states (`loading`, `ready`, `stale`, `conflict`, `accepted`, `rejected`, `superseded`, `failed`);
- clearly distinguish source evidence, canonical values, proposed values, and reviewer-edited values;
- escape/sanitize all untrusted email/model output and never render raw HTML;
- keep role and shipment visibility enforcement server-side;
- preserve Persian/English directionality, dates, units, and evidence spans;
- add pagination/bounded retrieval for long histories.

## 6. Backend and data readiness gaps

### P0

- No immutable provenance/source model.
- No provider-event or message-level idempotency enforced by database uniqueness.
- No extraction-run or field-level proposal/approval lifecycle.
- No aggregate version/optimistic concurrency protection; a reviewed proposal could overwrite a newer shipment state.
- Services frequently own and commit transactions internally, making multi-step approval/audit orchestration difficult to guarantee atomically.
- Migration governance is unsafe: startup code contains handwritten/recovery DDL and Alembic-version recovery behavior (`backend/startup.py:15`, `:64`). New audit/provenance tables must be deployed only through explicit migrations.

### P1

- History is fragmented across `ShipmentRequestLog`, `ExpertConsoleLog`, `ExpertConsoleMessage`, CRM `Activity`, and specialized CRM audit (`backend/models.py:312`, `:332`, `:357`, `:397`). Define a canonical operational-event contract/read model.
- `ExpertConsoleMessage` lacks external ID, thread, sender/recipients, direction, attachments, delivery/approval state, and source provenance.
- Message types are typed in the frontend but are not allow-listed by backend normalization (`backend/services/message_service.py:84`).
- International operations lack explicit partners, legs, milestones, responsibilities, documents, and exceptions.
- Silent read failures, such as treating any latest-quote exception as no quote, reduce observability (`backend/services/expert_request_detail_service.py:177`).

### P2

- Move transaction ownership to application/use-case boundaries.
- Add a bounded chronological history query service.
- Formalize enums and allowed state transitions in API and database constraints.
- Add retention, deletion/legal-hold, and archival policies for correspondence, attachments, extraction artifacts, drafts, and audits.

## 7. Test and quality strategy

The backend has a useful contract-test base. The best template is the CRM customer preview suite, which proves preview-only metadata, zero mutation, no invented missing fields, duplicate blocking, reviewed acceptance, and structured audit (`backend/tests/test_crm_customer_create_from_request_preview.py:184`). CRM unlink also tests idempotent no-op behavior (`backend/tests/test_crm_customer_link_contract.py:380`).

Current quality gaps:

- CI runs backend pytest, frontend lint/build, and structure/whitespace checks, but not frontend tests, typecheck as a separate gate, PostgreSQL integration, migration validation, browser E2E, security scans, or coverage thresholds (`.github/workflows/quality-gates.yml:10`).
- Backend fixtures force in-memory SQLite (`backend/tests/conftest.py:1`), so production PostgreSQL uniqueness, locking, concurrency, and migration behavior are unproven.
- Frontend test files exist, but `package.json` has no test script or declared Vitest/Testing Library dependencies (`package.json:6`).

Required P0 test contracts before implementation:

- duplicate and concurrent provider deliveries create one source;
- partial failure/retry never duplicates messages, activities, tasks, or audit;
- malformed/oversized/adversarial email and attachments fail safely;
- extraction performs zero canonical writes;
- absent or contradictory data yields unknown/ambiguity, not invented defaults;
- every proposal has evidence and version provenance;
- rejection is zero-write; acceptance applies exactly the reviewed value once;
- stale aggregate versions require re-review;
- authorization and cross-shipment isolation are enforced server-side;
- domain write, audit, notification, and resulting event commit or roll back together;
- logs never contain bodies, credentials, tokens, or sensitive attachments.

Create a versioned, access-controlled, de-identified freight-email evaluation corpus covering Persian, English, mixed language, forwarded threads, tables, signatures, OCR text, conflicting updates, multiple shipments, and adversarial instructions. Measure field-level precision/recall, shipment-link accuracy, evidence grounding, missing/ambiguity recall, calibration, abstention, and unsafe-action rate. Summary fluency must never substitute for factual accuracy.

## 8. Security, audit, and release blockers

### P0 security defects

1. `require_auth` records token type but does not require an access token, so a refresh token can authenticate ordinary protected endpoints (`backend/security.py:126`).
2. Logout returns success without token revocation (`backend/routes/expert_console.py:383`), and refresh rotation does not revoke the previous refresh token (`backend/auth.py:100`).
3. Login throttling is process-local/IP-only and resets or diverges across workers (`backend/auth.py:15`; `backend/Dockerfile:17`).
4. Customer verification logs the full URL containing the verification token (`backend/services/customer_gamification_service.py:22`).
5. Upload validation trusts extension, allows SVG, reads it wholly, and serves it inline (`backend/services/upload_service.py:9`; `backend/routes/site_settings.py:54`). This helper must not be reused for email attachments.
6. CSP permits `unsafe-inline` and `unsafe-eval` scripts (`backend/security.py:67`).
7. Error logging can include full URL/query, exception, traceback, user agent, and caller context without a centralized redaction policy (`backend/app_logging.py:185`).

### Release blockers

- Remove runtime schema mutation/Alembic rewriting and run migration as a single explicit deployment step (`backend/startup.py:15`).
- Remove or tightly isolate host-published production Adminer (`docker-compose.production.yml:57`).
- Replace the PostgreSQL superuser application connection with separate least-privilege application/migration roles (`docker-compose.production.yml:39`).
- Establish encrypted off-host backups and verified restore evidence; a mounted backup directory is not a backup policy.
- Add secret/dependency/SAST/container scanning, SBOM/provenance, PostgreSQL migration tests, deployment approval, and environment protection.
- Centralize redacted audit/security logs with retention, alerting, and access review.

### AI/email threat boundary

Treat email body, headers, links, attachments, forwarded text, extracted text, and model output as hostile input. Defend against prompt injection, arbitrary URL fetch/exfiltration, cross-shipment leakage, malicious/expanding attachments, unsafe HTML, replay/duplicates, denial-of-service/cost abuse, and poisoned operational knowledge. Define data classification, lawful basis, partner notice/consent, processing location, vendor retention, deletion, and legal hold before real correspondence leaves Forwarder infrastructure.

## 9. Phased roadmap

### Phase A — prerequisite hardening (P0)

- Fix access/refresh separation, refresh revocation/rotation, logout, and shared rate limiting.
- Remove verification-token logging; implement centralized PII/secret redaction.
- Remove active SVG exposure and design isolated attachment quarantine.
- Remove runtime DDL/recovery mutation; prove clean PostgreSQL migrations.
- Approve data-flow, threat model, classification, retention, provider, and human-approval policies.
- Define canonical operational-event and aggregate-version contracts.
- Define immutable source, extraction, proposal, decision, and audit schemas on paper; do not migrate yet.
- Establish deterministic acceptance tests and evaluation corpus before selecting a model.

### Phase B — synthetic shadow prototype

- Use a dedicated isolated mailbox or offline fixtures with synthetic/de-identified messages.
- Ingest idempotently into immutable source records.
- Parse in quarantine and generate proposals only; zero domain writes and zero outbound sends.
- Display results in the existing expert request-detail surface with evidence and explicit review states.
- Run PostgreSQL concurrency/idempotency/security tests and corpus evaluation.

### Phase C — controlled internal pilot

- Enable one narrowly scoped capability, such as missing-information detection or a follow-up draft.
- Restrict by mailbox/team/role and retain a per-capability kill switch.
- Require human approval; use existing domain services for every accepted effect.
- Monitor ingestion lag, duplicates, parse failures, unsupported claims, abstention, reviewer edits/rejections, stale conflicts, cost, and unauthorized attempts.

### Phase D — production consideration

- Require proven backups/restores, incident runbooks, centralized audit, provider/privacy approval, security abuse testing, signed/SBOM artifacts, canary rollout, and explicit product-owner/security go/no-go.
- Add capabilities incrementally. Do not combine extraction, decision, write, and send authority.

## 10. Architecture decision record

**Decision:** Adopt a human-controlled, evidence-grounded proposal architecture integrated into existing Forwarder shipment/CRM workflows.

**Rejected:** runtime autonomous AI agents; direct model writes; direct model email send; an AI-only inbox/task/workflow; storing generated summaries as canonical facts; reusing the current logo upload path for attachments; treating current free-text logs as sufficient provenance.

**Reason:** Forwarder is still standardizing international operations. A proposal layer can improve information quality without freezing immature processes or creating a parallel system. It also allows provenance, approval, rollback, and evaluation to be built before operational authority is introduced.

**Revisit condition:** P0 hardening is complete, international operating vocabulary is validated, synthetic shadow evaluation meets agreed thresholds, and security/product owners approve a narrowly bounded pilot.

## 11. Final readiness scorecard

| Area | Readiness | Decision |
|---|---|---|
| Domain anchor and workflow reuse | Partial/strong | Reuse `ShipmentRequest`, request detail, CRM Activity/Task, and existing services. |
| International operational model | Early | Validate partners, milestones, documents, responsibilities, and exceptions before schema design. |
| Email ingestion/provenance | Absent | Design required before implementation. |
| Human approval/audit | Partial | Reuse CRM preview/link pattern; introduce proposal/version/evidence contracts. |
| Frontend integration | Partial | Extend request detail; do not create a parallel workspace. |
| Automated quality | Partial | Backend contracts are useful; PostgreSQL, frontend, migration, E2E, and evaluation gates are missing. |
| Security/release | No-go | Authentication, sensitive logging, upload, migration, database-access, and release controls block real data. |
| Overall | **NO-GO for real AI/email processing** | Architecture work and synthetic/de-identified design prototypes only. |
