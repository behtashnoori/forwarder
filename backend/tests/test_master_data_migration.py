from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_master_data_is_single_additive_head():
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20260829_cargo_traceability_index"]
    assert script.get_revision("20260807_master_data").down_revision == "20260806_execution_units"
