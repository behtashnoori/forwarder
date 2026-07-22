# Phase 0 API Contract Draft

این سند design-only است و endpoint اجرایی ایجاد نمی‌کند. namespace پیشنهادی `/api/v1/operations` است.

## قواعد عمومی

- JSON UTF-8، زمان UTC ISO-8601؛
- `Authorization`, `X-Correlation-Id`؛
- `Idempotency-Key` برای create/convert/event/transition؛
- `If-Match` یا `expected_version` برای mutation aggregate؛
- cursor pagination و allowlist filter/sort؛
- شناسه عمومی غیرقابل حدس؛
- error envelope پایدار و OpenAPI-first.

## Resourceها و endpointهای پیشنهادی

| Method | Path | هدف | Permission |
|---|---|---|---|
| POST | `/shipments:convert-from-quote` | conversion idempotent | shipment.convert |
| GET | `/shipments/{id}` | detail projection | shipment.read |
| GET | `/shipments` | query/pagination | shipment.read |
| POST | `/shipments/{id}:submit-booking` | transition | shipment.transition |
| POST | `/shipments/{id}:start` | start execution | shipment.transition |
| POST | `/shipments/{id}:hold` | hold with reason | shipment.transition |
| POST | `/shipments/{id}:resume` | resume | shipment.transition |
| POST | `/shipments/{id}:complete` | completion gate | shipment.complete |
| POST | `/shipments/{id}/route-plans` | draft plan | route_plan.write |
| POST | `/route-plans/{id}:publish` | immutable baseline/revision | route_plan.publish |
| POST | `/milestones/{id}/events` | submit MilestoneEvent | milestone_event.submit |
| POST | `/milestone-events/{id}:verify` | verify evidence | milestone_event.verify |
| POST | `/exceptions/{id}:acknowledge` | exception transition | exception.manage |
| POST | `/work-items/{id}:claim` | work queue action | work_item.claim |
| GET | `/control-tower/work-items` | ranked queue | work_item.read |

## Conversion request

```json
{
  "shipment_request_id": "123",
  "accepted_quote_id": "456",
  "conversion_revision": 1,
  "owner_team_id": "ops-tehran",
  "service_level": "standard"
}
```

Response `201` در اولین اجرا و replay همان semantic response در تکرار همان key. payload متفاوت با key یکسان: `409 IDEMPOTENCY_KEY_REUSED`.

## OperationalShipment projection

```json
{
  "id": "ops_...",
  "version": 3,
  "lifecycle_status": "planned",
  "source": {"shipment_request_id": "123", "accepted_quote_id": "456"},
  "owner": {"team_id": "ops-tehran", "user_id": null},
  "active_route_plan": {"id": "rp_...", "revision": 1},
  "attention": {"open_work_items": 0, "data_freshness": "unknown"}
}
```

## RouteLeg draft

هر leg شامل sequence، mode، `from_location` و `to_location` با `canonical_location_id` و snapshot، provider اختیاری، planned departure/arrival و milestone definitions است. API master location را resolve می‌کند؛ client اجازه ساخت snapshot ناسازگار ندارد.

## MilestoneEvent contract

```json
{
  "event_type": "reported_actual",
  "occurred_at": "2026-08-01T08:30:00Z",
  "source": "manual_operator",
  "external_event_id": null,
  "location": {"canonical_location_id": "loc_..."},
  "evidence": [{"type": "operator_note", "reference": "..."}],
  "note": "arrival confirmed"
}
```

server `recorded_at`, actor، snapshot و verification state را تعیین می‌کند. correction با `event_type=correction` و `supersedes_event_id` است.

## Error envelope

```json
{
  "error": {
    "code": "TRANSITION_GUARD_FAILED",
    "message": "Required milestones are not verified.",
    "fields": [],
    "correlation_id": "...",
    "details": {"guard": "required_milestones_verified"}
  }
}
```

کدهای پایه: `VALIDATION_FAILED` (422)، `OPERATION_FORBIDDEN` (403)، `RESOURCE_NOT_FOUND` (404)، `INVALID_STATE_TRANSITION` (409)، `OPERATION_VERSION_CONFLICT` (409)، `IDEMPOTENCY_KEY_REUSED` (409)، `DUPLICATE_SOURCE_IDENTITY` (409).

## Public tracking boundary

public API از projection جدا و allowlisted استفاده می‌کند: status summary، milestone customer-visible، location display، event time و customer message. actor id، internal note، raw evidence، cost، policy decision و exception investigation ممنوع‌اند.

## Compatibility

APIهای فعلی Request/Quote بدون breaking change می‌مانند. هیچ endpoint جدیدی `ShipmentRequest.status` را با status عملیات update نمی‌کند. واژه `ShipmentJob` در path/schema ممنوع است.

## موارد نیازمند تأیید

versioning strategy نهایی، pagination limits، public identifier format، retention idempotency record، error localization، partner webhook signature و rate limits.
