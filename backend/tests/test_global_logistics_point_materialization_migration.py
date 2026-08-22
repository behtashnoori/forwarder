from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT=Path(__file__).resolve().parents[2]


def test_materialization_is_sole_additive_head_and_bounded():
    script=ScriptDirectory.from_config(Config(str(ROOT/"backend"/"migrations"/"alembic.ini")))
    assert script.get_heads()==["20260906_global_logistics_point_materialization"]
    revision=script.get_revision("20260906_global_logistics_point_materialization")
    assert revision.down_revision=="20260905_global_logistics_point_adoption"
    source=(ROOT/"backend"/"migrations"/"versions"/"20260906_global_logistics_point_materialization.py").read_text("utf-8")
    assert "Downgrade refused" in source and "INSERT INTO" not in source
    assert "project_logistics_point" not in source and "tracking_location_reference" not in source
