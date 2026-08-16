from __future__ import annotations

import json

import pytest

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import ExpertUser


@pytest.fixture()
def identity_app(tmp_path):
    manifest = tmp_path / "release-manifest.json"
    manifest.write_text(json.dumps({
        "application_version": "1.9.3", "git_tag": "v1.9.3",
        "git_commit": "1234567890abcdef1234567890abcdef12345678",
        "database_revision": "20260825_admin_multitenant",
        "package_hash": "secret-hash", "git_tree": "secret-tree",
        "git_tag_object": "secret-tag-object", "environment_fingerprint": "secret-env",
        "database_url": "postgresql://secret", "absolute_path": "C:/secret",
    }), encoding="utf-8")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "RELEASE_IDENTITY_PATH": str(manifest)})
    with app.app_context():
        users = [
            ExpertUser(username="identity-user", password_hash="unused", full_name="User", role="expert", is_active=True),
            ExpertUser(username="identity-admin", password_hash="unused", full_name="Admin", role="admin", is_active=True),
        ]
        db.session.add_all(users)
        db.session.commit()
        app.config["identity_tokens"] = [auth_manager.generate_tokens(user.id)["access_token"] for user in users]
    return app


def test_release_identity_requires_auth_and_minimizes_normal_projection(identity_app):
    client = identity_app.test_client()
    assert client.get("/api/system/release-identity").status_code == 401
    response = client.get("/api/system/release-identity", headers={"Authorization": f"Bearer {identity_app.config['identity_tokens'][0]}"})
    assert response.status_code == 200
    assert response.json == {"data": {"application_version": "1.9.3"}, "projection": "normal"}


def test_release_identity_support_projection_is_explicitly_allowlisted(identity_app):
    response = identity_app.test_client().get("/api/system/release-identity", headers={"Authorization": f"Bearer {identity_app.config['identity_tokens'][1]}"})
    assert response.status_code == 200 and response.json["projection"] == "support"
    assert response.json["data"] == {
        "application_version": "1.9.3", "frontend_version": "1.9.3", "backend_version": "1.9.5.1",
        "release_tag": "v1.9.3", "short_commit": "1234567890ab",
        "database_revision": "20260825_admin_multitenant",
    }
    body = response.get_data(as_text=True).lower()
    for forbidden in ("package_hash", "git_tree", "git_tag_object", "environment_fingerprint", "postgresql://", "c:/secret"):
        assert forbidden not in body
