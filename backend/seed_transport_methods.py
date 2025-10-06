#!/usr/bin/env python3
"""Seed transport methods for international and domestic shipping."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.extensions import db
from backend.models import TransportMethod
from backend import create_app


def seed_transport_methods():
    """Seed transport methods for both international and domestic shipping."""
    
    # International transport methods
    international_methods = [
        {
            "name": "Sea Freight",
            "name_fa": "حمل دریایی",
            "description": "حمل کالا از طریق دریا - مناسب برای بارهای حجیم و سنگین"
        },
        {
            "name": "Air Freight", 
            "name_fa": "حمل هوایی",
            "description": "حمل کالا از طریق هوا - سریع و مناسب برای بارهای فوری"
        },
        {
            "name": "Land Transport",
            "name_fa": "حمل زمینی",
            "description": "حمل کالا از طریق جاده - مناسب برای مسیرهای کوتاه و متوسط"
        },
        {
            "name": "Rail Transport",
            "name_fa": "حمل ریلی",
            "description": "حمل کالا از طریق راه‌آهن - مناسب برای بارهای حجیم و مسیرهای طولانی"
        }
    ]
    
    # Domestic transport methods
    domestic_methods = [
        {
            "name": "Road Transport",
            "name_fa": "حمل جاده‌ای",
            "description": "حمل کالا از طریق جاده - سریع و قابل اعتماد برای حمل داخلی"
        },
        {
            "name": "Rail Transport",
            "name_fa": "حمل ریلی", 
            "description": "حمل کالا از طریق راه‌آهن - مناسب برای بارهای حجیم و مسیرهای طولانی"
        },
        {
            "name": "Air Transport",
            "name_fa": "حمل هوایی",
            "description": "حمل کالا از طریق هوا - سریع‌ترین روش برای حمل داخلی"
        }
    ]
    
    app = create_app()
    
    with app.app_context():
        # Clear existing transport methods
        db.session.query(TransportMethod).delete()
        db.session.commit()
        
        # Add international transport methods
        for method_data in international_methods:
            method = TransportMethod(
                name=method_data["name"],
                name_fa=method_data["name_fa"],
                description=method_data["description"],
                is_active=True
            )
            db.session.add(method)
        
        # Add domestic transport methods
        for method_data in domestic_methods:
            method = TransportMethod(
                name=method_data["name"],
                name_fa=method_data["name_fa"],
                description=method_data["description"],
                is_active=True
            )
            db.session.add(method)
        
        db.session.commit()
        print("✅ Transport methods seeded successfully!")
        print(f"   - {len(international_methods)} international methods added")
        print(f"   - {len(domestic_methods)} domestic methods added")


if __name__ == "__main__":
    seed_transport_methods()
