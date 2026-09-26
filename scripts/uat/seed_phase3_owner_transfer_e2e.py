"""Owned synthetic current-owner, private document and independent-work journey."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalShipment, OperationalWorkItem, ProjectAccess, utcnow
from scripts.uat.seed_phase3_customer_shipment_e2e import main as seed_customer
from scripts.uat.seed_shared_transport_e2e import fixture_user


def main():
    seed_customer()
    path=Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture=json.loads(path.read_text(encoding="utf-8"))
    app=create_app(skip_startup=True)
    with app.app_context():
        shipment=OperationalShipment.query.filter_by(public_id=fixture["p304_shipment"]).one()
        old=OperationalMembership.query.filter_by(user_id=shipment.primary_responsible_expert_id,organization_id=shipment.organization_id).one()
        target=fixture_user(suffix="transfer_target",authority="EXPERT",password=os.environ["FORWARDER_E2E_PASSWORD"])
        third=ExpertUser.query.filter_by(username="shared_transport_e2e_zero").one()
        db.session.flush()
        db.session.add(OperationalMembership(user_id=target.id,organization_id=shipment.organization_id,permissions=list(old.permissions)))
        # This isolated case demonstrates loss of ownership-derived access;
        # independent Project access is exercised separately by the unit suite.
        ProjectAccess.query.filter_by(project_id=shipment.project_id,user_id=old.user_id).delete()
        for identity in (old.user_id,third.id):
            db.session.add(OperationalWorkItem(organization_id=shipment.organization_id,operational_shipment_id=shipment.id,
                work_type="FOLLOW_UP",action_context_type="SHIPMENT",assignee_user_id=identity,due_at=utcnow(),reason="P313 retained work"))
        db.session.commit()
        fixture.update(p313_shipment=shipment.public_id,p313_target_id=target.id,p313_target_label=target.full_name)
    path.write_text(json.dumps(fixture),encoding="utf-8")


if __name__=="__main__": main()
