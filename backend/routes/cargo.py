"""Internal-only cargo catalog and shipment cargo APIs."""

from datetime import datetime
from flask import Blueprint, jsonify, request
from sqlalchemy import and_, case, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from backend.auth import get_current_user
from backend.cargo_models import (
    CargoCatalogItem,
    CargoItemAlias,
    ProjectCargoCatalogItem,
    ShipmentCargoItem,
)
from backend.extensions import db
from backend.security import require_auth
from backend.services import cargo_service as svc
from backend.services import multi_unit_tracking_service as tracking_svc
from backend.services.admin_authorization_service import (
    AdminAuthorizationError,
    ORGANIZATION_ADMIN,
    effective_authority,
    organization_context_for_authenticated_user,
    require_organization_admin_context,
)
from backend.models import ExpertUser
from backend.operational_models import Project

cargo_bp = Blueprint("cargo", __name__, url_prefix="/api/internal")


def _user():
    user = get_current_user()
    return {"id": user.id, "role": user.role} if hasattr(user, "id") else user


def _error(exc):
    db.session.rollback()
    if isinstance(exc, IntegrityError):
        return jsonify({"error": "conflicting cargo data"}), 409
    return jsonify({"error": str(exc)}), getattr(exc, "status", 400)


def _parse_tracking_datetime(value):
    if not isinstance(value, str) or not value.strip():
        raise tracking_svc.TrackingValidationError("occurred_at is required")
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise tracking_svc.TrackingValidationError("occurred_at must be an ISO-8601 datetime") from exc


def _cargo_options_organization(user):
    """Resolve the tenant for approved cargo selectors.

    Catalog administration is organization-admin scoped, while shipment cargo
    entry and Project Configuration are permission scoped.  Every path still
    derives exactly one active organization from the authenticated membership.
    """
    actor = db.session.get(ExpertUser, user["id"])
    if actor and effective_authority(actor) == ORGANIZATION_ADMIN:
        organization_context_for_authenticated_user(actor.id)
    else:
        try:
            svc.operational_service.require_permission(
                user, "operational_shipment.read"
            )
        except svc.operational_service.OperationalError:
            svc.operational_service.require_permission(
                user, "project_configuration.read"
            )
    return svc.org_for(user)


@cargo_bp.get("/cargo-catalog")
@require_organization_admin_context()
def catalog_list():
    try:
        return jsonify(svc.list_catalog(_user(), request.args))
    except (svc.CargoError, ValueError) as exc:
        return _error(exc)


@cargo_bp.post("/cargo-catalog")
@require_organization_admin_context()
def catalog_create():
    try:
        return jsonify(
            {
                "item": svc.catalog_dict(
                    svc.create_catalog(_user(), request.get_json(silent=True) or {}),
                    True,
                )
            }
        ), 201
    except (svc.CargoError, IntegrityError) as exc:
        return _error(exc)


@cargo_bp.get("/cargo-catalog/<public_id>")
@require_organization_admin_context()
def catalog_detail(public_id):
    try:
        return jsonify(
            {"item": svc.catalog_dict(svc.scoped_catalog(_user(), public_id), True)}
        )
    except svc.CargoError as exc:
        return _error(exc)


@cargo_bp.get("/cargo-catalog/<public_id>/shipments")
@require_organization_admin_context()
def catalog_shipments(public_id):
    try:
        return jsonify(svc.catalog_shipment_usage(_user(), public_id, request.args))
    except (svc.CargoError, svc.operational_service.OperationalError) as exc:
        return _error(exc)


@cargo_bp.patch("/cargo-catalog/<public_id>")
@require_organization_admin_context()
def catalog_update(public_id):
    try:
        return jsonify(
            {
                "item": svc.catalog_dict(
                    svc.update_catalog(
                        _user(),
                        svc.scoped_catalog(_user(), public_id),
                        request.get_json(silent=True) or {},
                    ),
                    True,
                )
            }
        )
    except (svc.CargoError, IntegrityError) as exc:
        return _error(exc)


@cargo_bp.post("/cargo-catalog/<public_id>/<action>")
@require_organization_admin_context()
def catalog_activation(public_id, action):
    if action not in {"activate", "deactivate"}:
        return jsonify({"error": "not found"}), 404
    try:
        return jsonify(
            {
                "item": svc.catalog_dict(
                    svc.set_catalog_active(
                        _user(),
                        svc.scoped_catalog(_user(), public_id),
                        action == "activate",
                        request.get_json(silent=True) or {},
                    ),
                    True,
                )
            }
        )
    except svc.CargoError as exc:
        return _error(exc)


@cargo_bp.get("/cargo-catalog/<public_id>/aliases")
@require_organization_admin_context()
def aliases(public_id):
    try:
        return jsonify(
            {
                "items": [
                    svc.alias_dict(a)
                    for a in svc.scoped_catalog(_user(), public_id).aliases
                ]
            }
        )
    except svc.CargoError as exc:
        return _error(exc)


@cargo_bp.post("/cargo-catalog/<public_id>/aliases")
@require_organization_admin_context()
def alias_create(public_id):
    try:
        return jsonify(
            {
                "item": svc.alias_dict(
                    svc.create_alias(
                        _user(),
                        svc.scoped_catalog(_user(), public_id),
                        request.get_json(silent=True) or {},
                    )
                )
            }
        ), 201
    except (svc.CargoError, IntegrityError) as exc:
        return _error(exc)


@cargo_bp.patch("/cargo-catalog/<public_id>/aliases/<alias_id>")
@require_organization_admin_context()
def alias_update(public_id, alias_id):
    try:
        item = svc.scoped_catalog(_user(), public_id)
        return jsonify(
            {
                "item": svc.alias_dict(
                    svc.update_alias(
                        _user(),
                        svc.scoped_alias(item, alias_id),
                        request.get_json(silent=True) or {},
                    )
                )
            }
        )
    except (svc.CargoError, IntegrityError) as exc:
        return _error(exc)


@cargo_bp.post("/cargo-catalog/<public_id>/aliases/<alias_id>/deactivate")
@require_organization_admin_context()
def alias_deactivate(public_id, alias_id):
    try:
        item = svc.scoped_catalog(_user(), public_id)
        return jsonify(
            {
                "item": svc.alias_dict(
                    svc.update_alias(
                        _user(), svc.scoped_alias(item, alias_id), {"is_active": False}
                    )
                )
            }
        )
    except svc.CargoError as exc:
        return _error(exc)


@cargo_bp.get("/operational-shipments/<shipment_id>/cargo-items")
@require_auth
def shipment_items(shipment_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        rows = db.session.scalars(
            select(ShipmentCargoItem)
            .where(ShipmentCargoItem.operational_shipment_id == shipment.id)
            .options(
                selectinload(ShipmentCargoItem.catalog_item),
                selectinload(ShipmentCargoItem.cargo_type),
                selectinload(ShipmentCargoItem.uom),
            )
            .order_by(ShipmentCargoItem.line_number)
        ).all()
        return jsonify({"items": [svc.shipment_item_dict(r) for r in rows]})
    except svc.CargoError as exc:
        return _error(exc)


@cargo_bp.get("/cargo-options")
@require_auth
def cargo_options():
    try:
        user = _user()
        org = _cargo_options_organization(user)
        from backend.models import CargoType, UnitOfMeasure

        project = None
        project_public_id = str(request.args.get("project_public_id") or "").strip()
        if project_public_id:
            project = db.session.scalar(
                select(Project).where(
                    Project.public_id == project_public_id,
                    Project.organization_id == org,
                )
            )
            if not project:
                raise svc.CargoError("project not found", 404)

        preference_join = and_(
            ProjectCargoCatalogItem.cargo_catalog_item_id == CargoCatalogItem.id,
            ProjectCargoCatalogItem.project_id == (project.id if project else -1),
            ProjectCargoCatalogItem.organization_id == org,
            ProjectCargoCatalogItem.is_active.is_(True),
        )
        query = (
            select(CargoCatalogItem, ProjectCargoCatalogItem)
            .outerjoin(ProjectCargoCatalogItem, preference_join)
            .where(
                CargoCatalogItem.organization_id == org,
                CargoCatalogItem.is_active.is_(True),
            )
            .options(
                selectinload(CargoCatalogItem.cargo_type),
                selectinload(CargoCatalogItem.default_uom),
            )
        )
        raw_q = str(request.args.get("q") or "").strip()
        if len(raw_q) > 200:
            raise svc.CargoError("q is too long", 422)
        if raw_q:
            normalized = f"%{svc.normalize_text(raw_q)}%"
            contains = f"%{raw_q}%"
            query = query.where(
                or_(
                    CargoCatalogItem.search_text.like(normalized),
                    CargoCatalogItem.immutable_code.ilike(contains),
                    CargoCatalogItem.fa_name.ilike(contains),
                    CargoCatalogItem.en_name.ilike(contains),
                    CargoCatalogItem.part_number.ilike(contains),
                    CargoCatalogItem.customer_item_code.ilike(contains),
                    CargoCatalogItem.hs_code.ilike(contains),
                    CargoCatalogItem.brand.ilike(contains),
                    CargoCatalogItem.model.ilike(contains),
                    CargoCatalogItem.aliases.any(
                        and_(
                            CargoItemAlias.is_active.is_(True),
                            CargoItemAlias.normalized_alias.like(normalized),
                        )
                    ),
                )
            )
        query = query.order_by(
            case((ProjectCargoCatalogItem.id.is_not(None), 0), else_=1),
            ProjectCargoCatalogItem.display_order,
            CargoCatalogItem.fa_name,
            CargoCatalogItem.immutable_code,
            CargoCatalogItem.id,
        )
        catalog = db.session.execute(
            query
            .limit(100)
        ).all()
        cargo_types = db.session.scalars(
            select(CargoType)
            .where(CargoType.is_active.is_(True))
            .order_by(CargoType.display_order)
        ).all()
        uoms = db.session.scalars(
            select(UnitOfMeasure)
            .where(UnitOfMeasure.is_active.is_(True))
            .order_by(UnitOfMeasure.display_order)
        ).all()
        return jsonify(
            {
                "catalog": [
                    {
                        "public_id": r.public_id,
                        "code": r.immutable_code,
                        "name": r.fa_name,
                        "preferred": preference is not None,
                        "preference_order": preference.display_order
                        if preference
                        else None,
                        "cargo_type_public_id": r.cargo_type.public_id,
                        "default_uom_public_id": r.default_uom.public_id
                        if r.default_uom
                        else None,
                    }
                    for r, preference in catalog
                ],
                "cargo_types": [
                    {
                        "public_id": r.public_id,
                        "code": r.immutable_code,
                        "name": r.fa_name,
                    }
                    for r in cargo_types
                ],
                "uoms": [
                    {
                        "public_id": r.public_id,
                        "code": r.immutable_code,
                        "name": r.fa_name,
                        "symbol": r.symbol,
                    }
                    for r in uoms
                ],
            }
        )
    except (svc.CargoError, svc.operational_service.OperationalError, AdminAuthorizationError) as exc:
        return _error(exc)


@cargo_bp.post("/operational-shipments/<shipment_id>/cargo-items")
@require_auth
def shipment_item_create(shipment_id):
    try:
        return jsonify(
            {
                "item": svc.shipment_item_dict(
                    svc.create_shipment_item(
                        _user(),
                        svc.scoped_shipment(_user(), shipment_id),
                        request.get_json(silent=True) or {},
                    )
                )
            }
        ), 201
    except (svc.CargoError, IntegrityError) as exc:
        return _error(exc)


def _shipment_item(shipment, item_id):
    row = db.session.scalar(
        select(ShipmentCargoItem).where(
            ShipmentCargoItem.public_id == item_id,
            ShipmentCargoItem.operational_shipment_id == shipment.id,
        )
    )
    if not row:
        raise svc.CargoError("not found", 404)
    return row


@cargo_bp.get("/operational-shipments/<shipment_id>/cargo-items/<item_id>")
@require_auth
def shipment_item_detail(shipment_id, item_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        return jsonify(
            {"item": svc.shipment_item_dict(_shipment_item(shipment, item_id))}
        )
    except svc.CargoError as exc:
        return _error(exc)


@cargo_bp.patch("/operational-shipments/<shipment_id>/cargo-items/<item_id>")
@require_auth
def shipment_item_update(shipment_id, item_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        row = _shipment_item(shipment, item_id)
        return jsonify(
            {
                "item": svc.shipment_item_dict(
                    svc.update_shipment_item(
                        _user(), row, request.get_json(silent=True) or {}
                    )
                )
            }
        )
    except svc.CargoError as exc:
        return _error(exc)


@cargo_bp.get("/operational-shipments/<shipment_id>/cargo-transport-allocations")
@require_auth
def allocation_list(shipment_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        return jsonify(svc.shipment_allocation_view(_user(), shipment))
    except svc.CargoError as exc: return _error(exc)


@cargo_bp.post("/operational-shipments/<shipment_id>/transport-units")
@require_auth
def allocation_transport_create(shipment_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        row = svc.create_transport_unit(_user(), shipment, request.get_json(silent=True) or {})
        return jsonify({"transport_unit": {"id": row.id, "unit_code": row.unit_code, "unit_type": row.unit_type}}), 201
    except svc.CargoError as exc: return _error(exc)


@cargo_bp.get("/operational-shipments/<shipment_id>/transport-tracking")
@require_auth
def operational_transport_tracking(shipment_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        return jsonify({"source_type": shipment.source_type, "tracking": tracking_svc.build_internal_tracking_for_shipment(shipment)})
    except svc.CargoError as exc: return _error(exc)


@cargo_bp.post("/operational-shipments/<shipment_id>/transport-tracking/enable")
@require_auth
def operational_transport_tracking_enable(shipment_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        tracking_svc.enable_tracking_for_shipment(shipment, _user()["id"])
        db.session.commit()
        return jsonify({"source_type": shipment.source_type, "tracking": tracking_svc.build_internal_tracking_for_shipment(shipment)})
    except (svc.CargoError, tracking_svc.TrackingValidationError) as exc:
        db.session.rollback(); return _error(exc)


@cargo_bp.post("/operational-shipments/<shipment_id>/transport-units/<int:unit_id>/tracking-updates")
@require_auth
def operational_transport_tracking_update(shipment_id, unit_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        unit = db.session.get(tracking_svc.ShipmentTransportUnit, unit_id)
        tracking = tracking_svc.tracking_for_shipment(shipment)
        if not unit or not tracking or unit.tracking_id != tracking.id or unit.operational_shipment_id != shipment.id:
            raise svc.CargoError("transport unit not found", 404)
        data = request.get_json(silent=True) or {}
        if any(key in data for key in ("organization_id", "operational_organization_id")):
            raise svc.CargoError("organization override is not allowed", 403)
        tracking_svc.add_update(unit, _user()["id"], status=data.get("status"), occurred_at=_parse_tracking_datetime(data.get("occurred_at")), location=data.get("location"), logistics_point_public_id=data.get("logistics_point_public_id"), location_reference_id=data.get("location_reference_id"), location_text=data.get("location_text"), customer_message=data.get("customer_message"), internal_note=data.get("internal_note"), is_customer_visible=data.get("is_customer_visible", True))
        db.session.commit()
        return jsonify({"tracking": tracking_svc.build_internal_tracking_for_shipment(shipment)}), 201
    except (svc.CargoError, tracking_svc.TrackingValidationError) as exc:
        db.session.rollback(); return _error(exc)


@cargo_bp.post("/operational-shipments/<shipment_id>/cargo-transport-allocations")
@require_auth
def allocation_create(shipment_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        return jsonify({"allocation": svc.allocation_dict(svc.save_allocation(_user(), shipment, request.get_json(silent=True) or {}))}), 201
    except (svc.CargoError, IntegrityError) as exc: return _error(exc)


@cargo_bp.patch("/operational-shipments/<shipment_id>/cargo-transport-allocations/<allocation_id>")
@require_auth
def allocation_update(shipment_id, allocation_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        from backend.cargo_models import ShipmentCargoTransportAllocation
        row = db.session.scalar(select(ShipmentCargoTransportAllocation).where(ShipmentCargoTransportAllocation.public_id == allocation_id, ShipmentCargoTransportAllocation.operational_shipment_id == shipment.id))
        if not row: raise svc.CargoError("not found", 404)
        return jsonify({"allocation": svc.allocation_dict(svc.save_allocation(_user(), shipment, request.get_json(silent=True) or {}, row))})
    except svc.CargoError as exc: return _error(exc)


@cargo_bp.delete("/operational-shipments/<shipment_id>/cargo-transport-allocations/<allocation_id>")
@require_auth
def allocation_delete(shipment_id, allocation_id):
    try:
        shipment = svc.scoped_shipment(_user(), shipment_id)
        svc.delete_allocation(_user(), shipment, allocation_id)
        return "", 204
    except svc.CargoError as exc: return _error(exc)
