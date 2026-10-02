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

## Qualified implementation

Product SHA: `a705c9cb77f0a337a63f4d59a3dcdc5032546244`.
Final qualification commit: `7756349eef0fb75f778619380587a91f78f4b11f`.
The intervening changes affect four test files only; all runtime, migration,
dependency and frontend source blobs remain identical to the Product SHA.
Hash-bound logs, screenshots, exact clean candidate identities and accepted
subsets of each run are in `DOCUMENT-MANAGEMENT-PHASE1-EVIDENCE-20261002.json`.

The implementation adds organization create/edit/deactivate routes through the
existing catalog audit, a compact Admin catalog above the existing policy editor,
and an active type selector in the existing Shipment file uploader. It extends
DocumentDefinition and CaseDocumentFile in place, scopes every exposed definition
selector, and retains the existing private storage, download and audit paths.
Persian type, filename, actor, recorded time, optional note and inactive-type
status appear in the existing file list. Existing context, audience, replacement
and free-title compatibility are preserved; none is a new Phase 1 subsystem.

| Mission case | Evidence and result |
| --- | --- |
| 1 Admin creates type | PASS: persisted own-organization definition, stable identity, safe retry, no automatic requirement; browser normal Admin navigation |
| 2 Expert uploads | PASS: active permitted definition, exact file bytes, optional note and actor/time metadata; owning Expert only |
| 3 Persistence | PASS: reopen, reload, saved download equals uploaded bytes; stable type reference |
| 4 Deactivation | PASS: type absent from new-upload selector; existing file and classification readable/downloadable |
| 5 Required/optional | PASS: policy precedence and readiness/closure regressions; missing optional evidence is nonblocking and required evidence remains governed |
| 6 Closed Shipment | PASS: normal upload refused, explicit authorized historical repair audited; closure decision and closed state unchanged |
| 7 Tenant isolation | PASS: foreign catalog, policy, project selector, type injection and file access denied; browser foreign Admin cannot see own type |
| 8 Roles | PASS: owning Expert uploads; Organization Admin configures own types; Expert/customer configuration and ordinary Admin upload denied; platform-only global mutation retained |

Validation:

- Focused backend: 113 passed; final upload/auth/context recheck: 10 passed.
- PostgreSQL 18: fresh base-to-head migration PASS; three Phase 1/document-context/
  closure tests PASS, including comparison of every original table column across
  the new migration and refusal to downgrade once new ownership evidence exists.
  Public Tracking PostgreSQL regression: 1 passed.
- Frontend: 104 files / 499 tests passed. TypeScript and build PASS. Lint has
  zero errors and 16 pre-existing warnings; build retains its existing chunk-size
  advisory. Architecture governance and whitespace checks PASS.
- Chrome: 10 selected tests PASS: new Phase 1 (1), existing document/privacy (2),
  workspace and integrated access/navigation (5), owner transfer (1), continued
  history/ETA/privacy/closure/post-close denial (1). Desktop and 390px mobile
  screenshots inspected; no horizontal overflow in the new document journey.

Qualification corrections were confined to the evidence harness: migration census
SELECTs use the existing read-only certification option; the new download check
verifies the saved file rather than the CORS preflight; the existing workspace
source assertion is scoped to its overdue item; the existing closure journey uses
canonical button wording and the visible shared calendar. The stale closure run
was stopped after diagnosing its obsolete selector and rerun successfully.
Six existing readiness test failures were reproduced on the unchanged entry
baseline: successful verification calls incorrectly used an ordinary Expert.
Those fixtures now use their verifier principal while retaining Expert-denial
coverage. No product permission or acceptance criterion was weakened.
Earlier partial/failed runs are retained as diagnostics; only explicitly named
passing subsets and their successful reruns are accepted as evidence.

PDA-07 reconciliation: own type configuration, classified upload and explicit
closed repair intent are AUTHORIZED; platform governance, tenant/role boundaries,
policy/readiness, history and all advanced features are PRESERVED. No unresolved
VIOLATION or UNKNOWN was found. Engineering and automated journey qualification
are PASS; Human Product Walkthrough remains IN_PROGRESS, global Product validation
EVIDENCE_PENDING, Release Ready NO. No production, deployment or release action.

## Human walkthrough handoff

Use the same local runtime at `http://walkthrough.localhost:5173`. The Product
Owner, not automation, will perform the supplied eight steps: Organization Admin
opens «الزامات مستندات» and creates a new type in «انواع اسناد سازمان»; the owning
Expert opens the preserved second OPEN Shipment, selects that type and uploads
one file with an optional note; refresh verifies persistence; Admin deactivates
the type; Expert verifies the historical file is readable and the type is absent
from new upload choices. No example type has been seeded into the preserved DB.

Controlled integration and the preserved-runtime receipt are recorded below after
the source/schema refresh. The refresh must compare every original row/column,
sequence and the four named protected facts, with zero business actions.
