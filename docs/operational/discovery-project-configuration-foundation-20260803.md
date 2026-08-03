# Discovery — Project Configuration Foundation

- **Date:** 2026-08-03
- **Target candidate:** Release 1.8.0
- **Status:** Closed — governance accepted; bounded implementation authorized; not implemented
- **Evidence baseline:** branch `feature/case-document-management-phase1a`, commit `46cfc2bd359ee28968e8bdde3ed1eebfda1b1f0f`

## Evidence method and labels

- **Repository evidence** is directly observed in source, migrations, release records, or accepted governance.
- **Governance decision** is an accepted rule from an authoritative record.
- **Design recommendation** is proposed here and carries no implementation authority.
- **Unresolved business question** requires role-based approval; no interview evidence is claimed.

## Baseline and current maturity

Repository evidence: `v1.7.0` resolves to the baseline commit; the migration chain ends at `20260810_logistics_network`; Release 1.7.0 is published but not deployed; Production remains 1.6.1 and Production Seed has not run. The tracked working tree was clean before this discovery; pre-existing untracked `.codex/` and immutable release-package directories were not modified.

Project is more than descriptive today: it has organization/customer ownership, public/tracking identity, immutable organization-local code, lifecycle, version, party relationships, ShipmentRequest/ExecutionUnit relationships, OperationalShipment linkage, and an implemented 1.7.0 ProjectLogisticsPoint configuration/API/UI. It is not yet a coherent service/document/milestone/default configuration surface.

## Implementation inventory

| Area | Repository evidence | Capability classification | Gap / reuse conclusion |
| --- | --- | --- | --- |
| Project and organization/customer | `Project`, `project_party_relationship`, organization-first operational membership | Implemented; Project Configuration foundation | Reuse aggregate and tenant boundary. No duplicate Project. |
| ServiceType | Governed `ServiceType` table/admin/reference APIs | Implemented Reference Data; Seed not in Production | Reuse. ProjectService relationship is absent. |
| Project services | No Project–ServiceType relationship found | Absent at evidence baseline | New explicit ProjectService is justified; no Service entity is justified. |
| Transport | Legacy `TransportMethod`; RouteLeg `transport_mode` string; request transport fields | Existing but conceptually inconsistent | Keep separate from ServiceType. A canonical TransportMode record/default is not ready for this slice. |
| Logistics network | LogisticsPointType, LogisticsPoint, ProjectLogisticsPoint, v2 APIs, ProjectLogisticsNetwork UI | Implemented in 1.7.0 source; not deployed | Integrate existing capability; do not duplicate or auto-generate routes/checkpoints. |
| Route/Checkpoint/Milestone | Revisioned RoutePlan, RouteLeg, OperationalCheckpoint, operational Milestone and MilestoneEvent | Implemented Operational Execution | Do not reuse rows as Project templates. Add a separate definition only if approved. |
| Documents | DocumentDefinition, CaseDocumentRequirement, CaseDocumentFile, DocumentAuditEvent and internal case UI/API | Implemented in case context | Reuse DocumentDefinition as the governed document-category definition. Its missing opaque identity was discovered as an implementation blocker and is now resolved by the accepted identity amendment; no duplicate DocumentType is authorized. |
| SLA/targets | Request/expert SLA minutes/due fields and service; planned route/milestone timestamps | Bounded existing implementations | No Project SLA. Use only elapsed target/warning duration on milestone definition; do not call it full SLA. |
| Visibility/permissions | OperationalMembership JSON permission set, existing explicit permissions, event/file visibility rules | Implemented security foundation; document visibility governance partly Proposed | Add internal manage/read permissions only. No new role/authorization engine or customer/carrier visibility. |
| Defaults | Cargo catalog default UOM; request/quote currency strings; transport and location fields | Fragmented, context-specific | No governed Currency/Incoterm/default-language Project sources evidenced. Defer Project defaults. |
| Cargo | CargoType/UOM, CargoCatalogItem, immutable ShipmentCargoItem snapshot | Implemented | Do not add cargo defaults or rewrite snapshots. |
| Customer/parties | Customer master, primary customer, Project party roles including consignee | Implemented, partly legacy | Reuse. Shipper/carrier/forwarder canonical party roles remain unresolved. |

## Duplicate concepts and terminology conflicts

1. `DocumentDefinition` is the accepted governed document-category definition for Project requirements. Its category identity is reused; case snapshot behavior and file-policy fields remain unchanged. No duplicate DocumentType or rename is authorized.
2. `TransportMethod` and RouteLeg `transport_mode` coexist without an accepted canonical relationship. Neither is ServiceType.
3. “SLA” is used for expert/request timing but the candidate only supplies target duration; reporting must not conflate them.
4. `CanonicalLocation`, LogisticsPoint, and checkpoint/location fields coexist for different purposes. ADR-025 correctly prevents synonym collapse.
5. Milestone rows are operational instances; Project milestone configuration requires a definition, not reuse of operational rows.
6. Document, file, requirement, and evidence have overlapping informal language but distinct lifecycles.

## Candidate scope options

| Option | Business value | Complexity / dependencies | Migration and UI impact | Operational/reporting value | Major risks / governance burden | Recommended split |
| --- | --- | --- | --- | --- | --- | --- |
| A — Minimal | States offered services, expected network, and required documents. | Low–medium; ServiceType, 1.7.0 network, compatible document taxonomy. | Two proposed association tables; Project Configuration panels for services/network/documents. | No execution effects; basic configured-service/network/document dimensions. | DocumentDefinition reuse ambiguity; low–medium governance. | One 1.8.0 slice; milestone targets later. |
| B — Tightly bounded Balanced | Adds expected milestone sequence and simple elapsed targets, making configuration operationally useful without automation. | Medium; all A dependencies plus canonical milestone codes and ADR-027. | Adds milestone definition with target/warning fields; one additional panel. | Manual planning reference; future on-time dimensions, but no compliance claim. | Template/instance confusion and premature SLA language; medium governance. | Recommended for 1.8.0 only if D05/D07/D09 accepted; snapshot/enforcement later. |
| C — Broad | Adds defaults, visibility, and enforcement. | High; missing Currency/Incoterm/TransportMode governance, security policy, snapshot/enforcement orchestration. | Many schema/API/UI changes and likely cross-aggregate behavior. | Higher eventual automation/reporting. | Tenant leakage, historical rewriting, hidden side effects, low-maturity workflow; high governance. | Reject for 1.8.0; split into later evidence-backed slices. |

## Recommendation

Governance decision: choose Option B, tightly bounded. Include ProjectService, integration of existing ProjectLogisticsPoint, ProjectDocumentRequirement, ProjectMilestoneDefinition, and elapsed target/warning durations attached to milestone definitions. DocumentDefinition is reused as the category. A new governed MilestoneType catalog is authorized because no reusable governed configuration taxonomy exists; operational milestone strings are not reused as the catalog.

Proposed identity rules: one active ProjectService per `(project, service_type)`; zero or one primary service, all others secondary; required/optional is independent of primary/secondary. A ProjectMilestoneDefinition is unique by `(project, canonical_code)` and ordered among active definitions. Conditional documents carry the `CONDITIONAL` level and explanatory notes only; there is no expression or enforcement engine.

## Defaults assessment

| Candidate | Governed source | Project-level/snapshot conclusion | Recommendation |
| --- | --- | --- | --- |
| Currency | Quote/request strings; no governed currency catalog evidenced | Commercial/transaction context; snapshot policy unresolved | Defer |
| Incoterm | No canonical governed model evidenced | Commercial agreement, not safely a Project default yet | Defer |
| TransportMode | String usage; no governed catalog evidenced | Could be Project or leg-specific; snapshot unresolved | Defer |
| cargo UOM | UnitOfMeasure exists | Cargo item/category-specific; one Project default is unsafe | Defer |
| weight/volume UOM | UnitOfMeasure exists | Dimension-specific defaults may be organization/user policy | Defer |
| language | UI i18n exists; no Project language policy | Customer/communication context | Defer |

## Visibility assessment

Use existing organization membership and explicit backend permissions for internal `project_configuration.read` and `project_configuration.manage` (or bounded resource permissions accepted during implementation design). Admin/manager/expert/dispatcher semantics must map through existing membership policy, not hard-coded new role logic. Customer and carrier configuration access is unauthorized and excluded. Existing public Project tracking does not imply configuration visibility.

## Dependencies, reporting, and deferred work

Dependencies: governance acceptance of PDR-017, D01–D15, ADR-027, document taxonomy reuse, milestone codes, organization-isolation rules, and the separately deployed/available 1.7.0 logistics network. Implementation must verify the migration chain and PostgreSQL constraints.

Future reporting can compare configured services, expected points, required documents, and target definitions with separately captured execution snapshots. Current configuration is not historical execution truth. No target compliance, delay, SLA, dwell, document-completion, or customer visibility claim is valid until snapshot/measurement semantics and data quality are accepted.

Deferred: workflow/BPMN/rules, conditional expressions, event bus, GIS/maps, ETA/optimization/capacity/allocation, cargo-to-unit allocation, customer/carrier/public configuration UI, dashboards, automatic route/checkpoint/milestone generation, document approval/enforcement, calendars/penalties/escalations, imports, EAV/JSON settings, AI, and Production changes.

## Discovery conclusion

Governance closed on 2026-08-03. Product, Architecture, Operations, and Data role approval is recorded, with Security consulted where applicable; no individual signatures are asserted. PDR-017 and ADR-027 are Accepted, D01–D15 are Accepted, and the bounded Slice is authorized for implementation. Release 1.8.0 remains Not Yet Implemented and Not Deployed; Production remains 1.6.1.

### Closure note — DocumentDefinition identity

Implementation reconciliation found that DocumentDefinition lacked the opaque identity required by new Project Configuration APIs. The accepted [DocumentDefinition Identity Amendment](release-1.8.0-document-definition-identity-amendment.md) authorizes an immutable UUIDv4 `public_id`, migration-only population of existing rows, and the corresponding migration-boundary change while preserving numeric keys and legacy consumers. Release 1.8.0 implementation authority is restored; legacy numeric APIs remain temporary technical debt and are not normative.
