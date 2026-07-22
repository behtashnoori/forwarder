"""Safety tests for the border-customs seed without touching production."""

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import Country, CustomsOffice, Province
from backend.seed_border_customs import (
    BORDER_CUSTOMS,
    BORDER_PROVINCES,
    _ensure_border_provinces,
    _get_or_create_iran,
)


@pytest.fixture()
def app():
    test_app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


def test_border_customs_seed_helpers_are_idempotent(app):
    with app.app_context():
        first_country = _get_or_create_iran()
        first_provinces = _ensure_border_provinces()
        db.session.commit()

        second_country = _get_or_create_iran()
        second_provinces = _ensure_border_provinces()
        db.session.commit()

        assert first_country.id == second_country.id
        assert set(first_provinces) == set(second_provinces)
        assert Country.query.filter_by(code="IR").count() == 1
        assert Province.query.filter(Province.code.in_([row["code"] for row in BORDER_PROVINCES])).count() == len(BORDER_PROVINCES)
        assert CustomsOffice.query.count() == 0
        assert len({row["code"] for row in BORDER_CUSTOMS}) == len(BORDER_CUSTOMS)
