"""Location-related routes for provinces, counties, and cities."""
from flask import Blueprint, jsonify, request, current_app

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


# Add a direct route for /provinces (without /api prefix)
from flask import Blueprint

provinces_bp = Blueprint("provinces", __name__)

@provinces_bp.route("/provinces", methods=["GET", "OPTIONS"])
def list_provinces_direct():
    """Return a list of all provinces (direct route for frontend compatibility)."""
    
    # Get the origin from request headers
    origin = request.headers.get('Origin')
    
    # List of allowed origins
    allowed_origins = [
        'http://localhost:3000',
        'http://localhost:5173', 
        'http://localhost:8080',
        'http://localhost:8084',
        'http://localhost:8085',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5173',
        'http://127.0.0.1:8080',
        'http://127.0.0.1:8084',
        'http://127.0.0.1:8085'
    ]
    
    # Use the requesting origin if it's allowed, otherwise use wildcard for development
    cors_origin = origin if origin in allowed_origins else '*'
    
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', cors_origin)
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        # Use raw SQL to avoid relationship issues
        from backend.extensions import db
        result = db.session.execute(db.text("SELECT id, name_fa, code FROM province"))
        provinces = result.fetchall()
    except Exception as e:
        current_app.logger.error(f"Error querying provinces: {e}")
        return jsonify({"error": "خطا در دریافت استان‌ها"}), 500
    
    response = jsonify(
        [
            {
                "id": province.id,
                "name": province.name_fa,
                "code": province.code,
            }
            for province in provinces
        ]
    )
    
    # Add CORS headers manually with dynamic origin
    response.headers.add('Access-Control-Allow-Origin', cors_origin)
    response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    
    return response


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
