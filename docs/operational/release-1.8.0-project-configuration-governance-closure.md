# Release 1.8.0 — Project Configuration Governance Closure

- **Status:** Governance Accepted / Implemented / Not Published / Not Deployed
- **Acceptance date:** 2026-08-03
- **Authority:** Product, Architecture, Operations, and Data role authorities; Security consulted where applicable
- **Production:** Unchanged at 1.6.1

## Closure decision

Release 1.8.0 bounded Option B is authorized for implementation only. It contains ProjectService, reuse of existing ProjectLogisticsPoint, ProjectDocumentRequirement, ProjectMilestoneDefinition, and simple elapsed target/warning durations attached to ProjectMilestoneDefinition. This record authorizes no deployment, Production change, Seed apply, package, tag, or automatic execution behavior. No named individual signatures are asserted.

## Accepted scope and exclusions

Project is the configuration aggregate owner. The Slice adds three explicit configuration children and reuses the 1.7.0 ProjectLogisticsPoint association. It excludes a separate ProjectSlaDefinition; calendars, holidays, pause/resume clocks, penalties, escalations; defaults; a visibility engine or customer/carrier visibility; automatic OperationalShipment snapshots or operational record creation; document enforcement; workflow/BPMN/rule/conditional-expression engines; dashboards/reporting UI; allocation; GIS; ETA; optimization; AI; and all Production changes.

## D01–D15 closure

| ID | Result | Accepted decision |
| --- | --- | --- |
| D01 | Accepted | Tightly bounded Option B only. |
| D02 | Accepted | One active ProjectService per Project + ServiceType. |
| D03 | Accepted | At most one active primary per Project; draft configuration may have none. |
| D04 | Accepted | TransportMode remains separate; no inference from ServiceType. |
| D05 | Accepted | REQUIRED, OPTIONAL, and CONDITIONAL. |
| D06 | Accepted | CONDITIONAL is descriptive only; bounded reason/description, no engine. |
| D07 | Accepted | ProjectMilestoneDefinition is configuration, not an operational instance. |
| D08 | Accepted | No automatic OperationalShipment, RoutePlan, Checkpoint, Milestone, or Event creation. |
| D09 | Accepted | Optional target and warning values use MINUTE/HOUR/DAY and ELAPSED_TIME only. |
| D10 | Accepted | Defaults deferred; no generic settings or JSON. |
| D11 | Accepted | Existing organization/membership/role/permission mechanisms only; internal access only. |
| D12 | Accepted | Snapshots deferred to a separate accepted Slice; configuration never rewrites history. |
| D13 | Accepted | Active/inactive, optimistic version, no hard delete after use, readable history. |
| D14 | Accepted | Organization-first authorization, opaque IDs, 404-safe tenant isolation. |
| D15 | Accepted | Authority is limited to this bounded Release 1.8.0 Slice. |

## Taxonomy resolutions

### Document category

Repository model, migration, internal API, and admin UI evidence show that `DocumentDefinition` is the existing governed document-category/policy concept: it has an immutable code, revision, activation, description, applicability, ordering, file-policy fields, audit actors, and case requirement snapshots. ProjectDocumentRequirement references that existing definition. No duplicate DocumentType is implemented. Project-specific requirement level and conditional description belong to ProjectDocumentRequirement; DocumentDefinition case defaults do not override them. The association is configuration, not a Document, Attachment, Evidence, receipt or validity proof, and it cannot block execution in 1.8.0.

The accepted identity amendment adds a stable, immutable, unique, non-null UUIDv4 `public_id` to DocumentDefinition. Existing rows receive newly generated UUIDv4 values in the migration; the numeric primary key and internal foreign keys remain unchanged. New 1.8.0 APIs use only the opaque identity. Existing numeric case-document APIs are temporarily tolerated for compatibility, not normative, and require a future bounded modernization Slice.

### Milestone taxonomy

No governed reusable milestone category exists. Current `operational_milestone.milestone_type` values are constrained execution-instance strings and are not reused as configuration taxonomy. A separate `MilestoneType` Reference Data catalog is authorized with immutable code, Persian and English labels, definition, active/inactive state, and display order. Initial codes are `REQUEST_RECEIVED`, `CARGO_READY`, `PICKUP`, `LOADING`, `DEPARTURE`, `BORDER_ARRIVAL`, `CUSTOMS_START`, `CUSTOMS_COMPLETE`, `PORT_ARRIVAL`, `DISCHARGE`, `DELIVERY`, `COMPLETION`, and `OTHER_GOVERNED`. The catalog is separately versioned/checksummed; transport-mode-specific additions require later governance.

## ADR and aggregate boundary

ADR-027 is Accepted for this scope. ProjectService, ProjectDocumentRequirement, ProjectMilestoneDefinition, and existing ProjectLogisticsPoint are configuration. Document/Attachment/Evidence, Operational Milestone, OperationalShipment, RoutePlan, Checkpoint, and OperationalEvent retain separate lifecycles. Configuration changes do not rewrite operational history. Generic EAV/JSON settings and hidden cross-aggregate side effects are prohibited.

## Migration and Seed boundary

Implementation may create additive migration `20260811_project_configuration` with parent `20260810_logistics_network`. It may alter `document_definition` only to add nullable `public_id`, technically backfill existing rows with generated UUIDv4 values, enforce uniqueness, and make it non-null, then create the approved new tables. This identity backfill is not Seed. It may not mutate semantics, replace numeric keys, modify Project or OperationalShipment rows, infer associations, add defaults, or insert catalog rows. It must retain one Alembic head and prove safe downgrade/re-upgrade. No migration is created or run by this closure.

MilestoneType catalog planning is read-only. Apply must be explicit, audited, idempotent, and based on its version/checksum. No Seed execution is authorized, and Production apply requires separate authority. Existing ServiceType and DocumentDefinition records are reused without silently altering approved catalogs.

## API, UI, and security boundary

Internal APIs may be implemented under `/api/v2/projects/{project_public_id}/configuration` for `services`, `document-requirements`, and `milestone-definitions`; the existing logistics-points resource is reused. APIs require opaque IDs, organization-first authorization, bounded pagination/sorting, filter allowlists, optimistic conflicts, active/inactive lifecycle, no hard delete, no numeric ID leakage, no public/customer endpoint, and no execution side effects.

The Project Configuration UI contains Services, Network, Documents, and Milestones. Governed identities use selectors, forms/tables are simple, mobile-safe and bilingual where supported, and copy clearly states “configuration, not live operation.” No workflow/timeline/rule designer is authorized.

## Rollback and compatibility principles

Implementation is expand-first. The authorized DocumentDefinition identity population is the sole technical backfill. Before application use, an authorized downgrade may remove the new identity and tables. After ProjectDocumentRequirement data exists, default rollback reverts application code while retaining additive schema; database downgrade requires explicit authority and preservation/export of configuration data. Existing Projects, numeric DocumentDefinition keys and consumers, ProjectLogisticsPoints, OperationalShipments, RoutePlans, Checkpoints, Milestones, Events, documents, and shipment flows remain unchanged.

## Implementation authority

The bounded persistence models, migration, API, selectors, and UI are implemented and acceptance evidence is recorded in the traceability matrix and final RC review. Release 1.8.0 is implementation complete, not published, and not deployed. The MilestoneType catalog is prepared but not applied; Production is unchanged and Seed was not executed. Deployment, Seed apply, packaging, tagging, publication, reporting, visibility, defaults, snapshots, and automation remain separately governed or explicitly deferred.
