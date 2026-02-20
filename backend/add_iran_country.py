"""Add Iran to countries and international cities if not already present.
Run this when seed_international_data was already run without Iran (e.g. before Iran was added to the seed).
"""
import sys
import os
# Run from forwarder: python -m backend.add_iran_country  OR  PYTHONPATH=forwarder python forwarder/backend/add_iran_country.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from backend.__init__ import create_app
from backend.models import Country, InternationalCity
from backend.extensions import db

IRAN_COUNTRY = {
    "name_en": "Iran",
    "name_fa": "ایران",
    "code": "IR",
    "cities": [
        {"name_en": "Tehran", "name_fa": "تهران", "city_type": "city", "is_major_port": False, "is_major_airport": True},
        {"name_en": "Bandar Abbas", "name_fa": "بندرعباس", "city_type": "port", "is_major_port": True, "is_major_airport": True},
        {"name_en": "Imam Khomeini Port", "name_fa": "بندر امام خمینی", "city_type": "port", "is_major_port": True, "is_major_airport": False},
        {"name_en": "Mashhad", "name_fa": "مشهد", "city_type": "city", "is_major_port": False, "is_major_airport": True},
        {"name_en": "Shiraz", "name_fa": "شیراز", "city_type": "city", "is_major_port": False, "is_major_airport": True},
        {"name_en": "Tabriz", "name_fa": "تبریز", "city_type": "city", "is_major_port": False, "is_major_airport": True},
        {"name_en": "Isfahan", "name_fa": "اصفهان", "city_type": "city", "is_major_port": False, "is_major_airport": True},
    ],
}


def add_iran_if_missing():
    """Add Iran and its cities if Iran is not already in the database."""
    app = create_app()
    with app.app_context():
        existing = Country.query.filter_by(name_fa="ایران").first()
        if existing:
            print("Iran already exists in countries. Skipping.")
            return
        country = Country(
            name_en=IRAN_COUNTRY["name_en"],
            name_fa=IRAN_COUNTRY["name_fa"],
            code=IRAN_COUNTRY["code"],
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.session.add(country)
        db.session.flush()
        for city_data in IRAN_COUNTRY["cities"]:
            city = InternationalCity(
                name_en=city_data["name_en"],
                name_fa=city_data["name_fa"],
                country_id=country.id,
                city_type=city_data["city_type"],
                is_major_port=city_data["is_major_port"],
                is_major_airport=city_data["is_major_airport"],
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.session.add(city)
        try:
            db.session.commit()
            print(f"Successfully added Iran with {len(IRAN_COUNTRY['cities'])} cities.")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding Iran: {e}")
            raise


if __name__ == "__main__":
    add_iran_if_missing()
