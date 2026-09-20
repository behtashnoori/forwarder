from backend.extensions import db
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import Country, ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.tests.test_execution_units import eu_app  # noqa: F401


def _private_point(app, *, organization_id, actor_id, code, name, active=True):
    with app.app_context():
        country = Country.query.filter_by(code="IR").one_or_none()
        if country is None:
            country = Country(code="IR", name_en="Iran", name_fa="ایران")
            db.session.add(country)
            db.session.flush()
        point_type = LogisticsPointType.query.filter_by(
            immutable_code="WAREHOUSE"
        ).one_or_none()
        if point_type is None:
            point_type = LogisticsPointType(
                immutable_code="WAREHOUSE",
                fa_name="انبار",
                en_name="Warehouse",
                created_by=actor_id,
                updated_by=actor_id,
            )
            db.session.add(point_type)
            db.session.flush()
        row = LogisticsPoint(
            organization_id=organization_id,
            immutable_code=code,
            logistics_point_type_id=point_type.id,
            fa_name=name,
            en_name=f"{name} EN",
            normalized_name=name.casefold(),
            country_id=country.id,
            geography_key=f"IR:{code}",
            is_active=active,
            created_by=actor_id,
            updated_by=actor_id,
        )
        db.session.add(row)
        db.session.commit()
        return row.public_id


def _identities(app):
    with app.app_context():
        actor = ExpertUser.query.filter_by(username="eu-user").one()
        membership = OperationalMembership.query.filter_by(user_id=actor.id).one()
        other = OperationalOrganization.query.filter(
            OperationalOrganization.id != membership.organization_id
        ).one()
        return actor.id, membership.organization_id, other.id


def test_execution_authority_sees_only_active_same_tenant_private_points(eu_app):
    app, ctx = eu_app
    actor_id, organization_id, other_id = _identities(app)
    same_id = _private_point(
        app,
        organization_id=organization_id,
        actor_id=actor_id,
        code="B7-SAME",
        name="انبار خصوصی ب۷",
    )
    _private_point(
        app,
        organization_id=other_id,
        actor_id=actor_id,
        code="B7-FOREIGN",
        name="انبار سازمان دیگر",
    )
    inactive_id = _private_point(
        app,
        organization_id=organization_id,
        actor_id=actor_id,
        code="B7-INACTIVE",
        name="انبار غیرفعال",
        active=False,
    )

    endpoint = "/api/internal/logistics-points/tracking-selector"
    with app.test_client() as client:
        response = client.get(endpoint, headers=ctx["auth"])
        assert response.status_code == 200
        payload = response.get_json()
        assert [item["public_id"] for item in payload["items"]] == [same_id]
        assert payload["items"][0]["selector_kind"] == "organization_private"
        assert "organization_id" not in payload["items"][0]
        assert client.get(f"{endpoint}?q=B7-SAME", headers=ctx["auth"]).get_json()[
            "items"
        ][0]["public_id"] == same_id
        assert client.get(
            f"{endpoint}?organization_id={other_id}", headers=ctx["auth"]
        ).status_code == 403

    with app.app_context():
        inactive_point = LogisticsPoint.query.filter_by(public_id=inactive_id).one()
        assert inactive_point.is_active is False
        membership = OperationalMembership.query.filter_by(user_id=actor_id).one()
        membership.is_active = False
        db.session.commit()
    with app.test_client() as client:
        denied = client.get(endpoint, headers=ctx["auth"])
        assert denied.status_code in {401, 403}
        assert same_id not in denied.get_data(as_text=True)

    with app.app_context():
        membership = OperationalMembership.query.filter_by(user_id=actor_id).one()
        membership.is_active = True
        actor = db.session.get(ExpertUser, actor_id)
        actor.is_active = False
        db.session.commit()
    with app.test_client() as client:
        denied = client.get(endpoint, headers=ctx["auth"])
        assert denied.status_code == 401
        assert same_id not in denied.get_data(as_text=True)

    with app.app_context():
        actor = db.session.get(ExpertUser, actor_id)
        actor.is_active = True
        organization = db.session.get(OperationalOrganization, organization_id)
        organization.is_active = False
        db.session.commit()
    with app.test_client() as client:
        denied = client.get(endpoint, headers=ctx["auth"])
        assert denied.status_code == 403
        assert same_id not in denied.get_data(as_text=True)


def test_private_point_event_identity_round_trips_and_snapshot_survives_deactivation(
    eu_app,
):
    app, ctx = eu_app
    actor_id, organization_id, other_id = _identities(app)
    point_id = _private_point(
        app,
        organization_id=organization_id,
        actor_id=actor_id,
        code="B7-ROUNDTRIP",
        name="انبار تاریخی ب۷",
    )
    foreign_id = _private_point(
        app,
        organization_id=other_id,
        actor_id=actor_id,
        code="B7-GUESSED",
        name="انبار حدس‌زده‌شده",
    )

    with app.test_client() as client:
        unit = client.post(
            f"/api/v2/projects/{ctx['project']}/execution-units",
            headers=ctx["auth"],
            json={"unit_type": "road", "display_name": "B7 unit"},
        ).get_json()["data"]
        event_url = (
            f"/api/v2/projects/{ctx['project']}/execution-units/"
            f"{unit['public_id']}/events"
        )
        created = client.post(
            event_url,
            headers={**ctx["auth"], "Idempotency-Key": "b7-private-point"},
            json={
                "expected_version": unit["version"],
                "event_type": "unit_updated",
                "lifecycle_status": "in_progress",
                "visibility": "customer",
                "customer_message": "در محل عملیاتی",
                "location": {"logistics_point_public_id": point_id},
            },
        )
        assert created.status_code == 201
        internal = client.get(
            event_url.replace("/events", "/timeline"), headers=ctx["auth"]
        ).get_json()["data"][0]
        assert internal["location"]["source_type"] == "logistics_point"
        assert internal["location"]["source_identity"] == point_id
        assert internal["location"]["display_name"] == "انبار تاریخی ب۷"

        second = client.post(
            f"/api/v2/projects/{ctx['project']}/execution-units",
            headers=ctx["auth"],
            json={"unit_type": "road", "display_name": "B7 denied unit"},
        ).get_json()["data"]
        denied = client.post(
            f"/api/v2/projects/{ctx['project']}/execution-units/{second['public_id']}/events",
            headers={**ctx["auth"], "Idempotency-Key": "b7-foreign-point"},
            json={
                "expected_version": second["version"],
                "visibility": "internal",
                "location": {"logistics_point_public_id": foreign_id},
            },
        )
        assert denied.status_code == 404

    with app.app_context():
        point = LogisticsPoint.query.filter_by(public_id=point_id).one()
        point.fa_name = "نام جدید که نباید تاریخ را عوض کند"
        point.is_active = False
        db.session.commit()

    with app.test_client() as client:
        historical = client.get(
            event_url.replace("/events", "/timeline"), headers=ctx["auth"]
        ).get_json()["data"][0]
        assert historical["location"]["source_identity"] == point_id
        assert historical["location"]["display_name"] == "انبار تاریخی ب۷"
        public = client.get(
            f"/api/public/v2/projects/{ctx['tracking']}/execution-units/"
            f"{unit['public_id']}/timeline"
        ).get_json()["data"][0]
        assert public["location"]["display_name"] == "انبار تاریخی ب۷"
        serialized = str(public)
        assert "organization_id" not in serialized
        assert "B7-ROUNDTRIP" not in serialized
