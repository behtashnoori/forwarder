"""REQ-8 real Windows process topology and safe listener ownership tests."""
from __future__ import annotations

import http.client
import os
from pathlib import Path
import socket
import subprocess
import time

import psutil
import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PYTHON = ROOT.parent / "qualification/req12-layout-proof/release-a/runtime/python.exe"
WRAPPER = ROOT / "scripts/tests/fixtures/req8_execv_waitress_wrapper.py"
CANONICAL = "https://samand.forwarderet.ir"


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def listeners(port: int) -> list[psutil.Process]:
    found = []
    for connection in psutil.net_connections(kind="tcp"):
        if connection.status == psutil.CONN_LISTEN and connection.laddr.port == port and connection.pid:
            found.append(psutil.Process(connection.pid))
    return found


def wait_listener_count(port: int, expected: int, timeout: float = 20) -> list[psutil.Process]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = listeners(port)
        if len(found) == expected:
            return found
        time.sleep(0.1)
    raise AssertionError(f"listener count did not become {expected}: {len(listeners(port))}")


def governed_listener(port: int, identity_signal: str) -> psutil.Process:
    found = listeners(port)
    if len(found) != 1:
        raise RuntimeError("governed listener identity is ambiguous")
    process = found[0]
    command = " ".join(process.cmdline()).lower().replace("/", "\\")
    required = (identity_signal.lower().replace("/", "\\"), "-m waitress", "req8_candidate_wsgi:app")
    if not all(signal in command for signal in required):
        raise RuntimeError(f"listener does not match governed Forwarder identity: {command}")
    return process


def safe_stop(port: int, identity_signal: str) -> int:
    process = governed_listener(port, identity_signal)
    process.terminate()
    try:
        process.wait(timeout=10)
    except psutil.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    wait_listener_count(port, 0, timeout=10)
    return process.pid


def request(port: int, method: str = "GET", origin: str | None = None) -> tuple[int, dict[str, str]]:
    headers = {"Origin": origin} if origin else {}
    if method == "OPTIONS":
        headers["Access-Control-Request-Method"] = "GET"
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(method, "/api/health", headers=headers)
        response = connection.getresponse(); response.read()
        return response.status, {key.lower(): value for key, value in response.getheaders()}
    finally:
        connection.close()


def launch(tmp_path: Path, port: int) -> subprocess.Popen[str]:
    env_path = tmp_path / "production.env"
    env_path.write_text(
        "APP_ENV=production\nDATABASE_URL=sqlite:///:memory:\n"
        "SECRET_KEY=req8-production-realistic-secret\n"
        "JWT_SECRET_KEY=req8-production-realistic-jwt-secret-value\n"
        f"DOCUMENT_STORAGE_ROOT={tmp_path / 'documents'}\n"
        "CORS_ALLOW_ALL_ORIGINS=false\n"
        f"CORS_ORIGINS={CANONICAL}\nCORS_ORIGIN={CANONICAL}\n",
        encoding="utf-8",
    )
    command = (
        f'"{os.environ["COMSPEC"]}" /d /c ""{RUNTIME_PYTHON}" "{WRAPPER}" '
        f'"{env_path}" "{ROOT}" {port}"'
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    log_stream = (tmp_path / "process.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        stdout=log_stream, stderr=subprocess.STDOUT, text=True, env=environment,
    )
    log_stream.close()
    return process


@pytest.mark.skipif(os.name != "nt" or not RUNTIME_PYTHON.is_file(), reason="Windows candidate runtime required")
def test_cmd_packaged_runtime_waitress_identity_and_safe_listener_stop(tmp_path: Path) -> None:
    port = free_port()
    controller = launch(tmp_path, port)
    try:
        listener = wait_listener_count(port, 1)[0]
    except AssertionError as exc:
        raise AssertionError((tmp_path / "process.log").read_text(encoding="utf-8", errors="replace")) from exc
    try:
        identity_signal = listener.exe()
        listener = governed_listener(port, identity_signal)
        command = " ".join(listener.cmdline())
        assert str(RUNTIME_PYTHON).lower() in command.lower()
        assert listener.exe().lower() == str(RUNTIME_PYTHON).lower()
        assert request(port)[0] == 200
        assert request(port, origin=CANONICAL)[1]["access-control-allow-origin"] == CANONICAL
        assert request(port, method="OPTIONS", origin=CANONICAL)[1]["access-control-allow-origin"] == CANONICAL

        # The task-like controller may exit after the wrapper replaces itself;
        # the listener must retain the immutable packaged interpreter identity.
        controller.wait(timeout=10)
        assert listener.is_running()
        assert len(listeners(port)) == 1
        stopped_pid = safe_stop(port, identity_signal)
        assert stopped_pid == listener.pid
    finally:
        if controller.poll() is None:
            controller.kill()
        for process in listeners(port):
            process.kill()


@pytest.mark.skipif(os.name != "nt", reason="Windows process identity required")
def test_unrelated_listener_fails_closed_and_is_not_killed(tmp_path: Path) -> None:
    port = free_port()
    unrelated = subprocess.Popen(
        [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", f'python -m http.server {port} --bind 127.0.0.1'],
        cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    wait_listener_count(port, 1)
    try:
        with pytest.raises(RuntimeError, match="does not match"):
            safe_stop(port, str(RUNTIME_PYTHON))
        assert unrelated.poll() is None
        assert len(listeners(port)) == 1
        with pytest.raises(AssertionError, match="did not become 0"):
            wait_listener_count(port, 0, timeout=0.3)
        assert unrelated.poll() is None
    finally:
        unrelated.terminate()
        try:
            unrelated.wait(timeout=10)
        except subprocess.TimeoutExpired:
            unrelated.kill(); unrelated.wait(timeout=10)
        for process in listeners(port):
            process.kill()


def test_ambiguous_listener_set_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(__name__ + ".listeners", lambda _port: [object(), object()])
    with pytest.raises(RuntimeError, match="ambiguous"):
        governed_listener(free_port(), str(RUNTIME_PYTHON))


def test_powershell_safe_stop_has_no_broad_python_termination() -> None:
    source = (ROOT / "scripts/deploy/deploy_s7_rc_f11f2ab.ps1").read_text(encoding="utf-8")
    assert "Get-CimInstance Win32_Process" in source
    assert "Get-NetTCPConnection -LocalAddress 127.0.0.1" in source
    assert "backend.wsgi:app" in source and "-m\\s+waitress" in source
    assert "Stop-Process -Id ([int]$listener.ProcessId)" in source
    assert "Stop-Process -Name" not in source
    assert "taskkill /IM" not in source
