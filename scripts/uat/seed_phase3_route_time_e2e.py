"""Owned synthetic logistics points and two independent draft-planning contexts."""
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend import create_app
from backend.extensions import db
from backend.models import Country, ExpertUser
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.operational_models import OperationalShipment, OperationalMembership
from backend.services import route_time_service as svc
from scripts.uat.seed_phase3_branched_route_e2e import main as seed_route


def main():
    seed_route()
    path=Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture=json.loads(path.read_text(encoding="utf-8"))
    app=create_app(skip_startup=True)
    with app.app_context():
        old=OperationalShipment.query.filter_by(public_id=fixture["p3_route_shipment"]).one()
        admin=ExpertUser.query.filter_by(username="shared_transport_e2e_admin").one()
        foreign=ExpertUser.query.filter_by(username="shared_transport_e2e_foreign").one()
        foreign.authority="ORGANIZATION_ADMIN";foreign.role="admin"
        foreign_org=OperationalMembership.query.filter_by(user_id=foreign.id).one().organization_id
        country=Country.query.filter_by(code="ZZ").one_or_none()
        if country is None:
            country=Country(code="ZZ",name_fa="کشور مصنوعی آزمون",name_en="Synthetic test country",is_active=True)
            db.session.add(country);db.session.flush()
        kind=LogisticsPointType(immutable_code="P310_SYNTHETIC",fa_name="نقطه آزمایشی",en_name="Synthetic point",is_active=True,created_by=admin.id,updated_by=admin.id)
        db.session.add(kind);db.session.flush()
        points={}
        for org,actor,prefix in ((old.organization_id,admin.id,"own"),(foreign_org,foreign.id,"foreign")):
            for code,label in (("origin","خورگوس"),("destination","آکتائو")):
                row=LogisticsPoint(organization_id=org,immutable_code=f"P310-{code}",logistics_point_type_id=kind.id,
                    fa_name=label,normalized_name=f"p310 {code}",country_id=country.id,geography_key=f"country:{country.id}",is_active=True,created_by=actor,updated_by=actor)
                db.session.add(row);db.session.flush();points[f"{prefix}_{code}"]=row.public_id
        new=OperationalShipment(organization_id=old.organization_id,source_type="direct",customer_id=old.customer_id,
            lifecycle_status="planned",created_by_user_id=old.primary_responsible_expert_id,primary_responsible_expert_id=old.primary_responsible_expert_id)
        db.session.add(new);db.session.commit()
        foreign_version,_=svc.save({"id":foreign.id}, {"origin":{"source_type":"logistics_point","source_id":points["foreign_origin"]},
            "destination":{"source_type":"logistics_point","source_id":points["foreign_destination"]},"transport_mode":"rail",
            "movement_min_minutes":600,"movement_max_minutes":900,"effective_from":(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()},str(uuid4()))
        db.session.commit()
        from backend.route_time_models import OrganizationRouteTime
        fixture.update(p310_old_shipment=old.public_id,p310_new_shipment=new.public_id,p310_points=points,
            p310_foreign_reference=db.session.get(OrganizationRouteTime,foreign_version.reference_id).public_id)
        path.write_text(json.dumps(fixture),encoding="utf-8")


if __name__=="__main__":main()
