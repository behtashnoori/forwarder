"""Service helpers for public shipment request endpoints."""
import secrets
import string
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from flask import current_app

from backend.extensions import db
from backend.census_context import CensusTransitioned, CensusUnavailable
from backend.quarantine import QuarantinedResource
from backend.models import (
    CustomerGamification,
    CustomerWorkflowStep,
    CargoType,
    Country,
    RequestCargoItem,
    ShipmentRequest,
    ShipmentRequestLog,
    TransportMethod,
    UnitOfMeasure,
)
from backend.referral_engine import referral_engine
from backend.request_transport_catalog import (
    COMBINED_TRANSPORT_CODE,
    LEGACY_REQUEST_TRANSPORT_VALUES,
    catalog_name_key,
)
from backend.services.location_resolver import LocationResolutionError, resolve_location

INTERNATIONAL_METHOD_NAMES = ["sea freight", "air freight", "land transport", "rail transport"]
DOMESTIC_METHOD_NAMES = ["road transport", "rail transport", "air transport"]
PREFERENCE_OPTIONS = [
    {"value": "customer_choice", "label": "انتخاب مشتری", "description": "مشتری روش حمل را انتخاب می‌کند"},
    {"value": "forwarder_suggestion", "label": "پیشنهاد فورواردر", "description": "فورواردر بهترین روش را پیشنهاد می‌دهد"},
]
VALID_SHIPPING_TYPES = ["domestic", "international"]
VALID_TRANSPORT_PREFERENCES = ["customer_choice", "forwarder_suggestion"]
VALID_IRAN_DEST_TYPES = ["port", "customs", "city"]
SECURITY_FENCE_ERRORS = (QuarantinedResource, CensusTransitioned, CensusUnavailable)
DOMESTIC_LOCATION_ERROR = "اطلاعات مبدا و مقصد داخلی نامعتبر است."
REQUEST_CARGO_ERROR = "Request cargo is invalid."
REQUEST_CARGO_ALLOWED_FIELDS = frozenset({
    "description",
    "cargo_type_public_id",
    "quantity",
    "uom_public_id",
})
REQUEST_CARGO_DECIMAL_GRAMMAR = re.compile(
    r"^(?:0|[1-9][0-9]*)(?:\.([0-9]+))?$"
)

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

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "VALIDATION_FAILED",
        fields: list[dict[str, str]] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.fields = fields or []


def get_transport_methods_payload() -> dict:
    """Return available transport methods grouped for public shipment forms."""
    methods = (
        db.session.query(TransportMethod)
        .filter(TransportMethod.is_active == True)
        .order_by(TransportMethod.name, TransportMethod.id)
        .all()
    )
    international_methods = []
    domestic_methods = []
    seen_names: set[str] = set()

    for method in methods:
        name_key = catalog_name_key(method.name)
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
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


def _normalize_request_transport_value(value: Any, field: str) -> str | None:
    """Accept an exact active catalog value or a preserved historical API value."""
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ShipmentValidationError(
            "روش حمل انتخاب‌شده نامعتبر است.",
            code="REQUEST_TRANSPORT_INVALID",
            fields=[{"field": field, "code": "INVALID_TYPE", "message": "Transport method must be a string."}],
        )
    normalized = value.strip()
    active_names = {
        name
        for (name,) in db.session.query(TransportMethod.name)
        .filter(TransportMethod.is_active == True)
        .all()
    }
    if normalized not in LEGACY_REQUEST_TRANSPORT_VALUES and normalized not in active_names:
        raise ShipmentValidationError(
            "روش حمل انتخاب‌شده پشتیبانی نمی‌شود.",
            code="REQUEST_TRANSPORT_INVALID",
            fields=[{"field": field, "code": "UNSUPPORTED_VALUE", "message": "Transport method is not supported."}],
        )
    return normalized


def get_request_cargo_options_payload() -> dict[str, list[dict[str, Any]]]:
    """Return the fixed, active, public-safe Request Cargo reference projection."""
    cargo_types = (
        db.session.query(CargoType)
        .filter(CargoType.is_active.is_(True))
        .order_by(CargoType.display_order, CargoType.immutable_code, CargoType.id)
        .all()
    )
    uoms = (
        db.session.query(UnitOfMeasure)
        .filter(UnitOfMeasure.is_active.is_(True))
        .order_by(UnitOfMeasure.display_order, UnitOfMeasure.immutable_code, UnitOfMeasure.id)
        .all()
    )
    return {
        "cargo_types": [_serialize_cargo_type(row) for row in cargo_types],
        "uoms": [_serialize_uom(row) for row in uoms],
    }


def create_shipment_request(
    payload: dict[str, Any],
    remote_addr: str | None = None,
    request_host: str | None = None,
) -> ShipmentRequest:
    """Create and optionally auto-assign one request in one census-bound UoW."""
    from backend.census_context import census_unit_of_work

    try:
        with census_unit_of_work(db.session):
            from backend.services.organization_hostname_service import resolve_organization_for_host

            organization = resolve_organization_for_host(request_host)
            shipment_request = _stage_shipment_request(payload, remote_addr, organization)
            assign_request_with_referral(shipment_request)
            db.session.commit()
            return shipment_request
    except Exception:
        db.session.rollback()
        raise


def _stage_shipment_request(
    payload: dict[str, Any], remote_addr: str | None = None, organization=None
) -> ShipmentRequest:
    """Stage request creation without finalizing the caller's transaction."""
    normalized = normalize_shipment_payload(payload)
    timestamp = datetime.utcnow()

    organization_id = organization.id if organization is not None else None
    shipment_request = ShipmentRequest(
        ownership_scope="TENANT" if organization_id is not None else "INTAKE",
        operational_organization_id=organization_id,
        **build_shipment_request_data(normalized, timestamp),
    )
    db.session.add(shipment_request)
    db.session.flush()

    for position, cargo_item in enumerate(normalized["cargo_items"], start=1):
        db.session.add(RequestCargoItem(
            shipment_request_id=shipment_request.id,
            position=position,
            cargo_type_id=(
                cargo_item["cargo_type"].id if cargo_item["cargo_type"] else None
            ),
            description=cargo_item["description"],
            quantity=cargo_item["quantity"],
            uom_id=cargo_item["uom"].id if cargo_item["uom"] else None,
            created_at=datetime.now(timezone.utc),
        ))
    db.session.flush()

    shipment_request.tracking_code = generate_tracking_code(shipment_request)

    log_entry = ShipmentRequestLog(
        shipment_request_id=shipment_request.id,
        operational_organization_id=organization_id,
        created_at=timestamp,
        note="ثبت اولیه درخواست",
        ip_address=remote_addr,
    )
    db.session.add(log_entry)

    handle_gamification(shipment_request, normalized.get("gamification_customer_id"), timestamp)

    # New canonical cases receive the currently applicable document policies in
    # the same transaction. Legacy cases use the idempotent documents endpoint.
    from backend.services.case_document_service import initialize_requirements
    initialize_requirements(shipment_request, None)

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
        canonical_keys = ("origin_country_id", "origin_international_city_id", "dest_country_id", "dest_international_city_id")
        if any(payload.get(key) not in (None, "") for key in canonical_keys):
            normalized.update(_normalize_international_locations(payload))
        else:
            normalized.update(_normalize_legacy_international(payload))

    contact_phone = payload.get("contact_phone", "")
    if not is_valid_phone(contact_phone):
        raise ShipmentValidationError("شماره تماس نامعتبر است. لطفاً شماره‌ای با پیش‌شماره 09 و ۱۱ رقم وارد کنید.")

    transport_method_raw = payload.get("transport_method") or payload.get("shipment_mode")
    transport_method = None
    if transport_method_raw not in (None, ""):
        sanitized = _normalize_request_transport_value(transport_method_raw, "transport_method")
        if sanitized:
            transport_method = (
                COMBINED_TRANSPORT_CODE
                if sanitized == COMBINED_TRANSPORT_CODE
                else sanitized.lower()
            )

    international_transport_method = _normalize_request_transport_value(
        payload.get("international_transport_method"), "international_transport_method"
    )
    domestic_transport_method = _normalize_request_transport_value(
        payload.get("domestic_transport_method"), "domestic_transport_method"
    )

    transport_method_preference = payload.get("transport_method_preference", "customer_choice")
    if transport_method_preference not in VALID_TRANSPORT_PREFERENCES:
        transport_method_preference = "customer_choice"

    normalized.update({
        "contact_phone": contact_phone,
        "customer_first_name": payload.get("customer_first_name", "").strip() or None,
        "customer_last_name": payload.get("customer_last_name", "").strip() or None,
        "gamification_customer_id": payload.get("gamification_customer_id"),
        "transport_method": transport_method,
        "international_transport_method": international_transport_method,
        "domestic_transport_method": domestic_transport_method,
        "transport_method_preference": transport_method_preference,
        "cargo_description": payload.get("cargo_description", "").strip() or None,
        "cargo_weight": parse_float_or_none(payload.get("cargo_weight")),
        "cargo_volume": parse_float_or_none(payload.get("cargo_volume")),
        "cargo_value": parse_float_or_none(payload.get("cargo_value")),
        "special_instructions": payload.get("special_instructions", "").strip() or None,
        "pickup_date": parse_date_or_none(payload.get("pickup_date")),
        "delivery_date": parse_date_or_none(payload.get("delivery_date")),
        "cargo_items": normalize_request_cargo_items(payload),
    })
    return normalized


def _cargo_error(field: str, code: str, message: str) -> dict[str, str]:
    return {"field": field, "code": code, "message": message}


def _optional_public_id(
    item: dict[str, Any],
    key: str,
    path: str,
    errors: list[dict[str, str]],
) -> str | None:
    value = item.get(key)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        errors.append(_cargo_error(path, "INVALID_TYPE", "Value must be a string public ID."))
        return None
    return value.strip() or None


def _parse_request_cargo_quantity(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
) -> Decimal | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        errors.append(_cargo_error(path, "INVALID_TYPE", "Quantity must be a decimal string."))
        return None

    match = REQUEST_CARGO_DECIMAL_GRAMMAR.fullmatch(value)
    if match is None:
        if re.fullmatch(r"[0-9]+\.[0-9]+", value):
            fraction = value.partition(".")[2]
            if len(fraction) > 6:
                errors.append(_cargo_error(path, "DECIMAL_SCALE_EXCEEDED", "Quantity may have at most 6 decimal places."))
                return None
        errors.append(_cargo_error(path, "DECIMAL_FORMAT_INVALID", "Quantity must be a canonical non-exponent decimal string."))
        return None

    fraction = match.group(1) or ""
    integer = value.partition(".")[0]
    if len(fraction) > 6:
        errors.append(_cargo_error(path, "DECIMAL_SCALE_EXCEEDED", "Quantity may have at most 6 decimal places."))
        return None
    if len(value.replace(".", "")) > 18 or len(integer) > 12:
        errors.append(_cargo_error(path, "DECIMAL_PRECISION_EXCEEDED", "Quantity may have at most 18 digits."))
        return None

    parsed = Decimal(value)
    if parsed <= 0:
        errors.append(_cargo_error(path, "MUST_BE_POSITIVE", "Quantity must be greater than zero."))
        return None
    return parsed


def normalize_request_cargo_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate optional nested Request Cargo without making the collection mandatory."""
    if "cargo_items" not in payload:
        return []
    raw_items = payload.get("cargo_items")
    if not isinstance(raw_items, list):
        raise ShipmentValidationError(
            REQUEST_CARGO_ERROR,
            422,
            "REQUEST_CARGO_VALIDATION_FAILED",
            [_cargo_error("cargo_items", "INVALID_TYPE", "Cargo items must be an array.")],
        )

    normalized: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for index, raw_item in enumerate(raw_items):
        base = f"cargo_items[{index}]"
        if not isinstance(raw_item, dict):
            errors.append(_cargo_error(base, "INVALID_TYPE", "Each cargo item must be an object."))
            continue

        for key in raw_item:
            if key not in REQUEST_CARGO_ALLOWED_FIELDS:
                errors.append(_cargo_error(f"{base}.{key}", "UNKNOWN_FIELD", "Field is not accepted for Request cargo."))

        description_value = raw_item.get("description")
        description = None
        if description_value not in (None, ""):
            if not isinstance(description_value, str):
                errors.append(_cargo_error(f"{base}.description", "INVALID_TYPE", "Description must be text."))
            else:
                description = description_value.strip() or None
                if description and len(description) > 2000:
                    errors.append(_cargo_error(f"{base}.description", "MAX_LENGTH_EXCEEDED", "Description may have at most 2000 characters."))

        cargo_type_public_id = _optional_public_id(
            raw_item,
            "cargo_type_public_id",
            f"{base}.cargo_type_public_id",
            errors,
        )
        uom_public_id = _optional_public_id(
            raw_item,
            "uom_public_id",
            f"{base}.uom_public_id",
            errors,
        )
        quantity_supplied = raw_item.get("quantity") not in (None, "")
        quantity = _parse_request_cargo_quantity(
            raw_item.get("quantity"), f"{base}.quantity", errors
        )

        cargo_type = None
        if cargo_type_public_id:
            cargo_type = db.session.query(CargoType).filter(
                CargoType.public_id == cargo_type_public_id
            ).one_or_none()
            if cargo_type is None:
                errors.append(_cargo_error(f"{base}.cargo_type_public_id", "REFERENCE_NOT_FOUND", "Cargo type was not found."))
            elif not cargo_type.is_active:
                errors.append(_cargo_error(f"{base}.cargo_type_public_id", "REFERENCE_INACTIVE", "Cargo type is inactive."))

        uom = None
        if uom_public_id:
            uom = db.session.query(UnitOfMeasure).filter(
                UnitOfMeasure.public_id == uom_public_id
            ).one_or_none()
            if uom is None:
                errors.append(_cargo_error(f"{base}.uom_public_id", "REFERENCE_NOT_FOUND", "Unit of measure was not found."))
            elif not uom.is_active:
                errors.append(_cargo_error(f"{base}.uom_public_id", "REFERENCE_INACTIVE", "Unit of measure is inactive."))

        if quantity_supplied != bool(uom_public_id):
            pair_field = "uom_public_id" if quantity_supplied else "quantity"
            errors.append(_cargo_error(f"{base}.{pair_field}", "QUANTITY_UOM_PAIR_REQUIRED", "Quantity and unit of measure must be supplied together."))

        if not (description or cargo_type_public_id or (quantity_supplied and uom_public_id)):
            errors.append(_cargo_error(base, "ITEM_EMPTY", "Cargo item must contain at least one meaningful fact."))

        normalized.append({
            "description": description,
            "cargo_type": cargo_type,
            "quantity": quantity,
            "uom": uom,
        })

    if errors:
        raise ShipmentValidationError(
            REQUEST_CARGO_ERROR,
            422,
            "REQUEST_CARGO_VALIDATION_FAILED",
            errors,
        )
    return normalized


def _optional_text(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _normalize_legacy_international(payload: dict[str, Any]) -> dict[str, Any]:
    """Preserve N-1 text submissions without inferring canonical identity."""
    origin_country = _optional_text(payload.get("origin_country"))
    origin_city = _optional_text(payload.get("origin_city_international"))
    dest_country = _optional_text(payload.get("dest_country"))
    dest_city = _optional_text(payload.get("dest_city_international"))
    is_iran_destination = is_iran_destination_country(dest_country or "")
    if not origin_country or not origin_city or not dest_country or (not is_iran_destination and not dest_city):
        raise ShipmentValidationError("اطلاعات مبدا و مقصد بین‌المللی نامعتبر است.")
    return {
        "origin_country_id": None,
        "origin_international_city_id": None,
        "dest_country_id": None,
        "dest_international_city_id": None,
        "origin_country": origin_country,
        "origin_city_international": origin_city,
        "origin_address_international": _optional_text(payload.get("origin_address_international")),
        "dest_country": dest_country,
        "dest_city_international": dest_city,
        "dest_address_international": _optional_text(payload.get("dest_address_international")),
        "origin_province_id": None,
        "origin_county_id": None,
        "origin_city_id": None,
        **normalize_iran_destination(payload),
    }


def _location_error(exc: LocationResolutionError) -> ShipmentValidationError:
    return ShipmentValidationError(exc.message, exc.status, exc.code)


def _required_ref_id(payload: dict[str, Any], key: str) -> int:
    try:
        return parse_required_int(payload.get(key))
    except (TypeError, ValueError):
        raise ShipmentValidationError(f"{key} is required.", code="LOCATION_MAPPING_REQUIRED") from None


def _normalize_international_locations(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize new international writes from canonical IDs only."""
    origin_country_id = _required_ref_id(payload, "origin_country_id")
    dest_country_id = _required_ref_id(payload, "dest_country_id")
    try:
        origin_country = resolve_location({"source_type": "country", "source_id": origin_country_id})
        dest_country = resolve_location({"source_type": "country", "source_id": dest_country_id})
    except LocationResolutionError as exc:
        raise _location_error(exc) from exc

    result = {
        "origin_country_id": origin_country_id,
        "origin_international_city_id": None,
        "origin_country": origin_country.display_label,
        "origin_city_international": None,
        "origin_address_international": _optional_text(payload.get("origin_address_international")),
        "dest_country_id": dest_country_id,
        "dest_international_city_id": None,
        "dest_country": dest_country.display_label,
        "dest_city_international": None,
        "dest_address_international": _optional_text(payload.get("dest_address_international")),
        "origin_province_id": None,
        "origin_county_id": None,
        "origin_city_id": None,
        **{key: None for key in IRAN_DEST_KEYS},
    }

    # As with destination, IR uses the standard governed international
    # continuation whenever the caller supplies it; the province path is
    # retained solely for compatibility with older payloads.
    if origin_country.country_code == "IR" and not payload.get("origin_international_city_id"):
        province_id = _required_ref_id(payload, "origin_province_id")
        try:
            province = resolve_location(
                {"source_type": "province", "source_id": province_id},
                expected_country_id=origin_country_id,
            )
            lower = payload.get("origin_location")
            if lower:
                resolved_lower = resolve_location(
                    _canonical_reference(lower),
                    expected_country_id=origin_country_id,
                    expected_province_id=province_id,
                )
                if resolved_lower.source_type == "city":
                    result["origin_city_id"] = resolved_lower.source_id
                    result["origin_county_id"] = resolved_lower.county_id
            result["origin_province_id"] = province.source_id
            result["origin_city_international"] = province.display_label
        except LocationResolutionError as exc:
            raise _location_error(exc) from exc
    else:
        city_id = _required_ref_id(payload, "origin_international_city_id")
        try:
            city = resolve_location(
                {"source_type": "international_city", "source_id": city_id},
                expected_country_id=origin_country_id,
            )
        except LocationResolutionError as exc:
            raise _location_error(exc) from exc
        result["origin_international_city_id"] = city_id
        result["origin_city_international"] = city.display_label

    # A governed InternationalCity is the standard destination continuation
    # for every country, including IR.  The older domestic Iran destination
    # path remains a compatibility fallback only when that standard selection
    # was not supplied.
    if dest_country.country_code == "IR" and not payload.get("dest_international_city_id"):
        selection = payload.get("iran_destination")
        if selection is None and payload.get("iran_dest_type"):
            legacy_ids = {
                "port": payload.get("iran_entry_port_id"),
                "customs": payload.get("iran_dest_customs_office_id"),
                "city": payload.get("iran_dest_city_id"),
            }
            selection = {"type": payload.get("iran_dest_type"), "id": legacy_ids.get(payload.get("iran_dest_type"))}
        if not isinstance(selection, dict):
            raise ShipmentValidationError("Iran destination selection is required.", code="LOCATION_MAPPING_REQUIRED")
        if payload.get("iran_entry_province_id") not in (None, ""):
            raise ShipmentValidationError("Iran destination province is derived and must not be submitted.")
        reference = _canonical_reference(selection, public_types=True)
        try:
            destination = resolve_location(reference, expected_country_id=dest_country_id)
        except LocationResolutionError as exc:
            raise _location_error(exc) from exc
        if destination.province_id is None:
            raise ShipmentValidationError("Iran destination lacks governed province ancestry.", code="LOCATION_MAPPING_REQUIRED")
        public_type = {"iran_port": "port", "customs_office": "customs", "city": "city"}[destination.source_type]
        result.update({
            "iran_dest_type": public_type,
            "iran_entry_province_id": destination.province_id,
            "iran_entry_province": destination.province_name,
            "iran_entry_port_id": destination.source_id if public_type == "port" else None,
            "iran_entry_port": destination.display_label if public_type == "port" else None,
            "iran_dest_customs_office_id": destination.source_id if public_type == "customs" else None,
            "iran_dest_city_id": destination.source_id if public_type == "city" else None,
        })
    else:
        city_id = _required_ref_id(payload, "dest_international_city_id")
        try:
            city = resolve_location(
                {"source_type": "international_city", "source_id": city_id},
                expected_country_id=dest_country_id,
            )
        except LocationResolutionError as exc:
            raise _location_error(exc) from exc
        result["dest_international_city_id"] = city_id
        result["dest_city_international"] = city.display_label
    return result


def _canonical_reference(value: dict[str, Any], public_types: bool = False) -> dict[str, Any]:
    source_type = value.get("source_type", value.get("type"))
    if public_types:
        source_type = {"port": "iran_port", "customs": "customs_office", "city": "city"}.get(source_type)
    source_id = value.get("source_id", value.get("id"))
    try:
        source_id = parse_required_int(source_id)
    except (TypeError, ValueError):
        raise ShipmentValidationError("A canonical location selection is required.", code="LOCATION_MAPPING_REQUIRED") from None
    return {"source_type": source_type, "source_id": source_id}


def is_iran_destination_country(country_name: str) -> bool:
    """Resolve the submitted display name through canonical country data."""
    normalized_name = country_name.strip().casefold()
    if not normalized_name:
        return False

    iran = db.session.query(Country).filter(Country.code == "IR").one_or_none()
    if iran is None:
        return False

    return normalized_name in {
        iran.name_en.strip().casefold(),
        iran.name_fa.strip().casefold(),
    }


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
            "origin_country_id": normalized["origin_country_id"],
            "origin_international_city_id": normalized["origin_international_city_id"],
            "origin_country": normalized["origin_country"],
            "origin_city_international": normalized["origin_city_international"],
            "origin_address_international": normalized["origin_address_international"],
            "dest_country_id": normalized["dest_country_id"],
            "dest_international_city_id": normalized["dest_international_city_id"],
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
            "origin_province_id": normalized.get("origin_province_id"),
            "origin_county_id": normalized.get("origin_county_id"),
            "origin_city_id": normalized.get("origin_city_id"),
        })

    return shipment_request_data


def build_shipment_request_payload(shipment_request: ShipmentRequest) -> dict[str, Any]:
    """Build the current public create response payload."""
    tracking_display = getattr(shipment_request, "tracking_code", None) or f"SR{shipment_request.id:06d}"
    return {
        "message": "درخواست شما ثبت شد. کارشناسان ما ظرف دو ساعت با شما تماس خواهند گرفت.",
        "id": shipment_request.id,
        "tracking_code": tracking_display,
        "request_transport_intent": (
            shipment_request.domestic_transport_method
            if shipment_request.shipping_type == "domestic"
            else shipment_request.international_transport_method
        ),
        "cargo_items": serialize_request_cargo_items(shipment_request),
    }


def _serialize_cargo_type(row: CargoType) -> dict[str, Any]:
    return {
        "public_id": row.public_id,
        "code": row.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
    }


def _serialize_uom(row: UnitOfMeasure) -> dict[str, Any]:
    return {
        "public_id": row.public_id,
        "code": row.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
        "symbol": row.symbol,
        "measurement_dimension": row.measurement_dimension,
    }


def serialize_request_cargo_item(item: RequestCargoItem) -> dict[str, Any]:
    return {
        "public_id": item.public_id,
        "position": item.position,
        "description": item.description,
        "cargo_type": _serialize_cargo_type(item.cargo_type) if item.cargo_type else None,
        "quantity": f"{item.quantity:.6f}" if item.quantity is not None else None,
        "uom": _serialize_uom(item.uom) if item.uom else None,
    }


def serialize_request_cargo_items(shipment_request: ShipmentRequest) -> list[dict[str, Any]]:
    return [serialize_request_cargo_item(item) for item in shipment_request.request_cargo_items]


def has_legacy_cargo(shipment_request: ShipmentRequest) -> bool:
    return any(
        value is not None and value != ""
        for value in (
            shipment_request.cargo_description,
            shipment_request.cargo_weight,
            shipment_request.cargo_volume,
            shipment_request.cargo_value,
        )
    )


def build_legacy_cargo_payload(shipment_request: ShipmentRequest) -> dict[str, Any]:
    return {
        "description": shipment_request.cargo_description,
        "weight": shipment_request.cargo_weight,
        "volume": shipment_request.cargo_volume,
        "value": shipment_request.cargo_value,
        "special_instructions": shipment_request.special_instructions,
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
    except Exception as exc:
        if isinstance(exc, SECURITY_FENCE_ERRORS):
            raise
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
        if isinstance(e, SECURITY_FENCE_ERRORS):
            raise
        current_app.logger.error(f"Error in gamification for request {shipment_request.id}: {e}")


def assign_request_with_referral(shipment_request: ShipmentRequest) -> None:
    """Stage referral assignment in the caller-owned transaction."""
    assigned_expert_id = referral_engine.auto_assign_request(shipment_request.id)
    if assigned_expert_id:
        current_app.logger.info(
            f"Request {shipment_request.id} assigned to expert {assigned_expert_id} via referral rules"
        )
    else:
        current_app.logger.info("No active experts available for request %s; status remains new", shipment_request.id)


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
