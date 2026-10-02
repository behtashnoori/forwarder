# Document management Phase 1 — 2026-10-02

## Entry and authority

The Product Owner's supplied Phase 1 mission and corrected-baseline confirmation
authorize only an organization Document Type catalog and classified Shipment
file uploads. Entry PASS: fetched clean `integration/golden-controlled` at
`9264c106fcf7eef5e5e5a4fd473d24dd88381c44`, ahead/behind 0/0; single Alembic head
`20261016_active_route_basis`; tracked AGENTS.md and canonical acceptance activate
LPAF v2.7. The preceding walkthrough correction chat is completed, its final
evidence is integrated, and no other active Forwarder implementation was found.
The stale original checkout and its untracked material are untouched.

Rigor B; capability tier Sol: coupled catalog/file/tenant/history contracts and
PostgreSQL/browser verification. Work is decomposed into audit, bounded model
extension, Admin/Expert UI, focused qualification, and controlled integration.

## Product Authority Record

- AUTHORIZED_PRODUCT_CHANGES: Organization Admin creates and deactivates its own
  document types; owning Expert selects an active permitted type, uploads a file
  and optional note on an open Shipment, and reads its persisted classification,
  filename, actor, time and note. Historical files survive type deactivation.
- DELEGATED_TECHNICAL_CHOICES: extend the existing definitions/files, additive
  nullable ownership and classification keys, existing authority/audit/storage,
  compact catalog and document presentation, disposable test infrastructure.
- PROTECTED_OUT_OF_SCOPE_BEHAVIOR: platform catalog governance; generic types;
  policy/readiness distinctions; required/optional semantics; tenant and owning
  Expert authorization; closed default read-only and separate historical repair;
  existing contexts and customer visibility; all preserved walkthrough business
  data. No new workflow, lineage, reconciliation, extraction, case, or route-leg
  document model, no customer-specific seeds, production, deployment or release.
- DECISIONS_NEEDED: none from the audit; newly discovered authority conflicts
  stop affected work rather than changing Product meaning.
- APPROVING_OWNER_OR_AUTHORITY: requesting Product Owner.
- APPROVAL_REFERENCE: attached Phase 1 request and explicit corrected SHA reply
  in this chat; approval does not grant Human Walkthrough PASS.

## Architecture audit before implementation

FACT: `DocumentDefinition` in `backend/models.py` is the existing platform-owned
vocabulary, with stable code/public identity, bilingual names, description,
active state and catalog governance. It has no tenant-owner key. Existing global
create/lifecycle routes require Platform Admin. `OrganizationDocumentRequirement`
and `ProjectDocumentRequirement` express policy separately; their precedence is
implemented by `organization_document_policy_service.effective_definitions`.

FACT: `CaseDocumentFile`, `shipment_document_service`, `PrivateDocumentStorage`,
and `case_documents` routes already store, authorize, download, and audit files.
Shipment files currently store a free-text `custom_title`; they lack a direct
DocumentDefinition reference. `OperationalDocumentRequirement` and
`ArtifactAssociation` implement evidence readiness separately. Using a requirement
as file classification would incorrectly merge those meanings.

FACT: `ShipmentDocuments` already displays files, actor, recorded time and note.
`OperationalShipmentDetail` provides default closed read-only presentation and
an explicit historical-repair entry point. `authorize_document_management`
requires the persisted owning Expert; Admin read is not mutation authority.
Existing replacement/context machinery is preserved, not expanded by this phase.

MINIMUM GAP: tenant ownership on the existing definition; direct nullable
definition reference on the existing file; scoped Admin configuration and Expert
selection using those identities. Creating a type must not publish requirement
policy, change fallback mode, or itself satisfy document readiness.

### Bounded architecture decision

Accepted within the owner's Phase 1 authorization: nullable `organization_id`
extends DocumentDefinition ownership; null continues to mean platform reference.
Nullable `document_definition_id` extends CaseDocumentFile classification. Existing
catalog lifecycle gates remain platform-only; an organization type's active flag
is tenant configuration, not a source-verification claim. Existing free-title
uploads remain compatible; selecting a catalog type writes a stable reference.
No classification automatically creates a policy or evidence association.
All exposed selectors (including project configuration) apply the same tenant
scope. Generated immutable codes preserve the existing global uniqueness rule.
This extends the same SORs and avoids a second type/file subsystem. The additive
migration refuses downgrade once either new field contains business evidence.
Framework impact NONE; this record and OpenAPI document the project extension.

Closed normal uploads now require the explicit historical-repair intent already
represented by the separate UI entry. That intent is authorized by the existing
owning-Expert rule and recorded in OperationalAudit; it neither reopens Shipment
nor revises ClosureDecision. The mission specifically authorizes refusal of
normal uploads on closed Shipments.

MIGRATION_REQUIRED=YES: two additive nullable foreign keys are necessary because
neither organization ownership nor durable file classification can be expressed
by the existing schema without conflating policy or free text. Existing rows
retain null keys and their existing meanings; no historical rewrite or new
document entity is authorized. Codes can be generated stable identities, avoiding
changes to canonical global code uniqueness. No speculative fields are needed.

## Verification and reference impact

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J04/J06/J08/J09 and the document/admin
portions of FWD-IPJ-03/04. Reference: Product Acceptance Journeys v1.1 and the
Operational Shipment Product Contract v1. Framework reference impact NONE;
project reference UPDATE_REQUIRED, recorded by this bounded authority/audit and
the final evidence receipt. No existing journey is removed or redefined.

Required evidence: the eight mission cases on disposable PostgreSQL 18; focused
catalog/policy/file/readiness/closure/history and role/tenant regressions; frontend
tests, TypeScript/build/lint; normal-navigation Admin → Expert upload → reopen →
Admin deactivate → historical download browser journey, existing affected
document/closure integrated journeys. Bind final proof to a clean Product SHA.

Preserved runtime work is limited to source update, additive schema application
if needed, scoped process refresh and read-only identity/preservation evidence.
No preserved-runtime type creation, upload, or other business action. Human
walkthrough remains IN_PROGRESS; Release Ready and Release Complete remain NO.

Implementation/qualification results are pending and must not be inferred from
this mission record.
