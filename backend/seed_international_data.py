"""Seed script to create international countries and cities data."""
import sys
import os
from contextlib import nullcontext
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from backend.__init__ import create_app
from backend.models import Country, InternationalCity
from backend.extensions import db
from backend.services.international_geography_readiness import approved_snapshot, validate_snapshot


def _governed_records():
    """Return S1 additions from a checked-in, versioned snapshot only."""
    snapshot = approved_snapshot()
    errors = validate_snapshot(snapshot)
    if errors:
        raise ValueError("Invalid international geography snapshot: " + "; ".join(errors))
    return snapshot["records"], snapshot

def seed_international_data(app=None):
    """Reconcile the checked-in international reference input, idempotently.

    Passing an application is intended for controlled maintenance and tests;
    it never contacts another environment.
    """
    app = app or create_app()
    
    context = nullcontext() if app is not None and app.config.get("TESTING") else app.app_context()
    with context:
        # Checked-in, governed historical reference input.  Reconcile each
        # entry independently: an earlier Iran-only seed must not suppress
        # the rest of the catalog or Iran's InternationalCity continuation.
        countries_data = [
            {
                "name_en": "China",
                "name_fa": "چین",
                "code": "CN",
                "cities": [
                    {"name_en": "Shanghai", "name_fa": "شانگهای", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Beijing", "name_fa": "پکن", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Guangzhou", "name_fa": "گوانگژو", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Shenzhen", "name_fa": "شنژن", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Ningbo", "name_fa": "نینگبو", "city_type": "port", "is_major_port": True, "is_major_airport": False},
                    {"name_en": "Qingdao", "name_fa": "چینگدائو", "city_type": "port", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Tianjin", "name_fa": "تیانجین", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Dalian", "name_fa": "دالیان", "city_type": "port", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Xiamen", "name_fa": "شیامن", "city_type": "port", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Hangzhou", "name_fa": "هانگژو", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Chengdu", "name_fa": "چنگدو", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Wuhan", "name_fa": "ووهان", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Xi'an", "name_fa": "شیان", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Nanjing", "name_fa": "نانجینگ", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Chongqing", "name_fa": "چونگ کینگ", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                ]
            },
            {
                "name_en": "Turkey",
                "name_fa": "ترکیه",
                "code": "TR",
                "cities": [
                    {"name_en": "Istanbul", "name_fa": "استانبول", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Ankara", "name_fa": "آنکارا", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Izmir", "name_fa": "ازمیر", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Bursa", "name_fa": "بورسا", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Antalya", "name_fa": "آنتالیا", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                ]
            },
            {
                "name_en": "United Arab Emirates",
                "name_fa": "امارات متحده عربی",
                "code": "AE",
                "cities": [
                    {"name_en": "Dubai", "name_fa": "دبی", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Abu Dhabi", "name_fa": "ابوظبی", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Sharjah", "name_fa": "شارجه", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Ajman", "name_fa": "عجمان", "city_type": "city", "is_major_port": True, "is_major_airport": False},
                ]
            },
            {
                "name_en": "Germany",
                "name_fa": "آلمان",
                "code": "DE",
                "cities": [
                    {"name_en": "Berlin", "name_fa": "برلین", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Hamburg", "name_fa": "هامبورگ", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Munich", "name_fa": "مونیخ", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Frankfurt", "name_fa": "فرانکفورت", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Cologne", "name_fa": "کلن", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                ]
            },
            {
                "name_en": "United States",
                "name_fa": "ایالات متحده آمریکا",
                "code": "US",
                "cities": [
                    {"name_en": "New York", "name_fa": "نیویورک", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Los Angeles", "name_fa": "لس آنجلس", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Chicago", "name_fa": "شیکاگو", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Miami", "name_fa": "میامی", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "San Francisco", "name_fa": "سان فرانسیسکو", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                ]
            },
            {
                "name_en": "United Kingdom",
                "name_fa": "انگلستان",
                "code": "GB",
                "cities": [
                    {"name_en": "London", "name_fa": "لندن", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Manchester", "name_fa": "منچستر", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Birmingham", "name_fa": "بیرمنگام", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Liverpool", "name_fa": "لیورپول", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                ]
            },
            {
                "name_en": "Japan",
                "name_fa": "ژاپن",
                "code": "JP",
                "cities": [
                    {"name_en": "Tokyo", "name_fa": "توکیو", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Osaka", "name_fa": "اوساکا", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Yokohama", "name_fa": "یوکوهاما", "city_type": "port", "is_major_port": True, "is_major_airport": False},
                    {"name_en": "Kobe", "name_fa": "کوبه", "city_type": "port", "is_major_port": True, "is_major_airport": False},
                    {"name_en": "Nagoya", "name_fa": "ناگویا", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                ]
            },
            {
                "name_en": "South Korea",
                "name_fa": "کره جنوبی",
                "code": "KR",
                "cities": [
                    {"name_en": "Seoul", "name_fa": "سئول", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Busan", "name_fa": "بوسان", "city_type": "port", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Incheon", "name_fa": "اینچئون", "city_type": "port", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Daegu", "name_fa": "دگو", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                ]
            },
            {
                "name_en": "India",
                "name_fa": "هند",
                "code": "IN",
                "cities": [
                    {"name_en": "Mumbai", "name_fa": "بمبئی", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Delhi", "name_fa": "دهلی", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Chennai", "name_fa": "چنای", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Kolkata", "name_fa": "کلکته", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Bangalore", "name_fa": "بنگلور", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                ]
            },
            {
                "name_en": "Russia",
                "name_fa": "روسیه",
                "code": "RU",
                "cities": [
                    {"name_en": "Moscow", "name_fa": "مسکو", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                    {"name_en": "Saint Petersburg", "name_fa": "سن پترزبورگ", "city_type": "city", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Vladivostok", "name_fa": "ولادیوستوک", "city_type": "port", "is_major_port": True, "is_major_airport": True},
                    {"name_en": "Novosibirsk", "name_fa": "نووسیبیرسک", "city_type": "city", "is_major_port": False, "is_major_airport": True},
                ]
            },
            {
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
                ]
            }
        ]
        governed_records, snapshot = _governed_records()
        # Keep the established legacy catalog compatible while adding new
        # approved records exclusively through the governed snapshot.
        for record in governed_records:
            country = dict(record["country"])
            country["cities"] = [dict(location) for location in record["locations"]]
            countries_data.append(country)
        
        countries_created = cities_created = 0
        # Create only missing countries and cities.  Existing lifecycle state
        # is managed by admin CRUD and must not be silently reactivated here.
        for country_data in countries_data:
            code = str(country_data["code"]).upper()
            if len(code) != 2 or not code.isalpha():
                raise ValueError(f"Country code must be ISO alpha-2: {code!r}")
            country = Country.query.filter_by(code=code).one_or_none()
            if country is None:
                country = Country(
                    name_en=country_data["name_en"],
                    name_fa=country_data["name_fa"],
                    code=code,
                    is_active=True,
                    source_organization=country_data.get("source_organization"),
                    source_reference=country_data.get("source_reference"),
                    source_version=country_data.get("source_version"),
                    dataset_id=snapshot["dataset_id"] if country_data.get("source_organization") else None,
                    created_at=datetime.utcnow()
                )
                db.session.add(country)
                db.session.flush()
                countries_created += 1

            # Create cities for this country
            for city_data in country_data["cities"]:
                un_locode = city_data.get("un_locode")
                city = (InternationalCity.query.filter_by(country_id=country.id, un_locode=un_locode).one_or_none()
                        if un_locode else InternationalCity.query.filter_by(country_id=country.id, name_en=city_data["name_en"]).one_or_none())
                if city is None:
                    db.session.add(InternationalCity(
                        name_en=city_data["name_en"],
                        name_fa=city_data["name_fa"],
                        country_id=country.id,
                        city_type=city_data["city_type"],
                        is_major_port=city_data["is_major_port"],
                        is_major_airport=city_data["is_major_airport"],
                        is_active=True,
                        un_locode=un_locode,
                        source_organization=city_data.get("source_organization"),
                        source_reference=city_data.get("source_reference"),
                        source_version=city_data.get("source_version"),
                        dataset_id=snapshot["dataset_id"] if un_locode else None,
                        created_at=datetime.utcnow()
                    ))
                    cities_created += 1
        
        try:
            db.session.commit()
            print(f"International reference reconciliation complete: {countries_created} countries and {cities_created} cities created.")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding international data: {e}")
            raise

if __name__ == "__main__":
    seed_international_data()
