"""Owned PostgreSQL 18: upgrade preservation, immutable pins and concurrency."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4
from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import Customer, ExpertUser, Province
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment, RouteLeg, RoutePlan
from backend.route_time_models import OrganizationRouteTime as Reference, OrganizationRouteTimeVersion as Version, RouteLegTimeBasis as Basis
from backend.services import operational_service as base, route_time_service as svc

URL=os.environ.get("P3_ROUTE_TIME_POSTGRES_URL", "")
PREVIOUS="20261008_phase3_cargo_delivery"
HEAD="20261009_phase3_route_time"
pytestmark=pytest.mark.skipif(not URL,reason="requires explicit P3_ROUTE_TIME_POSTGRES_URL")


def test_postgresql18_route_time_upgrade_history_tenant_concurrency_and_safe_rollback():
    parsed=make_url(URL)
    assert parsed.drivername.startswith("postgresql") and parsed.host in {"127.0.0.1","localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_cert_p3_10_route_time_")
    engine=sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) < 190000
    config=alembic_config(URL)
    command.upgrade(config,PREVIOUS)
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":URL,"SECRET_KEY":"p310-owned-pg"},skip_startup=True)
    now=datetime.now(timezone.utc)
    with app.app_context():
        org=OperationalOrganization(name="P310 synthetic A"); foreign=OperationalOrganization(name="P310 synthetic B")
        admin=ExpertUser(username="p310-admin",password_hash="unused",full_name="P310 Admin",role="admin",authority="ORGANIZATION_ADMIN",is_active=True)
        expert=ExpertUser(username="p310-expert",password_hash="unused",full_name="P310 Expert",role="expert",authority="EXPERT",is_active=True)
        origin=Province(code="P310-O",name_fa="خورگوس آزمایشی",is_active=True); destination=Province(code="P310-D",name_fa="آکتائو آزمایشی",is_active=True)
        db.session.add_all([org,foreign,admin,expert,origin,destination]);db.session.flush()
        customer=Customer(company_name="P310 Customer",ownership_scope="TENANT",operational_organization_id=org.id,status="active")
        db.session.add(customer);db.session.flush()
        for user in (admin,expert):db.session.add(OperationalMembership(organization_id=org.id,user_id=user.id,permissions=["operational_shipment.read","route_leg.manage"]))
        shipment=OperationalShipment(organization_id=org.id,source_type="direct",customer_id=customer.id,lifecycle_status="planned",created_by_user_id=expert.id,primary_responsible_expert_id=expert.id)
        db.session.add(shipment);db.session.flush()
        plan=RoutePlan(operational_shipment_id=shipment.id,revision_number=1,status="draft",is_active=False,created_by_user_id=expert.id)
        db.session.add(plan);db.session.flush()
        a=base.resolve_location({"source_type":"province","source_id":origin.id}); b=base.resolve_location({"source_type":"province","source_id":destination.id})
        leg=RouteLeg(route_plan_id=plan.id,sequence_number=1,origin_location_id=a.canonical_location.id,destination_location_id=b.canonical_location.id,
            origin_snapshot=a.snapshot(),destination_snapshot=b.snapshot(),transport_mode="rail",planned_departure=now+timedelta(days=10),planned_arrival=now+timedelta(days=12),status="planned")
        db.session.add(leg);db.session.commit()
        ids={"org":org.id,"foreign":foreign.id,"admin":admin.id,"expert":expert.id,"shipment":shipment.public_id,"shipment_id":shipment.id,"plan":plan.id,"leg":leg.id}
        body={"origin":{"source_type":"province","source_id":origin.id},"destination":{"source_type":"province","source_id":destination.id},"transport_mode":"rail",
            "movement_min_minutes":1200,"movement_max_minutes":1440,"stop_min_minutes":240,"stop_max_minutes":480,"effective_from":(now-timedelta(days=1)).isoformat()}
    def legacy():
        with engine.connect() as c:return c.execute(sa.text("SELECT id,route_plan_id,origin_snapshot::text,destination_snapshot::text,planned_departure,planned_arrival,status,version FROM route_leg ORDER BY id")).all()
    before=legacy()
    command.upgrade(config,HEAD)
    assert legacy()==before
    with engine.connect() as c:
        for table in ("organization_route_time","organization_route_time_version","route_leg_time_basis"):
            assert c.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one()==0
    command.downgrade(config,PREVIOUS)
    assert legacy()==before
    command.upgrade(config,HEAD)
    admin_user={"id":ids["admin"],"role":"admin"}; expert_user={"id":ids["expert"],"role":"expert"}
    with app.app_context():
        first,_=svc.save(admin_user,body,str(uuid4()));db.session.commit()
        reference=db.session.get(Reference,first.reference_id)
        reference_id=reference.public_id; first_id=first.id; reference_db_id=reference.id
        select_payload={"expected_version":1,"expected_selection_revision":0,"reference_version_public_id":first.public_id}
        selection,_=svc.select_basis(ids["shipment"],ids["plan"],ids["leg"],expert_user,select_payload,str(uuid4()));db.session.commit()
        selection_id=selection.id
        second_values={key:value for key,value in body.items() if key in svc.VALUES}
        second_values.update(expected_version=1,effective_from=(now+timedelta(days=1)).isoformat(),movement_min_minutes=1500,movement_max_minutes=1800)
        second,_=svc.save(admin_user,second_values,str(uuid4()),reference_id);db.session.commit()
        current=svc.plan_read(ids["shipment"],ids["plan"],expert_user)["items"][0]
        assert current["selected"]["reference"]["version"]==1 and current["applicable"]["version"]==2
        assert db.session.get(Basis,selection_id).reference_version_id==first_id
        second_id=second.id
    assert legacy()==before
    # Raw SQL cannot rewrite/delete historical rows or cross tenant/key boundaries.
    for statement in (
        "UPDATE organization_route_time_version SET movement_min_minutes=1",
        "DELETE FROM route_leg_time_basis",
        "UPDATE organization_route_time SET transport_mode='road'",
    ):
        with pytest.raises(sa.exc.DBAPIError),engine.begin() as connection:connection.execute(sa.text(statement))
    with pytest.raises(sa.exc.DBAPIError),engine.begin() as connection:
        connection.execute(sa.text("""INSERT INTO organization_route_time_version(public_id,organization_id,reference_id,version,movement_min_minutes,movement_max_minutes,effective_from,actor_user_id,recorded_at)
            VALUES(:public,:foreign,:reference,3,20,30,:effective,:actor,now())"""),{"public":str(uuid4()),"foreign":ids["foreign"],"reference":reference_db_id,"effective":now+timedelta(days=2),"actor":ids["admin"]})
    with pytest.raises(sa.exc.DBAPIError),engine.begin() as connection:
        connection.execute(sa.text("""INSERT INTO route_leg_time_basis(public_id,organization_id,operational_shipment_id,route_plan_id,route_leg_id,reference_version_id,selection_revision,leg_basis,reference_at,actor_user_id,recorded_at)
            VALUES(:public,:foreign,:shipment,:plan,:leg,:version,2,'{}',:at,:actor,now())"""),{"public":str(uuid4()),"foreign":ids["foreign"],"shipment":ids["shipment_id"],"plan":ids["plan"],"leg":ids["leg"],"version":second_id,"at":now+timedelta(days=10),"actor":ids["expert"]})
    # Same key converges; separate commands with the same expected version compete.
    common={**second_values,"expected_version":2,"effective_from":(now+timedelta(days=2)).isoformat()}
    replay_key=str(uuid4())
    def write_version(values,key):
        with app.app_context():
            try:
                row,created=svc.save(admin_user,values,key,reference_id);db.session.commit()
                return ("OK",row.id,created)
            except base.OperationalError as exc:
                db.session.rollback();return (exc.code,None,False)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:write_version(common,replay_key),range(2)))
    assert results[0][1]==results[1][1] and sorted(x[2] for x in results)==[False,True]
    competing={**common,"expected_version":3,"effective_from":(now+timedelta(days=3)).isoformat()}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:write_version(competing,str(uuid4())),range(2)))
    assert sorted(x[0] for x in results)==["OK","STALE_ROUTE_TIME"]
    with app.app_context():
        assert Version.query.count()==4 and Basis.query.count()==1
        assert svc.plan_read(ids["shipment"],ids["plan"],expert_user)["items"][0]["selected"]["reference"]["version"]==1
    with pytest.raises(RuntimeError,match="history exists"):
        command.downgrade(config,PREVIOUS)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()==HEAD
    assert legacy()==before
    engine.dispose()
