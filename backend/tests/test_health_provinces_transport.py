"""Tests for /api/health, /api/provinces, /api/transport-methods (no 500 on empty DB)."""
import json
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import Province, TransportMethod


@pytest.fixture
def app_with_tables():
    """App with in-memory DB and critical tables created (no migrations)."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    })
    with app.app_context():
        db.create_all()
    return app


@pytest.fixture
def client(app_with_tables):
    return app_with_tables.test_client()


def test_health_returns_200_when_db_connected(client):
    """GET /api/health returns 200 with status ok when DB is connected."""
    r = client.get("/api/health")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data.get("status") == "ok"
    assert data.get("database") == "connected"
    assert "port" in data


def test_health_ping_returns_200(client):
    """GET /api/health/ping returns 200."""
    r = client.get("/api/health/ping")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data.get("status") == "ok"


def test_provinces_returns_200_empty_list(client):
    """GET /api/provinces returns 200 with [] when table is empty."""
    r = client.get("/api/provinces")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert isinstance(data, list)
    assert len(data) == 0


def test_transport_methods_returns_200_empty_lists(client):
    """GET /api/transport-methods returns 200 with empty lists when table is empty."""
    r = client.get("/api/transport-methods")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert "international_methods" in data
    assert "domestic_methods" in data
    assert "preference_options" in data
    assert isinstance(data["international_methods"], list)
    assert isinstance(data["domestic_methods"], list)
    assert isinstance(data["preference_options"], list)
    assert len(data["preference_options"]) >= 2  # seed defines at least 2 options


def test_provinces_returns_data_when_seeded(app_with_tables):
    """GET /api/provinces returns 200 with data when province table has rows."""
    with app_with_tables.app_context():
        db.session.add(Province(name_fa="تهران", code="TEH"))
        db.session.commit()
    client = app_with_tables.test_client()
    r = client.get("/api/provinces")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert len(data) == 1
    assert data[0]["name"] == "تهران"
    assert data[0]["code"] == "TEH"


def test_transport_methods_returns_data_when_seeded(app_with_tables):
    """GET /api/transport-methods returns 200 with methods when table has rows."""
    with app_with_tables.app_context():
        db.session.add(
            TransportMethod(name="Sea Freight", name_fa="حمل دریایی", description="دریایی", is_active=True)
        )
        db.session.commit()
    client = app_with_tables.test_client()
    r = client.get("/api/transport-methods")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert len(data["international_methods"]) >= 1 or len(data["domestic_methods"]) >= 1
