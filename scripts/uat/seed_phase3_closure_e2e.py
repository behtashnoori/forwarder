"""Owned synthetic completed/predecessor cases; never seeds closure or policy."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend import create_app
from backend.extensions import db
from backend.operational_models import OperationalShipment, RoutePlan, RouteLeg
from scripts.uat.seed_phase3_customer_shipment_e2e import main as seed_customer


def main():
    seed_customer()
    path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        original = OperationalShipment.query.filter_by(public_id=fixture["p304_shipment"]).one()
        original.lifecycle_status = "completed"
        leg = db.session.get(RouteLeg, fixture["p304_road_leg"])
        for name, state in (("exception", "completed"), ("planned", "planned")):
            shipment = OperationalShipment(organization_id=original.organization_id, source_type="direct",
                customer_id=original.customer_id, lifecycle_status=state,
                created_by_user_id=original.primary_responsible_expert_id,
                primary_responsible_expert_id=original.primary_responsible_expert_id)
            db.session.add(shipment); db.session.flush()
            plan = RoutePlan(operational_shipment_id=shipment.id, revision_number=1, status="active",is_active=True,
                created_by_user_id=original.primary_responsible_expert_id)
            db.session.add(plan); db.session.flush()
            db.session.add(RouteLeg(route_plan_id=plan.id,sequence_number=1,origin_location_id=leg.origin_location_id,
                destination_location_id=leg.destination_location_id,origin_snapshot=leg.origin_snapshot,
                destination_snapshot=leg.destination_snapshot,transport_mode="road",status="planned",
                planned_departure=leg.planned_departure,planned_arrival=leg.planned_arrival))
            db.session.flush();fixture[f"p312_{name}"]=shipment.public_id
        db.session.commit()
        fixture["p312_normal"] = original.public_id
    path.write_text(json.dumps(fixture),encoding="utf-8")


if __name__ == "__main__": main()
