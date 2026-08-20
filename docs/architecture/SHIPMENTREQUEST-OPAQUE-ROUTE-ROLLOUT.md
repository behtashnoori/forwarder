# ShipmentRequest Opaque Route Rollout

- Status: implemented and locally certified
- Authority: ADR-038; ADR-037 is future request-parent context only
- Schema migration: none
- Architecture deviations: none

## Canonical identity and authorization

`ShipmentRequest.public_id` is the canonical authenticated routing identity. It is an immutable canonical UUID v4 and grants no authority. `ShipmentRequest.id` remains the database primary/foreign-key identity and a temporary compatibility identity. `tracking_code` remains the separate public/customer tracking identity and is never accepted as an opaque authenticated parent.

Opaque expert and document routes authenticate first, derive one trusted active tenant context, call `resolve_tenant_request_by_public_id`, and then execute the existing action-specific authorization. The resolver rejects malformed/non-v4/noncanonical, foreign-tenant, non-tenant, missing, and quarantined identities without broadening scope. Body/query organization identifiers do not select tenant authority.

## Census and classification

The repository census covered 33 authenticated request-facing route contracts plus public tracking and internal foreign-key use.

| Surface | Logical contracts | Classification | Result |
| --- | ---: | --- | --- |
| Expert list | 1 | MIGRATE_NOW | emits `public_id`; frontend uses it |
| Expert request-parent routes | 13 | MIGRATE_NOW | opaque canonical aliases added |
| Request document routes | 7 | MIGRATE_NOW | opaque canonical aliases added |
| Operational-shipment request filter | 1 | MIGRATE_NOW | `request_public_id` added and used |
| Intake acceptance | 1 | LEGACY_COMPATIBILITY | numeric platform/intake workflow retained |
| Admin request list/detail/assignment/routing | 5 | LEGACY_COMPATIBILITY | numeric administrative compatibility retained |
| CRM request link/create routes | 5 | LEGACY_COMPATIBILITY | numeric existing-role compatibility retained; no CRM expansion |
| Database/service FKs, joins, logs, notifications | internal use | INTERNAL_ONLY | numeric identity retained |
| Public tracking and quote response | public surface | PUBLIC_TRACKING | `tracking_code` unchanged |
| Requiring a new ADR | 0 | ARCHITECTURE_DECISION_REQUIRED | none |

## Migrated route inventory

For each route below, the existing `<int:request_id>` or `<int:case_id>` form remains as an authorized compatibility alias. The canonical form uses the same path shape with an opaque UUID parent.

| Method | Canonical authenticated route |
| --- | --- |
| GET | `/api/expert/requests/{request_public_id}` |
| POST | `/api/expert/requests/{request_public_id}/assign-to-me` |
| POST | `/api/expert/requests/{request_public_id}/assign` |
| POST | `/api/expert/requests/{request_public_id}/status` |
| POST | `/api/expert/requests/{request_public_id}/quote` |
| GET | `/api/expert/requests/{request_public_id}/quote/latest` |
| POST | `/api/expert/requests/{request_public_id}/messages` |
| POST | `/api/expert/requests/{request_public_id}/mark-read` |
| GET/POST | `/api/expert/requests/{request_public_id}/tracking[/enable]` |
| POST | `/api/expert/requests/{request_public_id}/tracking/units` |
| PATCH | `/api/expert/requests/{request_public_id}/tracking/units/{unit_id}` |
| POST | `/api/expert/requests/{request_public_id}/tracking/units/{unit_id}/updates` |
| GET/POST | `/api/expert/requests/{request_public_id}/documents[/initialize]` |
| POST | `/api/expert/requests/{request_public_id}/document-requirements/{requirement_id}/files` |
| POST | `/api/expert/requests/{request_public_id}/document-requirements/{requirement_id}/replace` |
| POST | `/api/expert/requests/{request_public_id}/documents/miscellaneous` |
| GET/DELETE | `/api/expert/requests/{request_public_id}/documents/{file_id}[/download]` |
| GET | `/api/operational-shipments?request_public_id={request_public_id}` |

## Frontend and response rollout

Expert list-to-detail navigation, detail mutations, tracking, documents, quote, message, shipment-to-request, document-readiness-to-request, and external-reference document lookup now use `public_id`. Request list and detail payloads add `public_id` without removing the numeric compatibility field. Operational shipment source projections add `request_public_id`; numeric `shipment_request_id` remains temporarily for old consumers and internal compatibility but is no longer used for migrated request navigation.

Opaque UUIDs are not displayed as business labels. Refresh, direct deep links, browser history, and return-to-request navigation retain the opaque URL. Public tracking continues to use only `tracking_code`.

## Compatibility and deprecation conditions

Numeric expert/document routes remain tenant- and action-authorized and receive no weaker policy than opaque routes. Admin, intake, CRM, customer-workflow, payload FKs, audit/log, quote, notification, and relational IDs remain compatibility or internal debt. No route was removed.

Future contraction requires caller telemetry or an equivalent repository convention, a complete caller census showing zero supported numeric clients, authorization-parity regression evidence, bookmark/rollback evidence, and separate governance authorization. CRM route conversion should be a separately controlled tenant-certification goal; it must not be inferred from this rollout.

## Certification summary

Focused tests cover valid opaque detail/tracking, malformed identity, tracking-code substitution, same-tenant unauthorized access, numeric compatibility, tenant-fenced resolution, UUID immutability, and document authorization. The full regression record is captured in the implementation commit/report. No timestamp, aggregate ownership, tenant authority, public tracking, CRM authority, schema, or migration semantics changed.
