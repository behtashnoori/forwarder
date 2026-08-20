from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.extensions import db
from backend.models import Customer, ExpertUser, ShipmentRequest
from backend.operational_models import (
    OperationalOrganization,
    OperationalShipment,
    Project,
)


@pytest.fixture()
def project_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "project-foundation-test",
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _foundation_records():
    organization = OperationalOrganization(name="Project Foundation Operations")
    other_organization = OperationalOrganization(name="Other Operations")
    user = ExpertUser(
        username="project-foundation-owner",
        password_hash="unused",
        full_name="Project Foundation Owner",
        role="manager",
        is_active=True,
    )
    customer = Customer(first_name="Primary", last_name="Customer")
    request = ShipmentRequest(contact_phone="09000000001")
    db.session.add_all(
        [organization, other_organization, user, customer, request]
    )
    db.session.flush()
    return organization, other_organization, user, customer, request


def test_project_identity_ownership_and_request_lineage(project_app):
    with project_app.app_context():
        organization, _, user, customer, request = _foundation_records()
        project = Project(
            organization_id=organization.id,
            primary_customer_id=customer.id,
            project_code="PRJ-FOUNDATION-0001",
            created_by_user_id=user.id,
            shipment_requests=[request],
        )
        db.session.add(project)
        db.session.commit()

        assert project.public_id
        assert project.lifecycle_status == "not_started"
        assert project.version == 1
        assert [row.id for row in project.shipment_requests] == [request.id]
        assert request.status == "new"
        assert request.status_request_status == "new"


def test_project_code_is_unique_only_within_operational_organization(project_app):
    with project_app.app_context():
        organization, other_organization, user, customer, _ = _foundation_records()
        db.session.add_all(
            [
                Project(
                    organization_id=organization.id,
                    primary_customer_id=customer.id,
                    project_code="PRJ-SHARED-CODE",
                    created_by_user_id=user.id,
                ),
                Project(
                    organization_id=other_organization.id,
                    primary_customer_id=customer.id,
                    project_code="PRJ-SHARED-CODE",
                    created_by_user_id=user.id,
                ),
            ]
        )
        db.session.commit()

        db.session.add(
            Project(
                organization_id=organization.id,
                primary_customer_id=customer.id,
                project_code="PRJ-SHARED-CODE",
                created_by_user_id=user.id,
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()


def test_operational_shipment_project_link_is_optional_for_legacy_rows(project_app):
    with project_app.app_context():
        assert OperationalShipment.__table__.columns.project_id.nullable is True
        assert ShipmentRequest.__table__.columns.project_id.nullable is True


def test_project_foundation_migration_is_the_single_head():
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20260829_cargo_traceability_index"]
    revision = script.get_revision("20260805_project_foundation")
    assert revision.down_revision == "20260804_case_documents"


def test_project_foundation_migration_upgrades_and_downgrades_parent_schema(tmp_path):
    database_path = tmp_path / "project-foundation.db"
    url = f"sqlite:///{database_path.as_posix()}"
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

    sa.Table(
        "operational_organization",
        metadata,
        sa.Column("id", bigint, primary_key=True),
    )
    sa.Table("customer", metadata, sa.Column("id", bigint, primary_key=True))
    sa.Table("expert_user", metadata, sa.Column("id", bigint, primary_key=True))
    sa.Table("shipment_request", metadata, sa.Column("id", bigint, primary_key=True))
    sa.Table(
        "operational_shipment",
        metadata,
        sa.Column("id", bigint, primary_key=True),
        sa.Column("organization_id", bigint, nullable=False),
    )
    metadata.create_all(engine)

    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    command.stamp(config, "20260804_case_documents")
    command.upgrade(config, "20260805_project_foundation")

    inspector = sa.inspect(engine)
    assert {
        "project",
        "project_party_relationship",
    } <= set(inspector.get_table_names())
    assert "project_id" in {
        column["name"] for column in inspector.get_columns("operational_shipment")
    }
    assert {
        tuple(item["constrained_columns"])
        for item in inspector.get_foreign_keys("operational_shipment")
    } == {("project_id", "organization_id")}
    assert "project_id" in {
        column["name"] for column in inspector.get_columns("shipment_request")
    }

    command.downgrade(config, "20260804_case_documents")
    inspector = sa.inspect(engine)
    assert "project" not in inspector.get_table_names()
    assert "project_id" not in {
        column["name"] for column in inspector.get_columns("operational_shipment")
    }
    assert "project_id" not in {
        column["name"] for column in inspector.get_columns("shipment_request")
    }
