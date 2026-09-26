"""Current human authorization, immutable transfer and independent assignments."""
from uuid import uuid4
import pytest
from sqlalchemy import select, text
from backend.extensions import db
from backend.models import ExpertUser, ExpertQuote, ShipmentRequest
from backend.operational_models import OperationalMembership as Membership, OperationalShipment as Shipment
from backend.operational_models import OperationalWorkItem as Work, OperationalAudit, OperationalOutbox, utcnow
from backend.owner_transfer_models import ShipmentOwnerTransfer as Transfer
from backend.services import owner_transfer_service as svc, operational_service as base
from backend.services.assigned_work_authorization import authorize_document_management, authorize_work_action
from backend.tests.test_operational_vertical_slice import operational_app, _user, _auth, _payload
from backend.tests.test_shipment_document_authorization import shipment_documents_app, PDF, _headers


def setup(app):
    shipment,_ = base.create_from_accepted_quote(_payload(app),_user(app),str(uuid4()))
    membership = db.session.scalar(select(Membership).where(Membership.user_id == app.config["phase1a"]["user"]))
    people=[]
    for name in ("target","third"):
        person=ExpertUser(username="p313-"+name,password_hash="unused",full_name="Synthetic "+name,
            authority="EXPERT",role="expert",is_active=True)
        db.session.add(person);db.session.flush()
        db.session.add(Membership(user_id=person.id,organization_id=shipment.organization_id,permissions=list(membership.permissions)))
        app.config["phase1a"][name]=person.id
        people.append(person)
    db.session.commit()
    return shipment,*people


def command(shipment,target,**changes):
    return {"expected_owner_id":shipment.primary_responsible_expert_id,"target_owner_id":target.id,
        "expected_version":shipment.version,"reason":"Explicit synthetic responsibility transfer",**changes}


def transfer(app,shipment,target,**changes):
    result=svc.transfer(shipment.public_id,_user(app,"verifier"),command(shipment,target,**changes),str(uuid4()))
    db.session.commit()
    return result


def test_transfer_receipt_current_authority_and_independent_work_and_request(operational_app):
    app=operational_app
    with app.app_context():
        shipment,target,third=setup(app)
        old=shipment.primary_responsible_expert_id
        request=db.session.get(ShipmentRequest,shipment.shipment_request_id)
        quote=db.session.get(ExpertQuote,shipment.accepted_quote_id)
        request_before=(request.assigned_to,quote.created_by_expert_id)
        work=[Work(organization_id=shipment.organization_id,operational_shipment_id=shipment.id,
            work_type="FOLLOW_UP",action_context_type="SHIPMENT",assignee_user_id=person,due_at=utcnow(),reason="Retained independent work") for person in (old,third.id)]
        db.session.add_all(work);db.session.commit()
        initial=svc.read(shipment.public_id,_user(app,"verifier"))
        assert initial["initial_owner"]["occurred_at"] is None and initial["transfers"]==[]
        assert initial["old_owner_open_work_count"]==1 and initial["capabilities"]=={"TRANSFER_OWNER":True}
        row,created=transfer(app,shipment,target)
        assert created and shipment.primary_responsible_expert_id==target.id and row.next_shipment_version==shipment.version
        assert [w.assignee_user_id for w in work]==[old,third.id] and all(w.status=="open" for w in work)
        assert (request.assigned_to,quote.created_by_expert_id)==request_before
        assert not authorize_work_action(_user(app),shipment,"shipment.read").allowed
        assert not authorize_document_management(_user(app),shipment).allowed
        assert authorize_document_management(_user(app,"target"),shipment).allowed
        assert not authorize_document_management(_user(app,"verifier"),shipment).allowed
        view=svc.read(shipment.public_id,_user(app,"target"))
        assert view["current_owner"]["id"]==target.id and view["initial_owner"]["id"]==old
        assert not view["capabilities"]["TRANSFER_OWNER"] and view["old_owner_open_work_count"] is None
        assert OperationalAudit.query.filter_by(action="shipment.owner_transferred").count()==1
        event=OperationalOutbox.query.filter_by(event_type="shipment.owner_transferred").one()
        assert "_ownership_census" in event.payload
        with pytest.raises(base.OperationalError) as denied: svc.read(shipment.public_id,_user(app))
        assert denied.value.status==404


def test_exact_replay_later_chain_and_immutable_actor_labels(operational_app):
    app=operational_app
    with app.app_context():
        shipment,target,_=setup(app)
        old=db.session.get(ExpertUser,shipment.primary_responsible_expert_id)
        payload=command(shipment,target);key=str(uuid4())
        first,created=svc.transfer(shipment.public_id,_user(app,"verifier"),payload,key);db.session.commit()
        assert created
        second,_=transfer(app,shipment,old)
        assert second.previous_transfer_id==first.id and second.sequence_number==2
        pinned=first.new_owner_label
        target.full_name="Renamed current identity";target.is_active=False;db.session.commit()
        replay,created=svc.transfer(shipment.public_id,_user(app,"verifier"),payload,key);db.session.commit()
        assert not created and replay.id==first.id and Transfer.query.count()==2
        assert first.new_owner_label==pinned and shipment.primary_responsible_expert_id==old.id
        with pytest.raises(base.OperationalError) as conflict:
            svc.transfer(shipment.public_id,_user(app,"verifier"),{**payload,"reason":"different"},key)
        assert conflict.value.code=="OWNER_TRANSFER_KEY_CONFLICT"


@pytest.mark.parametrize("identity",["user","outsider","platform","inactive","duplicate"])
def test_admin_authority_is_live_not_claimed_in_input(operational_app,identity):
    app=operational_app
    with app.app_context():
        shipment,target,_=setup(app)
        actor=_user(app,identity if identity in {"user","outsider"} else "verifier")
        actor["role"]="admin";actor["authority"]="ORGANIZATION_ADMIN"
        row=db.session.get(ExpertUser,actor["id"])
        if identity=="platform": row.authority="PLATFORM_ADMIN"
        if identity=="inactive": row.is_active=False
        if identity=="duplicate": db.session.add(Membership(user_id=row.id,organization_id=app.config["phase1a"]["other_org"],permissions=[]))
        db.session.commit()
        with pytest.raises(base.OperationalError) as denied:
            svc.transfer(shipment.public_id,actor,command(shipment,target),str(uuid4()))
        assert denied.value.status==403 and Transfer.query.count()==0


@pytest.mark.parametrize("invalid",["inactive","foreign","admin","platform","no_membership","duplicate"])
def test_target_eligibility_is_current(operational_app,invalid):
    app=operational_app
    with app.app_context():
        shipment,target,_=setup(app)
        membership=db.session.scalar(select(Membership).where(Membership.user_id==target.id))
        if invalid=="inactive": target.is_active=False
        if invalid=="foreign": membership.organization_id=app.config["phase1a"]["other_org"]
        if invalid=="admin": target.authority="ORGANIZATION_ADMIN"
        if invalid=="platform": target.authority="PLATFORM_ADMIN"
        if invalid=="no_membership": membership.is_active=False
        if invalid=="duplicate": db.session.add(Membership(user_id=target.id,organization_id=app.config["phase1a"]["other_org"],permissions=[]))
        db.session.commit()
        with pytest.raises(base.OperationalError) as denied: transfer(app,shipment,target)
        assert denied.value.code=="OWNER_TRANSFER_TARGET_INVALID" and Transfer.query.count()==0
        assert target.id not in [row["id"] for row in svc.candidates(shipment.public_id,_user(app,"verifier"))["candidates"]]


def test_owner_and_history_orm_prohibition_and_atomic_rollback(operational_app,monkeypatch):
    app=operational_app
    with app.app_context():
        shipment,target,_=setup(app)
        old,version=shipment.primary_responsible_expert_id,shipment.version
        shipment.primary_responsible_expert_id=target.id
        with pytest.raises(ValueError,match="immutable"): db.session.flush()
        db.session.rollback()
        def failure(*_args,**_kwargs): raise RuntimeError("Synthetic outbox failure")
        with monkeypatch.context() as patch:
            patch.setattr(base,"_outbox",failure)
            with pytest.raises(RuntimeError,match="Synthetic outbox failure"):
                svc.transfer(shipment.public_id,_user(app,"verifier"),command(shipment,target),str(uuid4()))
            db.session.rollback()
        assert (shipment.primary_responsible_expert_id,shipment.version)==(old,version)
        assert Transfer.query.count()==0 and OperationalAudit.query.filter_by(action="shipment.owner_transferred").count()==0
        row,_=transfer(app,shipment,target)
        row.reason="rewrite"
        with pytest.raises(ValueError,match="immutable"): db.session.flush()
        db.session.rollback()
        db.session.delete(row)
        with pytest.raises(ValueError,match="immutable"): db.session.flush()
        db.session.rollback()


def test_http_binding_payload_no_store_and_post_transfer_access(operational_app):
    app=operational_app
    with app.app_context():
        shipment,target,_=setup(app);sid=shipment.public_id;payload=command(shipment,target)
    client=app.test_client();path=f"/api/operational-shipments/{sid}/owner-transfers"
    admin=_auth(app,"verifier")
    assert client.post(path,json=payload,headers={**_auth(app),"Idempotency-Key":str(uuid4())}).status_code==403
    assert client.post(path,json={**payload,"actor_user_id":app.config["phase1a"]["verifier"]},headers={**admin,"Idempotency-Key":str(uuid4())}).status_code==422
    response=client.post(path,json=payload,headers={**admin,"Idempotency-Key":str(uuid4())})
    assert response.status_code==201 and "no-store" in response.headers["Cache-Control"]
    assert client.get(path,headers=_auth(app)).status_code==404
    assert client.get(path,headers=_auth(app,"target")).status_code==200
    assert client.get(f"/api/operational-shipments/{sid}/owner-transfer-candidates",headers=_auth(app,"target")).status_code==403


def test_sqlite_adapter_cannot_bypass_a_migrated_database(operational_app):
    app=operational_app
    with app.app_context():
        shipment,target,_=setup(app)
        db.session.execute(text("CREATE TABLE alembic_version(version_num TEXT NOT NULL)"));db.session.commit()
        with pytest.raises(base.OperationalError) as denied: transfer(app,shipment,target)
        assert denied.value.code=="OWNER_TRANSFER_UNAVAILABLE" and Transfer.query.count()==0


def test_document_bytes_history_current_downloads_and_customer_visibility(shipment_documents_app):
    import io
    from backend.models import CaseDocumentFile
    from backend.tests.test_phase3_document_context import _portal, _as_customer
    app,state=shipment_documents_app
    customer,_=_portal(app,state)
    client=app.test_client()
    path=f"/api/internal/operational-shipments/{state['shipment']}/documents"
    uploaded=client.post(path,headers={**_headers(state["owner"]),"Idempotency-Key":str(uuid4())},
        data={"title":"Historical evidence","file":(io.BytesIO(PDF),"original.pdf"),
              "visibility":"EXPLICIT_SHARED","audience_public_ids":customer[1]})
    assert uploaded.status_code==201
    doc=uploaded.json["data"];download=f"{path}/{doc['public_id']}/download"
    _as_customer(client,customer[0])
    customer_before=client.get("/api/customer/documents").json
    with app.app_context():
        shipment=db.session.get(Shipment,state["shipment_id"])
        before=list(db.session.execute(select(CaseDocumentFile.__table__)).all())
        target=ExpertUser.query.filter_by(username="shipment-doc-peer").one()
        admin=ExpertUser.query.filter_by(username="shipment-doc-admin").one()
        svc.transfer(shipment.public_id,{"id":admin.id},command(shipment,target),str(uuid4()));db.session.commit()
        assert list(db.session.execute(select(CaseDocumentFile.__table__)).all())==before
    assert client.get(download,headers=_headers(state["owner"])).status_code==404
    assert client.get(path,headers=_headers(state["owner"])).status_code==404
    assert client.get(download,headers=_headers(state["peer"])).data==PDF
    assert client.get(path,headers=_headers(state["peer"])).json["can_manage_documents"] is True
    assert client.get(path,headers=_headers(state["admin"])).json["can_manage_documents"] is False
    for actor in ("owner","admin"):
        assert client.patch(f"{path}/{doc['public_id']}/context",headers=_headers(state[actor]),
            json={"expected_version":1,"visibility":"INTERNAL"}).status_code==404
        assert client.delete(f"{path}/{doc['public_id']}",headers=_headers(state[actor]),json={"reason":"Denied mutation"}).status_code==404
    assert client.get("/api/customer/documents").json==customer_before
    assert client.get(f"/api/customer/documents/{doc['public_id']}/download").data==PDF
    appended=client.post(path,headers={**_headers(state["peer"]),"Idempotency-Key":str(uuid4())},
        data={"title":"New owner evidence","file":(io.BytesIO(PDF),"next.pdf")})
    assert appended.status_code==201 and appended.json["data"]["actor"]=="Peer"
    assert client.get(download,headers=_headers(state["peer"])).data==PDF


def test_sla_background_and_old_and_third_party_work_remain_pinned(operational_app):
    from datetime import timedelta
    from backend.operational_models import OperationalSlaCommitment
    from backend.services import organization_sla_service as sla
    app=operational_app
    with app.app_context():
        shipment,target,third=setup(app);old=shipment.primary_responsible_expert_id
        sla.create_rule({"process_type":"ACTION_FOLLOW_UP","name":"Pinned action SLA","duration_minutes":60},{**_user(app,"verifier"),"authority":"ORGANIZATION_ADMIN"})
        started=utcnow()+timedelta(seconds=1)
        rows=[Work(organization_id=shipment.organization_id,operational_shipment_id=shipment.id,
            work_type="FOLLOW_UP",action_context_type="SHIPMENT",assignee_user_id=identity,
            created_at=started,due_at=started+timedelta(hours=1),reason="Retained assignment") for identity in (old,third.id)]
        db.session.add_all(rows);db.session.commit()
        sla.evaluate_organization(shipment.organization_id,calculation_time=started+timedelta(minutes=1));db.session.commit()
        commitments=OperationalSlaCommitment.query.all()
        assert len(commitments)==2
        pinned=[(row.id,row.responsible_user_id,row.rule_version,row.started_at,row.due_at) for row in commitments]
        transfer(app,shipment,target)
        for minutes in (5,90):
            sla.evaluate_organization(shipment.organization_id,calculation_time=started+timedelta(minutes=minutes));db.session.commit()
        assert [(row.id,row.responsible_user_id,row.rule_version,row.started_at,row.due_at) for row in commitments]==pinned
        assert [row.assignee_user_id for row in rows]==[old,third.id] and all(row.status=="open" for row in rows)


def test_closed_transfer_preserves_decision_and_closed_command_boundary(operational_app):
    from backend.tests.test_phase3_closure import policy, close
    from backend.services import closure_commands
    app=operational_app
    with app.app_context():
        shipment,target,_=setup(app);shipment.lifecycle_status="completed";db.session.commit()
        policy(app);decision=close(app,shipment)
        preserved=(decision.public_id,decision.actor_user_id,decision.occurred_at,decision.assessment)
        transfer(app,shipment,target)
        assert shipment.lifecycle_status=="closed"
        assert (decision.public_id,decision.actor_user_id,decision.occurred_at,decision.assessment)==preserved
        assert authorize_document_management(_user(app,"target"),shipment).allowed
        with pytest.raises(base.OperationalError): closure_commands.deny_new(shipment)


def test_current_list_workspace_tower_and_independent_project_read(operational_app):
    from backend.operational_models import Project, ProjectAccess
    app=operational_app
    with app.app_context():
        shipment,target,_=setup(app);sid=shipment.public_id
        db.session.add(Work(organization_id=shipment.organization_id,operational_shipment_id=shipment.id,work_type="FOLLOW_UP",action_context_type="SHIPMENT",assignee_user_id=shipment.primary_responsible_expert_id,due_at=utcnow(),reason="Current attention"));db.session.commit()
        transfer(app,shipment,target)
    client=app.test_client()
    for path in ("/api/operational-shipments?active=true","/api/operational-workspace","/api/control-tower/shipments"):
        old=client.get(path,headers=_auth(app));new=client.get(path,headers=_auth(app,"target"))
        assert old.status_code==new.status_code==200
        assert sid not in str(old.json) and sid in str(new.json)
    with app.app_context():
        shipment=Shipment.query.filter_by(public_id=sid).one()
        project=Project(organization_id=shipment.organization_id,project_code="Independent-project-read",primary_customer_id=shipment.customer_id,
            created_by_user_id=app.config["phase1a"]["verifier"])
        db.session.add(project);db.session.flush();shipment.project_id=project.id
        db.session.add(ProjectAccess(organization_id=shipment.organization_id,project_id=project.id,
            user_id=app.config["phase1a"]["user"],created_by_user_id=app.config["phase1a"]["verifier"]))
        db.session.commit()
        assert authorize_work_action(_user(app),shipment,"shipment.read").allowed
        assert not authorize_document_management(_user(app),shipment,for_update=True).allowed


def test_openapi_routes_and_recursive_allowlists(operational_app):
    import re
    from pathlib import Path
    import yaml
    app=operational_app
    document=yaml.safe_load((Path(__file__).resolve().parents[2]/"docs/openapi/openapi.yaml").read_text(encoding="utf-8"))
    actual={(re.sub(r"<(?:uuid|int):([^>]+)>",r"{\1}",rule.rule),method.lower()) for rule in app.url_map.iter_rules()
        if rule.endpoint.startswith("owner_transfer.") for method in rule.methods-{"HEAD","OPTIONS"}}
    declared={(path,method) for path,value in document["paths"].items() if "/owner-transfer" in path
        for method in value if method in {"get","post","put","delete","patch"}}
    assert actual==declared
    def check(value,schema):
        if "$ref" in schema:schema=document["components"]["schemas"][schema["$ref"].split("/")[-1]]
        if value is None: assert schema.get("nullable");return
        if isinstance(value,dict):
            assert schema["additionalProperties"] is False
            assert set(schema["required"])<=set(value)<=set(schema["properties"])
            for key,item in value.items():check(item,schema["properties"][key])
        elif isinstance(value,list):
            for item in value:check(item,schema["items"])
    with app.app_context():
        shipment,target,_=setup(app)
        check(command(shipment,target),document["components"]["schemas"]["OwnerTransferCommand"])
        check(svc.candidates(shipment.public_id,_user(app,"verifier")),document["components"]["schemas"]["OwnerTransferCandidates"])
        transfer(app,shipment,target)
        for actor in ("verifier","target"):
            check(svc.read(shipment.public_id,_user(app,actor)),document["components"]["schemas"]["OwnerTransferView"])
