"""Disposable PostgreSQL certification for ADR-041 Phase 2 governance."""
import os

import pytest
from sqlalchemy import inspect

from backend import create_app
from backend.extensions import db
from backend.logistics_network_models import LogisticsPointType
from backend.models import Country, ExpertUser
from backend.services import global_logistics_point_service as service

POSTGRES_URL = os.environ.get("GLOBAL_POINT_DISPOSABLE_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="requires explicit disposable PostgreSQL URL")


def test_migrated_postgresql_governance_lifecycle_and_constraints():
    assert POSTGRES_URL.startswith(("postgresql://", "postgresql+psycopg"))
    assert "global_point_phase2_" in POSTGRES_URL and "127.0.0.1" in POSTGRES_URL
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": POSTGRES_URL,
        "SECRET_KEY": "disposable-global-point-certification"}, skip_startup=True)
    with app.app_context():
        assert "global_logistics_point" in inspect(db.engine).get_table_names()
        actor = ExpertUser(username="global-point-pg-admin", password_hash="x", full_name="PG Admin",
            role="admin", authority="PLATFORM_ADMIN", is_active=True)
        country = Country(code="XZ", name_en="Certification Country", name_fa="کشور آزمون")
        db.session.add_all([actor, country]); db.session.flush()
        point_type = LogisticsPointType(immutable_code="PORT", fa_name="بندر", en_name="Port",
            created_by=actor.id, updated_by=actor.id)
        db.session.add(point_type); db.session.commit()
        payload = {"immutable_code":"XZ-PG-PORT-1","point_type_public_id":point_type.public_id,
            "country_code":"XZ","fa_name":"بندر آزمون","en_name":"Certification Port",
            "facility_identity_key":"certification-port","city_name":"Test City",
            "timezone":"UTC","border_side":"NOT_APPLICABLE","supported_modes":["SEA"],
            "aliases":[{"value":"PG Test Port","language_code":"en"}],
            "external_codes":[{"scheme":"CERT","value":"PG-1"}],
            "corridor_tags":["CERT_CORRIDOR"],"sources":[{"organization":"Certification Authority",
            "reference":"disposable:postgresql","version":"1"}]}
        row = service.create(payload, actor.id)
        assert row.lifecycle_status == "DRAFT" and row.version == 1
        with pytest.raises(Exception) as duplicate:
            service.create(payload, actor.id)
        assert getattr(duplicate.value, "code", None) == "DUPLICATE_CONFLICT"
        row = service.review(row.public_id, {"expected_version":1,"evidence_reference":"pg:review"}, actor.id)
        row = service.verify(row.public_id, {"expected_version":2,"evidence_reference":"pg:verify"}, actor.id)
        row = service.activate(row.public_id, {"expected_version":3}, actor.id)
        assert row.lifecycle_status == "ACTIVE" and row.verification_status == "VERIFIED" and row.version == 4
        row = service.deprecate(row.public_id, {"expected_version":4,"reason":"PG lifecycle certification"}, actor.id)
        assert row.lifecycle_status == "DEPRECATED" and row.version == 5
        assert len(row.sources) == 4
