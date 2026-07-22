"""Explicit migration commands: current, check, and upgrade."""
from __future__ import annotations

import argparse
import sys

from alembic import command

from backend.migration_runtime import (
    alembic_config,
    database_url,
    prepare_version_table_for_upgrade,
    revision_status,
    safe_database_target,
)


def _format(revisions: tuple[str, ...]) -> str:
    return ",".join(revisions) if revisions else "<base>"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explicit, non-secret Alembic operations")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("current", help="show stored and repository revisions (read-only)")
    subparsers.add_parser("check", help="exit non-zero when migrations are pending (read-only)")
    upgrade = subparsers.add_parser("upgrade", help="explicitly upgrade the configured database")
    upgrade.add_argument("revision", nargs="?", default="head")
    upgrade.add_argument(
        "--confirm",
        action="store_true",
        help="required confirmation that the target was reviewed",
    )
    args = parser.parse_args(argv)

    url = database_url()
    target = safe_database_target(url)
    if args.command in {"current", "check"}:
        status = revision_status(url)
        print(f"database={target}")
        print(f"current={_format(status.current)}")
        print(f"heads={_format(status.heads)}")
        print(f"pending={'yes' if status.pending else 'no'}")
        return 2 if args.command == "check" and status.pending else 0

    if not args.confirm:
        print("Refusing upgrade: pass --confirm after reviewing the sanitized target.", file=sys.stderr)
        print(f"database={target}", file=sys.stderr)
        return 2
    print(f"Applying explicit migration to {target}; revision={args.revision}")
    cfg = alembic_config(url)
    prepare_version_table_for_upgrade(url, cfg)
    command.upgrade(cfg, args.revision)
    print("Migration completed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Do not echo driver messages: they may include sensitive connection
        # details. Operators can correlate the exception class with server logs.
        print(f"Migration command failed ({type(exc).__name__}).", file=sys.stderr)
        raise SystemExit(1) from None
