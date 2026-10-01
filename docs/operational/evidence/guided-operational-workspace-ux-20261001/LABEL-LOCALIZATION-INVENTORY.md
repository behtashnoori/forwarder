# System-wide Label and Localization Inventory

## Result

`UX_008_SYSTEM_LABELS_LOCALIZATION=RESOLVED`

`RAW_ID_PRIMARY_UI_REMAINING=0`

`RAW_ENUM_PRIMARY_UI_REMAINING=0`

`UNLOCALIZED_PRIMARY_UI_REMAINING=0`

The audit rechecked all 38 substantive routes from the original 2026-10-01 route inventory. Classification is presentation-only: persisted values, API contracts, permissions, lifecycle meaning, and timezone semantics are unchanged.

## Route inventory

| Route / surface | Classification | Evidence |
|---|---|---|
| `/`, `/about`, `/contact` | RESOLVED | Public copy remains coherent; no raw application enum/UUID is primary. |
| Customer authentication, enrollment, recovery, verification, profile, password | RESOLVED | User-facing state and errors remain semantic; technical identity is not primary. |
| `/customer/requests` | RESOLVED | Request tracking/route/state are human labels; UUID is not the card title. |
| `/customer/requests/new` | RESOLVED | Cargo, transport, location, unit, and file controls use localized presentation. |
| `/customer/requests/:requestId` | RESOLVED | Current Quote/action and commercial progress are primary; Request detail and immutable Quote history are disclosed on demand; statuses and units are localized. |
| `/customer/shipments` and `/:shipmentId` | RESOLVED | Customer/route identity is primary; technical Shipment ID is secondary disclosure; transport/status/document/delivery labels are semantic. |
| `/customer/documents` | RESOLVED | Native file-copy leakage is removed; document lifecycle/context labels are semantic. |
| `/customer/track/:requestId` | RESOLVED | Public tracking presents capability-safe human status/timeline. |
| `/project/track/:trackingCode` | DEFERRED_POLISH | This separate public compatibility route is coherently English rather than mixed inside a Persian workflow; it has no HIGH raw ID/enum leakage. Full locale selection is outside this mission. |
| `/expert` | RESOLVED | Role/authority, Request state, priority, and next commercial action use semantic labels. |
| `/expert/requests/:id` | RESOLVED | Commercial facts/progress/action are primary; terminal actions are hidden; technical IDs/history are secondary. |
| `/crm`, `/customers` | RESOLVED | Customer identity/link state remains human-readable; no technical identifier is the primary label. |
| `/operations` | RESOLVED | Attention source/status and Shipment identity are semantic; source tokens and UUIDs are not primary. |
| `/operations/shipments` | RESOLVED | Human Shipment/customer/route identity is primary; UUID is explicit technical disclosure. |
| `/operations/shipments/new` | RESOLVED | Source, Request/Quote, project lifecycle, cargo, units, route, and review options use locale-aware semantic labels; IDs are selector values only. |
| Shipment Summary | RESOLVED | Human identity, stage, readiness, issue, ETA, and action are primary; technical identity is disclosed on demand. |
| Shipment Route & Execution | RESOLVED | Action, milestone, lifecycle, progress, reason, timeline, route, and equipment labels are Persian semantic presentation. |
| Shipment Stages | RESOLVED | Stage/status labels are semantic and progress-aware. |
| Shipment Cargo & Allocation | RESOLVED | Cargo identity and localized units are primary; Shipment/stage IDs are technical disclosure or form values. |
| Shipment Documents | RESOLVED | Lifecycle, context, audience, actions, history, file chooser, selected-file count, and result messages are localized; raw codes are not primary. |
| Shipment Tracking & ETA | RESOLVED | Status/location/ETA reason labels and dates are human-readable; structured codes remain internal. |
| Shipment Delivery | RESOLVED | Cargo/destination/state and localized units are primary; exact evidence identity remains secondary. |
| Shipment Closure | RESOLVED | Readiness, blockers, warnings, and actions are semantic; reason codes are technical disclosure. |
| Shipment History | RESOLVED | Event/source/status/unit labels and dual-calendar times are semantic; canonical IDs remain contextual links or technical detail. |
| `/operations/work-queue` | RESOLVED | Priority, type, owner, subject, status, and milestone labels are semantic; subject/policy IDs are collapsed technical detail. |
| `/operations/control-tower` | RESOLVED | Current route resolves to the semantic operational Control Tower; inactive definition-editor IDs remain configuration data. |
| `/operations/intelligence/:id` | RESOLVED | Situation health/type/priority/ownership/action labels are semantic; evidence and reason codes are technical disclosure. |
| `/operations/projects/:projectId/units` | RESOLVED | Execution state, allocations, events, and units are localized; Shipment IDs are collapsed technical detail. |
| `/dashboards*` | INTENTIONALLY_TECHNICAL | Dashboard builder IDs/query definitions are explicit configuration/editor context; normal dashboard titles, widgets, and filters remain semantic. |
| `/admin`, `/admin/customers`, `/admin/customer-portal-accounts`, `/user-management` | RESOLVED | Organization/platform scope, roles, statuses, logistics geography, catalog, project configuration, and account labels are semantic; IDs are advanced/admin detail. |
| System reference/catalog surfaces | INTENTIONALLY_TECHNICAL | Immutable reference codes, versions, provenance, lifecycle evidence, and exact IDs are required governance metadata and are presented in explicit admin/detail context rather than as the primary entity label. |
| Compatibility redirects and wildcard | INTENTIONALLY_TECHNICAL | Redirect parameters and route identities are transport/navigation mechanics, not visible primary UI. |

## Cross-cutting resolution

- Raw status/priority/authority/document/event codes now route through existing semantic label helpers or safe localized fallbacks.
- Human entity names and operational descriptions precede technical IDs; useful IDs are isolated with `bdi` in explicit details.
- Native browser strings such as `Choose Files` and `No file chosen` are replaced by the existing localized file-input component.
- Quantity units use the shared locale-aware unit formatter; normal Persian surfaces no longer lead with raw `pcs`/`ea` symbols.
- Date/time display continues to use existing dual-calendar helpers and preserves stored instants/timezones.
- Standard logistics abbreviations such as ETA/SLA and user-entered/industry codes remain where their code is the meaningful business value.

## Deferred polish

The following are not HIGH primary-UI leakage and do not block UX-008 closure:

- generic library-level accessibility labels in unused/base breadcrumb, pagination, and sidebar primitives are still English until those primitives receive locale-aware props;
- the standalone compatibility Project Tracking route remains coherently English rather than partially translated;
- full translation of developer/debug/test-only surfaces and source-level enum constants is outside the user-facing presentation scope.

`DEFERRED_POLISH_HIGH_COUNT=0`
