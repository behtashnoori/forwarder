from datetime import datetime, timedelta

import bcrypt
import jwt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import AuthSession, ExpertUser, RevokedToken
from backend.security import security
from backend.services import user_service
from backend.services.auth_session_service import cleanup_sessions, create_session_tokens


@pytest.fixture()
def session_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        user = ExpertUser(
            username="session-user",
            password_hash=bcrypt.hashpw(b"SafeTest123!", bcrypt.gensalt()).decode(),
            full_name="Session User",
            role="admin",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        yield app, user.id
        db.session.remove()
        db.drop_all()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_sessions_rotation_replay_and_independent_session(session_app):
    app, user_id = session_app
    client = app.test_client()
    with app.app_context():
        first = create_session_tokens(user_id)
        second = create_session_tokens(user_id)
        first_access = security.verify_token(first["access_token"])
        first_refresh = security.verify_token(first["refresh_token"])
        second_access = security.verify_token(second["access_token"])
        assert first_access["sid"] == first_refresh["sid"]
        assert first_access["jti"] != first_refresh["jti"]
        assert first_access["sid"] != second_access["sid"]

    rotated = client.post("/api/expert/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200
    rotated_tokens = rotated.get_json()
    assert rotated_tokens.keys() >= {"access_token", "refresh_token", "token_type", "expires_in"}
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(rotated_tokens["access_token"])).status_code == 200

    replay = client.post("/api/expert/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(rotated_tokens["access_token"])).status_code == 401
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(second["access_token"])).status_code == 200
    with app.app_context():
        session = AuthSession.query.filter_by(session_id=first_access["sid"]).one()
        assert not session.is_active
        assert session.revoked_reason == "refresh_reuse_detected"


def test_logout_and_logout_all_revoke_sessions_without_exposing_sid(session_app):
    app, user_id = session_app
    client = app.test_client()
    with app.app_context():
        first = create_session_tokens(user_id)
        second = create_session_tokens(user_id)
    response = client.post("/api/expert/auth/logout", headers=_headers(first["access_token"]))
    assert response.status_code == 200
    assert "session" not in str(response.get_json()).lower()
    assert client.post("/api/expert/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(second["access_token"])).status_code == 200
    all_response = client.post("/api/expert/auth/logout-all", headers=_headers(second["access_token"]))
    assert all_response.status_code == 200
    assert client.post("/api/expert/auth/refresh", json={"refresh_token": second["refresh_token"]}).status_code == 401


def test_password_deactivation_deletion_and_role_state_invalidate(session_app):
    app, user_id = session_app
    client = app.test_client()
    with app.app_context():
        password_session = create_session_tokens(user_id)
        user_service.update_user(user_id, {"password": "Changed-Safe-42!"})
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(password_session["access_token"])).status_code == 401
    assert client.post("/api/expert/auth/refresh", json={"refresh_token": password_session["refresh_token"]}).status_code == 401

    with app.app_context():
        active_session = create_session_tokens(user_id)
        user_service.update_user(user_id, {"is_active": False})
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(active_session["access_token"])).status_code == 401

    with app.app_context():
        user = db.session.get(ExpertUser, user_id)
        user.is_active = True
        db.session.commit()
        deleted_session = create_session_tokens(user_id)
        db.session.delete(user)
        db.session.commit()
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(deleted_session["access_token"])).status_code == 401


def test_token_type_missing_session_expiry_and_cleanup(session_app):
    app, user_id = session_app
    client = app.test_client()
    with app.app_context():
        tokens = create_session_tokens(user_id)
        access_payload = security.verify_token(tokens["access_token"])
        missing_sid = jwt.encode(
            {k: v for k, v in access_payload.items() if k != "sid"},
            app.config["JWT_SECRET_KEY"],
            algorithm="HS256",
        )
        session = AuthSession.query.filter_by(session_id=access_payload["sid"]).one()
        session.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(tokens["refresh_token"])).status_code == 401
    assert client.post("/api/expert/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(missing_sid)).status_code == 401
    assert client.get("/api/expert/dashboard/kpis", headers=_headers(tokens["access_token"])).status_code == 401
    assert client.post("/api/expert/auth/refresh", json={"refresh_token": "malformed"}).status_code == 401

    with app.app_context():
        assert cleanup_sessions(dry_run=True) == 1
        assert AuthSession.query.count() == 1
        assert cleanup_sessions(dry_run=False) == 1
        assert cleanup_sessions(dry_run=False) == 0
        assert not any(c.name in {"access_token", "refresh_token", "token_hash"} for c in AuthSession.__table__.columns)
        assert RevokedToken.query.filter(RevokedToken.reason == "refresh_rotated").count() == 0


def test_session_policy_is_configurable_and_absolute_lifetime_does_not_slide():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_ACCESS_TOKEN_EXPIRES": timedelta(minutes=5),
            "JWT_REFRESH_TOKEN_EXPIRES": timedelta(days=30),
            "SESSION_ABSOLUTE_LIFETIME": timedelta(days=90),
            "JWT_CLOCK_SKEW_SECONDS": 17,
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        user = ExpertUser(
            username="absolute-session-user",
            password_hash=bcrypt.hashpw(b"SafeTest123!", bcrypt.gensalt()).decode(),
            full_name="Absolute Session User",
            role="admin",
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        tokens = create_session_tokens(user.id)
        payload = security.verify_token(tokens["refresh_token"])
        session = AuthSession.query.filter_by(session_id=payload["sid"]).one()
        session.created_at = datetime.utcnow() - timedelta(days=89, hours=23)
        session.expires_at = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()

        rotated = app.test_client().post(
            "/api/expert/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert rotated.status_code == 200
        db.session.refresh(session)
        assert session.expires_at <= session.created_at + timedelta(days=90)
        assert app.config["JWT_ACCESS_TOKEN_EXPIRES"] == timedelta(minutes=5)
        assert app.config["JWT_CLOCK_SKEW_SECONDS"] == 17
