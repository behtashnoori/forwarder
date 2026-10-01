"""PostgreSQL 18 proof for the governed Expert operational baseline."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

from alembic import command
import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade
from backend.models import Customer, ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import (
    Milestone,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    RouteLeg,
    RoutePlan,
)
from backend.services import operational_service
from backend.services.assigned_work_authorization import authorize_document_management
from backend.services.expert_scope_service import (
    EXPERT_BASELINE_OPERATIONAL_PERMISSIONS,
    reconcile_expert_baseline_permissions,
)


def _database_url() -> str:
    value = os.environ.get("FORWARDER_EXPERT_BASELINE_POSTGRES_URL", "")
    if not value:
        pytest.skip("explicit Expert-baseline disposable PostgreSQL URL not provided")
    parsed = make_url(value)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert parsed.database.startswith("forwarder_expert_baseline_test_")
    return value


def _actor(user_id: int) -> dict[str, object]:
    return {"id": user_id, "role": "expert"}


def test_expert_baseline_reconciliation_and_owner_tenant_lifecycle_guards():
    database_url = _database_url()
    config = alembic_config(database_url)
    prepare_version_table_for_upgrade(database_url, config)
    command.upgrade(config, "head")
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": database_url,
            "SECRET_KEY": "expert-baseline-postgresql",
        },
        skip_startup=True,
    )

    with app.app_context():
        organization = OperationalOrganization(name="Expert Baseline PG18")
        other_organization = OperationalOrganization(name="Other Expert Baseline PG18")
        owner = ExpertUser(
            username="expert-baseline-owner",
            password_hash="unused",
            full_name="Owner Expert",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        peer = ExpertUser(
            username="expert-baseline-peer",
            password_hash="unused",
            full_name="Peer Expert",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        foreign = ExpertUser(
            username="expert-baseline-foreign",
            password_hash="unused",
            full_name="Foreign Expert",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        organization_admin = ExpertUser(
            username="expert-baseline-org-admin",
            password_hash="unused",
            full_name="Organization Admin",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        platform_admin = ExpertUser(
            username="expert-baseline-platform-admin",
            password_hash="unused",
            full_name="Platform Admin",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        db.session.add_all(
            [
                organization,
                other_organization,
                owner,
                peer,
                foreign,
                organization_admin,
                platform_admin,
            ]
        )
        db.session.flush()
        owner_original = [
            "custom.explicit",
            "operational_shipment.create",
            "operational_shipment.create_from_quote",
            "operational_shipment.read",
        ]
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=organization.id,
                    user_id=owner.id,
                    permissions=owner_original,
                ),
                OperationalMembership(
                    organization_id=organization.id,
                    user_id=peer.id,
                    permissions=list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS),
                ),
                OperationalMembership(
                    organization_id=other_organization.id,
                    user_id=foreign.id,
                    permissions=list(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS),
                ),
                OperationalMembership(
                    organization_id=organization.id,
                    user_id=organization_admin.id,
                    permissions=["closure_policy.manage", "shipment_stage.manage"],
                ),
                OperationalMembership(
                    organization_id=organization.id,
                    user_id=platform_admin.id,
                    permissions=["platform_governance.manage"],
                ),
            ]
        )
        origin = Province(name_fa="PG18 Origin", code="EBO")
        destination = Province(name_fa="PG18 Destination", code="EBD")
        customer = Customer(
            first_name="Expert",
            last_name="Baseline",
            status="active",
            ownership_scope="TENANT",
            operational_organization_id=organization.id,
        )
        db.session.add_all([origin, destination, customer])
        db.session.flush()
        request = ShipmentRequest(
            contact_phone="09000000018",
            status="waiting_for_customer",
            status_request_status="new",
            assigned_to=owner.id,
            customer_id=customer.id,
            ownership_scope="TENANT",
            operational_organization_id=organization.id,
        )
        db.session.add(request)
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=request.id,
            amount=18,
            currency="IRR",
            created_by_expert_id=owner.id,
            created_at=datetime.now(timezone.utc),
            customer_response="accepted",
            responded_at=datetime.now(timezone.utc),
            operational_organization_id=organization.id,
        )
        db.session.add(quote)
        db.session.commit()

        dry_run = reconcile_expert_baseline_permissions()
        assert dry_run["mode"] == "dry-run"
        assert dry_run["changed_memberships"] == 1
        owner_membership = OperationalMembership.query.filter_by(user_id=owner.id).one()
        assert owner_membership.permissions == owner_original

        applied = reconcile_expert_baseline_permissions(apply=True)
        db.session.commit()
        assert applied["changed_memberships"] == 1
        assert set(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS).issubset(
            owner_membership.permissions
        )
        assert "custom.explicit" in owner_membership.permissions
        assert reconcile_expert_baseline_permissions(apply=True)["changed_memberships"] == 0
        assert owner.role == "expert" and owner.authority == "EXPERT"
        assert OperationalMembership.query.filter_by(
            user_id=organization_admin.id
        ).one().permissions == ["closure_policy.manage", "shipment_stage.manage"]
        assert OperationalMembership.query.filter_by(
            user_id=platform_admin.id
        ).one().permissions == ["platform_governance.manage"]

        payload = {
            "accepted_quote_id": quote.id,
            "planned_departure": (
                datetime.now(timezone.utc) - timedelta(hours=2)
            ).isoformat(),
            "planned_arrival": (
                datetime.now(timezone.utc) + timedelta(hours=2)
            ).isoformat(),
            "origin": {"source_type": "province", "source_id": origin.id},
            "destination": {
                "source_type": "province",
                "source_id": destination.id,
            },
            "transport_mode": "road",
        }
        shipment, created = operational_service.create_from_accepted_quote(
            payload, _actor(owner.id), "expert-baseline-pg18-shipment"
        )
        assert created is True
        assert shipment.primary_responsible_expert_id == owner.id
        departure = db.session.scalar(
            select(Milestone)
            .join(RouteLeg, Milestone.route_leg_id == RouteLeg.id)
            .join(RoutePlan, RouteLeg.route_plan_id == RoutePlan.id)
            .where(
                RoutePlan.operational_shipment_id == shipment.id,
                Milestone.milestone_type == "departure",
            )
        )
        event = operational_service.record_event(
            shipment.id,
            departure.id,
            {"occurred_at": datetime.now(timezone.utc).isoformat()},
            _actor(owner.id),
            "expert-baseline-pg18-departure",
        )
        assert event.event_type == "reported"

        assert authorize_document_management(_actor(owner.id), shipment).allowed
        assert not authorize_document_management(_actor(peer.id), shipment).allowed
        assert not authorize_document_management(_actor(foreign.id), shipment).allowed
        assert not authorize_document_management(
            _actor(organization_admin.id), shipment
        ).allowed
        assert not authorize_document_management(_actor(platform_admin.id), shipment).allowed

        arrival = db.session.scalar(
            select(Milestone)
            .join(RouteLeg, Milestone.route_leg_id == RouteLeg.id)
            .join(RoutePlan, RouteLeg.route_plan_id == RoutePlan.id)
            .where(
                RoutePlan.operational_shipment_id == shipment.id,
                Milestone.milestone_type == "arrival",
            )
        )
        for actor_id in (peer.id, foreign.id):
            with pytest.raises(operational_service.OperationalError) as denied:
                operational_service.record_event(
                    shipment.id,
                    arrival.id,
                    {"occurred_at": datetime.now(timezone.utc).isoformat()},
                    _actor(actor_id),
                    f"expert-baseline-pg18-denied-{actor_id}",
                )
            assert denied.value.status in {403, 404}
            db.session.rollback()

        shipment = db.session.get(OperationalShipment, shipment.id)
        shipment.lifecycle_status = "cancelled"
        route_leg = db.session.get(RouteLeg, arrival.route_leg_id)
        route_leg.status = "cancelled"
        db.session.commit()
        with pytest.raises(operational_service.OperationalError) as lifecycle_denied:
            operational_service.record_event(
                shipment.id,
                arrival.id,
                {"occurred_at": datetime.now(timezone.utc).isoformat()},
                _actor(owner.id),
                "expert-baseline-pg18-cancelled-arrival",
            )
        assert lifecycle_denied.value.code == "INVALID_LEG_TRANSITION"
        db.session.rollback()

        forbidden_baseline = {
            "checkpoint.verify",
            "closure_policy.manage",
            "document_policy.manage",
            "logistics_point.manage",
            "milestone.correct",
            "milestone.verify",
            "operational_event.correct",
            "operational_event.verify",
            "platform_governance.manage",
            "shipment_owner.transfer",
            "shipment_stage.manage",
            "user.manage",
        }
        assert forbidden_baseline.isdisjoint(EXPERT_BASELINE_OPERATIONAL_PERMISSIONS)
