"""Read-only release blocker verification for credential and Alembic policy."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HEAD = "security_credential_remediation"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True)


def main() -> int:
    credential = run([sys.executable, "scripts/verify_credential_policy.py"])
    if credential.returncode:
        print(credential.stdout, end="")
        print(credential.stderr, end="", file=sys.stderr)
        return credential.returncode

    heads = run(
        [sys.executable, "-m", "alembic", "-c", "backend/migrations/alembic.ini", "heads"]
    )
    if heads.returncode:
        print(heads.stdout, end="")
        print(heads.stderr, end="", file=sys.stderr)
        return heads.returncode
    head_lines = [line.strip() for line in heads.stdout.splitlines() if "(head)" in line]
    if head_lines != [f"{EXPECTED_HEAD} (head)"]:
        print(f"release-security=FAIL heads={head_lines!r}")
        return 1

    print(credential.stdout, end="")
    print(f"release-security=PASS alembic_head={EXPECTED_HEAD} executable_defaults=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
