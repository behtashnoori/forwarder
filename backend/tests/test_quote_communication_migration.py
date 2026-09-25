"""Static graph and safety contracts for governed Quote communication."""
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "20260925_quote_communication.py"
)


def test_quote_communication_migration_is_single_head_and_additive():
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "20260925_quote_communication"' in source
    assert 'down_revision = "20260924_request_cargo_items"' in source
    assert 'sa.Column("public_id", sa.String(36)' in source
    assert 'sa.Column("customer_response_message", sa.String(500)' in source
    assert 'sa.Column("responded_by_customer_id"' in source
    assert 'ondelete="SET NULL"' in source
    assert "'accepted', 'discussion', 'declined'" in source
    assert "UPDATE expert_quote SET public_id" in source
    assert "UPDATE expert_quote SET customer_response" not in source
    assert "UPDATE expert_quote SET customer_response_message" not in source

    config = Config(str(Path(__file__).parents[1] / "migrations" / "alembic.ini"))
    config.set_main_option(
        "script_location", str(Path(__file__).parents[1] / "migrations")
    )
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20261007_phase3_reported_facts"]
    assert script.get_revision("20260925_quote_communication").down_revision == (
        "20260924_request_cargo_items"
    )
    assert script.get_bases() == ["20240917_initial_schema"]


def test_quote_communication_downgrade_refuses_to_discard_new_evidence():
    source = MIGRATION.read_text(encoding="utf-8")
    assert "customer_response = 'discussion'" in source
    assert "customer_response_message IS NOT NULL" in source
    assert "responded_by_customer_id IS NOT NULL" in source
    assert "Cannot downgrade while Quote communication evidence exists" in source
