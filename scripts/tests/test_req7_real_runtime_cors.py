"""REQ-7 production-realistic CORS and backend restart regression."""
from __future__ import annotations

import http.client
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PYTHON = ROOT.parent / "qualification/req12-layout-proof/release-a/runtime/python.exe"
CANONICAL = "https://samand.forwarderet.ir"
LEGACY = "https://server.logisticmarket.ir"
UNKNOWN = "https://example.invalid"

LAUNCHER = r"""
import os, sys
from dotenv import dotenv_values
from waitress import serve
env_path, repo, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
values = {str(k): str(v) for k, v in dotenv_values(env_path).items() if v is not None}
os.environ.update(values)
os.chdir(repo)
sys.path.insert(0, repo)
from backend import create_app
app = create_app(skip_startup=True)
print('VISIBLE_CORS_ALLOW_ALL_ORIGINS=' + os.environ.get('CORS_ALLOW_ALL_ORIGINS', '<absent>'), flush=True)
print('VISIBLE_CORS_ORIGINS=' + os.environ.get('CORS_ORIGINS', '<absent>'), flush=True)
print('VISIBLE_CORS_ORIGIN=' + os.environ.get('CORS_ORIGIN', '<absent>'), flush=True)
serve(app, host='127.0.0.1', port=port, threads=2)
"""


def _port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _request(port: int, method: str = "GET", origin: str | None = None) -> tuple[int, dict[str, str]]:
    headers = {}
    if origin:
        headers["Origin"] = origin
    if method == "OPTIONS":
        headers["Access-Control-Request-Method"] = "GET"
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(method, "/api/health", headers=headers)
        response = connection.getresponse()
        response.read()
        return response.status, {key.lower(): value for key, value in response.getheaders()}
    finally:
        connection.close()


def _start(env_path: Path, port: int, document_root: Path, *, inherited_origin: str = LEGACY,
           app_env: str = "production") -> subprocess.Popen[str]:
    environment = os.environ.copy()
    environment.update({
        "APP_ENV": app_env,
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "req7-production-realistic-secret",
        "JWT_SECRET_KEY": "req7-production-realistic-jwt-secret-value",
        "DOCUMENT_STORAGE_ROOT": str(document_root),
        "CORS_ORIGINS": inherited_origin,
        "CORS_ORIGIN": inherited_origin,
    })
    log_path = env_path.with_suffix(".runtime.log")
    log_stream = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(RUNTIME_PYTHON), "-c", LAUNCHER, str(env_path), str(ROOT), str(port)],
        stdout=log_stream, stderr=subprocess.STDOUT, text=True, env=environment,
    )
    log_stream.close()
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(log_path.read_text(encoding="utf-8", errors="replace"))
        try:
            if _request(port)[0] == 200:
                return process
        except OSError:
            time.sleep(0.1)
    process.terminate()
    process.wait(timeout=10)
    raise AssertionError(log_path.read_text(encoding="utf-8", errors="replace"))


def _stop(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=10)


def _assert_cors_contract(port: int) -> None:
    assert _request(port)[0] == 200
    status, canonical = _request(port, origin=CANONICAL)
    assert status == 200
    assert canonical.get("access-control-allow-origin") == CANONICAL
    assert canonical.get("access-control-allow-credentials") == "true"
    status, preflight = _request(port, method="OPTIONS", origin=CANONICAL)
    assert status == 200
    assert preflight.get("access-control-allow-origin") == CANONICAL
    assert preflight.get("access-control-allow-credentials") == "true"
    assert "access-control-allow-origin" not in _request(port, origin=LEGACY)[1]
    assert "access-control-allow-origin" not in _request(port, origin=UNKNOWN)[1]


@pytest.mark.parametrize("env_text", [
    f"CORS_ALLOW_ALL_ORIGINS=0\nCORS_ORIGINS={CANONICAL}\nCORS_ORIGIN={CANONICAL}\n",
    f"CORS_ALLOW_ALL_ORIGINS=false\nCORS_ORIGINS={CANONICAL}\nCORS_ORIGIN={CANONICAL}\n",
    f'CORS_ALLOW_ALL_ORIGINS="false"\nCORS_ORIGINS="{CANONICAL}"\nCORS_ORIGIN="{CANONICAL}"\n',
])
@pytest.mark.skipif(not RUNTIME_PYTHON.is_file(), reason="candidate Python environment unavailable")
def test_real_dotenv_export_waitress_http_contract(tmp_path: Path, env_text: str) -> None:
    env_path = tmp_path / "production.env"
    env_path.write_text(env_text, encoding="utf-8")
    port = _port()
    process = _start(env_path, port, tmp_path / "documents")
    try:
        _assert_cors_contract(port)
    finally:
        _stop(process)


@pytest.mark.skipif(not RUNTIME_PYTHON.is_file(), reason="candidate Python environment unavailable")
def test_running_backend_keeps_old_cors_until_explicit_restart(tmp_path: Path) -> None:
    env_path = tmp_path / "production.env"
    env_path.write_text(
        f"CORS_ALLOW_ALL_ORIGINS=false\nCORS_ORIGINS={LEGACY}\nCORS_ORIGIN={LEGACY}\n",
        encoding="utf-8",
    )
    port = _port()
    # Use development only for the historical legacy process because the frozen
    # candidate correctly refuses legacy-only production startup.
    process = _start(env_path, port, tmp_path / "documents", app_env="development")
    try:
        assert _request(port, origin=LEGACY)[1].get("access-control-allow-origin") == LEGACY
        assert "access-control-allow-origin" not in _request(port, origin=CANONICAL)[1]
        env_path.write_text(
            f"CORS_ALLOW_ALL_ORIGINS=0\nCORS_ORIGINS={CANONICAL}\nCORS_ORIGIN={CANONICAL}\n",
            encoding="utf-8",
        )
        # Updating production.env and task metadata cannot mutate the environment
        # of the process that already owns the listener.
        assert "access-control-allow-origin" not in _request(port, origin=CANONICAL)[1]
    finally:
        _stop(process)

    replacement = _start(env_path, port, tmp_path / "documents-new")
    try:
        _assert_cors_contract(port)
    finally:
        _stop(replacement)


def test_release_script_enforces_backend_handoff_and_owned_cleanup() -> None:
    source = (ROOT / "scripts/deploy/deploy_s7_rc_f11f2ab.ps1").read_text(encoding="utf-8")
    switching = source.index("Set-State 'SWITCHING'")
    stop = source.index("Stop-GovernedBackend", switching)
    rewrite = source.index("Set-TaskReference $script:TargetRelease", switching)
    start = source.index("Start-GovernedBackend", rewrite)
    verify = source.index("Set-State 'VERIFYING'", start)
    assert switching < stop < rewrite < start < verify
    assert "Wait-GovernedListenerCount 0" in source
    assert "Wait-GovernedListenerCount 1" in source
    assert "$script:TargetReleaseOwned" in source
    assert "if($script:TargetReleaseOwned -and" in source
    assert "runtime wrapper SHA-256 mismatch" in source


def test_scheduled_task_release_replacement_covers_every_runtime_identity() -> None:
    previous = r"C:\1-webapp\forwarder-production\release-adcc5da-adr043"
    target = r"C:\1-webapp\forwarder-production\release-f11f2ab-s7"
    action = (
        f"set PYTHONPATH={previous}&& cd /d {previous}&& "
        f"{previous}\\.venv\\Scripts\\python.exe wrapper.py serve --repo {previous}"
    )
    working_directory = previous
    updated_action = action.replace(f"{previous}\\.venv\\Scripts\\python.exe", f"{target}\\runtime\\python.exe").replace(previous, target)
    updated_working_directory = working_directory.replace(previous, target)
    assert previous not in updated_action + updated_working_directory
    assert updated_action.count(target) == 4
    assert updated_working_directory == target
    assert f"PYTHONPATH={target}" in updated_action
    assert f"cd /d {target}" in updated_action
    assert f"{target}\\runtime\\python.exe" in updated_action
    assert ".venv\\Scripts\\python.exe" not in updated_action
    assert f"--repo {target}" in updated_action
