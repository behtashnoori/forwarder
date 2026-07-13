"""Build the deterministic, read-only ShipmentRequest context contract.

The v1 contract is an allow-listed projection of scalar ``ShipmentRequest``
facts.  It performs no queries, writes, relationship traversal, or inference.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
from typing import Any, Literal

from backend.models import ShipmentRequest


CONTRACT_NAME = "shipment_request_context"
CONTRACT_VERSION = "1.0"
CONTRACT_PROFILE = "operational_minimum_v1"
SOURCE_AGGREGATE = "ShipmentRequest"

Applicability = Literal["all", "domestic", "international"]


@dataclass(frozen=True)
class ContextField:
    """An allow-listed v1 field in stable contract order."""

    field: str
    attribute: str
    classification: str = "operational_confidential"
    content_trust: str = "trusted_structured"
    applies_to: Applicability = "all"


_CONTEXT_FIELDS: tuple[ContextField, ...] = (
    ContextField("shipment.shipping_type", "shipping_type", classification="operational"),
    ContextField("route.origin.province_id", "origin_province_id", applies_to="domestic"),
    ContextField("route.origin.county_id", "origin_county_id", applies_to="domestic"),
    ContextField("route.origin.city_id", "origin_city_id", applies_to="domestic"),
    ContextField("route.destination.province_id", "dest_province_id", applies_to="domestic"),
    ContextField("route.destination.county_id", "dest_county_id", applies_to="domestic"),
    ContextField("route.destination.city_id", "dest_city_id", applies_to="domestic"),
    ContextField("route.origin.country", "origin_country", applies_to="international"),
    ContextField("route.origin.city", "origin_city_international", applies_to="international"),
    ContextField("route.destination.country", "dest_country", applies_to="international"),
    ContextField("route.destination.city", "dest_city_international", applies_to="international"),
    ContextField("route.iran_entry_port", "iran_entry_port", applies_to="international"),
    ContextField("route.iran_entry_port_id", "iran_entry_port_id", applies_to="international"),
    ContextField("route.iran_entry_province", "iran_entry_province", applies_to="international"),
    ContextField(
        "route.iran_entry_province_id",
        "iran_entry_province_id",
        applies_to="international",
    ),
    ContextField("transport.domestic_method", "domestic_transport_method", applies_to="domestic"),
    ContextField(
        "transport.international_method",
        "international_transport_method",
        applies_to="international",
    ),
    ContextField("transport.preference", "transport_method_preference"),
    ContextField(
        "cargo.description",
        "cargo_description",
        content_trust="untrusted_user_text",
    ),
    ContextField("cargo.weight", "cargo_weight"),
    ContextField("cargo.volume", "cargo_volume"),
    ContextField("dates.created_at", "created_at"),
    ContextField("dates.ready_at", "ready_at"),
    ContextField("dates.pickup", "pickup_date"),
    ContextField("dates.delivery", "delivery_date"),
    ContextField("operations.priority", "priority"),
    ContextField("operations.sla_due_at", "sla_due_at"),
    ContextField("operations.last_customer_touch_at", "last_customer_touch_at"),
    ContextField("operations.has_unread_for_assignee", "has_unread_for_assignee"),
)

_EXCLUDED_FIELDS: tuple[tuple[str, str], ...] = (
    ("status_request_status", "legacy_status; ShipmentRequest.status_is_canonical"),
    ("tracking_code", "public_identifier_not_required"),
    ("transport_method", "legacy_transport_label_not_reconciled_in_v1"),
    ("contact_phone", "direct_contact_data"),
    ("customer_first_name", "personal_data_not_required"),
    ("customer_last_name", "personal_data_not_required"),
    ("origin_address_international", "precise_address"),
    ("dest_address_international", "precise_address"),
    ("cargo_value", "commercially_sensitive"),
    ("estimated_value", "commercially_sensitive"),
    ("special_instructions", "unbounded_sensitive_free_text"),
    ("request_user_id", "internal_identity"),
    ("assigned_to", "internal_identity"),
    ("customer_id", "internal_relationship"),
    ("gamification_customer_id", "internal_relationship"),
    ("logs", "related_free_text_and_network_metadata"),
    ("expert_logs", "related_free_text_actor_and_network_metadata"),
    ("expert_messages", "related_raw_message_content"),
    ("expert_notifications", "related_notification_content"),
    ("assigned_expert", "related_actor_identity"),
    ("customer", "related_personal_and_commercial_data"),
    ("gamification_customer", "related_personal_data"),
)

_UNAVAILABLE_CAPABILITIES: tuple[tuple[str, str], ...] = (
    ("attachments", "not_supported_on_shipment_request"),
    ("correspondence_provenance", "not_supported"),
    ("cargo.weight_unit", "not_stored"),
    ("cargo.volume_unit", "not_stored"),
    ("shipment.source_revision", "not_stored"),
    ("shipment.incoterm", "not_stored"),
    ("shipment.partner_forwarder", "not_stored"),
)


def build_shipment_request_context(shipment_request: ShipmentRequest) -> dict[str, Any]:
    """Return a stable JSON-safe v1 snapshot without mutating the aggregate."""
    shipping_type = _normalized_string(getattr(shipment_request, "shipping_type", None))
    confirmed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    excluded = [
        {"field": field, "reason": reason}
        for field, reason in _EXCLUDED_FIELDS
    ]

    # This is the only lifecycle state in the contract.  The legacy
    # status_request_status column is always excluded above.
    _classify_field(
        ContextField("shipment.status", "status", classification="operational"),
        shipment_request,
        confirmed,
        missing,
    )

    for spec in _CONTEXT_FIELDS:
        if spec.applies_to != "all" and spec.applies_to != shipping_type:
            excluded.append(
                {
                    "field": spec.field,
                    "reason": f"not_applicable_for_{shipping_type or 'unknown'}_shipment",
                }
            )
            continue
        _classify_field(spec, shipment_request, confirmed, missing)

    return {
        "contract": {
            "name": CONTRACT_NAME,
            "version": CONTRACT_VERSION,
            "profile": CONTRACT_PROFILE,
            "mode": "read_only",
            "deterministic": True,
            "classification": "confidential",
        },
        "aggregate": {
            "type": SOURCE_AGGREGATE,
            "id": _json_value(shipment_request.id),
        },
        "confirmed": confirmed,
        "missing": missing,
        "ambiguous": _build_ambiguities(shipment_request, shipping_type),
        "excluded": excluded,
        "unavailable": [
            {"field": field, "availability": "not_supported", "reason": reason}
            for field, reason in _UNAVAILABLE_CAPABILITIES
        ],
        "limitations": [
            "read_only_snapshot",
            "shipment_request_allow_list_only",
            "no_related_records_or_relationship_traversal",
            "no_attachment_or_correspondence_content",
            "no_units_or_values_inferred",
            "not_authoritative_for_writes",
        ],
    }


def _classify_field(
    spec: ContextField,
    shipment_request: ShipmentRequest,
    confirmed: list[dict[str, Any]],
    missing: list[dict[str, Any]],
) -> None:
    raw_value = getattr(shipment_request, spec.attribute, None)
    value = _json_value(raw_value)
    base = {
        "field": spec.field,
        "source": f"{SOURCE_AGGREGATE}.{spec.attribute}",
        "classification": spec.classification,
        "content_trust": spec.content_trust,
    }
    if _is_missing(value):
        missing.append({**base, "reason": "not_provided"})
    else:
        confirmed.append({**base, "value": value})


def _build_ambiguities(
    shipment_request: ShipmentRequest,
    shipping_type: str | None,
) -> list[dict[str, Any]]:
    ambiguous: list[dict[str, Any]] = []
    if shipping_type not in {"domestic", "international"}:
        ambiguous.append(
            {
                "field": "shipment.shipping_type",
                "reason": "unsupported_shipping_type",
                "candidates": [_candidate("shipping_type", shipping_type)],
            }
        )
        return ambiguous

    other_mode_attributes = (
        (
            "route.international",
            (
                "origin_country",
                "origin_city_international",
                "dest_country",
                "dest_city_international",
                "international_transport_method",
            ),
        )
        if shipping_type == "domestic"
        else (
            "route.domestic",
            (
                "origin_province_id",
                "origin_county_id",
                "origin_city_id",
                "dest_province_id",
                "dest_county_id",
                "dest_city_id",
                "domestic_transport_method",
            ),
        )
    )
    field, attributes = other_mode_attributes
    unexpected = [
        _candidate(attribute, _json_value(getattr(shipment_request, attribute, None)))
        for attribute in attributes
        if not _is_missing(_json_value(getattr(shipment_request, attribute, None)))
    ]
    if unexpected:
        ambiguous.append(
            {
                "field": field,
                "reason": f"values_conflict_with_{shipping_type}_shipping_type",
                "candidates": unexpected,
            }
        )
    return ambiguous


def _candidate(attribute: str, value: Any) -> dict[str, Any]:
    return {
        "value": value,
        "source": f"{SOURCE_AGGREGATE}.{attribute}",
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "__int__") and not isinstance(value, complex):
        return int(value)
    return str(value)


def _normalized_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())
