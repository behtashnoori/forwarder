"""Two-organization adversarial certification for administrative isolation."""
import bcrypt
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.auth_session_service import create_session_tokens


@pytest.fixture()
def mt_admin_app():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","SECRET_KEY":"mt-admin-secret"},skip_startup=True)
    with app.app_context():
        db.create_all(); password=bcrypt.hashpw(b"test123",bcrypt.gensalt()).decode()
        org_a=OperationalOrganization(public_id="samand-tarabar",name="Org A",is_active=True)
        org_b=OperationalOrganization(public_id="company-b",name="Org B",is_active=True)
        db.session.add_all([org_a,org_b]);db.session.flush()
        platform=ExpertUser(username="platform",password_hash=password,full_name="Platform",role="admin",authority="PLATFORM_ADMIN",is_active=True)
        admin_a=ExpertUser(username="admin-a",password_hash=password,full_name="Admin A",role="admin",authority="ORGANIZATION_ADMIN",is_active=True)
        admin_b=ExpertUser(username="admin-b",password_hash=password,full_name="Admin B",role="admin",authority="ORGANIZATION_ADMIN",is_active=True)
        expert_a=ExpertUser(username="expert-a",password_hash=password,full_name="Expert A",role="expert",authority="EXPERT",is_active=True)
        expert_b=ExpertUser(username="expert-b",password_hash=password,full_name="Expert B",role="expert",authority="EXPERT",is_active=True)
        db.session.add_all([platform,admin_a,admin_b,expert_a,expert_b]);db.session.flush()
        for org,user in ((org_a,admin_a),(org_a,expert_a),(org_b,admin_b),(org_b,expert_b)):
            db.session.add(OperationalMembership(organization_id=org.id,user_id=user.id,is_active=True,permissions=[]))
        req_a=ShipmentRequest(tracking_code="MT-A",shipping_type="domestic",contact_phone="09000000001",status_request_status="new",status="new",operational_organization_id=org_a.id,ownership_scope="TENANT")
        req_b=ShipmentRequest(tracking_code="MT-B",shipping_type="domestic",contact_phone="09000000002",status_request_status="new",status="new",operational_organization_id=org_b.id,ownership_scope="TENANT")
        db.session.add_all([req_a,req_b]);db.session.commit()
        ids={name:obj.id for name,obj in {"platform":platform,"admin_a":admin_a,"admin_b":admin_b,"expert_a":expert_a,"expert_b":expert_b,"req_a":req_a,"req_b":req_b,"org_a":org_a,"org_b":org_b}.items()}
        tokens={name:create_session_tokens(obj.id)["access_token"] for name,obj in (("platform",platform),("admin_a",admin_a),("admin_b",admin_b),("expert_a",expert_a),("expert_b",expert_b))}
        return app,ids,tokens

def h(tokens,name): return {"Authorization":f"Bearer {tokens[name]}"}

def test_user_idor_and_role_escalation(mt_admin_app):
    app,ids,tokens=mt_admin_app;c=app.test_client();headers=h(tokens,"admin_a")
    users=c.get("/api/user-management/users",headers=headers).get_json()["users"]
    assert {u["id"] for u in users}=={ids["admin_a"],ids["expert_a"]}
    assert c.get(f"/api/user-management/users/{ids['expert_b']}",headers=headers).status_code==404
    assert c.put(f"/api/user-management/users/{ids['expert_b']}",headers=headers,json={"full_name":"pwned"}).status_code==404
    assert c.put(f"/api/user-management/users/{ids['expert_a']}",headers=headers,json={"manager_id":ids["admin_b"]}).status_code==400
    assert c.post("/api/user-management/users",headers=headers,json={"username":"escalate","password":"test123","full_name":"Escalate","role":"expert","authority":"PLATFORM_ADMIN"}).status_code==400

def test_dashboard_list_detail_and_export_are_tenant_scoped(mt_admin_app):
    app,ids,tokens=mt_admin_app;c=app.test_client();headers=h(tokens,"admin_a")
    assert c.get("/api/admin/dashboard",headers=headers).get_json()["total_requests"]==1
    rows=c.get("/api/admin/shipment-requests",headers=headers).get_json()["requests"]
    assert [row["id"] for row in rows]==[ids["req_a"]]
    assert c.get(f"/api/admin/shipment-requests/{ids['req_b']}",headers=headers).status_code==404
    export=c.get("/api/admin/reports/export.xlsx?period=yearly",headers=headers)
    assert export.status_code==200 and export.mimetype.endswith("sheet")

def test_manual_assignment_cannot_cross_tenant_or_change_owner(mt_admin_app):
    app,ids,tokens=mt_admin_app;c=app.test_client();headers=h(tokens,"admin_a")
    assert c.post("/api/user-management/manual-assignment",headers=headers,json={"request_id":ids["req_b"],"expert_id":ids["expert_a"]}).status_code==404
    assert c.post("/api/user-management/manual-assignment",headers=headers,json={"request_id":ids["req_a"],"expert_id":ids["expert_b"]}).status_code==404
    assert c.post("/api/user-management/manual-assignment",headers=headers,json={"request_id":ids["req_a"],"expert_id":ids["expert_a"]}).status_code==200
    with app.app_context(): assert db.session.get(ShipmentRequest,ids["req_a"]).operational_organization_id==ids["org_a"]

def test_referral_rules_and_experts_are_tenant_scoped(mt_admin_app):
    app,ids,tokens=mt_admin_app;c=app.test_client();headers=h(tokens,"admin_a")
    bad={"name":"bad","conditions":{},"action":{"type":"direct_assign","expert_id":ids["expert_b"]}}
    assert c.post("/api/admin/referral-rules",headers=headers,json=bad).status_code==400
    good={"name":"good","conditions":{},"action":{"type":"direct_assign","expert_id":ids["expert_a"]}}
    created=c.post("/api/admin/referral-rules",headers=headers,json=good);assert created.status_code==201
    assert len(c.get("/api/admin/referral-rules",headers=h(tokens,"admin_b")).get_json()["referral_rules"])==0
    assert c.post("/api/admin/referral-rules/preview",headers=headers,json={"request_id":ids["req_b"]}).status_code==404

def test_platform_global_mutations_require_platform_admin(mt_admin_app):
    app,ids,tokens=mt_admin_app;c=app.test_client();org=h(tokens,"admin_a");platform=h(tokens,"platform")
    assert c.put("/api/admin/site-settings",headers=org,json={"site_title":"no"}).status_code==403
    assert c.post("/api/admin/document-definitions",headers=org,json={}).status_code==403
    assert c.post("/api/admin/master-data/service-types",headers=org,json={}).status_code==403
    assert c.post("/api/admin/locations/provinces",headers=org,json={}).status_code==403
    assert c.put("/api/admin/site-settings",headers=platform,json={"site_title":"Platform"}).status_code==200

def test_tenant_delete_is_non_disclosing_and_does_not_touch_other_org(mt_admin_app):
    app,ids,tokens=mt_admin_app;c=app.test_client();headers=h(tokens,"admin_a")
    assert c.delete(f"/api/user-management/users/{ids['expert_b']}",headers=headers).status_code==404
    assert c.delete(f"/api/user-management/users/{ids['expert_a']}",headers=headers).status_code==200
    with app.app_context():
        assert db.session.get(ExpertUser,ids["expert_b"]).is_active is True
        assert db.session.get(ShipmentRequest,ids["req_b"]).operational_organization_id==ids["org_b"]

@pytest.mark.parametrize("mode",["missing","duplicate","inactive_membership","inactive_organization"])
def test_invalid_membership_context_fails_closed_without_500(mt_admin_app,mode):
    app,ids,tokens=mt_admin_app
    with app.app_context():
        membership=OperationalMembership.query.filter_by(user_id=ids["admin_a"],organization_id=ids["org_a"]).one()
        if mode=="missing": db.session.delete(membership)
        elif mode=="duplicate": db.session.add(OperationalMembership(user_id=ids["admin_a"],organization_id=ids["org_b"],is_active=True,permissions=[]))
        elif mode=="inactive_membership": membership.is_active=False
        else: db.session.get(OperationalOrganization,ids["org_a"]).is_active=False
        db.session.commit()
    response=app.test_client().get("/api/user-management/users",headers=h(tokens,"admin_a"))
    assert response.status_code==403
