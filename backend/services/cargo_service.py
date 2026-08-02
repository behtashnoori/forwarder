"""Bounded cargo catalog and shipment snapshot operations."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
import unicodedata

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from backend.cargo_models import CargoCatalogItem, CargoItemAlias, ShipmentCargoItem
from backend.extensions import db
from backend.models import CargoType, UnitOfMeasure
from backend.operational_models import OperationalShipment
from backend.services import operational_service


class CargoError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


_SPACES = re.compile(r"[\s\u200c]+")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize_text(value: str) -> str:
    """NFC, Arabic→Persian letters, digits→ASCII, ZWNJ/space collapse, trim, casefold."""
    value = unicodedata.normalize("NFC", str(value or ""))
    value = value.translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})).translate(
        _DIGITS
    )
    return _SPACES.sub(" ", value).strip().casefold()


def org_for(user):
    return operational_service.organization_for_user(user["id"])


def _required(data, name, limit=200):
    value = str(data.get(name, "")).strip()
    if not value:
        raise CargoError(f"{name} is required", 422)
    if len(value) > limit:
        raise CargoError(f"{name} is too long", 422)
    return value


def _optional(data, name, limit=255):
    value = data.get(name)
    if value is None or str(value).strip() == "":
        return None
    value = str(value).strip()
    if len(value) > limit:
        raise CargoError(f"{name} is too long", 422)
    return value


def catalog_dict(row, include_aliases=False):
    result = {
        "public_id": row.public_id,
        "immutable_code": row.immutable_code,
        "fa_name": row.fa_name,
        "en_name": row.en_name,
        "description": row.description,
        "part_number": row.part_number,
        "customer_item_code": row.customer_item_code,
        "hs_code": row.hs_code,
        "brand": row.brand,
        "model": row.model,
        "is_active": row.is_active,
        "version": row.version,
        "cargo_type": {
            "public_id": row.cargo_type.public_id,
            "code": row.cargo_type.immutable_code,
            "fa_name": row.cargo_type.fa_name,
            "en_name": row.cargo_type.en_name,
        },
        "default_uom": None
        if not row.default_uom
        else {
            "public_id": row.default_uom.public_id,
            "code": row.default_uom.immutable_code,
            "symbol": row.default_uom.symbol,
        },
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }
    if include_aliases:
        result["aliases"] = [alias_dict(a) for a in row.aliases]
    return result


def alias_dict(row):
    return {
        "public_id": row.public_id,
        "alias_text": row.alias_text,
        "normalized_alias": row.normalized_alias,
        "language": row.language,
        "alias_type": row.alias_type,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def list_catalog(user, args):
    org = org_for(user)
    per_page = min(max(int(args.get("per_page", 20)), 1), 100)
    page = max(int(args.get("page", 1)), 1)
    query = select(CargoCatalogItem).where(CargoCatalogItem.organization_id == org)
    active = args.get("active")
    if active in {"true", "false"}:
        query = query.where(CargoCatalogItem.is_active.is_(active == "true"))
    if args.get("cargo_type"):
        query = query.join(CargoType).where(CargoType.public_id == args["cargo_type"])
    if args.get("q"):
        raw_q = str(args["q"]).strip()
        q = f"%{normalize_text(raw_q)}%"
        query = query.where(
            or_(
                CargoCatalogItem.immutable_code == raw_q,
                CargoCatalogItem.fa_name == raw_q,
                CargoCatalogItem.part_number == raw_q,
                CargoCatalogItem.search_text.like(q),
                CargoCatalogItem.aliases.any(
                    and_(
                        CargoItemAlias.is_active.is_(True),
                        CargoItemAlias.normalized_alias.like(q),
                    )
                ),
            )
        )
    total = db.session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.session.scalars(
        query.options(
            selectinload(CargoCatalogItem.cargo_type),
            selectinload(CargoCatalogItem.default_uom),
        )
        .order_by(CargoCatalogItem.immutable_code)
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return {
        "items": [catalog_dict(r, True) for r in rows],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
    }


def scoped_catalog(user, public_id, active_only=False):
    row = db.session.scalar(
        select(CargoCatalogItem).where(
            CargoCatalogItem.public_id == public_id,
            CargoCatalogItem.organization_id == org_for(user),
        )
    )
    if not row:
        raise CargoError("not found", 404)
    if active_only and not row.is_active:
        raise CargoError("catalog item is inactive", 422)
    return row


def _references(data):
    ct = db.session.scalar(
        select(CargoType).where(CargoType.public_id == data.get("cargo_type_public_id"))
    )
    if not ct or not ct.is_active:
        raise CargoError("active cargo_type is required", 422)
    uom = None
    if data.get("default_uom_public_id"):
        uom = db.session.scalar(
            select(UnitOfMeasure).where(
                UnitOfMeasure.public_id == data["default_uom_public_id"]
            )
        )
        if not uom or not uom.is_active:
            raise CargoError("default_uom is invalid", 422)
    return ct, uom


def _refresh_search(row):
    row.search_text = " ".join(
        normalize_text(v)
        for v in [
            row.immutable_code,
            row.fa_name,
            row.en_name,
            row.part_number,
            row.customer_item_code,
        ]
        if v
    )


def create_catalog(user, data):
    ct, uom = _references(data)
    code = _required(data, "immutable_code", 64)
    row = CargoCatalogItem(
        organization_id=org_for(user),
        immutable_code=code,
        fa_name=_required(data, "fa_name", 160),
        en_name=_optional(data, "en_name", 160),
        cargo_type=ct,
        default_uom=uom,
        created_by=user["id"],
        updated_by=user["id"],
    )
    for field in (
        "description",
        "part_number",
        "customer_item_code",
        "hs_code",
        "brand",
        "model",
    ):
        setattr(
            row, field, _optional(data, field, 2000 if field == "description" else 120)
        )
    _refresh_search(row)
    db.session.add(row)
    db.session.commit()
    return row


def update_catalog(user, row, data):
    if "immutable_code" in data and data["immutable_code"] != row.immutable_code:
        raise CargoError("immutable_code cannot be changed", 422)
    if int(data.get("version", 0)) != row.version:
        raise CargoError("version conflict", 409)
    if "cargo_type_public_id" in data or "default_uom_public_id" in data:
        merged = {
            "cargo_type_public_id": data.get(
                "cargo_type_public_id", row.cargo_type.public_id
            ),
            "default_uom_public_id": data.get(
                "default_uom_public_id",
                row.default_uom.public_id if row.default_uom else None,
            ),
        }
        row.cargo_type, row.default_uom = _references(merged)
    if "fa_name" in data:
        row.fa_name = _required(data, "fa_name", 160)
    for field in (
        "en_name",
        "description",
        "part_number",
        "customer_item_code",
        "hs_code",
        "brand",
        "model",
    ):
        if field in data:
            setattr(
                row,
                field,
                _optional(data, field, 2000 if field == "description" else 160),
            )
    row.updated_by = user["id"]
    row.version += 1
    _refresh_search(row)
    db.session.commit()
    return row


def set_catalog_active(user, row, active, data):
    if int(data.get("version", 0)) != row.version:
        raise CargoError("version conflict", 409)
    row.is_active = active
    row.version += 1
    row.updated_by = user["id"]
    db.session.commit()
    return row


def create_alias(user, item, data):
    text = _required(data, "alias_text", 200)
    language = data.get("language", "und")
    alias_type = data.get("alias_type", "COMMON_NAME")
    if language not in {"fa", "en", "und"} or alias_type not in {
        "COMMON_NAME",
        "CUSTOMER_TERM",
        "ABBREVIATION",
        "LEGACY_TERM",
        "OTHER_GOVERNED",
    }:
        raise CargoError("invalid alias metadata", 422)
    row = CargoItemAlias(
        catalog_item=item,
        alias_text=text,
        normalized_alias=normalize_text(text),
        language=language,
        alias_type=alias_type,
        created_by=user["id"],
        updated_by=user["id"],
    )
    db.session.add(row)
    db.session.commit()
    return row


def scoped_alias(item, public_id):
    row = db.session.scalar(
        select(CargoItemAlias).where(
            CargoItemAlias.public_id == public_id,
            CargoItemAlias.catalog_item_id == item.id,
        )
    )
    if not row:
        raise CargoError("not found", 404)
    return row


def update_alias(user, row, data):
    if "alias_text" in data:
        row.alias_text = _required(data, "alias_text", 200)
        row.normalized_alias = normalize_text(row.alias_text)
    if "language" in data:
        if data["language"] not in {"fa", "en", "und"}:
            raise CargoError("invalid language", 422)
        row.language = data["language"]
    if "alias_type" in data:
        if data["alias_type"] not in {
            "COMMON_NAME",
            "CUSTOMER_TERM",
            "ABBREVIATION",
            "LEGACY_TERM",
            "OTHER_GOVERNED",
        }:
            raise CargoError("invalid alias_type", 422)
        row.alias_type = data["alias_type"]
    if "is_active" in data:
        row.is_active = bool(data["is_active"])
    row.updated_by = user["id"]
    db.session.commit()
    return row


def scoped_shipment(user, public_id):
    operational_service.require_permission(user, "operational_shipment.read")
    org = org_for(user)
    row = db.session.scalar(
        select(OperationalShipment).where(
            OperationalShipment.public_id == public_id,
            OperationalShipment.organization_id == org,
        )
    )
    if not row:
        raise CargoError("not found", 404)
    return row


def shipment_item_dict(row):
    return {
        "public_id": row.public_id,
        "line_number": row.line_number,
        "catalog_item_public_id": row.catalog_item.public_id
        if row.catalog_item
        else None,
        "source": "catalog" if row.catalog_item else "manual",
        "cargo_type_public_id": row.cargo_type.public_id,
        "uom_public_id": row.uom.public_id,
        "quantity": str(row.quantity),
        "display_name_snapshot": row.display_name_snapshot,
        "cargo_type_code_snapshot": row.cargo_type_code_snapshot,
        "cargo_type_fa_snapshot": row.cargo_type_fa_snapshot,
        "cargo_type_en_snapshot": row.cargo_type_en_snapshot,
        "uom_code_snapshot": row.uom_code_snapshot,
        "uom_symbol_snapshot": row.uom_symbol_snapshot,
        "part_number_snapshot": row.part_number_snapshot,
        "customer_item_code_snapshot": row.customer_item_code_snapshot,
        "hs_code_snapshot": row.hs_code_snapshot,
        "brand_snapshot": row.brand_snapshot,
        "model_snapshot": row.model_snapshot,
        "description_snapshot": row.description_snapshot,
        "version": row.version,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def create_shipment_item(user, shipment, data):
    operational_service.require_permission(user, "operational_shipment.create")
    try:
        quantity = Decimal(str(data.get("quantity")))
    except (InvalidOperation, TypeError):
        raise CargoError("quantity must be positive", 422)
    if quantity <= 0:
        raise CargoError("quantity must be positive", 422)
    ct = db.session.scalar(
        select(CargoType).where(
            CargoType.public_id == data.get("cargo_type_public_id"),
            CargoType.is_active.is_(True),
        )
    )
    uom = db.session.scalar(
        select(UnitOfMeasure).where(
            UnitOfMeasure.public_id == data.get("uom_public_id"),
            UnitOfMeasure.is_active.is_(True),
        )
    )
    if not ct or not uom:
        raise CargoError("active cargo_type and uom are required", 422)
    catalog = (
        scoped_catalog(user, data["catalog_item_public_id"], True)
        if data.get("catalog_item_public_id")
        else None
    )
    if catalog and catalog.cargo_type_id != ct.id:
        raise CargoError("cargo_type must match catalog item", 422)
    name = catalog.fa_name if catalog else _required(data, "display_name", 200)
    row = ShipmentCargoItem(
        operational_shipment_id=shipment.id,
        line_number=int(data.get("line_number", 0)),
        catalog_item=catalog,
        cargo_type=ct,
        quantity=quantity,
        uom=uom,
        display_name_snapshot=name,
        cargo_type_code_snapshot=ct.immutable_code,
        cargo_type_fa_snapshot=ct.fa_name,
        cargo_type_en_snapshot=ct.en_name,
        uom_code_snapshot=uom.immutable_code,
        uom_symbol_snapshot=uom.symbol,
        created_by=user["id"],
        updated_by=user["id"],
    )
    mapping = {
        "part_number_snapshot": "part_number",
        "customer_item_code_snapshot": "customer_item_code",
        "hs_code_snapshot": "hs_code",
        "brand_snapshot": "brand",
        "model_snapshot": "model",
        "description_snapshot": "description",
    }
    for target, source in mapping.items():
        setattr(
            row,
            target,
            getattr(catalog, source, None)
            if catalog
            else _optional(data, source, 2000 if source == "description" else 160),
        )
    db.session.add(row)
    db.session.commit()
    return row


def update_shipment_item(user, row, data):
    operational_service.require_permission(user, "operational_shipment.create")
    if int(data.get("version", 0)) != row.version:
        raise CargoError("version conflict", 409)
    if "quantity" in data:
        try:
            q = Decimal(str(data["quantity"]))
            assert q > 0
        except (InvalidOperation, TypeError, AssertionError):
            raise CargoError("quantity must be positive", 422)
        row.quantity = q
    immutable_inputs = {
        "catalog_item_public_id",
        "cargo_type_public_id",
        "uom_public_id",
        "display_name",
        "part_number",
        "customer_item_code",
        "hs_code",
        "brand",
        "model",
        "description",
    }
    if immutable_inputs.intersection(data):
        raise CargoError("shipment cargo snapshots cannot be changed", 422)
    row.updated_by = user["id"]
    row.version += 1
    db.session.commit()
    return row
