from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


MODULE = Path(__file__).parents[1] / "phase1b_fresh_transfer.py"
SPEC = importlib.util.spec_from_file_location("phase1b_fresh_transfer", MODULE)
tool = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = tool
SPEC.loader.exec_module(tool)


def column(name, nullable=True, default=None, dtype="integer", generated=False):
    return tool.Column(name, dtype, nullable, default, generated)


def test_database_guards_are_local_and_exact():
    assert "password" not in tool.quote_dsn("127.0.0.1", 5432, "postgres", "forwarder_db")
    with pytest.raises(tool.CutoverBlocked):
        tool.quote_dsn("example.com", 5432, "postgres", "forwarder_db")
    with pytest.raises(tool.CutoverBlocked):
        tool.quote_dsn("127.0.0.1", 5432, "postgres", "production")


def test_mapping_fixture_preserves_baseline_and_excludes_security():
    source = {
        "alembic_version": (column("version_num"),),
        "user": (column("id"), column("email", dtype="text")),
        "auth_session": (column("id"),),
    }
    target = {
        "alembic_version": source["alembic_version"],
        "user": source["user"],
        "auth_session": source["auth_session"],
    }
    plans, blockers = tool.build_mapping(source, target, {key: 2 for key in source})
    classes = {item.table: item.classification for item in plans}
    assert blockers == []
    assert classes["alembic_version"] == "TARGET_BASELINE_PRESERVE"
    assert classes["auth_session"] == "EXCLUDE_SECURITY_SENSITIVE"
    assert classes["user"] == "DIRECT_COPY"


def test_populated_unmapped_or_required_column_blocks():
    source = {"legacy": (column("id"),), "user": (column("id"),)}
    target = {"user": (column("id"), column("required", nullable=False))}
    plans, blockers = tool.build_mapping(source, target, {"legacy": 1, "user": 1})
    assert len(blockers) == 2
    assert {item.classification for item in plans} == {
        "SOURCE_ONLY_REVIEW", "MANUAL_DECISION_REQUIRED"
    }


def test_password_hash_is_not_copied_by_generic_schema_matching():
    columns, blocker = tool.transferable_columns(
        (column("id"), column("password_hash", nullable=False, dtype="text")),
        (column("id"), column("password_hash", nullable=False, dtype="text")),
        "user",
    )
    assert columns == ()
    assert "compatibility unproven" in blocker


def test_six_mapping_decisions_are_complete():
    tenant = (
        column("id"), column("name", dtype="text"), column("slug", dtype="text"),
        column("status", dtype="text"), column("created_at", dtype="timestamp"),
    )
    membership = (
        column("id"), column("tenant_id"), column("user_id"),
        column("role", dtype="text"), column("status", dtype="text"),
        column("created_at", dtype="timestamp"),
    )
    audit = (
        column("id"), column("tenant_id"), column("actor_type", dtype="text"),
        column("actor_id"), column("action", dtype="text"),
        column("metadata_json", dtype="text"), column("created_at", dtype="timestamp"),
    )
    expert = (
        column("id"), column("username", dtype="text"),
        column("password_hash", nullable=False, dtype="character varying"),
        column("full_name", dtype="text"),
    )
    country = (column("id"), column("code", dtype="text"))
    version = (column("version_num", nullable=False, dtype="text"),)
    source = {
        "tenants": tenant, "memberships": membership, "audit_logs": audit,
        "expert_user": expert, "country": country, "alembic_version": version,
    }
    target = {
        "operational_organization": (
            column("id"), column("public_id", dtype="text"),
            column("name", dtype="text"), column("is_active"),
            column("created_at", dtype="timestamp"),
        ),
        "operational_membership": (
            column("id"), column("organization_id"), column("user_id"),
            column("is_active"), column("permissions", dtype="json"),
            column("created_at", dtype="timestamp"),
        ),
        "operational_audit": (column("id"),),
        "expert_user": expert, "country": country, "alembic_version": version,
    }
    plans, blockers = tool.build_mapping(
        source, target, {name: 3 for name in source}
    )
    classes = {plan.table: plan.classification for plan in plans}
    assert blockers == []
    assert classes == {
        "alembic_version": "TARGET_BASELINE_PRESERVE",
        "audit_logs": "ARCHIVE_ONLY",
        "country": "TARGET_BASELINE_RECONCILE",
        "expert_user": "DIRECT_COPY",
        "memberships": "ID_REMAP_REQUIRED",
        "tenants": "ID_REMAP_REQUIRED",
    }
    assert tool.password_compatibility_proven()


def test_reconciliation_fixture_is_fail_closed():
    passed = tool.reconcile_metrics([{
        "source_rows": 4, "inserted_rows": 4, "excluded_rows": 0,
        "transformed_rows": 0, "rejected_rows": 0, "variance": 0,
    }])
    failed = tool.reconcile_metrics([{
        "source_rows": 4, "inserted_rows": 3, "excluded_rows": 0,
        "transformed_rows": 0, "rejected_rows": 1, "variance": 1,
    }])
    assert passed["pass"] is True
    assert failed["pass"] is False


def test_cutover_and_rollback_state_machines():
    state = "INITIAL"
    for event in ("PREFLIGHT_PASS", "BACKUP_PASS", "REHEARSAL_PASS",
                  "FINAL_PASS", "CUTOVER_PASS"):
        state = tool.state_transition(state, event)
    assert tool.state_transition(state, "VALIDATION_PASS") == "COMPLETE"
    assert tool.state_transition(state, "VALIDATION_FAIL") == "ROLLBACK_REQUIRED"
    assert tool.state_transition("ROLLBACK_REQUIRED", "ROLLBACK_PASS") == "ROLLED_BACK"
    with pytest.raises(tool.CutoverBlocked):
        tool.state_transition("INITIAL", "CUTOVER_PASS")


def test_cleanup_allow_list():
    assert tool.cleanup_allowed("forwarder_phase1b_rehearsal_abc", "abc")
    assert not tool.cleanup_allowed("forwarder_db", "abc")
    assert not tool.cleanup_allowed("forwarder_db_legacy_abc", "abc")
