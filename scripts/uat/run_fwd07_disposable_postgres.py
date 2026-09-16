"""Run FWD-07 persistence qualification against an owned loopback PostgreSQL 18 cluster."""
from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
import tempfile
import json
import argparse
import shutil
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boundary-proof", action="store_true", help="only boundary proof and four bounded gate reproductions")
    parser.add_argument("--ci", action="store_true", help="owned backend CI suite")
    parser.add_argument("--browser", action="store_true", help="correlated zero-requirement browser UAT")
    parser.add_argument("--test-target", action="append", help="additional bounded target for boundary proof")
    options = parser.parse_args()
    binary = Path(r"C:\Program Files\PostgreSQL\18\bin") if os.name == "nt" else Path("/usr/lib/postgresql/18/bin")
    suffix = ".exe" if os.name == "nt" else ""
    if not (binary / ("initdb" + suffix)).is_file():
        raise RuntimeError("PostgreSQL 18 binaries are required at the approved local location")
    root = (Path(tempfile.gettempdir()) / f"forwarder-fwd07-qualification-{uuid4().hex}").resolve()
    root.mkdir(mode=0o777)
    data, storage = root / "data", root / "private-storage"
    storage.mkdir()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    # Allowlist: no inherited connection, provider, storage, dotenv or plugin settings.
    environment = {key: value for key, value in os.environ.items() if key.upper() in {
        "SYSTEMROOT", "WINDIR", "PATH", "COMSPEC", "PATHEXT", "SYSTEMDRIVE", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOME", "LANG",
    }}
    temporary = root / "tmp"
    temporary.mkdir()
    environment.update(
        APP_ENV="uat", SECRET_KEY=secrets.token_hex(32), JWT_SECRET_KEY=secrets.token_hex(64),
        DATABASE_URL="sqlite:///:memory:", TEST_DATABASE_URL="sqlite:///:memory:",
        TMP=str(temporary), TEMP=str(temporary), DOCUMENT_STORAGE_ROOT=str(storage),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
    )

    def run(args: list[object], **kwargs: object) -> None:
        command = [str(item) for item in args]
        started_at = datetime.now(timezone.utc).isoformat()
        python_child = command[0] == sys.executable
        if python_child:
            kwargs.update(capture_output=True, text=True)
        result = subprocess.run(command, env=environment, timeout=900, **kwargs)
        event = dict(command=command, started_at=started_at, ended_at=datetime.now(timezone.utc).isoformat(), exit_code=result.returncode)
        with (root / "run-events.jsonl").open("a", encoding="utf-8") as output:
            output.write(json.dumps(event) + "\n")
        if python_child:
            label = "migration" if "backend.migration_cli" in command else "postgres-tests"
            (root / (label + ".txt")).write_text(result.stdout + result.stderr, encoding="utf-8")
            print(result.stdout)
        result.check_returncode()

    negative_command = [sys.executable, "-B", "-m", "scripts.uat.test_boundary_proof"]
    negative = subprocess.run(negative_command, env=environment, capture_output=True, text=True, timeout=60)
    (root / "negative-tests.txt").write_text(negative.stdout + negative.stderr, encoding="utf-8")
    if negative.returncode:
        raise RuntimeError("negative boundary proof failed; no cluster started")
    (root / "negative-result.json").write_text(json.dumps(dict(command=negative_command, exit_code=0, completed_at=datetime.now(timezone.utc).isoformat())), encoding="utf-8")
    run([binary / ("initdb" + suffix), "-D", data, "-U", "fwd07_qualification", "-A", "trust", "--no-locale", "-E", "UTF8"], stdout=subprocess.DEVNULL)
    started = False
    try:
        run([binary / ("pg_ctl" + suffix), "-D", data, "-l", root / "server.log", "-o", f"-h 127.0.0.1 -p {port}", "-w", "start"], stdout=subprocess.DEVNULL)
        started = True
        lines = (data / "postmaster.pid").read_text().splitlines()
        assert Path(lines[1]).resolve() == data and int(lines[3]) == port
        database = f"dms_fwd07_{uuid4().hex}"
        run([binary / ("createdb" + suffix), "-h", "127.0.0.1", "-p", str(port), "-U", "fwd07_qualification", database])
        url = f"postgresql+psycopg2://fwd07_qualification@127.0.0.1:{port}/{database}"
        environment.update(DATABASE_URL=url, FWD07_DISPOSABLE_POSTGRES_URL=url, FWD07_DISPOSABLE_STORAGE_ROOT=str(storage))
        (root / "owner.json").write_text(root.name, encoding="utf-8")
        manifest = dict(run_id=root.name, root=str(root), data=str(data), storage=str(storage),
                        host="127.0.0.1", port=port, database=database, role="fwd07_qualification",
                        postmaster_pid=int(lines[0]), origin="runner-created-initdb",
                        tracked_files=subprocess.check_output(["git", "ls-files", "-z"], cwd=Path(__file__).resolve().parents[2], env=environment).decode("utf-8").strip("\0").split("\0"))
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        repository = Path(__file__).resolve().parents[2]
        environment.update(FWD_TEST_MANIFEST=str(manifest_path), FWD_TEST_GUARD_ACTIVE="1",
                           PYTHONPATH=os.pathsep.join([str(repository / "scripts/uat/boundary_bootstrap"), str(repository)]))
        if options.boundary_proof:
            run([sys.executable, "-B", "-m", "scripts.uat.test_boundary_proof"])
            environment.update(APP_ENV="test", DATABASE_URL="sqlite:///:memory:", TEST_DATABASE_URL="sqlite:///:memory:")
            targets = [
                "backend/tests/test_alembic_version_table.py::test_historical_long_revision_ids_are_detected_and_graph_has_one_feature_head",
                "backend/tests/test_operational_execution_190.py::test_verification_separation_and_one_migration_head",
                "backend/tests/test_project_configuration.py::test_identity_catalog_and_single_head",
                "backend/tests/test_global_logistics_point_materialization.py::test_phase4b_materialized_point_uses_ordinary_tracking_and_project_contracts",
            ]
            targets += options.test_target or []
            command = [sys.executable, "-B", "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider", "--basetemp", str(temporary / "pytest"), *targets]
            result = subprocess.run(command, env=environment, text=True, capture_output=True, timeout=180)
            (root / "four-gates.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
            (root / "gates-result.json").write_text(json.dumps(dict(command=command, exit_code=result.returncode)), encoding="utf-8")
            print(f"FOUR_GATES_EXIT={result.returncode}; evidence={root / 'four-gates.txt'}")
            focused_command = [sys.executable, "-B", "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider", "--basetemp", str(temporary / "focused-pytest"),
                "backend/tests/test_case_documents.py::test_zero_configured_requirements_existing_list_route",
                "backend/tests/test_case_documents.py::test_multi_file_requirement_round_trip_append_and_same_name_safety",
                "backend/tests/test_case_documents.py::test_revoked_assignment_denies_previously_authorized_direct_download",
                "backend/tests/test_tenant_architecture_contract.py::test_every_mapped_model_and_association_table_is_classified"]
            focused = subprocess.run(focused_command, env=environment, capture_output=True, text=True, timeout=60)
            (root / "focused-tests.txt").write_text(focused.stdout + focused.stderr, encoding="utf-8")
            (root / "focused-result.json").write_text(json.dumps(dict(command=focused_command, exit_code=focused.returncode)), encoding="utf-8")
            print(f"FOCUSED_REGRESSION_EXIT={focused.returncode}; evidence={root / 'focused-tests.txt'}")
            if result.returncode or focused.returncode:
                raise RuntimeError("bounded mandatory gates failed")
        elif options.browser:
            browser_uat(root, manifest, manifest_path, environment, repository)
        else:
            run([sys.executable, "-B", "-m", "backend.migration_cli", "upgrade", "--confirm"])
            if options.ci:
                environment.update(APP_ENV="test", DATABASE_URL="sqlite:///:memory:", TEST_DATABASE_URL="sqlite:///:memory:")
            run([sys.executable, "-B", "-m", "pytest", "-q", "--tb=short", "--disable-warnings", "-p", "no:cacheprovider", "--basetemp", str(temporary / "pytest"), "backend/tests" if options.ci else "backend/tests/test_case_documents_postgresql.py"])
    finally:
        if started:
            assert data.resolve().is_relative_to(root)
            # Parent owns these native resources; child guards never grant cleanup authority.
            environment.pop("FWD_TEST_GUARD_ACTIVE", None)
            environment.pop("PYTHONPATH", None)
            current = (data / "postmaster.pid").read_text().splitlines()
            if Path(current[1]).resolve() != data or int(current[0]) != int(lines[0]):
                raise RuntimeError("cleanup ownership mismatch; cluster retained")
            run([binary / ("pg_ctl" + suffix), "-D", data, "-m", "fast", "-w", "stop"], stdout=subprocess.DEVNULL)
            (root / "teardown.json").write_text(json.dumps(dict(owned_cluster_stopped=True, retained=True)), encoding="utf-8")
        print(f"FWD07_DISPOSABLE_CLUSTER_STOPPED; retained diagnostics: {root}")


def browser_uat(root, manifest, manifest_path, environment, repository):
    ports = []
    for _ in range(2):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            ports.append(listener.getsockname()[1])
    api, ui = ports
    manifest["local_endpoints"] = [["127.0.0.1", api], ["127.0.0.1", ui]]
    manifest["browser_database"] = str(root / "browser.sqlite")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    environment.update(APP_ENV="test", FWD07_UAT_PASSWORD=secrets.token_hex(24),
        FWD07_UAT_API_PORT=str(api), FWD07_UAT_BASE_URL=f"http://127.0.0.1:{ui}",
        FWD07_UAT_EVIDENCE_DIR=str(root), VITE_BACKEND_URL=f"http://127.0.0.1:{api}",
        FWD07_UAT_ZERO="1")
    processes = []
    handles = []
    def launch(label, command):
        output = (root / (label + ".out")).open("w", encoding="utf-8")
        error = (root / (label + ".err")).open("w", encoding="utf-8")
        handles.extend([output, error])
        child_env = dict(environment)
        process = subprocess.Popen(command, env=child_env, cwd=repository, stdout=output, stderr=error)
        processes.append((label, process))
        return process
    def ready(url, process):
        deadline = time.monotonic() + 40
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("owned runtime exited before readiness")
            try:
                with opener.open(url, timeout=1) as response:
                    if response.status == 200:
                        return
            except OSError:
                time.sleep(.25)
        raise RuntimeError("owned runtime readiness timeout")
    try:
        backend = launch("backend", [sys.executable, "-B", "-m", "scripts.uat.fwd07_browser_fixture"])
        ready(f"http://127.0.0.1:{api}/api/health", backend)
        node = shutil.which("node")
        if not node:
            raise RuntimeError("Node runtime unavailable")
        frontend = launch("frontend", [node, "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", str(ui), "--strictPort"])
        ready(f"http://127.0.0.1:{ui}", frontend)
        runner = launch("browser", [node, "scripts/uat/fwd07_browser_runner.mjs"])
        (root / "browser-correlation.json").write_text(json.dumps(dict(run_id=manifest["run_id"], manifest=str(manifest_path), database=manifest["browser_database"], storage=manifest["storage"], endpoints=manifest["local_endpoints"], processes={label:p.pid for label,p in processes}), indent=2))
        code = runner.wait(timeout=180)
        if code:
            raise RuntimeError("zero-requirement browser UAT failed")
    finally:
        stopped = {}
        for label, process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=15)
            stopped[label] = dict(pid=process.pid, exit_code=process.returncode)
        for handle in handles:
            handle.close()
        (root / "browser-teardown.json").write_text(json.dumps(stopped, indent=2))


if __name__ == "__main__":
    main()
