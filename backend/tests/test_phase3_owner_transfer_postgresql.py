"""Real restricted LOGIN proof for ADR-069; supplied identity is structural only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from uuid import uuid4
import os
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from alembic import command
from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership as Membership, OperationalShipment as Shipment
from backend.services import owner_transfer_service as svc
from backend.tests.test_phase3_transport_execution_postgresql import _seed_runtime

URL=os.environ.get("P3_OWNER_TRANSFER_POSTGRES_URL","")
HEAD="20261011_phase3_owner_transfer"
PREVIOUS="20261010_phase3_closure"
pytestmark=pytest.mark.skipif(not URL,reason="requires explicit owned P3_OWNER_TRANSFER_POSTGRES_URL")
CALL=sa.text("SELECT * FROM public.transfer_shipment_owner(:org,:shipment,:actor,:target,:owner,:version,:reason,:key,:previous,CAST(:census AS jsonb))")


def denied(engine,statement,params=None,code=None):
    with pytest.raises(sa.exc.DBAPIError) as caught:
        with engine.begin() as connection:
            connection.execute(sa.text(statement) if isinstance(statement,str) else statement,params or {})
    if code:
        assert getattr(caught.value.orig,"pgcode",getattr(caught.value.orig,"sqlstate",None))==code
    return str(getattr(getattr(caught.value.orig,"diag",None),"message_primary",""))


def wait_blocked(engine,pid,ready):
    assert ready.wait(5)
    until=monotonic()+8
    while monotonic()<until:
        with engine.connect() as connection:
            if connection.execute(sa.text("SELECT cardinality(pg_blocking_pids(:pid))>0"),{"pid":pid[0]}).scalar(): return
        sleep(.03)
    raise AssertionError("No genuine PostgreSQL lock waiter observed")


def test_pg18_restricted_role_receipt_atomicity_concurrency_and_current_authority():
    url=make_url(URL)
    assert url.get_backend_name()=="postgresql" and url.host in {"localhost","127.0.0.1"}
    assert url.database.startswith("forwarder_integrated_cert_p3_13_owner_")
    root=sa.create_engine(URL)
    with root.connect() as connection:
        assert 180000<=int(connection.execute(sa.text("SHOW server_version_num")).scalar())<190000
    config=alembic_config(URL)
    command.upgrade(config,PREVIOUS)
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":URL,"SECRET_KEY":"p313-owned-pg"}, skip_startup=True)
    with app.app_context():
        ids=_seed_runtime(app)
        shipment=Shipment.query.filter_by(public_id=ids["shipment"]).one()
        ids.update(org=shipment.organization_id,shipment_id=shipment.id)
        for name,authority in (("admin","ORGANIZATION_ADMIN"),("admin2","ORGANIZATION_ADMIN"),("target","EXPERT"),("third","EXPERT")):
            actor=ExpertUser(username="p313-"+name,password_hash="unused",full_name="Synthetic "+name,
                authority=authority,role="admin" if authority=="ORGANIZATION_ADMIN" else "expert",is_active=True)
            db.session.add(actor);db.session.flush()
            db.session.add(Membership(user_id=actor.id,organization_id=ids["org"],permissions=["operational_shipment.read","operational_shipment.create"]))
            ids[name]=actor.id
        db.session.commit()
    def state():
        with root.connect() as connection:
            return tuple(connection.execute(sa.text("SELECT primary_responsible_expert_id,version,lifecycle_status FROM public.operational_shipment WHERE id=:id"),{"id":ids["shipment_id"]}).one())
    before=state()
    command.upgrade(config,HEAD)
    assert state()==before
    command.downgrade(config,PREVIOUS)
    assert state()==before
    denied(root,"UPDATE public.operational_shipment SET primary_responsible_expert_id=:target WHERE id=:id",{"target":ids["target"],"id":ids["shipment_id"]},"23514")
    command.upgrade(config,HEAD)
    suffix=uuid4().hex[:10]
    role="p313_runtime_"+suffix;public_role="p313_public_"+suffix
    with root.begin() as connection:
        for name in (role,public_role):
            connection.execute(sa.text(f"CREATE ROLE {name} LOGIN INHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"))
            connection.execute(sa.text(f"GRANT USAGE ON SCHEMA public TO {name}"))
        connection.execute(sa.text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}"))
        connection.execute(sa.text(f"GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}"))
        connection.execute(sa.text(f"GRANT forwarder_owner_transfer_caller TO {role}"))
    runtime_url=url.set(username=role,password=None)
    runtime=sa.create_engine(runtime_url)
    public=sa.create_engine(url.set(username=public_role,password=None))
    with runtime.connect() as connection:
        assert connection.execute(sa.text("SELECT current_user=session_user AND NOT (SELECT rolsuper FROM pg_roles WHERE rolname=current_user)")).scalar()
    params={"org":ids["org"],"shipment":ids["shipment_id"],"actor":ids["admin"],"target":ids["target"],
        "owner":ids["owner"],"version":before[1],"reason":"Synthetic administrative transfer","key":str(uuid4()),"previous":None,
        "census":'{"census_id":"legacy-mt1c","cache_version":0,"cache_token":0}'}
    # Claims A/C: real restricted caller cannot alter owner/roles/trigger state.
    denied(runtime,"UPDATE public.operational_shipment SET primary_responsible_expert_id=:target WHERE id=:shipment",params,"23514")
    denied(runtime,"SET ROLE forwarder_owner_transfer_owner",code="42501")
    denied(runtime,"ALTER TABLE public.operational_shipment DISABLE TRIGGER USER",code="42501")
    denied(runtime,"SET session_replication_role='replica'",code="42501")
    denied(public,CALL,params,"42501")
    invalid=[("actor",ids["outsider"],"ACTOR_INVALID"),("actor",ids["owner"],"ACTOR_INVALID"),
        ("target",ids["outsider"],"TARGET_INVALID"),("target",ids["admin"],"TARGET_INVALID"),
        ("owner",ids["third"],"STALE"),("version",before[1]+9,"STALE"),("previous",999999,"CHAIN_INVALID"),
        ("org",999999,"TENANT_INVALID")]
    for field,value,reason in invalid:
        assert denied(runtime,CALL,{**params,field:value},"P0001")=="OWNER_TRANSFER_"+reason
    with root.begin() as connection:
        connection.execute(sa.text("UPDATE public.expert_user SET authority='ORGANIZATION_ADMIN' WHERE id=:id"),{"id":ids["outsider"]})
    assert denied(runtime,CALL,{**params,"actor":ids["outsider"]},"P0001")=="OWNER_TRANSFER_ACTOR_INVALID"
    with root.begin() as connection:
        connection.execute(sa.text("UPDATE public.expert_user SET authority='EXPERT' WHERE id=:id"),{"id":ids["outsider"]})
        connection.execute(sa.text("UPDATE public.expert_user SET is_active=false WHERE id=:id"),{"id":ids["admin"]})
    assert denied(runtime,CALL,params,"P0001")=="OWNER_TRANSFER_ACTOR_INVALID"
    with root.begin() as connection:
        connection.execute(sa.text("UPDATE public.expert_user SET is_active=true WHERE id=:id"),{"id":ids["admin"]})
    # A caller-controlled temporary object/search path cannot supply authority.
    with runtime.connect() as connection:
        connection.execute(sa.text("CREATE TEMP TABLE expert_user (id bigint, authority text, is_active boolean)"))
        connection.execute(sa.text("INSERT INTO pg_temp.expert_user VALUES (:id,'ORGANIZATION_ADMIN',true)"), {"id":ids["owner"]})
        connection.execute(sa.text("SET LOCAL search_path=pg_temp,public"))
        with pytest.raises(sa.exc.DBAPIError) as spoofed:
            connection.execute(CALL,{**params,"actor":ids["owner"]})
        assert spoofed.value.orig.diag.message_primary=="OWNER_TRANSFER_ACTOR_INVALID"
        connection.rollback()
    # Revocation commits while the routine is waiting. Its later read must
    # observe the revoked actor/target, including target membership activity.
    revocations=[
        ("UPDATE public.expert_user SET is_active=false WHERE id=:id", "UPDATE public.expert_user SET is_active=true WHERE id=:id", ids["target"], "TARGET_INVALID"),
        ("UPDATE public.expert_user SET authority='PLATFORM_ADMIN' WHERE id=:id", "UPDATE public.expert_user SET authority='ORGANIZATION_ADMIN' WHERE id=:id", ids["admin"], "ACTOR_INVALID"),
        ("UPDATE public.operational_membership SET is_active=false WHERE user_id=:id", "UPDATE public.operational_membership SET is_active=true WHERE user_id=:id", ids["target"], "TARGET_INVALID"),
    ]
    for change,restore,identity,expected in revocations:
        with root.connect() as revoker:
            transaction=revoker.begin();revoker.execute(sa.text(change),{"id":identity})
            ready=Event();pid=[]
            def revoked_attempt():
                with runtime.connect() as connection:
                    pid.append(connection.execute(sa.text("SELECT pg_backend_pid()")).scalar());ready.set()
                    try:
                        connection.execute(CALL,params);connection.commit();return "unexpected success"
                    except sa.exc.DBAPIError as exc:
                        connection.rollback();return exc.orig.diag.message_primary
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(revoked_attempt)
                try: wait_blocked(root,pid,ready)
                finally: transaction.commit()
                assert future.result(timeout=10)=="OWNER_TRANSFER_"+expected
        with root.begin() as connection: connection.execute(sa.text(restore),{"id":identity})
        assert state()==before
    # Fail after history/owner/audit writes, before outbox completes: transaction
    # must leave neither owner change nor any transfer/audit residue.
    with root.begin() as connection:
        connection.execute(sa.text("REVOKE USAGE ON SEQUENCE public.operational_outbox_id_seq FROM forwarder_owner_transfer_owner"))
    denied(runtime,CALL,params,"42501")
    assert state()==before
    with root.begin() as connection:
        assert connection.execute(sa.text("SELECT count(*) FROM public.shipment_owner_transfer")).scalar()==0
        assert connection.execute(sa.text("SELECT count(*) FROM public.operational_audit WHERE action='shipment.owner_transferred'")).scalar()==0
        connection.execute(sa.text("GRANT USAGE ON SEQUENCE public.operational_outbox_id_seq TO forwarder_owner_transfer_owner"))
    # One winner; a real second transaction blocks, then sees the changed version.
    with runtime.connect() as first:
        transaction=first.begin();receipt=first.execute(CALL,params).one()
        ready=Event();pid=[]
        def compete():
            with runtime.connect() as second:
                pid.append(second.execute(sa.text("SELECT pg_backend_pid()")).scalar());ready.set()
                try:
                    second.execute(CALL,{**params,"actor":ids["admin2"],"target":ids["third"],"key":str(uuid4())});second.commit()
                    return "unexpected success"
                except sa.exc.DBAPIError as exc:
                    second.rollback();return exc.orig.diag.message_primary
        replay_ready=Event();replay_pid=[]
        def duplicate():
            with runtime.begin() as connection:
                replay_pid.append(connection.execute(sa.text("SELECT pg_backend_pid()")).scalar());replay_ready.set()
                return tuple(connection.execute(CALL,params).one())
        with ThreadPoolExecutor(max_workers=2) as pool:
            future=pool.submit(compete)
            replay_future=pool.submit(duplicate)
            try:
                wait_blocked(root,pid,ready);wait_blocked(root,replay_pid,replay_ready)
            finally: transaction.commit()
            assert future.result(timeout=10)=="OWNER_TRANSFER_STALE"
            assert replay_future.result(timeout=10)==(receipt.transfer_id,False)
    assert state()==(ids["target"],before[1]+1,before[2])
    with runtime.begin() as connection:
        replay=connection.execute(CALL,params).one()
        assert not replay.created and replay.transfer_id==receipt.transfer_id
    assert denied(runtime,CALL,{**params,"reason":"different"},"P0001")=="OWNER_TRANSFER_KEY_CONFLICT"
    # Claim B: broad ordinary DML is still unable to fabricate or rewrite history.
    columns="public_id,organization_id,operational_shipment_id,old_owner_id,new_owner_id,actor_user_id,old_owner_label,new_owner_label,actor_label,reason,occurred_at,recorded_at,sequence_number,previous_shipment_version,next_shipment_version,previous_transfer_id,idempotency_key"
    denied(runtime,f"INSERT INTO public.shipment_owner_transfer ({columns}) SELECT {columns} FROM public.shipment_owner_transfer LIMIT 1",code="23514")
    denied(runtime,"UPDATE public.shipment_owner_transfer SET reason='rewrite'",code="23514")
    denied(runtime,"DELETE FROM public.shipment_owner_transfer",code="23514")
    denied(runtime,"TRUNCATE public.shipment_owner_transfer",code="42501")
    with root.connect() as connection:
        assert connection.execute(sa.text("SELECT count(*) FROM public.shipment_owner_transfer")).scalar()==1
        assert connection.execute(sa.text("SELECT count(*) FROM public.operational_outbox WHERE event_type='shipment.owner_transferred'")).scalar()==1
    # The real app connection is restricted too; no TESTING exception for PG.
    restricted=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":runtime_url.render_as_string(hide_password=False),"SECRET_KEY":"p313-owned-restricted"}, skip_startup=True)
    with app.app_context(): assert not svc.database_ready()
    with restricted.app_context():
        assert svc.database_ready()
        view=svc.read(ids["shipment"],{"id":ids["admin"]})
        assert view["current_owner"]["id"]==ids["target"] and len(view["transfers"])==1
        result,created=svc.transfer(ids["shipment"],{"id":ids["admin"]},
            {"expected_owner_id":ids["target"],"target_owner_id":ids["owner"],"expected_version":before[1]+1,"reason":"Explicit return transfer"},str(uuid4()))
        # A former-owner mutation already carrying an identity-map object
        # waits on the transfer and rechecks current authority before writing.
        waiters=[(kind,Event(),[]) for kind in ("document","milestone","checkpoint")]
        def former_owner_mutation(kind,ready,pid):
            from backend.services.assigned_work_authorization import authorize_document_management
            from backend.services import operational_service as base, route_orchestration_service as routes
            with restricted.app_context():
                current=db.session.get(Shipment,ids["shipment_id"])
                assert authorize_document_management({"id":ids["target"]},current).allowed
                pid.append(db.session.execute(sa.text("SELECT pg_backend_pid()")).scalar());ready.set()
                try:
                    if kind=="document":
                        allowed=authorize_document_management({"id":ids["target"]},current,for_update=True).allowed
                    elif kind=="milestone":
                        base.scoped_shipment(ids["shipment"],{"id":ids["target"]},for_update=True);allowed=True
                    else:
                        routes._shipment(ids["shipment"],{"id":ids["target"]},"operational_shipment.read",for_update=True);allowed=True
                except base.OperationalError as exc:
                    assert exc.status==404;allowed=False
                db.session.rollback();db.session.remove();return allowed
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures=[pool.submit(former_owner_mutation,*waiter) for waiter in waiters]
            try:
                for _,ready,pid in waiters: wait_blocked(root,pid,ready)
            finally: db.session.commit()
            assert all(future.result(timeout=10) is False for future in futures)
        assert created and result.sequence_number==2 and result.previous_transfer_id==receipt.transfer_id
        current=db.session.get(Shipment,ids["shipment_id"])
        assert current.primary_responsible_expert_id==ids["owner"]
        current.primary_responsible_expert_id=ids["target"]
        with pytest.raises(ValueError,match="immutable"): db.session.flush()
        db.session.rollback()
        db.session.remove()
    with runtime.begin() as connection:
        replay=connection.execute(CALL,params).one()
        assert not replay.created and replay.transfer_id==receipt.transfer_id
    with pytest.raises(RuntimeError,match="history exists"):
        command.downgrade(config,PREVIOUS)
    assert state()==(ids["owner"],before[1]+2,before[2])
    with root.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar()==HEAD
        previous_id=connection.execute(sa.text("SELECT id FROM shipment_owner_transfer ORDER BY sequence_number DESC LIMIT 1")).scalar()
    # Reverse order: a parent mutation already owning the row serializes first.
    # Roll back this final synthetic transfer so the retained chain stays at 2.
    with runtime.connect() as writer:
        transaction=writer.begin()
        writer.execute(sa.text("SELECT id FROM public.operational_shipment WHERE id=:id FOR UPDATE"),{"id":ids["shipment_id"]})
        ready=Event();pid=[]
        def after_mutation():
            with runtime.connect() as connection:
                pid.append(connection.execute(sa.text("SELECT pg_backend_pid()")).scalar());ready.set()
                result=connection.execute(CALL,{**params,"version":before[1]+2,"previous":previous_id,"key":str(uuid4())}).one()
                connection.rollback();return result.created
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(after_mutation)
            try: wait_blocked(root,pid,ready)
            finally: transaction.commit()
            assert future.result(timeout=10)
    assert state()==(ids["owner"],before[1]+2,before[2])
    with app.app_context(): db.session.remove();db.engine.dispose()
    with restricted.app_context(): db.engine.dispose()
    runtime.dispose();public.dispose();root.dispose()
