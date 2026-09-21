"""Shared backend test configuration.

The backend test suite should never fall back to a developer or production
DATABASE_URL. Tests use an isolated SQLite database by default unless a test
explicitly overrides the URI.
"""
from __future__ import annotations

import os

TEST_DATABASE_URI = "sqlite:///:memory:"

# A developer shell may already carry a user-local database URL.  The default
# suite is deliberately isolated; PostgreSQL proofs use their own explicit,
# test-specific environment variables and application configurations.
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URI
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-for-pytest-only-32-key-for-pytest-only-32")
