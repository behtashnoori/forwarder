"""Security contracts for the additive credential remediation revision."""

from __future__ import annotations

import importlib


MODULE = "backend.migrations.versions.security_credential_remediation"


def test_revision_is_security_child_of_project_configuration():
    migration = importlib.import_module(MODULE)
    assert migration.revision == "security_credential_remediation"
    assert migration.down_revision == "20260811_project_configuration"


def test_upgrade_disables_only_the_exact_legacy_hash(monkeypatch):
    migration = importlib.import_module(MODULE)
    statements = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    assert len(statements) == 1
    compiled = statements[0].compile(compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    assert "UPDATE expert_user" in sql
    assert "password_hash =" in sql
    assert "is_active=false" in sql.replace(" ", "").lower()
    assert "DELETE" not in sql.upper()
    assert "password_hash = NULL" not in sql


def test_downgrade_never_reactivates_legacy_accounts(monkeypatch):
    migration = importlib.import_module(MODULE)
    monkeypatch.setattr(
        migration.op,
        "execute",
        lambda *_: (_ for _ in ()).throw(AssertionError("must not write")),
    )
    assert migration.downgrade() is None
