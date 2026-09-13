"""The production repair must be additive and scoped to one selected Expert."""
import pytest

from backend import create_app
from backend.extensions import db
from backend.external_reference_models import ExternalReferenceType
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from scripts.repair_forwarder_production_workflow import run


@pytest.fixture()
def repair_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        org = OperationalOrganization(name="Repair test")
        user = ExpertUser(username="repair-expert", password_hash="unused", full_name="Repair Expert", role="expert", is_active=True)
        db.session.add_all([org, user])
        db.session.flush()
        db.session.add(OperationalMembership(organization_id=org.id, user_id=user.id, is_active=True, permissions=["operational_shipment.read"]))
        for code in ("BILL_OF_LADING_NUMBER", "AIR_WAYBILL_NUMBER", "CMR_NUMBER"):
            from scripts.repair_forwarder_production_workflow import PACKAGE_PATH
            from backend.external_reference_type_package import load_package
            item = next(item for item in load_package(PACKAGE_PATH).definitions if item["code"] == code)
            db.session.add(ExternalReferenceType(code=code, name_fa=item["name_fa"], name_en=item["name_en"], lifecycle_status="DRAFT", source_authority=item["provenance"]["source_authority"], provenance_reference=item["provenance"]["source_reference"], allows_operational_shipment=False, allows_execution_unit=True, created_by_user_id=user.id, updated_by_user_id=user.id))
        db.session.commit()
    return app


def test_validate_and_repair_are_scoped_and_idempotent(repair_app):
    with repair_app.app_context():
        _, plan = run(user_identifier="repair-expert", execute=False)
        assert plan["result"] == "VALIDATED"
        assert plan["plan"]["membership"]["missing_permissions"] == ["execution_unit.create", "execution_unit.update"]
        assert OperationalMembership.query.one().permissions == ["operational_shipment.read"]
        _, result = run(user_identifier="repair-expert", execute=True)
        assert result["permissions_added"] == ["execution_unit.create", "execution_unit.update"]
        assert OperationalMembership.query.one().permissions == ["operational_shipment.read", "execution_unit.create", "execution_unit.update"]
        assert all(row.lifecycle_status == "ACTIVE" and row.allows_operational_shipment for row in ExternalReferenceType.query.all())
        _, again = run(user_identifier="repair-expert", execute=True)
        assert again["permissions_added"] == []


def test_missing_reference_stops_all_writes(repair_app):
    with repair_app.app_context():
        ExternalReferenceType.query.filter_by(code="CMR_NUMBER").delete()
        db.session.commit()
        code, report = run(user_identifier="repair-expert", execute=True)
        assert code == 2 and report["result"] == "REFERENCE_RECORD_MISSING_STOP"
        assert OperationalMembership.query.one().permissions == ["operational_shipment.read"]
