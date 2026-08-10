"""Disposable v1.9.0 -> v1.9.1 migration and backup/restore evidence."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Event, Thread
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade
from backend.tests.test_v191_persistence_postgresql import _direct_insert, _seed_v190

BASELINE = "20260818_immutable_fx_provenance"
HEAD = "20260819_v191_acceptance_corrections"
PG_BIN = Path(r"C:\Program Files\PostgreSQL\18\bin")


def main() -> int:
    admin_url = os.environ["DATABASE_URL"]
    parsed = make_url(admin_url)
    if parsed.host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Disposable rehearsal requires loopback PostgreSQL")
    run_id = uuid4().hex[:10]
    source_name = f"forwarder_v191_rc_{run_id}"
    restore_name = f"forwarder_v191_restore_{run_id}"
    source_url = parsed.set(database=source_name).render_as_string(hide_password=False)
    restore_url = parsed.set(database=restore_name).render_as_string(hide_password=False)
    evidence = Path(os.environ.get("V191_RC_EVIDENCE", "docs/operational/evidence/v1.9.1-slice7-rc-hardening/rehearsal"))
    evidence.mkdir(parents=True, exist_ok=True)
    dump_path = evidence / f"synthetic-{run_id}.dump"
    result_path = evidence / f"rehearsal-{run_id}.json"
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    locks: list[dict[str, object]] = []
    stop = Event()
    started = time.time()
    result: dict[str, object] = {"run_id": run_id, "baseline": BASELINE, "head": HEAD}

    def create_database(name: str) -> None:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))

    def drop_database(name: str) -> None:
        with admin.connect() as connection:
            connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"), {"name": name})
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))

    def observe_locks() -> None:
        while not stop.wait(0.01):
            with admin.connect() as connection:
                rows = connection.execute(text(
                    "SELECT mode, granted, count(*) FROM pg_locks l JOIN pg_database d ON d.oid=l.database "
                    "WHERE d.datname=:name GROUP BY mode, granted ORDER BY mode, granted"
                ), {"name": source_name}).all()
            for mode, granted, count in rows:
                sample = {"mode": mode, "granted": bool(granted), "count": int(count)}
                if sample not in locks:
                    locks.append(sample)

    def pg_env(database: str) -> dict[str, str]:
        env = os.environ.copy()
        env.update({"PGHOST": parsed.host or "127.0.0.1", "PGPORT": str(parsed.port or 5432),
                    "PGUSER": parsed.username or "postgres", "PGDATABASE": database})
        if parsed.password:
            env["PGPASSWORD"] = parsed.password
        return env

    try:
        create_database(source_name)
        config = alembic_config(source_url)
        prepare_version_table_for_upgrade(source_url, config)
        command.upgrade(config, BASELINE)
        engine = create_engine(source_url)
        with engine.begin() as connection:
            _seed_v190(connection)
        with engine.connect() as connection:
            before_counts = {table: int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()) for table in ("shipment_request", "expert_quote", "operational_shipment")}
            wal_start = connection.execute(text("SELECT pg_current_wal_lsn()::text")).scalar_one()
        observer = Thread(target=observe_locks, daemon=True)
        observer.start()
        migration_started = time.perf_counter()
        command.upgrade(config, HEAD)
        migration_seconds = time.perf_counter() - migration_started
        stop.set(); observer.join(timeout=2)
        with engine.begin() as connection:
            wal_bytes = int(connection.execute(text("SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), CAST(:start AS pg_lsn))"), {"start": wal_start}).scalar_one())
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            after_counts = {table: int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()) for table in before_counts}
            accepted = connection.execute(text("SELECT count(*) FROM operational_shipment WHERE source_type='accepted_quote' AND shipment_request_id IS NOT NULL AND accepted_quote_id IS NOT NULL")).scalar_one()
            _direct_insert(connection, 9201)
            direct = connection.execute(text("SELECT count(*) FROM operational_shipment WHERE source_type='direct' AND customer_id IS NOT NULL AND shipment_request_id IS NULL AND accepted_quote_id IS NULL")).scalar_one()
        dump = subprocess.run([str(PG_BIN / "pg_dump.exe"), "--format=custom", "--file", str(dump_path)], env=pg_env(source_name), capture_output=True, text=True)
        if dump.returncode:
            raise RuntimeError("pg_dump failed: " + dump.stderr[-500:])
        create_database(restore_name)
        restore = subprocess.run([str(PG_BIN / "pg_restore.exe"), "--exit-on-error", "--no-owner", "--dbname", restore_name, str(dump_path)], env=pg_env(restore_name), capture_output=True, text=True)
        if restore.returncode:
            raise RuntimeError("pg_restore failed: " + restore.stderr[-500:])
        restored = create_engine(restore_url)
        with restored.connect() as connection:
            restored_revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            restored_counts = {table: int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()) for table in before_counts}
            restored_operational = int(connection.execute(text("SELECT count(*) FROM operational_shipment")).scalar_one())
        restored.dispose()
        doc_source = evidence / f"document-source-{run_id}"
        doc_restore = evidence / f"document-restore-{run_id}"
        doc_source.mkdir(); synthetic = doc_source / "synthetic-document.bin"; synthetic.write_bytes(b"Forwarder v1.9.1 synthetic document backup rehearsal\n")
        archive = Path(shutil.make_archive(str(evidence / f"synthetic-documents-{run_id}"), "zip", doc_source))
        shutil.unpack_archive(archive, doc_restore)
        doc_hash = hashlib.sha256(synthetic.read_bytes()).hexdigest()
        restored_hash = hashlib.sha256((doc_restore / synthetic.name).read_bytes()).hexdigest()
        shutil.rmtree(doc_source); shutil.rmtree(doc_restore)
        result.update({"status": "PASS", "migration_seconds": round(migration_seconds, 6), "wal_bytes": wal_bytes,
                       "lock_samples": locks, "blocking_locks_observed": any(not row["granted"] for row in locks),
                       "revision": revision, "row_counts_before": before_counts, "row_counts_after": after_counts,
                       "accepted_quote_rows": int(accepted), "direct_rows": int(direct), "dump_bytes": dump_path.stat().st_size,
                       "restore_revision": restored_revision, "restore_row_counts": restored_counts,
                       "restore_operational_shipments": restored_operational, "document_backup_bytes": archive.stat().st_size,
                       "document_hash_match": doc_hash == restored_hash, "total_seconds": round(time.time() - started, 3)})
        expected_restored = dict(after_counts)
        expected_restored["operational_shipment"] += int(direct)
        if revision != HEAD or restored_revision != HEAD or before_counts != after_counts or restored_counts != expected_restored or not accepted or not direct or doc_hash != restored_hash:
            raise AssertionError("rehearsal verification failed")
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    finally:
        stop.set()
        for name in (restore_name, source_name):
            try: drop_database(name)
            except Exception: pass
        admin.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
