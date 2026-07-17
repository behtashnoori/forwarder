from flask import Blueprint,jsonify,request
from sqlalchemy.exc import IntegrityError

from backend.auth import get_current_user
from backend.extensions import db
from backend.models import TrackingLocationReference
from backend.security import require_auth,require_role
from backend.services import tracking_location_service
from backend.services.multi_unit_tracking_service import TrackingValidationError

tracking_locations_bp=Blueprint("tracking_locations",__name__,url_prefix="/api/tracking-locations")

@tracking_locations_bp.get("")
@require_auth
def list_locations():
    admin=(get_current_user() or {}).get("role")=="admin"
    rows=tracking_location_service.search(query=request.args.get("q"),country=request.args.get("country"),location_type=request.args.get("location_type"),include_inactive=admin and request.args.get("include_inactive")=="true")
    return jsonify({"items":[tracking_location_service.serialize(x,admin=admin) for x in rows]})

@tracking_locations_bp.post("")
@require_role("admin")
def create_location():
    try:
        row=tracking_location_service.apply_fields(TrackingLocationReference(),request.get_json(silent=True) or {},creating=True); db.session.add(row);db.session.commit()
        return jsonify(tracking_location_service.serialize(row,admin=True)),201
    except TrackingValidationError as e: db.session.rollback();return jsonify({"error":str(e)}),400
    except IntegrityError: db.session.rollback();return jsonify({"error":"internal_key already exists"}),409

@tracking_locations_bp.patch("/<int:location_id>")
@require_role("admin")
def update_location(location_id):
    row=db.session.get(TrackingLocationReference,location_id)
    if not row:return jsonify({"error":"tracking location not found"}),404
    try: tracking_location_service.apply_fields(row,request.get_json(silent=True) or {});db.session.commit();return jsonify(tracking_location_service.serialize(row,admin=True))
    except TrackingValidationError as e: db.session.rollback();return jsonify({"error":str(e)}),400
    except IntegrityError: db.session.rollback();return jsonify({"error":"internal_key already exists"}),409

@tracking_locations_bp.delete("/<int:location_id>")
@require_role("admin")
def deactivate_location(location_id):
    row=db.session.get(TrackingLocationReference,location_id)
    if not row:return jsonify({"error":"tracking location not found"}),404
    row.is_active=False;row.reference_status="inactive";db.session.commit();return jsonify(tracking_location_service.serialize(row,admin=True))
