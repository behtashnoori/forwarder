"""Tests for CORS configuration."""
import os
import pytest
from backend import create_app


@pytest.fixture
def app_with_cors():
    """Create app with CORS allowed (dev mode)."""
    orig_env = os.environ.get("FLASK_ENV"), os.environ.get("FLASK_DEBUG")
    os.environ["FLASK_ENV"] = "development"
    os.environ["FLASK_DEBUG"] = "true"
    try:
        app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-secret",
            "JWT_SECRET_KEY": "test-jwt",
        })
        yield app
    finally:
        if orig_env[0] is not None:
            os.environ["FLASK_ENV"] = orig_env[0]
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]
        if orig_env[1] is not None:
            os.environ["FLASK_DEBUG"] = orig_env[1]
        elif "FLASK_DEBUG" in os.environ:
            del os.environ["FLASK_DEBUG"]


@pytest.fixture
def client(app_with_cors):
    """Test client for app."""
    return app_with_cors.test_client()


ORIGIN = "http://127.0.0.1:8080"


def test_options_provinces_returns_cors_headers(client):
    """OPTIONS /api/provinces must include Access-Control-Allow-Origin."""
    response = client.open(
        "/api/provinces",
        method="OPTIONS",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == ORIGIN
    assert "Access-Control-Allow-Credentials" in response.headers
    assert "Access-Control-Allow-Methods" in response.headers
    assert "GET" in response.headers["Access-Control-Allow-Methods"]


def test_options_transport_methods_returns_cors_headers(client):
    """OPTIONS /api/transport-methods must include Access-Control-Allow-Origin."""
    response = client.open(
        "/api/transport-methods",
        method="OPTIONS",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == ORIGIN
    assert "Access-Control-Allow-Credentials" in response.headers
    assert "Access-Control-Allow-Methods" in response.headers
    assert "GET" in response.headers["Access-Control-Allow-Methods"]
