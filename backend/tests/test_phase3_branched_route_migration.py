"""P3-03 migration graph, empty round-trip and fail-closed downgrade."""

from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa

from backend.migration_runtime import alembic_config


PREVIOUS = "20261001_phase3_cargo_lineage"
HEAD = "20261002_phase3_branched_route"
REPOSITORY_HEAD = "20261011_phase3_owner_transfer"
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _parent_schema(url):
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    expert = sa.Table("expert_user", metadata, sa.Column("id", BIGINT, primary_key=True))
    shipment = sa.Table(
        "operational_shipment", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("organization_id", BIGINT, nullable=False),
        sa.UniqueConstraint("id", "organization_id", name="uq_operational_shipment_id_org"),
    )
    plan = sa.Table(
        "route_plan", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("created_by_user_id", BIGINT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id", "operational_shipment_id", name="uq_route_plan_id_shipment"),
    )
    location = sa.Table("canonical_location", metadata, sa.Column("id", BIGINT, primary_key=True))
    point = sa.Table("logistics_point", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table(
        "route_leg", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("source_route_leg_id", BIGINT, nullable=True),
        sa.Column("route_plan_id", BIGINT, nullable=False),
        sa.Column("sequence_number", sa.Integer, nullable=False),
        sa.Column("origin_location_id", BIGINT, nullable=False),
        sa.Column("destination_location_id", BIGINT, nullable=False),
        sa.Column("origin_logistics_point_id", BIGINT, nullable=True),
        sa.Column("destination_logistics_point_id", BIGINT, nullable=True),
        sa.Column("origin_snapshot", sa.JSON, nullable=False),
        sa.Column("destination_snapshot", sa.JSON, nullable=False),
        sa.Column("transport_mode", sa.String(32), nullable=False),
        sa.Column("carrier_reference", sa.String(120), nullable=True),
        sa.Column("planned_departure", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_arrival", sa.DateTime(timezone=True), nullable=False),
        sa.Column("projected_departure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("projected_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_departure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id", "route_plan_id", name="uq_route_leg_id_plan"),
        sa.UniqueConstraint("route_plan_id", "sequence_number", name="uq_route_leg_plan_sequence"),
        sa.ForeignKeyConstraint(["route_plan_id"], [plan.c.id]),
        sa.ForeignKeyConstraint(["origin_location_id"], [location.c.id]),
        sa.ForeignKeyConstraint(["destination_location_id"], [location.c.id]),
        sa.ForeignKeyConstraint(["origin_logistics_point_id"], [point.c.id]),
        sa.ForeignKeyConstraint(["destination_logistics_point_id"], [point.c.id]),
    )
    sa.Table(
        "shipment_cargo_item", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.ForeignKeyConstraint(["operational_shipment_id"], [shipment.c.id]),
    )
    metadata.create_all(engine)
    return engine


def test_p3_03_is_single_head_additive_seed_free_and_round_trips(tmp_path):
    config = alembic_config("sqlite://")
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [REPOSITORY_HEAD]
    assert script.get_revision(HEAD).down_revision == PREVIOUS

    source = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20261002_phase3_branched_route.py"
    ).read_text(encoding="utf-8")
    assert "bulk_insert" not in source
    assert "UPDATE route_leg" not in source
    assert "Downgrade refused" in source

    url = f"sqlite:///{(tmp_path / 'p3-03-roundtrip.db').as_posix()}"
    config = alembic_config(url)
    engine = _parent_schema(url)
    command.stamp(config, PREVIOUS)
    command.upgrade(config, HEAD)
    inspector = sa.inspect(engine)
    assert {"parent_route_leg_id", "branch_label"} <= {
        row["name"] for row in inspector.get_columns("route_leg")
    }
    assert {
        "route_cargo_destination",
        "route_traversal_fact",
    } <= set(inspector.get_table_names())

    command.downgrade(config, PREVIOUS)
    inspector = sa.inspect(engine)
    assert "route_cargo_destination" not in inspector.get_table_names()
    assert "route_traversal_fact" not in inspector.get_table_names()
    assert "parent_route_leg_id" not in {
        row["name"] for row in inspector.get_columns("route_leg")
    }
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one() == HEAD
    engine.dispose()


def test_p3_03_downgrade_refuses_incomplete_route_without_partial_ddl(tmp_path):
    url = f"sqlite:///{(tmp_path / 'p3-03-guard.db').as_posix()}"
    config = alembic_config(url)
    engine = _parent_schema(url)
    command.stamp(config, PREVIOUS)
    command.upgrade(config, HEAD)
    with engine.begin() as connection:
        connection.execute(sa.text("PRAGMA foreign_keys=OFF"))
        connection.execute(sa.text(
            "INSERT INTO route_plan "
            "(id, operational_shipment_id, revision, status, is_active, version, "
            "created_by_user_id, created_at) VALUES "
            "(999, 999, 1, 'draft', 0, 1, 999, CURRENT_TIMESTAMP)"
        ))
        connection.execute(sa.text(
            "INSERT INTO route_leg "
            "(id, route_plan_id, sequence_number, origin_location_id, "
            "destination_location_id, origin_snapshot, destination_snapshot, "
            "transport_mode, planned_departure, planned_arrival, status, version, "
            "created_at, updated_at) VALUES "
            "(999, 999, 1, 1, 2, '{}', '{}', NULL, NULL, NULL, "
            "'planned', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ))

    with pytest.raises(RuntimeError, match="Downgrade refused"):
        command.downgrade(config, PREVIOUS)

    inspector = sa.inspect(engine)
    assert "route_cargo_destination" in inspector.get_table_names()
    assert "route_traversal_fact" in inspector.get_table_names()
    assert "parent_route_leg_id" in {
        row["name"] for row in inspector.get_columns("route_leg")
    }
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one() == HEAD
        assert connection.execute(sa.text("SELECT 1")).scalar_one() == 1
    engine.dispose()
