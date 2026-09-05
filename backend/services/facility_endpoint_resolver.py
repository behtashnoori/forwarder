"""Tenant-safe facility endpoint resolution for operational routes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from backend.extensions import db
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import City, Country, Province
from backend.services.location_resolver import ResolvedLocation, resolve_location
from backend.services.location_resolver import LocationResolutionError


@dataclass(frozen=True)
class ResolvedFacilityEndpoint:
    logistics_point: LogisticsPoint
    geography: ResolvedLocation

    def snapshot(self) -> dict[str, Any]:
        point = self.logistics_point
        global_point = point.global_point
        return {
            "endpoint_kind": "logistics_point",
            "logistics_point_public_id": point.public_id,
            "organization_local_code": point.immutable_code,
            "point_type": {
                "code": point.point_type.immutable_code,
                "fa_name": point.point_type.fa_name,
                "en_name": point.point_type.en_name,
            },
            "display_name": point.fa_name,
            "global_provenance": ({
                "public_id": global_point.public_id,
                "immutable_code": global_point.immutable_code,
            } if global_point else None),
            "canonical_geography": self.geography.snapshot(),
            "address": point.short_address,
        }


def _geographic_reference(point: LogisticsPoint) -> dict[str, int]:
    # Explicit governed FK precedence; never derive identity from labels or addresses.
    if point.city_id is not None:
        return {"source_type": "city", "source_id": point.city_id}
    if point.province_id is not None:
        return {"source_type": "province", "source_id": point.province_id}
    if point.country_id is not None:
        return {"source_type": "country", "source_id": point.country_id}
    raise LocationResolutionError("LOCATION_MAPPING_REQUIRED", "The logistics point has no governed geographic projection.")


def resolve_facility_endpoint(organization_id: int, public_id: Any) -> ResolvedFacilityEndpoint:
    if not isinstance(public_id, str) or not public_id.strip():
        raise LocationResolutionError("LOCATION_MAPPING_REQUIRED", "A logistics point public identity is required.")
    point = db.session.scalar(select(LogisticsPoint).where(LogisticsPoint.public_id == public_id))
    if point is None or point.organization_id != organization_id:
        raise LocationResolutionError("RESOURCE_NOT_FOUND", "The selected logistics point was not found.", 404)
    if not point.is_active or not point.point_type.is_active:
        raise LocationResolutionError("LOCATION_MAPPING_REQUIRED", "The selected logistics point is not active.")
    try:
        geography = resolve_location(_geographic_reference(point))
    except Exception as exc:
        if isinstance(exc, LocationResolutionError):
            raise
        raise LocationResolutionError("LOCATION_MAPPING_REQUIRED", "The logistics point has no valid governed geographic projection.") from exc
    return ResolvedFacilityEndpoint(point, geography)
