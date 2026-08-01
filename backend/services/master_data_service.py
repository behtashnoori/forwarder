"""Reusable governance rules for canonical master-data resources."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm.exc import StaleDataError

from backend.extensions import db
from backend.models import CargoType, MASTER_DATA_DIMENSIONS, ServiceType, UnitOfMeasure


class MasterDataValidationError(ValueError):
    pass


class VersionConflictError(ValueError):
    pass


RESOURCES = {
    "cargo-types": CargoType,
    "service-types": ServiceType,
    "units-of-measure": UnitOfMeasure,
}
COMMON_CREATE_FIELDS = {"immutable_code", "fa_name", "en_name", "description", "display_order", "is_active"}
COMMON_UPDATE_FIELDS = {"immutable_code", "fa_name", "en_name", "description", "display_order", "version"}
RESOURCE_FIELDS = {
    "cargo-types": {"parent_id"},
    "service-types": set(),
    "units-of-measure": {"symbol", "measurement_dimension"},
}


def model_for(resource: str):
    return RESOURCES.get(resource)


def serialize(row):
    value = {
        "public_id": row.public_id,
        "immutable_code": row.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
        "description": row.description,
        "display_order": row.display_order,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "version": row.version,
    }
    if isinstance(row, CargoType):
        value["parent_id"] = row.parent.public_id if row.parent else None
    if isinstance(row, UnitOfMeasure):
        value.update(symbol=row.symbol, measurement_dimension=row.measurement_dimension)
    return value


def _required_text(data, key, *, max_length):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MasterDataValidationError(f"{key} is required")
    value = value.strip()
    if len(value) > max_length:
        raise MasterDataValidationError(f"{key} must be at most {max_length} characters")
    return value


def _optional_text(data, key, current=None):
    if key not in data:
        return current
    value = data[key]
    if value is None:
        return None
    if not isinstance(value, str):
        raise MasterDataValidationError(f"{key} must be text")
    return value.strip() or None


def _parent(data, row=None):
    if "parent_id" not in data:
        return row.parent if row is not None else None
    public_id = data.get("parent_id")
    if public_id is None:
        return None
    parent = CargoType.query.filter_by(public_id=public_id).first()
    if parent is None:
        raise MasterDataValidationError("parent_id is invalid")
    if not parent.is_active:
        raise MasterDataValidationError("parent must be active")
    cursor = parent
    while cursor is not None:
        if row is not None and cursor.id == row.id:
            raise MasterDataValidationError("cargo type hierarchy cannot contain a cycle")
        cursor = cursor.parent
    return parent


def create(resource, data):
    model = model_for(resource)
    if model is None:
        raise MasterDataValidationError("unknown resource")
    _validate_fields(resource, data, creating=True)
    code = _required_text(data, "immutable_code", max_length=64).upper()
    if model.query.filter_by(immutable_code=code).first():
        raise MasterDataValidationError("immutable_code already exists")
    kwargs = dict(
        immutable_code=code,
        fa_name=_required_text(data, "fa_name", max_length=160),
        en_name=_required_text(data, "en_name", max_length=160),
        description=_optional_text(data, "description"),
        display_order=_integer(data.get("display_order", 0), "display_order"),
        is_active=_boolean(data.get("is_active", True), "is_active"),
    )
    if model is CargoType:
        kwargs["parent"] = _parent(data)
    if model is UnitOfMeasure:
        kwargs["symbol"] = _required_text(data, "symbol", max_length=32)
        dimension = data.get("measurement_dimension")
        if dimension not in MASTER_DATA_DIMENSIONS:
            raise MasterDataValidationError("measurement_dimension is invalid")
        kwargs["measurement_dimension"] = dimension
    row = model(**kwargs)
    db.session.add(row)
    try:
        db.session.commit()
    except StaleDataError as exc:
        db.session.rollback()
        raise VersionConflictError("resource was updated by another request") from exc
    return row


def update(row, data):
    resource = next(name for name, model in RESOURCES.items() if isinstance(row, model))
    _validate_fields(resource, data, creating=False)
    supplied_version = _integer(data.get("version"), "version")
    if supplied_version != row.version:
        raise VersionConflictError("resource was updated by another request")
    if "immutable_code" in data and data["immutable_code"].strip().upper() != row.immutable_code:
        raise MasterDataValidationError("immutable_code cannot be changed")
    for key in ("fa_name", "en_name"):
        if key in data:
            setattr(row, key, _required_text(data, key, max_length=160))
    row.description = _optional_text(data, "description", row.description)
    if "display_order" in data:
        row.display_order = _integer(data["display_order"], "display_order")
    if isinstance(row, CargoType):
        row.parent = _parent(data, row)
    if isinstance(row, UnitOfMeasure):
        if "symbol" in data:
            row.symbol = _required_text(data, "symbol", max_length=32)
        if "measurement_dimension" in data:
            if data["measurement_dimension"] not in MASTER_DATA_DIMENSIONS:
                raise MasterDataValidationError("measurement_dimension is invalid")
            row.measurement_dimension = data["measurement_dimension"]
    row.version += 1
    row.updated_at = datetime.utcnow()
    try:
        db.session.commit()
    except StaleDataError as exc:
        db.session.rollback()
        raise VersionConflictError("resource was updated by another request") from exc
    return row


def set_active(row, active, version):
    if _integer(version, "version") != row.version:
        raise VersionConflictError("resource was updated by another request")
    if isinstance(row, CargoType) and not active and any(child.is_active for child in row.children):
        raise MasterDataValidationError("deactivate active child cargo types first")
    row.is_active = active
    row.version += 1
    row.updated_at = datetime.utcnow()
    try:
        db.session.commit()
    except StaleDataError as exc:
        db.session.rollback()
        raise VersionConflictError("resource was updated by another request") from exc
    return row


def list_rows(resource, *, search="", active=None, dimension=None, sort="display_order", direction="asc", page=1, per_page=20):
    model = model_for(resource)
    query = model.query
    if search:
        if len(search) > 160:
            raise MasterDataValidationError("q must be at most 160 characters")
        term = f"%{search.strip()}%"
        query = query.filter(or_(model.immutable_code.ilike(term), model.fa_name.ilike(term), model.en_name.ilike(term)))
    if active is not None:
        query = query.filter(model.is_active.is_(active))
    if model is UnitOfMeasure and dimension:
        if dimension not in MASTER_DATA_DIMENSIONS:
            raise MasterDataValidationError("measurement_dimension is invalid")
        query = query.filter_by(measurement_dimension=dimension)
    columns = {"display_order": model.display_order, "code": model.immutable_code, "fa_name": model.fa_name, "en_name": model.en_name, "updated_at": model.updated_at}
    column = columns.get(sort, model.display_order)
    query = query.order_by(column.desc() if direction == "desc" else column.asc(), model.id.asc())
    return query.paginate(page=max(1, page), per_page=min(max(1, per_page), 100), error_out=False)


def _validate_fields(resource, data, *, creating):
    if not isinstance(data, dict):
        raise MasterDataValidationError("request body must be an object")
    allowed = (COMMON_CREATE_FIELDS if creating else COMMON_UPDATE_FIELDS) | RESOURCE_FIELDS[resource]
    unexpected = sorted(set(data) - allowed)
    if unexpected:
        raise MasterDataValidationError(f"fields are not valid for {resource}: {', '.join(unexpected)}")


def _integer(value, key):
    if isinstance(value, bool) or not isinstance(value, int):
        raise MasterDataValidationError(f"{key} must be an integer")
    return value


def _boolean(value, key):
    if not isinstance(value, bool):
        raise MasterDataValidationError(f"{key} must be a boolean")
    return value
