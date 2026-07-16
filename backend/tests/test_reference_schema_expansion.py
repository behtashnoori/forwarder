from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.extensions import db
from backend.models import (
    City, Country, County, CustomsOffice, CustomsProvinceMapping, IranPort,
    PortLocation, PortProvinceMapping, Province,
)
from backend.services.reference_schema_service import (
    ReferenceValidationError, build_readiness_report, export_backfill_inventory,
    validate_effective_range, validate_port_location_hierarchy,
)
from backend.services import customs_service


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all(); yield app
        db.session.remove(); db.drop_all()


def _hierarchy():
    country = Country(code="ZZ", name_en="Synthetic", name_fa="آزمایشی")
    db.session.add(country); db.session.flush()
    province = Province(code=None, name_fa="استان آزمایشی", country_id=country.id)
    db.session.add(province); db.session.flush()
    county = County(code=None, name_fa="شهرستان آزمایشی", province_id=province.id)
    db.session.add(county); db.session.flush()
    city = City(code=None, name_fa="شهر آزمایشی", province_id=province.id, county_id=county.id)
    db.session.add(city); db.session.flush()
    return country, province, county, city


def test_nullable_stable_codes_and_country_relationship(app):
    with app.app_context():
        country, province, county, city = _hierarchy(); db.session.commit()
        assert province.country_id == country.id
        assert province.code is county.code is city.code is None
        assert province.is_active and county.is_active and city.is_active


@pytest.mark.parametrize("model,parent_name", [(Province, "country_id"), (County, "province_id"), (City, "county_id")])
def test_parent_scoped_non_null_code_uniqueness(app, model, parent_name):
    with app.app_context():
        country, province, county, _ = _hierarchy(); db.session.commit()
        parent_id = {"country_id": country.id, "province_id": province.id, "county_id": county.id}[parent_name]
        kwargs = {parent_name: parent_id, "code": "TEST-DUP", "name_fa": "یک"}
        if model is City: kwargs["province_id"] = province.id
        db.session.add(model(**kwargs)); db.session.commit()
        kwargs["name_fa"] = "دو"; db.session.add(model(**kwargs))
        with pytest.raises(IntegrityError): db.session.commit()


def test_port_identity_is_nullable_and_scoped(app):
    with app.app_context():
        country, province, _, _ = _hierarchy()
        port = IranPort(code=None, country_id=None, name_fa="بندر آزمایشی", name_en="Synthetic", province_id=province.id)
        db.session.add(port); db.session.commit()
        assert port.code is None and port.country_id is None and port.province_id == province.id


def test_effective_range_validation_and_constraint(app):
    validate_effective_range(date(2026, 1, 1), date(2026, 1, 1))
    with pytest.raises(ReferenceValidationError): validate_effective_range(date(2026, 2, 1), date(2026, 1, 1))
    with app.app_context():
        db.session.add(Province(name_fa="bad", effective_from=date(2026, 2, 1), effective_to=date(2026, 1, 1)))
        with pytest.raises(IntegrityError): db.session.commit()


def test_country_effective_range_constraint(app):
    with app.app_context():
        db.session.add(Country(code="ZZ", name_en="Synthetic", name_fa="آزمایشی", effective_from=date(2026, 2, 1), effective_to=date(2026, 1, 1)))
        with pytest.raises(IntegrityError): db.session.commit()


def test_port_location_hierarchy_and_one_active_location(app):
    with app.app_context():
        country, province, county, city = _hierarchy()
        port = IranPort(name_fa="بندر آزمایشی", name_en="Synthetic", province_id=province.id)
        db.session.add(port); db.session.flush()
        validate_port_location_hierarchy(country=country, province=province, county=county, city=city)
        db.session.add(PortLocation(port_id=port.id, country_id=country.id, province_id=province.id, location_status="provisional")); db.session.commit()
        db.session.add(PortLocation(port_id=port.id, country_id=country.id, province_id=province.id, location_status="confirmed"))
        with pytest.raises(IntegrityError): db.session.commit()


def test_port_location_direct_write_rejects_inconsistent_hierarchy(app):
    with app.app_context():
        country, province, county, city = _hierarchy()
        other = Country(code="ZX", name_en="Other", name_fa="دیگر")
        port = IranPort(name_fa="بندر", name_en="Port", province_id=province.id)
        db.session.add_all([other, port]); db.session.flush()
        db.session.add(PortLocation(port_id=port.id, country_id=other.id, province_id=province.id, county_id=county.id, city_id=city.id))
        with pytest.raises(ValueError): db.session.commit()


def test_no_geography_or_customs_is_created_implicitly(app):
    with app.app_context():
        assert all(model.query.count() == 0 for model in (Country, Province, County, City, IranPort, PortLocation, CustomsOffice, CustomsProvinceMapping))


def test_coverage_uniqueness_and_lifecycle(app):
    with app.app_context():
        _, province, _, _ = _hierarchy(); port = IranPort(name_fa="بندر", name_en="Port", province_id=province.id)
        db.session.add(port); db.session.flush()
        db.session.add(PortProvinceMapping(port_id=port.id, province_id=province.id)); db.session.commit()
        assert PortProvinceMapping.query.one().is_active
        db.session.add(PortProvinceMapping(port_id=port.id, province_id=province.id))
        with pytest.raises(IntegrityError): db.session.commit()


def test_customs_coverage_uniqueness_without_implicit_creation(app):
    with app.app_context():
        country, province, _, _ = _hierarchy()
        office = CustomsOffice(code="TEST-CUSTOMS", name_fa="گمرک آزمایشی", customs_type="other", country_id=country.id)
        db.session.add(office); db.session.flush()
        db.session.add(CustomsProvinceMapping(customs_office_id=office.id, province_id=province.id)); db.session.commit()
        db.session.add(CustomsProvinceMapping(customs_office_id=office.id, province_id=province.id))
        with pytest.raises(IntegrityError): db.session.commit()


def test_readiness_and_inventory_are_read_only_and_generate_no_code(app, tmp_path):
    with app.app_context():
        _hierarchy(); db.session.commit()
        before = tuple(model.query.count() for model in (Country, Province, County, City))
        report = build_readiness_report()
        output = tmp_path / "inventory.csv"; count = export_backfill_inventory(output)
        after = tuple(model.query.count() for model in (Country, Province, County, City))
        assert report["status"] == "BACKFILL_REQUIRED" and report["production_readiness"] == "NO-GO"
        assert before == after and count == 3
        text = output.read_text(encoding="utf-8")
        assert "proposed_code_owner_must_supply" in text and "TEST-" not in text


def test_inventory_neutralizes_spreadsheet_formula(app, tmp_path):
    with app.app_context():
        country = Country(code="ZZ", name_en="Synthetic", name_fa="Synthetic")
        db.session.add(country); db.session.flush()
        db.session.add(Province(name_fa="=1+1", country_id=country.id)); db.session.commit()
        output = tmp_path / "inventory.csv"; export_backfill_inventory(output)
        assert "'=1+1" in output.read_text(encoding="utf-8")


def test_existing_location_api_shape_is_unchanged(app):
    with app.app_context():
        _hierarchy(); db.session.commit()
    response = app.test_client().get("/api/provinces")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload[0].keys() == {"id", "name", "code"}


def test_inactive_geography_is_hidden_without_shape_change(app):
    with app.app_context():
        _, province, county, city = _hierarchy()
        province.is_active = county.is_active = city.is_active = False; db.session.commit()
    assert app.test_client().get("/api/provinces").get_json() == []


def test_customs_rejects_country_province_mismatch(app):
    with app.app_context():
        first = Country(code="ZZ", name_en="Synthetic", name_fa="آزمایشی")
        second = Country(code="ZX", name_en="Other", name_fa="دیگر")
        db.session.add_all([first, second]); db.session.flush()
        province = Province(name_fa="استان", country_id=first.id); db.session.add(province); db.session.commit()
        with pytest.raises(customs_service.CustomsValidationError):
            customs_service.create_office({"code": "TEST-CUSTOMS", "name_fa": "گمرک", "customs_type": "other", "country_id": second.id, "province_id": province.id})
