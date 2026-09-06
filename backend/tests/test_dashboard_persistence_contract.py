from copy import deepcopy

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.dashboard_models import DashboardRevision
from backend import dashboard_service as service
from backend.services.operational_service import OperationalError


@pytest.fixture()
def dashboard_context():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "dashboard-test"}, skip_startup=True)
    with app.app_context():
        db.create_all()
        first = ExpertUser(username="dashboard-a", password_hash="x", full_name="A")
        second = ExpertUser(username="dashboard-b", password_hash="x", full_name="B")
        other = ExpertUser(username="dashboard-c", password_hash="x", full_name="C")
        org_a, org_b = OperationalOrganization(name="Org A"), OperationalOrganization(name="Org B")
        db.session.add_all([first, second, other, org_a, org_b]); db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=org_a.id, user_id=first.id, permissions=["operational_shipment.read"]),
            OperationalMembership(organization_id=org_a.id, user_id=second.id, permissions=["operational_shipment.read"]),
            OperationalMembership(organization_id=org_b.id, user_id=other.id, permissions=["operational_shipment.read"]),
        ])
        db.session.commit()
        yield {"a": {"id": first.id}, "b": {"id": second.id}, "other": {"id": other.id}}
        db.session.remove(); db.drop_all()


def test_exact_clone_revision_and_private_tenant_boundary(dashboard_context):
    user = dashboard_context["a"]
    first = service.clone("operations-control-tower", user)
    second = service.clone("operations-control-tower", user)
    canonical = service.system_dashboard("operations-control-tower")
    assert first["definition"] == canonical["definition"]
    assert first["source_type"] == "SYSTEM"
    assert first["source_dashboard_public_id"] == canonical["system_dashboard_id"]
    assert first["source_version"] == canonical["system_version"]
    assert first["version"] == 1 and first["visibility"] == "PRIVATE" and first["cloned_at"]
    assert first["public_id"] != second["public_id"]
    assert db.session.query(DashboardRevision).filter_by(revision_number=1).count() == 2
    with pytest.raises(OperationalError) as denied:
        service.get(first["public_id"], dashboard_context["b"])
    assert denied.value.code == "DASHBOARD_NOT_FOUND"
    with pytest.raises(OperationalError) as cross_org:
        service.get(first["public_id"], dashboard_context["other"])
    assert cross_org.value.code == "DASHBOARD_NOT_FOUND"


def test_revision_concurrency_and_lifecycle_do_not_mutate_history(dashboard_context):
    user = dashboard_context["a"]
    created = service.clone("operations-control-tower", user)
    updated = service.update(created["public_id"], {"expected_version": 1, "name": "نسخهٔ من"}, user)
    assert updated["version"] == 2
    assert db.session.query(DashboardRevision).filter_by(dashboard_id=db.session.query(DashboardRevision).first().dashboard_id).count() == 2
    with pytest.raises(OperationalError) as conflict:
        service.update(created["public_id"], {"expected_version": 1, "name": "قدیمی"}, user)
    assert conflict.value.code == "DASHBOARD_VERSION_CONFLICT" and conflict.value.status == 409
    with pytest.raises(OperationalError) as invalid:
        service.update(created["public_id"], {"expected_version": 2}, user)
    assert invalid.value.code == "EMPTY_DASHBOARD_PATCH"
    before = db.session.query(DashboardRevision).count()
    assert service.lifecycle(created["public_id"], user, "ARCHIVED")["status"] == "ARCHIVED"
    assert service.lifecycle(created["public_id"], user, "ACTIVE")["status"] == "ACTIVE"
    assert db.session.query(DashboardRevision).count() == before


def test_invalid_definition_creates_no_revision(dashboard_context):
    user = dashboard_context["a"]
    created = service.clone("operations-control-tower", user)
    invalid = deepcopy(created["definition"])
    invalid["widgets"][0]["query"]["metric_keys"] = ["NOT_A_METRIC"]
    before = db.session.query(DashboardRevision).count()
    with pytest.raises(ValueError):
        service.update(created["public_id"], {"expected_version": 1, "definition": invalid}, user)
    assert db.session.query(DashboardRevision).count() == before
    assert service.get(created["public_id"], user)["version"] == 1
