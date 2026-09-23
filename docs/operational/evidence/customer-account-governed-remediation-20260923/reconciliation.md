# Governed Customer Account Completion — mission and reconciliation record

Date: 2026-09-23
Baseline: LPAF v2.6 — ACTIVE / FROZEN / CANONICAL
Rigor / routing: Level B (Product), Sol; bounded implementation and tests may be decomposed
Owner / authority: Product Owner approval in the mission supplied on 2026-09-23
Approval reference: `Forwarder — Governed Customer Account Completion and Golden Reconciliation`

## Mission contract

Outcome: complete the optional Customer Account on current Golden without making
an account a prerequisite for Request creation, without broadening Public
Tracking, and without changing operational Shipment, Expert, CRM, pricing,
notification, document, or Control Tower behavior.

Canonical implementation base:

- repository: `D:\1-webapp\15-forwarder-golden-20260921`
- branch / entry HEAD: `integration/golden-controlled` /
  `0837172e04ef8cafa0098f0935999fe73569bb85`
- remote alignment after fetch: one local governance commit ahead of
  `github/integration/golden-controlled`, zero behind
- entry worktree: clean
- isolated candidate: `D:\1-webapp\forwarder-dev\customer-account-governed-remediation`
- implementation branch: `codex/customer-account-governed-remediation`
- Golden entry Alembic head: `20260926_fixed_shipment_responsible_expert`
- candidate Alembic head: `20260927_customer_portal_account_lifecycle`
- Golden has no repository-local `AGENTS.md`; the invoking repository's
  LPAF v2.6 governance instruction and the canonical v2.6 documents govern.

Donor only:

- repository: `D:\1-webapp\15-forwarder`
- branch / HEAD: `codex/ct-prod-regression-rc-20260921` /
  `d6297fdf50b27f7d69a5bf2086d11ef2eed882ed`
- state: dirty with material tracked and untracked evidence; never cleaned,
  reset, merged, or used as the implementation base

## Fact / assumption / unknown / decision needed

FACT:

- Golden already implements ADR-052's opaque 128-bit Request tracking
  capability and its fixed minimal public allowlist.
- Golden already has opaque `ShipmentRequest.public_id`, opaque
  `ExpertQuote.public_id`, immutable Quote revision rows, discussion response
  text, and separate `ShipmentRequest.customer_id` (CRM) and
  `ShipmentRequest.gamification_customer_id` relationships.
- `CustomerGamification` is distinct from CRM `Customer`; it is the existing
  portal/gamification identity source, but currently has no password or account
  lifecycle.
- Anonymous Request creation is currently supported.

ASSUMPTION (delegated technical choice, verified in synthetic qualification):

- A server-checked account session generation can revoke all Customer sessions
  after password change, reset, disable, or enrollment without introducing a
  second staff JWT model.
- A newly registered portal account may be scoped only from the server-resolved
  organization hostname. Client input never selects its organization. An
  unscoped legacy identity is invisible to Organization Admin support.

UNKNOWN:

- No governed source currently proves that a CRM `Customer` row and a legacy
  `CustomerGamification` row represent the same subject.
- There are currently no real Customer records to reconcile; migration and
  enrollment qualification use synthetic data only (Product Owner clarification
  on 2026-09-23).

DECISION_NEEDED:

- If legacy enrollment must originate from CRM `Customer`, select the governed
  evidence and authority that proves a CRM-to-portal link. This mission will
  not infer it from name, email, or mobile.

Subsequent Product Owner clarification:

- routine portal-account support belongs to the Organization Admin of the same
  organization; Platform Admin is reserved for broad platform matters and does
  not substitute for that tenant-scoped responsibility;
- therefore portal accounts carry an explicit server-owned organization scope,
  and Organization Admin queries/actions must derive the organization from the
  authenticated membership;
- legacy rows without proven organization scope are not exposed to any
  Organization Admin and are never auto-scoped by contact similarity.
- password-recovery delivery uses the account email (Product Owner response on
  2026-09-23). The bounded implementation uses an explicitly configured,
  Production-only SMTP adapter; local/test/UAT delivery is suppressed and the
  general Notification architecture remains unchanged.

## Product Authority Record

`AUTHORIZED_PRODUCT_CHANGES`:

- optional Customer Account; anonymous Request creation remains available
- self-registration without mandatory initial email verification
- authenticated, server-scoped Request list/detail
- private current Quote/history and version-safe response
- change password and email-delivered reset
- ACTIVE/DISABLED portal account lifecycle
- narrow same-organization Admin account support, email recovery, and
  controlled enrollment link
- view-only minimum portal identity/contact profile
- preserve ADR-052 limited Public Tracking

`DELEGATED_TECHNICAL_CHOICES`:

- service/module structure, password hashing, digest-only token persistence,
  token expiry/single-use implementation, session generation/revocation,
  transaction boundaries, refactoring, tests, and synthetic UAT fixtures

`PROTECTED_OUT_OF_SCOPE_BEHAVIOR`:

- Operational Shipment process and execution workflow; Expert ownership and
  assignment; Control Tower; Documents; pricing ownership and amount/currency
  authority; Notifications; anonymous Request submission; unrelated Request
  lifecycle; unrelated Admin/Manager responsibility; CRM Customer semantics;
  `ShipmentRequest.customer_id`; ADR-052 Public Tracking purpose/projection

`APPROVING_OWNER_OR_AUTHORITY`: Product Owner
`APPROVAL_REFERENCE`: mission text supplied in the 2026-09-23 task
`DECISIONS_NEEDED`: proof source for any future CRM-to-portal legacy link

## Ownership, SOR, data scope, and chain

- Portal identity/account SOR: `CustomerGamification` plus governed credential,
  lifecycle, session-generation, server-owned organization scope, and
  recovery/enrollment metadata.
- CRM organization/customer SOR: `Customer`; it is not modified or linked by
  inference in this mission.
- Private Request ownership SOR: server-written
  `ShipmentRequest.gamification_customer_id`.
- CRM link SOR: `ShipmentRequest.customer_id` (preserved).
- Quote SOR: immutable `ExpertQuote` rows; amount/currency remain Expert-owned;
  Customer response targets the current exact Quote and expected response
  version.
- Public Tracking authority/projection: ADR-052; independent of portal session.

Domain chain:

`portal account -> authenticated session + current ACTIVE/version check ->
server-owned gamification_customer_id -> opaque Request public_id -> immutable
Quote public_id/version -> Customer response + audit`.

Recovery/enrollment chain:

`public enumeration-safe request or exact Admin selection -> digest-only,
purpose-bound, expiring token -> Production-only email delivery for reset or
authorized manual delivery for initial enrollment -> single consume -> password
hash replacement -> session-generation increment -> replay rejection + audit
metadata`. Failed or suppressed reset delivery revokes the issued token.

## Candidate reconciliation inventory (completed before product code changes)

Classification means whether the dirty donor file is used in the current
Golden-based implementation. `MODIFY` and `REIMPLEMENT` never mean file-copy.

| Donor file | Disposition | Golden reconciliation |
| --- | --- | --- |
| `backend/__init__.py` | MODIFY | Reapply only secure Customer cookie lifetime/flags compatible with current factory. |
| `backend/models.py` | MODIFY | Reimplement credential/account/session/token fields on current models; retain Golden Quote discussion model and add only missing concurrency field. |
| `backend/migrations/versions/20260923_customer_quote_portal.py` | REJECT | Wrong ancestor and duplicates Golden Quote migration; replace with one minimal migration after current `20260926` head. |
| `backend/routes/customer_gamification.py` | REIMPLEMENT | Keep current Golden Quote communication semantics while replacing client-supplied Customer authority with session authority and adding lifecycle endpoints. |
| `backend/routes/shipment_request.py` | REIMPLEMENT | Preserve anonymous POST; when a valid Customer session exists derive ownership server-side and require Customer CSRF. |
| `backend/services/customer_portal_auth.py` | MODIFY | Useful boundary; add ACTIVE/DISABLED checks, session generation, password change/reset, safe existence response, enrollment, and audit-safe errors. |
| `backend/services/customer_portal_service.py` | MODIFY | Reuse owned pagination/detail concept; reconcile with Golden Quote discussion/history/current and exact response-version contract. |
| `backend/services/quote_service.py` | MODIFY | Golden already emits opaque Quote identity; add response version only, never Customer amount/currency authority. |
| `backend/services/shipment_service.py` | REIMPLEMENT | Remove trusted client `gamification_customer_id`; accept only route-derived ownership while preserving all current cargo/assignment behavior. |
| `backend/services/tracking_service.py` | REJECT | Donor was based on a broader public projection. Preserve current Golden ADR-052 implementation byte-for-behavior except regression assertions. |
| `backend/tests/test_customer_quote_portal_migration.py` | REIMPLEMENT | Rewrite for current head, populated compatibility, token/account state, and guarded downgrade. |
| `backend/tests/test_customer_gamification_contract.py` | MODIFY | Preserve legacy contracts where still authorized; add session/profile isolation. |
| `backend/tests/test_customer_quote_response.py` | MODIFY | Replace public tracking-code write authority with authenticated exact Quote/version/CSRF tests while retaining Golden discussion semantics. |
| `backend/tests/test_public_tracking_timeline.py` | REJECT | Donor only proves Quote omission while normalizing its broad unsafe projection; keep and strengthen Golden ADR-052 tests instead. |
| `backend/tests/test_alembic_version_table.py` | NOT_APPLICABLE | No version-table behavior change. |
| `backend/tests/test_case_documents_migration.py` | NOT_APPLICABLE | No document migration behavior change. |
| `backend/tests/test_execution_units.py` | NOT_APPLICABLE | No execution-unit behavior change. |
| `backend/tests/test_expert_assignment_referral_contract.py` | MODIFY | Only ownership-input and anonymous-preservation regressions where signatures require it. |
| `backend/tests/test_expert_sla_migration.py` | NOT_APPLICABLE | No SLA migration behavior change. |
| `backend/tests/test_global_logistics_point_adoption_migration.py` | NOT_APPLICABLE | No logistics-point migration behavior change. |
| `backend/tests/test_global_logistics_point_materialization_migration.py` | NOT_APPLICABLE | No materialization behavior change. |
| `backend/tests/test_logistics_network.py` | NOT_APPLICABLE | No logistics-network behavior change. |
| `backend/tests/test_master_data_migration.py` | NOT_APPLICABLE | No master-data migration behavior change. |
| `backend/tests/test_operational_execution_190.py` | NOT_APPLICABLE | Operational execution is protected. |
| `backend/tests/test_project_aggregate_foundation.py` | NOT_APPLICABLE | Project aggregate is protected. |
| `backend/tests/test_project_configuration.py` | NOT_APPLICABLE | Project configuration is protected. |
| `backend/tests/test_reference_data_seed_migration.py` | NOT_APPLICABLE | No reference seed change. |
| `backend/tests/test_release_publication_contract.py` | NOT_APPLICABLE | This mission does not publish or alter a release package. |
| `backend/tests/test_shipment_request_update_trigger_migration.py` | NOT_APPLICABLE | No update-trigger change. |
| `docs/EXPERT_QUOTE_FLOW.md` | MODIFY | Reconcile private session-based Customer response with current Golden discussion semantics. |
| `docs/architecture/ADR-INDEX.md` | MODIFY | Do not reuse donor ADR-048; add the next available authoritative decision and preserve occupied-number note. |
| `docs/operational/adr/ADR-048-authenticated-customer-request-quote-workspace.md` | REJECT | Donor ADR is Proposed, conflicts with occupied lineage, and predates ADR-052/current Golden. |
| `docs/operational/evidence/customer-quote-visibility-20260923/report.md` | KEEP | Preserve as donor provenance/root-cause evidence only; it is tied to a dirty uncommitted tree and is not current candidate certification. |
| `scripts/build_release_package.py` | NOT_APPLICABLE | No release package is built. |
| `scripts/tests/test_release_package_builder.py` | NOT_APPLICABLE | No release package contract changes. |
| `scripts/uat/customer_quote_visibility_seed.py` | REIMPLEMENT | Replace with bounded synthetic journey fixture only if browser qualification needs it; no secrets in evidence. |
| `src/App.tsx` | REIMPLEMENT | Add Customer and narrow Admin routes on current Golden router. |
| `src/components/Header.tsx` | MODIFY | Add discoverable Customer entry without altering staff navigation authority. |
| `src/components/LocationForm.tsx` | MODIFY | Preserve anonymous success; authenticated success may navigate to private opaque detail. |
| `src/i18n.tsx` | MODIFY | Add only account strings required by new surfaces. |
| `src/lib/api.ts` | REIMPLEMENT | Add credentialed Customer APIs, CSRF, lifecycle, private Request/Quote, and Admin account-support contracts. |
| `src/pages/CustomerPortalAccess.tsx` | MODIFY | Reuse login/signup concept; add forgot/reset entry and state-safe errors. |
| `src/pages/CustomerPortalRequestDetail.tsx` | MODIFY | Reconcile with Golden `discussion` message and response-version semantics. |
| `src/pages/CustomerPortalRequests.tsx` | MODIFY | Reuse paginated complete discovery and add minimal profile/change-password access. |
| `src/pages/VerifyEmail.tsx` | REJECT | Donor auto-authenticates/redirects a legacy verification identity; keep Golden verification behavior until governed enrollment proves credentials and organization scope. |
| `src/tests/pages/CustomerPortal.test.tsx` | REIMPLEMENT | Expand for signup/login/list/detail/history/response/password/forgot/state and public regression. |

## Verification plan and gates

- Backend: account/session lifecycle, enumeration resistance, token
  expiry/single-use/replay, session revocation, disabled denial, exact ownership,
  anonymous denial, Quote current/history/version, Admin recovery/enrollment,
  anonymous Request preservation, and ADR-052 projection.
- Frontend: normal navigation for signup/login/list/detail/history/response,
  change password, forgot core boundary, disabled message, and Admin support.
- Migration: repository one-head check, clean upgrade, populated compatibility,
  downgrade guard/recovery behavior; no Production execution.
- Browser: synthetic local journeys only. Real email delivery is never exercised
  in local/test/UAT and requires separate Production configuration validation.

Release boundary: implementation candidate only. No Production access,
migration, deploy, merge, package publication, or Operational Shipment work.

## Verification evidence and residual gates

Evidence captured on 2026-09-23 against the isolated candidate:

- complete backend suite after email-recovery implementation: `1355 passed,
  106 skipped`; the three initially
  stale assertions were reconciled without removing coverage, then their
  focused contract set passed `11/11`;
- final Customer Portal account set after hostname fail-closed hardening:
  `12/12` passed;
- final Customer/Quote/migration/Public Tracking focused set: `66/66` passed;
- recovery email, Customer Portal lifecycle, and lifecycle-migration focused
  set: `21/21` passed, including fake-SMTP success, Production configuration
  fail-closed, non-Production suppression, and token revocation on non-delivery;
- complete frontend suite: `364/364` passed; final focused portal/API/router
  suite: `11/11` passed;
- TypeScript check, production frontend build, backend compileall, Alembic
  one-head check, tenant-ownership inventory contract, and diff whitespace
  check passed;
- lint completed with zero errors and 13 pre-existing warnings outside this
  slice;
- synthetic predecessor-to-head migration, populated compatibility, guarded
  downgrade, and repository-head contracts passed `11/11`.

Qualification limits:

- the canonical Playwright runner requires an explicitly named disposable
  PostgreSQL database through `E2E_DATABASE_URL`; none was supplied, so no
  integrated browser journey was claimed;
- a clean-from-base SQLite probe was attempted and stopped in the historical
  `20240920_add_transport_method_to_shipment_request` migration before reaching
  this slice. The temporary synthetic database was removed. PostgreSQL
  clean-upgrade/browser qualification remains required before release;
- the email recovery adapter, account-existence-safe public response,
  same-organization Admin trigger, delivery evidence, and failure/suppression
  revocation are qualified with a fake SMTP boundary. No real email was sent;
  Production SMTP credentials and a live delivery check remain operational
  release gates;
- no real Customers exist. Synthetic scoped portal identities prove the exact
  enrollment mechanism, but a future CRM-to-portal proof source remains a
  separate Product decision.

This evidence is sufficient for a reviewable implementation candidate, not
for release. `PRODUCT_VALIDATION_EVIDENCE_FOR_THIS_SLICE` remains `INCOMPLETE`
until the disposable PostgreSQL migration/browser gate and Production email
delivery qualification are completed.
