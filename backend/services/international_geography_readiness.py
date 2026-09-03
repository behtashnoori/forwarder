"""Non-mutating readiness checks for governed international geography."""

from __future__ import annotations

import json
from pathlib import Path

from backend.models import Country, InternationalCity


_SNAPSHOT = Path(__file__).resolve().parents[1] / "reference_data" / "international-geography-v1.json"


def approved_snapshot() -> dict:
    """Load the checked-in input; this deliberately performs no network I/O."""
    return json.loads(_SNAPSHOT.read_text(encoding="utf-8"))


def validate_snapshot(snapshot: dict | None = None) -> list[str]:
    snapshot = snapshot or approved_snapshot()
    errors: list[str] = []
    if snapshot.get("country_authority") != "ISO 3166-1 alpha-2":
        errors.append("country authority must be ISO 3166-1 alpha-2")
    seen_codes: set[str] = set()
    seen_locations: set[tuple[str, str]] = set()
    for record in snapshot.get("records", []):
        country = record.get("country", {})
        code = country.get("code", "")
        if not isinstance(code, str) or len(code) != 2 or code != code.upper() or not code.isalpha():
            errors.append(f"invalid country code: {code!r}")
        if code in seen_codes:
            errors.append(f"duplicate country code: {code}")
        seen_codes.add(code)
        for location in record.get("locations", []):
            locode = location.get("un_locode", "")
            if not isinstance(locode, str) or len(locode) != 5 or not locode.isalnum() or locode[:2] != code:
                errors.append(f"invalid UN/LOCODE for {code}: {locode!r}")
            key = (code, locode)
            if key in seen_locations:
                errors.append(f"duplicate UN/LOCODE: {locode}")
            seen_locations.add(key)
    return errors


def readiness_report() -> dict:
    """Report existence separately from public-selector readiness.

    This is safe for tests, release diagnostics and operational inspection: it
    never writes reference rows and intentional deactivation is reported rather
    than repaired or treated as missing data.
    """
    snapshot = approved_snapshot()
    errors = validate_snapshot(snapshot)
    countries = []
    for record in snapshot["records"]:
        source = record["country"]
        country = Country.query.filter_by(code=source["code"]).one_or_none()
        location_rows = []
        for item in record["locations"]:
            row = None
            if country:
                row = InternationalCity.query.filter_by(country_id=country.id, un_locode=item["un_locode"]).one_or_none()
            location_rows.append({
                "un_locode": item["un_locode"],
                "exists": row is not None,
                "is_active": None if row is None else row.is_active,
                "selectable": bool(country and country.is_active and row and row.is_active),
                "country_match": bool(row and country and row.country_id == country.id),
            })
        countries.append({
            "code": source["code"],
            "exists": country is not None,
            "is_active": None if country is None else country.is_active,
            "selectable": bool(country and country.is_active and any(x["selectable"] for x in location_rows)),
            "locations": location_rows,
        })
    return {"dataset_id": snapshot["dataset_id"], "valid": not errors, "errors": errors, "countries": countries}
