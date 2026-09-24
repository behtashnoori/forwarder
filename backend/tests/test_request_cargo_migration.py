"""Static and graph contracts for the additive Request Cargo migration."""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


MIGRATION = Path(__file__).parents[1] / "migrations" / "versions" / "20260924_request_cargo_items.py"


def test_request_cargo_migration_is_single_head_additive_and_zero_backfill():
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "20260924_request_cargo_items"' in source
    assert 'down_revision = "20260923_notification_lifecycle"' in source
    assert '"request_cargo_item"' in source
    assert 'ondelete="RESTRICT"' in source
    assert "bulk_insert" not in source
    assert "INSERT INTO request_cargo_item" not in source
    assert "ALTER TABLE shipment_request" not in source
    assert "shipment_cargo_item" not in source

    config = Config(str(Path(__file__).parents[1] / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20260928_operational_workspace_phase2"]
    assert script.get_bases() == ["20240917_initial_schema"]


def test_request_cargo_downgrade_refuses_to_discard_customer_evidence():
    source = MIGRATION.read_text(encoding="utf-8")
    assert "SELECT COUNT(*) FROM request_cargo_item" in source
    assert "Cannot downgrade while Request Cargo Item evidence exists" in source
