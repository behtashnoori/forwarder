"""Admin report overview JSON payload builders."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import joinedload

from backend.extensions import db
from backend.models import City, County, ExpertUser, Province, ShipmentRequest

MISSING_FIELD_LABEL = "ثبت نشده"
MISSING_EXPERT_LABEL = "بدون کارشناس"
TIMEZONE_BASIS = "UTC"

STATUS_LABELS_FA = {
    "new": "جدید",
    "assigned": "در انتظار بررسی",
    "in_progress": "در حال بررسی",
    "quoted": "پیشنهاد ارسال‌شده",
    "waiting_for_customer": "منتظر مشتری",
    "won": "پذیرفته‌شده",
    "lost": "ردشده / از دست‌رفته",
    "closed": "مختومه",
}

PERIOD_LABELS_FA = {
    "weekly": "گزارش هفتگی",
    "monthly": "گزارش ماهانه",
    "yearly": "گزارش سالانه",
}

TRANSPORT_LABELS_FA = {
    "road": "جاده‌ای",
    "rail": "ریلی",
    "air": "هوایی",
    "sea": "دریایی",
    "road transport": "حمل جاده‌ای",
    "rail transport": "حمل ریلی",
    "air transport": "حمل هوایی",
    "sea freight": "حمل دریایی",
    "unknown": MISSING_FIELD_LABEL,
}

ACTIVE_STATUSES = {"assigned", "in_progress", "quoted", "waiting_for_customer"}
COMPLETED_STATUSES = {"won", "closed"}
LOST_STATUSES = {"lost"}


class AdminReportOverviewError(Exception):
    """Raised when report overview query parameters are invalid."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class PeriodBounds:
    """UTC period boundaries for report filtering."""

    period: str
    start: datetime
    end: datetime
    now: datetime


def get_report_overview_payload(period: str | None) -> dict[str, Any]:
    """Return admin report overview payload for the requested period."""
    bounds = get_period_bounds(period or "weekly")
    requests = fetch_period_requests(bounds)
    context = build_report_context(requests)

    return {
        "metadata": build_metadata(bounds),
        "summary": build_summary(requests, bounds),
        "requests_by_status": build_requests_by_status(requests),
        "transport_distribution": build_transport_distribution(requests),
        "location_distribution": build_location_distribution(requests, context),
        "expert_performance": build_expert_performance(requests),
        "customer_concentration": build_customer_concentration(requests, context),
        "trends": build_trends(requests, bounds),
        "request_details": build_request_details(requests, context),
    }


def get_period_bounds(period: str) -> PeriodBounds:
    """Return inclusive start and exclusive end UTC boundaries for a supported period."""
    if period not in PERIOD_LABELS_FA:
        raise AdminReportOverviewError("دوره گزارش نامعتبر است", 400)

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)

    if period == "weekly":
        start = today_start - timedelta(days=6)
        end = today_start + timedelta(days=1)
    elif period == "monthly":
        start = datetime(now.year, now.month, 1)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1)
        else:
            end = datetime(now.year, now.month + 1, 1)
    else:
        start = datetime(now.year, 1, 1)
        end = datetime(now.year + 1, 1, 1)

    return PeriodBounds(period=period, start=start, end=end, now=now)


def fetch_period_requests(bounds: PeriodBounds) -> list[ShipmentRequest]:
    """Fetch shipment requests for the selected report period, newest first."""
    return (
        ShipmentRequest.query.options(
            joinedload(ShipmentRequest.assigned_expert),
            joinedload(ShipmentRequest.customer),
        )
        .filter(ShipmentRequest.created_at >= bounds.start)
        .filter(ShipmentRequest.created_at < bounds.end)
        .order_by(ShipmentRequest.created_at.desc(), ShipmentRequest.id.desc())
        .all()
    )


def build_report_context(requests: list[ShipmentRequest]) -> dict[str, dict[int, str]]:
    """Build lookup dictionaries for domestic location names."""
    province_ids = {
        location_id
        for request in requests
        for location_id in (request.origin_province_id, request.dest_province_id)
        if location_id
    }
    county_ids = {
        location_id
        for request in requests
        for location_id in (request.origin_county_id, request.dest_county_id)
        if location_id
    }
    city_ids = {
        location_id
        for request in requests
        for location_id in (request.origin_city_id, request.dest_city_id)
        if location_id
    }

    provinces = Province.query.filter(Province.id.in_(province_ids)).all() if province_ids else []
    counties = County.query.filter(County.id.in_(county_ids)).all() if county_ids else []
    cities = City.query.filter(City.id.in_(city_ids)).all() if city_ids else []

    return {
        "provinces": {province.id: province.name_fa for province in provinces},
        "counties": {county.id: county.name_fa for county in counties},
        "cities": {city.id: city.name_fa for city in cities},
    }


def build_metadata(bounds: PeriodBounds) -> dict[str, Any]:
    """Build report metadata."""
    return {
        "period": bounds.period,
        "period_label_fa": PERIOD_LABELS_FA[bounds.period],
        "start_date": bounds.start.isoformat(),
        "end_date": bounds.end.isoformat(),
        "generated_at": bounds.now.isoformat(),
        "timezone_basis": TIMEZONE_BASIS,
    }


def build_summary(requests: list[ShipmentRequest], bounds: PeriodBounds) -> dict[str, int]:
    """Build top-level report counters for the selected period."""
    statuses = Counter(request.status for request in requests)
    last_24h_start = bounds.now - timedelta(hours=24)
    last_7d_start = bounds.now - timedelta(days=7)

    return {
        "total_requests": len(requests),
        "new_requests": statuses["new"],
        "pending_review_requests": statuses["assigned"],
        "in_progress_requests": statuses["in_progress"],
        "completed_requests": sum(statuses[status] for status in COMPLETED_STATUSES),
        "lost_or_rejected_requests": sum(statuses[status] for status in LOST_STATUSES),
        "unassigned_requests": sum(1 for request in requests if request.assigned_to is None),
        "requests_last_24h": sum(1 for request in requests if request.created_at and request.created_at >= last_24h_start),
        "requests_last_7d": sum(1 for request in requests if request.created_at and request.created_at >= last_7d_start),
    }


def build_requests_by_status(requests: list[ShipmentRequest]) -> list[dict[str, Any]]:
    """Build request counts grouped by canonical request status."""
    total = len(requests)
    grouped: dict[str, list[ShipmentRequest]] = defaultdict(list)
    for request in requests:
        grouped[request.status].append(request)

    return [
        {
            "status": status,
            "label_fa": status_label(status),
            "count": len(items),
            "percent_of_total": percent(len(items), total),
            "latest_created_at": iso_or_none(max(item.created_at for item in items if item.created_at)),
        }
        for status, items in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    ]


def build_transport_distribution(requests: list[ShipmentRequest]) -> list[dict[str, Any]]:
    """Build request counts grouped by coalesced transport method."""
    total = len(requests)
    grouped: dict[str, list[ShipmentRequest]] = defaultdict(list)
    for request in requests:
        grouped[coalesced_transport_method(request)].append(request)

    return [
        {
            "transport_method": method,
            "label_fa": transport_label(method),
            "count": len(items),
            "percent_of_total": percent(len(items), total),
            "completed_count": sum(1 for item in items if item.status in COMPLETED_STATUSES),
            "in_progress_count": sum(1 for item in items if item.status == "in_progress"),
        }
        for method, items in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    ]


def build_location_distribution(
    requests: list[ShipmentRequest],
    context: dict[str, dict[int, str]],
) -> list[dict[str, Any]]:
    """Build origin and destination distribution rows."""
    total = len(requests)
    grouped: dict[tuple[str, str, str, str], list[ShipmentRequest]] = defaultdict(list)

    for request in requests:
        origin = location_tuple(request, "origin", context)
        destination = location_tuple(request, "destination", context)
        grouped[("origin", *origin)].append(request)
        grouped[("destination", *destination)].append(request)

    rows = []
    for (location_type, province, county, city), items in grouped.items():
        rows.append(
            {
                "location_type": location_type,
                "location_type_label_fa": "مبدا" if location_type == "origin" else "مقصد",
                "province": province,
                "county": county,
                "city": city,
                "count": len(items),
                "percent_of_total": percent(len(items), total),
                "top_transport_method": top_value(coalesced_transport_method(item) for item in items),
            }
        )

    return sorted(rows, key=lambda row: (-row["count"], row["location_type"], row["province"], row["county"], row["city"]))


def build_expert_performance(requests: list[ShipmentRequest]) -> list[dict[str, Any]]:
    """Build per-expert status counters without SLA or priority metrics."""
    grouped: dict[int | None, list[ShipmentRequest]] = defaultdict(list)
    for request in requests:
        grouped[request.assigned_to].append(request)

    rows = []
    for expert_id, items in grouped.items():
        expert = items[0].assigned_expert if expert_id else None
        completed_count = sum(1 for item in items if item.status in COMPLETED_STATUSES)
        rows.append(
            {
                "expert_id": expert.id if expert else None,
                "expert_name": expert.full_name if expert else MISSING_EXPERT_LABEL,
                "username": expert.username if expert else MISSING_FIELD_LABEL,
                "role": expert.role if expert else MISSING_FIELD_LABEL,
                "assigned_count": len(items),
                "active_count": sum(1 for item in items if item.status in ACTIVE_STATUSES),
                "completed_count": completed_count,
                "lost_or_rejected_count": sum(1 for item in items if item.status in LOST_STATUSES),
                "completion_rate": percent(completed_count, len(items)),
            }
        )

    return sorted(rows, key=lambda row: (-row["assigned_count"], row["expert_name"]))


def build_customer_concentration(
    requests: list[ShipmentRequest],
    context: dict[str, dict[int, str]],
) -> list[dict[str, Any]]:
    """Build request counts grouped by customer identity."""
    grouped: dict[tuple[str, str, str], list[ShipmentRequest]] = defaultdict(list)
    for request in requests:
        name = customer_name(request)
        phone = value_or_missing(request.contact_phone)
        company = company_name(request)
        grouped[(name, phone, company)].append(request)

    rows = []
    for (name, phone, company), items in grouped.items():
        newest = max(items, key=lambda item: item.created_at or datetime.min)
        rows.append(
            {
                "customer_name": name,
                "phone": phone,
                "company": company,
                "request_count": len(items),
                "latest_request_date": iso_or_none(newest.created_at),
                "latest_request_status": newest.status,
                "latest_request_status_label_fa": status_label(newest.status),
                "dominant_transport_method": top_value(coalesced_transport_method(item) for item in items),
                "dominant_origin": top_value(location_display(item, "origin", context) for item in items),
                "dominant_destination": top_value(location_display(item, "destination", context) for item in items),
            }
        )

    return sorted(rows, key=lambda row: (-row["request_count"], row["customer_name"], row["phone"]))


def build_trends(requests: list[ShipmentRequest], bounds: PeriodBounds) -> list[dict[str, Any]]:
    """Build daily or monthly trend buckets for the selected period."""
    counts: Counter[str] = Counter()

    if bounds.period == "yearly":
        cursor = datetime(bounds.start.year, 1, 1)
        while cursor < bounds.end:
            counts[cursor.strftime("%Y-%m")] = 0
            if cursor.month == 12:
                cursor = datetime(cursor.year + 1, 1, 1)
            else:
                cursor = datetime(cursor.year, cursor.month + 1, 1)
        for request in requests:
            if request.created_at:
                counts[request.created_at.strftime("%Y-%m")] += 1
    else:
        cursor = bounds.start
        while cursor < bounds.end:
            counts[cursor.strftime("%Y-%m-%d")] = 0
            cursor += timedelta(days=1)
        for request in requests:
            if request.created_at:
                counts[request.created_at.strftime("%Y-%m-%d")] += 1

    return [
        {
            "bucket": bucket,
            "label": bucket,
            "request_count": counts[bucket],
        }
        for bucket in sorted(counts)
    ]


def build_request_details(
    requests: list[ShipmentRequest],
    context: dict[str, dict[int, str]],
) -> list[dict[str, Any]]:
    """Build newest-first request detail rows for the report."""
    rows = []
    for request in requests:
        origin = location_parts(request, "origin", context)
        destination = location_parts(request, "destination", context)
        rows.append(
            {
                "id": request.id,
                "tracking_number": request.tracking_code or f"SR{request.id:06d}",
                "created_at": iso_or_none(request.created_at),
                "status": request.status,
                "status_label_fa": status_label(request.status),
                "customer_name": customer_name(request),
                "phone": value_or_missing(request.contact_phone),
                "transport_method": coalesced_transport_method(request),
                "origin_province": origin["province"],
                "origin_county": origin["county"],
                "origin_city": origin["city"],
                "destination_province": destination["province"],
                "destination_county": destination["county"],
                "destination_city": destination["city"],
                "expert_name": request.assigned_expert.full_name if request.assigned_expert else MISSING_EXPERT_LABEL,
                "cargo_description": value_or_missing(request.cargo_description),
                "weight": request.cargo_weight,
                "volume": request.cargo_volume,
                "cargo_value": request.cargo_value,
                "pickup_date": request.pickup_date.isoformat() if request.pickup_date else None,
                "delivery_date": request.delivery_date.isoformat() if request.delivery_date else None,
                "has_unread_for_assignee": bool(request.has_unread_for_assignee),
            }
        )
    return rows


def status_label(status: str | None) -> str:
    return STATUS_LABELS_FA.get(status or "", status or MISSING_FIELD_LABEL)


def transport_label(method: str) -> str:
    return TRANSPORT_LABELS_FA.get(method, method if method != "unknown" else MISSING_FIELD_LABEL)


def coalesced_transport_method(request: ShipmentRequest) -> str:
    for value in (
        request.domestic_transport_method,
        request.international_transport_method,
        request.transport_method,
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def location_parts(
    request: ShipmentRequest,
    location_type: str,
    context: dict[str, dict[int, str]],
) -> dict[str, str]:
    if location_type == "origin":
        if request.shipping_type == "international":
            return {
                "province": value_or_missing(request.origin_country),
                "county": MISSING_FIELD_LABEL,
                "city": value_or_missing(request.origin_city_international),
            }
        return {
            "province": context["provinces"].get(request.origin_province_id, MISSING_FIELD_LABEL),
            "county": context["counties"].get(request.origin_county_id, MISSING_FIELD_LABEL),
            "city": context["cities"].get(request.origin_city_id, MISSING_FIELD_LABEL),
        }

    if request.shipping_type == "international":
        return {
            "province": value_or_missing(request.dest_country),
            "county": MISSING_FIELD_LABEL,
            "city": value_or_missing(request.dest_city_international),
        }
    return {
        "province": context["provinces"].get(request.dest_province_id, MISSING_FIELD_LABEL),
        "county": context["counties"].get(request.dest_county_id, MISSING_FIELD_LABEL),
        "city": context["cities"].get(request.dest_city_id, MISSING_FIELD_LABEL),
    }


def location_tuple(
    request: ShipmentRequest,
    location_type: str,
    context: dict[str, dict[int, str]],
) -> tuple[str, str, str]:
    parts = location_parts(request, location_type, context)
    return parts["province"], parts["county"], parts["city"]


def location_display(
    request: ShipmentRequest,
    location_type: str,
    context: dict[str, dict[int, str]],
) -> str:
    parts = location_parts(request, location_type, context)
    values = [parts["province"], parts["county"], parts["city"]]
    present = [value for value in values if value != MISSING_FIELD_LABEL]
    return "، ".join(present) if present else MISSING_FIELD_LABEL


def customer_name(request: ShipmentRequest) -> str:
    name = f"{request.customer_first_name or ''} {request.customer_last_name or ''}".strip()
    if name:
        return name
    if request.customer:
        crm_name = f"{request.customer.first_name or ''} {request.customer.last_name or ''}".strip()
        if crm_name:
            return crm_name
    return MISSING_FIELD_LABEL


def company_name(request: ShipmentRequest) -> str:
    if request.customer and request.customer.company_name:
        return request.customer.company_name
    return MISSING_FIELD_LABEL


def value_or_missing(value: Any) -> str:
    if value is None:
        return MISSING_FIELD_LABEL
    if isinstance(value, str) and not value.strip():
        return MISSING_FIELD_LABEL
    return str(value)


def top_value(values) -> str:
    counter = Counter(values)
    if not counter:
        return MISSING_FIELD_LABEL
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]


def percent(count: int, total: int) -> float:
    return round((count / total * 100), 2) if total else 0.0


def iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
