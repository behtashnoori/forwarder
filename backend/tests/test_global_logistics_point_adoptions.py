"""ADR-041 Phase 3 tenant adoption API and domain contract."""
import pytest

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.global_logistics_point_models import GlobalLogisticsPoint, GlobalLogisticsPointMode
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType, ProjectLogisticsPoint
from backend.models import Country, ExpertUser, TrackingLocationReference
from backend.operational_models import OperationalMembership, OperationalOrganization


@pytest.fixture()
def adoption_app():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","SECRET_KEY":"adoption-test"})
    with app.app_context():
        db.create_all()
        platform=ExpertUser(username="adopt-platform",password_hash="x",full_name="Platform",role="admin",authority="PLATFORM_ADMIN",is_active=True)
        admin_a=ExpertUser(username="adopt-a",password_hash="x",full_name="Admin A",role="admin",authority="ORGANIZATION_ADMIN",is_active=True)
        admin_b=ExpertUser(username="adopt-b",password_hash="x",full_name="Admin B",role="admin",authority="ORGANIZATION_ADMIN",is_active=True)
        expert=ExpertUser(username="adopt-expert",password_hash="x",full_name="Expert",role="expert",authority="EXPERT",is_active=True)
        org_a=OperationalOrganization(name="Organization A"); org_b=OperationalOrganization(name="Organization B")
        country=Country(code="XZ",name_en="Test Country",name_fa="کشور آزمون")
        db.session.add_all([platform,admin_a,admin_b,expert,org_a,org_b,country]); db.session.flush()
        point_type=LogisticsPointType(immutable_code="PORT",fa_name="بندر",en_name="Port",created_by=platform.id,updated_by=platform.id)
        db.session.add(point_type); db.session.flush()
        for user,org in ((admin_a,org_a),(admin_b,org_b),(expert,org_a)):
            db.session.add(OperationalMembership(organization_id=org.id,user_id=user.id,permissions=["logistics_point.read","logistics_point.manage"]))
        def point(code,status,verification="VERIFIED"):
            row=GlobalLogisticsPoint(immutable_code=code,logistics_point_type_id=point_type.id,fa_name=code,en_name=code,
                normalized_name=code.lower(),country_id=country.id,city_name="Test City",geography_key="XZ:test",
                facility_identity_key=code.lower(),lifecycle_status=status,verification_status=verification,
                created_by=platform.id,updated_by=platform.id)
            row.modes.append(GlobalLogisticsPointMode(mode_code="SEA")); db.session.add(row); return row
        active=point("XZ-ACTIVE-PORT","ACTIVE"); draft=point("XZ-DRAFT-PORT","DRAFT","UNVERIFIED"); deprecated=point("XZ-OLD-PORT","DEPRECATED")
        db.session.commit()
        headers=lambda user:{"Authorization":f"Bearer {auth_manager.generate_tokens(user.id)['access_token']}"}
        yield app,{"platform":headers(platform),"a":headers(admin_a),"b":headers(admin_b),"expert":headers(expert),
            "active":active.public_id,"draft":draft.public_id,"deprecated":deprecated.public_id,
            "org_a":org_a.id,"org_b":org_b.id}
        db.session.remove();db.drop_all()


def test_authority_eligibility_and_server_derived_tenant(adoption_app):
    app,c=adoption_app; browse="/api/admin/global-logistics-points"
    with app.test_client() as client:
        assert client.get(browse).status_code==401
        assert client.get(browse,headers=c["expert"]).status_code==403
        assert client.get(browse,headers=c["platform"]).status_code==403
        result=client.get(browse,headers=c["a"]); assert result.status_code==200
        assert [x["public_id"] for x in result.get_json()["items"]]==[c["active"]]
        for target in (c["draft"],c["deprecated"]):
            assert client.post(f"{browse}/{target}/adopt",headers=c["a"],json={}).status_code==409
        malicious={"organization_id":c["org_b"],"tenant_id":c["org_b"],"created_by":999}
        denied=client.post(f"{browse}/{c['active']}/adopt",headers=c["a"],json=malicious)
        assert denied.status_code==400 and denied.get_json()["error"]["code"]=="UNKNOWN_FIELDS"


def test_two_tenant_adoption_isolation_metadata_and_no_materialization(adoption_app):
    app,c=adoption_app; base="/api/admin/global-logistics-points"
    with app.test_client() as client:
        a=client.post(f"{base}/{c['active']}/adopt",headers=c["a"],json={"organization_reference_code":"A-PORT","display_label":"A Port","notes":"Tenant A"})
        assert a.status_code==201; adoption_a=a.get_json()["item"]
        assert adoption_a["version"]==1 and adoption_a["status"]=="ACTIVE" and "organization_id" not in adoption_a
        duplicate=client.post(f"{base}/{c['active']}/adopt",headers=c["a"],json={})
        assert duplicate.status_code==409
        b=client.post(f"{base}/{c['active']}/adopt",headers=c["b"],json={"display_label":"B Port"})
        assert b.status_code==201 and b.get_json()["item"]["public_id"]!=adoption_a["public_id"]
        a_browse=client.get(base,headers=c["a"]).get_json()["items"][0]
        assert a_browse["organization_state"]=="ADOPTED" and a_browse["adoption"]["display_label"]=="A Port"
        for method,path,json in (("get",f"/api/admin/global-logistics-point-adoptions/{b.get_json()['item']['public_id']}",None),
            ("patch",f"/api/admin/global-logistics-point-adoptions/{b.get_json()['item']['public_id']}",{"version":1,"notes":"attack"}),
            ("post",f"/api/admin/global-logistics-point-adoptions/{b.get_json()['item']['public_id']}/deactivate",{"version":1})):
            assert getattr(client,method)(path,headers=c["a"],json=json).status_code==404
        with app.app_context():
            assert db.session.query(LogisticsPoint).count()==0
            assert db.session.query(ProjectLogisticsPoint).count()==0
            assert db.session.query(TrackingLocationReference).count()==0


def test_update_lifecycle_version_and_platform_deprecation_preserves_history(adoption_app):
    app,c=adoption_app; base="/api/admin/global-logistics-points"
    with app.test_client() as client:
        item=client.post(f"{base}/{c['active']}/adopt",headers=c["a"],json={}).get_json()["item"]
        url=f"/api/admin/global-logistics-point-adoptions/{item['public_id']}"
        updated=client.patch(url,headers=c["a"],json={"version":1,"display_label":"Local label","organization_reference_code":"LOCAL-1","notes":"Local notes"})
        assert updated.status_code==200 and updated.get_json()["item"]["version"]==2
        assert client.patch(url,headers=c["a"],json={"version":1,"notes":"stale"}).status_code==409
        for forbidden in ("global_immutable_code","fa_name","country","global_logistics_point_id","organization_id"):
            assert client.patch(url,headers=c["a"],json={"version":2,forbidden:"attack"}).status_code==400
        inactive=client.post(f"{url}/deactivate",headers=c["a"],json={"version":2})
        assert inactive.status_code==200 and inactive.get_json()["item"]["status"]=="INACTIVE"
        active=client.post(f"{url}/activate",headers=c["a"],json={"version":3})
        assert active.status_code==200 and active.get_json()["item"]["status"]=="ACTIVE"
        client.post(f"{url}/deactivate",headers=c["a"],json={"version":4})
        with app.app_context():
            db.session.execute(db.update(GlobalLogisticsPoint).where(GlobalLogisticsPoint.public_id==c["active"]).values(lifecycle_status="DEPRECATED"))
            db.session.commit(); db.session.remove()
        view=next(x for x in client.get(base,headers=c["a"]).get_json()["items"] if x["public_id"]==c["active"])
        assert view["organization_state"]=="PLATFORM_DEPRECATED" and view["adoption"] is not None
        assert client.post(f"{url}/activate",headers=c["a"],json={"version":5}).status_code==409
        assert client.post(f"{base}/{c['active']}/adopt",headers=c["b"],json={}).status_code==409
