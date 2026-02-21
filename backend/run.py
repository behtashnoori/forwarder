"""
Canonical dev entrypoint. Loads config, checks port, starts server.
Migrations + verify + seed run inside create_app() so they always run on any backend start.
Run: python -m backend.run [--reload]
"""
from __future__ import annotations

import argparse
import os
import socket
import sys

# Ensure project root is on path when run as python -m backend.run or from backend/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load config first (loads .env and sets HOST, PORT, DEBUG, USE_RELOAD)
from backend import config  # noqa: E402
from backend import create_app  # noqa: E402
from backend.startup import run_migrations, verify_critical_tables  # noqa: E402
from backend.startup_seed import run_startup_seed  # noqa: E402


def _is_port_in_use(host: str, port: int) -> bool:
    """Cross-platform: True if host:port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def _print_port_hints(port: int) -> None:
    print("  Linux/macOS: lsof -ti:%d | xargs kill" % port)
    print("  Windows: Get-NetTCPConnection -LocalPort %d | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }" % port)
    print("  Or: netstat -ano | findstr :%d" % port)


def _get_server_ip_for_display() -> str:
    """Best-effort non-loopback IP for startup log."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "<server-ip>"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run backend server (migrations run automatically in create_app)")
    parser.add_argument("--reload", action="store_true", help="Enable Flask reloader (default: off for stability)")
    args = parser.parse_args()
    use_reloader = args.reload

    host = config.HOST
    port = config.PORT
    debug = config.DEBUG

    print("[startup] PORT=%s, HOST=%s, DEBUG=%s, use_reloader=%s" % (port, host, debug, use_reloader))

    if not os.getenv("DATABASE_URL"):
        print("[startup] DATABASE_URL is required. Set it in .env or environment.")
        sys.exit(1)
    print("[startup] Environment OK.")

    # If configured port is in use, try next ports so the backend does not exit
    max_tries = 20
    try_port = port
    while _is_port_in_use(host, try_port) and (try_port - port) < max_tries:
        try_port += 1
    if _is_port_in_use(host, try_port):
        print("Ports %s..%s are in use. Please free a port." % (port, port + max_tries - 1))
        _print_port_hints(port)
        sys.exit(1)
    if try_port != port:
        print("Port %s in use, using port %s instead." % (port, try_port))
        port = try_port

    # So Vite proxy always targets the port we actually use (e.g. 5002 when 5001 is busy)
    _backend_port_file = os.path.join(_PROJECT_ROOT, ".backend-port")
    try:
        with open(_backend_port_file, "w") as f:
            f.write(str(port))
    except OSError:
        pass

    # Skip startup inside create_app so we run it once here (avoids running twice when reloader spawns child)
    app = create_app(skip_startup=True)
    run_migrations(app)
    verify_critical_tables(app)
    run_startup_seed(app)

    server_ip = _get_server_ip_for_display()
    print("Backend started successfully.")
    print("Listening on:")
    print("  - http://localhost:%s" % port)
    print("  - http://%s:%s" % (server_ip, port))
    print("Health: GET http://localhost:%s/api/health" % port)
    app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)


if __name__ == "__main__":
    main()
