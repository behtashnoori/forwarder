import bcrypt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import CargoType, ExpertUser, ServiceType, UnitOfMeasure
from backend.services import master_data_service as svc
from backend.services.auth_session_service import create_session_tokens


@pytest.fixture()
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def payload(code="CODE"):
    return {"immutable_code": code, "fa_name": "نام فارسی", "en_name": "English name", "display_order": 2}


def test_crud_bilingual_code_and_optimistic_locking(app):
    with app.app_context():
        row = svc.create("service-types", payload("road"))
        assert row.immutable_code == "ROAD" and row.version == 1
        row = svc.update(row, {"fa_name": "نام جدید", "version": 1})
        assert row.version == 2
        with pytest.raises(svc.VersionConflictError):
            svc.update(row, {"en_name": "stale", "version": 1})
        with pytest.raises(svc.MasterDataValidationError):
            svc.update(row, {"immutable_code": "OTHER", "version": 2})
        row.immutable_code = "DIRECT_CHANGE"
        with pytest.raises(ValueError, match="immutable_code cannot be changed"):
            db.session.commit()
        db.session.rollback()
        with pytest.raises(svc.MasterDataValidationError):
            svc.create("service-types", payload("ROAD"))
        assert ServiceType.query.count() == 1


def test_unit_dimension_is_governed(app):
    with app.app_context():
        data = {**payload("KG"), "symbol": "kg", "measurement_dimension": "WEIGHT"}
        assert svc.create("units-of-measure", data).measurement_dimension == "WEIGHT"
        with pytest.raises(svc.MasterDataValidationError):
            svc.create("units-of-measure", {**data, "immutable_code": "BAD", "measurement_dimension": "mass-ish"})
        assert UnitOfMeasure.query.count() == 1


def test_cargo_hierarchy_cycle_and_inactive_parent_rules(app):
    with app.app_context():
        root = svc.create("cargo-types", payload("ROOT"))
        child = svc.create("cargo-types", {**payload("CHILD"), "parent_id": root.public_id})
        with pytest.raises(svc.MasterDataValidationError):
            svc.update(root, {"parent_id": child.public_id, "version": root.version})
        with pytest.raises(svc.MasterDataValidationError):
            svc.set_active(root, False, root.version)
        svc.set_active(child, False, child.version)
        svc.set_active(root, False, root.version)
        with pytest.raises(svc.MasterDataValidationError):
            svc.create("cargo-types", {**payload("LATE"), "parent_id": root.public_id})
        assert CargoType.query.count() == 2


def _headers(app, role="admin"):
    with app.app_context():
        user = ExpertUser(username=f"{role}_master", password_hash=bcrypt.hashpw(b"password", bcrypt.gensalt()).decode(), full_name="Master Admin", email=f"{role}@example.test", role=role, authority="PLATFORM_ADMIN" if role == "admin" else "EXPERT", is_active=True)
        db.session.add(user); db.session.commit()
        token = create_session_tokens(user.id)["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_api_roundtrip_pagination_and_permissions(app):
    client = app.test_client()
    assert client.get("/api/admin/master-data/service-types").status_code == 401
    assert client.get("/api/admin/master-data/service-types", headers=_headers(app, "expert")).status_code == 403
    headers = _headers(app)
    created = client.post("/api/admin/master-data/service-types", json=payload("AIR"), headers=headers)
    assert created.status_code == 201
    item = created.get_json()["item"]
    assert "id" not in item
    detail = client.get(f"/api/admin/master-data/service-types/{item['public_id']}", headers=headers)
    assert detail.status_code == 200
    listed = client.get("/api/admin/master-data/service-types?q=air&page=1&per_page=1", headers=headers).get_json()
    assert listed["total"] == 1 and listed["pages"] == 1
    updated = client.patch(f"/api/admin/master-data/service-types/{item['public_id']}", json={"en_name": "Air freight", "version": 1}, headers=headers)
    assert updated.status_code == 200 and updated.get_json()["item"]["version"] == 2
    conflict = client.patch(f"/api/admin/master-data/service-types/{item['public_id']}", json={"en_name": "stale", "version": 1}, headers=headers)
    assert conflict.status_code == 409
    deactivated = client.post(f"/api/admin/master-data/service-types/{item['public_id']}/deactivate", json={"version": 2}, headers=headers)
    assert deactivated.status_code == 200 and deactivated.get_json()["item"]["is_active"] is False


def test_resource_specific_fields_and_search_bound_are_rejected(app):
    client = app.test_client()
    headers = _headers(app)
    invalid_field = client.post(
        "/api/admin/master-data/service-types",
        json={**payload("SEA"), "measurement_dimension": "VOLUME"},
        headers=headers,
    )
    assert invalid_field.status_code == 400
    oversized_search = client.get(
        "/api/admin/master-data/service-types?q=" + ("x" * 161), headers=headers
    )
    assert oversized_search.status_code == 400
    dimension_on_wrong_resource = client.get(
        "/api/admin/master-data/service-types?measurement_dimension=WEIGHT", headers=headers
    )
    assert dimension_on_wrong_resource.status_code == 200
