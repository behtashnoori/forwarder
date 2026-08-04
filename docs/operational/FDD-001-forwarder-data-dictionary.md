# FDD-001 — Forwarder Business Data Dictionary

## Release 1.9.0 authorized vocabulary reconciliation

Implementation reconciliation: **Implemented — Not Published — Not Deployed** under `20260812_operational_execution`; Evidence and dashboards/reporting remain excluded.

PDR-018 is Partially Accepted and ADR-029 is Accepted: **Governance Accepted — Implementation Authorized — Not Implemented — Not Deployed**. `ProjectMilestoneDefinition` remains configuration; the existing operational `Milestone` is the authorized shipment execution instance. Lifecycle, verification, and Shipment status are distinct; Delay is an independent condition; correction appends rather than deletes; timeline differs from audit. `DelayReason` and `ExceptionReason` are separate administrator-managed catalogs with no Seed or deployed rows. Evidence linkage is Deferred because ADR-020 remains Proposed; progress is calculated, not stored. Security Track is complete; the future Release 1.9.0 migration parent is `security_credential_remediation`.

- **Status:** Living Document
- **Architecture version:** DA-1.0
- **Date:** 2026-08-02
- **Vocabulary authority:** [Canonical Business Object Catalog](canonical_business_object_catalog.md)

This is the authoritative business dictionary, not a raw schema inventory. Implementation state is based on repository and deployment evidence. `TBD — Governance Required` means evidence is insufficient; it is not permission to infer a value.

## FDD-001-001 — Organization

- **Canonical/Persian:** Organization / سازمان; **definition/rationale:** tenant and operational ownership boundary used to isolate reusable and transactional facts.
- **Class/owners:** Master Data; business owner Security/Product; system owner CAP-010.
- **Lifecycle/identity/scope:** active/inactive; internal ID plus opaque public ID; one organization scope per record.
- **Relationships:** memberships, Projects, OperationalShipments, CargoCatalogItems, future LogisticsPoints.
- **Mutable/immutable:** name/active mutable; public identity immutable; ownership changes require governance.
- **Activation/history:** no casual delete; inactive scope remains historical. **API/UI/reporting:** resolved by backend membership; organization dimension, never client authority.
- **Version/state/future/exclusions:** operational foundation; Implemented and Deployed; future enterprise tenancy policy; excludes cross-tenant sharing by assumption.
- **Governance/source:** Constitution, ADR-017, ADR-022, ADR-025; `backend.operational_models.OperationalOrganization`.

## FDD-001-002 — ExpertUser

- **Canonical/Persian:** ExpertUser / کاربر کارشناس; **definition/rationale:** authenticated internal principal acting through roles/memberships.
- **Class/owners:** Master Data/security identity; business owner TBD — Governance Required; system owner CAP-010.
- **Lifecycle/identity/scope:** user lifecycle; internal ID and authentication identity; organization access through OperationalMembership.
- **Relationships:** audit actors, membership, created/updated records. **Mutable/immutable:** profile/role state mutable; identity/audit references stable.
- **Activation/history:** deactivation must retain actor history; deletion policy TBD. **API/UI/reporting:** authentication/admin surfaces; actor audit, not business KPI.
- **Version/state/future/exclusions:** legacy/foundation; Implemented and Deployed; future principal unification; excludes AI authority inheritance beyond permission.
- **Governance/source:** Security Standard, permission matrices; `backend.models.ExpertUser` and auth/security services.

## FDD-001-003 — Customer

- **Canonical/Persian:** Customer / مشتری; **definition/rationale:** business party receiving/requesting service; not a location or organization synonym.
- **Class/owners:** Master Data; Product/CRM; system owner CAP-002/CAP-007.
- **Lifecycle/identity/scope:** CRM lifecycle; internal/public identity varies by legacy surface; linked to operational organization where governed.
- **Relationships:** ShipmentRequest, Project party roles, optional future customer-site relationship. **Mutable/immutable:** contact/profile mutable; historical transaction references stable.
- **Activation/history:** governed CRM behavior; hard-delete rules remain source-specific. **API/UI/reporting:** CRM/request/Project views; customer reporting dimension under authorization.
- **Version/state/future/exclusions:** legacy foundation; Implemented and Deployed; party/stakeholder refinement; Customer is not LogisticsPoint.
- **Governance/source:** Catalog, ADR-017, PDR-001; `backend.models.Customer`.

## FDD-001-004 — Project

- **Canonical/Persian:** Project / پروژه; **definition/rationale:** business coordination boundary grouping requests, execution, parties, and configuration.
- **Class/owners:** Configuration/aggregate; Product; CAP-001.
- **Lifecycle/identity/scope:** not_started→in_progress→partially_delivered/completed/cancelled; UUID public ID, immutable org-local ProjectCode, tracking code; organization-scoped.
- **Relationships:** Customer parties, ShipmentRequests, OperationalShipments, ExecutionUnits, future ProjectLogisticsPoints.
- **Mutable/immutable:** lifecycle/configuration mutable with version; identity/organization immutable. **Activation/history:** no rewrite of execution; deletion prohibited after use.
- **API/UI/reporting:** internal/public tracking as authorized; central reporting dimension.
- **Version/state/future/exclusions:** 1.2.0 lineage; Implemented and Deployed; Logistics Network configuration; excludes automatic RoutePlan generation.
- **Governance/source:** PDR-001–004, ADR-017; `backend.operational_models.Project`.

## FDD-001-005 — ShipmentRequest

- **Canonical/Persian:** ShipmentRequest / درخواست حمل; **definition/rationale:** commercial request capturing customer intent before operational execution.
- **Class/owners:** Transaction; Product; CAP-002.
- **Lifecycle/identity/scope:** commercial statuses; request/tracking identity; customer/organization access governed by existing contracts.
- **Relationships:** Customer, Quote, Project, later OperationalShipment lineage. **Mutable/immutable:** request fields/status mutable per workflow; tracking identity stable.
- **Activation/history:** logs preserve change; deletion behavior governed by legacy policy. **API/UI/reporting:** customer request/admin/expert surfaces; commercial reporting.
- **Version/state/future/exclusions:** original application foundation; Implemented and Deployed; structured service/cargo evolution; not OperationalShipment.
- **Governance/source:** ADR-002/007, Catalog; `backend.models.ShipmentRequest`.

## FDD-001-006 — OperationalShipment

- **Canonical/Persian:** OperationalShipment / محموله عملیاتی; **definition/rationale:** execution aggregate created from accepted commercial lineage.
- **Class/owners:** Transaction/operational aggregate; Operations/Product; CAP-002.
- **Lifecycle/identity/scope:** planned/in_progress/completed/cancelled; UUID; organization-scoped.
- **Relationships:** Project, ShipmentRequest, accepted Quote, RoutePlans, ShipmentCargoItems, ExecutionUnits.
- **Mutable/immutable:** lifecycle/version mutable; lineage and public identity stable. **Activation/history:** cancellation does not erase history; no hard delete.
- **API/UI/reporting:** internal operational APIs/workspace; shipment status/count dimension.
- **Version/state/future/exclusions:** operational foundation; Implemented and Deployed; standardized visibility; not ShipmentRequest.
- **Governance/source:** ADR-002/003/007/017; `backend.operational_models.OperationalShipment`.

## FDD-001-007 — ExecutionUnit

- **Canonical/Persian:** ExecutionUnit / واحد اجرایی; **definition/rationale:** independently managed physical/logical execution unit within a Project.
- **Class/owners:** Transaction/aggregate; Operations; CAP-003.
- **Lifecycle/identity/scope:** not_started/ready/in_progress/arrived/delivered/cancelled plus active state; UUID and Project-local unit code; Project/organization-scoped.
- **Relationships:** Project, optional OperationalShipment, OperationalEvents, legacy ShipmentTransportUnit.
- **Mutable/immutable:** lifecycle/display/operational attributes mutable with version; identity/code stable. **Activation/history:** deactivate, do not erase events.
- **API/UI/reporting:** internal execution pages; unit status/performance dimension.
- **Version/state/future/exclusions:** 1.3.0-era foundation; Implemented and Deployed; future cargo linkage; allocation/split-merge deferred.
- **Governance/source:** ADR-018, PDR-005/006; `backend.operational_models.ExecutionUnit`.

## FDD-001-008 — OperationalEvent

- **Canonical/Persian:** OperationalEvent / رویداد عملیاتی; **definition/rationale:** append-only evidence envelope for an operational fact.
- **Class/owners:** Evidence; Architecture/Operations; CAP-004.
- **Lifecycle/identity/scope:** recorded once; corrections supersede; opaque event ID; organization/subject scoped.
- **Relationships:** Project, ExecutionUnit and governed subjects; timeline projection/audit remain distinct.
- **Mutable/immutable:** fact envelope immutable; visibility/schema governed. **Activation/history:** never destructively updated/deleted through business APIs.
- **API/UI/reporting:** permission-filtered timeline; dwell/status evidence where defined.
- **Version/state/future/exclusions:** existing bounded model; Implemented and Deployed; wider event catalog; not configuration/audit synonym.
- **Governance/source:** ADR-019; `backend.operational_models.OperationalEvent`.

## FDD-001-009 — RoutePlan

- **Canonical/Persian:** RoutePlan / برنامه مسیر; **definition/rationale:** revisioned operational plan for one OperationalShipment.
- **Class/owners:** Configuration within execution; Operations; CAP-002/CAP-003.
- **Lifecycle/identity/scope:** draft/active/superseded/cancelled; internal identity/revision; shipment organization inherited.
- **Relationships:** OperationalShipment, RouteLeg, Checkpoint, Milestone. **Mutable/immutable:** draft mutable; active structure immutable/revisioned.
- **Activation/history:** supersede rather than rewrite; historical revisions retained. **API/UI/reporting:** operational planning/timeline; plan progress.
- **Version/state/future/exclusions:** Phase 1A/1B; Implemented and Deployed; explicit future point reference; never auto-created by ProjectLogisticsPoint.
- **Governance/source:** ADR-004, ADR-017, phase1b route docs; `backend.operational_models.RoutePlan`.

## FDD-001-010 — Checkpoint

- **Canonical/Persian:** Checkpoint / نقطه کنترل; **definition/rationale:** ordered execution-plan element used in route orchestration.
- **Class/owners:** Configuration/execution plan; Operations; CAP-003.
- **Lifecycle/identity/scope:** plan-owned state; identity and lifecycle per Phase 1B model; organization inherited.
- **Relationships:** RoutePlan/legs/dependencies/milestones; future explicit LogisticsPoint reference only if governed.
- **Mutable/immutable:** active plan structure revision-controlled; projected values derived. **Activation/history:** plan supersession preserves history.
- **API/UI/reporting:** operational timeline; delay/progress input. **Version/state/future/exclusions:** Phase 1B; Implemented and Deployed; point reference future; not LogisticsPoint.
- **Governance/source:** ADR-004, phase1b documents; `backend.operational_models.RouteCheckpoint`.

## FDD-001-011 — Milestone

- **Canonical/Persian:** Milestone / نقطه عطف; **definition/rationale:** planned/projected/actual control fact in route execution.
- **Class/owners:** Transaction/configuration fact; Operations; CAP-003/CAP-004.
- **Lifecycle/identity/scope:** planned/reported/verified/corrected semantics; route-owned identity; organization inherited.
- **Relationships:** RoutePlan/RouteLeg/Checkpoint and MilestoneEvents. **Mutable/immutable:** projections/current verification mutable via governed commands; event history immutable.
- **Activation/history:** correction appends evidence; no destructive rewrite. **API/UI/reporting:** timeline/verification; delay/dwell facts.
- **Version/state/future/exclusions:** Phase 1A/1B; Implemented and Deployed; broader reporting later; not OperationalEvent synonym.
- **Governance/source:** ADR-004/009/019; `backend.operational_models.Milestone`.

## FDD-001-012 — CargoType

- **Canonical/Persian:** CargoType / نوع کالا; **definition/rationale:** governed cargo classification.
- **Class/owners:** Reference Data; Product/Data; CAP-013.
- **Lifecycle/identity/scope:** active/inactive hierarchy; UUID and immutable global code; organization-independent.
- **Relationships:** catalog and shipment snapshots. **Mutable/immutable:** labels/order/description active state mutable with version; code immutable.
- **Activation/history:** deactivate, no used-value deletion; historical snapshots readable. **API/UI/reporting:** admin/selectors; cargo dimension.
- **Version/state/future/exclusions:** 1.4.0 schema, 1.5.0 catalog; Implemented and Deployed, Production Seed not executed; taxonomy growth governed; no generic EAV.
- **Governance/source:** PDR-013/014, ADR-021; `backend.models.CargoType`.

## FDD-001-013 — ServiceType

- **Canonical/Persian:** ServiceType / نوع خدمت; **definition/rationale:** governed service classification distinct from TransportMethod.
- **Class/owners:** Reference Data; Product/Data; CAP-013.
- **Lifecycle/identity/scope:** active/inactive; UUID/immutable global code; organization-independent.
- **Relationships:** future service packages; current relationships unresolved. **Mutable/immutable:** labels/order/description mutable with version; code immutable.
- **Activation/history:** deactivate, preserve history. **API/UI/reporting:** admin/reference selectors; service dimension when relationships accepted.
- **Version/state/future/exclusions:** 1.4.0/1.5.0; Implemented and Deployed, Production Seed not executed; relationships future; not TransportMethod.
- **Governance/source:** PDR-013 D02/D03 Proposed boundaries, PDR-014, ADR-021; `backend.models.ServiceType`.

## FDD-001-014 — UnitOfMeasure

- **Canonical/Persian:** UnitOfMeasure / واحد اندازه‌گیری; **definition/rationale:** governed unit and measurement dimension for structured quantities.
- **Class/owners:** Reference Data; Product/Data; CAP-013.
- **Lifecycle/identity/scope:** active/inactive; UUID/immutable code; organization-independent.
- **Relationships:** ShipmentCargoItem and catalog defaults. **Mutable/immutable:** labels/symbol/order mutable with version; code/dimension governed.
- **Activation/history:** inactive historical values readable; no implicit conversion. **API/UI/reporting:** admin/selectors; quantity interpretation.
- **Version/state/future/exclusions:** 1.4.0/1.5.0; Implemented and Deployed, Production Seed not executed; conversions deferred.
- **Governance/source:** PDR-013 D04, PDR-014, ADR-021/022; `backend.models.UnitOfMeasure`.

## FDD-001-015 — CargoCatalogItem

- **Canonical/Persian:** CargoCatalogItem / قلم کاتالوگ کالا; **definition/rationale:** reusable organization-owned cargo definition.
- **Class/owners:** Master Data; Data/Product; CAP-013.
- **Lifecycle/identity/scope:** active/inactive; UUID and immutable organization-local code; organization-scoped.
- **Relationships:** CargoType, default UOM, aliases, optional ShipmentCargoItem lineage.
- **Mutable/immutable:** descriptive fields mutable with version; code/organization/public identity immutable. **Activation/history:** no hard delete after use; snapshots unchanged.
- **API/UI/reporting:** internal admin/catalog; governed cargo dimension under tenant scope.
- **Version/state/future/exclusions:** 1.6.0; Implemented and Deployed; internal search later; no global catalog/customer public search.
- **Governance/source:** PDR-013 D05/D06, ADR-022; `backend.cargo_models.CargoCatalogItem`.

## FDD-001-016 — CargoItemAlias

- **Canonical/Persian:** CargoItemAlias / نام جایگزین قلم کالا; **definition/rationale:** governed alternate term owned by one catalog item.
- **Class/owners:** Master Data child; Data; CAP-013.
- **Lifecycle/identity/scope:** active/inactive; UUID; inherits catalog organization.
- **Relationships:** exactly one CargoCatalogItem. **Mutable/immutable:** alias text/type/language lifecycle governed; parent/scope stable.
- **Activation/history:** deactivate; no silent merge/cross-tenant collision. **API/UI/reporting:** catalog admin/matching; not independent reporting identity.
- **Version/state/future/exclusions:** 1.6.0; Implemented and Deployed; search assistance later; not public search authority.
- **Governance/source:** PDR-013 D06, ADR-022; `backend.cargo_models.CargoItemAlias`.

## FDD-001-017 — ShipmentCargoItem

- **Canonical/Persian:** ShipmentCargoItem / قلم کالای محموله; **definition/rationale:** OperationalShipment-owned transaction snapshot of carried cargo meaning.
- **Class/owners:** Transaction snapshot; Product/Operations; CAP-002.
- **Lifecycle/identity/scope:** shipment line lifecycle; UUID and shipment-unique line; inherits organization.
- **Relationships:** OperationalShipment, CargoType, UOM, optional catalog lineage. **Mutable/immutable:** quantity handling bounded; snapshot facts immutable after creation.
- **Activation/history:** destructive rewrite prohibited; correction design deferred. **API/UI/reporting:** internal shipment cargo; cargo visibility foundation.
- **Version/state/future/exclusions:** 1.6.0; Implemented and Deployed; allocation/search later; no allocation/delivery semantics.
- **Governance/source:** PDR-013 D07, ADR-022; `backend.cargo_models.ShipmentCargoItem`.

## FDD-001-018 — ReferenceDataSeedRun

- **Canonical/Persian:** ReferenceDataSeedRun / اجرای بذر داده مرجع; **definition/rationale:** auditable record of an explicit governed catalog apply.
- **Class/owners:** Evidence; Data/Operations; CAP-013.
- **Lifecycle/identity/scope:** started/succeeded/failed/refused; UUID/catalog checksum; environment-scoped evidence.
- **Relationships:** catalog version/checksum and executor. **Mutable/immutable:** execution outcome finalized; identity/checksum evidence immutable.
- **Activation/history:** retained audit evidence; no business delete. **API/UI/reporting:** CLI/operations evidence; seed status.
- **Version/state/future/exclusions:** 1.5.0; Implemented and deployed schema; Production Seed not executed; multi-catalog extension requires safe design; not startup seed.
- **Governance/source:** PDR-014, ADR-021/011; `backend.models.ReferenceDataSeedRun`.

## FDD-001-019 — Country

- **Canonical/Persian:** Country / کشور; **definition/rationale:** governed geographic country reference.
- **Class/owners:** Reference Data; Data/Administration; CAP-013.
- **Lifecycle/identity/scope:** active/effective-dated; internal ID and ISO-like code; shared reference.
- **Relationships:** Province, international city, future LogisticsPoint. **Mutable/immutable:** names/provenance/effective dates governed; code stable.
- **Activation/history:** inactive values remain referenceable. **API/UI/reporting:** location selectors; geography dimension.
- **Version/state/future/exclusions:** legacy/reference foundation; Implemented and Deployed; LogisticsPoint required reference; not LogisticsPoint.
- **Governance/source:** ADR-005/025; `backend.models.Country`.

## FDD-001-020 — Province

- **Canonical/Persian:** Province / استان; **definition/rationale:** governed first-level geographic reference.
- **Class/owners:** Reference Data; Data/Administration; CAP-013.
- **Lifecycle/identity/scope:** active/effective-dated; internal ID/code within country; shared reference.
- **Relationships:** Country, County, City, future LogisticsPoint. **Mutable/immutable:** names/provenance governed; code identity stable where present.
- **Activation/history:** retain references; no conversion into logistics place. **API/UI/reporting:** geographic selectors/dimension.
- **Version/state/future/exclusions:** legacy/reference foundation; Implemented and Deployed; optional point geography; not warehouse/port.
- **Governance/source:** ADR-005/025; `backend.models.Province`.

## FDD-001-021 — City

- **Canonical/Persian:** City / شهر; **definition/rationale:** governed city reference within Province/County.
- **Class/owners:** Reference Data; Data/Administration; CAP-013.
- **Lifecycle/identity/scope:** active/effective-dated; internal ID/code within County; shared reference.
- **Relationships:** County, Province, future LogisticsPoint. **Mutable/immutable:** name/provenance governed; geography identity stable.
- **Activation/history:** retain references; no conversion into logistics place. **API/UI/reporting:** location selectors/dimension.
- **Version/state/future/exclusions:** legacy/reference foundation; Implemented and Deployed; optional point geography; not LogisticsPoint.
- **Governance/source:** ADR-005/025; `backend.models.City`.

## FDD-001-022 — LogisticsPointType

- **Canonical/Persian:** LogisticsPointType / نوع نقطه لجستیکی; **definition/rationale:** cross-industry classification of a LogisticsPoint.
- **Class/owners:** Reference Data; Product/Data; CAP-013.
- **Lifecycle/identity/scope:** active/inactive; UUID and immutable global code; organization-independent.
- **Relationships:** LogisticsPoint. **Mutable/immutable:** labels/definition/order/state mutable with version; code immutable.
- **Activation/history:** deactivate; referenced history readable. **API/UI/reporting:** implemented admin/selectors; no reporting UI.
- **Version/state/future/exclusions:** 1.7.0; **Governance Accepted — Implemented, Not Deployed**; separate governed catalog prepared but not applied; excludes loading/unloading/generic terminal types.
- **Governance/source:** PDR-016, ADR-025, accepted 1.7.0 contract; `backend.logistics_network_models.LogisticsPointType`.

## FDD-001-023 — LogisticsPoint

- **Canonical/Persian:** LogisticsPoint / نقطه لجستیکی; **definition/rationale:** reusable organization-owned real-world logistics place.
- **Class/owners:** Master Data; Data/Product; CAP-013.
- **Lifecycle/identity/scope:** active/inactive; UUID and immutable org-local code; organization-scoped.
- **Relationships:** type, Country, optional Province/City, ProjectLogisticsPoint. **Mutable/immutable:** names/address/geography/state versioned; identity/code/organization immutable.
- **Activation/history:** no hard delete; inactive history readable and new selection blocked. **API/UI/reporting:** implemented admin/expert selection; no reporting UI.
- **Version/state/future/exclusions:** 1.7.0; **Governance Accepted — Implemented, Not Deployed**; future explicit operational references; excludes GIS/telemetry/public search.
- **Governance/source:** PDR-016, ADR-025, accepted 1.7.0 contract; `backend.logistics_network_models.LogisticsPoint`.

## FDD-001-024 — ProjectLogisticsPoint

- **Canonical/Persian:** ProjectLogisticsPoint / نقطه لجستیکی پروژه; **definition/rationale:** Project-specific association, role, and sequence for a governed point.
- **Class/owners:** Configuration; Product/Operations; CAP-001.
- **Lifecycle/identity/scope:** active/inactive; UUID and Project+point+role identity; Project organization-scoped.
- **Relationships:** Project and LogisticsPoint. **Mutable/immutable:** sequence/label/notes/state versioned; Project/point/role identity governed.
- **Activation/history:** removal means deactivation; no historical rewrite. **API/UI/reporting:** implemented Project configuration; no reporting UI.
- **Version/state/future/exclusions:** 1.7.0; **Governance Accepted — Implemented, Not Deployed**; operational linkage later; no RoutePlan/Checkpoint/Event generation.
- **Governance/source:** PDR-016, ADR-025, accepted 1.7.0 contract; `backend.logistics_network_models.ProjectLogisticsPoint`.

## FDD-001-025 — DocumentArtifact

- **Canonical/Persian:** DocumentArtifact / سند; **definition/rationale:** logical business document distinct from stored attachment/version.
- **Class/owners:** Master/Transaction boundary by document type; Product; CAP-005.
- **Lifecycle/identity/scope:** current bounded case-document lifecycle; opaque identity where implemented; request/project scope varies.
- **Relationships:** DocumentAttachment/version, requirements, business subjects. **Mutable/immutable:** metadata/state governed; historical versions/evidence preserved.
- **Activation/history:** no silent history replacement. **API/UI/reporting:** document tabs and evidence inventory.
- **Version/state/future/exclusions:** bounded case-document implementation exists/deployed lineage; platform-wide model partly Proposed; visibility/retention not generalized.
- **Governance/source:** ADR-020 Proposed and case-document records; `backend` case document models/services.

## FDD-001-026 — DocumentAttachment

- **Canonical/Persian:** DocumentAttachment / پیوست سند; **definition/rationale:** stored-file association to a business document/subject.
- **Class/owners:** Evidence; Product/Security; CAP-005.
- **Lifecycle/identity/scope:** upload/replace/verify per bounded feature; opaque identity where implemented; resource/visibility scoped.
- **Relationships:** artifact, storage object, actor/audit. **Mutable/immutable:** metadata/state mutable; historical bytes/version evidence preserved.
- **Activation/history:** destructive removal/visibility requires policy. **API/UI/reporting:** bounded document UI; evidence inventory.
- **Version/state/future/exclusions:** bounded implementation; platform visibility architecture Proposed; no universal customer visibility inference.
- **Governance/source:** ADR-020 Proposed, case-document docs/models/services.

## FDD-001-027 — OperationalAudit

- **Canonical/Persian:** AuditEntry (implemented OperationalAudit) / ثبت ممیزی; **definition/rationale:** security/command evidence distinct from business timeline.
- **Class/owners:** Evidence; Security/Operations; CAP-010.
- **Lifecycle/identity/scope:** append-only record; internal identity; organization/resource scoped.
- **Relationships:** actor, action, entity, correlation metadata. **Mutable/immutable:** immutable after record.
- **Activation/history:** retention-protected; not business-delete controlled. **API/UI/reporting:** internal audit/diagnostics; compliance evidence, not customer timeline.
- **Version/state/future/exclusions:** operational foundation; Implemented and Deployed; unified audit vocabulary future; excludes business-event ownership.
- **Governance/source:** Constitution, ADR-019; `backend.operational_models.OperationalAudit`.

## FDD-001-028 — OperationalOutbox

- **Canonical/Persian:** OperationalOutbox / صندوق خروجی عملیاتی; **definition/rationale:** reliable integration/event-delivery record committed with domain change.
- **Class/owners:** Evidence/integration infrastructure; Architecture/Operations; CAP-011/CAP-004.
- **Lifecycle/identity/scope:** pending/published/failure behavior per implementation; internal identity; organization/aggregate scoped.
- **Relationships:** domain command, aggregate, event payload. **Mutable/immutable:** delivery state mutable; emitted fact identity/payload controlled.
- **Activation/history:** retained for reconciliation per operations policy. **API/UI/reporting:** internal processing only; operational delivery metrics.
- **Version/state/future/exclusions:** operational foundation; Implemented and Deployed; integration expansion later; not OperationalEvent or audit synonym.
- **Governance/source:** ADR-019 and operational services; `backend.operational_models.OperationalOutbox`.

## Governance gaps

- Named business owner and deletion lifecycle for ExpertUser require explicit identity-governance confirmation.
- Platform-wide DocumentArtifact/DocumentAttachment visibility, retention, and customer action rules remain Proposed under ADR-020/PDR-008/009/011.
- ServiceType relationships remain unresolved under PDR-013 D02/D03.
- ShipmentCargoItem correction/supersession, allocation, and customer search remain deferred/proposed.
- Logistics Network physical/API choices are Accepted and implemented in Release 1.7.0 source; Production migration, catalog apply, packaging, and deployment remain separately governed.

## Release 1.8.0 implemented definitions — not deployed

The following entries are **Implemented — Not Deployed** for the bounded Release 1.8.0 Slice. Release 1.8.0 is implementation complete, not published, and not deployed; Production is unchanged and Seed was not executed.

### FDD-001-029 — ProjectService

- **Canonical/Persian:** ProjectService / خدمت پروژه; Project-owned association to one governed ServiceType.
- **Class/owners/scope:** Project Configuration; Product/Data; CAP-001/CAP-013; organization inherited from Project; opaque ID, version, active lifecycle.
- **Relationships/exclusions:** Project and ServiceType; not TransportMode, execution, snapshot, or generator.
- **Governance/reporting:** PDR-017 D02–D04 and ADR-027 Accepted; future service-mix dimension only after implementation.

### FDD-001-030 — ProjectDocumentRequirement

- **Canonical/Persian:** ProjectDocumentRequirement / الزام سند پروژه; Project declaration that a governed document category is required, optional, or conditional.
- **Class/owners/scope:** Project Configuration; Product/Operations; CAP-001/CAP-005; organization inherited from Project; opaque ID, version, active lifecycle.
- **Relationships/exclusions:** existing governed DocumentDefinition category, referenced by numeric FK internally and immutable UUIDv4 `public_id` externally; not a Document, Attachment, Evidence, receipt/validity proof, expression, approval, or blocking rule.
- **Governance/reporting:** PDR-017 D05/D06 and ADR-027 Accepted; completeness reporting requires later snapshot/enforcement governance.

#### DocumentDefinition identity amendment

- **Identity:** numeric primary key remains internal; a stable, unique, non-null, immutable UUIDv4 `public_id` is accepted for new API identity.
- **Population/compatibility:** migration-only technical identity backfill assigns generated UUIDv4 values to existing rows without semantic changes. Legacy numeric case-document APIs are temporarily tolerated; new numeric API exposure is prohibited.

### FDD-001-031 — ProjectMilestoneDefinition

- **Canonical/Persian:** ProjectMilestoneDefinition / تعریف نقطه عطف پروژه; ordered Project expectation with optional point and elapsed target.
- **Class/owners/scope:** Project Configuration; Product/Operations; CAP-001/CAP-003; organization inherited from Project; opaque ID, version, active lifecycle.
- **Relationships/exclusions:** governed MilestoneType and optional ProjectLogisticsPoint; not an operational Milestone, Event, workflow, or generation instruction.
- **Governance/reporting:** PDR-017 D07–D09 and ADR-027 Accepted; planned-versus-actual reporting requires separately accepted snapshots.

### FDD-001-032 — MilestoneType

- **Canonical/Persian:** MilestoneType / نوع نقطه عطف; governed cross-project category for Project milestone definitions.
- **Class/owners/scope:** Reference Data; Product/Data/Operations; immutable code, bilingual labels, definition, display order, active lifecycle.
- **Relationships/exclusions:** selected by ProjectMilestoneDefinition; not the existing operational Milestone row or its execution-specific string constraint.
- **Governance/reporting:** versioned/checksummed catalog; no migration Seed rows and no Production apply without separate authority.
## Permanent data-class administration policy

ADR-028 classifies LogisticsPointType, MilestoneType, ServiceType, DocumentDefinition, CargoType, UnitOfMeasure, Cargo Catalog, and equivalent governed lookups as administrator-managed Reference Data. They use immutable business codes, duplicate protection, activation/deactivation rather than hard delete, audit, and applicable organization rules. Empty catalogs are valid and no deployment or release validation depends on population.

System Data—roles, permissions, feature flags, internal configuration, framework metadata, and indispensable bootstrap objects—is separate and may be installer-generated. Master Data—Project, Customer, LogisticsPoint, Carrier, Vehicle, Driver, Organization—is user-created during normal operation. Operational Data—Shipment, RoutePlan, Quote, Operational Milestone, Operational Event, Invoice, Evidence—is created only through business execution. Seed/import/export/catalog-apply tools are optional migration utilities.
