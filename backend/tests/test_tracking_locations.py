from datetime import datetime,timedelta

from backend import create_app
from backend.extensions import db
import pytest
from sqlalchemy.exc import IntegrityError

from backend.models import Customer,ExpertUser,ShipmentRequest,TrackingLocationReference
from backend.operational_models import OperationalMembership,OperationalOrganization,OperationalShipment,Project
from backend.services import execution_unit_service
from backend.services.auth_session_service import create_session_tokens
from backend.services.operational_service import OperationalError
from backend.services.tracking_projection_service import project_execution_units
from backend.tests.canonical_tracking_fixture import append_event,execution_unit
from backend.services.tracking_location_bootstrap_service import ROWS,bootstrap
from backend.services import tracking_location_service

def _app(): return create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","SECRET_KEY":"tracking-location"},skip_startup=True)

def _canonical_root(actor,organization,code):
 customer=Customer(first_name="Tracking",last_name=code);db.session.add(customer);db.session.flush()
 project=Project(organization_id=organization.id,primary_customer_id=customer.id,project_code=code,tracking_code=code,created_by_user_id=actor.id);db.session.add(project);db.session.flush()
 shipment=OperationalShipment(organization_id=organization.id,project_id=project.id,source_type="direct",customer_id=customer.id,created_by_user_id=actor.id,primary_responsible_expert_id=actor.id);db.session.add(shipment);db.session.flush()
 return project,shipment

def test_bootstrap_dry_run_apply_idempotency_and_alias_policy():
 app=_app()
 with app.app_context():
  db.create_all(); dry=bootstrap(); assert dry["inserted"]==len(ROWS);assert TrackingLocationReference.query.count()==0
  first=bootstrap(apply=True);assert first["inserted"]==len(ROWS)
  second=bootstrap(apply=True);assert second=={"inserted":0,"updated":0,"unchanged":len(ROWS),"total":len(ROWS),"applied":True}
  yiwu=TrackingLocationReference.query.filter_by(internal_key="cn-yiwu").one();xian=TrackingLocationReference.query.filter_by(internal_key="cn-xian").one()
  assert yiwu.id!=xian.id;assert "یی وو" in yiwu.aliases;assert "Xian" in xian.aliases
  assert not TrackingLocationReference.query.filter(db.func.lower(TrackingLocationReference.name_en)=="ash").first()
  osh=TrackingLocationReference.query.filter_by(internal_key="KG-OSH").one()
  assert osh.country_code=="KG";assert osh.location_type=="commercial_hub"
  assert osh.aliases==["Osh","Ош","اوش"]

def test_osh_search_identity_and_bootstrap_preserves_protected_fields():
 app=_app()
 with app.app_context():
  db.create_all();bootstrap(apply=True)
  osh=TrackingLocationReference.query.filter_by(internal_key="KG-OSH").one()
  osh.name_fa="نام قدیمی";osh.aliases=[];osh.country_code="KG";osh.location_type="commercial_hub"
  db.session.commit();result=bootstrap(apply=True);db.session.refresh(osh)
  assert result["updated"]==1;assert osh.name_fa=="اوش";assert osh.country_code=="KG"
  assert osh.location_type=="commercial_hub"
  for term in ("Osh","Ош","اوش"):
   assert [row.internal_key for row in tracking_location_service.search(query=term)]==["KG-OSH"]
  assert "KG-OSH" not in [row.internal_key for row in tracking_location_service.search(query="Ash")]

def test_known_and_free_text_snapshots_survive_rename_and_deactivation():
 app=_app()
 with app.app_context():
  db.create_all();bootstrap(apply=True)
  actor=ExpertUser(username="e",password_hash="x",full_name="E",role="expert",is_active=True)
  organization=OperationalOrganization(name="Tracking Location Organization")
  db.session.add_all([actor,organization])
  db.session.flush()
  db.session.add(OperationalMembership(organization_id=organization.id,user_id=actor.id,permissions=[]))
  req=ShipmentRequest(contact_phone="1",status="won",status_request_status="new",tracking_code="T",ownership_scope="TENANT",operational_organization_id=organization.id)
  db.session.add(req);project,shipment=_canonical_root(actor,organization,"T")
  db.session.commit()
  unit=execution_unit(project,actor.id,shipment=shipment,unit_code="U",unit_type="truck")
  yiwu=TrackingLocationReference.query.filter_by(internal_key="cn-yiwu").one();known=append_event(unit,actor.id,status="in_transit",occurred_at=datetime.utcnow()-timedelta(minutes=2),location_reference_id=yiwu.id)
  free=append_event(unit,actor.id,status="at_checkpoint",occurred_at=datetime.utcnow()-timedelta(minutes=1),location_text="Ash")
  db.session.commit();yiwu.name_fa="نام جدید";yiwu.is_active=False;db.session.commit()
  assert known.location_evidence.display_name_snapshot=="ایوو";assert known.location_evidence.country_code_snapshot=="CN";assert free.location_evidence.location_text_snapshot=="Ash";assert free.location_evidence.source_type=="manual"
  assert TrackingLocationReference.query.count()==len(ROWS)

def test_search_permissions_filters_and_admin_deactivation():
 app=_app()
 with app.app_context():
  db.create_all();bootstrap(apply=True)
  expert=ExpertUser(username="e",password_hash="x",full_name="E",role="expert",is_active=True);admin=ExpertUser(username="a",password_hash="x",full_name="A",role="admin",authority="PLATFORM_ADMIN",is_active=True);db.session.add_all([expert,admin]);db.session.commit()
  et=create_session_tokens(expert.id)["access_token"];at=create_session_tokens(admin.id)["access_token"];client=app.test_client();h=lambda t:{"Authorization":f"Bearer {t}"}
  assert client.get("/api/tracking-locations").status_code==401
  fa=client.get("/api/tracking-locations?q=ایوو",headers=h(et));assert fa.status_code==200;assert fa.get_json()["items"][0]["name_en"]=="Yiwu"
  alias=client.get("/api/tracking-locations?q=Xian&country=CN&location_type=rail_terminal",headers=h(et));assert any(x["name_en"]=="Xi'an" for x in alias.get_json()["items"])
  assert client.post("/api/tracking-locations",headers=h(et),json={}).status_code==403
  yiwu=TrackingLocationReference.query.filter_by(internal_key="cn-yiwu").one();assert client.delete(f"/api/tracking-locations/{yiwu.id}",headers=h(at)).status_code==200
  assert not any(x["id"]==yiwu.id for x in client.get("/api/tracking-locations",headers=h(et)).get_json()["items"])
  assert any(x["id"]==yiwu.id for x in client.get("/api/tracking-locations?include_inactive=true",headers=h(at)).get_json()["items"])

def test_reference_constraints_defaults_and_distinct_required_locations():
 app=_app()
 with app.app_context():
  db.create_all();bootstrap(apply=True)
  osh=TrackingLocationReference.query.filter_by(internal_key="KG-OSH").one()
  assert osh.is_active is True and osh.reference_status=="internal_reference"
  assert osh.location_type!="border_point"
  required={"cn-yiwu","cn-xian","KG-OSH","kz-almaty","kz-shymkent","cn-kashgar"}
  assert required.issubset({row.internal_key for row in TrackingLocationReference.query.all()})
  db.session.add(TrackingLocationReference(internal_key="KG-OSH",name_fa="تکراری",country_code="KG",location_type="other"))
  with pytest.raises(IntegrityError): db.session.commit()
  db.session.rollback()
  invalid=TrackingLocationReference(internal_key="bad-type",name_fa="نام",country_code="IR",location_type="customs_master")
  db.session.add(invalid)
  with pytest.raises(IntegrityError): db.session.commit()

def test_location_validation_latest_snapshot_and_no_hard_delete_when_referenced():
 app=_app()
 with app.app_context():
  db.create_all();bootstrap(apply=True)
  actor=ExpertUser(username="rules",password_hash="x",full_name="Rules",role="expert",is_active=True)
  organization=OperationalOrganization(name="Tracking Rules Organization")
  db.session.add_all([actor,organization])
  db.session.flush()
  db.session.add(OperationalMembership(organization_id=organization.id,user_id=actor.id,permissions=[]))
  req=ShipmentRequest(contact_phone="2",status="won",status_request_status="new",tracking_code="RULES",ownership_scope="TENANT",operational_organization_id=organization.id)
  db.session.add(req);project,shipment=_canonical_root(actor,organization,"RULES")
  db.session.commit()
  unit=execution_unit(project,actor.id,shipment=shipment,unit_code="RULES-U",unit_type="truck")
  osh=TrackingLocationReference.query.filter_by(internal_key="KG-OSH").one()
  known=append_event(unit,actor.id,status="in_transit",occurred_at=datetime.utcnow()-timedelta(minutes=3),location_reference_id=osh.id)
  append_event(unit,actor.id,status="delayed",occurred_at=datetime.utcnow()-timedelta(minutes=2))
  ash=append_event(unit,actor.id,status="at_checkpoint",occurred_at=datetime.utcnow()-timedelta(minutes=1),location_text="اش")
  db.session.commit()
  assert ash.location_evidence.source_type=="manual" and ash.location_evidence.country_code_snapshot is None
  assert TrackingLocationReference.query.count()==len(ROWS)
  internal=project_execution_units(organization.id,[unit.id])[unit.id]
  public=execution_unit_service.timeline(unit,{},customer=True)["data"]
  assert internal["current_location"]=="اش"
  assert public[0]["location"]["source_type"]=="manual"
  osh.name_fa="اوش جدید";osh.is_active=False;db.session.commit()
  assert known.location_evidence.display_name_snapshot=="اوش" and known.location_evidence.country_code_snapshot=="KG"
  with pytest.raises(OperationalError,match="not active"):
   append_event(unit,actor.id,status="in_transit",occurred_at=datetime.utcnow(),location_reference_id=osh.id)
  db.session.delete(osh)
  with pytest.raises(ValueError,match="cannot be hard deleted"): db.session.commit()
  db.session.rollback()
  assert known.location_evidence.display_name_snapshot=="اوش"

def test_ash_exact_terms_never_resolve_to_osh_and_bootstrap_repairs_osh_identity():
 app=_app()
 with app.app_context():
  db.create_all();bootstrap(apply=True)
  osh=TrackingLocationReference.query.filter_by(internal_key="KG-OSH").one()
  osh.country_code="KZ";osh.location_type="border_point";osh.is_active=False;osh.reference_status="inactive"
  db.session.commit();result=bootstrap(apply=True);db.session.refresh(osh)
  assert result["updated"]==1
  assert (osh.country_code,osh.location_type,osh.is_active,osh.reference_status)==("KG","commercial_hub",True,"internal_reference")
  for term in ("Ash","اش"):
   assert all(row.internal_key!="KG-OSH" for row in tracking_location_service.search(query=term))
