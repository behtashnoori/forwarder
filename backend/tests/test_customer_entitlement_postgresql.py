"""Owned PostgreSQL 18 migration, isolation and concurrent DN10 commands."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import os
from uuid import uuid4

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.customer_entitlement_models import CustomerEntitlement
from backend.migration_runtime import alembic_config
from backend.models import Customer, CustomerGamification, ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalShipment
from backend.services import customer_entitlement_service as service
from backend.tests.test_phase3_transport_execution_postgresql import _seed_runtime

URL = os.environ.get("DN10_POSTGRES_URL", "")
PARENT = "20261005_phase3_contextual_documents"
HEAD = "20261006_customer_entitlement"
pytestmark = pytest.mark.skipif(not URL, reason="requires owned DN10_POSTGRES_URL")


def test_postgresql18_legacy_roundtrip_tenant_constraints_and_concurrent_grants():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql" and parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_cert_dn10_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) < 190000
    config = alembic_config(URL)
    command.upgrade(config, PARENT)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": URL,
                      "SECRET_KEY": "synthetic-dn10-pg"}, skip_startup=True)
    with app.app_context():
        state = _seed_runtime(app)
        shipment = OperationalShipment.query.filter_by(public_id=state["shipment"]).one()
        org = shipment.organization_id
        admin = ExpertUser(username="dn10-admin", password_hash="unused", full_name="Admin",
                           role="admin", authority="ORGANIZATION_ADMIN", is_active=True)
        account = CustomerGamification(email="dn10-match@example.test", phone="09120000001",
                                       operational_organization_id=org)
        db.session.add_all([admin, account])
        db.session.flush()
        db.session.add(OperationalMembership(organization_id=org, user_id=admin.id, permissions=[]))
        crm = db.session.get(Customer, state["carrier"])
        crm.email, crm.phone = account.email, account.phone
        db.session.add(ShipmentRequest(contact_phone=account.phone, customer_id=crm.id,
                                       gamification_customer_id=account.id, operational_organization_id=org,
                                       ownership_scope="TENANT"))
        db.session.commit()
        actor, account_id = admin.id, account.id
        payload = {"portal_account_public_id": account.public_id, "customer_id": crm.id}
        db.session.remove()
        db.engine.dispose()
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT count(*) FROM customer_entitlement")).scalar_one() == 0
        assert connection.execute(sa.text("SELECT count(*) FROM shipment_request WHERE gamification_customer_id=:id"), {"id": account_id}).scalar_one() == 1
    command.downgrade(config, PARENT)
    command.upgrade(config, HEAD)

    barrier = Barrier(2)
    def grant_once():
        with app.app_context():
            barrier.wait(timeout=15)
            try:
                return service.grant(org, actor, payload, "same-concurrent-command")
            finally:
                db.session.remove()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(grant_once) for _ in range(2)]
        results = [f.result(timeout=30) for f in futures]
    assert sorted(created for _row, created in results) == [False, True]
    grant_id = results[0][0]["public_id"]
    assert results[1][0]["public_id"] == grant_id

    barrier = Barrier(2)
    def revoke_once():
        with app.app_context():
            barrier.wait(timeout=15)
            try:
                return service.revoke(org, actor, grant_id)
            finally:
                db.session.remove()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(revoke_once) for _ in range(2)]
        revoked = [f.result(timeout=30) for f in futures]
    assert revoked[0]["revoked_at"] == revoked[1]["revoked_at"]
    with app.app_context():
        account = db.session.get(CustomerGamification, account_id)
        assert db.session.scalars(service.authorized_customer_ids(account)).all() == []
        assert service.grant(org, actor, payload, "same-concurrent-command")[0]["status"] == "REVOKED"
        fresh, created = service.grant(org, actor, payload, "explicit-regrant")
        assert created and fresh["public_id"] != grant_id
        service.revoke(org, actor, grant_id)  # delayed revoke must not revoke the new grant
        assert db.session.scalars(service.authorized_customer_ids(account)).all() == [state["carrier"]]
        for customer_id in (state["foreign_carrier"], state["carrier"]):
            with pytest.raises(sa.exc.IntegrityError):
                with db.session.begin_nested():
                    db.session.add(CustomerEntitlement(organization_id=org, portal_account_id=account_id,
                        customer_id=customer_id, command_key=str(uuid4()), granted_by=actor))
                    db.session.flush()
        assert CustomerEntitlement.query.count() == 2
        db.session.remove()
        db.engine.dispose()
    with pytest.raises(RuntimeError, match="entitlement history exists"):
        command.downgrade(config, PARENT)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        assert connection.execute(sa.text("SELECT count(*) FROM customer_entitlement")).scalar_one() == 2
    engine.dispose()
