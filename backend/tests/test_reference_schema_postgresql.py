"""Explicit disposable-PostgreSQL checks for the reference schema expansion."""
import os

import pytest
from sqlalchemy import inspect, text

from backend import create_app
from backend.extensions import db


def test_reference_schema_constraints_on_disposable_postgresql():
    url = os.environ.get("FORWARDER_REFERENCE_SCHEMA_TEST_URL")
    if not url:
        pytest.skip("explicit disposable reference-schema PostgreSQL URL not provided")
    name = url.rstrip("/").rsplit("/", 1)[-1]
    assert name == "forwarder_reference_schema_test_20260720"
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": url, "SECRET_KEY": "synthetic-only"}, skip_startup=True)
    with app.app_context():
        inspector = inspect(db.engine)
        assert {"port_location", "customs_province_mapping"} <= set(inspector.get_table_names())
        assert db.session.execute(text("select version_num from alembic_version")).scalar_one() == "20260720_expand_reference_data_identity"
        assert db.session.execute(text("select count(*) from port_location")).scalar_one() == 0
        assert db.session.execute(text("select count(*) from customs_province_mapping")).scalar_one() == 0
        constraints = {item["name"] for item in inspector.get_unique_constraints("port_province_mapping")}
        assert "uq_port_province_mapping" in constraints
        indexes = {item["name"] for item in inspector.get_indexes("port_location")}
        assert "uq_port_location_active_port" in indexes
        db.session.rollback()
