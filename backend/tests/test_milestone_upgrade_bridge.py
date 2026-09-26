"""Operator bridge selection and rollback contract; no SQLite PostgreSQL claims."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from alembic.script import ScriptDirectory
from backend.migration_runtime import alembic_config
from backend import milestone_upgrade_bridge as bridge


def test_linear_head_and_backfill_ancestry():
    script = ScriptDirectory.from_config(alembic_config("sqlite://"))
    assert script.get_heads() == ["20261012_phase3_cargo_eta"]
    assert bridge._contains(script, "head", bridge.BACKFILL)
    assert not bridge._contains(script, bridge.PREDECESSOR, bridge.BACKFILL)


@pytest.mark.parametrize("current,expected", [(bridge.BACKFILL, ["head"]),
    (bridge.PREDECESSOR, [bridge.PREDECESSOR, bridge.BACKFILL, "head"])])
def test_bridge_only_before_pending_backfill(monkeypatch, current, expected):
    cfg = alembic_config("sqlite://")
    engine = MagicMock(); engine.dialect.name = "postgresql"
    connection = engine.begin.return_value.__enter__.return_value
    result = MagicMock()
    result.one.return_value = ("O", "phase1a_reject_milestone_event_mutation_v1()")
    result.scalar_one.side_effect = [bridge.STRICT, True, bridge.STRICT]
    connection.execute.return_value = result
    monkeypatch.setattr(bridge.MigrationContext, "configure", lambda c: SimpleNamespace(get_current_heads=lambda: (current,)))
    calls = []
    def upgrade(config, revision):
        calls.append(revision)
        if revision == bridge.BACKFILL:
            assert config.attributes["connection"] is connection
    monkeypatch.setattr(bridge.command, "upgrade", upgrade)
    bridge.upgrade_with_bridge(cfg, "head", engine)
    assert calls == expected
    assert "connection" not in cfg.attributes
    if current == bridge.PREDECESSOR:
        sql = "\n".join(str(call.args[0]) for call in connection.execute.call_args_list)
        assert "ACCESS EXCLUSIVE" in sql and "RETURN NEW" in sql and bridge.STRICT in sql
        assert "DISABLE TRIGGER" not in sql


def test_bridge_failure_exits_transaction_with_error(monkeypatch):
    cfg = alembic_config("sqlite://")
    engine = MagicMock(); engine.dialect.name = "postgresql"
    connection = engine.begin.return_value.__enter__.return_value
    result = MagicMock(); result.one.return_value = ("O", "phase1a_reject_milestone_event_mutation_v1()")
    result.scalar_one.side_effect = [bridge.STRICT, True]
    connection.execute.return_value = result
    monkeypatch.setattr(bridge.MigrationContext, "configure", lambda c: SimpleNamespace(get_current_heads=lambda: (bridge.PREDECESSOR,)))
    def fail(config, revision):
        if revision == bridge.BACKFILL:
            raise RuntimeError("injected failure")
    monkeypatch.setattr(bridge.command, "upgrade", fail)
    with pytest.raises(RuntimeError, match="injected"):
        bridge.upgrade_with_bridge(cfg, "head", engine)
    assert "connection" not in cfg.attributes
    assert engine.begin.return_value.__exit__.call_args.args[0] is RuntimeError


def test_bridge_permission_is_exact_metadata_only():
    assert "TG_OP='UPDATE'" in bridge.BRIDGE
    assert "to_jsonb(NEW)-'public_id'-'organization_id'" in bridge.BRIDGE
    assert "to_jsonb(OLD)-'public_id'-'organization_id'" in bridge.BRIDGE
    assert "SELECT organization_id FROM operational_milestone" in bridge.BRIDGE
    assert "DISABLE" not in bridge.BRIDGE and "GRANT" not in bridge.BRIDGE
    assert "RETURN NEW" not in bridge.STRICT
