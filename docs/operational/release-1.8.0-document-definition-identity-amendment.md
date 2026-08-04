# Release 1.8.0 — DocumentDefinition Identity Amendment

- **Status:** Accepted
- **Date:** 2026-08-03
- **Authority:** Product, Architecture, and Data role authorities; Security authority; Operations consulted
- **Release status:** Implemented / Not Published / Not Deployed
- **Production:** Unchanged at 1.6.1

## Blocker

The existing `DocumentDefinition` has an internal numeric primary key but no opaque API identity. Release 1.8.0 requires Project Configuration APIs to reuse `DocumentDefinition` without exposing numeric IDs. The original migration boundary did not authorize altering that existing table, so implementation correctly stopped fail-closed.

## Considered options and accepted decision

The considered options were to expose the numeric key, duplicate the document taxonomy, relax the new API identity rule, or add an opaque identity to the existing definition. Numeric exposure, taxonomy duplication, and relaxation were rejected.

The accepted option adds `public_id`: a stable, immutable, unique, non-null UUIDv4. The numeric `id` remains the database primary key and internal foreign-key target. New Release 1.8.0 APIs must never expose it.

## Migration authority and population strategy

Migration `20260811_project_configuration`, with parent `20260810_logistics_network`, is additionally authorized to:

1. add nullable `document_definition.public_id`;
2. assign one newly generated UUIDv4 to every existing row, without derivation from its numeric ID;
3. verify uniqueness, add the unique constraint/index, and make the column non-null; and
4. create `milestone_type`, `project_service`, `project_document_requirement`, and `project_milestone_definition` as already authorized.

The implementation must make population rerun-safe where practical and must neither delete rows nor change their business semantics. This technical identity backfill is not Seed Data. It does not authorize reference-data Seed, MilestoneType catalog insertion, catalog apply, or Production execution.

Still prohibited are primary-key replacement, foreign-key conversion, existing-column rename, semantic changes, document/attachment/evidence mutation, operational behavior changes, or milestone catalog rows in the migration.

## API boundary

New Project Configuration requests and projections accept and return only `DocumentDefinition.public_id`. Resolution to the numeric key occurs server-side after authorization, with 404-safe handling for unknown or inaccessible references. `ProjectDocumentRequirement` has its own opaque `public_id` and stores the existing numeric DocumentDefinition foreign key internally. Project plus DocumentDefinition is unique; inactive definitions are blocked for new configuration while historical associations remain readable. No Document, Attachment, or Evidence is created.

Existing case-document APIs may temporarily continue their numeric contract to avoid breaking consumers. They are legacy technical debt, not normative precedent, and require a future bounded modernization Slice. New numeric API exposure is prohibited.

## Backward compatibility

Existing rows, numeric primary keys, foreign keys, case-document consumers, semantics, and behavior remain intact. The additive identity does not substitute numeric values in legacy payloads and does not modify operational or document records.

## Rollback

Before application use and before ProjectDocumentRequirement data exists, an authorized downgrade may remove the new tables and `public_id`. After new configuration data or APIs depend on the identity, the default application rollback retains the additive column and tables while reverting application code. Database downgrade then requires explicit authorization and preservation/export of configuration data; `public_id` must not be dropped while dependent APIs or data remain.

## Decision record

| Decision | Status |
| --- | --- |
| DocumentDefinition opaque identity | Accepted |
| Existing-row identity backfill | Accepted |
| Legacy numeric APIs | Temporarily tolerated; not normative |
| New numeric API exposure | Prohibited |
| Migration boundary amendment | Accepted |
| Release 1.8.0 implementation authority | Restored |

No personal signatures are asserted. This amendment authorizes implementation only; it authorizes no deployment, Production change, Seed execution, push, tag, or package.

## Implementation reconciliation

Migration `20260811_project_configuration` implements the nullable-add, independent UUIDv4 existing-row backfill, unique constraint, and non-null enforcement. Numeric primary keys and existing foreign keys are preserved. New Release 1.8.0 APIs expose only opaque public IDs; legacy numeric case-document APIs remain temporarily compatible. Disposable PostgreSQL 18 fresh, upgrade, downgrade, and re-upgrade evidence passed. Production remains unchanged and Seed was not executed.
