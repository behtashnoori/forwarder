import pytest

from backend import create_app
from backend.extensions import db
from backend.models import Country, County, CustomsOffice, IranPort, PortCustomsOffice, Province, City
from backend.seed_country import CountrySeedConflict, seed_canonical_iran
from backend.services import customs_service


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove(); db.drop_all()


def test_country_seed_is_idempotent_and_does_not_create_geography(app):
    with app.app_context():
        seed_canonical_iran(); seed_canonical_iran()
        assert Country.query.filter_by(code="IR").count() == 1
        assert Province.query.count() == County.query.count() == City.query.count() == 0


def test_country_seed_fails_closed_on_alias_without_code(app):
    with app.app_context():
        db.session.add(Country(code="XX", name_en="Iran", name_fa="ایران")); db.session.commit()
        with pytest.raises(CountrySeedConflict): seed_canonical_iran()


def _geography():
    country = Country(code="IR", name_en="Iran", name_fa="ایران")
    province = Province(code="TEH", name_fa="تهران")
    db.session.add_all([country, province]); db.session.flush()
    county = County(name_fa="تهران", province_id=province.id); db.session.add(county); db.session.flush()
    city = City(name_fa="تهران", province_id=province.id, county_id=county.id); db.session.add(city); db.session.commit()
    return country, province, county, city


def test_customs_validation_and_explicit_relationship(app):
    with app.app_context():
        country, province, county, city = _geography()
        office = customs_service.create_office({"code": "SYN-1", "name_fa": "آزمایشی", "customs_type": "inland",
            "country_id": country.id, "province_id": province.id, "county_id": county.id, "city_id": city.id})
        port = IranPort(name_fa="آزمایشی", name_en="Synthetic", port_type="land", province_id=province.id)
        db.session.add(port); db.session.commit()
        relation = customs_service.create_relationship({"port_id": port.id, "customs_office_id": office.id, "relationship_type": "associated"})
        assert relation.id and CustomsOffice.query.count() == PortCustomsOffice.query.count() == 1
        with pytest.raises(customs_service.CustomsValidationError):
            customs_service.create_office({"code": "BAD", "name_fa": "بد", "customs_type": "invented", "country_id": country.id})
        with pytest.raises(customs_service.CustomsValidationError):
            customs_service.create_office({"code": "BAD-BOOL", "name_fa": "بد", "customs_type": "inland", "country_id": country.id, "is_active": "false"})


def test_zero_customs_is_valid_empty_state(app):
    with app.app_context():
        assert CustomsOffice.query.count() == 0


def test_customs_update_rejects_blank_name_and_non_boolean_active(app):
    with app.app_context():
        country, _, _, _ = _geography()
        office = customs_service.create_office({"code": "SYN-UPDATE", "name_fa": "آزمایشی", "customs_type": "other", "country_id": country.id})
        with pytest.raises(customs_service.CustomsValidationError):
            customs_service.update_office(office, {"name_fa": "   "})
        with pytest.raises(customs_service.CustomsValidationError):
            customs_service.update_office(office, {"is_active": "false"})
