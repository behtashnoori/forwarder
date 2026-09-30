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
from backend.geonames_geography_catalog import DATASET_ID as GEONAMES_DATASET_ID
from backend.models import City, Country, ExpertUser
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.operational_models import OperationalShipment, OperationalMembership
from backend.services import route_time_service as svc
from scripts.uat.canonical_geography_fixture import ensure_canonical_geography
from scripts.uat.seed_phase3_branched_route_e2e import main as seed_route


def main():
    seed_route()
    path=Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture=json.loads(path.read_text(encoding="utf-8"))
    app=create_app(skip_startup=True)
    with app.app_context():
        ensure_canonical_geography()
        old=OperationalShipment.query.filter_by(public_id=fixture["p3_route_shipment"]).one()
        admin=ExpertUser.query.filter_by(username="shared_transport_e2e_admin").one()
        foreign=ExpertUser.query.filter_by(username="shared_transport_e2e_foreign").one()
        foreign.authority="ORGANIZATION_ADMIN";foreign.role="admin"
        foreign_org=OperationalMembership.query.filter_by(user_id=foreign.id).one().organization_id
        cities=(City.query.join(Country).filter(
            Country.code=="IR",City.dataset_id==GEONAMES_DATASET_ID,City.is_active.is_(True)
        ).order_by(City.geoname_id).limit(2).all())
        if len(cities)!=2 or any(city.province is None for city in cities):
            raise RuntimeError("P3-10 requires two qualified canonical cities")
        geography={code:{"country_id":city.country_id,"admin1_geoname_id":city.province.geoname_id,"city_geoname_id":city.geoname_id}
            for code,city in zip(("origin","destination"),cities)}
        kind=LogisticsPointType(immutable_code="P310_SYNTHETIC",fa_name="نقطه آزمایشی",en_name="Synthetic point",is_active=True,created_by=admin.id,updated_by=admin.id)
        db.session.add(kind);db.session.flush()
        points={}
        for org,actor,prefix in ((old.organization_id,admin.id,"own"),(foreign_org,foreign.id,"foreign")):
            for code,city in zip(("origin","destination"),cities):
                label=f"نقطه آزمون {city.name_fa}"
                row=LogisticsPoint(organization_id=org,immutable_code=f"P310-{code}",logistics_point_type_id=kind.id,
                    fa_name=label,normalized_name=f"p310 {prefix} {code}",country_id=city.country_id,province_id=city.province_id,
                    city_id=city.id,geography_key=f"city:{city.geoname_id}",governance_state="APPROVED",is_active=True,created_by=actor,updated_by=actor)
                db.session.add(row);db.session.flush();points[f"{prefix}_{code}"]=row.public_id
        new=OperationalShipment(organization_id=old.organization_id,source_type="direct",customer_id=old.customer_id,
            lifecycle_status="planned",created_by_user_id=old.primary_responsible_expert_id,primary_responsible_expert_id=old.primary_responsible_expert_id)
        db.session.add(new);db.session.commit()
        foreign_version,_=svc.save({"id":foreign.id}, {"origin":{"country_id":cities[0].country_id,"source_type":"logistics_point","source_id":points["foreign_origin"]},
            "destination":{"country_id":cities[1].country_id,"source_type":"logistics_point","source_id":points["foreign_destination"]},"transport_mode":"rail",
            "movement_min_minutes":600,"movement_max_minutes":900,"effective_from":(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()},str(uuid4()))
        db.session.commit()
        from backend.route_time_models import OrganizationRouteTime
        fixture.update(p310_old_shipment=old.public_id,p310_new_shipment=new.public_id,p310_points=points,p310_geography=geography,
            p310_foreign_reference=db.session.get(OrganizationRouteTime,foreign_version.reference_id).public_id)
        path.write_text(json.dumps(fixture),encoding="utf-8")


if __name__=="__main__":main()
