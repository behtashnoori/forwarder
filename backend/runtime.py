"""Runtime startup policy. Never migrates or seeds a database."""
from __future__ import annotations

import os

from sqlalchemy import inspect

from backend import create_app
from backend.config import is_production_environment
from backend.migration_runtime import database_engine, revision_status


CRITICAL_TABLES = ("province", "transport_method", "expert_quote")
_TRUE = frozenset({"1", "true", "yes", "on"})


def readiness_report(app) -> dict[str, object]:
    """Return deployment readiness without changing schema or data."""
    report: dict[str, object] = {
        "ready": False,
        "database": "not_ready",
        "migrations": "unknown",
        "critical_tables": "unknown",
    }
    try:
        url = app.config["SQLALCHEMY_DATABASE_URI"]
        status = revision_status(url)
        report["database"] = "connected"
        engine = database_engine(url)
        try:
            report["migrations"] = "pending" if status.pending else "current"
            existing = set(inspect(engine).get_table_names())
            missing = sorted(set(CRITICAL_TABLES) - existing)
            report["critical_tables"] = "missing" if missing else "ready"
            report["missing_tables"] = missing
            report["ready"] = not status.pending and not missing
        finally:
            engine.dispose()
    except Exception:
        # Driver exceptions can contain connection details; keep probe logs
        # deliberately generic and rely on a controlled operator check.
        app.logger.error("Runtime readiness check failed")
    return report


def create_runtime_app():
    """Create the deployable app and enforce non-mutating production gates."""
    if os.getenv("AUTO_MIGRATE_ON_STARTUP", "false").strip().lower() in _TRUE:
        raise RuntimeError(
            "AUTO_MIGRATE_ON_STARTUP is unsupported; run "
            "`python -m backend.migration_cli upgrade --confirm` explicitly"
        )
    app = create_app(skip_startup=True)
    report = readiness_report(app)
    app.extensions["runtime_readiness"] = report
    is_production = is_production_environment(app.config.get("APP_ENV"))
    if is_production and not report["ready"]:
        raise RuntimeError(
            "Production startup blocked: database schema is not ready; "
            "run the read-only migration check and explicit deployment migration"
        )
    if not report["ready"]:
        app.logger.warning("Runtime started non-ready in non-production: %s", report)
    return app


__all__ = ["CRITICAL_TABLES", "create_runtime_app", "readiness_report"]
