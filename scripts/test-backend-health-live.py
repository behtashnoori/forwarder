#!/usr/bin/env python3
"""
CI/regression: start backend on a fixed port, hit /api/health, ensure process stays alive, then shut down.
Uses port 18999 to avoid conflicting with dev (8000). Run from project root: python scripts/test-backend-health-live.py
"""
import os
import subprocess
import sys
import time
import urllib.request

PORT = 18999
WAIT_START = 4
WAIT_ALIVE = 2
HEALTH_URL = f"http://127.0.0.1:{PORT}/api/health"


def main():
    env = {**os.environ, "PORT": str(PORT)}
    proc = subprocess.Popen(
        [sys.executable, "-m", "backend.run"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        time.sleep(WAIT_START)
        if proc.poll() is not None:
            out, _ = proc.communicate(timeout=1)
            print("Backend exited early:", out or "(no output)")
            sys.exit(1)
        req = urllib.request.Request(HEALTH_URL)
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read().decode()
            if "ok" not in data.lower() or r.status != 200:
                print("Health check failed:", r.status, data)
                sys.exit(1)
        time.sleep(WAIT_ALIVE)
        if proc.poll() is not None:
            print("Backend exited during alive wait (expected to stay up)")
            sys.exit(1)
    except urllib.error.URLError as e:
        print("Health request failed:", e)
        proc.terminate()
        proc.wait(timeout=5)
        sys.exit(1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print("test-backend-health-live: OK (backend started, health ok, process stayed alive)")


if __name__ == "__main__":
    main()
