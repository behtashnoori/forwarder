"""Seed major Iran land/rail border customs offices.

Idempotent. Ensures the Iran country row and the border provinces referenced by
these offices exist, then creates the customs offices themselves. Safe to run
repeatedly; existing rows are matched by their stable ``code``.

Run:  python -m backend.seed_border_customs
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from backend.__init__ import create_app
from backend.extensions import db
from backend.models import Country, CustomsOffice, Province

# Border provinces referenced below. Existing rows are reused by code; missing
# ones are created so the customs offices always resolve to a real province.
BORDER_PROVINCES = [
    {"code": "WAZ", "name_fa": "آذربایجان غربی"},
    {"code": "EAZ", "name_fa": "آذربایجان شرقی"},
    {"code": "KRM", "name_fa": "کرمانشاه"},
    {"code": "ILM", "name_fa": "ایلام"},
    {"code": "ARL", "name_fa": "اردبیل"},
    {"code": "GIL", "name_fa": "گیلان"},
    {"code": "KHO", "name_fa": "خراسان رضوی"},
    {"code": "SIS", "name_fa": "سیستان و بلوچستان"},
    {"code": "KHU", "name_fa": "خوزستان"},
]

# Major road/rail border customs offices with the neighbouring country they face.
BORDER_CUSTOMS = [
    {"code": "IRBZG", "name_fa": "گمرک بازرگان", "name_en": "Bazargan", "province": "WAZ", "customs_type": "road_border", "neighbor": "ترکیه"},
    {"code": "IRSRO", "name_fa": "گمرک سرو", "name_en": "Sero", "province": "WAZ", "customs_type": "road_border", "neighbor": "ترکیه"},
    {"code": "IRTMR", "name_fa": "گمرک تمرچین (پیرانشهر)", "name_en": "Tamarchin", "province": "WAZ", "customs_type": "road_border", "neighbor": "عراق"},
    {"code": "IRJLF", "name_fa": "گمرک جلفا", "name_en": "Jolfa", "province": "EAZ", "customs_type": "road_border", "neighbor": "جمهوری آذربایجان"},
    {"code": "IRRAZ", "name_fa": "گمرک رازی", "name_en": "Razi", "province": "WAZ", "customs_type": "rail", "neighbor": "ترکیه"},
    {"code": "IRPVK", "name_fa": "گمرک پرویزخان", "name_en": "Parvizkhan", "province": "KRM", "customs_type": "road_border", "neighbor": "عراق"},
    {"code": "IRKSR", "name_fa": "گمرک خسروی", "name_en": "Khosravi", "province": "KRM", "customs_type": "road_border", "neighbor": "عراق"},
    {"code": "IRMHR", "name_fa": "گمرک مهران", "name_en": "Mehran", "province": "ILM", "customs_type": "road_border", "neighbor": "عراق"},
    {"code": "IRCZB", "name_fa": "گمرک چذابه", "name_en": "Chazabeh", "province": "KHU", "customs_type": "road_border", "neighbor": "عراق"},
    {"code": "IRSHL", "name_fa": "گمرک شلمچه", "name_en": "Shalamcheh", "province": "KHU", "customs_type": "road_border", "neighbor": "عراق"},
    {"code": "IRAST", "name_fa": "گمرک آستارا", "name_en": "Astara", "province": "GIL", "customs_type": "road_border", "neighbor": "جمهوری آذربایجان"},
    {"code": "IRBLS", "name_fa": "گمرک بیله‌سوار", "name_en": "Bilesavar", "province": "ARL", "customs_type": "road_border", "neighbor": "جمهوری آذربایجان"},
    {"code": "IRDGN", "name_fa": "گمرک دوغارون", "name_en": "Dogharoun", "province": "KHO", "customs_type": "road_border", "neighbor": "افغانستان"},
    {"code": "IRMJV", "name_fa": "گمرک میرجاوه", "name_en": "Mirjaveh", "province": "SIS", "customs_type": "road_border", "neighbor": "پاکستان"},
    {"code": "IRMLK", "name_fa": "گمرک ملک‌تیمور (سرخس)", "name_en": "Sarakhs", "province": "KHO", "customs_type": "rail", "neighbor": "ترکمنستان"},
]


def _get_or_create_iran() -> Country:
    country = Country.query.filter_by(code="IR").first()
    if country is None:
        country = Country(name_en="Iran", name_fa="ایران", code="IR", is_active=True, created_at=datetime.utcnow())
        db.session.add(country)
        db.session.flush()
    return country


def _ensure_border_provinces() -> dict[str, Province]:
    by_code: dict[str, Province] = {}
    for data in BORDER_PROVINCES:
        province = Province.query.filter_by(code=data["code"]).first()
        if province is None:
            province = Province(name_fa=data["name_fa"], code=data["code"])
            db.session.add(province)
            db.session.flush()
        by_code[data["code"]] = province
    return by_code


def seed_border_customs() -> None:
    """Create border customs offices, ensuring their geography exists first."""
    app = create_app()
    with app.app_context():
        iran = _get_or_create_iran()
        provinces = _ensure_border_provinces()

        created = 0
        for data in BORDER_CUSTOMS:
            province = provinces[data["province"]]
            office = CustomsOffice.query.filter_by(code=data["code"]).first()
            description_note = f"گمرک مرزی هم‌مرز با {data['neighbor']}"
            if office is None:
                office = CustomsOffice(
                    code=data["code"],
                    name_fa=data["name_fa"],
                    name_en=data["name_en"],
                    customs_type=data["customs_type"],
                    country_id=iran.id,
                    province_id=province.id,
                    is_active=True,
                    source_organization="IRICA",
                    source_reference=description_note,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.session.add(office)
                created += 1
            else:
                # Keep geography aligned without clobbering manual edits to names.
                office.country_id = iran.id
                if office.province_id is None:
                    office.province_id = province.id

        try:
            db.session.commit()
            print(f"Border customs seed complete. Created {created} new offices ({len(BORDER_CUSTOMS)} total).")
        except Exception as exc:  # pragma: no cover - defensive
            db.session.rollback()
            print(f"Error seeding border customs: {exc}")
            raise


if __name__ == "__main__":
    seed_border_customs()
