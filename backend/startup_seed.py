"""Minimal seed at startup when critical tables are empty. Ensures /api/transport-methods and /api/provinces can serve after fresh DB or restart."""
from __future__ import annotations

import sys
import traceback

from backend.extensions import db
from backend.models import Province, TransportMethod


# Minimal transport methods (same as seed_transport_methods, insert only when empty)
TRANSPORT_METHODS = [
    {"name": "Sea Freight", "name_fa": "حمل دریایی", "description": "حمل کالا از طریق دریا - مناسب برای بارهای حجیم و سنگین"},
    {"name": "Air Freight", "name_fa": "حمل هوایی", "description": "حمل کالا از طریق هوا - سریع و مناسب برای بارهای فوری"},
    {"name": "Land Transport", "name_fa": "حمل زمینی", "description": "حمل کالا از طریق جاده - مناسب برای مسیرهای کوتاه و متوسط"},
    {"name": "Rail Transport", "name_fa": "حمل ریلی", "description": "حمل کالا از طریق راه‌آهن - مناسب برای بارهای حجیم و مسیرهای طولانی"},
    {"name": "Road Transport", "name_fa": "حمل جاده‌ای", "description": "حمل کالا از طریق جاده - سریع و قابل اعتماد برای حمل داخلی"},
    {"name": "Air Transport", "name_fa": "حمل هوایی", "description": "حمل کالا از طریق هوا - سریع‌ترین روش برای حمل داخلی"},
]

# Minimal provinces (Iran) so frontend and routes never depend on manual seed
PROVINCES = [
    {"name_fa": "تهران", "code": "TEH"},
    {"name_fa": "اصفهان", "code": "ISF"},
    {"name_fa": "فارس", "code": "FAR"},
    {"name_fa": "خراسان رضوی", "code": "KHO"},
    {"name_fa": "آذربایجان شرقی", "code": "EAZ"},
    {"name_fa": "خوزستان", "code": "KHU"},
    {"name_fa": "کرمان", "code": "KER"},
    {"name_fa": "گیلان", "code": "GIL"},
    {"name_fa": "هرمزگان", "code": "HOR"},
    {"name_fa": "بوشهر", "code": "BUS"},
    {"name_fa": "سیستان و بلوچستان", "code": "SIS"},
]


def run_startup_seed(app) -> None:
    """Seed transport_method and province when empty. On failure: log and exit(1)."""
    with app.app_context():
        try:
            if db.session.query(TransportMethod).count() == 0:
                for data in TRANSPORT_METHODS:
                    db.session.add(
                        TransportMethod(
                            name=data["name"],
                            name_fa=data["name_fa"],
                            description=data["description"],
                            is_active=True,
                        )
                    )
                db.session.commit()
                print("[startup] Transport methods seeded (table was empty).")

            if db.session.query(Province).count() == 0:
                for data in PROVINCES:
                    db.session.add(
                        Province(name_fa=data["name_fa"], code=data["code"])
                    )
                db.session.commit()
                print("[startup] Provinces seeded (table was empty).")
        except Exception as e:
            print("[startup] Startup seed failed:", e)
            traceback.print_exc()
            sys.exit(1)
