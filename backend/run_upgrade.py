"""Backward-compatible wrapper for the explicit migration CLI."""
from __future__ import annotations

import sys


def main() -> int:
    from backend.migration_cli import main as migration_main

    print(
        "Deprecated wrapper: use `python -m backend.migration_cli upgrade --confirm`.",
        file=sys.stderr,
    )
    return migration_main(["upgrade", "--confirm"])


if __name__ == "__main__":
    raise SystemExit(main())
