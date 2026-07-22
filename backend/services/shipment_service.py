"""Service helpers for public shipment request endpoints."""
import secrets
import string
from datetime import datetime
from typing import Any

from flask import current_app

from backend.extensions import db
from backend.models import (
    CustomerGamification,
    CustomerWorkflowStep,
    ShipmentRequest,
    ShipmentRequestLog,
    TransportMethod,
)
from backend.referral_engine import referral_engine

INTERNATIONAL_METHOD_NAMES = ["sea freight", "air freight", "land transport", "rail transport"]
DOMESTIC_METHOD_NAMES = ["road transport", "rail transport", "air transport"]
PREFERENCE_OPTIONS = [
    {"value": "customer_choice", "label": "انتخاب مشتری", "description": "مشتری روش حمل را انتخاب می‌کند"},
    {"value": "forwarder_suggestion", "label": "پیشنهاد فورواردر", "description": "فورواردر بهترین روش را پیشنهاد می‌دهد"},
]
VALID_SHIPPING_TYPES = ["domestic", "international"]
VALID_TRANSPORT_PREFERENCES = ["customer_choice", "forwarder_suggestion"]
VALID_IRAN_DEST_TYPES = ["port", "customs", "city"]
DOMESTIC_LOCATION_ERROR = "اطلاعات مبدا و مقصد داخلی نامعتبر است."

# Keys carrying the structured Iran destination point. Absent for domestic and
# for international shipments whose destination is not Iran.
IRAN_DEST_KEYS = (
    "iran_dest_type",
    "iran_entry_port",
    "iran_entry_province",
    "iran_entry_port_id",
    "iran_entry_province_id",
    "iran_dest_customs_office_id",
    "iran_dest_city_id",
)


class ShipmentValidationError(ValueError):
    """Raised when shipment request payload validation should return a 400 response."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_transport_methods_payload() -> dict:
    """Return available transport methods grouped for public shipment forms."""
    methods = db.session.query(TransportMethod).filter(TransportMethod.is_active == True).all()
    international_methods = []
    domestic_methods = []

    for method in methods:
        method_data = {
            "id": method.id,
            "name": method.name,
            "name_fa": method.name_fa,
            "description": method.description,
        }
        method_name_lower = method.name.lower()
        if method_name_lower in INTERNATIONAL_METHOD_NAMES:
            international_methods.append(method_data)
        if method_name_lower in DOMESTIC_METHOD_NAMES:
            domestic_methods.append(method_data)
        if method_name_lower not in INTERNATIONAL_METHOD_NAMES and method_name_lower not in DOMESTIC_METHOD_NAMES:
            international_methods.append(method_data)
            domestic_methods.append(method_data)

    return {
        "international_methods": international_methods,
        "domestic_methods": domestic_methods,
        "preference_options": PREFERENCE_OPTIONS,
    }


def create_shipment_request(payload: dict[str, Any], remote_addr: str | None = None) -> ShipmentRequest:
    """Create, commit, and optionally auto-assign a public shipment request."""
    normalized = normalize_shipment_payload(payload)
    timestamp = datetime.utcnow()

    shipment_request = ShipmentRequest(**build_shipment_request_data(normalized, timestamp))
    db.session.add(shipment_request)
    db.session.flush()

    shipment_request.tracking_code = generate_tracking_code(shipment_request)

    log_entry = ShipmentRequestLog(
        shipment_request_id=shipment_request.id,
        created_at=timestamp,
        note="ثبت اولیه درخواست",
        ip_address=remote_addr,
    )
    db.session.add(log_entry)

    handle_gamification(shipment_request, normalized.get("gamification_customer_id"), timestamp)

    db.session.commit()
    assign_request_with_referral(shipment_request)
    return shipment_request


def normalize_shipment_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize the public shipment request payload without changing current behavior."""
    shipping_type = payload.get("shipping_type", "domestic")
    if shipping_type not in VALID_SHIPPING_TYPES:
        raise ShipmentValidationError("نوع ارسال نامعتبر است.")

    normalized: dict[str, Any] = {"shipping_type": shipping_type}

    if shipping_type == "domestic":
        try:
            normalized.update({
                "origin_province_id": parse_required_int(payload.get("origin_province_id")),
                "origin_county_id": parse_optional_int(payload.get("origin_county_id")),
                "origin_city_id": parse_optional_int(payload.get("origin_city_id")),
                "dest_province_id": parse_required_int(payload.get("dest_province_id")),
                "dest_county_id": parse_optional_int(payload.get("dest_county_id")),
                "dest_city_id": parse_optional_int(payload.get("dest_city_id")),
            })
        except (KeyError, TypeError, ValueError):
            raise ShipmentValidationError(DOMESTIC_LOCATION_ERROR) from None
    else:
        origin_country = payload.get("origin_country", "").strip()
        origin_city_international = payload.get("origin_city_international", "").strip()
        dest_country = payload.get("dest_country", "").strip()
        dest_city_international = payload.get("dest_city_international", "").strip()

        if not origin_country or not origin_city_international or not dest_country or not dest_city_international:
            raise ShipmentValidationError("اطلاعات مبدا و مقصد بین‌المللی نامعتبر است.")

        normalized.update({
            "origin_country": origin_country,
            "origin_city_international": origin_city_international,
            "origin_address_international": payload.get("origin_address_international", "").strip() or None,
            "dest_country": dest_country,
            "dest_city_international": dest_city_international,
            "dest_address_international": payload.get("dest_address_international", "").strip() or None,
        })
        normalized.update(normalize_iran_destination(payload))

    contact_phone = payload.get("contact_phone", "")
    if not is_valid_phone(contact_phone):
        raise ShipmentValidationError("شماره تماس نامعتبر است. لطفاً شماره‌ای با پیش‌شماره 09 و ۱۱ رقم وارد کنید.")

    transport_method_raw = payload.get("transport_method") or payload.get("shipment_mode")
    transport_method = None
    if isinstance(transport_method_raw, str):
        sanitized = transport_method_raw.strip()
        if sanitized:
            transport_method = sanitized.lower()

    transport_method_preference = payload.get("transport_method_preference", "customer_choice")
    if transport_method_preference not in VALID_TRANSPORT_PREFERENCES:
        transport_method_preference = "customer_choice"

    normalized.update({
        "contact_phone": contact_phone,
        "customer_first_name": payload.get("customer_first_name", "").strip() or None,
        "customer_last_name": payload.get("customer_last_name", "").strip() or None,
        "gamification_customer_id": payload.get("gamification_customer_id"),
        "transport_method": transport_method,
        "international_transport_method": payload.get("international_transport_method"),
        "domestic_transport_method": payload.get("domestic_transport_method"),
        "transport_method_preference": transport_method_preference,
        "cargo_description": payload.get("cargo_description", "").strip() or None,
        "cargo_weight": parse_float_or_none(payload.get("cargo_weight")),
        "cargo_volume": parse_float_or_none(payload.get("cargo_volume")),
        "cargo_value": parse_float_or_none(payload.get("cargo_value")),
        "special_instructions": payload.get("special_instructions", "").strip() or None,
        "pickup_date": parse_date_or_none(payload.get("pickup_date")),
        "delivery_date": parse_date_or_none(payload.get("delivery_date")),
    })
    return normalized


def normalize_iran_destination(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize the structured Iran destination point.

    The three modes ('port', 'customs', 'city') are mutually exclusive and each
    requires its own reference plus a province. Validation only runs when the
    caller explicitly declares ``iran_dest_type``; legacy payloads without it are
    persisted as-is, preserving backward-compatible behavior.
    """
    result: dict[str, Any] = {
        "iran_dest_type": None,
        "iran_entry_port": payload.get("iran_entry_port", "").strip() or None
        if isinstance(payload.get("iran_entry_port"), str) else None,
        "iran_entry_province": payload.get("iran_entry_province", "").strip() or None
        if isinstance(payload.get("iran_entry_province"), str) else None,
        "iran_entry_port_id": _parse_ref_id(payload.get("iran_entry_port_id")),
        "iran_entry_province_id": _parse_ref_id(payload.get("iran_entry_province_id")),
        "iran_dest_customs_office_id": _parse_ref_id(payload.get("iran_dest_customs_office_id")),
        "iran_dest_city_id": _parse_ref_id(payload.get("iran_dest_city_id")),
    }

    raw_type = payload.get("iran_dest_type")
    if raw_type in (None, ""):
        return result

    dest_type = str(raw_type).strip().lower()
    if dest_type not in VALID_IRAN_DEST_TYPES:
        raise ShipmentValidationError("نوع مقصد در ایران نامعتبر است.")
    result["iran_dest_type"] = dest_type

    # Only the reference belonging to the declared mode may survive. This also
    # protects non-UI clients from persisting stale IDs after changing modes.
    if dest_type != "port":
        result["iran_entry_port"] = None
        result["iran_entry_port_id"] = None
    if dest_type != "customs":
        result["iran_dest_customs_office_id"] = None
    if dest_type != "city":
        result["iran_dest_city_id"] = None

    if dest_type == "port" and not result["iran_entry_port_id"]:
        raise ShipmentValidationError("بندر مقصد در ایران را انتخاب کنید.")
    if dest_type == "customs" and not result["iran_dest_customs_office_id"]:
        raise ShipmentValidationError("گمرک مرزی مقصد در ایران را انتخاب کنید.")
    if dest_type == "city" and not result["iran_dest_city_id"]:
        raise ShipmentValidationError("شهر مقصد در ایران را انتخاب کنید.")
    if not result["iran_entry_province_id"]:
        raise ShipmentValidationError("استان مقصد در ایران را انتخاب کنید.")

    return result


def _parse_ref_id(value):
    """Parse an optional reference id; reject non-numeric values with a 400."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ShipmentValidationError("شناسه مرجع مقصد در ایران نامعتبر است.") from None


def build_shipment_request_data(normalized: dict[str, Any], timestamp: datetime) -> dict[str, Any]:
    """Build ShipmentRequest constructor data from a normalized payload."""
    shipment_request_data = {
        "shipping_type": normalized["shipping_type"],
        "contact_phone": normalized["contact_phone"],
        "customer_first_name": normalized["customer_first_name"],
        "customer_last_name": normalized["customer_last_name"],
        "transport_method": normalized["transport_method"],
        "international_transport_method": normalized["international_transport_method"],
        "domestic_transport_method": normalized["domestic_transport_method"],
        "transport_method_preference": normalized["transport_method_preference"],
        "cargo_description": normalized["cargo_description"],
        "cargo_weight": normalized["cargo_weight"],
        "cargo_volume": normalized["cargo_volume"],
        "cargo_value": normalized["cargo_value"],
        "special_instructions": normalized["special_instructions"],
        "pickup_date": normalized["pickup_date"],
        "delivery_date": normalized["delivery_date"],
        "created_at": timestamp,
        "ready_at": timestamp,
        "status_request_status": "new",
        "assigned_to": None,
        "status": "new",
        "sla_due_at": None,
        "last_customer_touch_at": None,
        "has_unread_for_assignee": True,
        "priority": "normal",
        "estimated_value": None,
        "customer_id": None,
        "gamification_customer_id": normalized["gamification_customer_id"],
    }

    if normalized["shipping_type"] == "domestic":
        shipment_request_data.update({
            "origin_province_id": normalized["origin_province_id"],
            "origin_county_id": normalized["origin_county_id"],
            "origin_city_id": normalized["origin_city_id"],
            "dest_province_id": normalized["dest_province_id"],
            "dest_county_id": normalized["dest_county_id"],
            "dest_city_id": normalized["dest_city_id"],
        })
    else:
        shipment_request_data.update({
            "origin_country": normalized["origin_country"],
            "origin_city_international": normalized["origin_city_international"],
            "origin_address_international": normalized["origin_address_international"],
            "dest_country": normalized["dest_country"],
            "dest_city_international": normalized["dest_city_international"],
            "dest_address_international": normalized["dest_address_international"],
            "iran_dest_type": normalized.get("iran_dest_type"),
            "iran_entry_port": normalized.get("iran_entry_port"),
            "iran_entry_province": normalized.get("iran_entry_province"),
            "iran_entry_port_id": normalized.get("iran_entry_port_id"),
            "iran_entry_province_id": normalized.get("iran_entry_province_id"),
            "iran_dest_customs_office_id": normalized.get("iran_dest_customs_office_id"),
            "iran_dest_city_id": normalized.get("iran_dest_city_id"),
        })

    return shipment_request_data


def build_shipment_request_payload(shipment_request: ShipmentRequest) -> dict[str, Any]:
    """Build the current public create response payload."""
    tracking_display = getattr(shipment_request, "tracking_code", None) or f"SR{shipment_request.id:06d}"
    return {
        "message": "درخواست شما ثبت شد. کارشناسان ما ظرف دو ساعت با شما تماس خواهند گرفت.",
        "id": shipment_request.id,
        "tracking_code": tracking_display,
    }


def generate_tracking_code(shipment_request: ShipmentRequest) -> str:
    """Generate a unique public tracking code, preserving the legacy fallback behavior."""
    try:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(100):
            code = "SR-" + "".join(secrets.choice(alphabet) for _ in range(6))
            if db.session.query(ShipmentRequest).filter(ShipmentRequest.tracking_code == code).first() is None:
                return code
        return "SR-" + secrets.token_hex(3).upper()
    except Exception:
        return f"SR{shipment_request.id:06d}"


def handle_gamification(shipment_request: ShipmentRequest, gamification_customer_id, timestamp: datetime) -> None:
    """Apply existing gamification side effects without failing request creation."""
    if not gamification_customer_id:
        return

    try:
        customer = db.session.query(CustomerGamification).filter(
            CustomerGamification.id == gamification_customer_id
        ).first()

        if customer:
            customer.total_requests += 1
            workflow_step = CustomerWorkflowStep(
                customer_id=gamification_customer_id,
                shipment_request_id=shipment_request.id,
                step_name="request_submitted",
                step_order=2,
                is_completed=True,
                completed_at=timestamp,
                points_earned=20,
            )
            db.session.add(workflow_step)
            customer.update_loyalty_points(20)
            current_app.logger.info(
                f"Gamification: Customer {gamification_customer_id} submitted request {shipment_request.id}, earned 20 points"
            )
    except Exception as e:
        current_app.logger.error(f"Error in gamification for request {shipment_request.id}: {e}")


def assign_request_with_referral(shipment_request: ShipmentRequest) -> None:
    """Run referral assignment after creation without failing public request creation."""
    try:
        assigned_expert_id = referral_engine.auto_assign_request(shipment_request.id)
        if assigned_expert_id:
            current_app.logger.info(
                f"Request {shipment_request.id} assigned to expert {assigned_expert_id} via referral rules"
            )
        else:
            current_app.logger.info("No active experts available for request %s; status remains new", shipment_request.id)
    except Exception as e:
        current_app.logger.error(f"Error in referral assignment for request {shipment_request.id}: {e}")


def parse_float_or_none(value):
    """Parse optional numeric form fields using current tolerant behavior."""
    if value is not None:
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return value


def parse_required_int(value):
    """Parse required integer IDs and reject blank values."""
    if value in (None, ""):
        raise ValueError
    return int(value)


def parse_optional_int(value):
    """Parse optional integer IDs; blank values are stored as NULL."""
    if value in (None, ""):
        return None
    return int(value)


def parse_date_or_none(value):
    """Parse optional YYYY-MM-DD form dates using current tolerant behavior."""
    if value:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    return None


def is_valid_phone(phone: str) -> bool:
    """Validate Iranian mobile phone number format."""
    if not isinstance(phone, str):
        return False
    return phone.startswith("09") and len(phone) == 11 and phone.isdigit()
