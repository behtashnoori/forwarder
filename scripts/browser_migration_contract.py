"""Fail-closed migration contract for disposable browser qualification databases."""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from collections.abc import Iterable
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


class BrowserMigrationContractError(RuntimeError):
    """Raised when browser qualification cannot prove one exact migration head."""


def require_single_head(heads: Iterable[str]) -> str:
    resolved = tuple(heads)
    if len(resolved) != 1:
        raise BrowserMigrationContractError(
            f"expected exactly one repository Alembic head; found {len(resolved)}"
        )
    return resolved[0]


def repository_head() -> str:
    # Repository graph inspection must not depend on a reachable/configured DB.
    migrations = Path(__file__).resolve().parents[1] / "backend" / "migrations"
    config = Config(str(migrations / "alembic.ini"))
    config.set_main_option("script_location", str(migrations))
    script = ScriptDirectory.from_config(config)
    return require_single_head(script.get_heads())


def verify_database_head(expected: str) -> str:
    actual_repository_head = repository_head()
    if expected != actual_repository_head:
        raise BrowserMigrationContractError(
            "requested browser migration target is not the repository Alembic head"
        )
    # The backend package may report local .env loading on stdout. Keep this
    # command's stdout machine-readable for its PowerShell caller.
    with contextlib.redirect_stdout(io.StringIO()):
        from backend.migration_runtime import database_url, revision_status

        status = revision_status(database_url())
    if status.current != (expected,):
        raise BrowserMigrationContractError(
            "browser database revision does not exactly match the repository Alembic head"
        )
    return expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("repository-head")
    verify = subparsers.add_parser("verify-database-head")
    verify.add_argument("--expected", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "repository-head":
            print(repository_head())
        else:
            print(verify_database_head(args.expected))
        return 0
    except BrowserMigrationContractError as exc:
        print(f"Browser migration contract failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
