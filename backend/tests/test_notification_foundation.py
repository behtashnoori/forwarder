"""Focused contract tests for the inactive notification foundation."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import Customer, CustomerGamification, ExpertUser, ShipmentRequest
from backend.notification_models import NotificationAction, NotificationAttempt
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    OperationalOutbox,
    Project,
)


@pytest.fixture()
def foundation_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "phase-c1-foundation-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        db.session.execute(text("PRAGMA foreign_keys=ON"))
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _organization(name: str) -> OperationalOrganization:
    row = OperationalOrganization(name=name)
    db.session.add(row)
    db.session.flush()
    return row


def test_action_attempt_identity_defaults_relationship_and_neutrality(foundation_app):
    with foundation_app.app_context():
        organization = _organization("C1 tenant")
        event = OperationalOutbox(
            organization_id=organization.id,
            event_type="synthetic.foundation.reference.v1",
            aggregate_type="Synthetic",
            aggregate_id=1,
            payload={},
        )
        db.session.add(event)
        db.session.flush()
        action = NotificationAction(
            organization_id=organization.id,
            source_event_id=event.id,
            idempotency_key="c1-action-1",
            correlation_key="c1-correlation-1",
            purpose="SYNTHETIC_FOUNDATION_PROOF",
        )
        db.session.add(action)
        db.session.flush()

        assert action.public_id
        assert action.status == "PENDING"
        assert action.recipient_reference is None
        assert action.channel is None
        assert action.created_at is not None
        assert action.updated_at is not None

        attempt = NotificationAttempt(
            organization_id=organization.id,
            action_id=action.id,
            attempt_number=1,
        )
        db.session.add(attempt)
        db.session.commit()

        assert attempt.public_id
        assert attempt.status == "PENDING"
        assert attempt.channel is None
        assert attempt.provider is None
        assert attempt.provider_reference is None
        assert attempt.attempted_at is None
        assert attempt.delivered_at is None
        assert action.attempts == [attempt]
        assert attempt.action is action


def test_identity_idempotency_attempt_number_and_audit_delete_are_constrained(
    foundation_app,
):
    with foundation_app.app_context():
        organization = _organization("C1 constrained tenant")
        action = NotificationAction(
            organization_id=organization.id,
            idempotency_key="same-logical-action",
            purpose="SYNTHETIC_FOUNDATION_PROOF",
        )
        db.session.add(action)
        db.session.commit()

        duplicate = NotificationAction(
            organization_id=organization.id,
            idempotency_key="same-logical-action",
            purpose="SYNTHETIC_FOUNDATION_PROOF",
        )
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        invalid_attempt = NotificationAttempt(
            organization_id=organization.id,
            action_id=action.id,
            attempt_number=0,
        )
        db.session.add(invalid_attempt)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        attempt = NotificationAttempt(
            organization_id=organization.id,
            action_id=action.id,
            attempt_number=1,
        )
        db.session.add(attempt)
        db.session.commit()

        db.session.delete(action)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        assert NotificationAction.query.count() == 1
        assert NotificationAttempt.query.count() == 1


def test_existing_quote_response_and_execution_event_do_not_activate_foundation(
    foundation_app,
):
    with foundation_app.app_context():
        organization = _organization("C1 inactive tenant")
        expert = ExpertUser(
            username="phase-c1-expert",
            password_hash="synthetic-unusable",
            full_name="Phase C1 Expert",
            role="manager",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        gamification_customer = CustomerGamification(
            email="phase-c1@example.test", phone="09120000001"
        )
        project_customer = Customer(first_name="C1", last_name="Customer")
        db.session.add_all([expert, gamification_customer, project_customer])
        db.session.flush()
        db.session.add(
            OperationalMembership(
                organization_id=organization.id,
                user_id=expert.id,
                permissions=[
                    "request.quote",
                    "execution_unit.read",
                    "execution_unit.create",
                    "execution_unit.update",
                ],
            )
        )
        request_row = ShipmentRequest(
            ownership_scope="TENANT",
            operational_organization_id=organization.id,
            tracking_code="SR-PHASE-C1-INACTIVE",
            shipping_type="domestic",
            contact_phone=gamification_customer.phone,
            gamification_customer_id=gamification_customer.id,
            status="in_progress",
            status_request_status="in_progress",
            assigned_to=expert.id,
        )
        project = Project(
            organization_id=organization.id,
            primary_customer_id=project_customer.id,
            project_code="PHASE-C1-INACTIVE",
            tracking_code="phase-c1-public-tracking",
            created_by_user_id=expert.id,
        )
        db.session.add_all([request_row, project])
        db.session.commit()
        access_token = auth_manager.generate_tokens(expert.id)["access_token"]
        request_id = request_row.id
        request_tracking_code = request_row.tracking_code
        project_public_id = project.public_id

    headers = {"Authorization": f"Bearer {access_token}"}
    with foundation_app.test_client() as client:
        quote = client.post(
            f"/api/expert/requests/{request_id}/quote",
            headers=headers,
            json={
                "amount": 125000,
                "currency": "EUR",
                "valid_until": (date.today() + timedelta(days=3)).isoformat(),
            },
        )
        assert quote.status_code == 200
        response = client.post(
            f"/api/customer/quote-response/{request_tracking_code}",
            json={"response": "accepted"},
        )
        assert response.status_code == 404

        unit = client.post(
            f"/api/v2/projects/{project_public_id}/execution-units",
            headers=headers,
            json={"unit_type": "road", "display_name": "C1 truck"},
        )
        assert unit.status_code == 201
        unit_data = unit.get_json()["data"]
        event = client.post(
            f"/api/v2/projects/{project_public_id}/execution-units/"
            f"{unit_data['public_id']}/events",
            headers={**headers, "Idempotency-Key": "phase-c1-inactive-event"},
            json={
                "expected_version": unit_data["version"],
                "event_type": "unit_updated",
                "lifecycle_status": "in_progress",
                "visibility": "customer",
                "customer_message": "Synthetic C1 progress",
            },
        )
        assert event.status_code == 201

    with foundation_app.app_context():
        assert NotificationAction.query.count() == 0
        assert NotificationAttempt.query.count() == 0
