import pytest
from backend import create_app
from backend.extensions import db
from backend.external_reference_models import ExternalReferenceType
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from scripts.repair_forwarder_production_workflow import run

@pytest.fixture()
def app():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:"})
    with app.app_context():
        org=OperationalOrganization(name="Repair"); user=ExpertUser(username="repair-expert",password_hash="x",full_name="Repair",role="expert",is_active=True); db.session.add_all([org,user]); db.session.flush(); db.session.add(OperationalMembership(organization_id=org.id,user_id=user.id,is_active=True,permissions=["operational_shipment.read"])); db.session.commit()
    return app

def test_missing_rows_are_created_transactionally_and_idempotently(app):
    with app.app_context():
        _,plan=run(user_identifier="repair-expert",execute=False); assert plan["plan"]["reference_plan"]["CMR_NUMBER"]["action"]=="CREATE"
        _,result=run(user_identifier="repair-expert",execute=True); assert result["result"]=="REPAIRED" and ExternalReferenceType.query.count()==3
        assert OperationalMembership.query.one().permissions==["operational_shipment.read","execution_unit.create","execution_unit.update"]
        _,again=run(user_identifier="repair-expert",execute=True); assert again["permissions_added"]==[] and again["after"]["REFERENCE_DATA_CONFIGURATION_REQUIRED"]=="NO"

def test_conflict_stops_without_permission_write(app):
    with app.app_context():
        u=ExpertUser.query.one(); db.session.add(ExternalReferenceType(code="CMR_NUMBER",name_fa="conflict",name_en="CMR Number",lifecycle_status="ACTIVE",source_authority="UNECE",provenance_reference="CMR Convention and UN/EDIFACT 1153 CMR",allows_operational_shipment=True,allows_execution_unit=True,created_by_user_id=u.id,updated_by_user_id=u.id)); db.session.commit()
        code,report=run(user_identifier="repair-expert",execute=True); assert code==2 and report["result"]=="REFERENCE_DEFINITION_CONFLICT_STOP" and OperationalMembership.query.one().permissions==["operational_shipment.read"]
