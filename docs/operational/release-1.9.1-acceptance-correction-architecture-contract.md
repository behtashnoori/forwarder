# Forwarder 1.9.1 Acceptance-Correction Architecture Contract

- **Status:** Accepted architecture; implementation not started
- **Slice:** 1 — architecture, contracts, and governance only
- **Date:** 2026-08-10
- **Source baseline:** commit `60657257ed6a10c16fc6bc86dae1a483ae954fcf`, tree `f880bfdafe13b21280519fd30cff01885e7bb304`
- **Production baseline:** Forwarder 1.9.0, database `20260818_immutable_fx_provenance`
- **Authority:** Future Slices 2–8 only within this contract; no migration, Seed, package, tag, deployment, or Production authority

This contract applies [ADR-034](adr/ADR-034-optional-commercial-lineage-single-operational-shipment.md), preserves ADR-002 through ADR-006 and ADR-010, and reuses the existing `CanonicalLocation` bridge. Where examples contain numeric IDs, they describe internal persistence only; new authenticated APIs use opaque public identities whenever the referenced model exposes one.

## 1. Direct-create API contract

### Command

```http
POST /api/operational-shipments
Authorization: Bearer <credential>
Idempotency-Key: <1..100 characters>
Content-Type: application/json
```

Required permission: `operational_shipment.create_direct` through exactly one active `OperationalMembership` in an active `OperationalOrganization`.

Normative request shape:

```json
{
  "source_type": "direct",
  "customer_id": 481,
  "project_public_id": null,
  "route": {
    "origin": {"source_type": "city", "source_id": 101},
    "destination": {"source_type": "iran_port", "source_id": 45},
    "transport_mode": "road",
    "planned_departure": "2026-08-20T08:00:00+03:30",
    "planned_arrival": "2026-08-21T15:00:00+03:30"
  }
}
```

Until `Customer` has an opaque public identity, `customer_id` is a documented compatibility exception for this internal API. Slice 2 must not invent a public identifier during a migration; a later bounded identity amendment may replace it additively. The backend resolves the customer before any mutation and returns no foreign-customer distinction.

Rules:

- `source_type` must be exactly `direct`; request and quote fields are rejected even when null-like clients attempt to send them ambiguously.
- Customer is required, canonical, and active. The current `Customer` table is not organization-scoped, so selection alone grants no visibility; authorization is through the caller's operational organization and any supplied Project. Cross-organization customer governance remains fail-closed where an organization relationship exists.
- Project is optional. If supplied, it is resolved by `public_id`, belongs to the caller organization, and has the same `primary_customer_id`.
- Route endpoints use the canonical location reference contract below.
- Transport mode is required and uses the existing accepted vocabulary; this slice invents no Iran-specific mode requirement.
- Planned departure and arrival are required timezone-aware instants; arrival is not before departure; endpoints differ.
- Initial shipment state is `planned`. One active RoutePlan revision 1, one RouteLeg, and departure/arrival milestones are created in the same transaction.
- No ShipmentRequest, ExpertQuote, request-scoped document, or case record is created.
- The transaction also records `OperationalIdempotency`, `OperationalAudit`, and `OperationalOutbox`.

Idempotency scope is `(organization_id, create_direct_shipment, idempotency_key)`. Same key and canonical payload replays the original response. Same key with a different payload returns `409`. PostgreSQL advisory locking or an equivalent unique database boundary serializes concurrent attempts.

Created response:

```json
{
  "data": {
    "public_id": "opaque-shipment-id",
    "status": "planned",
    "version": 1,
    "customer": {"id": 481, "display_name": "Canonical CRM label"},
    "project_public_id": null,
    "source": {
      "type": "direct",
      "shipment_request_id": null,
      "accepted_quote_id": null,
      "quote_amount": null
    },
    "route_plan": {"revision": 1, "status": "active"}
  },
  "meta": {"created": true, "replayed": false}
}
```

The outbox event is `operational_shipment.created` with aggregate public identity, organization identity, `source_type`, customer identity, and optional Project identity. It excludes customer contact details and route free text. Audit action uses the same event name plus actor and idempotency/correlation metadata.

Errors:

| Code | HTTP | Meaning |
| --- | ---: | --- |
| `VALIDATION_FAILED` | 422 | Missing/malformed command field |
| `INVALID_OPERATION_SOURCE` | 422 | Unknown or wrong source for endpoint |
| `COMMERCIAL_LINEAGE_NOT_ALLOWED` | 422 | Direct command supplied request/quote lineage |
| `CUSTOMER_REQUIRED` | 422 | Canonical customer absent |
| `CUSTOMER_NOT_ELIGIBLE` | 422 | Customer inactive or not governed for creation |
| `PROJECT_CUSTOMER_MISMATCH` | 422 | Project and shipment customer differ |
| `LOCATION_MAPPING_REQUIRED` | 422 | Endpoint cannot resolve canonically |
| `LOCATION_ANCESTRY_MISMATCH` | 422 | Point/geography relationships conflict |
| `INVALID_ROUTE_TIMELINE` | 422 | Invalid endpoints or schedule |
| `FORBIDDEN_OPERATION` | 403 | Permission absent |
| `TENANT_SCOPE_VIOLATION` | 403 | Active membership is absent or ambiguous |
| `RESOURCE_NOT_FOUND` | 404 | Tenant-scoped resource unavailable; foreign is indistinguishable |
| `IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD` | 409 | Key conflict |

## 2. Accepted-quote compatibility contract

`POST /api/operational-shipments/from-accepted-quote` remains explicit. It requires `operational_shipment.create_from_quote`, locks the accepted quote, validates its organization and accepted state, obtains its ShipmentRequest, and requires `ShipmentRequest.customer_id` for every new conversion.

It creates the same aggregate with `source_type=accepted_quote`, `customer_id=ShipmentRequest.customer_id`, both existing lineage IDs, and an optional validated Project. Quote/request mismatch, missing canonical customer, Project/customer mismatch, or foreign organization fails before mutation. Existing quote uniqueness and idempotent replay remain unchanged. The response is additive: existing fields retain meaning; `source.type` and canonical customer are added. Existing 1.9.0 rows remain readable when classified `legacy_incomplete` because their historical request lacks `customer_id`.

Both source endpoints invoke one internal initializer for route plan, route leg, milestones, audit, outbox, and transaction boundaries. Neither calls the other or creates a second aggregate.

## 3. Downstream capability matrix

| Capability | `accepted_quote` | `direct` | Contract |
| --- | --- | --- | --- |
| Operational lifecycle | SUPPORTED | SUPPORTED | Same states, commands, locking, versioning |
| RoutePlan / RouteLeg / milestones | SUPPORTED | SUPPORTED | Same canonical route and initialization |
| Work queue | SUPPORTED | SUPPORTED | Must not inner-join customer through request |
| Request-scoped documents | SUPPORTED | NOT_APPLICABLE | No fake request/case |
| MDPM request requirements | SUPPORTED | NOT_APPLICABLE | Explicit applicability response |
| Native operation documents | FUTURE_EXTENSION | FUTURE_EXTENSION | ADR-020 seam; no 1.9.1 DMS |
| OIP | SUPPORTED | SUPPORTED | Shipment/route facts do not require request lineage |
| Ordinary economics | SUPPORTED | SUPPORTED | Same governed manual facts |
| Accepted-quote commitment | SOURCE_SPECIFIC | NOT_APPLICABLE | Quote source only |
| FX | SUPPORTED | SUPPORTED | Same immutable provenance for eligible facts |
| Cargo | SUPPORTED | SUPPORTED | Same shipment boundary |
| Project | SUPPORTED optional | SUPPORTED optional | Same-org/customer validation |
| Reporting | SUPPORTED | SUPPORTED | Explicit source dimension and intentional null lineage |
| Audit / outbox | SUPPORTED | SUPPORTED | Same event family with source metadata |

NOT_APPLICABLE APIs return `409 SOURCE_CAPABILITY_NOT_APPLICABLE`; they do not dereference null lineage or imply readiness through a misleading empty success. FUTURE_EXTENSION authorizes no 1.9.1 implementation.

## 4. Six-scenario location contract

| Scenario | UI | Required canonical identity | Derived data | Persistence / legacy |
| --- | --- | --- | --- | --- |
| Domestic origin | Province then existing county/city | existing `origin_province_id`; lower IDs per existing rules | hierarchy from selected city | Existing IDs and behavior; ancestry must agree |
| Domestic destination | Province then existing county/city | existing `dest_province_id`; lower IDs per existing rules | hierarchy from selected city | Existing IDs and behavior |
| International origin non-Iran | Country then international city | new `origin_country_id`, `origin_international_city_id` | country from city FK | New IDs authoritative; legacy labels retained/readable |
| International origin Iran | Iran, mandatory Province, optional lower point | new `origin_country_id`, existing `origin_province_id` | province in snapshot | No name inference; lower requirement is a later mode/context policy |
| International destination non-Iran | Country then international city | new `dest_country_id`, `dest_international_city_id` | country from city FK | New IDs authoritative; legacy labels retained/readable |
| International destination Iran | Iran then one Destination selector | new `dest_country_id` plus exactly one typed existing Iran destination ID | province and optional lower ancestry | No redundant province; invalid ancestry unavailable |

Canonical IDs are authoritative for new writes. Legacy text columns remain historical display snapshots for N/N-1 compatibility. Text is never used to infer an ID. Historical RouteLeg snapshots remain immutable.

## 5. Unified Iran destination selector

```json
{
  "identity": {"type": "customs", "id": 73},
  "display": {
    "fa": "گمرک بازرگان — مرز/گمرک — آذربایجان غربی",
    "en": "Bazargan Customs — Border/Customs — West Azerbaijan"
  },
  "administrative_geography": {
    "country_id": 1,
    "country_code": "IR",
    "province_id": 31,
    "province_label": "آذربایجان غربی"
  }
}
```

Allowed identity types are `city`, `port`, and `customs`; border semantics derive from governed customs type. Commands submit only `{type,id}`. The backend derives and validates Iran and province transactionally.

Eligibility requires an active governed record and one valid province ancestry: `City.province_id`, `IranPort.province_id` consistent with confirmed active location data, or `CustomsOffice.province_id`. Coverage mappings do not replace physical ancestry. Missing, conflicting, provisional, or ambiguous ancestry excludes the point pending master-data remediation.

Duplicate names always show type and province. Province may filter search but is not resubmitted. RTL labels remain RTL while codes/version tokens use isolated LTR spans. Mobile results stack name, type, and province with at least 44 CSS pixel touch targets.

## 6. Persistence and constraint contract

Future Slice 2 may propose one migration; this document creates none.

`operational_shipment` changes:

- add ultimately non-null `source_type varchar(24)` constrained to `accepted_quote|direct`;
- add `customer_id bigint` FK `customer.id ON DELETE RESTRICT`, nullable only for legacy-incomplete quote rows;
- make `shipment_request_id` and `accepted_quote_id` nullable;
- retain optional `project_id`, accepted-quote uniqueness, and existing FKs;
- add `customer_id` and evidence-supported tenant/customer/status indexes.

Source shape check:

```sql
(source_type = 'accepted_quote'
 AND shipment_request_id IS NOT NULL
 AND accepted_quote_id IS NOT NULL)
OR
(source_type = 'direct'
 AND customer_id IS NOT NULL
 AND shipment_request_id IS NULL
 AND accepted_quote_id IS NULL)
```

Customer cannot be globally NOT NULL unless rehearsal proves every historical quote shipment maps deterministically. Service validation requires customer for every new operation.

`shipment_request` gains nullable `origin_country_id`, `origin_international_city_id`, `dest_country_id`, and `dest_international_city_id`, each with `RESTRICT` FK. Reuse existing Iranian province/destination IDs. No generic logistics-location table or duplicate province column is added. Cross-row ancestry, activity/effective dates, Iran province, and destination exclusivity are service validations rather than invalid SQL checks or triggers.

## 7. Proposed migration specification

```text
revision: 20260819_v191_acceptance_corrections
down_revision: 20260818_immutable_fx_provenance
```

Safe order:

1. Assert the expected sole parent.
2. Add nullable source, customer, and international-location columns.
3. Add named FKs and evidence-supported indexes.
4. Backfill all existing operational source values to `accepted_quote`; fail if either lineage ID is absent.
5. Backfill shipment customer only through the exact request `customer_id` FK when non-null.
6. Gate total/source-complete/customer-complete/legacy-incomplete counts; never match text.
7. Make source non-null and remove any temporary default.
8. Drop NOT NULL on lineage columns.
9. Add source-shape check, preferably PostgreSQL `NOT VALID` then validation.
10. Leave legacy location IDs null; no location backfill.
11. Verify constraints, FKs, indexes, counts, and one head.

Risk is source-update WAL plus DDL/validation locks. Rehearsal measures table size, lock wait, duration, WAL, replication impact where applicable, and index behavior. Use bounded lock/statement timeouts and explicit migration execution.

Downgrade fails closed if direct rows exist or populated canonical location IDs would be lost. Before durable writes, it may reverse changes only after proving no null lineage. It never fabricates records. Production rehearsal requires a restored Production-compatible PostgreSQL copy, pre/post counts, invalid-state queries, current=head, N/N-1 checks, lock telemetry, backup/restore, downgrade-guard proof, and security review.

## 8. Permission transition contract

Target permissions are `operational_shipment.create_from_quote` and `operational_shipment.create_direct`.

1. Backend initially accepts `create_from_quote OR operational_shipment.create` only on the existing quote endpoint.
2. Direct creation accepts only `create_direct`; legacy create never implies it.
3. Administrators explicitly assign `create_from_quote` after reviewing existing creators.
4. Observe remaining legacy quote calls.
5. Remove fallback only after clients and memberships transition through a separate gate.

No migration or Seed grants permissions. UI hiding is not authorization. Foreign resources return 404, missing permission 403, and inactive/zero/ambiguous membership 403.

## 9. Release identity contract

The immutable packaged manifest is authoritative. Build gates validate:

```text
approved version -> package.json -> Vite compile-time value
                 -> backend __version__
                 -> builder/tag -> release manifest
```

Authenticated chrome renders `Forwarder 1.9.1` from compile-time identity. A sanitized authenticated `GET /api/system/release-identity` returns only application version, release tag, frontend version, backend version, short commit, and optional admin database revision. The endpoint consumes a verified allowlisted projection of the package manifest, not live Git/filesystem inspection.

Admin/support states are `MATCH`, `MISMATCH`, `BACKEND_UNAVAILABLE`, and `IDENTITY_UNAVAILABLE`. Normal users see only the product version. Package/requirements hashes, Git tree, tag object, paths, environment fingerprint, DB URL, secrets, host/process/runtime/server versions, and unknown manifest fields are excluded.

## 10. Acceptance traceability

| Gap / decision | Contract | Slice | Automated acceptance | Browser UAT | Release gate |
| --- | --- | --- | --- | --- | --- |
| Direct source/no fake commerce | ADR-034; §§1–3 | 2,4,5 | state matrix, no request/quote, idempotency, audit/outbox | source chooser/direct create | cross-flow PASS |
| Canonical customer | ADR-034; §§1,2,6,7 | 2,4 | required/copy/Project mismatch/legacy | selector/display | no fuzzy backfill |
| Optional Project | ADR-034; §§1–2 | 4,5 | null success, foreign/mismatch fail | with/without Project | tenant PASS |
| Documents | §3 | 4,8 | direct not-applicable, quote unchanged | explicit state | DMS regression PASS |
| Split permissions | §8 | 4,5 | fallback/direct denial/membership | permission controls | assignment review |
| Iran origin province | §4 | 3,6 | required canonical province | RTL/mobile | round-trip PASS |
| Unified Iran destination | §§4–5 | 3,6 | three kinds, ancestry, duplicates | one selector | eligibility PASS |
| CanonicalLocation reuse | §§4–6 | 3 | equal snapshots both sources | route display | no second aggregate |
| Version identity | §9 | 7 | match/mismatch/unavailable/allowlist | chrome/admin responsive | artifact identity PASS |
| Safe migration | §§6–7 | 2,8 | clone/constraints/counts/guards | N/A | PostgreSQL/restore PASS |

Implementation-dependent tests are future acceptance tests and must not be committed red in Slice 1.

## 11. Future Slices 2–8 impact inventory

| Slice | Likely files/modules | Impact |
| --- | --- | --- |
| 2 | `backend/operational_models.py`, `backend/models.py`, one migration, model/migration tests | source/customer/location columns and invariants |
| 3 | operational/shipment/location services, `backend/routes/locations.py`, tests | shared resolver, ancestry, selector projection, snapshots |
| 4 | `backend/routes/operations.py`, operational/document/MDPM/economics services, backend/PostgreSQL tests | direct endpoint, shared initializer, null applicability |
| 5 | `src/App.tsx`, authenticated navigation, operations pages/components, `src/lib/api.ts`, i18n/tests | navigation, source chooser, common form |
| 6 | `src/components/LocationForm.tsx`, request API/service/tests | Iran origin and unified destination, legacy UX |
| 7 | version files, system route/service, chrome/admin UI, builder/security tests | identity derivation, allowlist, mismatch |
| 8 | PostgreSQL/UAT runners, assurance docs, verification scripts/runbooks | integrated release gates |

Slice 2 must not implement APIs, UI, release identity, permission assignment, package, deployment, or Production access.

## 12. Slice 1 acceptance and non-goals

Slice 1 is complete when ADR-034 and this contract are consistent, indexed, link-valid, whitespace-clean, and relevant existing tests pass. It intentionally does not modify runtime code, OpenAPI, ORM models, migrations, permissions, reference data, versions, packages, tags, deployment, or Production.
