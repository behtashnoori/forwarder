from __future__ import annotations

import pytest

from backend import create_app
from backend.analytics import service as analytics
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import Project, ProjectAccess
from backend.personal_analytics_uat import ensure_safe_target, provision
from backend.services import project_access_authorization
from backend.services.operational_service import OperationalError


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    result = create_app({"TESTING":True, "SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:", "SECRET_KEY":"test"}, skip_startup=True)
    with result.app_context(): db.create_all()
    return result


def test_personal_analytics_fixture_is_idempotent_and_authorized(app):
    with app.app_context():
        first = provision(app, "synthetic-password")
        second = provision(app, "synthetic-password")
        assert first == second
        expert = ExpertUser.query.filter_by(username="personal_analytics_uat_expert_a").one()
        rows = analytics.query({"query_kind":"ROWSET", "semantic_version":"analytics-semantic-v2", "population":"SHIPMENTS", "columns":["PROJECT"], "filters":[{"dimension":"SHIPMENT_STATUS","value":"planned"}], "operational_window":{"from":"2041-01-01T00:00:00+00:00","to":"2041-01-02T00:00:00+00:00"}, "sort":{"field":"PLANNED_DEPARTURE","direction":"ASC"}, "limit":20}, {"id":expert.id})["rows"]
        assert [row["shipment_public_id"] for row in rows] == [first["shipment_public_ids"][key] for key in ("project_only","direct","request")]
        grant = ProjectAccess.query.filter_by(user_id=expert.id).one()
        admin = ExpertUser.query.filter_by(username="personal_analytics_uat_admin_a").one()
        project_access_authorization.revoke_assignment(Project.query.get(grant.project_id).public_id, grant.public_id, {"id":admin.id})
        after = analytics.query({"query_kind":"ROWSET", "semantic_version":"analytics-semantic-v2", "population":"SHIPMENTS", "columns":["PROJECT"], "filters":[{"dimension":"SHIPMENT_STATUS","value":"planned"}], "operational_window":{"from":"2041-01-01T00:00:00+00:00","to":"2041-01-02T00:00:00+00:00"}, "sort":{"field":"PLANNED_DEPARTURE","direction":"ASC"}, "limit":20}, {"id":expert.id})["rows"]
        assert [row["shipment_public_id"] for row in after] == [first["shipment_public_ids"][key] for key in ("direct","request")]


def test_fixture_rejects_production(app, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with app.app_context(), pytest.raises(OperationalError):
        ensure_safe_target(app)
