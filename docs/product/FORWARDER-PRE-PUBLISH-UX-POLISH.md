# Forwarder Pre-Publish UX Polish

- Review date: 2026-08-21
- Initial baseline: `552541cc6bca187784f7d25469c8b91087d549a4`
- Scope: bounded terminology, Persian localization, RTL/LTR, first-use guidance, states, and accessibility
- Feature freeze: **RESPECTED**
- Architecture change / new ADR / backend / API / migration: **NONE**

## Architecture gate

The architecture baseline, development gate, review checklist, ADR index, ADR-035/036/038/039/040, terminology guide, E2E readiness and gap register, and tracking authority/projection documents were reviewed. Changes are presentation-only. Canonical ownership, tenant authority, document/cargo ownership, assignment semantics, tracking write/read authority, public tracking, CRM, and temporal contracts are unchanged.

## Review matrix

| Screen | Primary user/task | Finding | Severity | Action |
| --- | --- | --- | --- | --- |
| Dashboard / navigation | Expert; enter active work | Navigation is consistent; release identity remains secondary | — | Reviewed |
| Requests / detail | Expert; commercial intake and hand-off | Governed request/operation separation is already visible | — | Reviewed |
| Operational Shipments | Expert; find execution aggregate | Raw English filter keys, weak no-results state, unsafe identifier direction | P2 | Implemented |
| Shipment detail | Expert; inspect end-to-end execution | Several deep route/economics phrases remain English | P3 | Backlog; broad translation would exceed bounded pass |
| Projects / Execution Units | Expert; manage independent execution | Preferred «بخش اجرایی حمل» and localized statuses are present | — | Reviewed |
| Legacy request tracking | Expert; update trackable segments | Preferred «بخش قابل رهگیری حمل» is preserved; no authority convergence claimed | — | Reviewed |
| Cargo Catalog | Org Admin / expert; reuse and trace cargo master | Master vs shipment line and incompatible-UOM behavior needed stronger first-use copy; controls mixed languages; location states raw | P2 | Implemented |
| Shipment Cargo | Expert; record shipment snapshot/quantity | Catalog line distinction is visible; some bilingual controls remain | P3 | Backlog |
| Logistics Network | Org Admin; maintain reusable places | First-use copy implied reuse but did not explicitly deny route/shipment creation; primary controls were English | P2 | Implemented |
| Project logistics configuration | Org Admin; select existing points | Correctly avoids automatic route/checkpoint creation | — | Reviewed |
| Shipment Documents | Expert; satisfy shipment requirements | Type/requirement/file/assessment separation is clear; upload is not approval | — | Reviewed |
| Organization document policy | Org Admin; configure tenant policy | Platform vocabulary vs organization policy is explicit | — | Reviewed |
| External References | Expert; manage B/L, AWB, CMR | “Reference” copy was architecture-flavored; loading and first-use explanation weak | P2 | Implemented |
| Workload / assignment | Org Admin; understand responsibility | Governed assigned + in-progress explanation and round-robin distinction are present | — | Reviewed |
| Master/project configuration | Org Admin; select governed types | Generic controls are locale-sensitive and remain mixed in the existing compatibility component | P3 | Backlog |
| Platform catalog surfaces touched by recent work | Platform Admin; govern vocabulary | Platform/organization authority distinction preserved | — | Reviewed only |

## Terminology decisions

- `ShipmentRequest`: «درخواست حمل»; commercial intent, not execution.
- `OperationalShipment`: «محموله عملیاتی».
- Canonical `ExecutionUnit`: «بخش اجرایی حمل».
- Legacy trackable segment: «بخش قابل رهگیری حمل»; no copy-based convergence.
- `CargoCatalogItem`: «کالای استاندارد»; `ShipmentCargoItem`: «قلم محموله».
- `LogisticsPoint`: «مکان لجستیکی سازمان»; reported location is «موقعیت فعلی/ثبت‌شده».
- Documents retain «نوع سند» / «الزام سند» / «فایل بارگذاری‌شده» / «وضعیت بررسی».
- External V1 scope is only B/L, AWB, and CMR, presented as shipment operational reference numbers.
- «بار کاری فعلی» remains assigned + in-progress cases and does not describe default round-robin selection.

## Tracking location presentation

| Projection value | Persian presentation |
| --- | --- |
| `UNAVAILABLE` | موقعیت فعلی ثبت نشده است |
| `SINGLE` | موقعیت فعلی |
| `COMMON` | موقعیت مشترک بخش‌های حمل |
| `MULTIPLE` | محموله در چند موقعیت قرار دارد |

`MULTIPLE` never fabricates a single location. Legacy/canonical/fallback governance terms are not exposed as user guidance.

## Implemented polish

- Localized shipment filter names, paging accessibility names, and no-results guidance.
- Added LTR isolation for project/request identities, cargo codes, English names, UOM/quantity, timestamps, and logistics codes.
- Rewrote Cargo Catalog first-use copy to explain reusable organization master data, shipment-line snapshots, no shipment creation, traceability, and incompatible UOMs.
- Localized Cargo Catalog field/action/status labels and ADR-040 location-state presentation.
- Rewrote Logistics Network first-use copy and localized organization-facing creation/search/lifecycle controls.
- Clarified external references as B/L/AWB/CMR operational numbers and distinguished them from document type, requirement, file, and approval; added a loading state.
- Improved accessible link/button names and status regions in changed surfaces.

## Findings and disposition

| Severity | Count | Implemented | Deferred |
| --- | ---: | ---: | ---: |
| P0 | 0 | 0 | 0 |
| P1 | 0 | 0 | 0 |
| P2 | 5 | 5 | 0 |
| P3 | 6 | 0 | 6 |
| **Total** | **11** | **5** | **6** |

No unresolved release-blocking issue was found.

## POST-PUBLISH BACKLOG

- ADR-040 phases 3–6, only through their controlled lineage/cohort/privacy/write-authority gates.
- Full localization of deep route reconciliation, checkpoint, exception, economics, and audit terminology.
- Remaining bilingual cargo-line and platform-admin catalog controls.
- CRM expansion/remediation (**ON HOLD — NO EXPANSION in this goal**).
- Cotage, Warehouse Receipt, Registration Order, and Barfarabaran reference types.
- Numeric compatibility contraction after consumer and tenant-certification evidence.
- Advanced analytics and optional UI enhancements.

## Scenario verification

The governed gearbox scenario was traced conceptually through Request → Project → Operational Shipment → Cargo → Execution Unit / Tracking → Logistics location → Documents → External Reference → current status/location. Each transition has an existing navigation or bounded empty-state instruction. Cargo quantities remain per-line/per-UOM, documents remain independently materialized per shipment while files stay request-owned, and shipment location uses ADR-040 aggregation without selecting one unit as the whole shipment.

## Explicit exclusions

No Production or Production database access, deployment, push, release, CRM expansion, public-tracking change, tracking-authority change, API change, backend change, domain change, or migration occurred.
