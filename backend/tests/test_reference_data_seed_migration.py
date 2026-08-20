from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_reference_data_seed_run_is_single_additive_head():
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20260902_shipment_request_public_id"]
    assert script.get_revision("20260809_cargo_catalog_items").down_revision == "20260808_reference_seed"
    assert script.get_revision("20260808_reference_seed").down_revision == "20260807_master_data"
