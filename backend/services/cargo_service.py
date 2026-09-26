"""Bounded cargo catalog and shipment snapshot operations."""

from __future__ import annotations

from datetime import timezone
from decimal import Decimal, InvalidOperation
import re
import unicodedata

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from backend.cargo_models import CargoCatalogItem, CargoItemAlias, ExecutionUnitCargoAllocation, ShipmentCargoItem, ShipmentCargoTransportAllocation
from backend.extensions import db
from backend.models import (
    Customer,
    CargoType,
    ExpertUser,
    PackagingType,
    RequestCargoItem,
    ShipmentRequest,
    ShipmentTracking,
    ShipmentTransportUnit,
    UnitOfMeasure,
)
from backend.operational_models import (
    ExecutionUnit,
    OperationalAudit,
    OperationalShipment,
    Project,
)
from backend.organization_reference_catalog_models import (
    OrganizationCargoTypeActivation,
    OrganizationPackagingTypeActivation,
    OrganizationUnitOfMeasureActivation,
)
from backend.services import operational_service
from backend.services.assigned_work_authorization import (
    assigned_request_scope,
    authorize_document_management,
    authorize_work_action,
)
from backend.services.organization_reference_catalog_service import (
    is_definition_active_for_organization,
)
from backend.services.tracking_projection_service import project_operational_shipments


class CargoError(ValueError):
    def __init__(self, message: str, status: int = 400, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


SHIPMENT_STATUSES = frozenset({"planned", "in_progress", "completed", "cancelled", "closed"})
ACTIVE_SHIPMENT_STATUSES = frozenset({"planned", "in_progress"})


_SPACES = re.compile(r"[\s\u200c]+")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


from backend.services import closure_commands as closure_guard


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


def _iso(value):
    if not value:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def catalog_shipment_usage(user, public_id, args):
    """Project tenant-safe catalog usage without changing cargo ownership."""
    operational_service.require_permission(user, "operational_shipment.read")
    catalog = scoped_catalog(user, public_id)
    try:
        limit = min(max(int(args.get("limit", 50)), 1), 100)
        offset = max(int(args.get("offset", 0)), 0)
    except (TypeError, ValueError) as exc:
        raise CargoError("limit and offset must be integers", 422) from exc
    status = str(args.get("status") or "").strip()
    if status and status not in SHIPMENT_STATUSES:
        raise CargoError("invalid shipment status", 422)
    active_only = str(args.get("active_only") or "false").lower()
    if active_only not in {"true", "false"}:
        raise CargoError("active_only must be true or false", 422)

    base = (
        select(ShipmentCargoItem, OperationalShipment, Project, ShipmentRequest)
        .join(OperationalShipment, ShipmentCargoItem.operational_shipment_id == OperationalShipment.id)
        .outerjoin(Project, OperationalShipment.project_id == Project.id)
        .outerjoin(ShipmentRequest, OperationalShipment.shipment_request_id == ShipmentRequest.id)
        .where(
            ShipmentCargoItem.catalog_item_id == catalog.id,
            OperationalShipment.organization_id == catalog.organization_id,
            or_(Project.id.is_(None), Project.organization_id == catalog.organization_id),
            or_(
                ShipmentRequest.id.is_(None),
                ShipmentRequest.operational_organization_id == catalog.organization_id,
            ),
        )
    )
    if status:
        base = base.where(OperationalShipment.lifecycle_status == status)
    if active_only == "true":
        base = base.where(OperationalShipment.lifecycle_status.in_(ACTIVE_SHIPMENT_STATUSES))

    filtered = base.subquery()
    shipment_count = db.session.scalar(
        select(func.count(func.distinct(filtered.c.operational_shipment_id)))
    ) or 0
    active_count = db.session.scalar(
        select(func.count(func.distinct(filtered.c.operational_shipment_id))).where(
            filtered.c.lifecycle_status.in_(ACTIVE_SHIPMENT_STATUSES)
        )
    ) or 0
    rows = db.session.execute(
        base.order_by(OperationalShipment.updated_at.desc(), ShipmentCargoItem.line_number)
        .offset(offset)
        .limit(limit)
    ).all()

    shipment_ids = {shipment.id for _line, shipment, _project, _request in rows}
    projections = project_operational_shipments(catalog.organization_id, shipment_ids)

    items = []
    for line, shipment, project, request_row in rows:
        projection = projections.get(shipment.id, {
            "current_location": None,
            "location_state": "UNAVAILABLE",
            "source": "unavailable",
            "latest_event_at": None,
            "is_fallback": False,
            "reconciliation_health": "NOT_APPLICABLE",
        })
        items.append({
            "operational_shipment_public_id": shipment.public_id,
            "project_public_id": project.public_id if project else None,
            "project_code": project.project_code if project else None,
            "shipment_request_reference": request_row.tracking_code if request_row else None,
            "quantity": str(line.quantity),
            "uom": line.uom_symbol_snapshot,
            "status": shipment.lifecycle_status,
            "shipment_cargo_line_public_id": line.public_id,
            "display_name_snapshot": line.display_name_snapshot,
            "current_location": projection["current_location"],
            "location_state": projection["location_state"],
            "location_source": projection["source"],
            "latest_event_at": projection["latest_event_at"],
            "is_fallback": projection["is_fallback"],
            "reconciliation_health": projection["reconciliation_health"],
        })
    return {
        "cargo_item": catalog_dict(catalog),
        "summary": {"shipment_count": shipment_count, "active_shipment_count": active_count},
        "items": items,
        "limit": limit,
        "offset": offset,
    }


def _require_organization_activation(
    activation_model, definition_fk, definition_id, organization_id
):
    if not is_definition_active_for_organization(
        activation_model, definition_fk, definition_id, organization_id
    ):
        raise CargoError(
            "این نوع در تعاریف سازمان موجود نیست. برای ادامه، مدیر سازمان باید آن را تعریف یا فعال کند.",
            409,
            "ORGANIZATION_REFERENCE_NOT_ACTIVE",
        )


def _references(data, organization_id):
    ct = db.session.scalar(
        select(CargoType).where(CargoType.public_id == data.get("cargo_type_public_id"))
    )
    if not ct or not ct.is_active:
        raise CargoError("active cargo_type is required", 422)
    _require_organization_activation(
        OrganizationCargoTypeActivation,
        "cargo_type_id",
        ct.id,
        organization_id,
    )
    uom = None
    if data.get("default_uom_public_id"):
        uom = db.session.scalar(
            select(UnitOfMeasure).where(
                UnitOfMeasure.public_id == data["default_uom_public_id"]
            )
        )
        if not uom or not uom.is_active:
            raise CargoError("default_uom is invalid", 422)
        _require_organization_activation(
            OrganizationUnitOfMeasureActivation,
            "unit_of_measure_id",
            uom.id,
            organization_id,
        )
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
            row.hs_code,
            row.brand,
            row.model,
        ]
        if v
    )


def create_catalog(user, data):
    organization_id = org_for(user)
    ct, uom = _references(data, organization_id)
    code = _required(data, "immutable_code", 64)
    row = CargoCatalogItem(
        organization_id=organization_id,
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
        row.cargo_type, row.default_uom = _references(merged, row.organization_id)
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
    try:
        return operational_service.scoped_shipment(public_id, user)
    except operational_service.OperationalError as exc:
        # Keep the cargo API's error boundary while reusing the canonical
        # tenant + current assignment/ownership decision.
        raise CargoError("not found", 404) from exc


def _require_cargo_mutation(user, shipment):
    try:
        operational_service.require_permission(user, "operational_shipment.create")
    except operational_service.OperationalError as exc:
        raise CargoError(exc.message, exc.status, exc.code) from exc
    decision = authorize_document_management(user, shipment, for_update=True)
    if not decision.allowed:
        raise CargoError(
            "Only the owning Transport Expert can change Cargo.",
            403,
            "OWNING_TRANSPORT_EXPERT_REQUIRED",
        )


def _decimal(value, field, *, required=False):
    if value in (None, ""):
        if required:
            raise CargoError(f"{field} must be positive", 422)
        return None
    if isinstance(value, bool):
        raise CargoError(f"{field} must be positive", 422)
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CargoError(f"{field} must be positive", 422) from exc
    if result <= 0:
        raise CargoError(f"{field} must be positive", 422)
    return result


def _active_uom(public_id, organization_id, *, dimension=None, field="uom"):
    row = db.session.scalar(
        select(UnitOfMeasure).where(
            UnitOfMeasure.public_id == public_id,
            UnitOfMeasure.is_active.is_(True),
        )
    )
    if not row:
        raise CargoError(f"active {field} is required", 422)
    _require_organization_activation(
        OrganizationUnitOfMeasureActivation,
        "unit_of_measure_id",
        row.id,
        organization_id,
    )
    if dimension and row.measurement_dimension != dimension:
        raise CargoError(f"{field} must use a {dimension.lower()} unit", 422)
    return row


def _active_packaging(public_id, organization_id):
    if not public_id:
        return None
    row = db.session.scalar(
        select(PackagingType).where(
            PackagingType.public_id == public_id,
            PackagingType.is_active.is_(True),
        )
    )
    if not row:
        raise CargoError("active packaging_type is required", 422)
    _require_organization_activation(
        OrganizationPackagingTypeActivation,
        "packaging_type_id",
        row.id,
        organization_id,
    )
    return row


def _quantity_payload(row):
    return {
        "requested": str(row.requested_quantity)
        if row.requested_quantity is not None
        else None,
        "planned": str(row.planned_quantity)
        if row.planned_quantity is not None
        else None,
        "actual": str(row.actual_quantity)
        if row.actual_quantity is not None
        else None,
        "legacy": str(row.quantity),
        "legacy_meaning": "PLANNED_COMPATIBILITY"
        if row.planned_quantity is not None
        else "UNKNOWN",
    }


def _lineage_kind(row):
    if row.source_shipment_request_id:
        return "REQUEST"
    if row.planned_quantity is not None:
        return "DIRECT"
    return "UNKNOWN"


def _incomplete_fields(row):
    missing = []
    if not row.hs_code_snapshot:
        missing.append("HS_CODE")
    if row.packaging_type_id is None:
        missing.append("PACKAGING_TYPE")
    if row.gross_weight is None:
        missing.append("WEIGHT")
    if row.volume is None:
        missing.append("VOLUME")
    return missing


def shipment_item_dict(row):
    # Canonical execution allocations win for a cargo line.  A legacy row is
    # historical compatibility data only and is shown only when no canonical
    # allocation exists for that line.
    # The compatibility summary has no stage dimension. Summing successive
    # route stages would count the same physical Cargo repeatedly.
    canonical = db.session.scalar(select(func.coalesce(func.sum(ExecutionUnitCargoAllocation.allocated_quantity), 0)).where(
        ExecutionUnitCargoAllocation.shipment_cargo_item_id == row.id,
        ExecutionUnitCargoAllocation.route_stage_execution_id.is_(None),
        ExecutionUnitCargoAllocation.is_current.is_(True),
    ))
    allocated = canonical or db.session.scalar(select(func.coalesce(func.sum(ShipmentCargoTransportAllocation.allocated_quantity), 0)).where(ShipmentCargoTransportAllocation.shipment_cargo_item_id == row.id))
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
        "quantities": _quantity_payload(row),
        "allocated_quantity": str(allocated),
        "remaining_quantity": str(row.quantity - allocated),
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
        "source_lineage": {
            "kind": _lineage_kind(row),
            "request_public_id": row.source_shipment_request.public_id
            if row.source_shipment_request
            else None,
            "request_reference": (
                row.source_shipment_request.tracking_code
                or row.source_shipment_request.public_id[:8]
            )
            if row.source_shipment_request
            else None,
            "request_cargo_item_public_id": row.source_request_cargo_item.public_id
            if row.source_request_cargo_item
            else None,
            "request_cargo_position": row.source_request_cargo_item.position
            if row.source_request_cargo_item
            else None,
        },
        "packaging": None
        if not row.packaging_type_id
        else {
            "public_id": row.packaging_type.public_id if row.packaging_type else None,
            "code": row.packaging_code_snapshot,
            "fa_name": row.packaging_fa_snapshot,
            "en_name": row.packaging_en_snapshot,
        },
        "gross_weight": None
        if row.gross_weight is None
        else {
            "value": str(row.gross_weight),
            "uom_public_id": row.gross_weight_uom.public_id
            if row.gross_weight_uom
            else None,
            "uom_code": row.gross_weight_uom_code_snapshot,
            "uom_symbol": row.gross_weight_uom_symbol_snapshot,
        },
        "volume": None
        if row.volume is None
        else {
            "value": str(row.volume),
            "uom_public_id": row.volume_uom.public_id if row.volume_uom else None,
            "uom_code": row.volume_uom_code_snapshot,
            "uom_symbol": row.volume_uom_symbol_snapshot,
        },
        "destination_description": row.destination_description,
        "incomplete_fields": _incomplete_fields(row),
        "cargo_owner": None
        if not row.cargo_owner_customer
        else {
            "id": row.cargo_owner_customer.id,
            "label": operational_service._customer_label(row.cargo_owner_customer),
        },
        "version": row.version,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _cargo_owner(shipment, data):
    """Resolve an explicitly selected active tenant customer, or shipment default."""
    explicit_owner = "cargo_owner_customer_id" in data
    raw_id = data.get("cargo_owner_customer_id", shipment.customer_id)
    if raw_id in (None, ""):
        raise CargoError("cargo_owner_customer_id is required", 422)
    try:
        customer_id = int(raw_id)
    except (TypeError, ValueError) as exc:
        raise CargoError("cargo_owner_customer_id must be an integer", 422) from exc
    query = select(Customer).where(
        Customer.id == customer_id,
        Customer.status == "active",
        Customer.ownership_scope == "TENANT",
        Customer.operational_organization_id == shipment.organization_id,
    )
    owner = db.session.scalar(query)
    if not owner:
        raise CargoError("active cargo owner was not found", 422)
    return owner


def _authorized_source_request(user, shipment, public_id):
    if not public_id:
        return None
    row = db.session.scalar(
        select(ShipmentRequest).where(
            ShipmentRequest.public_id == str(public_id),
            ShipmentRequest.ownership_scope == "TENANT",
            ShipmentRequest.operational_organization_id == shipment.organization_id,
        )
    )
    if not row:
        raise CargoError("source request was not found", 422, "INVALID_SOURCE_REQUEST")
    decision = authorize_work_action(user, row, "request.read")
    if not decision.allowed:
        raise CargoError("source request was not found", 422, "INVALID_SOURCE_REQUEST")
    return row


def _source_request_cargo(request_row, public_id):
    if not public_id:
        return None
    if request_row is None:
        raise CargoError(
            "source_request_public_id is required for Request Cargo lineage",
            422,
            "SOURCE_REQUEST_REQUIRED",
        )
    row = db.session.scalar(
        select(RequestCargoItem).where(
            RequestCargoItem.public_id == str(public_id),
            RequestCargoItem.shipment_request_id == request_row.id,
        )
    )
    if not row:
        raise CargoError(
            "source Request Cargo was not found",
            422,
            "INVALID_SOURCE_REQUEST_CARGO",
        )
    return row


def _lineage(user, shipment, data, owner, uom):
    request_row = _authorized_source_request(
        user, shipment, data.get("source_request_public_id")
    )
    request_cargo = _source_request_cargo(
        request_row, data.get("source_request_cargo_item_public_id")
    )
    requested = _decimal(data.get("requested_quantity"), "requested_quantity")
    if requested is not None and request_row is None:
        raise CargoError(
            "requested_quantity requires a real source Request",
            422,
            "REQUESTED_SOURCE_REQUIRED",
        )
    if request_row and request_row.customer_id and request_row.customer_id != owner.id:
        raise CargoError(
            "Cargo Customer must match the source Request Customer",
            422,
            "SOURCE_CUSTOMER_MISMATCH",
        )
    if request_cargo and request_cargo.quantity is not None:
        if request_cargo.uom_id != uom.id:
            raise CargoError(
                "source Request Cargo uses a different UOM; conversion is not allowed",
                422,
                "SOURCE_UOM_MISMATCH",
            )
        source_quantity = Decimal(request_cargo.quantity)
        if requested is not None and requested != source_quantity:
            raise CargoError(
                "requested_quantity must match the source Request Cargo",
                422,
                "SOURCE_QUANTITY_MISMATCH",
            )
        requested = source_quantity
    return request_row, request_cargo, requested


def _audit_value(field, value):
    if field in {"hs_code_snapshot", "description_snapshot", "destination_description"}:
        return "SET" if value not in (None, "") else "MISSING"
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "public_id"):
        return value.public_id
    return value


def _cargo_audit(user, shipment, row, action, changes, reason=None):
    db.session.add(
        OperationalAudit(
            organization_id=shipment.organization_id,
            actor_user_id=user["id"],
            action=action,
            entity_type="ShipmentCargoItem",
            entity_id=row.id,
            metadata_json={
                "cargo_public_id": row.public_id,
                "shipment_public_id": shipment.public_id,
                "version": row.version,
                "changed_fields": sorted(changes),
                "reason": reason,
                "changes": {
                    field: {
                        "before": _audit_value(field, before),
                        "after": _audit_value(field, after),
                    }
                    for field, (before, after) in changes.items()
                },
            },
        )
    )


def cargo_history(row):
    audits = db.session.scalars(
        select(OperationalAudit)
        .where(
            OperationalAudit.entity_type == "ShipmentCargoItem",
            OperationalAudit.entity_id == row.id,
        )
        .order_by(OperationalAudit.recorded_at, OperationalAudit.id)
    ).all()
    return [
        {
            "action": audit.action,
            "recorded_at": audit.recorded_at.isoformat(),
            "actor_user_id": audit.actor_user_id,
            "actor_name": db.session.get(ExpertUser, audit.actor_user_id).full_name,
            **(audit.metadata_json or {}),
        }
        for audit in audits
    ]


def cargo_lineage_options(user, shipment):
    _require_cargo_mutation(user, shipment)
    customers = db.session.scalars(
        select(Customer)
        .where(
            Customer.operational_organization_id == shipment.organization_id,
            Customer.ownership_scope == "TENANT",
            Customer.status == "active",
        )
        .order_by(Customer.company_name, Customer.last_name, Customer.first_name, Customer.id)
        .limit(200)
    ).all()
    requests = db.session.scalars(
        select(ShipmentRequest)
        .where(
            ShipmentRequest.public_id.is_not(None),
            assigned_request_scope(user, "request.read"),
        )
        .options(
            selectinload(ShipmentRequest.customer),
            selectinload(ShipmentRequest.request_cargo_items).selectinload(
                RequestCargoItem.cargo_type
            ),
            selectinload(ShipmentRequest.request_cargo_items).selectinload(
                RequestCargoItem.uom
            ),
        )
        .order_by(ShipmentRequest.created_at.desc(), ShipmentRequest.id.desc())
        .limit(200)
    ).all()
    return {
        "customers": [
            {"id": customer.id, "label": operational_service._customer_label(customer)}
            for customer in customers
        ],
        "requests": [
            {
                "public_id": request_row.public_id,
                "label": f"درخواست {request_row.tracking_code or request_row.public_id[:8]}",
                "customer_id": request_row.customer_id,
                "customer_label": operational_service._customer_label(request_row.customer)
                if request_row.customer
                else None,
                "cargo_items": [
                    {
                        "public_id": item.public_id,
                        "position": item.position,
                        "description": item.description,
                        "quantity": str(item.quantity)
                        if item.quantity is not None
                        else None,
                        "cargo_type_public_id": item.cargo_type.public_id
                        if item.cargo_type
                        else None,
                        "cargo_type_name": item.cargo_type.fa_name
                        if item.cargo_type
                        else None,
                        "uom_public_id": item.uom.public_id if item.uom else None,
                        "uom_symbol": item.uom.symbol if item.uom else None,
                    }
                    for item in request_row.request_cargo_items
                ],
            }
            for request_row in requests
        ],
    }


def _allocation_quantity(value):
    try: q = Decimal(str(value))
    except (InvalidOperation, TypeError): raise CargoError("allocated_quantity must be positive", 422)
    if q <= 0: raise CargoError("allocated_quantity must be positive", 422)
    return q


def allocation_dict(row):
    return {"public_id": row.public_id, "cargo_item_public_id": row.cargo_item.public_id,
            "transport_unit_id": row.transport_unit_id, "allocated_quantity": str(row.allocated_quantity),
            "uom_symbol": row.cargo_item.uom_symbol_snapshot, "cargo_name": row.cargo_item.display_name_snapshot,
            "transport_unit_code": row.transport_unit.unit_code, "transport_unit_type": row.transport_unit.unit_type}


def canonical_allocation_dict(row):
    return {"public_id": row.public_id, "cargo_item_public_id": row.cargo_item.public_id,
            "execution_unit_public_id": row.execution_unit.public_id,
            "allocated_quantity": str(row.allocated_quantity),
            "uom_symbol": row.cargo_item.uom_symbol_snapshot,
            "cargo_name": row.cargo_item.display_name_snapshot}


def shipment_allocation_view(user, shipment):
    operational_service.require_permission(user, "operational_shipment.read")
    allocations = db.session.scalars(select(ShipmentCargoTransportAllocation).where(ShipmentCargoTransportAllocation.operational_shipment_id == shipment.id).options(selectinload(ShipmentCargoTransportAllocation.cargo_item), selectinload(ShipmentCargoTransportAllocation.transport_unit))).all()
    units = db.session.scalars(select(ShipmentTransportUnit).where(ShipmentTransportUnit.operational_shipment_id == shipment.id, ShipmentTransportUnit.operational_organization_id == shipment.organization_id, ShipmentTransportUnit.is_active.is_(True))).all()
    # Request-derived units remain canonical and are admitted only when their tracking request is this shipment's root.
    if shipment.shipment_request_id:
        units += db.session.scalars(select(ShipmentTransportUnit).join(ShipmentTransportUnit.tracking).where(ShipmentTransportUnit.operational_organization_id == shipment.organization_id, ShipmentTracking.shipment_request_id == shipment.shipment_request_id, ShipmentTransportUnit.is_active.is_(True))).all()
    return {"allocations": [allocation_dict(x) for x in allocations], "transport_units": [{"id":x.id,"unit_code":x.unit_code,"unit_type":x.unit_type,"display_name":x.display_name,"vehicle_reference":x.vehicle_reference} for x in {x.id:x for x in units}.values()]}


def create_transport_unit(user, shipment, data):
    """Retire the legacy current-write endpoint without fabricating an execution.

    This compatibility route carries neither an execution identity nor the
    project lineage required to create one.  Creating a ShipmentTransportUnit
    here used to make a second current transport truth.  Callers must use the
    project-scoped ExecutionUnit command instead.
    """
    raise CargoError("LEGACY_WRITE_MAPPING = NEEDS_DECISION", 409)


def _legacy_execution_unit(user, shipment, unit_id):
    """Map a legacy transport unit only when its execution identity is exact."""
    unit = db.session.get(ShipmentTransportUnit, unit_id)
    if not unit or unit.operational_organization_id != shipment.organization_id:
        raise CargoError("invalid cargo or transport unit", 422)
    matches = db.session.scalars(select(ExecutionUnit).where(
        ExecutionUnit.legacy_unit_id == unit.id,
        ExecutionUnit.organization_id == shipment.organization_id,
    )).all()
    if len(matches) != 1:
        # The legacy request contains no safe execution identity.  Do not
        # manufacture one or retain a second writable allocation truth.
        raise CargoError("LEGACY_WRITE_MAPPING = NEEDS_DECISION", 409)
    return matches[0]


def save_allocation(user, shipment, data, row=None):
    """Compatibility adapter: legacy endpoint writes canonical truth only."""
    from backend.services import shared_transport_service
    cargo = db.session.scalar(select(ShipmentCargoItem).where(
        ShipmentCargoItem.public_id == data.get("cargo_item_public_id", row.cargo_item.public_id if row else None),
        ShipmentCargoItem.operational_shipment_id == shipment.id,
    ))
    unit_id = data.get("transport_unit_id", row.transport_unit_id if row else None)
    if not cargo:
        raise CargoError("invalid cargo or transport unit", 422)
    execution = _legacy_execution_unit(user, shipment, unit_id)
    try:
        return shared_transport_service.allocate(
            execution_public_id=execution.public_id, cargo_public_id=cargo.public_id,
            allocated_quantity=data.get("allocated_quantity", row.allocated_quantity if row else None), user=user,
        )
    except operational_service.OperationalError as exc:
        raise CargoError(exc.message, exc.status) from exc


def delete_allocation(user, shipment, public_id):
    from backend.services import shared_transport_service
    row = db.session.scalar(select(ShipmentCargoTransportAllocation).where(ShipmentCargoTransportAllocation.public_id == public_id, ShipmentCargoTransportAllocation.operational_shipment_id == shipment.id))
    if not row: raise CargoError("not found",404)
    execution = _legacy_execution_unit(user, shipment, row.transport_unit_id)
    canonical = db.session.scalar(select(ExecutionUnitCargoAllocation).where(
        ExecutionUnitCargoAllocation.execution_unit_id == execution.id,
        ExecutionUnitCargoAllocation.shipment_cargo_item_id == row.shipment_cargo_item_id,
        ExecutionUnitCargoAllocation.route_stage_execution_id.is_(None),
        ExecutionUnitCargoAllocation.is_current.is_(True),
    ))
    if not canonical:
        raise CargoError("LEGACY_WRITE_MAPPING = NEEDS_DECISION", 409)
    try:
        shared_transport_service.release(execution_public_id=execution.public_id, allocation_public_id=canonical.public_id, user=user)
    except operational_service.OperationalError as exc:
        raise CargoError(exc.message, exc.status) from exc


def create_shipment_item(user, shipment, data):
    _require_cargo_mutation(user, shipment)
    try:
        closure_guard.deny_new(shipment)
    except operational_service.OperationalError as exc:
        raise CargoError(exc.message, exc.status, exc.code) from exc
    planned = _decimal(data.get("planned_quantity"), "planned_quantity")
    quantity = _decimal(
        data.get("quantity", planned), "quantity", required=True
    )
    if planned is not None and quantity != planned:
        raise CargoError(
            "quantity compatibility value must equal planned_quantity",
            422,
            "PLANNED_QUANTITY_MISMATCH",
        )
    requested_input = data.get("requested_quantity")
    actual = _decimal(data.get("actual_quantity"), "actual_quantity")
    try:
        line_number = int(data.get("line_number", 0))
    except (TypeError, ValueError) as exc:
        raise CargoError("line_number must be positive", 422) from exc
    if line_number < 1:
        raise CargoError("line_number must be positive", 422)
    ct = db.session.scalar(
        select(CargoType).where(
            CargoType.public_id == data.get("cargo_type_public_id"),
            CargoType.is_active.is_(True),
        )
    )
    if not ct:
        raise CargoError("active cargo_type is required", 422)
    _require_organization_activation(
        OrganizationCargoTypeActivation,
        "cargo_type_id",
        ct.id,
        shipment.organization_id,
    )
    uom = _active_uom(data.get("uom_public_id"), shipment.organization_id)
    catalog = (
        scoped_catalog(user, data["catalog_item_public_id"], True)
        if data.get("catalog_item_public_id")
        else None
    )
    if catalog and catalog.cargo_type_id != ct.id:
        raise CargoError("cargo_type must match catalog item", 422)
    name = catalog.fa_name if catalog else _required(data, "display_name", 200)
    owner = _cargo_owner(shipment, data)
    lineage_data = dict(data)
    lineage_data["requested_quantity"] = requested_input
    source_request, source_request_cargo, requested = _lineage(
        user, shipment, lineage_data, owner, uom
    )
    packaging = _active_packaging(
        data.get("packaging_type_public_id"), shipment.organization_id
    )
    gross_weight = _decimal(data.get("gross_weight"), "gross_weight")
    gross_weight_uom = None
    if gross_weight is not None:
        gross_weight_uom = _active_uom(
            data.get("gross_weight_uom_public_id"),
            shipment.organization_id,
            dimension="WEIGHT",
            field="gross_weight_uom",
        )
    elif data.get("gross_weight_uom_public_id"):
        raise CargoError("gross_weight is required with its UOM", 422)
    volume = _decimal(data.get("volume"), "volume")
    volume_uom = None
    if volume is not None:
        volume_uom = _active_uom(
            data.get("volume_uom_public_id"),
            shipment.organization_id,
            dimension="VOLUME",
            field="volume_uom",
        )
    elif data.get("volume_uom_public_id"):
        raise CargoError("volume is required with its UOM", 422)
    row = ShipmentCargoItem(
        operational_shipment_id=shipment.id,
        line_number=line_number,
        catalog_item=catalog,
        cargo_type=ct,
        quantity=quantity,
        requested_quantity=requested,
        planned_quantity=planned,
        actual_quantity=actual,
        uom=uom,
        cargo_owner_customer=owner,
        source_shipment_request=source_request,
        source_request_cargo_item=source_request_cargo,
        packaging_type=packaging,
        gross_weight=gross_weight,
        gross_weight_uom=gross_weight_uom,
        volume=volume,
        volume_uom=volume_uom,
        destination_description=_optional(data, "destination_description", 300),
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
        supplied_progressive = (
            source in {"hs_code", "description"}
            and data.get(source) not in (None, "")
        )
        setattr(
            row,
            target,
            _optional(data, source, 2000 if source == "description" else 160)
            if supplied_progressive or not catalog
            else getattr(catalog, source, None),
        )
    if packaging:
        row.packaging_code_snapshot = packaging.immutable_code
        row.packaging_fa_snapshot = packaging.fa_name
        row.packaging_en_snapshot = packaging.en_name
    if gross_weight_uom:
        row.gross_weight_uom_code_snapshot = gross_weight_uom.immutable_code
        row.gross_weight_uom_symbol_snapshot = gross_weight_uom.symbol
    if volume_uom:
        row.volume_uom_code_snapshot = volume_uom.immutable_code
        row.volume_uom_symbol_snapshot = volume_uom.symbol
    db.session.add(row)
    db.session.flush()
    _cargo_audit(
        user,
        shipment,
        row,
        "SHIPMENT_CARGO_CREATED",
        {
            "cargo_owner_customer_id": (None, owner.id),
            "source_request_public_id": (
                None,
                source_request.public_id if source_request else None,
            ),
            "source_request_cargo_item_public_id": (
                None,
                source_request_cargo.public_id if source_request_cargo else None,
            ),
            "requested_quantity": (None, requested),
            "planned_quantity": (None, planned),
            "actual_quantity": (None, actual),
            "packaging_type": (None, packaging),
            "gross_weight": (None, gross_weight),
            "volume": (None, volume),
        },
    )
    db.session.commit()
    return row


def update_shipment_item(user, row, data):
    shipment = db.session.get(OperationalShipment, row.operational_shipment_id)
    if shipment is None:
        raise CargoError("shipment not found", 404)
    _require_cargo_mutation(user, shipment)
    try:
        closure_guard.current(shipment)
        db.session.refresh(row)
        _require_cargo_mutation(user, shipment)
        if any(field in data and _decimal(data[field], field) != getattr(row, field)
               for field in ("planned_quantity", "quantity")):
            closure_guard.deny_new(shipment)
        closure_guard.correction(shipment, data.get("reason"))
    except operational_service.OperationalError as exc:
        raise CargoError(exc.message, exc.status, exc.code) from exc
    reason = data.get("reason")
    if reason is not None and (not isinstance(reason, str) or len(reason.strip()) > 500):
        raise CargoError("reason must be short text", 422)
    if isinstance(data.get("version"), bool):
        raise CargoError("version conflict", 409)
    try:
        expected_version = int(data.get("version", 0))
    except (TypeError, ValueError):
        expected_version = 0
    if expected_version != row.version:
        raise CargoError("version conflict", 409)
    changes = {}

    def change(field, value):
        before = getattr(row, field)
        if before != value:
            changes[field] = (before, value)
            setattr(row, field, value)

    if "planned_quantity" in data:
        planned = _decimal(data.get("planned_quantity"), "planned_quantity")
        if planned is None:
            raise CargoError("planned_quantity must be positive", 422)
        if "quantity" in data and _decimal(
            data.get("quantity"), "quantity", required=True
        ) != planned:
            raise CargoError(
                "quantity compatibility value must equal planned_quantity",
                422,
                "PLANNED_QUANTITY_MISMATCH",
            )
        change("planned_quantity", planned)
        change("quantity", planned)
    elif "quantity" in data:
        if row.planned_quantity is not None:
            raise CargoError(
                "planned_quantity is required for this Cargo",
                422,
                "PLANNED_QUANTITY_REQUIRED",
            )
        change("quantity", _decimal(data.get("quantity"), "quantity", required=True))

    if "actual_quantity" in data:
        change(
            "actual_quantity",
            _decimal(data.get("actual_quantity"), "actual_quantity"),
        )
    immutable_inputs = {
        "catalog_item_public_id",
        "cargo_type_public_id",
        "uom_public_id",
        "display_name",
        "part_number",
        "customer_item_code",
        "brand",
        "model",
    }
    if immutable_inputs.intersection(data):
        raise CargoError("shipment cargo snapshots cannot be changed", 422)
    lineage_fields = {
        "cargo_owner_customer_id",
        "source_request_public_id",
        "source_request_cargo_item_public_id",
        "requested_quantity",
    }
    if lineage_fields.intersection(data):
        owner_data = {
            "cargo_owner_customer_id": data.get(
                "cargo_owner_customer_id", row.cargo_owner_customer_id
            )
        }
        owner = _cargo_owner(shipment, owner_data)
        lineage_data = {
            "source_request_public_id": row.source_shipment_request.public_id
            if row.source_shipment_request
            else None,
            "source_request_cargo_item_public_id": row.source_request_cargo_item.public_id
            if row.source_request_cargo_item
            else None,
            "requested_quantity": row.requested_quantity,
        }
        lineage_data.update({key: data[key] for key in lineage_fields if key in data})
        source_request, source_request_cargo, requested = _lineage(
            user, shipment, lineage_data, owner, row.uom
        )
        if row.cargo_owner_customer_id != owner.id:
            changes["cargo_owner_customer_id"] = (
                row.cargo_owner_customer_id,
                owner.id,
            )
            row.cargo_owner_customer = owner
        if row.source_shipment_request_id != (
            source_request.id if source_request else None
        ):
            changes["source_request_public_id"] = (
                row.source_shipment_request.public_id
                if row.source_shipment_request
                else None,
                source_request.public_id if source_request else None,
            )
            row.source_shipment_request = source_request
        if row.source_request_cargo_item_id != (
            source_request_cargo.id if source_request_cargo else None
        ):
            changes["source_request_cargo_item_public_id"] = (
                row.source_request_cargo_item.public_id
                if row.source_request_cargo_item
                else None,
                source_request_cargo.public_id if source_request_cargo else None,
            )
            row.source_request_cargo_item = source_request_cargo
        change("requested_quantity", requested)

    if "packaging_type_public_id" in data:
        packaging = _active_packaging(
            data.get("packaging_type_public_id"), shipment.organization_id
        )
        if row.packaging_type_id != (packaging.id if packaging else None):
            changes["packaging_type"] = (row.packaging_type, packaging)
            row.packaging_type = packaging
            row.packaging_code_snapshot = (
                packaging.immutable_code if packaging else None
            )
            row.packaging_fa_snapshot = packaging.fa_name if packaging else None
            row.packaging_en_snapshot = packaging.en_name if packaging else None

    def update_dimension(prefix, dimension):
        value_field = "gross_weight" if prefix == "gross_weight" else "volume"
        uom_field = f"{prefix}_uom"
        public_field = f"{prefix}_uom_public_id"
        if value_field not in data and public_field not in data:
            return
        raw_value = data.get(value_field, getattr(row, value_field))
        value = _decimal(raw_value, value_field)
        current_uom = getattr(row, uom_field)
        public_id = data.get(
            public_field, current_uom.public_id if current_uom else None
        )
        if value is None:
            if public_field in data and public_id:
                raise CargoError(f"{value_field} is required with its UOM", 422)
            uom_value = None
        else:
            uom_value = _active_uom(
                public_id,
                shipment.organization_id,
                dimension=dimension,
                field=uom_field,
            )
        change(value_field, value)
        if getattr(row, f"{uom_field}_id") != (uom_value.id if uom_value else None):
            changes[uom_field] = (current_uom, uom_value)
            setattr(row, uom_field, uom_value)
        setattr(
            row,
            f"{uom_field}_code_snapshot",
            uom_value.immutable_code if uom_value else None,
        )
        setattr(
            row,
            f"{uom_field}_symbol_snapshot",
            uom_value.symbol if uom_value else None,
        )

    update_dimension("gross_weight", "WEIGHT")
    update_dimension("volume", "VOLUME")

    if "hs_code" in data:
        change("hs_code_snapshot", _optional(data, "hs_code", 32))
    if "description" in data:
        change("description_snapshot", _optional(data, "description", 2000))
    if "destination_description" in data:
        change(
            "destination_description",
            _optional(data, "destination_description", 300),
        )
    if not changes:
        return row
    row.updated_by = user["id"]
    row.version += 1
    db.session.flush()
    _cargo_audit(user, shipment, row, "SHIPMENT_CARGO_UPDATED", changes, (reason.strip() or None) if isinstance(reason, str) else None)
    db.session.commit()
    return row
