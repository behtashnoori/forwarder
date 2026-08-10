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
        label = city.name_fa if city else None

    return {
        "type": req.iran_dest_type,
        "label": label,
        "province": province.name_fa if province else (req.iran_entry_province or None),
    }


def build_route_payload(req: ShipmentRequest) -> dict[str, Any]:
    """Build a unified route payload for both domestic and international shipments."""
    origin = _empty_endpoint()
    destination = _empty_endpoint()

    if req.shipping_type == "international":
        origin_country = db.session.get(Country, req.origin_country_id) if req.origin_country_id else None
        origin_city = db.session.get(InternationalCity, req.origin_international_city_id) if req.origin_international_city_id else None
        dest_country = db.session.get(Country, req.dest_country_id) if req.dest_country_id else None
        dest_city = db.session.get(InternationalCity, req.dest_international_city_id) if req.dest_international_city_id else None
        origin.update({
            "country": (origin_country.name_fa if origin_country else None) or req.origin_country or UNKNOWN,
            "international_city": (origin_city.name_fa if origin_city else None) or req.origin_city_international or UNKNOWN,
            "address": req.origin_address_international,
        })
        destination.update({
            "country": (dest_country.name_fa if dest_country else None) or req.dest_country or UNKNOWN,
            "international_city": (dest_city.name_fa if dest_city else None) or req.dest_city_international or UNKNOWN,
            "address": req.dest_address_international,
        })
    else:
        origin_province = db.session.get(Province, req.origin_province_id) if req.origin_province_id else None
        origin_county = db.session.get(County, req.origin_county_id) if req.origin_county_id else None
        origin_city = db.session.get(City, req.origin_city_id) if req.origin_city_id else None
        dest_province = db.session.get(Province, req.dest_province_id) if req.dest_province_id else None
        dest_county = db.session.get(County, req.dest_county_id) if req.dest_county_id else None
        dest_city = db.session.get(City, req.dest_city_id) if req.dest_city_id else None
        origin.update({
            "province": origin_province.name_fa if origin_province else UNKNOWN,
            "county": origin_county.name_fa if origin_county else UNKNOWN,
            "city": origin_city.name_fa if origin_city else UNKNOWN,
        })
        destination.update({
            "province": dest_province.name_fa if dest_province else UNKNOWN,
            "county": dest_county.name_fa if dest_county else UNKNOWN,
            "city": dest_city.name_fa if dest_city else UNKNOWN,
        })

    return {
        "shipping_type": req.shipping_type,
        "location_state": _location_state(req),
        "canonical_ids": {
            "origin_country_id": req.origin_country_id,
            "origin_international_city_id": req.origin_international_city_id,
            "dest_country_id": req.dest_country_id,
            "dest_international_city_id": req.dest_international_city_id,
        },
        "origin": origin,
        "destination": destination,
        "iran_destination": build_iran_destination_payload(req),
    }


def _location_state(req: ShipmentRequest) -> str:
    if req.shipping_type != "international":
        return "canonical"
    origin_country = db.session.get(Country, req.origin_country_id) if req.origin_country_id else None
    dest_country = db.session.get(Country, req.dest_country_id) if req.dest_country_id else None
    origin_complete = bool(origin_country and (
        req.origin_province_id if origin_country.code == "IR" else req.origin_international_city_id
    ))
    iran_destination_ids = (
        req.iran_entry_port_id,
        req.iran_dest_customs_office_id,
        req.iran_dest_city_id,
    )
    destination_complete = bool(dest_country and (
        sum(value is not None for value in iran_destination_ids) == 1
        if dest_country.code == "IR" else req.dest_international_city_id
    ))
    if origin_complete and destination_complete:
        return "canonical"
    if req.origin_country_id or req.dest_country_id:
        return "legacy_incomplete"
    labels = [req.origin_country, req.origin_city_international, req.dest_country, req.dest_city_international]
    return "legacy_ambiguous" if all(labels) else "legacy_incomplete"
