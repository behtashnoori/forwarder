from datetime import datetime, timedelta

import bcrypt
import jwt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, RevokedToken
from backend.security import security
from backend.services.token_revocation_service import cleanup_expired


@pytest.fixture()
def revocation_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.drop_all()
        db.create_all()
        user = ExpertUser(username="security-admin", password_hash=bcrypt.hashpw(b"SafeTest123!", bcrypt.gensalt()).decode(), full_name="Security Admin", role="admin", is_active=True)
        db.session.add(user)
        db.session.commit()
        yield app, user.id
        db.session.remove()
        db.drop_all()


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_unique_jti_and_logout_revokes_only_presented_token(revocation_app):
    app, user_id = revocation_app
    client = app.test_client()
    with app.app_context():
        first = security.generate_token(user_id)
        second = security.generate_token(user_id)
        first_payload = security.verify_token(first)
        second_payload = security.verify_token(second)
        assert first_payload["jti"] != second_payload["jti"]

    assert client.get("/api/expert/dashboard/kpis", headers=_headers(first)).status_code == 200
    assert client.post("/api/expert/auth/logout", headers=_headers(first)).status_code == 200
    assert client.post("/api/expert/auth/logout", headers=_headers(first)).status_code == 401
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(first)).status_code == 401
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(second)).status_code == 200
    with app.app_context():
        row = RevokedToken.query.one()
        assert row.jti == first_payload["jti"]
        assert first not in repr(row.__dict__)


def test_missing_jti_inactive_and_missing_users_are_rejected(revocation_app):
    app, user_id = revocation_app
    client = app.test_client()
    with app.app_context():
        now = datetime.utcnow()
        without_jti = jwt.encode({"user_id": user_id, "token_type": "access", "iat": now, "exp": now + timedelta(hours=1)}, app.config["JWT_SECRET_KEY"], algorithm="HS256")
        active_token = security.generate_token(user_id)
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(without_jti)).status_code == 401
    with app.app_context():
        db.session.get(ExpertUser, user_id).is_active = False
        db.session.commit()
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(active_token)).status_code == 401
    with app.app_context():
        db.session.delete(db.session.get(ExpertUser, user_id))
        db.session.commit()
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(active_token)).status_code == 401


def test_cleanup_is_dry_run_scoped_and_idempotent(revocation_app):
    app, user_id = revocation_app
    with app.app_context():
        db.session.add_all([
            RevokedToken(jti="expired", user_id=user_id, token_type="access", expires_at=datetime.utcnow() - timedelta(seconds=1), reason="logout"),
            RevokedToken(jti="active", user_id=user_id, token_type="access", expires_at=datetime.utcnow() + timedelta(hours=1), reason="logout"),
        ])
        db.session.commit()
        assert cleanup_expired(dry_run=True) == 1
        assert RevokedToken.query.count() == 2
        assert cleanup_expired(dry_run=False) == 1
        assert cleanup_expired(dry_run=False) == 0
        assert [row.jti for row in RevokedToken.query.all()] == ["active"]
