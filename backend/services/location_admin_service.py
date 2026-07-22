"""Validated admin CRUD for origin/destination reference geography.

Covers the entities that back the shipment-request origin/destination pickers,
for both domestic (Province -> County -> City) and international
(Country -> InternationalCity) shipping, plus Iran entry ports (IranPort).

Rules mirror the existing customs master-data service:
  * geography is validated against existing parents; parents are never
    created implicitly,
  * codes are supplied by the admin, never generated from names or ids,
  * "delete" is a soft deactivation (is_active = False); rows are never
    physically removed.
"""
from backend.extensions import db
from backend.models import (
    City,
    Country,
    County,
    InternationalCity,
    IranPort,
    Province,
)

INTERNATIONAL_CITY_TYPES = frozenset({"city", "port", "airport"})
IRAN_PORT_TYPES = frozenset({"sea", "air", "land"})


class LocationValidationError(ValueError):
    """Raised when an admin location payload fails validation."""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _required_str(data, key, *, max_len=None):
    value = data.get(key)
    if value is None or not isinstance(value, str) or not value.strip():
        raise LocationValidationError(f"{key} is required")
    value = value.strip()
    if max_len is not None and len(value) > max_len:
        raise LocationValidationError(f"{key} must be at most {max_len} characters")
    return value


def _optional_str(data, key, current, *, max_len=None):
    if key not in data:
        return current
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise LocationValidationError(f"{key} must be text")
    value = value.strip()
    if not value:
        return None
    if max_len is not None and len(value) > max_len:
        raise LocationValidationError(f"{key} must be at most {max_len} characters")
    return value


def _optional_bool(data, key, current):
    if key not in data:
        return current
    value = data.get(key)
    if not isinstance(value, bool):
        raise LocationValidationError(f"{key} must be a boolean")
    return value


def _required_id(data, key):
    value = data.get(key)
    if value is None:
        raise LocationValidationError(f"{key} is required")
    if isinstance(value, bool) or not isinstance(value, int):
        raise LocationValidationError(f"{key} must be an integer id")
    return value


def _optional_id(data, key, current):
    if key not in data:
        return current
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise LocationValidationError(f"{key} must be an integer id")
    return value


def _lookup(model, entity_id, label):
    row = db.session.get(model, entity_id)
    if row is None:
        raise LocationValidationError(f"{label} is invalid")
    return row


# ---------------------------------------------------------------------------
# serializers
# ---------------------------------------------------------------------------
def serialize_province(row):
    return {
        "id": row.id,
        "name_fa": row.name_fa,
        "code": row.code,
        "country_id": row.country_id,
        "is_active": row.is_active,
    }


def serialize_county(row):
    return {
        "id": row.id,
        "name_fa": row.name_fa,
        "code": row.code,
        "province_id": row.province_id,
        "province_name": row.province.name_fa if row.province else None,
        "is_active": row.is_active,
    }


def serialize_city(row):
    return {
        "id": row.id,
        "name_fa": row.name_fa,
        "code": row.code,
        "county_id": row.county_id,
        "county_name": row.county.name_fa if row.county else None,
        "province_id": row.province_id,
        "province_name": row.province.name_fa if row.province else None,
        "is_active": row.is_active,
    }


def serialize_country(row):
    return {
        "id": row.id,
        "name_fa": row.name_fa,
        "name_en": row.name_en,
        "code": row.code,
        "is_active": row.is_active,
    }


def serialize_international_city(row):
    return {
        "id": row.id,
        "name_fa": row.name_fa,
        "name_en": row.name_en,
        "country_id": row.country_id,
        "country_name": row.country.name_fa if row.country else None,
        "city_type": row.city_type,
        "is_major_port": row.is_major_port,
        "is_major_airport": row.is_major_airport,
        "is_active": row.is_active,
    }


def serialize_iran_port(row):
    return {
        "id": row.id,
        "name_fa": row.name_fa,
        "name_en": row.name_en,
        "port_type": row.port_type,
        "province_id": row.province_id,
        "province_name": row.province.name_fa if row.province else None,
        "country_id": row.country_id,
        "is_major_port": row.is_major_port,
        "description": row.description,
        "is_active": row.is_active,
    }


# ---------------------------------------------------------------------------
# Province
# ---------------------------------------------------------------------------
def list_provinces(*, include_inactive=False):
    query = Province.query
    if not include_inactive:
        query = query.filter(Province.is_active.is_(True))
    return query.order_by(Province.name_fa).all()


def create_province(data):
    country_id = _optional_id(data, "country_id", None)
    if country_id is not None:
        _lookup(Country, country_id, "country_id")
    row = Province(
        name_fa=_required_str(data, "name_fa"),
        code=_optional_str(data, "code", None, max_len=10),
        country_id=country_id,
        is_active=_optional_bool(data, "is_active", True),
    )
    db.session.add(row)
    db.session.commit()
    return row


def update_province(row, data):
    if "name_fa" in data:
        row.name_fa = _required_str(data, "name_fa")
    row.code = _optional_str(data, "code", row.code, max_len=10)
    country_id = _optional_id(data, "country_id", row.country_id)
    if country_id is not None and country_id != row.country_id:
        _lookup(Country, country_id, "country_id")
    row.country_id = country_id
    row.is_active = _optional_bool(data, "is_active", row.is_active)
    db.session.commit()
    return row


# ---------------------------------------------------------------------------
# County
# ---------------------------------------------------------------------------
def list_counties(*, province_id=None, include_inactive=False):
    query = County.query
    if province_id is not None:
        query = query.filter(County.province_id == province_id)
    if not include_inactive:
        query = query.filter(County.is_active.is_(True))
    return query.order_by(County.name_fa).all()


def create_county(data):
    province_id = _required_id(data, "province_id")
    _lookup(Province, province_id, "province_id")
    row = County(
        name_fa=_required_str(data, "name_fa"),
        code=_optional_str(data, "code", None, max_len=64),
        province_id=province_id,
        is_active=_optional_bool(data, "is_active", True),
    )
    db.session.add(row)
    db.session.commit()
    return row


def update_county(row, data):
    if "name_fa" in data:
        row.name_fa = _required_str(data, "name_fa")
    row.code = _optional_str(data, "code", row.code, max_len=64)
    if "province_id" in data:
        province_id = _required_id(data, "province_id")
        _lookup(Province, province_id, "province_id")
        row.province_id = province_id
    row.is_active = _optional_bool(data, "is_active", row.is_active)
    db.session.commit()
    return row


# ---------------------------------------------------------------------------
# City
# ---------------------------------------------------------------------------
def list_cities(*, county_id=None, province_id=None, include_inactive=False):
    query = City.query
    if county_id is not None:
        query = query.filter(City.county_id == county_id)
    if province_id is not None:
        query = query.filter(City.province_id == province_id)
    if not include_inactive:
        query = query.filter(City.is_active.is_(True))
    return query.order_by(City.name_fa).all()


def create_city(data):
    county_id = _required_id(data, "county_id")
    county = _lookup(County, county_id, "county_id")
    row = City(
        name_fa=_required_str(data, "name_fa"),
        code=_optional_str(data, "code", None, max_len=64),
        county_id=county_id,
        # province is always derived from the county so the hierarchy stays consistent
        province_id=county.province_id,
        is_active=_optional_bool(data, "is_active", True),
    )
    db.session.add(row)
    db.session.commit()
    return row


def update_city(row, data):
    if "name_fa" in data:
        row.name_fa = _required_str(data, "name_fa")
    row.code = _optional_str(data, "code", row.code, max_len=64)
    if "county_id" in data:
        county_id = _required_id(data, "county_id")
        county = _lookup(County, county_id, "county_id")
        row.county_id = county_id
        row.province_id = county.province_id
    row.is_active = _optional_bool(data, "is_active", row.is_active)
    db.session.commit()
    return row


# ---------------------------------------------------------------------------
# Country
# ---------------------------------------------------------------------------
def list_countries(*, include_inactive=False):
    query = Country.query
    if not include_inactive:
        query = query.filter(Country.is_active.is_(True))
    return query.order_by(Country.name_fa).all()


def create_country(data):
    code = _required_str(data, "code", max_len=3).upper()
    if Country.query.filter_by(code=code).first():
        raise LocationValidationError("country code already exists")
    row = Country(
        name_fa=_required_str(data, "name_fa", max_len=100),
        name_en=_required_str(data, "name_en", max_len=100),
        code=code,
        is_active=_optional_bool(data, "is_active", True),
    )
    db.session.add(row)
    db.session.commit()
    return row


def update_country(row, data):
    if "name_fa" in data:
        row.name_fa = _required_str(data, "name_fa", max_len=100)
    if "name_en" in data:
        row.name_en = _required_str(data, "name_en", max_len=100)
    if "code" in data:
        code = _required_str(data, "code", max_len=3).upper()
        existing = Country.query.filter_by(code=code).first()
        if existing and existing.id != row.id:
            raise LocationValidationError("country code already exists")
        row.code = code
    row.is_active = _optional_bool(data, "is_active", row.is_active)
    db.session.commit()
    return row


# ---------------------------------------------------------------------------
# International city / port
# ---------------------------------------------------------------------------
def list_international_cities(*, country_id=None, include_inactive=False):
    query = InternationalCity.query
    if country_id is not None:
        query = query.filter(InternationalCity.country_id == country_id)
    if not include_inactive:
        query = query.filter(InternationalCity.is_active.is_(True))
    return query.order_by(InternationalCity.name_fa).all()


def _validate_city_type(data, current):
    city_type = data.get("city_type", current)
    if city_type not in INTERNATIONAL_CITY_TYPES:
        raise LocationValidationError("unsupported city_type")
    return city_type


def create_international_city(data):
    country_id = _required_id(data, "country_id")
    _lookup(Country, country_id, "country_id")
    row = InternationalCity(
        name_fa=_required_str(data, "name_fa", max_len=100),
        name_en=_required_str(data, "name_en", max_len=100),
        country_id=country_id,
        city_type=_validate_city_type(data, "city"),
        is_major_port=_optional_bool(data, "is_major_port", False),
        is_major_airport=_optional_bool(data, "is_major_airport", False),
        is_active=_optional_bool(data, "is_active", True),
    )
    db.session.add(row)
    db.session.commit()
    return row


def update_international_city(row, data):
    if "name_fa" in data:
        row.name_fa = _required_str(data, "name_fa", max_len=100)
    if "name_en" in data:
        row.name_en = _required_str(data, "name_en", max_len=100)
    if "country_id" in data:
        country_id = _required_id(data, "country_id")
        _lookup(Country, country_id, "country_id")
        row.country_id = country_id
    row.city_type = _validate_city_type(data, row.city_type)
    row.is_major_port = _optional_bool(data, "is_major_port", row.is_major_port)
    row.is_major_airport = _optional_bool(data, "is_major_airport", row.is_major_airport)
    row.is_active = _optional_bool(data, "is_active", row.is_active)
    db.session.commit()
    return row


# ---------------------------------------------------------------------------
# Iran entry port
# ---------------------------------------------------------------------------
def list_iran_ports(*, include_inactive=False):
    query = IranPort.query
    if not include_inactive:
        query = query.filter(IranPort.is_active.is_(True))
    return query.order_by(IranPort.name_fa).all()


def _validate_port_type(data, current):
    port_type = data.get("port_type", current)
    if port_type not in IRAN_PORT_TYPES:
        raise LocationValidationError("unsupported port_type")
    return port_type


def create_iran_port(data):
    province_id = _required_id(data, "province_id")
    _lookup(Province, province_id, "province_id")
    country_id = _optional_id(data, "country_id", None)
    if country_id is not None:
        _lookup(Country, country_id, "country_id")
    row = IranPort(
        name_fa=_required_str(data, "name_fa", max_len=100),
        name_en=_required_str(data, "name_en", max_len=100),
        port_type=_validate_port_type(data, "sea"),
        province_id=province_id,
        country_id=country_id,
        code=_optional_str(data, "code", None, max_len=64),
        is_major_port=_optional_bool(data, "is_major_port", True),
        description=_optional_str(data, "description", None),
        is_active=_optional_bool(data, "is_active", True),
    )
    db.session.add(row)
    db.session.commit()
    return row


def update_iran_port(row, data):
    if "name_fa" in data:
        row.name_fa = _required_str(data, "name_fa", max_len=100)
    if "name_en" in data:
        row.name_en = _required_str(data, "name_en", max_len=100)
    row.port_type = _validate_port_type(data, row.port_type)
    if "province_id" in data:
        province_id = _required_id(data, "province_id")
        _lookup(Province, province_id, "province_id")
        row.province_id = province_id
    if "country_id" in data:
        country_id = _optional_id(data, "country_id", row.country_id)
        if country_id is not None:
            _lookup(Country, country_id, "country_id")
        row.country_id = country_id
    row.code = _optional_str(data, "code", row.code, max_len=64)
    row.is_major_port = _optional_bool(data, "is_major_port", row.is_major_port)
    row.description = _optional_str(data, "description", row.description)
    row.is_active = _optional_bool(data, "is_active", row.is_active)
    db.session.commit()
    return row


# ---------------------------------------------------------------------------
# soft deactivate (shared)
# ---------------------------------------------------------------------------
def deactivate(row):
    row.is_active = False
    db.session.commit()
    return row
