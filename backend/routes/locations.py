"""Location-related routes for provinces, counties, and cities."""
from flask import Blueprint, jsonify, request

from backend.models import City, County, Province

location_bp = Blueprint("location", __name__, url_prefix="/api")


@location_bp.get("/provinces")
def list_provinces():
    """Return a list of all provinces."""
    provinces = Province.query.all()
    return jsonify(
        [
            {
                "id": province.id,
                "name": province.name_fa,
                "code": province.code,
            }
            for province in provinces
        ]
    )


@location_bp.get("/counties")
def list_counties():
    """Return counties filtered by the provided province ID."""
    province_id = request.args.get("province_id", type=int)
    if province_id is None:
        return (
            jsonify({"message": "شناسه استان الزامی است."}),
            400,
        )

    counties = County.query.filter_by(province_id=province_id).all()
    return jsonify(
        [
            {
                "id": county.id,
                "name": county.name_fa,
            }
            for county in counties
        ]
    )


@location_bp.get("/cities")
def list_cities():
    """Return cities filtered by the provided county ID."""
    county_id = request.args.get("county_id", type=int)
    if county_id is None:
        return (
            jsonify({"message": "شناسه شهرستان الزامی است."}),
            400,
        )

    cities = City.query.filter_by(county_id=county_id).all()
    return jsonify(
        [
            {
                "id": city.id,
                "name": city.name_fa,
            }
            for city in cities
        ]
    )
