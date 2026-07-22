"""Deprecated wrapper for the explicit migration CLI."""
from __future__ import annotations

import sys

from backend.migration_cli import main as migration_main


def run_migrations() -> bool:
    print(
        "Deprecated wrapper: use `python -m backend.migration_cli upgrade --confirm`.",
        file=sys.stderr,
    )
    return migration_main(["upgrade", "--confirm"]) == 0


if __name__ == "__main__":
    raise SystemExit(0 if run_migrations() else 1)
