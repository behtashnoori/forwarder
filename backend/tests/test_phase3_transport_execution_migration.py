"""P3-04 additive migration, legacy preservation, and guarded downgrade."""

from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa

from backend.migration_runtime import alembic_config


PREVIOUS = "20261002_phase3_branched_route"
HEAD = "20261003_phase3_transport_execution"
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _parent_schema(url: str):
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    organization = sa.Table(
        "operational_organization", metadata, sa.Column("id", BIGINT, primary_key=True)
    )
    expert = sa.Table(
        "expert_user", metadata, sa.Column("id", BIGINT, primary_key=True)
    )
    customer = sa.Table(
        "customer", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("operational_organization_id", BIGINT, nullable=False),
        sa.UniqueConstraint(
            "id", "operational_organization_id", name="uq_customer_id_operational_org"
        ),
        sa.ForeignKeyConstraint(
            ["operational_organization_id"], [organization.c.id]
        ),
    )
    means = sa.Table(
        "transport_means_type", metadata, sa.Column("id", BIGINT, primary_key=True)
    )
    equipment = sa.Table(
        "transport_equipment_type", metadata, sa.Column("id", BIGINT, primary_key=True)
    )
    shipment = sa.Table(
        "operational_shipment", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.UniqueConstraint(
            "id", "organization_id", name="uq_operational_shipment_id_org"
        ),
    )
    plan = sa.Table(
        "route_plan", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.UniqueConstraint(
            "id", "operational_shipment_id", name="uq_route_plan_id_shipment"
        ),
    )
    leg = sa.Table(
        "route_leg", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("route_plan_id", BIGINT, nullable=False),
        sa.UniqueConstraint("id", "route_plan_id", name="uq_route_leg_id_plan"),
    )
    unit = sa.Table(
        "execution_unit", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("organization_id", BIGINT, nullable=False),
    )
    event = sa.Table(
        "operational_event", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("execution_unit_id", BIGINT, nullable=False),
        sa.ForeignKeyConstraint(["execution_unit_id"], [unit.c.id]),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(organization.insert(), [{"id": 1}, {"id": 2}])
        connection.execute(expert.insert(), [{"id": 10}, {"id": 20}])
        connection.execute(customer.insert(), {"id": 100, "operational_organization_id": 1})
        connection.execute(means.insert(), {"id": 200})
        connection.execute(equipment.insert(), {"id": 300})
        connection.execute(shipment.insert(), {"id": 400, "organization_id": 1})
        connection.execute(plan.insert(), {"id": 500, "operational_shipment_id": 400})
        connection.execute(leg.insert(), {"id": 600, "route_plan_id": 500})
        connection.execute(unit.insert(), {"id": 700, "organization_id": 1})
        connection.execute(event.insert(), {"id": 800, "execution_unit_id": 700})
    return engine


def test_p3_04_is_single_head_additive_seed_free_and_round_trips(tmp_path):
    config = alembic_config("sqlite://")
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261009_phase3_route_time"]
    assert script.get_revision(HEAD).down_revision == PREVIOUS
    source = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20261003_phase3_transport_execution.py"
    ).read_text(encoding="utf-8")
    assert "bulk_insert" not in source
    assert "UPDATE execution_unit" not in source
    assert "Downgrade refused" in source

    url = f"sqlite:///{(tmp_path / 'p3-04-roundtrip.db').as_posix()}"
    config = alembic_config(url)
    engine = _parent_schema(url)
    command.stamp(config, PREVIOUS)
    command.upgrade(config, HEAD)
    inspector = sa.inspect(engine)
    assert {
        "route_stage_execution",
        "execution_transport_revision",
        "execution_transport_equipment_snapshot",
    } <= set(inspector.get_table_names())
    assert "transport_revision_id" in {
        row["name"] for row in inspector.get_columns("operational_event")
    }
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT transport_revision_id FROM operational_event WHERE id=800")
        ).scalar_one() is None
        assert connection.execute(
            sa.text("SELECT organization_id FROM execution_unit WHERE id=700")
        ).scalar_one() == 1

    command.downgrade(config, PREVIOUS)
    assert "route_stage_execution" not in sa.inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT organization_id FROM execution_unit WHERE id=700")
        ).scalar_one() == 1
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one() == HEAD
    engine.dispose()


def test_p3_04_downgrade_refuses_governed_execution_without_partial_ddl(tmp_path):
    url = f"sqlite:///{(tmp_path / 'p3-04-guard.db').as_posix()}"
    config = alembic_config(url)
    engine = _parent_schema(url)
    command.stamp(config, PREVIOUS)
    command.upgrade(config, HEAD)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO route_stage_execution "
                "(id, public_id, organization_id, operational_shipment_id, "
                "route_plan_id, route_leg_id, execution_unit_id, idempotency_key, "
                "request_hash, created_by_user_id, created_at) VALUES "
                "(1, '00000000-0000-4000-8000-000000000001', 1, 400, 500, 600, "
                "700, 'guard', :request_hash, 10, CURRENT_TIMESTAMP)"
            ),
            {"request_hash": "x" * 64},
        )

    with pytest.raises(RuntimeError, match="Downgrade refused"):
        command.downgrade(config, PREVIOUS)

    inspector = sa.inspect(engine)
    assert "route_stage_execution" in inspector.get_table_names()
    assert "transport_revision_id" in {
        row["name"] for row in inspector.get_columns("operational_event")
    }
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one() == HEAD
    engine.dispose()
