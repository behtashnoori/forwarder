"""Canonical governed location resolution shared by requests and operations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import or_, select

from backend.extensions import db
from backend.models import (
    City,
    Country,
    County,
    CustomsOffice,
    InternationalCity,
    IranPort,
    PortLocation,
    Province,
)
from backend.operational_models import CanonicalLocation


class LocationResolutionError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass(frozen=True)
class ResolvedLocation:
    canonical_location: CanonicalLocation
    source_type: str
    source_id: int
    location_type: str
    display_label: str
    country_id: int | None
    country_code: str | None
    country_name: str | None
    province_id: int | None = None
    province_name: str | None = None
    county_id: int | None = None
    county_name: str | None = None
    city_id: int | None = None
    city_name: str | None = None
    operational_metadata: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "canonical_location_id": self.canonical_location.id,
            "canonical_reference": {"source_type": self.source_type, "source_id": self.source_id},
            "display_name": self.display_label,
            "location_type": self.location_type,
            "country": (
                {"id": self.country_id, "code": self.country_code, "name": self.country_name}
                if self.country_id is not None else None
            ),
            "country_code": self.country_code,
            "province": (
                {"id": self.province_id, "name": self.province_name}
                if self.province_id is not None else None
            ),
            "county": (
                {"id": self.county_id, "name": self.county_name}
                if self.county_id is not None else None
            ),
            "city": (
                {"id": self.city_id, "name": self.city_name}
                if self.city_id is not None else None
            ),
            "operational_point": self.operational_metadata,
            "verification_state": self.canonical_location.verification_state,
        }


def _eligible(row: Any) -> bool:
    today = date.today()
    return bool(
        getattr(row, "is_active", False)
        and (getattr(row, "effective_from", None) is None or row.effective_from <= today)
        and (getattr(row, "effective_to", None) is None or row.effective_to >= today)
    )


def _required(model, row_id: int, source_type: str):
    row = db.session.get(model, row_id)
    if row is None:
        raise LocationResolutionError("RESOURCE_NOT_FOUND", "The selected location was not found.", 404)
    if not _eligible(row):
        raise LocationResolutionError("LOCATION_MAPPING_REQUIRED", "The selected location is not eligible.")
    return row


def _country(country_id: int | None) -> Country | None:
    if country_id is None:
        return None
    return _required(Country, country_id, "country")


def _province(province_id: int | None) -> Province | None:
    if province_id is None:
        return None
    return _required(Province, province_id, "province")


def _canonical(source_type: str, source_id: int, location_type: str, label: str, country_code: str | None):
    row = db.session.scalar(select(CanonicalLocation).where(
        CanonicalLocation.source_type == source_type,
        CanonicalLocation.source_id == source_id,
    ))
    if row is None:
        row = CanonicalLocation(
            source_type=source_type,
            source_id=source_id,
            location_type=location_type,
            display_name=label,
            country_code=country_code,
            verification_state="verified",
        )
        db.session.add(row)
        db.session.flush()
    return row


def resolve_location(
    reference: dict[str, Any],
    *,
    expected_country_id: int | None = None,
    expected_province_id: int | None = None,
) -> ResolvedLocation:
    """Resolve one typed source and fail closed on invalid governed ancestry."""
    source_type, source_id = reference.get("source_type"), reference.get("source_id")
    if source_type not in {"province", "city", "country", "international_city", "iran_port", "customs_office"} or not isinstance(source_id, int) or isinstance(source_id, bool):
        raise LocationResolutionError("LOCATION_MAPPING_REQUIRED", "A supported location source_type and numeric source_id are required.")

    province = county = country = None
    city_id = city_name = None
    metadata = None
    if source_type == "country":
        source = _required(Country, source_id, source_type)
        country, location_type = source, "country"
    elif source_type == "province":
        source = _required(Province, source_id, source_type)
        province, country, location_type = source, _country(source.country_id), "province"
    elif source_type == "city":
        source = _required(City, source_id, source_type)
        province = _province(source.province_id)
        county = _required(County, source.county_id, "county")
        if county.province_id != province.id:
            raise LocationResolutionError("LOCATION_ANCESTRY_MISMATCH", "City ancestry is inconsistent.")
        country, location_type = _country(province.country_id), "city"
        city_id, city_name = source.id, source.name_fa
    elif source_type == "international_city":
        source = _required(InternationalCity, source_id, source_type)
        country, location_type = _country(source.country_id), "city"
        city_id, city_name = source.id, source.name_fa
        metadata = {"city_type": source.city_type}
    elif source_type == "iran_port":
        source = _required(IranPort, source_id, source_type)
        province, country = _province(source.province_id), _country(source.country_id)
        physical = db.session.scalars(select(PortLocation).where(
            PortLocation.port_id == source.id,
            PortLocation.is_active.is_(True),
            PortLocation.location_status == "confirmed",
        )).all()
        if len(physical) != 1 or physical[0].province_id != source.province_id or physical[0].country_id != source.country_id:
            raise LocationResolutionError("LOCATION_MAPPING_REQUIRED", "The selected port lacks unambiguous confirmed ancestry.")
        location_type = "port"
        metadata = {"port_type": source.port_type, "port_location_id": physical[0].id}
    else:
        source = _required(CustomsOffice, source_id, source_type)
        if source.province_id is None:
            raise LocationResolutionError("LOCATION_MAPPING_REQUIRED", "The selected customs office lacks governed province ancestry.")
        province, country = _province(source.province_id), _country(source.country_id)
        if province.country_id != source.country_id:
            raise LocationResolutionError("LOCATION_ANCESTRY_MISMATCH", "Customs ancestry is inconsistent.")
        if source.county_id is not None:
            county = _required(County, source.county_id, "county")
            if county.province_id != province.id:
                raise LocationResolutionError("LOCATION_ANCESTRY_MISMATCH", "Customs ancestry is inconsistent.")
        if source.city_id is not None:
            city = _required(City, source.city_id, "city")
            if city.province_id != province.id or (county is not None and city.county_id != county.id):
                raise LocationResolutionError("LOCATION_ANCESTRY_MISMATCH", "Customs ancestry is inconsistent.")
            city_id, city_name = city.id, city.name_fa
        location_type = "customs"
        metadata = {"customs_type": source.customs_type}

    if expected_country_id is not None and (country is None or country.id != expected_country_id):
        raise LocationResolutionError("LOCATION_ANCESTRY_MISMATCH", "The selected location does not belong to the selected country.")
    if expected_province_id is not None and (province is None or province.id != expected_province_id):
        raise LocationResolutionError("LOCATION_ANCESTRY_MISMATCH", "The selected location does not belong to the selected province.")

    label = str(source.name_fa)
    canonical = _canonical(source_type, source.id, location_type, label, country.code if country else None)
    return ResolvedLocation(
        canonical, source_type, source.id, location_type, label,
        country.id if country else None, country.code if country else None,
        country.name_fa if country else None,
        province.id if province else None, province.name_fa if province else None,
        county.id if county else None, county.name_fa if county else None,
        city_id, city_name, metadata,
    )


def iran_destination_results(q: str | None = None, source_type: str | None = None, province_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Return the bounded eligible projection; invalid master data is omitted."""
    type_map = {"city": (City, "city"), "port": (IranPort, "iran_port"), "customs": (CustomsOffice, "customs_office")}
    selected = [source_type] if source_type else list(type_map)
    if any(item not in type_map for item in selected):
        raise LocationResolutionError("VALIDATION_FAILED", "Unsupported Iran destination type.", 400)
    iran = db.session.scalar(select(Country).where(Country.code == "IR", Country.is_active.is_(True)))
    if iran is None:
        return []
    results = []
    for public_type in selected:
        model, canonical_type = type_map[public_type]
        query = select(model).where(model.is_active.is_(True))
        if q:
            pattern = f"%{q.strip()}%"
            names = [model.name_fa.ilike(pattern)]
            if hasattr(model, "name_en"):
                names.append(model.name_en.ilike(pattern))
            query = query.where(or_(*names))
        if province_id is not None:
            query = query.where(model.province_id == province_id)
        for row in db.session.scalars(query.order_by(model.name_fa, model.id).limit(limit)).all():
            try:
                resolved = resolve_location({"source_type": canonical_type, "source_id": row.id}, expected_country_id=iran.id)
            except LocationResolutionError:
                continue
            label = f"{resolved.display_label} — {public_type} — {resolved.province_name}"
            results.append({
                "identity": {"type": public_type, "id": row.id},
                "label": label,
                "province": {"id": resolved.province_id, "name": resolved.province_name},
                "secondary_label": f"{public_type} — {resolved.province_name}",
            })
    return sorted(results, key=lambda item: (item["label"], item["identity"]["id"]))[:limit]
