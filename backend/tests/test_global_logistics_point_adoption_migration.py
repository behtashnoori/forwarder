from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT=Path(__file__).resolve().parents[2]


def test_adoption_is_sole_additive_head_and_has_retained_data_guard():
    config=Config(str(ROOT/"backend"/"migrations"/"alembic.ini"))
    script=ScriptDirectory.from_config(config)
    assert script.get_heads()==["20260907_direct_shipment_responsibility"]
    revision=script.get_revision("20260905_global_logistics_point_adoption")
    assert revision.down_revision=="20260904_global_logistics_point_foundation"
    source=(ROOT/"backend"/"migrations"/"versions"/"20260905_global_logistics_point_adoption.py").read_text(encoding="utf-8")
    assert "Downgrade refused" in source and "SELECT count(*)" in source
    for forbidden in ("logistics_point\"", "project_logistics_point", "tracking_location_reference", "shipment_transport_unit_update", "INSERT INTO"):
        assert forbidden not in source
