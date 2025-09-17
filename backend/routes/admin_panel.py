"""Admin panel routes for shipment request insights."""
from flask import Blueprint, jsonify

from backend.models import City, County, Province, ShipmentRequest

admin_bp = Blueprint("admin_panel", __name__, url_prefix="/api")


@admin_bp.get("/shipment-request/<int:request_id>")
def get_shipment_request_detail(request_id: int):
    """Return a shipment request with human-readable location names."""
    shipment_request = ShipmentRequest.query.get(request_id)
    if shipment_request is None:
        return jsonify({"message": "درخواست موردنظر یافت نشد."}), 404

    origin_province = Province.query.get(shipment_request.origin_province_id)
    origin_county = County.query.get(shipment_request.origin_county_id)
    origin_city = City.query.get(shipment_request.origin_city_id)

    dest_province = Province.query.get(shipment_request.dest_province_id)
    dest_county = County.query.get(shipment_request.dest_county_id)
    dest_city = City.query.get(shipment_request.dest_city_id)

    response = {
        "id": shipment_request.id,
        "contact_phone": shipment_request.contact_phone,
        "origin": {
            "province": origin_province.name_fa if origin_province else None,
            "county": origin_county.name_fa if origin_county else None,
            "city": origin_city.name_fa if origin_city else None,
        },
        "destination": {
            "province": dest_province.name_fa if dest_province else None,
            "county": dest_county.name_fa if dest_county else None,
            "city": dest_city.name_fa if dest_city else None,
        },
        "created_at": shipment_request.created_at.isoformat()
        if shipment_request.created_at
        else None,
    }

    return jsonify(response)


@admin_bp.get("/shipment-requests")
def list_shipment_requests():
    """Return the 50 most recent shipment requests with location names."""
    shipment_requests = (
        ShipmentRequest.query.order_by(ShipmentRequest.created_at.desc())
        .limit(50)
        .all()
    )

    origin_province_ids = {
        req.origin_province_id
        for req in shipment_requests
        if req.origin_province_id is not None
    }
    origin_county_ids = {
        req.origin_county_id
        for req in shipment_requests
        if req.origin_county_id is not None
    }
    origin_city_ids = {
        req.origin_city_id for req in shipment_requests if req.origin_city_id is not None
    }

    dest_province_ids = {
        req.dest_province_id
        for req in shipment_requests
        if req.dest_province_id is not None
    }
    dest_county_ids = {
        req.dest_county_id for req in shipment_requests if req.dest_county_id is not None
    }
    dest_city_ids = {
        req.dest_city_id for req in shipment_requests if req.dest_city_id is not None
    }

    province_ids = origin_province_ids | dest_province_ids
    county_ids = origin_county_ids | dest_county_ids
    city_ids = origin_city_ids | dest_city_ids

    provinces = (
        Province.query.filter(Province.id.in_(province_ids)).all() if province_ids else []
    )
    counties = (
        County.query.filter(County.id.in_(county_ids)).all() if county_ids else []
    )
    cities = City.query.filter(City.id.in_(city_ids)).all() if city_ids else []

    province_lookup = {province.id: province.name_fa for province in provinces}
    county_lookup = {county.id: county.name_fa for county in counties}
    city_lookup = {city.id: city.name_fa for city in cities}

    response = []
    for shipment_request in shipment_requests:
        response.append(
            {
                "id": shipment_request.id,
                "contact_phone": shipment_request.contact_phone,
                "origin": {
                    "province": province_lookup.get(shipment_request.origin_province_id),
                    "county": county_lookup.get(shipment_request.origin_county_id),
                    "city": city_lookup.get(shipment_request.origin_city_id),
                },
                "destination": {
                    "province": province_lookup.get(shipment_request.dest_province_id),
                    "county": county_lookup.get(shipment_request.dest_county_id),
                    "city": city_lookup.get(shipment_request.dest_city_id),
                },
                "created_at": shipment_request.created_at.isoformat()
                if shipment_request.created_at
                else None,
            }
        )

    return jsonify(response)
