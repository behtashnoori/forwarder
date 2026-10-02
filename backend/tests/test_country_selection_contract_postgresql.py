"""Owned PostgreSQL 18 proof for the complete active country read contract."""

import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import Country, ExpertUser, InternationalCity
from scripts.uat.canonical_geography_fixture import ensure_canonical_geography


URL = os.environ.get("COUNTRY_SELECTION_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(
    not URL, reason="requires owned COUNTRY_SELECTION_POSTGRES_URL"
)


def _identities(rows):
    return [(row["id"], row["code"]) for row in rows]


def test_public_customer_and_authenticated_country_projections_match_active_sor():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql" and parsed.host == "127.0.0.1"
    assert (parsed.database or "").startswith("forwarder_country_selection_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(
            connection.execute(sa.text("SHOW server_version_num")).scalar_one()
        ) < 190000

    command.upgrade(alembic_config(URL), "head")
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": URL,
            "SECRET_KEY": "owned-country-contract-secret-key-32",
            "JWT_SECRET_KEY": "owned-country-contract-jwt-key-32",
        },
        skip_startup=True,
    )
    with app.app_context():
        ensure_canonical_geography()
        inactive = Country(
            code="ZZZ", name_fa="غیرفعال آزمون", name_en="Inactive Test", is_active=False
        )
        expert = ExpertUser(
            username="country-contract-expert",
            full_name="Country Contract Expert",
            password_hash="unused",
            role="expert",
            is_active=True,
        )
        db.session.add_all([inactive, expert])
        db.session.flush()
        iran = db.session.scalar(sa.select(Country).where(Country.code == "IR"))
        db.session.add(
            InternationalCity(
                country_id=iran.id,
                name_fa="مکان آزمون قرارداد",
                name_en="Contract Test Place",
                is_active=True,
            )
        )
        db.session.commit()

        expected = db.session.execute(
            sa.select(Country.id, Country.code)
            .where(Country.is_active.is_(True))
            .order_by(Country.id)
        ).all()
        expected_identities = [(row.id, row.code) for row in expected]
        token = auth_manager.generate_tokens(expert.id)["access_token"]

    with app.test_client() as client:
        legacy = client.get("/api/countries")
        public = client.get("/api/geography/countries")
        internal = client.get(
            "/api/internal/geography/countries",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert legacy.status_code == public.status_code == internal.status_code == 200
        legacy_rows = legacy.get_json()
        public_rows = public.get_json()["items"]
        internal_rows = internal.get_json()["items"]
        assert sorted(_identities(legacy_rows)) == expected_identities
        assert sorted(_identities(public_rows)) == expected_identities
        assert sorted(_identities(internal_rows)) == expected_identities
        assert len(_identities(legacy_rows)) == len(set(_identities(legacy_rows)))
        assert len(_identities(public_rows)) == len(set(_identities(public_rows)))
        assert len(_identities(internal_rows)) == len(set(_identities(internal_rows)))
        assert "ZZZ" not in {row["code"] for row in legacy_rows}
        assert next(row for row in legacy_rows if row["code"] == "IR")[
            "international_locations_available"
        ] is True
        assert next(row for row in legacy_rows if row["code"] == "FR")[
            "international_locations_available"
        ] is False
        assert set(legacy_rows[0]) <= {
            "id",
            "name",
            "name_en",
            "code",
            "name_fa_is_fallback",
            "international_locations_available",
        }
        assert "FR" in {
            row["code"]
            for row in client.get("/api/geography/countries?q=FR").get_json()["items"]
        }
