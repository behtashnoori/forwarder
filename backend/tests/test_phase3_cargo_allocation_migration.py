"""P3-05 migration preserves unknown legacy meaning and guards historical facts."""

from datetime import datetime, timezone

from alembic import command
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa

from backend.migration_runtime import alembic_config


PARENT = "20261003_phase3_transport_execution"
HEAD = "20261004_phase3_cargo_allocation_trace"
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _parent_schema(url):
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    sa.Table("operational_organization", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table("expert_user", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table("project", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table("operational_shipment", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table("shipment_cargo_item", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table("execution_unit", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table("route_stage_execution", metadata, sa.Column("id", BIGINT, primary_key=True))
    allocation = sa.Table(
        "execution_unit_cargo_allocation", metadata,
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("execution_unit_id", BIGINT, nullable=False),
        sa.Column("shipment_cargo_item_id", BIGINT, nullable=False),
        sa.Column("operational_shipment_id", BIGINT, nullable=False),
        sa.Column("project_id", BIGINT, nullable=True),
        sa.Column("allocated_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", BIGINT, nullable=False),
        sa.Column("updated_by", BIGINT, nullable=False),
        sa.UniqueConstraint("shipment_cargo_item_id", "execution_unit_id", name="uq_execution_unit_cargo_allocation_pair"),
        sa.CheckConstraint("allocated_quantity > 0", name="ck_execution_unit_cargo_allocation_positive"),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(allocation.insert(), {
            "id": 1, "public_id": "legacy", "execution_unit_id": 1,
            "shipment_cargo_item_id": 1, "operational_shipment_id": 1,
            "allocated_quantity": 50, "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc), "created_by": 1, "updated_by": 1,
        })
    return engine


def test_p3_05_migration_roundtrip_legacy_unknown_and_guard(tmp_path):
    url = f"sqlite:///{(tmp_path / 'p305.db').as_posix()}"
    config = alembic_config(url)
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261012_phase3_cargo_eta"]
    assert script.get_revision(HEAD).down_revision == PARENT
    engine = _parent_schema(url)
    command.stamp(config, PARENT)
    command.upgrade(config, HEAD)
    inspector = sa.inspect(engine)
    assert {"cargo_allocation_revision", "cargo_allocation_transfer"} <= set(inspector.get_table_names())
    with engine.begin() as connection:
        legacy = connection.execute(sa.text("SELECT dimension, route_stage_execution_id, is_current, version, allocated_quantity FROM execution_unit_cargo_allocation WHERE id=1")).one()
        assert legacy.dimension is None and legacy.route_stage_execution_id is None
        assert legacy.is_current == 1 and legacy.version == 1 and legacy.allocated_quantity == 50
        assert connection.execute(sa.text("SELECT count(*) FROM cargo_allocation_revision")).scalar_one() == 0
    command.downgrade(config, PARENT)
    command.upgrade(config, HEAD)
    with engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO cargo_allocation_revision (id,public_id,organization_id,shipment_cargo_item_id,allocation_id,revision_number,action,before_quantity,after_quantity,occurred_at,recorded_by_user_id,idempotency_key,request_hash) VALUES (1,'revision',1,1,1,1,'LEGACY_RECORD',50,55,CURRENT_TIMESTAMP,1,'key','hash')"))
    with pytest.raises(RuntimeError, match="history exists"):
        command.downgrade(config, PARENT)
