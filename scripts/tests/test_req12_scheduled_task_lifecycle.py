"""Real Development-only Windows Scheduled Task/backend/HTTP/CORS lifecycle."""
from __future__ import annotations

import http.client
import os
from pathlib import Path
import socket
import subprocess
import time
import uuid

import psutil
import pytest

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT.parent / "qualification/req12-layout-proof/release-a/runtime/python.exe"
LAUNCHER = ROOT / "scripts/tests/fixtures/req12_scheduled_task_launcher.py"
CANONICAL = "https://samand.forwarderet.ir"


def request(port: int, method: str = "GET", origin: str | None = None):
    headers = {"Origin": origin} if origin else {}
    if method == "OPTIONS": headers["Access-Control-Request-Method"] = "GET"
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(method, "/api/health", headers=headers)
        response = connection.getresponse(); response.read()
        return response.status, {k.lower(): v for k, v in response.getheaders()}
    finally: connection.close()


@pytest.mark.skipif(os.name != "nt" or not PYTHON.is_file(), reason="Windows packaged runtime required")
def test_real_scheduled_task_backend_listener_http_cors_lifecycle(tmp_path: Path) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]
    env = tmp_path / "development.env"
    env.write_text(
        "APP_ENV=production\nDATABASE_URL=sqlite:///:memory:\n"
        "SECRET_KEY=req12-development-lifecycle-secret\n"
        "JWT_SECRET_KEY=req12-development-lifecycle-jwt-secret\n"
        f"DOCUMENT_STORAGE_ROOT={tmp_path / 'documents'}\n"
        "CORS_ALLOW_ALL_ORIGINS=false\n"
        f"CORS_ORIGINS={CANONICAL}\nCORS_ORIGIN={CANONICAL}\n", encoding="utf-8",
    )
    task = "Forwarder REQ12 Development " + uuid.uuid4().hex
    runner = tmp_path / "run.py"
    runner.write_text(
        f"import runpy,sys\nsys.argv=['x',{str(env)!r},{str(ROOT)!r},{port!r}]\nrunpy.run_path({str(LAUNCHER)!r},run_name='__main__')\n",
        encoding="utf-8",
    )
    action = f'"{PYTHON}" "{runner}"'
    create = subprocess.run(["schtasks.exe", "/Create", "/TN", task, "/SC", "ONCE", "/ST", "23:59", "/TR", action, "/F"], capture_output=True, text=True)
    assert create.returncode == 0, create.stdout + create.stderr
    pid = None
    try:
        run = subprocess.run(["schtasks.exe", "/Run", "/TN", task], capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            listeners = [c for c in psutil.net_connections("tcp") if c.status == psutil.CONN_LISTEN and c.laddr.port == port]
            if len(listeners) == 1:
                pid = listeners[0].pid; break
            time.sleep(.2)
        assert pid is not None
        process = psutil.Process(pid)
        assert process.exe().lower() == str(PYTHON).lower()
        assert str(PYTHON).lower() in " ".join(process.cmdline()).lower()
        assert request(port)[0] == 200
        assert request(port, origin=CANONICAL)[1].get("access-control-allow-origin") == CANONICAL
        assert request(port, "OPTIONS", CANONICAL)[1].get("access-control-allow-origin") == CANONICAL
        assert "access-control-allow-origin" not in request(port, origin="https://server.logisticmarket.ir")[1]
    finally:
        subprocess.run(["schtasks.exe", "/End", "/TN", task], capture_output=True)
        if pid and psutil.pid_exists(pid):
            psutil.Process(pid).terminate()
            try: psutil.Process(pid).wait(10)
            except psutil.TimeoutExpired: psutil.Process(pid).kill()
        subprocess.run(["schtasks.exe", "/Delete", "/TN", task, "/F"], capture_output=True)
