"""ADR-041 explicit materialization and Phase 4B consumption contracts."""
from datetime import datetime, timedelta

import pytest

from backend.extensions import db
from backend.global_logistics_point_models import GlobalLogisticsPoint
from backend.logistics_network_models import LogisticsPoint, ProjectLogisticsPoint
from backend.models import (
    Customer, ShipmentRequest, ShipmentTransportUnit, TrackingLocationReference,
)
from backend.operational_models import Project
from backend.services.multi_unit_tracking_service import (
    TrackingValidationError, add_unit, add_update, enable_tracking,
)
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


def test_phase4b_materialized_point_uses_ordinary_tracking_and_project_contracts(adoption_app):
    app, c = adoption_app
    with app.test_client() as client:
        adoption_a = _adopt(client, c)
        materialized_a = client.post(
            f"/api/admin/global-logistics-point-adoptions/{adoption_a['public_id']}/materialize",
            headers=c["a"], json={"immutable_code": "A-GLOBAL-PORT"},
        ).get_json()["item"]
        adoption_b = _adopt(client, c, "b")
        materialized_b = client.post(
            f"/api/admin/global-logistics-point-adoptions/{adoption_b['public_id']}/materialize",
            headers=c["b"], json={"immutable_code": "B-GLOBAL-PORT"},
        ).get_json()["item"]

        with app.app_context():
            organization_only = LogisticsPoint(
                organization_id=c["org_a"], immutable_code="A-PRIVATE-PORT",
                logistics_point_type_id=c["point_type_id"], fa_name="Private Port",
                en_name="Private Port", normalized_name="private port",
                country_id=c["country_id"], geography_key="XZ:private",
                created_by=c["admin_a_id"], updated_by=c["admin_a_id"],
            )
            customer = Customer(
                operational_organization_id=c["org_a"], ownership_scope="TENANT",
                first_name="Phase", last_name="Four B",
            )
            db.session.add_all([organization_only, customer]); db.session.flush()
            project = Project(
                organization_id=c["org_a"], primary_customer_id=customer.id,
                project_code="P4B", tracking_code="p4b-project",
                created_by_user_id=c["admin_a_id"],
            )
            request = ShipmentRequest(
                ownership_scope="TENANT", operational_organization_id=c["org_a"],
                contact_phone="09120000000", status="won", status_request_status="new",
                tracking_code="p4b-tracking",
            )
            legacy = TrackingLocationReference(
                internal_key="p4b-legacy", name_fa="Legacy Point", country_code="XZ",
                location_type="other", reference_status="internal_reference",
            )
            db.session.add_all([project, request, legacy]); db.session.commit()
            project_public_id = project.public_id
            request_id = request.id
            private_public_id = organization_only.public_id
            legacy_id = legacy.id

        selector = client.get(
            "/api/internal/logistics-points/tracking-selector", headers=c["expert"]
        )
        selected_ids = {item["public_id"] for item in selector.get_json()["items"]}
        assert selected_ids == {materialized_a["logistics_point_public_id"], private_public_id}
        assert materialized_b["logistics_point_public_id"] not in selected_ids

        project_url = f"/api/v2/projects/{project_public_id}/logistics-points"
        for sequence, point_id in enumerate(
            (materialized_a["logistics_point_public_id"], private_public_id), 1
        ):
            response = client.post(project_url, headers=c["a"], json={
                "logistics_point_public_id": point_id, "project_role": "INTERMEDIATE",
                "sequence_number": sequence,
            })
            assert response.status_code == 201
        foreign = client.post(project_url, headers=c["a"], json={
            "logistics_point_public_id": materialized_b["logistics_point_public_id"],
            "project_role": "DESTINATION", "sequence_number": 3,
        })
        assert foreign.status_code == 404

        with app.app_context():
            request = db.session.get(ShipmentRequest, request_id)
            unit = add_unit(enable_tracking(request, c["expert_id"]), c["expert_id"],
                            unit_code="P4B-U", unit_type="truck")
            update = add_update(
                unit, c["expert_id"], status="in_transit",
                occurred_at=datetime.utcnow() - timedelta(minutes=1),
                logistics_point_public_id=materialized_a["logistics_point_public_id"],
            )
            db.session.commit()
            unit_id = unit.id
            tenant_point = db.session.scalar(db.select(LogisticsPoint).where(
                LogisticsPoint.public_id == materialized_a["logistics_point_public_id"]
            ))
            assert update.logistics_point_id == tenant_point.id
            assert update.location_name_snapshot == tenant_point.fa_name
            assert update.country_code_snapshot == "XZ"
            assert update.location_type_code_snapshot == "PORT"
            assert update.location_city_name_snapshot is None
            assert db.session.query(ProjectLogisticsPoint).count() == 2

            tenant_point.global_point.lifecycle_status = "DEPRECATED"
            tenant_point.global_adoption.status = "INACTIVE"
            db.session.commit()

        still_visible = client.get(
            "/api/internal/logistics-points/tracking-selector", headers=c["expert"]
        ).get_json()["items"]
        assert materialized_a["logistics_point_public_id"] in {x["public_id"] for x in still_visible}

        with app.app_context():
            tenant_point = db.session.scalar(db.select(LogisticsPoint).where(
                LogisticsPoint.public_id == materialized_a["logistics_point_public_id"]
            ))
            tenant_point.is_active = False
            db.session.commit()
            unit = db.session.get(ShipmentTransportUnit, unit_id)
            with pytest.raises(TrackingValidationError, match="active logistics point"):
                add_update(unit, c["expert_id"], status="in_transit",
                           occurred_at=datetime.utcnow() - timedelta(seconds=1),
                           logistics_point_public_id=tenant_point.public_id)
            assert db.session.query(ProjectLogisticsPoint).count() == 2
            assert unit.updates[0].location_name_snapshot == "Tenant Port"
            add_update(unit, c["expert_id"], status="in_transit",
                       occurred_at=datetime.utcnow() - timedelta(seconds=1),
                       location_reference_id=legacy_id)
