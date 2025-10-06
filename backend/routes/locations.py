"""Location-related routes for provinces, counties, and cities."""
from flask import Blueprint, jsonify, request, current_app

from backend.models import City, County, Province, Country, InternationalCity, IranPort, PortProvinceMapping

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


@location_bp.get("/countries")
def list_countries():
    """Return a list of all active countries for international shipping."""
    countries = Country.query.filter_by(is_active=True).order_by(Country.name_fa).all()
    return jsonify(
        [
            {
                "id": country.id,
                "name": country.name_fa,
                "name_en": country.name_en,
                "code": country.code,
            }
            for country in countries
        ]
    )


@location_bp.get("/international-cities")
def list_international_cities():
    """Return international cities/ports filtered by the provided country ID."""
    country_id = request.args.get("country_id", type=int)
    if country_id is None:
        return (
            jsonify({"message": "شناسه کشور الزامی است."}),
            400,
        )

    cities = InternationalCity.query.filter_by(
        country_id=country_id, 
        is_active=True
    ).order_by(InternationalCity.name_fa).all()
    
    return jsonify(
        [
            {
                "id": city.id,
                "name": city.name_fa,
                "name_en": city.name_en,
                "city_type": city.city_type,
                "is_major_port": city.is_major_port,
                "is_major_airport": city.is_major_airport,
            }
            for city in cities
        ]
    )


@location_bp.get("/iran-ports")
def list_iran_ports():
    """Return a list of all active Iran ports."""
    port_type = request.args.get("port_type")  # Optional filter by port type
    
    query = IranPort.query.filter_by(is_active=True)
    if port_type:
        query = query.filter_by(port_type=port_type)
    
    ports = query.order_by(IranPort.name_fa).all()
    
    return jsonify(
        [
            {
                "id": port.id,
                "name_fa": port.name_fa,
                "name_en": port.name_en,
                "port_type": port.port_type,
                "province_id": port.province_id,
                "province_name": port.province.name_fa if port.province else None,
                "is_major_port": port.is_major_port,
                "description": port.description,
            }
            for port in ports
        ]
    )


@location_bp.get("/port-province-mappings")
def list_port_province_mappings():
    """Return port-province mappings for a specific port or province."""
    port_id = request.args.get("port_id", type=int)
    province_id = request.args.get("province_id", type=int)
    
    if not port_id and not province_id:
        return (
            jsonify({"message": "شناسه بندر یا استان الزامی است."}),
            400,
        )
    
    query = PortProvinceMapping.query
    if port_id:
        query = query.filter_by(port_id=port_id)
    if province_id:
        query = query.filter_by(province_id=province_id)
    
    mappings = query.order_by(PortProvinceMapping.suitability_score.desc()).all()
    
    return jsonify(
        [
            {
                "id": mapping.id,
                "port_id": mapping.port_id,
                "port_name": mapping.port.name_fa if mapping.port else None,
                "province_id": mapping.province_id,
                "province_name": mapping.province.name_fa if mapping.province else None,
                "suitability_score": mapping.suitability_score,
                "transport_method": mapping.transport_method,
                "estimated_days": mapping.estimated_days,
                "is_recommended": mapping.is_recommended,
            }
            for mapping in mappings
        ]
    )


@location_bp.get("/recommended-ports")
def get_recommended_ports():
    """Get recommended ports for a specific province based on suitability scores."""
    province_id = request.args.get("province_id", type=int)
    if province_id is None:
        return (
            jsonify({"message": "شناسه استان الزامی است."}),
            400,
        )
    
    # Get recommended ports for the province
    mappings = PortProvinceMapping.query.filter_by(
        province_id=province_id,
        is_recommended=True
    ).order_by(PortProvinceMapping.suitability_score.desc()).all()
    
    # Also get top 3 ports by suitability score even if not marked as recommended
    top_mappings = PortProvinceMapping.query.filter_by(
        province_id=province_id
    ).order_by(PortProvinceMapping.suitability_score.desc()).limit(3).all()
    
    # Combine and deduplicate
    all_mappings = {}
    for mapping in mappings + top_mappings:
        if mapping.port_id not in all_mappings:
            all_mappings[mapping.port_id] = mapping
    
    return jsonify(
        [
            {
                "port_id": mapping.port_id,
                "port_name_fa": mapping.port.name_fa if mapping.port else None,
                "port_name_en": mapping.port.name_en if mapping.port else None,
                "port_type": mapping.port.port_type if mapping.port else None,
                "suitability_score": mapping.suitability_score,
                "transport_method": mapping.transport_method,
                "estimated_days": mapping.estimated_days,
                "is_recommended": mapping.is_recommended,
                "description": mapping.port.description if mapping.port else None,
            }
            for mapping in sorted(all_mappings.values(), key=lambda x: x.suitability_score, reverse=True)
        ]
    )
