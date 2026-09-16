"""Fail-closed boundary for the existing FWD07 runner (not product policy)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

INSTALLED = False
MANIFEST = None
DO_CONNECT_LISTENER = None


def deny(reason):
    raise RuntimeError("TEST_BOUNDARY_REJECTED: " + reason)


def load_manifest():
    path = os.environ.get("FWD_TEST_MANIFEST")
    if not path:
        deny("owned-run manifest required; use run_fwd07_disposable_postgres.py")
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    root = Path(manifest["root"]).resolve()
    if Path(path).resolve().parent != root or not manifest.get("run_id"):
        deny("manifest identity")
    if (root / "owner.json").read_text(encoding="utf-8") != manifest["run_id"]:
        deny("runner ownership marker")
    if manifest["origin"] != "runner-created-initdb" or manifest["host"] != "127.0.0.1":
        deny("resource creation provenance")
    data = Path(manifest["data"]).resolve()
    if not data.is_relative_to(root):
        deny("data directory ownership")
    lines = (data / "postmaster.pid").read_text().splitlines()
    if Path(lines[1]).resolve() != data or int(lines[3]) != manifest["port"] or int(lines[0]) != manifest["postmaster_pid"]:
        deny("owned cluster identity")
    endpoints = manifest.get("local_endpoints", [])
    if len(endpoints) > 2 or any(not isinstance(endpoint, list) or len(endpoint) != 2 or endpoint[0] != "127.0.0.1" or type(endpoint[1]) is not int or not 1024 <= endpoint[1] <= 65535 for endpoint in endpoints):
        deny("invalid owned local endpoints")
    if "browser_database" in manifest and not Path(manifest["browser_database"]).resolve().is_relative_to(root):
        deny("browser database outside run")
    return manifest


def validate_url(value, manifest):
    from sqlalchemy.engine import make_url
    url = make_url(value)
    if url.get_backend_name() == "sqlite":
        if url.query:
            deny("SQLite query/URI overrides")
        if url.database not in (None, "", ":memory:") and not Path(url.database).resolve().is_relative_to(Path(manifest["root"]).resolve()):
            deny("SQLite file outside owned run")
        return
    if url.get_backend_name() != "postgresql" or url.query or url.password:
        deny("unsupported destination or connection overrides")
    if (url.host, url.port, url.database, url.username) != (manifest["host"], manifest["port"], manifest["database"], manifest["role"]):
        deny("host/port/database/role mismatch")


def validate_environment(environment, manifest):
    if environment.get("FWD_TEST_MANIFEST") != os.environ.get("FWD_TEST_MANIFEST"):
        deny("child manifest mismatch")
    for key, value in environment.items():
        if key.startswith("PG"):
            deny("inherited PostgreSQL configuration")
        if "DATABASE_URL" in key or key.endswith("POSTGRES_URL"):
            validate_url(value, manifest)


def validate_storage(value):
    if not INSTALLED:
        deny("boundary not installed")
    if not value or not Path(value).resolve().is_relative_to(Path(MANIFEST["root"]).resolve()):
        deny("storage outside owned run")


def install():
    global INSTALLED, MANIFEST, DO_CONNECT_LISTENER
    if INSTALLED:
        return
    manifest = load_manifest()
    validate_environment(os.environ, manifest)
    # Import drivers only after the manifest/environment check, before app/plugins.
    import psycopg2
    from psycopg2.extensions import parse_dsn
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    original_connect = psycopg2.connect

    def guarded_connect(dsn=None, *args, **kwargs):
        if args or kwargs.get("connection_factory") or kwargs.get("async_") or kwargs.get("async"):
            deny("unsupported driver connection mode")
        params = parse_dsn(dsn or "")
        params.update(kwargs)
        allowed = {"host", "port", "dbname", "database", "user", "connect_timeout", "application_name"}
        if set(params) - allowed:
            deny("driver connection overrides")
        identity = (params.get("host"), int(params.get("port", 0)), params.get("dbname", params.get("database")), params.get("user"))
        if identity != (manifest["host"], manifest["port"], manifest["database"], manifest["role"]):
            deny("final driver destination mismatch")
        load_manifest()  # recheck live ownership immediately before connection
        connection = original_connect(dsn, **kwargs) if dsn else original_connect(**kwargs)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), current_user, host(inet_server_addr()), inet_server_port(), current_setting('data_directory')")
                database, role, host, port, directory = cursor.fetchone()
            (Path(manifest["root"]) / "server-attestation.json").write_text(json.dumps(dict(database=database, role=role, host=host, port=port, data=directory)), encoding="utf-8")
            if (database, role, host, port, Path(directory).resolve()) != (manifest["database"], manifest["role"], manifest["host"], manifest["port"], Path(manifest["data"]).resolve()):
                deny("server identity attestation failed")
            connection.rollback()
            return connection
        except BaseException:
            connection.close()
            raise

    psycopg2.connect = guarded_connect
    import sqlite3
    import sqlite3.dbapi2
    sqlite_connect = sqlite3.connect

    def guarded_sqlite(database, *args, **kwargs):
        if kwargs.get("uri"):
            deny("SQLite URI overrides")
        validate_url("sqlite:///" + str(database), manifest)
        return sqlite_connect(database, *args, **kwargs)

    sqlite3.connect = sqlite3.dbapi2.connect = guarded_sqlite

    @event.listens_for(Engine, "do_connect")
    def before_connect(dialect, record, args, params):
        # The final DBAPI args are checked by the driver as well as the engine URL.
        if dialect.name == "sqlite":
            validate_url("sqlite:///" + str(args[0]), manifest)
        elif dialect.name != "postgresql" or dialect.driver != "psycopg2":
            deny("unsupported DBAPI driver")
    DO_CONNECT_LISTENER = before_connect

    original_popen = subprocess.Popen

    class GuardedPopen(original_popen):
        def __init__(self, *args, **kwargs):
            import sys
            command = args[0] if args else kwargs.get("args")
            if kwargs.get("shell") or not isinstance(command, (list, tuple)) or Path(command[0]).resolve() != Path(sys.executable).resolve() or any(flag in command for flag in ("-S", "-I", "-E")):
                deny("child must use guarded Python bootstrap")
            child = kwargs.get("env", os.environ)
            validate_environment(child, manifest)
            if child.get("PYTHONPATH") != os.environ.get("PYTHONPATH") or child.get("FWD_TEST_GUARD_ACTIVE") != "1":
                deny("child bootstrap missing")
            super().__init__(*args, **kwargs)

    subprocess.Popen = GuardedPopen
    # No real message/API network can escape this test process.
    import socket
    original_socket_connect = socket.socket.connect

    def guarded_socket_connect(sock, address):
        if address not in [(manifest["host"], manifest["port"]), *[tuple(endpoint) for endpoint in manifest.get("local_endpoints", [])]]:
            deny("network destination outside owned run endpoints")
        return original_socket_connect(sock, address)

    socket.socket.connect = guarded_socket_connect
    original_connect_ex = socket.socket.connect_ex

    def guarded_connect_ex(sock, address):
        if address not in [(manifest["host"], manifest["port"]), *[tuple(endpoint) for endpoint in manifest.get("local_endpoints", [])]]:
            deny("network destination outside owned run endpoints")
        return original_connect_ex(sock, address)

    socket.socket.connect_ex = guarded_connect_ex
    MANIFEST = manifest
    INSTALLED = True
