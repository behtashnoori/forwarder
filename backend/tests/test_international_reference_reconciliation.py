"""Regression coverage for partial international reference-data seeding."""
from backend import create_app
from backend.extensions import db
from backend.models import Country, InternationalCity
from backend.seed_international_data import seed_international_data


def test_reconciliation_repairs_partial_iran_seed_without_reactivating_existing_records():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        iran = Country(code="IR", name_en="Iran", name_fa="ایران", is_active=True)
        inactive = Country(code="CN", name_en="China", name_fa="چین", is_active=False)
        db.session.add_all([iran, inactive]); db.session.commit()

        seed_international_data(app)

        assert Country.query.filter_by(code="IR").one().is_active is True
        assert InternationalCity.query.join(Country).filter(Country.code == "IR").count() > 0
        assert Country.query.filter_by(code="CN").one().is_active is False
        assert InternationalCity.query.join(Country).filter(Country.code == "CN").count() > 0
        assert Country.query.filter_by(code="TR").one() is not None

        first_counts = (Country.query.count(), InternationalCity.query.count())
        seed_international_data(app)
        assert (Country.query.count(), InternationalCity.query.count()) == first_counts
