"""Seed the owned HW_GEO_008 browser proof with bounded governed locations."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import Country, InternationalCity
from scripts.uat.seed_phase3_final_candidate_e2e import main as seed_candidate


def _assert_owned_database() -> None:
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("HW_GEO_008 E2E seed requires APP_ENV=uat")
    parsed = make_url(os.environ["DATABASE_URL"])
    if parsed.host != "127.0.0.1" or not (parsed.database or "").startswith(
        "forwarder_workspace_phase1_"
    ):
        raise RuntimeError(
            "HW_GEO_008 E2E seed is restricted to its owned loopback database"
        )


def main() -> None:
    _assert_owned_database()
    seed_candidate()
    app = create_app(skip_startup=True)

    with app.app_context():
        fixtures = (
            ("IR", "HW GEO 008 Tehran", "تهران آزمایشی اچ دبلیو", "IRG08"),
            ("TR", "HW GEO 008 Istanbul", "استانبول آزمایشی اچ دبلیو", "TRG08"),
        )
        for code, name_en, name_fa, un_locode in fixtures:
            country = Country.query.filter_by(code=code, is_active=True).one()
            available = InternationalCity.query.filter_by(
                country_id=country.id, is_active=True
            ).first()
            if available is None:
                db.session.add(
                    InternationalCity(
                        country_id=country.id,
                        name_en=name_en,
                        name_fa=name_fa,
                        un_locode=un_locode,
                        source_organization="FORWARDER HW_GEO_008",
                        source_reference="DISPOSABLE_BROWSER_FIXTURE",
                        source_version="1",
                        dataset_id="HW_GEO_008",
                        is_active=True,
                    )
                )
        db.session.commit()

    print("HW_GEO_008_FIXTURE_SEEDED=YES")


if __name__ == "__main__":
    main()
