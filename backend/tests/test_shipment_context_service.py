"""Contract tests for the read-only ShipmentRequest context projection."""
from __future__ import annotations

from datetime import date, datetime
import json

from sqlalchemy import inspect

from backend.models import ShipmentRequest
from backend.services.shipment_context_service import build_shipment_request_context


def _request(**overrides) -> ShipmentRequest:
    values = {
        "id": 42,
        "contact_phone": "+980000000000",
        "status": "in_progress",
        "status_request_status": "closed",
        "shipping_type": "international",
        "origin_country": "Iran",
        "origin_city_international": "Tehran",
        "dest_country": "Germany",
        "dest_city_international": "Hamburg",
        "iran_entry_port": "Bandar Abbas",
        "iran_entry_port_id": 71,
        "iran_entry_province": "Hormozgan",
        "iran_entry_province_id": 72,
        "international_transport_method": "sea",
        "cargo_description": "Synthetic machinery",
        "cargo_weight": 1250.5,
        "cargo_volume": 8.25,
        "created_at": datetime(2026, 7, 13, 8, 30, 0),
        "ready_at": datetime(2026, 7, 14, 9, 0, 0),
        "pickup_date": date(2026, 7, 15),
        "priority": "high",
        "has_unread_for_assignee": False,
    }
    values.update(overrides)
    return ShipmentRequest(**values)


def _by_field(items: list[dict]) -> dict[str, dict]:
    return {item["field"]: item for item in items}


def test_v1_envelope_and_deterministic_strict_json_contract() -> None:
    shipment = _request()

    first = build_shipment_request_context(shipment)
    second = build_shipment_request_context(shipment)

    assert list(first) == [
        "contract",
        "aggregate",
        "confirmed",
        "missing",
        "ambiguous",
        "excluded",
        "unavailable",
        "limitations",
    ]
    assert first["contract"] == {
        "name": "shipment_request_context",
        "version": "1.0",
        "profile": "operational_minimum_v1",
        "mode": "read_only",
        "deterministic": True,
        "classification": "confidential",
    }
    assert first["aggregate"] == {"type": "ShipmentRequest", "id": 42}
    assert first == second
    assert json.dumps(first, allow_nan=False, sort_keys=True) == json.dumps(
        second, allow_nan=False, sort_keys=True
    )


def test_status_is_canonical_and_legacy_status_is_excluded() -> None:
    context = build_shipment_request_context(_request())
    confirmed = _by_field(context["confirmed"])
    excluded = _by_field(context["excluded"])

    assert confirmed["shipment.status"]["value"] == "in_progress"
    assert confirmed["shipment.status"]["source"] == "ShipmentRequest.status"
    assert "legacy_status" in excluded["status_request_status"]["reason"]
    assert "closed" not in json.dumps(context)


def test_international_applicability_classifies_values_and_excludes_domestic_fields() -> None:
    context = build_shipment_request_context(_request())
    confirmed = _by_field(context["confirmed"])
    excluded = _by_field(context["excluded"])

    assert confirmed["route.origin.country"]["value"] == "Iran"
    assert confirmed["route.iran_entry_port_id"]["value"] == 71
    assert confirmed["route.iran_entry_province_id"]["value"] == 72
    assert confirmed["transport.international_method"]["value"] == "sea"
    assert excluded["route.origin.province_id"]["reason"] == (
        "not_applicable_for_international_shipment"
    )
    assert "route.origin.province_id" not in _by_field(context["missing"])


def test_domestic_applicability_and_cross_mode_values_are_ambiguous() -> None:
    shipment = _request(
        shipping_type="domestic",
        origin_province_id=1,
        dest_province_id=2,
        domestic_transport_method="road",
    )
    context = build_shipment_request_context(shipment)
    confirmed = _by_field(context["confirmed"])
    excluded = _by_field(context["excluded"])

    assert confirmed["route.origin.province_id"]["value"] == 1
    assert confirmed["transport.domestic_method"]["value"] == "road"
    assert excluded["route.origin.country"]["reason"] == "not_applicable_for_domestic_shipment"
    assert context["ambiguous"] == [
        {
            "field": "route.international",
            "reason": "values_conflict_with_domestic_shipping_type",
            "candidates": [
                {"value": "Iran", "source": "ShipmentRequest.origin_country"},
                {
                    "value": "Tehran",
                    "source": "ShipmentRequest.origin_city_international",
                },
                {"value": "Germany", "source": "ShipmentRequest.dest_country"},
                {
                    "value": "Hamburg",
                    "source": "ShipmentRequest.dest_city_international",
                },
                {
                    "value": "sea",
                    "source": "ShipmentRequest.international_transport_method",
                },
            ],
        }
    ]


def test_missing_values_keep_classification_and_untrusted_text_is_labeled() -> None:
    context = build_shipment_request_context(
        _request(cargo_description="  ", cargo_volume=None, delivery_date=None)
    )
    missing = _by_field(context["missing"])

    assert missing["cargo.description"] == {
        "field": "cargo.description",
        "source": "ShipmentRequest.cargo_description",
        "classification": "operational_confidential",
        "content_trust": "untrusted_user_text",
        "reason": "not_provided",
    }
    assert missing["cargo.volume"]["reason"] == "not_provided"
    assert missing["dates.delivery"]["reason"] == "not_provided"


def test_privacy_canaries_relationships_and_attachment_content_never_leak() -> None:
    canaries = {
        "contact_phone": "CANARY-PHONE",
        "customer_first_name": "CANARY-FIRST",
        "customer_last_name": "CANARY-LAST",
        "origin_address_international": "CANARY-ORIGIN-ADDRESS",
        "dest_address_international": "CANARY-DEST-ADDRESS",
        "cargo_value": 987654321.25,
        "estimated_value": 123456789.5,
        "special_instructions": "CANARY-SECRET-INSTRUCTIONS",
        "request_user_id": 99101,
        "assigned_to": 99102,
        "customer_id": 99103,
        "gamification_customer_id": 99104,
        "tracking_code": "CANARY-TRACKING",
    }
    context = build_shipment_request_context(_request(**canaries))
    serialized = json.dumps(context, sort_keys=True)

    for value in canaries.values():
        assert str(value) not in serialized
    assert _by_field(context["excluded"])["expert_messages"]["reason"] == (
        "related_raw_message_content"
    )
    unavailable = _by_field(context["unavailable"])
    assert unavailable["attachments"]["availability"] == "not_supported"
    assert unavailable["correspondence_provenance"]["reason"] == "not_supported"
    assert "no_attachment_or_correspondence_content" in context["limitations"]


def test_nonfinite_numbers_become_missing_and_strict_json_safe() -> None:
    context = build_shipment_request_context(
        _request(cargo_weight=float("nan"), cargo_volume=float("inf"))
    )
    missing = _by_field(context["missing"])

    assert missing["cargo.weight"]["reason"] == "not_provided"
    assert missing["cargo.volume"]["reason"] == "not_provided"
    json.dumps(context, allow_nan=False)


def test_builder_does_not_mutate_or_attach_transient_aggregate() -> None:
    shipment = _request()
    before = dict(shipment.__dict__)
    assert inspect(shipment).transient

    build_shipment_request_context(shipment)

    assert shipment.__dict__ == before
    assert inspect(shipment).transient
