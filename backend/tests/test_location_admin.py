"""Tests for admin CRUD over origin/destination reference geography."""
import bcrypt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import City, Country, County, ExpertUser, InternationalCity, IranPort, Province
from backend.services import location_admin_service as svc
from backend.services.auth_session_service import create_session_tokens


@pytest.fixture()
def app():
    app = create_app(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"},
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


# ---------------------------------------------------------------------------
# service layer
# ---------------------------------------------------------------------------
def test_domestic_hierarchy_create_and_validation(app):
    with app.app_context():
        province = svc.create_province({"name_fa": "تهران", "code": "TEH"})
        county = svc.create_county({"name_fa": "تهران", "province_id": province.id})
        city = svc.create_city({"name_fa": "تهران", "county_id": county.id})
        # province is always derived from the county so the hierarchy stays consistent
        assert city.province_id == province.id
        assert County.query.count() == City.query.count() == 1

        with pytest.raises(svc.LocationValidationError):
            svc.create_county({"name_fa": "خطا", "province_id": 9999})
        with pytest.raises(svc.LocationValidationError):
            svc.create_city({"name_fa": "خطا", "county_id": 9999})
        with pytest.raises(svc.LocationValidationError):
            svc.create_province({"name_fa": "   "})


def test_international_create_and_unique_country_code(app):
    with app.app_context():
        country = svc.create_country({"name_fa": "چین", "name_en": "China", "code": "cn"})
        assert country.code == "CN"  # normalised to upper-case
        city = svc.create_international_city(
            {"name_fa": "شانگهای", "name_en": "Shanghai", "country_id": country.id,
             "city_type": "port", "is_major_port": True}
        )
        assert city.is_major_port is True
        with pytest.raises(svc.LocationValidationError):
            svc.create_country({"name_fa": "دیگر", "name_en": "Other", "code": "CN"})
        with pytest.raises(svc.LocationValidationError):
            svc.create_international_city({"name_fa": "x", "name_en": "x", "country_id": country.id, "city_type": "bogus"})


def test_iran_port_requires_valid_province(app):
    with app.app_context():
        province = svc.create_province({"name_fa": "هرمزگان"})
        port = svc.create_iran_port(
            {"name_fa": "بندرعباس", "name_en": "Bandar Abbas", "port_type": "sea", "province_id": province.id}
        )
        assert port.province_id == province.id
        with pytest.raises(svc.LocationValidationError):
            svc.create_iran_port({"name_fa": "x", "name_en": "x", "port_type": "sea", "province_id": 9999})
        with pytest.raises(svc.LocationValidationError):
            svc.create_iran_port({"name_fa": "x", "name_en": "x", "port_type": "orbit", "province_id": province.id})


def test_deactivate_is_soft_and_hidden_from_active_lists(app):
    with app.app_context():
        province = svc.create_province({"name_fa": "اصفهان"})
        svc.deactivate(province)
        assert province.is_active is False
        assert svc.list_provinces() == []
        assert province in svc.list_provinces(include_inactive=True)
        assert Province.query.count() == 1  # row physically retained


# ---------------------------------------------------------------------------
# HTTP layer (auth + routing)
# ---------------------------------------------------------------------------
def _admin_headers(app):
    with app.app_context():
        password_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8")
        admin = ExpertUser(
            username="loc_admin",
            password_hash=password_hash,
            full_name="Location Admin",
            email="loc-admin@example.test",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()
        token = create_session_tokens(admin.id)["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_routes_require_admin(app):
    client = app.test_client()
    resp = client.get("/api/admin/locations/provinces")
    assert resp.status_code in (401, 403)


def test_route_create_list_update_deactivate_roundtrip(app):
    client = app.test_client()
    headers = _admin_headers(app)

    created = client.post("/api/admin/locations/provinces", json={"name_fa": "قم"}, headers=headers)
    assert created.status_code == 201
    province_id = created.get_json()["item"]["id"]

    listed = client.get("/api/admin/locations/provinces", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == province_id for item in listed.get_json()["items"])

    updated = client.patch(
        f"/api/admin/locations/provinces/{province_id}", json={"name_fa": "قم (ویرایش)"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.get_json()["item"]["name_fa"] == "قم (ویرایش)"

    removed = client.delete(f"/api/admin/locations/provinces/{province_id}", headers=headers)
    assert removed.status_code == 200
    assert removed.get_json()["item"]["is_active"] is False

    unknown = client.get("/api/admin/locations/bogus", headers=headers)
    assert unknown.status_code == 404
