"""P3-02 migration graph, legacy preservation, round-trip, and guard evidence."""

from decimal import Decimal
from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa

from backend.migration_runtime import alembic_config


PREVIOUS = "20260930_phase3_reference_catalog"
HEAD = "20261001_phase3_cargo_lineage"
REPOSITORY_HEAD = "20261004_phase3_cargo_allocation_trace"
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _parent_schema(url):
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    shipment_request = sa.Table(
        "shipment_request", metadata, sa.Column("id", BIGINT, primary_key=True)
    )
    sa.Table("packaging_type", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table("unit_of_measure", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table(
        "request_cargo_item",
        metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column(
            "shipment_request_id",
            BIGINT,
            sa.ForeignKey(shipment_request.c.id, ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    sa.Table(
        "shipment_cargo_item",
        metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("cargo_owner_customer_id", BIGINT, nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
    )
    metadata.create_all(engine)
    return engine


def test_p3_02_migration_is_single_head_seed_free_and_preserves_legacy_roundtrip(tmp_path):
    config = alembic_config("sqlite://")
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [REPOSITORY_HEAD]
    assert script.get_revision(HEAD).down_revision == PREVIOUS

    source = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20261001_phase3_cargo_lineage.py"
    ).read_text(encoding="utf-8")
    assert "bulk_insert" not in source
    assert "INSERT INTO" not in source
    assert "UPDATE shipment_cargo_item" not in source
    assert "Downgrade refused" in source

    url = f"sqlite:///{(tmp_path / 'p3-02-roundtrip.db').as_posix()}"
    engine = _parent_schema(url)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO shipment_cargo_item "
                "(id, operational_shipment_id, cargo_owner_customer_id, quantity) "
                "VALUES (1, 10, NULL, 7.5)"
            )
        )
    config = alembic_config(url)
    command.stamp(config, PREVIOUS)
    command.upgrade(config, HEAD)

    inspector = sa.inspect(engine)
    columns = {row["name"] for row in inspector.get_columns("shipment_cargo_item")}
    assert {
        "source_shipment_request_id",
        "source_request_cargo_item_id",
        "requested_quantity",
        "planned_quantity",
        "actual_quantity",
        "packaging_type_id",
        "gross_weight",
        "gross_weight_uom_id",
        "volume",
        "volume_uom_id",
        "destination_description",
    } <= columns
    indexes = {row["name"] for row in inspector.get_indexes("shipment_cargo_item")}
    assert {
        "ix_shipment_cargo_item_source_request",
        "ix_shipment_cargo_item_source_request_cargo",
        "ix_shipment_cargo_item_customer_shipment",
    } <= indexes
    checks = {row["name"] for row in inspector.get_check_constraints("shipment_cargo_item")}
    assert {
        "ck_shipment_cargo_requested_quantity_positive",
        "ck_shipment_cargo_planned_quantity_positive",
        "ck_shipment_cargo_actual_quantity_positive",
        "ck_shipment_cargo_requested_has_source",
        "ck_shipment_cargo_source_item_has_request",
        "ck_shipment_cargo_weight_pair",
        "ck_shipment_cargo_volume_pair",
    } <= checks
    with engine.connect() as connection:
        preserved = connection.execute(
            sa.text(
                "SELECT quantity, requested_quantity, planned_quantity, actual_quantity, "
                "source_shipment_request_id FROM shipment_cargo_item WHERE id = 1"
            )
        ).mappings().one()
    assert str(preserved["quantity"]) in {"7.5", "7.500000"}
    assert all(
        preserved[field] is None
        for field in (
            "requested_quantity",
            "planned_quantity",
            "actual_quantity",
            "source_shipment_request_id",
        )
    )

    command.downgrade(config, PREVIOUS)
    downgraded = {
        row["name"] for row in sa.inspect(engine).get_columns("shipment_cargo_item")
    }
    assert "planned_quantity" not in downgraded
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT quantity FROM shipment_cargo_item WHERE id = 1")
        ).scalar_one() == Decimal("7.500000")
    command.upgrade(config, HEAD)
    assert "planned_quantity" in {
        row["name"] for row in sa.inspect(engine).get_columns("shipment_cargo_item")
    }
    engine.dispose()


def test_p3_02_downgrade_refuses_semantic_data(tmp_path):
    url = f"sqlite:///{(tmp_path / 'p3-02-guard.db').as_posix()}"
    engine = _parent_schema(url)
    config = alembic_config(url)
    command.stamp(config, PREVIOUS)
    command.upgrade(config, HEAD)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO shipment_cargo_item "
                "(id, operational_shipment_id, cargo_owner_customer_id, quantity, planned_quantity) "
                "VALUES (1, 10, NULL, 5, 5)"
            )
        )
    with pytest.raises(RuntimeError, match="Downgrade refused"):
        command.downgrade(config, PREVIOUS)
    engine.dispose()
