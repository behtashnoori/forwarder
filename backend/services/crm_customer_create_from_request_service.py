"""Preview helpers for creating CRM customers from shipment requests.

This module is intentionally read-only. It must not create CRM customers,
link shipment requests, write audit rows, or mutate request lifecycle data.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_

from backend.extensions import db
from backend.models import Customer, ShipmentRequest
from backend.services.crm_customer_link_service import build_customer_summary


class CrmCustomerCreatePreviewError(Exception):
    """Base preview exception with an HTTP status code."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CrmCustomerCreatePreviewNotFoundError(CrmCustomerCreatePreviewError):
    """Raised when the target shipment request is missing."""


def _clean_text(value: Any) -> str | None:
    """Return a trimmed string, or None when the value has no useful text."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_suggested_customer_fields(shipment_request: ShipmentRequest) -> dict[str, Any]:
    """Build safe, editable CRM Customer field suggestions from a request."""
    first_name = _clean_text(shipment_request.customer_first_name)
    last_name = _clean_text(shipment_request.customer_last_name)
    phone = _clean_text(shipment_request.contact_phone)

    country = _clean_text(shipment_request.dest_country) or _clean_text(
        shipment_request.origin_country
    )
    city = _clean_text(shipment_request.dest_city_international) or _clean_text(
        shipment_request.origin_city_international
    )

    return {
        "first_name": first_name,
        "last_name": last_name,
        "company_name": None,
        "email": None,
        "phone": phone,
        "mobile": None,
        "customer_type": "prospect",
        "status": "active",
        "source": "shipment_request",
        "notes": f"Previewed from shipment_request_id={shipment_request.id}",
        "city": city,
        "province": None,
        "country": country or "Iran",
    }


def get_missing_fields(suggested_fields: dict[str, Any]) -> dict[str, list[str]]:
    """Return required and optional CRM fields missing from the preview."""
    required = [
        field for field in ("first_name", "last_name") if not suggested_fields.get(field)
    ]
    recommended = [
        field
        for field in ("company_name", "email", "mobile")
        if not suggested_fields.get(field)
    ]
    return {"required": required, "recommended": recommended}


def _candidate_match_metadata(
    customer: Customer,
    suggested_fields: dict[str, Any],
) -> dict[str, Any]:
    """Describe why a CRM customer is a possible duplicate."""
    reasons: list[str] = []
    score = 0
    phone = suggested_fields.get("phone")
    first_name = suggested_fields.get("first_name")
    last_name = suggested_fields.get("last_name")

    if phone and phone in {customer.phone, customer.mobile}:
        reasons.append("phone_or_mobile_exact")
        score += 100
    if first_name and first_name == customer.first_name:
        reasons.append("first_name_exact")
        score += 10
    if last_name and last_name == customer.last_name:
        reasons.append("last_name_exact")
        score += 10

    if score >= 100:
        strength = "strong"
    elif score >= 20:
        strength = "weak"
    else:
        strength = "possible"

    return {
        "match_strength": strength,
        "match_score": score,
        "match_reasons": reasons,
    }


def find_duplicate_candidates(
    suggested_fields: dict[str, Any],
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return advisory duplicate candidates without choosing a match."""
    phone = suggested_fields.get("phone")
    first_name = suggested_fields.get("first_name")
    last_name = suggested_fields.get("last_name")

    conditions = []
    if phone:
        conditions.append(Customer.phone == phone)
        conditions.append(Customer.mobile == phone)
    if first_name and last_name:
        conditions.append(
            (Customer.first_name == first_name) & (Customer.last_name == last_name)
        )

    if not conditions:
        return []

    customers = (
        db.session.query(Customer)
        .filter(or_(*conditions))
        .order_by(Customer.id.asc())
        .limit(limit)
        .all()
    )

    candidates = []
    for customer in customers:
        summary = build_customer_summary(customer)
        summary.update(_candidate_match_metadata(customer, suggested_fields))
        candidates.append(summary)

    return sorted(
        candidates,
        key=lambda candidate: (-candidate["match_score"], candidate["id"]),
    )


def get_customer_create_preview(request_id: int) -> dict[str, Any]:
    """Return a read-only CRM customer creation preview for one request."""
    shipment_request = db.session.get(ShipmentRequest, request_id)
    if shipment_request is None:
        raise CrmCustomerCreatePreviewNotFoundError("Shipment request not found", 404)

    suggested_fields = build_suggested_customer_fields(shipment_request)
    duplicate_candidates = find_duplicate_candidates(suggested_fields)
    strong_matches = [
        candidate
        for candidate in duplicate_candidates
        if candidate["match_strength"] == "strong"
    ]

    return {
        "operation": "preview",
        "preview_only": True,
        "shipment_request": {
            "id": shipment_request.id,
            "customer_id": shipment_request.customer_id,
            "status": shipment_request.status,
            "assigned_to": shipment_request.assigned_to,
            "gamification_customer_id": shipment_request.gamification_customer_id,
        },
        "suggested_customer": suggested_fields,
        "duplicate_candidates": duplicate_candidates,
        "metadata": {
            "match_policy": "advisory_only",
            "strong_duplicate_count": len(strong_matches),
            "missing_fields": get_missing_fields(suggested_fields),
            "can_create_without_user_review": False,
            "mutation_allowed": False,
        },
    }
