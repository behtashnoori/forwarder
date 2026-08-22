"""ADR-041 Phase 4A explicit operational materialization contract."""
from backend.extensions import db
from backend.global_logistics_point_models import GlobalLogisticsPoint
from backend.logistics_network_models import LogisticsPoint
from backend.tests.test_global_logistics_point_adoptions import adoption_app  # noqa: F401


def _adopt(client, c, who="a"):
    return client.post(f"/api/admin/global-logistics-points/{c['active']}/adopt",
                       headers=c[who], json={"display_label":"Tenant Port"}).get_json()["item"]


def test_materialize_valid_idempotent_and_provenance(adoption_app):
    app,c=adoption_app
    with app.test_client() as client:
        adoption=_adopt(client,c)
        url=f"/api/admin/global-logistics-point-adoptions/{adoption['public_id']}/materialize"
        created=client.post(url,headers=c["a"],json={"immutable_code":"A-OP-PORT"})
        assert created.status_code==201
        item=created.get_json()["item"]
        assert item["materialization_state"]=="MATERIALIZED" and item["version"]==1
        repeated=client.post(url,headers=c["a"],json={"immutable_code":"IGNORED-IDEMPOTENT"})
        assert repeated.status_code==200
        assert repeated.get_json()["item"]["logistics_point_public_id"]==item["logistics_point_public_id"]
        detail=client.get(f"/api/admin/logistics-points/{item['logistics_point_public_id']}",headers=c["a"]).get_json()["item"]
        assert detail["immutable_code"]=="A-OP-PORT"
        assert detail["global_source"]["adoption_public_id"]==adoption["public_id"]
        with app.app_context():
            row=db.session.query(LogisticsPoint).one()
            assert row.organization_id==c["org_a"] and row.global_adoption_id and row.global_logistics_point_id


def test_materialization_eligibility_tenant_scope_and_strict_payload(adoption_app):
    app,c=adoption_app
    with app.test_client() as client:
        adoption=_adopt(client,c)
        url=f"/api/admin/global-logistics-point-adoptions/{adoption['public_id']}/materialize"
        assert client.post(url,headers=c["b"],json={"immutable_code":"B-X"}).status_code==404
        assert client.post(url,headers=c["expert"],json={"immutable_code":"X"}).status_code==403
        assert client.post(url,headers=c["platform"],json={"immutable_code":"X"}).status_code==403
        for payload in ({},{"immutable_code":"X","organization_id":c["org_b"]},
                        {"immutable_code":"X","created_by":999}):
            assert client.post(url,headers=c["a"],json=payload).status_code==400
        client.post(f"/api/admin/global-logistics-point-adoptions/{adoption['public_id']}/deactivate",
                    headers=c["a"],json={"version":1})
        assert client.post(url,headers=c["a"],json={"immutable_code":"A-X"}).status_code==409


def test_deprecation_and_adoption_deactivation_preserve_materialized_point_without_sync(adoption_app):
    app,c=adoption_app
    with app.test_client() as client:
        adoption=_adopt(client,c)
        url=f"/api/admin/global-logistics-point-adoptions/{adoption['public_id']}"
        point=client.post(f"{url}/materialize",headers=c["a"],json={"immutable_code":"A-STABLE"}).get_json()["item"]
        client.post(f"{url}/deactivate",headers=c["a"],json={"version":1})
        with app.app_context():
            global_row=db.session.query(GlobalLogisticsPoint).filter_by(public_id=c["active"]).one()
            global_row.lifecycle_status="DEPRECATED"; global_row.fa_name="Platform Changed"
            db.session.commit()
        tenant=client.get(f"/api/admin/logistics-points/{point['logistics_point_public_id']}",headers=c["a"]).get_json()["item"]
        assert tenant["fa_name"]=="Tenant Port" and tenant["is_active"] is True
        assert tenant["global_source"]["platform_lifecycle_status"]=="DEPRECATED"
        assert tenant["global_source"]["adoption_status"]=="INACTIVE"


def test_adoption_does_not_automatically_materialize(adoption_app):
    app,c=adoption_app
    with app.test_client() as client: _adopt(client,c)
    with app.app_context(): assert db.session.query(LogisticsPoint).count()==0
