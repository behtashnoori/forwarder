"""PostgreSQL 18 concurrency proof for platform admin provisioning."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade
from backend.models import ExpertUser
from backend.operational_models import (
    OperationalAudit,
    OperationalIdempotency,
    OperationalMembership,
    OperationalOrganization,
)
from backend.services.platform_admin_provisioning_service import (
    PROVISION_ACTIONS,
    PROVISION_OPERATION,
    provision_platform_maintenance_admin,
)


URL = os.environ.get("PLATFORM_ADMIN_PROVISIONING_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(
    not URL, reason="requires explicit owned PLATFORM_ADMIN_PROVISIONING_POSTGRES_URL"
)


def test_postgresql18_concurrent_provisioning_is_atomic_and_idempotent():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_platform_admin_bootstrap_")

    config = alembic_config(URL)
    prepare_version_table_for_upgrade(URL, config)
    command.upgrade(config, "head")
    app = create_app(
        {
            "TESTING": True,
            "APP_ENV": "testing",
            "SQLALCHEMY_DATABASE_URI": URL,
            "SECRET_KEY": "platform-admin-postgresql-test",
        },
        skip_startup=True,
    )
    with app.app_context():
        organization = OperationalOrganization(
            name="PostgreSQL Provisioning Organization", is_active=True
        )
        db.session.add(organization)
        db.session.commit()
        organization_public_id = organization.public_id

    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(
            connection.execute(sa.text("SHOW server_version_num")).scalar_one()
        ) < 190000
        assert connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "20261016_active_route_basis"

    def provision_once(_attempt):
        with app.app_context():
            try:
                return provision_platform_maintenance_admin(
                    username="postgres_platform_admin",
                    full_name="PostgreSQL Platform Maintenance Admin",
                    password="PostgresPlatformAdmin-2026!",
                    organization_public_id=organization_public_id,
                    operator="postgres.bootstrap.operator",
                    approval_reference="ADR-073/postgresql-concurrency",
                    bootstrap_authorized=True,
                )["status"]
            finally:
                db.session.remove()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(provision_once, (1, 2)))

    assert sorted(outcomes) == ["CHANGED", "UNCHANGED"]
    with app.app_context():
        actor = ExpertUser.query.filter_by(username="postgres_platform_admin").one()
        assert actor.authority == "PLATFORM_ADMIN"
        assert actor.is_active is True
        memberships = OperationalMembership.query.filter_by(user_id=actor.id).all()
        assert len(memberships) == 1
        assert memberships[0].is_active is True
        assert OperationalAudit.query.filter(
            OperationalAudit.actor_user_id == actor.id,
            OperationalAudit.action.in_(PROVISION_ACTIONS),
        ).count() == 3
        assert OperationalIdempotency.query.filter_by(
            operation=PROVISION_OPERATION
        ).count() == 1
        db.session.remove()
    engine.dispose()
