"""Admin CRUD API for origin/destination reference geography.

Exposes admin-only create/update/deactivate for the entities that back the
shipment-request origin/destination pickers (domestic Province/County/City,
international Country/InternationalCity, and Iran entry ports). Public read
endpoints for the customer-facing form stay in ``locations.py``; these routes
are for management and include inactive rows.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import (
    City,
    Country,
    County,
    InternationalCity,
    IranPort,
    Province,
)
from backend.security import require_role
from backend.services import location_admin_service as svc
from backend.services.admin_authorization_service import require_organization_admin_context, require_platform_admin

location_admin_bp = Blueprint("location_admin", __name__, url_prefix="/api/admin/locations")


# Each resource maps a URL segment to its model, serializer, and CRUD callables.
# ``list_kwargs`` pulls optional query-string filters (parent ids) for the list view.
_RESOURCES = {
    "provinces": {
        "model": Province,
        "serialize": svc.serialize_province,
        "list": svc.list_provinces,
        "create": svc.create_province,
        "update": svc.update_province,
        "list_kwargs": lambda args: {},
    },
    "counties": {
        "model": County,
        "serialize": svc.serialize_county,
        "list": svc.list_counties,
        "create": svc.create_county,
        "update": svc.update_county,
        "list_kwargs": lambda args: {"province_id": args.get("province_id", type=int)},
    },
    "cities": {
        "model": City,
        "serialize": svc.serialize_city,
        "list": svc.list_cities,
        "create": svc.create_city,
        "update": svc.update_city,
        "list_kwargs": lambda args: {
            "county_id": args.get("county_id", type=int),
            "province_id": args.get("province_id", type=int),
        },
    },
    "countries": {
        "model": Country,
        "serialize": svc.serialize_country,
        "list": svc.list_countries,
        "create": svc.create_country,
        "update": svc.update_country,
        "list_kwargs": lambda args: {},
    },
    "international-cities": {
        "model": InternationalCity,
        "serialize": svc.serialize_international_city,
        "list": svc.list_international_cities,
        "create": svc.create_international_city,
        "update": svc.update_international_city,
        "list_kwargs": lambda args: {"country_id": args.get("country_id", type=int)},
    },
    "iran-ports": {
        "model": IranPort,
        "serialize": svc.serialize_iran_port,
        "list": svc.list_iran_ports,
        "create": svc.create_iran_port,
        "update": svc.update_iran_port,
        "list_kwargs": lambda args: {},
    },
}


def _resource_or_404(resource):
    cfg = _RESOURCES.get(resource)
    if cfg is None:
        return None, (jsonify({"error": "unknown resource"}), 404)
    return cfg, None


def _error(message, status=400):
    db.session.rollback()
    return jsonify({"error": message}), status


@location_admin_bp.get("/<resource>")
@require_organization_admin_context()
def list_resource(resource):
    cfg, err = _resource_or_404(resource)
    if err:
        return err
    include_inactive = request.args.get("include_inactive") == "true"
    kwargs = {k: v for k, v in cfg["list_kwargs"](request.args).items() if v is not None}
    rows = cfg["list"](include_inactive=include_inactive, **kwargs)
    return jsonify({"items": [cfg["serialize"](row) for row in rows]})


@location_admin_bp.post("/<resource>")
@require_platform_admin()
def create_resource(resource):
    cfg, err = _resource_or_404(resource)
    if err:
        return err
    try:
        row = cfg["create"](request.get_json(silent=True) or {})
        return jsonify({"item": cfg["serialize"](row)}), 201
    except svc.LocationValidationError as exc:
        return _error(str(exc))
    except IntegrityError:
        return _error("conflicting reference data", 409)


@location_admin_bp.put("/<resource>/<int:entity_id>")
@location_admin_bp.patch("/<resource>/<int:entity_id>")
@require_platform_admin()
def update_resource(resource, entity_id):
    cfg, err = _resource_or_404(resource)
    if err:
        return err
    row = db.session.get(cfg["model"], entity_id)
    if row is None:
        return jsonify({"error": "not found"}), 404
    try:
        row = cfg["update"](row, request.get_json(silent=True) or {})
        return jsonify({"item": cfg["serialize"](row)})
    except svc.LocationValidationError as exc:
        return _error(str(exc))
    except IntegrityError:
        return _error("conflicting reference data", 409)


@location_admin_bp.delete("/<resource>/<int:entity_id>")
@require_platform_admin()
def deactivate_resource(resource, entity_id):
    cfg, err = _resource_or_404(resource)
    if err:
        return err
    row = db.session.get(cfg["model"], entity_id)
    if row is None:
        return jsonify({"error": "not found"}), 404
    svc.deactivate(row)
    return jsonify({"item": cfg["serialize"](row)})
