from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_case_document_migration_is_single_head():
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20260826_org_document_policy"]
    revision = script.get_revision("20260804_case_documents")
    assert revision.down_revision == "20260803_expert_sla"
