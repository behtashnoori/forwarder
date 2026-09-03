"""Internal-only cargo catalog and shipment cargo APIs."""

from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from backend.auth import get_current_user
from backend.cargo_models import ShipmentCargoItem
from backend.extensions import db
from backend.security import require_auth
from backend.services import cargo_service as svc
from backend.services.admin_authorization_service import (
    AdminAuthorizationError,
    ORGANIZATION_ADMIN,
    effective_authority,
    organization_context_for_authenticated_user,
    require_organization_admin_context,
)
from backend.models import ExpertUser

cargo_bp = Blueprint("cargo", __name__, url_prefix="/api/internal")


def _user():
    user = get_current_user()
    return {"id": user.id, "role": user.role} if hasattr(user, "id") else user


def _error(exc):
    db.session.rollback()
    if isinstance(exc, IntegrityError):
        return jsonify({"error": "conflicting cargo data"}), 409
    return jsonify({"error": str(exc)}), getattr(exc, "status", 400)


def _cargo_options_organization(user):
    """Resolve the tenant for the two approved cargo-options consumers.

    Catalog administration is organization-admin scoped, while shipment cargo
    entry is permission scoped.  Both paths must still derive exactly one
    active organization from the authenticated user's membership.
    """
    actor = db.session.get(ExpertUser, user["id"])
    if actor and effective_authority(actor) == ORGANIZATION_ADMIN:
        organization_context_for_authenticated_user(actor.id)
    else:
        svc.operational_service.require_permission(user, "operational_shipment.read")
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
        from backend.cargo_models import CargoCatalogItem
        from backend.models import CargoType, UnitOfMeasure

        catalog = db.session.scalars(
            select(CargoCatalogItem)
            .where(
                CargoCatalogItem.organization_id == org,
                CargoCatalogItem.is_active.is_(True),
            )
            .options(
                selectinload(CargoCatalogItem.cargo_type),
                selectinload(CargoCatalogItem.default_uom),
            )
            .order_by(CargoCatalogItem.fa_name)
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
                        "cargo_type_public_id": r.cargo_type.public_id,
                        "default_uom_public_id": r.default_uom.public_id
                        if r.default_uom
                        else None,
                    }
                    for r in catalog
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
