"""Public tracking API routes for customers to track their requests."""
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import ShipmentRequest, Province, County, City, ExpertUser

public_tracking_bp = Blueprint("public_tracking", __name__, url_prefix="/api/public")


@public_tracking_bp.get("/track/<int:request_id>")
def get_public_tracking_info(request_id: int):
    """Get public tracking information for a shipment request."""
    try:
        # Get the shipment request
        req = db.session.query(ShipmentRequest).filter(
            ShipmentRequest.id == request_id
        ).first()
        
        if not req:
            return jsonify({"message": "درخواست یافت نشد"}), 404
        
        # Get location information
        origin_province = None
        origin_county = None
        origin_city = None
        dest_province = None
        dest_county = None
        dest_city = None
        
        if req.shipping_type == "domestic":
            if req.origin_province_id:
                origin_province = db.session.query(Province).filter(
                    Province.id == req.origin_province_id
                ).first()
            if req.origin_county_id:
                origin_county = db.session.query(County).filter(
                    County.id == req.origin_county_id
                ).first()
            if req.origin_city_id:
                origin_city = db.session.query(City).filter(
                    City.id == req.origin_city_id
                ).first()
            if req.dest_province_id:
                dest_province = db.session.query(Province).filter(
                    Province.id == req.dest_province_id
                ).first()
            if req.dest_county_id:
                dest_county = db.session.query(County).filter(
                    County.id == req.dest_county_id
                ).first()
            if req.dest_city_id:
                dest_city = db.session.query(City).filter(
                    City.id == req.dest_city_id
                ).first()
        
        # Get assigned expert
        assigned_expert = None
        if req.assigned_to:
            assigned_expert = db.session.query(ExpertUser).filter(
                ExpertUser.id == req.assigned_to
            ).first()
        
        # Build response with limited information for public access
        response_data = {
            "id": req.id,
            "tracking_number": f"SR{req.id:06d}",
            "status": req.status,
            "created_at": req.created_at.isoformat(),
            "shipping_type": req.shipping_type,
            "contact_phone": req.contact_phone,
            "customer_first_name": req.customer_first_name,
            "customer_last_name": req.customer_last_name,
            "route": {
                "origin": {
                    "province": origin_province.name_fa if origin_province else None,
                    "county": origin_county.name_fa if origin_county else None,
                    "city": origin_city.name_fa if origin_city else None,
                    "country": req.origin_country,
                    "city_international": req.origin_city_international
                },
                "destination": {
                    "province": dest_province.name_fa if dest_province else None,
                    "county": dest_county.name_fa if dest_county else None,
                    "city": dest_city.name_fa if dest_city else None,
                    "country": req.dest_country,
                    "city_international": req.dest_city_international
                }
            },
            "assigned_expert": {
                "id": assigned_expert.id,
                "full_name": assigned_expert.full_name,
                "phone": assigned_expert.phone
            } if assigned_expert else None
        }
        
        return jsonify(response_data), 200
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in public tracking: {e}")
        return jsonify({"message": "خطا در دریافت اطلاعات"}), 500
    except Exception as e:
        current_app.logger.error(f"Error in public tracking: {e}")
        return jsonify({"message": "خطای داخلی سرور"}), 500

