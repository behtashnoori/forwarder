"""Helpers for CRM customer creation workflows from shipment requests."""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_

from backend.extensions import db
from backend.models import Customer, ShipmentRequest
from backend.services.ownership_service import require_tenant_resource, tenant_organization_for_user
from backend.services.crm_customer_link_service import (
    add_customer_link_audit_records,
    build_customer_summary,
    build_request_link_payload,
)


class CrmCustomerCreatePreviewError(Exception):
    """Base preview exception with an HTTP status code."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CrmCustomerCreatePreviewNotFoundError(CrmCustomerCreatePreviewError):
    """Raised when the target shipment request is missing."""


class CrmCustomerCreateValidationError(CrmCustomerCreatePreviewError):
    """Raised when create-and-link input is invalid."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class CrmCustomerCreateConflictError(CrmCustomerCreatePreviewError):
    """Raised when controlled creation needs explicit user acknowledgement."""

    def __init__(self, message: str):
        super().__init__(message, 409)


CUSTOMER_CREATE_FIELDS = {
    "company_name",
    "first_name",
    "last_name",
    "email",
    "phone",
    "mobile",
    "website",
    "industry",
    "company_size",
    "customer_type",
    "status",
    "source",
    "notes",
    "address",
    "city",
    "province",
    "postal_code",
    "country",
}


def _clean_text(value: Any) -> str | None:
    """Return a trimmed string, or None when the value has no useful text."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_customer_payload(customer_payload: dict[str, Any]) -> dict[str, Any]:
    """Keep only CRM Customer fields and trim string values."""
    cleaned: dict[str, Any] = {}
    for field in CUSTOMER_CREATE_FIELDS:
        if field not in customer_payload:
            continue
        value = customer_payload[field]
        cleaned[field] = _clean_text(value) if isinstance(value, str) or value is None else value
    return cleaned


def _validate_customer_payload(customer_payload: dict[str, Any]) -> None:
    """Validate the minimum fields needed by the current Customer model."""
    missing = [
        field for field in ("first_name", "last_name") if not customer_payload.get(field)
    ]
    if missing:
        raise CrmCustomerCreateValidationError(
            f"Missing required customer fields: {', '.join(missing)}"
        )


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


def create_customer_from_request(
    request_id: int,
    payload: dict[str, Any],
    user: dict[str, Any],
    remote_addr: str | None = None,
) -> dict[str, Any]:
    """Create a CRM Customer from reviewed request data and optionally link it."""
    shipment_request = db.session.get(ShipmentRequest, request_id)
    if shipment_request is None:
        raise CrmCustomerCreatePreviewNotFoundError("Shipment request not found", 404)
    organization_id = tenant_organization_for_user(user)
    require_tenant_resource(shipment_request, expected_organization_id=organization_id)

    link_to_request = payload.get("link", True)
    if not isinstance(link_to_request, bool):
        raise CrmCustomerCreateValidationError("link must be a boolean")

    if link_to_request and shipment_request.customer_id is not None:
        raise CrmCustomerCreateConflictError("Shipment request already has a CRM customer")

    suggested_fields = build_suggested_customer_fields(shipment_request)
    submitted_customer = payload.get("customer") or {}
    if not isinstance(submitted_customer, dict):
        raise CrmCustomerCreateValidationError("customer must be an object")

    reviewed_customer = dict(suggested_fields)
    reviewed_customer.update(_clean_customer_payload(submitted_customer))
    _validate_customer_payload(reviewed_customer)

    duplicate_candidates = find_duplicate_candidates(reviewed_customer)
    strong_matches = [
        candidate
        for candidate in duplicate_candidates
        if candidate["match_strength"] == "strong"
    ]
    duplicate_acknowledged = payload.get("duplicate_acknowledged", False)
    if strong_matches and duplicate_acknowledged is not True:
        raise CrmCustomerCreateConflictError("Strong duplicate candidates require acknowledgement")

    customer = Customer(
        ownership_scope="TENANT",
        operational_organization_id=organization_id,
        company_name=reviewed_customer.get("company_name"),
        first_name=reviewed_customer.get("first_name"),
        last_name=reviewed_customer.get("last_name"),
        email=reviewed_customer.get("email"),
        phone=reviewed_customer.get("phone"),
        mobile=reviewed_customer.get("mobile"),
        website=reviewed_customer.get("website"),
        industry=reviewed_customer.get("industry"),
        company_size=reviewed_customer.get("company_size"),
        customer_type=reviewed_customer.get("customer_type") or "prospect",
        status=reviewed_customer.get("status") or "active",
        source=reviewed_customer.get("source") or "shipment_request",
        notes=reviewed_customer.get("notes"),
        address=reviewed_customer.get("address"),
        city=reviewed_customer.get("city"),
        province=reviewed_customer.get("province"),
        postal_code=reviewed_customer.get("postal_code"),
        country=reviewed_customer.get("country") or "Iran",
    )
    db.session.add(customer)
    db.session.flush()

    operation = "create"
    if link_to_request:
        old_customer_id = shipment_request.customer_id
        shipment_request.customer_id = customer.id
        operation = "create_and_link"
        add_customer_link_audit_records(
            shipment_request=shipment_request,
            user=user,
            operation=operation,
            old_customer_id=old_customer_id,
            new_customer_id=customer.id,
            note=payload.get("reason"),
            remote_addr=remote_addr,
        )

    db.session.commit()
    link_payload = build_request_link_payload(shipment_request, operation)
    return {
        "operation": operation,
        "created_customer": build_customer_summary(customer),
        "shipment_request": link_payload["shipment_request"],
        "customer": link_payload["customer"],
        "duplicate_candidates": duplicate_candidates,
        "metadata": {
            "linked": link_to_request,
            "strong_duplicate_count": len(strong_matches),
            "duplicate_acknowledged": duplicate_acknowledged,
        },
    }
