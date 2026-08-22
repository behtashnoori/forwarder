import os
import pytest
from sqlalchemy import inspect

from backend import create_app
from backend.extensions import db
from backend.global_logistics_point_models import GlobalLogisticsPoint,GlobalLogisticsPointMode,OrganizationGlobalLogisticsPointAdoption
from backend.logistics_network_models import LogisticsPoint,LogisticsPointType
from backend.models import Country,ExpertUser
from backend.operational_models import OperationalMembership,OperationalOrganization
from backend.services import global_logistics_point_adoption_service as svc

URL=os.environ.get("GLOBAL_POINT_ADOPTION_DISPOSABLE_POSTGRES_URL","")
pytestmark=pytest.mark.skipif(not URL,reason="requires explicit disposable PostgreSQL URL")


def test_postgresql_two_tenant_adoption_constraints_and_lifecycle():
 assert "127.0.0.1" in URL and "global_point_adoption_" in URL
 app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":URL,"SECRET_KEY":"pg-adoption"},skip_startup=True)
 with app.app_context():
  assert "organization_global_logistics_point_adoption" in inspect(db.engine).get_table_names()
  actor_a=ExpertUser(username="pg-adopt-a",password_hash="x",full_name="A",role="admin",authority="ORGANIZATION_ADMIN",is_active=True)
  actor_b=ExpertUser(username="pg-adopt-b",password_hash="x",full_name="B",role="admin",authority="ORGANIZATION_ADMIN",is_active=True)
  org_a=OperationalOrganization(name="PG A");org_b=OperationalOrganization(name="PG B");country=Country(code="XY",name_en="PG",name_fa="آزمون")
  db.session.add_all([actor_a,actor_b,org_a,org_b,country]);db.session.flush()
  kind=LogisticsPointType(immutable_code="PORT",fa_name="بندر",en_name="Port",created_by=actor_a.id,updated_by=actor_a.id);db.session.add(kind);db.session.flush()
  db.session.add_all([OperationalMembership(organization_id=org_a.id,user_id=actor_a.id),OperationalMembership(organization_id=org_b.id,user_id=actor_b.id)])
  point=GlobalLogisticsPoint(immutable_code="XY-PG-PORT",logistics_point_type_id=kind.id,fa_name="بندر",en_name="Port",normalized_name="port",country_id=country.id,city_name="PG City",geography_key="XY:pg",facility_identity_key="pg-port",lifecycle_status="ACTIVE",verification_status="VERIFIED",created_by=actor_a.id,updated_by=actor_a.id)
  point.modes.append(GlobalLogisticsPointMode(mode_code="SEA"));db.session.add(point);db.session.commit()
  a=svc.adopt(point.public_id,{},org_a.id,actor_a.id);b=svc.adopt(point.public_id,{},org_b.id,actor_b.id)
  assert a.public_id!=b.public_id and db.session.query(OrganizationGlobalLogisticsPointAdoption).count()==2
  with pytest.raises(Exception) as duplicate:svc.adopt(point.public_id,{},org_a.id,actor_a.id)
  assert getattr(duplicate.value,"code",None)=="ADOPTION_CONFLICT"
  a=svc.transition(a.public_id,{"version":1},org_a.id,actor_a.id,"INACTIVE")
  a=svc.transition(a.public_id,{"version":2},org_a.id,actor_a.id,"ACTIVE")
  assert a.status=="ACTIVE" and a.version==3
  materialized,created=svc.materialize(a.public_id,{"immutable_code":"PG-A-PORT"},org_a.id,actor_a.id)
  assert created and materialized.organization_id==org_a.id
  repeated,created=svc.materialize(a.public_id,{"immutable_code":"IGNORED"},org_a.id,actor_a.id)
  assert not created and repeated.id==materialized.id
  other,created=svc.materialize(b.public_id,{"immutable_code":"PG-B-PORT"},org_b.id,actor_b.id)
  assert created and other.organization_id==org_b.id and db.session.query(LogisticsPoint).count()==2
  with pytest.raises(Exception) as hidden:svc.scoped_adoption(b.public_id,org_a.id)
  assert getattr(hidden.value,"status",None)==404
