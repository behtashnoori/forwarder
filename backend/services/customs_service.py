"""Validated customs master-data operations."""
from backend.extensions import db
from backend.models import (
    CUSTOMS_OFFICE_TYPES, PORT_CUSTOMS_RELATIONSHIP_TYPES,
    City, Country, County, CustomsOffice, IranPort, PortCustomsOffice, Province,
)


class CustomsValidationError(ValueError):
    pass


def _required(data, key):
    value = data.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise CustomsValidationError(f"{key} is required")
    return value.strip() if isinstance(value, str) else value


def _optional_bool(data, key, default):
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise CustomsValidationError(f"{key} must be a boolean")
    return value


def _validate_geography(country_id, province_id=None, county_id=None, city_id=None):
    country = db.session.get(Country, country_id)
    if country is None:
        raise CustomsValidationError("country_id is invalid")
    province = db.session.get(Province, province_id) if province_id else None
    county = db.session.get(County, county_id) if county_id else None
    city = db.session.get(City, city_id) if city_id else None
    if province_id and province is None:
        raise CustomsValidationError("province_id is invalid")
    if county_id and (county is None or province is None or county.province_id != province.id):
        raise CustomsValidationError("county does not belong to province")
    if city_id and (city is None or county is None or city.county_id != county.id or (province and city.province_id != province.id)):
        raise CustomsValidationError("city hierarchy is inconsistent")


def serialize_office(office):
    return {"id": office.id, "code": office.code, "name_fa": office.name_fa,
            "name_en": office.name_en, "customs_type": office.customs_type,
            "country_id": office.country_id, "province_id": office.province_id,
            "county_id": office.county_id, "city_id": office.city_id,
            "is_active": office.is_active}


def create_office(data):
    code = _required(data, "code").upper()
    customs_type = _required(data, "customs_type")
    if customs_type not in CUSTOMS_OFFICE_TYPES:
        raise CustomsValidationError("unsupported customs_type")
    country_id = _required(data, "country_id")
    _validate_geography(country_id, data.get("province_id"), data.get("county_id"), data.get("city_id"))
    if CustomsOffice.query.filter_by(code=code).first():
        raise CustomsValidationError("customs code already exists")
    office = CustomsOffice(code=code, name_fa=_required(data, "name_fa"), name_en=data.get("name_en"),
        customs_type=customs_type, country_id=country_id, province_id=data.get("province_id"),
        county_id=data.get("county_id"), city_id=data.get("city_id"), is_active=_optional_bool(data, "is_active", True))
    db.session.add(office); db.session.commit(); return office


def update_office(office, data):
    merged = {k: data.get(k, getattr(office, k)) for k in ("country_id", "province_id", "county_id", "city_id")}
    _validate_geography(**merged)
    if "customs_type" in data and data["customs_type"] not in CUSTOMS_OFFICE_TYPES:
        raise CustomsValidationError("unsupported customs_type")
    for key in ("name_fa", "name_en", "customs_type", "country_id", "province_id", "county_id", "city_id", "is_active"):
        if key in data: setattr(office, key, data[key])
    db.session.commit(); return office


def create_relationship(data):
    relation_type = _required(data, "relationship_type")
    if relation_type not in PORT_CUSTOMS_RELATIONSHIP_TYPES:
        raise CustomsValidationError("unsupported relationship_type")
    port_id, customs_id = _required(data, "port_id"), _required(data, "customs_office_id")
    if db.session.get(IranPort, port_id) is None or db.session.get(CustomsOffice, customs_id) is None:
        raise CustomsValidationError("port_id or customs_office_id is invalid")
    if PortCustomsOffice.query.filter_by(port_id=port_id, customs_office_id=customs_id, relationship_type=relation_type).first():
        raise CustomsValidationError("relationship already exists")
    relation = PortCustomsOffice(port_id=port_id, customs_office_id=customs_id,
        relationship_type=relation_type, is_primary=_optional_bool(data, "is_primary", False), is_active=True)
    db.session.add(relation); db.session.commit(); return relation
