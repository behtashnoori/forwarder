"""Authorization contract for the shared cargo-options selector."""
import bcrypt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.auth_session_service import create_session_tokens


@pytest.fixture()
def cargo_options_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "cargo-options"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        password = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode()
        org = OperationalOrganization(public_id="cargo-org", name="Cargo Org", is_active=True)
        admin = ExpertUser(username="cargo-admin", password_hash=password, full_name="Cargo Admin", role="admin", authority="ORGANIZATION_ADMIN", is_active=True)
        reader = ExpertUser(username="cargo-reader", password_hash=password, full_name="Cargo Reader", role="expert", authority="EXPERT", is_active=True)
        denied = ExpertUser(username="cargo-denied", password_hash=password, full_name="Cargo Denied", role="expert", authority="EXPERT", is_active=True)
        db.session.add_all([org, admin, reader, denied]); db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=org.id, user_id=admin.id, is_active=True, permissions=[]),
            OperationalMembership(organization_id=org.id, user_id=reader.id, is_active=True, permissions=["operational_shipment.read"]),
            OperationalMembership(organization_id=org.id, user_id=denied.id, is_active=True, permissions=[]),
        ])
        db.session.commit()
        return app, {name: create_session_tokens(user.id)["access_token"] for name, user in (("admin", admin), ("reader", reader), ("denied", denied))}


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_cargo_options_allows_catalog_organization_admin_and_shipment_reader(cargo_options_app):
    app, tokens = cargo_options_app
    client = app.test_client()
    assert client.get("/api/internal/cargo-options", headers=_headers(tokens["admin"])).status_code == 200
    assert client.get("/api/internal/cargo-options", headers=_headers(tokens["reader"])).status_code == 200


def test_cargo_options_keeps_unprivileged_authenticated_user_forbidden(cargo_options_app):
    app, tokens = cargo_options_app
    response = app.test_client().get("/api/internal/cargo-options", headers=_headers(tokens["denied"]))
    assert response.status_code == 403
