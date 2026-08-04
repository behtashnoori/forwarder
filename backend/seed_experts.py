"""Compatibility entry point for the retired expert credential seed."""

from __future__ import annotations


def seed_experts() -> int:
    """Refuse shared-account creation and direct operators to safe onboarding."""
    print(
        "BLOCKED: shared expert credential seeding is retired. "
        "Create the first administrator with `python manage.py create-admin`, "
        "then create individual users through the authorized administration flow."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(seed_experts())
