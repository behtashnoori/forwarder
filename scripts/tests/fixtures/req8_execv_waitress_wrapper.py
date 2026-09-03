"""Development-only reproduction of the Production wrapper serve semantics."""
from __future__ import annotations

import os
from pathlib import Path
import sys

from dotenv import dotenv_values


def main() -> None:
    env_path = Path(sys.argv[1])
    repo_path = Path(sys.argv[2])
    port = int(sys.argv[3])
    values = {
        str(key): str(value)
        for key, value in dotenv_values(env_path).items()
        if value is not None
    }
    if not values:
        raise RuntimeError("empty test environment")
    os.environ.update(values)
    os.chdir(repo_path)
    command = [
        sys.executable,
        "-m",
        "waitress",
        f"--listen=127.0.0.1:{port}",
        "scripts.tests.fixtures.req8_candidate_wsgi:app",
    ]
    os.execv(sys.executable, command)


if __name__ == "__main__":
    main()
