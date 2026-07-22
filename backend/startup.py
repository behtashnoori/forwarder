"""Deprecated startup helpers retained without schema/data side effects."""
from __future__ import annotations

from sqlalchemy import inspect

from backend.runtime import CRITICAL_TABLES


def run_migrations(_app) -> None:
    """Reject legacy implicit migration calls."""
    raise RuntimeError(
        "Implicit startup migration is disabled. Run "
        "`python -m backend.migration_cli upgrade --confirm` explicitly."
    )


def verify_critical_tables(app) -> None:
    """Perform a non-mutating critical-table check for legacy callers."""
    from backend.extensions import db

    with app.app_context():
        existing = set(inspect(db.engine).get_table_names())
    missing = sorted(set(CRITICAL_TABLES) - existing)
    if missing:
        raise RuntimeError("Critical database tables are missing or inaccessible")


__all__ = ["run_migrations", "verify_critical_tables"]
