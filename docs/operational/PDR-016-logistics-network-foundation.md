# PDR-016 — Logistics Network Foundation

- **Status:** Accepted for bounded Logistics Network governance
- **Accepted:** 2026-08-02
- **Date:** 2026-08-02
- **Decision scope:** Minimum governed structure; no implementation authorization
- **Candidate implementation release:** 1.7.0 or the next valid MINOR after approval
- **Owners:** Product (behavior), Data (reference/master meaning), Architecture (boundaries), Operations (use)
- **Approvals recorded:** Product, Architecture, Operations, Data; Security for organization/isolation boundaries
- **Roadmap:** [PDR-015](PDR-015-forwarder-domain-development-roadmap.md), Layers 1–3
- **Business definitions:** DA-1.0 [FDD-001](FDD-001-forwarder-data-dictionary.md) entries FDD-001-022 through FDD-001-024

## 1. Purpose and authority boundary

Define the minimum governed structure for standardized logistics points used across Projects and OperationalShipments. The design prevents uncontrolled free-text naming while remaining usable at current operational maturity. This acceptance closes D01–D10 and authorizes preparation of a separately controlled bounded implementation Slice; it does not itself implement or deploy schema, migration, API, UI, seed, backfill, report, or dashboard work.

## 2. Core concepts

### LogisticsPointType — Reference Data

A governed classification of a logistics location. The accepted initial concepts are `FACTORY`, `WAREHOUSE`, `DISTRIBUTION_CENTER`, `CUSTOMS`, `PORT`, `BORDER_CROSSING`, `AIRPORT`, `RAIL_TERMINAL`, `ROAD_TERMINAL`, `CUSTOMER_SITE`, and `OTHER_GOVERNED`. `LOADING_SITE`, `UNLOADING_SITE`, and a generic `TERMINAL` are not introduced. Loading and unloading are Project roles, not physical point types.

### LogisticsPoint — Master Data

A reusable real-world named physical/business place, such as “Bandar Abbas — Shahid Rajaee Port”, “Bazargan Customs”, “Aprin Rail Terminal”, “Zamyad Factory”, or “Customer Central Warehouse”. It has governed identity and does not represent a visit or event.

### ProjectLogisticsPoint — Project Configuration

A Project-specific use of a LogisticsPoint: selection, sequence, operational role, optional display label, and active/inactive participation. It references rather than duplicates the LogisticsPoint master record.

## 3. LogisticsPointType policy and taxonomy ambiguities

The recommended Reference Data contract is an immutable code, Persian name, English name, definition, active state, display order, and audit metadata consistent with ADR-021 governance. Types should support cross-industry reporting and the initial release must avoid excessive detail.

| Ambiguity | Options | Recommendation | Reporting impact | Operational impact | Required approvers | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CUSTOMER_SITE vs UNLOADING_SITE | Combine by physical type; keep both; model site type plus project role | Accept `CUSTOMER_SITE`; use `UNLOADING` as Project role | Separates customer-site performance from activity | One site can load or unload by Project | Product, Data, Operations, Architecture | Accepted |
| FACTORY vs LOADING_SITE | Combine; keep both; factory type plus loading role | Accept `FACTORY`; use `LOADING` as Project role | Preserves factory comparisons without conflating activity | Supports returns/unloading at factories | Product, Data, Operations, Architecture | Accepted |
| PORT vs TERMINAL | One generic terminal; distinct mode terminals; PORT plus terminal subtype | Accept `PORT`, `RAIL_TERMINAL`, and `ROAD_TERMINAL`; no generic terminal | Enables mode/type dwell comparison | Avoids a vague catch-all | Product, Data, Operations, Architecture | Accepted |
| BORDER_CROSSING vs CUSTOMS | Combine; keep distinct; one type with role | Accept both as distinct physical/business concepts | Allows border transit versus customs dwell | Project may reference both at one geography | Product, Data, Operations, Architecture | Accepted |
| WAREHOUSE vs DISTRIBUTION_CENTER | Combine; keep distinct; subtype later | Accept both as distinct initial concepts | Supports separate storage and distribution reporting | Operators select the real facility purpose | Product, Data, Operations, Architecture | Accepted |

The authority recorded by this closure accepts these bounded taxonomy resolutions.

## 4. LogisticsPoint master contract

Minimum fields: opaque public identifier; organization scope where applicable; immutable code; Persian name; optional English name; LogisticsPointType; country; optional province/region and city; optional short address; active state; optimistic version; audit timestamps and actors.

Deferred fields: latitude/longitude, timezone, working hours, capacity, ownership, contacts, geofence, and operational restrictions.

Rules:

- no hard delete after use; inactive points remain historically readable;
- code is immutable;
- duplicate prevention considers organization, type, normalized name, and geography;
- no global cross-organization disclosure without explicit authorization;
- aliases may later reuse a governed alias pattern;
- ordinary experts cannot silently create uncontrolled points; and
- unresolved scope, duplicate, or permission fails closed.

## 5. ProjectLogisticsPoint contract

Minimum fields: Project reference, LogisticsPoint reference, sequence/order, project role, optional project-specific display label, active state, optional notes, and audit timestamps/actors.

Recommended initial roles are a bounded enum: `ORIGIN`, `INTERMEDIATE`, `DESTINATION`, `CUSTOMS_PROCESSING`, `TRANSFER`, `STORAGE`, `LOADING`, `UNLOADING`, and `OTHER_GOVERNED`. A bounded enum is simpler than a separately administered taxonomy at current maturity, gives stable reporting keys, and may be superseded by governed Reference Data only when extension evidence exists.

Sequence is Project-specific. One point may have more than one role only if the chosen implementation explicitly supports multiple roles; otherwise the model permits one ProjectLogisticsPoint association per role rather than overloading one association.

Rules:

- a Project may use multiple points of the same type;
- one LogisticsPoint may serve many Projects;
- sequence is Project-specific and does not create a RoutePlan;
- ProjectLogisticsPoint is configuration, not operational evidence;
- removal/deactivation does not rewrite historical operations;
- no forced backfill for existing Projects; and
- no automatic conversion from free-text addresses.

## 6. User experience and free-text policy

Admins manage types and points, activate/deactivate records, resolve duplicates, and approve/create requested points. Experts select existing points for a Project, order them, assign a role, and request a missing point.

Normal flow: select type → filter available points → select point → assign Project role → set sequence → save. Normal Project configuration does not permit unrestricted free-text point creation. A controlled “Request new logistics point” may be added later. At low maturity an admin may create a requested point directly without a complex workflow; where practical, preserve requesting user and creation actor.

## 7. Reporting foundation

- **Point level:** dwell at Bazargan Customs, Projects using Shahid Rajaee Port, delayed OperationalShipments at Aprin Terminal.
- **Type level:** average customs/port/warehouse dwell and active Projects by point type.
- **Project level:** configured network, current shipment position, completed/pending points, route progress.

This structure makes stable point/type dimensions possible. PDR-016 does not authorize dashboards, reports, reporting UI, metric definitions, or automatic inference of position.

## 8. Existing-domain boundaries

| Concept | Boundary |
| --- | --- |
| LogisticsPoint | Reusable physical/business place; may use country/province/city references and may reference a customer where appropriate |
| ProjectLogisticsPoint | Project configuration only |
| RoutePlan | Revisioned operational plan for an OperationalShipment |
| Checkpoint | Operational route element; may later reference a LogisticsPoint through a separate accepted design |
| Milestone | Planned/actual control fact associated with execution, not master data |
| OperationalEvent | Evidence of what occurred; may reference a point but does not define it |
| Province/City | Geographic Reference Data, not a logistics point |
| Customer site | May reference Customer, but is not identical to Customer |
| Cargo visibility | A projection using governed shipment, unit, event, and point facts; not point ownership |

Project, OperationalShipment, RoutePlan, Checkpoint, Milestone, OperationalEvent, geographic Reference Data, Customer, and the three proposed network concepts remain separate aggregates/boundaries. They must not be merged.

## 9. Candidate bounded implementation Slice

After approval, a future bounded Slice may contain only LogisticsPointType, LogisticsPoint, ProjectLogisticsPoint, admin management, Project selection/ordering, organization/security isolation, an additive migration, and tests. Candidate SemVer is **1.7.0** or the next valid MINOR.

Explicit exclusions: GIS, maps, geofencing, ETA, traffic, weather, route optimization, automatic location detection, dashboard/reporting UI, Route Template, automatic RoutePlan generation, customer public point search, bulk import, advanced point approval workflow, and historical backfill.

## 10. Decision register

Evidence common to D01–D10: current free-text/geographic and Project/route models; ADR-017 through ADR-019; ADR-021; PDR-013/PDR-014; the Canonical Catalog; organization-isolation evidence; and PDR-015. The recorded Product, Architecture, Operations, Data, and applicable Security authority accepts all decisions within the bounded scope below.

### D01 — LogisticsPointType scope

- **Options:** broad initial taxonomy; minimal cross-industry taxonomy; unrestricted/custom types.
- **Recommendation:** the eleven accepted concepts in Section 2 with immutable codes; loading/unloading remain roles and generic terminal is excluded.
- **Benefits/Risks:** stable reporting and naming; risk of premature or insufficient categories.
- **UX/Reporting:** filtered bilingual selection and stable type dimensions.
- **Migration/Security:** additive table, no inferred types; admin-only mutation and permitted reads.
- **Approvers:** Product, Data, Operations, Architecture, Security consultation.
- **Fail-safe:** seed only the accepted catalog through separately authorized seed governance; reject unknown type codes.
- **Status:** Accepted.

### D02 — LogisticsPoint master identity and ownership

- **Options:** global shared master; organization-owned only; governed hybrid scope.
- **Recommendation:** opaque identity and immutable scoped code; organization scope by default, with any platform-shared record requiring explicit governance.
- **Benefits/Risks:** reuse and isolation; duplicates across scopes and accidental disclosure require controls.
- **UX/Reporting:** scoped search; reports aggregate only authorized scope.
- **Migration/Security:** additive, no free-text conversion; tenant-first authorization.
- **Approvers:** Product, Data, Architecture, Security, Operations.
- **Fail-safe:** deny access/creation when ownership is ambiguous.
- **Status:** Accepted.

### D03 — ProjectLogisticsPoint relationship

- **Options:** copy point fields into Project; direct many-to-many only; explicit association entity.
- **Recommendation:** explicit association entity referencing one Project and one LogisticsPoint.
- **Benefits/Risks:** preserves master truth and Project-specific data; association lifecycle needs audit.
- **UX/Reporting:** reusable selection and project-network reporting.
- **Migration/Security:** additive, no backfill; validate Project and point organization access.
- **Approvers:** Product, Architecture, Operations, Data, Security.
- **Fail-safe:** reject cross-scope or unresolved references.
- **Status:** Accepted.

### D04 — Sequence and Project role

- **Options:** sequence only; free-text role; bounded enum; governed Reference Data.
- **Recommendation:** integer Project-specific sequence plus bounded enum listed in Section 5.
- **Benefits/Risks:** simplest reportable model; enum extension requires governed change.
- **UX/Reporting:** ordered network and stable role filters; no implied RoutePlan.
- **Migration/Security:** no backfill; normal Project edit permission.
- **Approvers:** Product, Operations, Data, Architecture.
- **Fail-safe:** reject missing/duplicate invalid sequence under the accepted validation policy; do not infer role.
- **Status:** Accepted.

### D05 — Expert creation/request policy

- **Options:** unrestricted creation; admin-only creation; controlled request then admin creation.
- **Recommendation:** experts select/request; admins create and resolve duplicates; simple direct handling initially.
- **Benefits/Risks:** controls duplicates; may add operational delay.
- **UX/Reporting:** request path instead of free text; cleaner dimensions.
- **Migration/Security:** no legacy conversion; explicit admin permission and actor/request provenance.
- **Approvers:** Product, Operations, Security, Data.
- **Fail-safe:** no point creation by ordinary experts.
- **Status:** Accepted.

### D06 — Geographic fields

- **Options:** address only; country/province/city; full GIS coordinates/geofence.
- **Recommendation:** governed country plus optional existing province/city and short address; defer GIS fields.
- **Benefits/Risks:** useful geographic filtering without GIS complexity; incomplete locations remain possible.
- **UX/Reporting:** cascading optional geography; region/city analysis where populated.
- **Migration/Security:** nullable additive references, no inference; avoid address disclosure outside authorized views.
- **Approvers:** Product, Data, Operations, Architecture, Security.
- **Fail-safe:** accept unknown optional subregion without fabricating it.
- **Status:** Accepted.

### D07 — Duplicate prevention

- **Options:** code uniqueness only; normalized-name uniqueness; composite candidate detection plus steward resolution.
- **Recommendation:** immutable scoped code plus candidate detection using organization, type, normalized name, and geography; ambiguous candidates require admin resolution.
- **Benefits/Risks:** fewer duplicates; normalization can produce false positives/negatives.
- **UX/Reporting:** warn/block on candidates; improves stable point counts.
- **Migration/Security:** no automatic merge; candidate results remain scope-filtered.
- **Approvers:** Data, Product, Operations, Security, Architecture.
- **Fail-safe:** block silent merge and require explicit resolution.
- **Status:** Accepted.

### D08 — Historical preservation

- **Options:** hard delete; mutable replacement; deactivate with immutable historical references.
- **Recommendation:** deactivate, never hard-delete after use, and preserve referenced history.
- **Benefits/Risks:** auditable history; inactive records require clear presentation.
- **UX/Reporting:** inactive badge, unavailable for new selection but readable historically.
- **Migration/Security:** additive lifecycle; historical permissions still apply.
- **Approvers:** Product, Data, Operations, Architecture, Security.
- **Fail-safe:** refuse destructive removal when use cannot be disproved.
- **Status:** Accepted.

### D09 — Security and organization isolation

- **Options:** global discovery; client-selected organization filter; backend tenant-first authorization.
- **Recommendation:** backend tenant/resource authorization before lookup, matching, serialization, logs, and reporting.
- **Benefits/Risks:** prevents cross-organization disclosure; shared-point use needs later explicit policy.
- **UX/Reporting:** users see only authorized choices and aggregates.
- **Migration/Security:** scoped indexes/constraints; opaque IDs and deny-by-default.
- **Approvers:** Security, Product, Architecture, Data, Operations.
- **Fail-safe:** deny when organization or resource authorization is unclear.
- **Status:** Accepted.

### D10 — Reporting readiness boundary

- **Options:** structure only; structure plus metrics; immediate dashboards.
- **Recommendation:** structure only; define metrics/reports in a later governed Slice after data-quality evidence.
- **Benefits/Risks:** avoids misleading dashboards; value realization is intentionally later.
- **UX/Reporting:** no dashboard UI now; stable future dimensions only.
- **Migration/Security:** no reporting projection/backfill; future reports inherit tenant and field controls.
- **Approvers:** Product, Data, Operations, Architecture, Security.
- **Fail-safe:** do not publish point KPIs until definitions and evidence are accepted.
- **Status:** Accepted.

## 11. Exact governance gate

Product, Architecture, Operations, Data, and applicable Security authority have accepted D01–D10 and closed the five taxonomy ambiguities. ADR-025 records aggregate boundaries. A bounded Logistics Network implementation Slice is authorized for planning as the next valid MINOR release, but implementation, seed execution, packaging, and deployment require their normal separate controls.
