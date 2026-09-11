"""Run pytest once and persist a conclusive, machine-readable result."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SUMMARY_RE = re.compile(
    r"=+\s*(?P<summary>[^\r\n]+?)\s+in (?P<duration>[\d.]+)s(?: \([^)]+\))?\s*=+"
)
COUNT_RE = re.compile(
    r"(\d+) (passed|failed|skipped|xfailed|xpassed|warning|warnings|error|errors)"
)


def run(command: list[str], output_dir: Path, timeout: float | None) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    start_clock = time.monotonic()
    record: dict[str, object] = {
        "command": command,
        "started_at": started.isoformat(),
        "timeout_seconds": timeout,
    }
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, errors="replace", timeout=timeout
        )
        stdout, stderr = completed.stdout, completed.stderr
        exit_code = completed.returncode
        if exit_code < 0:
            status = "PYTEST_ABNORMAL_TERMINATION"
        elif exit_code == 0:
            status = "PASS"
        else:
            status = "PYTEST_TEST_FAILURE"
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        exit_code = None
        status = "TIMEOUT"
    except Exception as exc:  # outer harness faults must remain distinguishable
        stdout = ""
        stderr = f"{type(exc).__name__}: {exc}"
        exit_code = None
        status = "OUTER_HARNESS_FAILURE"

    combined = f"{stdout}\n{stderr}"
    matches = list(SUMMARY_RE.finditer(combined))
    summary = matches[-1].group("summary") if matches else None
    counts = {name: 0 for name in ("passed", "failed", "skipped", "xfailed", "xpassed", "warnings", "errors")}
    if summary:
        for value, name in COUNT_RE.findall(summary):
            normalized = {"error": "errors", "warning": "warnings"}.get(name, name)
            counts[normalized] = int(value)
    record.update(
        {
            "status": status,
            "pytest_exit_code": exit_code,
            "summary": summary,
            "counts": counts,
            "pytest_duration_seconds": float(matches[-1].group("duration")) if matches else None,
            "outer_duration_seconds": round(time.monotonic() - start_clock, 3),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "stdout_file": "stdout.log",
            "stderr_file": "stderr.log",
        }
    )
    (output_dir / "stdout.log").write_text(stdout, encoding="utf-8")
    (output_dir / "stderr.log").write_text(stderr, encoding="utf-8")
    (output_dir / "result.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")
    result = run(command, args.output_dir, args.timeout)
    code = result["pytest_exit_code"]
    return int(code) if isinstance(code, int) and code >= 0 else 124 if result["status"] == "TIMEOUT" else 125


if __name__ == "__main__":
    sys.exit(main())
