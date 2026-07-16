"""Regression checks for the invalid shipment_request update trigger repair."""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "backend"
    / "migrations"
    / "versions"
    / "20260716_drop_invalid_shipment_update_trigger.py"
)


def test_trigger_repair_remains_in_the_single_head_chain():
    config = Config(str(ROOT / "backend" / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20260717_add_customs_office_domain"]
    revision = script.get_revision("20260716_drop_invalid_shipment_update_trigger")
    assert revision.down_revision == "20260715_multi_unit_tracking"
    assert script.get_revision("20260717_add_customs_office_domain").down_revision == revision.revision


def test_trigger_repair_drops_only_the_invalid_trigger():
    source = MIGRATION.read_text(encoding="utf-8")
    assert "DROP TRIGGER IF EXISTS update_shipment_request_updated_at" in source
    assert "DROP FUNCTION" not in source
    assert "ADD COLUMN" not in source
    assert "updated_at =" not in source
    assert "CREATE TRIGGER update_shipment_request_updated_at" in source
