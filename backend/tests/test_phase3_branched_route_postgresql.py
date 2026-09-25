"""Owned PostgreSQL 18 qualification for P3-03 branched routes."""
from datetime import datetime, timedelta, timezone
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
from backend.models import CargoType, Customer, ExpertUser, Province, UnitOfMeasure
from backend.operational_models import (
    OperationalException,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    RoutePlan,
)
from backend.services import route_orchestration_service as routes


POSTGRES_URL = os.environ.get("P3_BRANCHED_ROUTE_POSTGRES_URL", "")
PREVIOUS = "20261001_phase3_cargo_lineage"
HEAD = "20261002_phase3_branched_route"

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires explicit P3_BRANCHED_ROUTE_POSTGRES_URL",
)


def _assert_disposable_postgres_18():
    parsed = make_url(POSTGRES_URL)
    assert parsed.drivername.startswith("postgresql")
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith(
        "forwarder_integrated_cert_p3_03_branched_route_"
    )
    engine = sa.create_engine(POSTGRES_URL)
    try:
        with engine.connect() as connection:
            assert int(
                connection.execute(sa.text("SHOW server_version_num")).scalar_one()
            ) >= 180000
    finally:
        engine.dispose()


def test_postgresql18_upgrade_roundtrip_constraints_and_route_runtime():
    _assert_disposable_postgres_18()
    config = alembic_config(POSTGRES_URL)
    command.upgrade(config, HEAD)
    engine = sa.create_engine(POSTGRES_URL)
    inspector = sa.inspect(engine)
    assert {"route_cargo_destination", "route_traversal_fact"}.issubset(
        inspector.get_table_names()
    )
    columns = {row["name"]: row for row in inspector.get_columns("route_leg")}
    assert columns["parent_route_leg_id"]["nullable"] is True
    assert columns["transport_mode"]["nullable"] is True

    command.downgrade(config, PREVIOUS)
    assert "parent_route_leg_id" not in {
        row["name"] for row in sa.inspect(engine).get_columns("route_leg")
    }
    command.upgrade(config, HEAD)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": POSTGRES_URL,
            "SECRET_KEY": "p3-03-postgresql",
        },
        skip_startup=True,
    )
    with app.app_context():
        org = OperationalOrganization(name="P3-03 PostgreSQL Org")
        owner = ExpertUser(
            username="p3-03-postgresql-owner",
            password_hash="unused",
            full_name="P3-03 PostgreSQL Owner",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        customer = Customer(
            company_name="P3-03 PostgreSQL Customer",
            status="active",
            ownership_scope="TENANT",
        )
        cargo_type = CargoType(
            immutable_code="P3_03_PG_CARGO",
            fa_name="کالای مسیر",
            en_name="Route cargo",
            is_active=True,
        )
        uom = UnitOfMeasure(
            immutable_code="P3_03_PG_EA",
            fa_name="عدد",
            en_name="Each",
            symbol="ea",
            measurement_dimension="COUNT",
            is_active=True,
        )
        db.session.add_all([org, owner, cargo_type, uom])
        db.session.flush()
        customer.operational_organization_id = org.id
        db.session.add(customer)
        db.session.flush()
        db.session.add(
            OperationalMembership(
                organization_id=org.id,
                user_id=owner.id,
                permissions=[
                    "operational_shipment.read",
                    "route_plan.create",
                    "route_plan.activate",
                    "route_plan.replan",
                    "route_leg.manage",
                ],
            )
        )
        shipment = OperationalShipment(
            organization_id=org.id,
            source_type="direct",
            customer_id=customer.id,
            lifecycle_status="planned",
            created_by_user_id=owner.id,
            primary_responsible_expert_id=owner.id,
        )
        db.session.add(shipment)
        db.session.flush()
        cargo = []
        for line in (1, 2):
            row = ShipmentCargoItem(
                operational_shipment_id=shipment.id,
                cargo_owner_customer_id=customer.id,
                line_number=line,
                cargo_type_id=cargo_type.id,
                quantity=Decimal("10"),
                planned_quantity=Decimal("10"),
                uom_id=uom.id,
                display_name_snapshot=f"P3-03 Cargo {line}",
                cargo_type_code_snapshot=cargo_type.immutable_code,
                cargo_type_fa_snapshot=cargo_type.fa_name,
                cargo_type_en_snapshot=cargo_type.en_name,
                uom_code_snapshot=uom.immutable_code,
                uom_symbol_snapshot=uom.symbol,
                created_by=owner.id,
                updated_by=owner.id,
            )
            db.session.add(row)
            cargo.append(row)
        locations = []
        for code, name in (
            ("P303PG-O", "مبدأ"),
            ("P303PG-H", "مرکز مشترک"),
            ("P303PG-A", "مقصد الف"),
            ("P303PG-B", "مقصد ب"),
            ("P303PG-X", "مقصد واقعی"),
        ):
            row = Province(code=code, name_fa=name, is_active=True)
            db.session.add(row)
            locations.append(row)
        db.session.commit()
        user = {"id": owner.id, "role": "expert", "authority": "EXPERT"}
        plan = routes.create_plan(shipment.id, {}, user)
        incomplete = routes.add_leg(
            shipment.id,
            plan["id"],
            {
                "sequence_number": 1,
                "origin": {"source_type": "province", "source_id": locations[0].id},
                "destination": {"source_type": "province", "source_id": locations[1].id},
                "branch_label": "بخش مشترک",
            },
            user,
        )
        detail = routes.get_plan(shipment.id, plan["id"], user)
        assert detail["is_complete"] is False
        assert detail["legs"][0]["transport_mode"] is None
        assert detail["legs"][0]["planned_departure"] is None
        assert detail["legs"][0]["departure_milestone_id"] is None

        start = datetime.now(timezone.utc) + timedelta(days=2)
        routes.update_leg(
            shipment.id,
            plan["id"],
            incomplete["id"],
            {
                "expected_version": incomplete["version"],
                "transport_mode": "road",
                "planned_departure": start.isoformat(),
                "planned_arrival": (start + timedelta(hours=2)).isoformat(),
            },
            user,
        )
        branches = []
        for sequence, location, label, hours in (
            (2, locations[2], "مقصد الف", 5),
            (3, locations[3], "مقصد ب", 6),
        ):
            branches.append(
                routes.add_leg(
                    shipment.id,
                    plan["id"],
                    {
                        "sequence_number": sequence,
                        "parent_route_leg_id": incomplete["id"],
                        "origin": {"source_type": "province", "source_id": locations[1].id},
                        "destination": {"source_type": "province", "source_id": location.id},
                        "branch_label": label,
                        "transport_mode": "road",
                        "planned_departure": (start + timedelta(hours=3)).isoformat(),
                        "planned_arrival": (start + timedelta(hours=hours)).isoformat(),
                    },
                    user,
                )
            )
        for item, branch in zip(cargo, branches):
            routes.assign_cargo_destination(
                shipment.id,
                plan["id"],
                item.public_id,
                {"destination_route_leg_id": branch["id"]},
                user,
            )
        assert routes.validate_plan(shipment.id, plan["id"], user)["valid"] is True
        active = routes.activate_plan(
            shipment.id,
            plan["id"],
            {"expected_version": plan["version"]},
            user,
        )
        traversal = routes.record_traversal(
            shipment.id,
            plan["id"],
            {
                "planned_route_leg_id": branches[0]["id"],
                "origin": {"source_type": "province", "source_id": locations[1].id},
                "destination": {"source_type": "province", "source_id": locations[4].id},
                "departed_at": datetime.now(timezone.utc).isoformat(),
                "notes": "PostgreSQL deviation",
            },
            user,
        )
        assert traversal["is_deviation"] is True
        assert OperationalException.query.filter_by(
            operational_shipment_id=shipment.id
        ).count() == 0
        replanned = routes.replan(
            shipment.id,
            plan["id"],
            {"expected_version": active["version"], "reason": "PostgreSQL history"},
            user,
            "p3-03-postgresql-replan",
        )
        source = routes.get_plan(shipment.id, plan["id"], user)
        current = routes.get_plan(shipment.id, replanned["id"], user)
        assert source["actual_traversal_count"] == 1
        assert current["actual_traversal_count"] == 0
        assert len(current["cargo_destinations"]) == 2

        db.session.add(
            RoutePlan(
                operational_shipment_id=shipment.id,
                revision_number=3,
                status="active",
                is_active=True,
                created_by_user_id=owner.id,
            )
        )
        with pytest.raises(sa.exc.IntegrityError):
            db.session.flush()
        db.session.rollback()

    with pytest.raises(RuntimeError, match="Downgrade refused"):
        command.downgrade(config, PREVIOUS)
    with engine.begin() as connection:
        connection.execute(sa.text("DELETE FROM route_traversal_fact"))
        connection.execute(sa.text("DELETE FROM route_cargo_destination"))
        connection.execute(
            sa.text(
                "UPDATE route_leg SET parent_route_leg_id = NULL, branch_label = NULL"
            )
        )
    command.downgrade(config, PREVIOUS)
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one() == HEAD
    engine.dispose()
