"""Seed script to create Iran ports and port-province mapping data."""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from backend.__init__ import create_app
from backend.models import Province, IranPort, PortProvinceMapping
from backend.extensions import db

def seed_iran_ports():
    """Create Iran ports and port-province mapping data."""
    app = create_app()
    
    with app.app_context():
        # Check if Iran ports already exist
        try:
            if IranPort.query.count() > 0:
                print("Iran ports data already exists. Skipping seed.")
                return
        except Exception as e:
            print(f"Tables not created yet, proceeding with seed: {e}")
        
        # First, ensure we have Iran provinces
        iran_provinces = {
            "تهران": {"code": "TEH", "id": None},
            "اصفهان": {"code": "ISF", "id": None},
            "شیراز": {"code": "FAR", "id": None},
            "مشهد": {"code": "KHO", "id": None},
            "تبریز": {"code": "EAZ", "id": None},
            "اهواز": {"code": "KHU", "id": None},
            "کرمان": {"code": "KER", "id": None},
            "رشت": {"code": "GIL", "id": None},
            "بندرعباس": {"code": "HOR", "id": None},
            "بوشهر": {"code": "BUS", "id": None},
            "خرمشهر": {"code": "KHU", "id": None},
            "چابهار": {"code": "SIS", "id": None},
            "انزلی": {"code": "GIL", "id": None},
            "ماهشهر": {"code": "KHU", "id": None},
            "امام خمینی": {"code": "KHU", "id": None},
        }
        
        # Get or create provinces
        for province_name, province_data in iran_provinces.items():
            province = Province.query.filter_by(name_fa=province_name).first()
            if not province:
                province = Province(
                    name_fa=province_name,
                    code=province_data["code"]
                )
                db.session.add(province)
                db.session.flush()
            iran_provinces[province_name]["id"] = province.id
        
        # Iran ports data
        iran_ports_data = [
            {
                "name_fa": "بندرعباس",
                "name_en": "Bandar Abbas",
                "port_type": "sea",
                "province_name": "بندرعباس",
                "description": "بندر اصلی جنوب ایران در خلیج فارس",
                "is_major_port": True
            },
            {
                "name_fa": "بوشهر",
                "name_en": "Bushehr",
                "port_type": "sea",
                "province_name": "بوشهر",
                "description": "بندر مهم جنوب ایران",
                "is_major_port": True
            },
            {
                "name_fa": "امام خمینی",
                "name_en": "Imam Khomeini",
                "port_type": "sea",
                "province_name": "اهواز",
                "description": "بندر بزرگ جنوب غرب ایران",
                "is_major_port": True
            },
            {
                "name_fa": "خرمشهر",
                "name_en": "Khorramshahr",
                "port_type": "sea",
                "province_name": "اهواز",
                "description": "بندر در مرز عراق",
                "is_major_port": True
            },
            {
                "name_fa": "ماهشهر",
                "name_en": "Mahshahr",
                "port_type": "sea",
                "province_name": "اهواز",
                "description": "بندر صنعتی جنوب",
                "is_major_port": True
            },
            {
                "name_fa": "چابهار",
                "name_en": "Chabahar",
                "port_type": "sea",
                "province_name": "چابهار",
                "description": "بندر آزاد در دریای عمان",
                "is_major_port": True
            },
            {
                "name_fa": "انزلی",
                "name_en": "Anzali",
                "port_type": "sea",
                "province_name": "رشت",
                "description": "بندر شمال ایران در دریای خزر",
                "is_major_port": True
            },
            {
                "name_fa": "تهران",
                "name_en": "Tehran",
                "port_type": "air",
                "province_name": "تهران",
                "description": "فرودگاه بین‌المللی امام خمینی",
                "is_major_port": True
            },
            {
                "name_fa": "مشهد",
                "name_en": "Mashhad",
                "port_type": "air",
                "province_name": "مشهد",
                "description": "فرودگاه بین‌المللی مشهد",
                "is_major_port": True
            },
            {
                "name_fa": "شیراز",
                "name_en": "Shiraz",
                "port_type": "air",
                "province_name": "شیراز",
                "description": "فرودگاه بین‌المللی شیراز",
                "is_major_port": True
            },
            {
                "name_fa": "اصفهان",
                "name_en": "Isfahan",
                "port_type": "air",
                "province_name": "اصفهان",
                "description": "فرودگاه بین‌المللی اصفهان",
                "is_major_port": True
            },
            {
                "name_fa": "تبریز",
                "name_en": "Tabriz",
                "port_type": "air",
                "province_name": "تبریز",
                "description": "فرودگاه بین‌المللی تبریز",
                "is_major_port": True
            }
        ]
        
        # Create ports
        for port_data in iran_ports_data:
            province_id = iran_provinces[port_data["province_name"]]["id"]
            port = IranPort(
                name_fa=port_data["name_fa"],
                name_en=port_data["name_en"],
                port_type=port_data["port_type"],
                province_id=province_id,
                description=port_data["description"],
                is_major_port=port_data["is_major_port"],
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(port)
            db.session.flush()
            
            # Create port-province mappings with suitability scores
            port_province_mappings = get_port_province_mappings(port_data["name_fa"], port.id)
            for mapping in port_province_mappings:
                db.session.add(mapping)
        
        try:
            db.session.commit()
            print(f"Successfully seeded {len(iran_ports_data)} Iran ports with province mappings.")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding Iran ports data: {e}")
            raise

def get_port_province_mappings(port_name, port_id):
    """Generate port-province mappings with suitability scores."""
    mappings = []
    
    # Get all provinces
    provinces = Province.query.all()
    
    for province in provinces:
        # Calculate suitability score based on port type and province
        suitability_score = calculate_suitability_score(port_name, province.name_fa)
        
        if suitability_score > 0.3:  # Only include provinces with reasonable suitability
            mapping = PortProvinceMapping(
                port_id=port_id,
                province_id=province.id,
                suitability_score=suitability_score,
                transport_method=get_transport_method(port_name, province.name_fa),
                estimated_days=get_estimated_days(port_name, province.name_fa),
                is_recommended=suitability_score > 0.7,
                created_at=datetime.utcnow()
            )
            mappings.append(mapping)
    
    return mappings

def calculate_suitability_score(port_name, province_name):
    """Calculate suitability score between port and province (0.0 to 1.0)."""
    # Same province = highest score
    if port_name == province_name:
        return 1.0
    
    # Port-specific mappings with high suitability
    high_suitability = {
        "بندرعباس": ["تهران", "اصفهان", "شیراز", "کرمان"],
        "بوشهر": ["تهران", "اصفهان", "شیراز"],
        "امام خمینی": ["تهران", "اصفهان", "تبریز"],
        "خرمشهر": ["تهران", "اصفهان", "تبریز"],
        "ماهشهر": ["تهران", "اصفهان", "تبریز"],
        "چابهار": ["تهران", "اصفهان", "شیراز", "کرمان"],
        "انزلی": ["تهران", "تبریز", "مشهد"],
        "تهران": ["اصفهان", "شیراز", "مشهد", "تبریز"],
        "مشهد": ["تهران", "تبریز", "اصفهان"],
        "شیراز": ["تهران", "اصفهان", "بندرعباس"],
        "اصفهان": ["تهران", "شیراز", "مشهد"],
        "تبریز": ["تهران", "مشهد", "اصفهان"]
    }
    
    # Medium suitability for nearby provinces
    medium_suitability = {
        "بندرعباس": ["مشهد", "تبریز"],
        "بوشهر": ["مشهد", "تبریز"],
        "امام خمینی": ["شیراز", "مشهد"],
        "خرمشهر": ["شیراز", "مشهد"],
        "ماهشهر": ["شیراز", "مشهد"],
        "چابهار": ["مشهد", "تبریز"],
        "انزلی": ["اصفهان", "شیراز"],
        "تهران": ["بندرعباس", "بوشهر", "انزلی"],
        "مشهد": ["شیراز", "بندرعباس"],
        "شیراز": ["مشهد", "تبریز", "بندرعباس"],
        "اصفهان": ["تبریز", "بندرعباس", "بوشهر"],
        "تبریز": ["شیراز", "بندرعباس", "بوشهر"]
    }
    
    if port_name in high_suitability and province_name in high_suitability[port_name]:
        return 0.8
    elif port_name in medium_suitability and province_name in medium_suitability[port_name]:
        return 0.6
    else:
        return 0.4

def get_transport_method(port_name, province_name):
    """Get recommended transport method between port and province."""
    if port_name == province_name:
        return "local"
    
    # Sea ports typically use road transport
    sea_ports = ["بندرعباس", "بوشهر", "امام خمینی", "خرمشهر", "ماهشهر", "چابهار", "انزلی"]
    if port_name in sea_ports:
        return "road"
    
    # Air ports can use both road and air
    air_ports = ["تهران", "مشهد", "شیراز", "اصفهان", "تبریز"]
    if port_name in air_ports:
        return "air"
    
    return "road"

def get_estimated_days(port_name, province_name):
    """Get estimated transport days between port and province."""
    if port_name == province_name:
        return 1
    
    # Base estimates in days
    base_estimates = {
        "بندرعباس": {"تهران": 2, "اصفهان": 1, "شیراز": 1, "کرمان": 1},
        "بوشهر": {"تهران": 2, "اصفهان": 1, "شیراز": 1},
        "امام خمینی": {"تهران": 2, "اصفهان": 1, "تبریز": 2},
        "تهران": {"اصفهان": 1, "شیراز": 2, "مشهد": 2, "تبریز": 2},
        "مشهد": {"تهران": 2, "تبریز": 1, "اصفهان": 2},
        "شیراز": {"تهران": 2, "اصفهان": 1, "بندرعباس": 1},
        "اصفهان": {"تهران": 1, "شیراز": 1, "مشهد": 2},
        "تبریز": {"تهران": 2, "مشهد": 1, "اصفهان": 2}
    }
    
    if port_name in base_estimates and province_name in base_estimates[port_name]:
        return base_estimates[port_name][province_name]
    
    return 2  # Default estimate

if __name__ == "__main__":
    seed_iran_ports()
