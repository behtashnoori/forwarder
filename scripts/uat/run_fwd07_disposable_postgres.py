"""Run FWD-07 persistence qualification against an owned loopback PostgreSQL 18 cluster."""
from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4


def main() -> None:
    binary = Path(r"C:\Program Files\PostgreSQL\18\bin")
    if not (binary / "initdb.exe").is_file():
        raise RuntimeError("PostgreSQL 18 binaries are required at the approved local location")
    root = (Path(tempfile.gettempdir()) / f"forwarder-fwd07-qualification-{uuid4().hex}").resolve()
    root.mkdir(mode=0o777)
    data, storage = root / "data", root / "private-storage"
    storage.mkdir()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = dict(os.environ)
    for key in list(environment):
        if "DATABASE_URL" in key or key.startswith("PG"):
            del environment[key]
    environment.update(
        APP_ENV="uat", SECRET_KEY=secrets.token_hex(32), JWT_SECRET_KEY=secrets.token_hex(64),
        DATABASE_URL="sqlite:///:memory:", TEST_DATABASE_URL="sqlite:///:memory:",
    )

    def run(args: list[object], **kwargs: object) -> None:
        subprocess.run([str(item) for item in args], env=environment, check=True, **kwargs)

    run([binary / "initdb.exe", "-D", data, "-U", "fwd07_qualification", "-A", "trust", "--no-locale", "-E", "UTF8"], stdout=subprocess.DEVNULL)
    started = False
    try:
        run([binary / "pg_ctl.exe", "-D", data, "-l", root / "server.log", "-o", f"-h 127.0.0.1 -p {port}", "-w", "start"], stdout=subprocess.DEVNULL)
        started = True
        lines = (data / "postmaster.pid").read_text().splitlines()
        assert Path(lines[1]).resolve() == data and int(lines[3]) == port
        database = f"dms_fwd07_{uuid4().hex}"
        run([binary / "createdb.exe", "-h", "127.0.0.1", "-p", str(port), "-U", "fwd07_qualification", database])
        url = f"postgresql+psycopg2://fwd07_qualification@127.0.0.1:{port}/{database}"
        environment.update(DATABASE_URL=url, DMS_DISPOSABLE_POSTGRES_URL=url, DMS_DISPOSABLE_STORAGE_ROOT=str(storage))
        run([sys.executable, "-B", "-m", "backend.migration_cli", "upgrade", "--confirm"])
        run([sys.executable, "-B", "-m", "pytest", "-q", "--tb=short", "--disable-warnings", "-p", "no:cacheprovider", "backend/tests/test_case_documents_postgresql.py"])
    finally:
        if started:
            assert data.resolve().is_relative_to(root)
            run([binary / "pg_ctl.exe", "-D", data, "-m", "fast", "-w", "stop"], stdout=subprocess.DEVNULL)
        print(f"FWD07_DISPOSABLE_CLUSTER_STOPPED; retained diagnostics: {root}")


if __name__ == "__main__":
    main()
