"""Run one governed PostgreSQL read-only SQL payload without exposing secrets.

The Production launcher uses python-dotenv and SQLAlchemy URL parsing.  This
bridge deliberately uses the same two libraries, then passes the password to
psql only through its child-process environment.  The URL and password are
never written, printed, or placed on the command line.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

from dotenv import dotenv_values
from sqlalchemy.engine import URL, make_url


READ_ONLY_START = re.compile(r"^\s*BEGIN\s+TRANSACTION\s+READ\s+ONLY\s*;", re.I | re.S)
READ_ONLY_END = re.compile(r"COMMIT\s*;\s*$", re.I | re.S)
MUTATION_KEYWORD = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|ALTER|CREATE|DROP|TRUNCATE|GRANT|REVOKE|"
    r"VACUUM|REINDEX|CALL|DO)\b",
    re.I | re.M,
)
LIBPQ_QUERY_ENV = {
    "application_name": "PGAPPNAME",
    "connect_timeout": "PGCONNECT_TIMEOUT",
    "sslcert": "PGSSLCERT",
    "sslcrl": "PGSSLCRL",
    "sslkey": "PGSSLKEY",
    "sslmode": "PGSSLMODE",
    "sslrootcert": "PGSSLROOTCERT",
    "target_session_attrs": "PGTARGETSESSIONATTRS",
}


class BridgeError(RuntimeError):
    """A sanitized, operator-actionable bridge failure."""


def assert_read_only_sql(sql: str) -> None:
    if not READ_ONLY_START.search(sql) or not READ_ONLY_END.search(sql):
        raise BridgeError("SQL_READ_ONLY_ENVELOPE_INVALID")
    if MUTATION_KEYWORD.search(sql):
        raise BridgeError("SQL_MUTATION_KEYWORD_REJECTED")


def load_connection_url(environment_file: Path) -> URL:
    try:
        values = dotenv_values(environment_file)
    except Exception as exc:  # pragma: no cover - defensive library boundary
        raise BridgeError("PRODUCTION_ENV_LOAD_FAILED") from exc
    raw = values.get("DATABASE_URL")
    if not raw:
        raise BridgeError("DATABASE_URL_ABSENT")
    try:
        url = make_url(str(raw))
    except Exception as exc:
        raise BridgeError("DATABASE_URL_INVALID") from exc
    if url.get_backend_name() != "postgresql":
        raise BridgeError("DATABASE_URL_NOT_POSTGRESQL")
    if not url.host or not url.username or not url.database:
        raise BridgeError("DATABASE_URL_IDENTITY_INCOMPLETE")
    return url


def _query_value(value: object) -> str:
    if isinstance(value, tuple):
        if len(value) != 1:
            raise BridgeError("DATABASE_URL_QUERY_VALUE_AMBIGUOUS")
        return str(value[0])
    return str(value)


def build_psql_invocation(
    *, psql_path: Path, url: URL, inherited_environment: dict[str, str] | None = None
) -> tuple[list[str], dict[str, str]]:
    if not psql_path.is_file():
        raise BridgeError("PSQL_NOT_AVAILABLE")
    command = [
        str(psql_path),
        "-X",
        "-w",
        "-q",
        "-A",
        "-t",
        "-F",
        "|",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        str(url.host),
        "-p",
        str(url.port or 5432),
        "-U",
        str(url.username),
        "-d",
        str(url.database),
    ]
    environment = dict(inherited_environment if inherited_environment is not None else os.environ)
    if url.password is not None:
        environment["PGPASSWORD"] = str(url.password)
    for key, value in url.query.items():
        target = LIBPQ_QUERY_ENV.get(str(key).lower())
        if target:
            environment[target] = _query_value(value)
    return command, environment


def run_read_only_sql(
    *, environment_file: Path, psql_path: Path, sql: str, timeout_seconds: int = 120
) -> str:
    assert_read_only_sql(sql)
    url = load_connection_url(environment_file)
    command, environment = build_psql_invocation(psql_path=psql_path, url=url)
    try:
        completed = subprocess.run(
            command,
            input=sql,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        raise BridgeError("PSQL_TIMEOUT") from exc
    except OSError as exc:
        raise BridgeError("PSQL_START_FAILED") from exc
    finally:
        environment.pop("PGPASSWORD", None)
        url = URL.create("postgresql")
    if completed.returncode != 0:
        # Do not relay arbitrary stderr: fixed reason codes prevent an unusual
        # server/client message from reflecting connection material.
        raise BridgeError(f"PSQL_FAILED_EXIT_{completed.returncode}")
    return completed.stdout


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment-file", required=True, type=Path)
    parser.add_argument("--psql", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    sql = sys.stdin.read()
    try:
        output = run_read_only_sql(
            environment_file=args.environment_file,
            psql_path=args.psql,
            sql=sql,
        )
    except BridgeError as exc:
        print(f"READ_ONLY_DATABASE_BRIDGE_ERROR={exc}", file=sys.stderr)
        return 2
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
