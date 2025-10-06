"""Seed script to create international countries and cities data."""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from backend.__init__ import create_app
from backend.models import Country, InternationalCity
from backend.extensions import db

def seed_international_data():
    """Create international countries and cities data."""
    app = create_app()
    
    with app.app_context():
        # Check if countries already exist
        if Country.query.count() > 0:
            print("International data already exists. Skipping seed.")
            return
        
        # Create countries
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
            }
        ]
        
        # Create countries and their cities
        for country_data in countries_data:
            country = Country(
                name_en=country_data["name_en"],
                name_fa=country_data["name_fa"],
                code=country_data["code"],
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(country)
            db.session.flush()  # Get the country ID
            
            # Create cities for this country
            for city_data in country_data["cities"]:
                city = InternationalCity(
                    name_en=city_data["name_en"],
                    name_fa=city_data["name_fa"],
                    country_id=country.id,
                    city_type=city_data["city_type"],
                    is_major_port=city_data["is_major_port"],
                    is_major_airport=city_data["is_major_airport"],
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(city)
        
        try:
            db.session.commit()
            print(f"Successfully seeded {len(countries_data)} countries with their cities.")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding international data: {e}")
            raise

if __name__ == "__main__":
    seed_international_data()
