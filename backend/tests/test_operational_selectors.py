"""Governed selector contracts for operational shipment creation."""

from datetime import datetime, timedelta, timezone
import os

import pytest
from sqlalchemy.engine import make_url

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import Customer, ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    Project,
)
from backend.services import operational_service


@pytest.fixture()
def selector_app():
    database_url = os.environ.get(
        "FORWARDER_SELECTOR_POSTGRES_URL", "sqlite:///:memory:"
    )
    if database_url.startswith("postgresql"):
        parsed = make_url(database_url)
        assert parsed.host in {"127.0.0.1", "localhost"}
        assert (parsed.database or "").startswith("forwarder_selector_test_")
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": database_url,
            "SECRET_KEY": "selector-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.create_all()
        org = OperationalOrganization(name="Selector Org")
        foreign_org = OperationalOrganization(name="Foreign Selector Org")
        direct_user = ExpertUser(
            username="selector-direct",
            password_hash="unused",
            full_name="Direct Creator",
            role="customer",
            is_active=True,
        )
        quote_user = ExpertUser(
            username="selector-quote",
            password_hash="unused",
            full_name="Quote Creator",
            role="customer",
            is_active=True,
        )
        legacy_user = ExpertUser(
            username="selector-legacy",
            password_hash="unused",
            full_name="Legacy Creator",
            role="customer",
            is_active=True,
        )
        denied_user = ExpertUser(
            username="selector-denied",
            password_hash="unused",
            full_name="Denied Creator",
            role="admin",
            is_active=True,
        )
        db.session.add_all(
            [org, foreign_org, direct_user, quote_user, legacy_user, denied_user]
        )
        db.session.flush()
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org.id,
                    user_id=direct_user.id,
                    permissions=["operational_shipment.create_direct"],
                ),
                OperationalMembership(
                    organization_id=org.id,
                    user_id=quote_user.id,
                    permissions=["operational_shipment.create_from_quote"],
                ),
                OperationalMembership(
                    organization_id=org.id,
                    user_id=legacy_user.id,
                    permissions=["operational_shipment.create"],
                ),
                OperationalMembership(
                    organization_id=org.id,
                    user_id=denied_user.id,
                    permissions=["operational_shipment.read"],
                ),
            ]
        )
        alpha = Customer(
            first_name="Alpha",
            last_name="Owner",
            company_name="Alpha Logistics",
            email="private@example.test",
            phone="09000000001",
            status="active",
        )
        beta = Customer(first_name="Beta", last_name="Owner", status="active")
        inactive = Customer(first_name="Inactive", last_name="Owner", status="inactive")
        db.session.add_all([alpha, beta, inactive])
        db.session.flush()
        local_project = Project(
            organization_id=org.id,
            primary_customer_id=alpha.id,
            project_code="LOCAL-1",
            created_by_user_id=direct_user.id,
        )
        completed_project = Project(
            organization_id=org.id,
            primary_customer_id=alpha.id,
            project_code="DONE-1",
            lifecycle_status="completed",
            created_by_user_id=direct_user.id,
        )
        foreign_project = Project(
            organization_id=foreign_org.id,
            primary_customer_id=alpha.id,
            project_code="FOREIGN-1",
            created_by_user_id=direct_user.id,
        )
        origin = Province(name_fa="Origin", code="SEL-O")
        destination = Province(name_fa="Destination", code="SEL-D")
        db.session.add_all(
            [local_project, completed_project, foreign_project, origin, destination]
        )
        db.session.flush()

        def request(customer_id, tracking_code):
            row = ShipmentRequest(
                contact_phone="09000000009",
                tracking_code=tracking_code,
                customer_id=customer_id,
                status="waiting_for_customer",
                status_request_status="new",
                origin_city_international="Origin",
                dest_city_international="Destination",
            )
            db.session.add(row)
            db.session.flush()
            return row

        eligible_request = request(alpha.id, "REQ-ELIGIBLE")
        converted_request = request(alpha.id, "REQ-CONVERTED")
        incomplete_request = request(None, "REQ-INCOMPLETE")
        foreign_request = request(alpha.id, "REQ-FOREIGN")
        now = datetime.now(timezone.utc)

        def quote(request_row, organization_id, response="accepted"):
            row = ExpertQuote(
                shipment_request_id=request_row.id,
                amount=100,
                currency="IRR",
                created_by_expert_id=quote_user.id,
                created_at=now,
                customer_response=response,
                responded_at=now,
                operational_organization_id=organization_id,
            )
            db.session.add(row)
            db.session.flush()
            return row

        eligible_quote = quote(eligible_request, org.id)
        converted_quote = quote(converted_request, org.id)
        quote(incomplete_request, org.id)
        quote(eligible_request, org.id, "declined")
        quote(foreign_request, foreign_org.id)
        db.session.add(
            OperationalShipment(
                organization_id=org.id,
                source_type="accepted_quote",
                customer_id=alpha.id,
                shipment_request_id=converted_request.id,
                accepted_quote_id=converted_quote.id,
                created_by_user_id=quote_user.id,
            )
        )
        db.session.commit()
        app.config["selector_ids"] = {
            "org": org.id,
            "foreign_org": foreign_org.id,
            "direct": direct_user.id,
            "quote": quote_user.id,
            "legacy": legacy_user.id,
            "denied": denied_user.id,
            "alpha": alpha.id,
            "beta": beta.id,
            "project": local_project.public_id,
            "eligible_quote": eligible_quote.id,
            "origin": origin.id,
            "destination": destination.id,
        }
    yield app
    if database_url.startswith("postgresql"):
        with app.app_context():
            db.session.remove()
            db.drop_all()


def _headers(app, user):
    with app.app_context():
        token = auth_manager.generate_tokens(app.config["selector_ids"][user])[
            "access_token"
        ]
    return {"Authorization": f"Bearer {token}"}


def test_customer_selector_is_permission_based_minimal_and_bounded(selector_app):
    client = selector_app.test_client()
    response = client.get(
        "/api/operations/selectors/customers?q=Alpha&limit=1",
        headers=_headers(selector_app, "direct"),
    )
    assert response.status_code == 200
    assert response.json["meta"] == {"count": 1, "limit": 1}
    assert response.json["items"] == [
        {
            "id": selector_app.config["selector_ids"]["alpha"],
            "label": "Alpha Logistics",
        }
    ]
    assert not {"email", "phone", "organization_id"}.intersection(
        response.json["items"][0]
    )
    denied = client.get(
        "/api/operations/selectors/customers",
        headers=_headers(selector_app, "denied"),
    )
    assert denied.status_code == 403
    invalid = client.get(
        "/api/operations/selectors/customers?limit=101",
        headers=_headers(selector_app, "direct"),
    )
    assert invalid.status_code == 422


def test_project_selector_is_tenant_scoped_and_customer_filterable(selector_app):
    client = selector_app.test_client()
    customer_id = selector_app.config["selector_ids"]["alpha"]
    response = client.get(
        f"/api/operations/selectors/projects?q=Local&customer_id={customer_id}",
        headers=_headers(selector_app, "direct"),
    )
    assert response.status_code == 200
    assert response.json["items"] == [
        {
            "public_id": selector_app.config["selector_ids"]["project"],
            "label": "LOCAL-1",
            "project_code": "LOCAL-1",
            "primary_customer_id": customer_id,
            "lifecycle_status": "not_started",
        }
    ]
    assert "organization_id" not in response.json["items"][0]
    no_match = client.get(
        f"/api/operations/selectors/projects?customer_id={selector_app.config['selector_ids']['beta']}",
        headers=_headers(selector_app, "direct"),
    )
    assert no_match.json["items"] == []


@pytest.mark.parametrize("permission_user", ["quote", "legacy"])
def test_accepted_quote_selector_permissions_eligibility_and_create_consistency(
    selector_app, permission_user
):
    client = selector_app.test_client()
    response = client.get(
        "/api/operations/selectors/accepted-quotes?q=ELIGIBLE",
        headers=_headers(selector_app, permission_user),
    )
    assert response.status_code == 200
    assert len(response.json["items"]) == 1
    item = response.json["items"][0]
    assert item["id"] == selector_app.config["selector_ids"]["eligible_quote"]
    assert item["request_public_id"] == "REQ-ELIGIBLE"
    assert set(item) == {
        "id",
        "request_public_id",
        "customer_label",
        "route_label",
        "quote_label",
        "accepted_at",
    }
    if permission_user == "quote":
        with selector_app.app_context():
            now = datetime.now(timezone.utc)
            payload = {
                "accepted_quote_id": item["id"],
                "origin": {
                    "source_type": "province",
                    "source_id": selector_app.config["selector_ids"]["origin"],
                },
                "destination": {
                    "source_type": "province",
                    "source_id": selector_app.config["selector_ids"]["destination"],
                },
                "transport_mode": "road",
                "planned_departure": now.isoformat(),
                "planned_arrival": (now + timedelta(hours=1)).isoformat(),
            }
            shipment, created = operational_service.create_from_accepted_quote(
                payload,
                {"id": selector_app.config["selector_ids"]["quote"]},
                "selector-consistency",
            )
            assert created and shipment.accepted_quote_id == item["id"]
        after = client.get(
            "/api/operations/selectors/accepted-quotes",
            headers=_headers(selector_app, "quote"),
        )
        assert after.json["items"] == []


def test_direct_permission_does_not_grant_quote_selector_and_membership_is_exact(
    selector_app,
):
    client = selector_app.test_client()
    forbidden = client.get(
        "/api/operations/selectors/accepted-quotes",
        headers=_headers(selector_app, "direct"),
    )
    assert forbidden.status_code == 403
    with selector_app.app_context():
        ids = selector_app.config["selector_ids"]
        db.session.add(
            OperationalMembership(
                organization_id=ids["foreign_org"],
                user_id=ids["direct"],
                permissions=["operational_shipment.create_direct"],
            )
        )
        db.session.commit()
    ambiguous = client.get(
        "/api/operations/selectors/projects",
        headers=_headers(selector_app, "direct"),
    )
    assert ambiguous.status_code == 403
    assert ambiguous.json["error"]["code"] == "TENANT_SCOPE_VIOLATION"
