"""Seed the owned HW_GEO_009 browser proof with the legacy three-row fixture."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import City, Country, InternationalCity
from scripts.uat.seed_phase3_final_candidate_e2e import main as seed_candidate


def main() -> None:
    parsed = make_url(os.environ["DATABASE_URL"])
    if os.environ.get("APP_ENV") != "uat" or parsed.host != "127.0.0.1" or not (parsed.database or "").startswith("forwarder_workspace_phase1_customer_location_browser_"):
        raise RuntimeError("HW_GEO_009 seed requires its owned loopback database")
    seed_candidate()
    app = create_app(skip_startup=True)
    with app.app_context():
        iran = Country.query.filter_by(code="IR", is_active=True).one()
        required = {"Isfahan", "Tehran", "Bandar Abbas", "Beijing"}
        available = {row.name_en for row in City.query.filter(City.name_en.in_(required), City.is_active.is_(True)).all()}
        if available != required:
            raise RuntimeError(f"canonical city fixture incomplete: {sorted(required - available)}")
        InternationalCity.query.update({"is_active": False})
        for name_en, name_fa, code, kind in [
            ("Bandar Abbas", "بندرعباس", "IRBND", "city"),
            ("Tehran", "تهران", "IRTHR", "city"),
            ("Imam Khomeini Airport", "فرودگاه امام خمینی", "IRIKA", "airport"),
        ]:
            row = InternationalCity.query.filter_by(country_id=iran.id, un_locode=code).one_or_none()
            if row is None:
                row = InternationalCity(country_id=iran.id, name_en=name_en, name_fa=name_fa, un_locode=code)
                db.session.add(row)
            row.name_en, row.name_fa, row.city_type = name_en, name_fa, kind
            row.is_major_airport = kind == "airport"
            row.is_major_port = False
            row.is_active = True
            row.dataset_id = "HW_GEO_009_LEGACY"
        db.session.commit()
        print(f"HW_GEO_009_ACTIVE_LEGACY_REFERENCE_COUNT={InternationalCity.query.filter_by(is_active=True).count()}")


if __name__ == "__main__":
    main()
