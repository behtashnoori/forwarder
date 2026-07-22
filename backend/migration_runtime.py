"""Alembic configuration and revision checks without constructing Flask."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from backend.config import get_database_uri


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
ALEMBIC_INI = MIGRATIONS_DIR / "alembic.ini"


@dataclass(frozen=True)
class RevisionStatus:
    current: tuple[str, ...]
    heads: tuple[str, ...]

    @property
    def pending(self) -> bool:
        return set(self.current) != set(self.heads)


def database_url() -> str:
    """Return the validated URL without logging credentials or importing Flask."""
    return get_database_uri(testing=False)


def safe_database_target(url: str) -> str:
    """Return only dialect and host/database identity; never credentials."""
    parsed = make_url(url)
    host = parsed.host or "local"
    database = parsed.database or "memory"
    return f"{parsed.get_backend_name()}://{host}/{database}"


def alembic_config(url: str | None = None) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("prepend_sys_path", str(MIGRATIONS_DIR.parents[1]))
    # ConfigParser uses percent interpolation; escaped URL components must not
    # be interpreted as configuration placeholders.
    cfg.set_main_option("sqlalchemy.url", (url or database_url()).replace("%", "%%"))
    return cfg


def database_engine(url: str):
    """Create a short-lived probe/CLI engine with a bounded PostgreSQL connect."""
    parsed = make_url(url)
    connect_args = {}
    if parsed.get_backend_name() == "postgresql":
        timeout = max(1, int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5")))
        connect_args["connect_timeout"] = timeout
    return create_engine(
        url,
        poolclass=NullPool,
        connect_args=connect_args,
    )


def revision_status(url: str | None = None) -> RevisionStatus:
    """Inspect current/head revisions without importing or creating Flask."""
    resolved = url or database_url()
    cfg = alembic_config(resolved)
    script = ScriptDirectory.from_config(cfg)
    heads = tuple(sorted(script.get_heads()))
    engine = database_engine(resolved)
    try:
        with engine.connect() as connection:
            current = tuple(sorted(MigrationContext.configure(connection).get_current_heads()))
    finally:
        engine.dispose()
    return RevisionStatus(current=current, heads=heads)


def prepare_version_table_for_upgrade(url: str, cfg: Config) -> None:
    """Widen/validate Alembic version storage only for an explicit upgrade."""
    from backend.migrations.version_table import ensure_version_table_capacity

    script = ScriptDirectory.from_config(cfg)

    def valid_parallel_heads(revisions: tuple[str, ...]) -> bool:
        try:
            current = script.get_all_current(revisions)
        except Exception:
            return False
        return {item.revision for item in current} == set(revisions)

    engine = database_engine(url)
    try:
        with engine.begin() as connection:
            ensure_version_table_capacity(
                connection,
                multiple_revision_validator=valid_parallel_heads,
            )
    finally:
        engine.dispose()


__all__ = [
    "ALEMBIC_INI",
    "MIGRATIONS_DIR",
    "RevisionStatus",
    "alembic_config",
    "database_url",
    "database_engine",
    "prepare_version_table_for_upgrade",
    "revision_status",
    "safe_database_target",
]
