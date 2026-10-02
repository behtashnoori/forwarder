"""Shared route payload builder for expert console list and detail views.

Historically the expert console resolved only the domestic province/county/city
triplet, so every international shipment (all shipments to Iran included)
rendered as «نامشخص». This builder resolves both domestic and international
routes plus the structured Iran destination point, using one consistent shape.
"""
from __future__ import annotations

from typing import Any

from backend.extensions import db
from backend.models import City, Country, County, CustomsOffice, InternationalCity, IranPort, Province, ShipmentRequest
from backend.services.geography_presentation import name_fa as presented_name_fa

UNKNOWN = "نامشخص"


def _empty_endpoint() -> dict[str, Any]:
    return {
        "province": None,
        "county": None,
        "city": None,
        "country": None,
        "international_city": None,
        "address": None,
    }


def _international_endpoint(req: ShipmentRequest, side: str) -> dict[str, Any]:
    country_id = getattr(req, f"{side}_country_id")
    city_id = getattr(req, f"{side}_city_id")
    point_id = getattr(req, f"{side}_international_city_id")
    country_snapshot = getattr(req, f"{side}_country")
    place_snapshot = getattr(req, f"{side}_city_international")
    address = getattr(req, f"{side}_address_international")
    country = db.session.get(Country, country_id) if country_id else None
    city = db.session.get(City, city_id) if city_id else None
    point = db.session.get(InternationalCity, point_id) if point_id else None
    endpoint = _empty_endpoint()
    endpoint.update({
        "country": (country.name_fa if country else None) or country_snapshot or UNKNOWN,
        "international_city": (
            presented_name_fa(city) if city else
            (point.name_fa if point else None) or place_snapshot or UNKNOWN
        ),
        "address": address,
        "selection_kind": None,
        "selection_label": None,
        "reference_type": None,
        "source_id": None,
        "resolution_state": None,
    })
    if city and country and city.country_id == country.id:
        endpoint.update({
            "city": presented_name_fa(city),
            "selection_kind": "canonical_city",
            "selection_label": "مکان مرجع انتخاب‌شده",
            "reference_type": "city",
            "source_id": city.id,
            "resolution_state": "reference_selected",
        })
    elif point and country and point.country_id == country.id:
        is_physical = point.city_type in {"airport", "port"}
        endpoint.update({
            "selection_kind": "physical_reference" if is_physical else "legacy_reference",
            "selection_label": "مکان مرجع انتخاب‌شده" if is_physical else "مرجع تاریخی ثبت‌شده",
            "reference_type": point.city_type,
            "source_id": point.id,
            "resolution_state": "reference_selected" if is_physical else "legacy_reference",
        })
    elif country_id and place_snapshot:
        endpoint.update({
            "selection_kind": "declared",
            "selection_label": "محل اعلام‌شده مشتری؛ هنوز به مکان مرجع متصل نیست",
            "reference_type": None,
            "source_id": None,
            "resolution_state": "requires_expert_review",
        })
    else:
        endpoint.update({
            "selection_kind": "legacy_unstructured",
            "selection_label": "اطلاعات تاریخی درخواست",
            "resolution_state": "legacy_incomplete",
        })
    return endpoint


def build_iran_destination_payload(req: ShipmentRequest) -> dict[str, Any] | None:
    """Resolve the structured in-Iran destination point, or None when absent."""
    if not req.iran_dest_type:
        return None

    province = db.session.get(Province, req.iran_entry_province_id) if req.iran_entry_province_id else None
    label: str | None = None

    if req.iran_dest_type == "port":
        port = db.session.get(IranPort, req.iran_entry_port_id) if req.iran_entry_port_id else None
        label = (port.name_fa if port else None) or (req.iran_entry_port or None)
    elif req.iran_dest_type == "customs":
        office = db.session.get(CustomsOffice, req.iran_dest_customs_office_id) if req.iran_dest_customs_office_id else None
        label = office.name_fa if office else None
    elif req.iran_dest_type == "city":
        city = db.session.get(City, req.iran_dest_city_id) if req.iran_dest_city_id else None
        label = presented_name_fa(city) if city else None

    return {
        "type": req.iran_dest_type,
        "label": label,
        "province": presented_name_fa(province) if province else (req.iran_entry_province or None),
    }


def build_route_payload(req: ShipmentRequest) -> dict[str, Any]:
    """Build a unified route payload for both domestic and international shipments."""
    origin = _empty_endpoint()
    destination = _empty_endpoint()

    if req.shipping_type == "international":
        origin = _international_endpoint(req, "origin")
        destination = _international_endpoint(req, "dest")
    else:
        origin_province = db.session.get(Province, req.origin_province_id) if req.origin_province_id else None
        origin_county = db.session.get(County, req.origin_county_id) if req.origin_county_id else None
        origin_city = db.session.get(City, req.origin_city_id) if req.origin_city_id else None
        dest_province = db.session.get(Province, req.dest_province_id) if req.dest_province_id else None
        dest_county = db.session.get(County, req.dest_county_id) if req.dest_county_id else None
        dest_city = db.session.get(City, req.dest_city_id) if req.dest_city_id else None
        origin.update({
            "province": presented_name_fa(origin_province) if origin_province else UNKNOWN,
            "county": origin_county.name_fa if origin_county else UNKNOWN,
            "city": presented_name_fa(origin_city) if origin_city else UNKNOWN,
        })
        destination.update({
            "province": presented_name_fa(dest_province) if dest_province else UNKNOWN,
            "county": dest_county.name_fa if dest_county else UNKNOWN,
            "city": presented_name_fa(dest_city) if dest_city else UNKNOWN,
        })

    return {
        "shipping_type": req.shipping_type,
        "location_state": _location_state(req),
        "canonical_ids": {
            "origin_country_id": req.origin_country_id,
            "origin_international_city_id": req.origin_international_city_id,
            "origin_city_id": req.origin_city_id,
            "dest_country_id": req.dest_country_id,
            "dest_international_city_id": req.dest_international_city_id,
            "dest_city_id": req.dest_city_id,
        },
        "origin": origin,
        "destination": destination,
        "iran_destination": build_iran_destination_payload(req),
    }


def _location_state(req: ShipmentRequest) -> str:
    if req.shipping_type != "international":
        return "canonical"
    origin_endpoint = _international_endpoint(req, "origin")
    destination_endpoint = _international_endpoint(req, "dest")
    states = {origin_endpoint["resolution_state"], destination_endpoint["resolution_state"]}
    if "requires_expert_review" in states:
        return "customer_declared"
    if states == {"reference_selected"}:
        return "canonical"
    if "legacy_reference" in states and states <= {"reference_selected", "legacy_reference"}:
        return "canonical"
    origin_country = db.session.get(Country, req.origin_country_id) if req.origin_country_id else None
    dest_country = db.session.get(Country, req.dest_country_id) if req.dest_country_id else None
    def international_city_matches(country, city_id):
        # Read historical selections even after reference deactivation. Activity
        # is a write-time eligibility rule, not a reason to lose stored identity.
        city = db.session.get(InternationalCity, city_id) if city_id else None
        return bool(country and city and city.country_id == country.id)

    origin_complete = bool(origin_country and (
        (international_city_matches(origin_country, req.origin_international_city_id)
         if req.origin_international_city_id else bool(req.origin_province_id))
        if origin_country.code == "IR" else req.origin_international_city_id
    ))
    iran_destination_ids = (
        req.iran_entry_port_id,
        req.iran_dest_customs_office_id,
        req.iran_dest_city_id,
    )
    destination_complete = bool(dest_country and (
        (international_city_matches(dest_country, req.dest_international_city_id)
         if req.dest_international_city_id
         else sum(value is not None for value in iran_destination_ids) == 1)
        if dest_country.code == "IR" else req.dest_international_city_id
    ))
    if origin_complete and destination_complete:
        return "canonical"
    if req.origin_country_id or req.dest_country_id:
        return "legacy_incomplete"
    labels = [req.origin_country, req.origin_city_international, req.dest_country, req.dest_city_international]
    return "legacy_ambiguous" if all(labels) else "legacy_incomplete"
