"""Owned PostgreSQL 18 qualification for P3-02 Cargo lineage."""

from decimal import Decimal
import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.cargo_models import ShipmentCargoItem
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import (
    CargoType,
    Customer,
    ExpertUser,
    PackagingType,
    RequestCargoItem,
    ShipmentRequest,
    UnitOfMeasure,
)
from backend.operational_models import (
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
)
from backend.organization_reference_catalog_models import (
    OrganizationCargoTypeActivation,
    OrganizationPackagingTypeActivation,
    OrganizationUnitOfMeasureActivation,
)
from backend.services import cargo_service


POSTGRES_URL = os.environ.get("P3_CARGO_LINEAGE_POSTGRES_URL", "")
PREVIOUS = "20260930_phase3_reference_catalog"
HEAD = "20261001_phase3_cargo_lineage"

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires explicit P3_CARGO_LINEAGE_POSTGRES_URL",
)


def _assert_disposable_postgres_18():
    parsed = make_url(POSTGRES_URL)
    assert parsed.drivername.startswith("postgresql")
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_p3_02_cargo_lineage_")
    engine = sa.create_engine(POSTGRES_URL)
    try:
        with engine.connect() as connection:
            assert int(
                connection.execute(sa.text("SHOW server_version_num")).scalar_one()
            ) >= 180000
    finally:
        engine.dispose()


def test_postgresql18_full_upgrade_roundtrip_constraints_and_runtime():
    _assert_disposable_postgres_18()
    config = alembic_config(POSTGRES_URL)
    command.upgrade(config, HEAD)
    engine = sa.create_engine(POSTGRES_URL)
    inspector = sa.inspect(engine)
    assert "shipment_cargo_item" in inspector.get_table_names()
    assert "planned_quantity" in {
        row["name"] for row in inspector.get_columns("shipment_cargo_item")
    }
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT count(*) FROM shipment_cargo_item")
        ).scalar_one() == 0

    command.downgrade(config, PREVIOUS)
    assert "planned_quantity" not in {
        row["name"] for row in sa.inspect(engine).get_columns("shipment_cargo_item")
    }
    command.upgrade(config, HEAD)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": POSTGRES_URL,
            "SECRET_KEY": "p3-02-postgresql",
        },
        skip_startup=True,
    )
    with app.app_context():
        org = OperationalOrganization(name="P3-02 PostgreSQL Org")
        owner = ExpertUser(
            username="p3-02-postgresql-owner",
            password_hash="unused",
            full_name="P3-02 PostgreSQL Owner",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        customer = Customer(
            first_name="PostgreSQL",
            last_name="Customer",
            phone="09129999999",
            status="active",
            ownership_scope="TENANT",
        )
        cargo_type = CargoType(
            immutable_code="P3_02_PG_CARGO",
            fa_name="کالای آزمون",
            en_name="Test cargo",
            is_active=True,
        )
        uom = UnitOfMeasure(
            immutable_code="P3_02_PG_EA",
            fa_name="عدد",
            en_name="Each",
            symbol="ea",
            measurement_dimension="COUNT",
            is_active=True,
        )
        packaging = PackagingType(
            immutable_code="P3_02_PG_BOX",
            fa_name="جعبه",
            en_name="Box",
            is_active=True,
        )
        db.session.add_all([org, owner, cargo_type, uom, packaging])
        db.session.flush()
        customer.operational_organization_id = org.id
        db.session.add(customer)
        db.session.flush()
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org.id,
                    user_id=owner.id,
                    permissions=[
                        "operational_shipment.read",
                        "operational_shipment.create",
                    ],
                ),
                OrganizationCargoTypeActivation(
                    organization_id=org.id,
                    cargo_type_id=cargo_type.id,
                    created_by=owner.id,
                    updated_by=owner.id,
                ),
                OrganizationUnitOfMeasureActivation(
                    organization_id=org.id,
                    unit_of_measure_id=uom.id,
                    created_by=owner.id,
                    updated_by=owner.id,
                ),
                OrganizationPackagingTypeActivation(
                    organization_id=org.id,
                    packaging_type_id=packaging.id,
                    created_by=owner.id,
                    updated_by=owner.id,
                ),
            ]
        )
        request_row = ShipmentRequest(
            contact_phone="09129999999",
            assigned_to=owner.id,
            customer_id=customer.id,
            operational_organization_id=org.id,
            ownership_scope="TENANT",
        )
        shipment = OperationalShipment(
            organization_id=org.id,
            source_type="direct",
            customer_id=customer.id,
            lifecycle_status="planned",
            created_by_user_id=owner.id,
            primary_responsible_expert_id=owner.id,
        )
        db.session.add_all([request_row, shipment])
        db.session.flush()
        request_cargo = RequestCargoItem(
            shipment_request_id=request_row.id,
            position=1,
            cargo_type_id=cargo_type.id,
            description="PostgreSQL source",
            quantity=Decimal("5"),
            uom_id=uom.id,
        )
        db.session.add(request_cargo)
        db.session.commit()

        created = cargo_service.create_shipment_item(
            {"id": owner.id, "role": owner.role},
            shipment,
            {
                "line_number": 1,
                "display_name": "PostgreSQL Cargo",
                "cargo_type_public_id": cargo_type.public_id,
                "uom_public_id": uom.public_id,
                "cargo_owner_customer_id": customer.id,
                "source_request_public_id": request_row.public_id,
                "source_request_cargo_item_public_id": request_cargo.public_id,
                "requested_quantity": "5",
                "planned_quantity": "4",
                "quantity": "4",
                "packaging_type_public_id": packaging.public_id,
            },
        )
        assert created.requested_quantity == Decimal("5")
        assert created.planned_quantity == Decimal("4")
        assert created.actual_quantity is None
        assert created.source_request_cargo_item_id == request_cargo.id
        cargo_id = created.id
        db.session.remove()

    with pytest.raises(sa.exc.IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "UPDATE shipment_cargo_item SET source_shipment_request_id = NULL "
                    "WHERE id = :cargo_id"
                ),
                {"cargo_id": cargo_id},
            )

    with pytest.raises(RuntimeError, match="Downgrade refused"):
        command.downgrade(config, PREVIOUS)

    with engine.begin() as connection:
        certified = connection.execution_options(
            include_quarantined_for_certification=True
        )
        certified.execute(
            sa.text("DELETE FROM operational_audit WHERE entity_type = 'ShipmentCargoItem'")
        )
        certified.execute(
            sa.text("DELETE FROM shipment_cargo_item WHERE id = :cargo_id"),
            {"cargo_id": cargo_id},
        )
    command.downgrade(config, PREVIOUS)
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one() == HEAD
    engine.dispose()
