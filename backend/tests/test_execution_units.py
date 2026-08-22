from datetime import timedelta
import os
from pathlib import Path
import time
import pytest
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
import sqlalchemy as sa

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import Customer, ExpertUser
from backend.operational_models import ExecutionUnit, OperationalEvent, OperationalMembership, OperationalOrganization, Project, utcnow


@pytest.fixture()
def eu_app():
    database_url = os.environ.get(
        "FORWARDER_RELEASE_120_POSTGRES_URL", "sqlite:///:memory:"
    )
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":database_url,"SECRET_KEY":"eu-test"})
    with app.app_context():
        db.create_all()
        org=OperationalOrganization(name="Org"); other=OperationalOrganization(name="Other")
        user=ExpertUser(username="eu-user",password_hash="x",full_name="EU",role="manager",is_active=True)
        outsider=ExpertUser(username="eu-other",password_hash="x",full_name="Other",role="manager",is_active=True)
        customer=Customer(first_name="C",last_name="One")
        db.session.add_all([org,other,user,outsider,customer]); db.session.flush()
        perms=["execution_unit.read","execution_unit.create","execution_unit.update"]
        db.session.add_all([OperationalMembership(organization_id=org.id,user_id=user.id,permissions=perms),OperationalMembership(organization_id=other.id,user_id=outsider.id,permissions=perms)])
        project=Project(organization_id=org.id,primary_customer_id=customer.id,project_code="PRJ-1",tracking_code="opaque-project-code",created_by_user_id=user.id)
        db.session.add(project); db.session.commit()
        yield app,{"project":project.public_id,"tracking":project.tracking_code,"auth":{"Authorization":f"Bearer {auth_manager.generate_tokens(user.id)['access_token']}"},"other_auth":{"Authorization":f"Bearer {auth_manager.generate_tokens(outsider.id)['access_token']}"}}
        db.session.remove(); db.drop_all()


def _create(client,ctx,name="Truck"):
    response=client.post(f"/api/v2/projects/{ctx['project']}/execution-units",headers=ctx["auth"],json={"unit_type":"road","display_name":name})
    assert response.status_code==201
    return response.get_json()["data"]


def test_create_generated_code_list_detail_filters_and_no_timeline_eager_load(eu_app):
    app,ctx=eu_app
    with app.test_client() as client:
        first=_create(client,ctx); second=_create(client,ctx,"Container")
        assert first["unit_code"]=="U-0001" and second["unit_code"]=="U-0002"
        listed=client.get(f"/api/v2/projects/{ctx['project']}/execution-units?search=Container&per_page=25",headers=ctx["auth"]).get_json()
        assert listed["meta"]["total"]==1 and "timeline" not in listed["data"][0]
        detail=client.get(f"/api/v2/projects/{ctx['project']}/execution-units/{second['public_id']}",headers=ctx["auth"])
        assert detail.status_code==200 and "id" not in detail.get_json()["data"]


def test_event_idempotency_concurrency_and_customer_projection(eu_app):
    app,ctx=eu_app
    with app.test_client() as client:
        unit=_create(client,ctx); url=f"/api/v2/projects/{ctx['project']}/execution-units/{unit['public_id']}/events"
        payload={"expected_version":1,"lifecycle_status":"in_progress","checkpoint_text":"Border gate","visibility":"customer","customer_message":"Departed hub","internal_note":"private","delayed":True}
        headers={**ctx["auth"],"Idempotency-Key":"event-1"}
        first=client.post(url,headers=headers,json=payload); replay=client.post(url,headers=headers,json=payload)
        assert first.status_code==201 and replay.status_code==200
        conflict=client.post(url,headers=headers,json={**payload,"customer_message":"changed"})
        assert conflict.status_code==409 and conflict.get_json()["error"]["code"]=="IDEMPOTENCY_CONFLICT"
        stale=client.post(url,headers={**ctx["auth"],"Idempotency-Key":"event-2"},json=payload)
        assert stale.status_code==409 and stale.get_json()["error"]["code"]=="VERSION_CONFLICT"
        assert client.patch(url,headers=ctx["auth"],json={}).status_code==405
        assert client.delete(url,headers=ctx["auth"]).status_code==405
        public=client.get(f"/api/public/v2/projects/{ctx['tracking']}/execution-units/{unit['public_id']}/timeline").get_json()
        assert public["meta"]["total"]==1
        body=str(public); assert "private" not in body and "actor_user" not in body and '"id"' not in body


def test_internal_event_never_leaks_and_cross_org_is_404_safe(eu_app):
    app,ctx=eu_app
    with app.test_client() as client:
        unit=_create(client,ctx)
        client.post(f"/api/v2/projects/{ctx['project']}/execution-units/{unit['public_id']}/events",headers={**ctx["auth"],"Idempotency-Key":"internal"},json={"expected_version":1,"visibility":"internal","internal_note":"secret"})
        assert client.get(f"/api/public/v2/projects/{ctx['tracking']}/execution-units/{unit['public_id']}/timeline").get_json()["meta"]["total"]==0
        assert client.get(f"/api/v2/projects/{ctx['project']}/execution-units",headers=ctx["other_auth"]).status_code==404
        assert client.get(f"/api/public/v2/projects/123/execution-units").status_code==404


def test_summary_alerts_stale_policy_and_500_unit_10000_event_bounded_queries(eu_app):
    app,ctx=eu_app
    with app.app_context():
        project=Project.query.filter_by(public_id=ctx["project"]).one(); actor=ExpertUser.query.filter_by(username="eu-user").one()
        now=utcnow(); units=[]; events=[]
        for i in range(500):
            unit=ExecutionUnit(project_id=project.id,unit_code=f"U-{i+1:04d}",unit_type="road",lifecycle_status="in_progress",last_event_at=now-timedelta(hours=25 if i<10 else 1),delayed=i<5,attention_required=i<3,created_by_user_id=actor.id)
            units.append(unit)
        db.session.add_all(units); db.session.flush()
        for unit in units:
            for j in range(20): events.append(OperationalEvent(project_id=project.id,execution_unit_id=unit.id,event_type="checkpoint",visibility="internal",occurred_at=now-timedelta(minutes=j),actor_user_id=actor.id,idempotency_key=f"{unit.id}-{j}",request_hash="x"*64))
        db.session.add_all(events); db.session.commit()
        first_unit_public_id=units[0].public_id; first_unit_id=units[0].id; project_id=project.id
    queries=[]
    from sqlalchemy import event
    with app.app_context(): event.listen(db.engine,"before_cursor_execute",lambda *args:queries.append(1))
    started=time.perf_counter()
    with app.test_client() as client:
        list_response=client.get(f"/api/v2/projects/{ctx['project']}/execution-units?per_page=25&stale=true",headers=ctx["auth"])
        result=list_response.get_json()
        elapsed=time.perf_counter()-started
        print(f"500-unit list (10 stale of 10,000 events): {elapsed*1000:.2f} ms, {len(queries)} SQL statements, {len(list_response.data)} bytes")
        assert result["meta"]["total"]==10 and len(result["data"])==10 and len(queries)<=12
        queries.clear(); timeline_started=time.perf_counter()
        timeline_response=client.get(f"/api/v2/projects/{ctx['project']}/execution-units/{first_unit_public_id}/timeline?per_page=25",headers=ctx["auth"])
        timeline_elapsed=time.perf_counter()-timeline_started
        print(f"20-event timeline: {timeline_elapsed*1000:.2f} ms, {len(queries)} SQL statements, {len(timeline_response.data)} bytes")
        assert timeline_response.status_code==200 and timeline_response.get_json()["meta"]["total"]==20
        summary=client.get(f"/api/public/v2/projects/{ctx['tracking']}/summary").get_json()["data"]
        assert summary["total_units"]==500 and summary["units_without_recent_update"]==10 and summary["threshold_policy"]["stale_after_hours"]==24
        assert elapsed < 5
    if db.engine.dialect.name == "postgresql":
        with app.app_context():
            list_plan=db.session.execute(sa.text("EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM execution_unit WHERE project_id=:project_id AND is_active IS TRUE AND last_event_at < :cutoff ORDER BY updated_at DESC LIMIT 25"),{"project_id":project_id,"cutoff":now-timedelta(hours=24)}).scalars().all()
            timeline_plan=db.session.execute(sa.text("EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM operational_event WHERE execution_unit_id=:unit_id ORDER BY occurred_at DESC,id DESC LIMIT 25"),{"unit_id":first_unit_id}).scalars().all()
            print("Unit-list query plan: " + " | ".join(list_plan))
            print("Timeline query plan: " + " | ".join(timeline_plan))


def test_execution_unit_migration_is_single_head():
    root=Path(__file__).resolve().parents[1]; config=Config(str(root/"migrations"/"alembic.ini")); config.set_main_option("script_location",str(root/"migrations"))
    assert ScriptDirectory.from_config(config).get_heads()==["20260905_global_logistics_point_adoption"]


def test_execution_unit_migration_parent_round_trip_and_indexes(tmp_path):
    path=tmp_path/"execution-unit-roundtrip.db"; url=f"sqlite:///{path.as_posix()}"; engine=sa.create_engine(url); metadata=sa.MetaData(); bigint=sa.BigInteger().with_variant(sa.Integer(),"sqlite")
    sa.Table("expert_user",metadata,sa.Column("id",bigint,primary_key=True))
    sa.Table("shipment_transport_unit",metadata,sa.Column("id",bigint,primary_key=True))
    sa.Table("operational_shipment",metadata,sa.Column("id",bigint,primary_key=True))
    sa.Table("project",metadata,sa.Column("id",bigint,primary_key=True),sa.Column("public_id",sa.String(36),nullable=False),sa.Column("organization_id",bigint,nullable=False),sa.Column("primary_customer_id",bigint,nullable=False),sa.Column("project_code",sa.String(64),nullable=False),sa.Column("lifecycle_status",sa.String(24),nullable=False),sa.Column("version",sa.Integer,nullable=False),sa.Column("created_by_user_id",bigint,nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    metadata.create_all(engine)
    root=Path(__file__).resolve().parents[1]; config=Config(str(root/"migrations"/"alembic.ini")); config.set_main_option("script_location",str(root/"migrations")); config.set_main_option("sqlalchemy.url",url)
    command.stamp(config,"20260805_project_foundation"); command.upgrade(config,"20260806_execution_units")
    inspector=sa.inspect(engine); assert {"execution_unit","operational_event"}<=set(inspector.get_table_names()); assert "tracking_code" in {c["name"] for c in inspector.get_columns("project")}; assert {"ix_execution_unit_project_status_active","ix_execution_unit_project_updated"}<={i["name"] for i in inspector.get_indexes("execution_unit")}
    command.downgrade(config,"20260805_project_foundation"); inspector=sa.inspect(engine); assert "execution_unit" not in inspector.get_table_names() and "tracking_code" not in {c["name"] for c in inspector.get_columns("project")}
    command.upgrade(config,"20260806_execution_units"); assert "operational_event" in sa.inspect(engine).get_table_names()
# ruff: noqa: E701, E702, F541
