"""Sanitized runtime release identity without a live-Git dependency."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from flask import current_app
from sqlalchemy import text

from backend import __version__
from backend.extensions import db

NORMAL_FIELDS = ("application_version",)
SUPPORT_FIELDS = ("application_version", "frontend_version", "backend_version", "release_tag", "short_commit", "database_revision")


def _manifest_path() -> Path | None:
    configured = current_app.config.get("RELEASE_IDENTITY_PATH") or os.getenv("RELEASE_IDENTITY_PATH")
    if configured:
        return Path(configured)
    packaged = Path(current_app.root_path).parent / "release-manifest.json"
    return packaged if packaged.is_file() else None


def _manifest() -> dict[str, Any]:
    path = _manifest_path()
    if not path or not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        current_app.logger.warning("Release identity metadata is unavailable")
        return {}


def _database_revision() -> str | None:
    try:
        return db.session.execute(text("select version_num from alembic_version")).scalar_one_or_none()
    except Exception:
        current_app.logger.warning("Database revision is unavailable for release identity")
        return None


def release_identity(*, support: bool) -> dict[str, Any]:
    """Return only explicitly approved fields for the caller projection."""
    manifest = _manifest()
    commit = manifest.get("git_commit") or os.getenv("FORWARDER_RELEASE_COMMIT")
    values = {
        "application_version": str(manifest.get("application_version") or __version__),
        "frontend_version": manifest.get("frontend_version") or manifest.get("application_version") or __version__,
        "backend_version": manifest.get("backend_version") or __version__,
        "release_tag": manifest.get("git_tag") or os.getenv("FORWARDER_RELEASE_TAG"),
        "short_commit": str(commit)[:12] if commit else None,
        "database_revision": manifest.get("database_revision") or _database_revision(),
    }
    fields = SUPPORT_FIELDS if support else NORMAL_FIELDS
    return {field: values[field] for field in fields}
