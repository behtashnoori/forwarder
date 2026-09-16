"""Connection sentinels first; tiny real PostgreSQL proof only in owned child."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.uat import test_boundary as boundary


class NegativeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.manifest = dict(root=tempfile.gettempdir(), host="127.0.0.1", port=25432,
                             database="synthetic_owned", role="synthetic_role", local_endpoints=[["127.0.0.1", 25434], ["127.0.0.1", 25435]])
        self.good = "postgresql+psycopg2://synthetic_role@127.0.0.1:25432/synthetic_owned"

    def test_inherited_configuration(self):
        with self.assertRaisesRegex(RuntimeError, "REJECTED"):
            boundary.validate_environment({"TEST_DATABASE_URL": "postgresql://x@127.0.0.1:5432/synthetic_existing_test"}, self.manifest)

    def test_test_name_is_not_ownership(self):
        with self.assertRaisesRegex(RuntimeError, "REJECTED"):
            boundary.validate_url("postgresql://synthetic_role@127.0.0.1:25432/unowned_test", self.manifest)

    def test_unowned_manifest_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = dict(self.manifest, root=str(root), run_id="synthetic", origin="existing-database")
            (root / "owner.json").write_text("synthetic", encoding="utf-8")
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with patch.dict(os.environ, {"FWD_TEST_MANIFEST": str(path)}), self.assertRaisesRegex(RuntimeError, "provenance"):
                boundary.load_manifest()

    def test_missing_manifest(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, "manifest required"):
            boundary.load_manifest()

    def test_host_port_database_mismatch(self):
        for url in (self.good.replace("127.0.0.1", "localhost"), self.good.replace("25432", "25433"), self.good.replace("synthetic_owned", "other")):
            with self.subTest(url=url), self.assertRaisesRegex(RuntimeError, "REJECTED"):
                boundary.validate_url(url, self.manifest)

    def test_secondary_bind(self):
        for value in ("postgresql://x@127.0.0.1:5432/secondary_test", "postgresql://x@127.0.0.1:5432/secondary_test?service=other"):
            with self.assertRaisesRegex(RuntimeError, "REJECTED"):
                boundary.validate_url(value, self.manifest)

    def test_driver_config_mutation_and_child(self):
        # Entire install uses a synthetic manifest; forbidden connect is a sentinel.
        import psycopg2
        import sqlite3
        import socket
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        before = (sqlite3.connect, subprocess.Popen, socket.socket.connect, socket.socket.connect_ex)
        sentinel = Mock(side_effect=AssertionError("CONNECTION ATTEMPT"))
        old_installed, old_manifest, old_listener = boundary.INSTALLED, boundary.MANIFEST, boundary.DO_CONNECT_LISTENER
        try:
            boundary.INSTALLED = False
            with patch.object(boundary, "load_manifest", return_value=self.manifest), patch.dict(os.environ, {"FWD_TEST_GUARD_ACTIVE": "1", "PYTHONPATH": "synthetic-bootstrap", "APP_ENV": "test", "DOCUMENT_STORAGE_ROOT": tempfile.gettempdir()}, clear=True), patch.object(psycopg2, "connect", sentinel):
                boundary.install()
                boundary.validate_url(self.good, self.manifest)
                from sqlalchemy import create_engine
                for value in (self.good.replace("25432", "25433"), self.good.replace("127.0.0.1", "localhost"), self.good.replace("synthetic_owned", "unowned_test")):
                    engine = create_engine(value)
                    with self.assertRaisesRegex(RuntimeError, "REJECTED"):
                        engine.connect()
                    engine.dispose()
                from backend import create_app
                with self.assertRaisesRegex(RuntimeError, "REJECTED"):
                    create_app({"TESTING": True, "SQLALCHEMY_BINDS": {"secondary": self.good.replace("synthetic_owned", "secondary_test")}})
                with self.assertRaisesRegex(RuntimeError, "REJECTED"):
                    psycopg2.connect(host="127.0.0.1", port=5432, dbname="changed_test", user="x")
                child = dict(os.environ, DATABASE_URL="postgresql://x@127.0.0.1:5432/child_test")
                with self.assertRaisesRegex(RuntimeError, "REJECTED"):
                    subprocess.Popen([sys.executable, "-c", "pass"], env=child)
                with socket.socket() as sock:
                    for address in (("127.0.0.1", 25436), ("localhost", 25434), ("example.invalid", 443)):
                        with self.assertRaisesRegex(RuntimeError, "REJECTED"):
                            sock.connect(address)
                sentinel.assert_not_called()
        finally:
            sqlite3.connect = sqlite3.dbapi2.connect = before[0]
            subprocess.Popen, socket.socket.connect, socket.socket.connect_ex = before[1:]
            event.remove(Engine, "do_connect", boundary.DO_CONNECT_LISTENER)
            boundary.DO_CONNECT_LISTENER = old_listener
            boundary.INSTALLED, boundary.MANIFEST = old_installed, old_manifest

    def test_direct_pytest_rejected(self):
        env = {key: value for key, value in os.environ.items() if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE"}}
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        result = subprocess.run([sys.executable, "-B", "-m", "pytest", "--collect-only", "-q", "backend/tests/test_tenant_architecture_contract.py"], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("direct pytest has no approved", result.stdout + result.stderr)
        fixture = subprocess.run([sys.executable, "-B", "-m", "scripts.uat.fwd07_browser_fixture"], env=env, capture_output=True, text=True)
        self.assertNotEqual(fixture.returncode, 0)
        self.assertIn("browser fixture requires approved bootstrap", fixture.stdout + fixture.stderr)


def main():
    if not boundary.INSTALLED:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NegativeBoundaryTests))
        if not result.wasSuccessful():
            raise SystemExit(1)
        print("NEGATIVE_PRECONNECTION_PASS; sentinel calls=0; no PostgreSQL connection performed")
        return
    import psycopg2
    from sqlalchemy.engine import make_url
    manifest = boundary.MANIFEST
    url = make_url(os.environ["FWD07_DISPOSABLE_POSTGRES_URL"])
    connection = psycopg2.connect(host=url.host, port=url.port, dbname=url.database, user=url.username)
    with connection, connection.cursor() as cursor:
        cursor.execute("CREATE TABLE boundary_synthetic (value integer NOT NULL)")
        cursor.execute("INSERT INTO boundary_synthetic VALUES (7)")
        cursor.execute("SELECT value FROM boundary_synthetic")
        assert cursor.fetchone() == (7,)
        cursor.execute("DROP TABLE boundary_synthetic")
    connection.close()
    (Path(manifest["root"]) / "positive-result.json").write_text(json.dumps(dict(startup=True, server_attested=True, synthetic_write_read=True, synthetic_table_removed=True)), encoding="utf-8")
    print("OWNED_POSTGRESQL_POSITIVE_PASS")


if __name__ == "__main__":
    main()
