"""Deterministic, operator-run Phase 1B full UAT orchestrator.

This module is deliberately stdlib-only.  The safe modes never start PostgreSQL,
the applications, or a browser.  Real execution requires both --run and
--confirm and is intended for a normal local Windows terminal, not an executor.
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import datetime as dt
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import IO, Iterable, Mapping, Sequence


EXPECTED_BRANCH = "feature/forwarder-multileg-route-orchestration-phase1b"
EXPECTED_HEAD = "268d329060acd7f0516ddf90a2a0c54846d8e396"
DATABASE_PREFIX = "forwarder_phase1b_uat_"
PYTHON = Path(r"C:\Users\pc\AppData\Local\Programs\Python\Python313\python.exe")
PG_BIN = Path(r"C:\Program Files\PostgreSQL\18\bin")
NODE = Path(r"C:\Program Files\nodejs\node.exe")
PRODUCTION_REPOSITORY = Path(r"C:\1-webapp\1-forwarder")
PRODUCTION_PORT = 5001
PUBLIC_POSTGRES_PORT = 5432
DEFAULT_BACKEND_PORT = 57065
SECRET_NAMES = {
    "DATABASE_URL", "FORWARDER_UAT_PASSWORD", "PHASE1B_UAT_PASSWORD",
    "SECRET_KEY", "JWT_SECRET_KEY",
}
SAFE_PARENT_ENV = ("SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP")
REDACTIONS = (
    (re.compile(r"(?i)(postgres(?:ql)?://[^:\s/]+:)[^@\s/]+(@)"), r"\1[REDACTED]\2"),
    (re.compile(r"(?i)(password|secret|token|authorization)(\s*[=:]\s*)\S+"), r"\1\2[REDACTED]"),
)


class HarnessError(RuntimeError):
    """Expected, sanitized harness failure."""


@dataclasses.dataclass(frozen=True)
class Command:
    name: str
    argv: tuple[str, ...]
    env: Mapping[str, str]
    long_running: bool = False


@dataclasses.dataclass
class StepResult:
    name: str
    status: str
    detail: str
    duration_seconds: float = 0.0


def sanitize(value: object, secret_values: Iterable[str] = ()) -> str:
    text = str(value)
    for secret in sorted((s for s in secret_values if s), key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def safe_env(extra: Mapping[str, str]) -> dict[str, str]:
    env = {name: os.environ[name] for name in SAFE_PARENT_ENV if os.environ.get(name)}
    env.update({"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"})
    env.update({str(k): str(v) for k, v in extra.items()})
    return env


def display_command(command: Command) -> dict[str, object]:
    shown_env = {
        key: ("[REDACTED]" if key.upper() in SECRET_NAMES else sanitize(value))
        for key, value in sorted(command.env.items())
    }
    shown_argv = [sanitize(part, command.env.values()) for part in command.argv]
    return {"name": command.name, "argv": shown_argv, "env": shown_env,
            "long_running": command.long_running, "shell": False}


def find_free_port(excluded: set[int]) -> int:
    for _ in range(100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        if port not in excluded:
            return port
    raise HarnessError("Could not allocate a safe loopback port.")


def probe(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, urllib.error.URLError):
        return False


def wait_for_probe(url: str, process: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise HarnessError(f"Process exited before readiness probe: {url}")
        if probe(url):
            return
        time.sleep(0.25)
    raise HarnessError(f"Readiness timeout: {url}")


def wait_for_port(port: int, process: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise HarnessError("PostgreSQL exited before accepting connections.")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise HarnessError("PostgreSQL readiness timeout.")


def terminate_process(process: subprocess.Popen[bytes], timeout: float = 10.0) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout)


def run_capture(command: Command, cwd: Path, timeout: float,
                stdout: IO[bytes] | int = subprocess.PIPE,
                stderr: IO[bytes] | int = subprocess.PIPE) -> subprocess.CompletedProcess[bytes]:
    process = subprocess.Popen(
        list(command.argv), cwd=str(cwd), env=dict(command.env), shell=False,
        stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
    )
    try:
        captured_stdout, captured_stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_process(process)
        raise
    return subprocess.CompletedProcess(
        list(command.argv), process.returncode, captured_stdout, captured_stderr
    )


def start_process(command: Command, cwd: Path, stdout: IO[bytes],
                  stderr: IO[bytes]) -> subprocess.Popen[bytes]:
    kwargs: dict[str, object] = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(
        list(command.argv), cwd=str(cwd), env=dict(command.env), shell=False,
        stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, **kwargs,
    )


def git_value(root: Path, *args: str) -> str:
    process = subprocess.Popen(
        ["git", *args], cwd=str(root), shell=False, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        stdout, _ = process.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        terminate_process(process)
        raise HarnessError("Git preflight timed out.")
    if process.returncode:
        raise HarnessError("Git preflight failed.")
    return stdout.strip()


def validate(root: Path, args: argparse.Namespace) -> list[StepResult]:
    checks: list[StepResult] = []

    def check(name: str, condition: bool, detail: str) -> None:
        checks.append(StepResult(name, "PASS" if condition else "FAIL", detail))

    check("repository", (root / ".git").exists(), str(root))
    if (root / ".git").exists():
        branch = git_value(root, "branch", "--show-current")
        head = git_value(root, "rev-parse", "HEAD")
        check("branch", branch == EXPECTED_BRANCH, branch)
        check("head", head == EXPECTED_HEAD, head)
    check("not-production-repository",
          root.resolve() != PRODUCTION_REPOSITORY.resolve(), str(root))
    check("backend-port-file",
          (root / ".backend-port").is_file()
          and (root / ".backend-port").read_text(encoding="utf-8").strip() == str(DEFAULT_BACKEND_PORT),
          "expected unchanged value 57065")
    env_files = [path for path in root.rglob(".env") if path.is_file()]
    check("repository-env-files", not env_files, f"count={len(env_files)}")
    check("python", PYTHON.is_file(), str(PYTHON))
    check("postgresql-18", all((PG_BIN / name).is_file() for name in
                              ("initdb.exe", "pg_ctl.exe", "pg_isready.exe",
                               "createdb.exe", "dropdb.exe")),
          str(PG_BIN))
    check("node", NODE.is_file(), str(NODE))
    check("vite-cli", (root / "node_modules/vite/bin/vite.js").is_file(),
          "node_modules/vite/bin/vite.js")
    browser = Path(args.browser_runner).resolve() if args.browser_runner else None
    check("browser-runner", browser is not None and browser.is_file(),
          str(browser) if browser else "not supplied (required only for --run)")
    check("forbidden-ports", args.backend_port not in {PRODUCTION_PORT, PUBLIC_POSTGRES_PORT}
          and args.vite_port not in {PRODUCTION_PORT, PUBLIC_POSTGRES_PORT}
          and args.postgres_port not in {PRODUCTION_PORT, PUBLIC_POSTGRES_PORT},
          "5001 and 5432 are forbidden")
    return checks


def build_plan(root: Path, args: argparse.Namespace, runtime: Path,
               token: str, password: str) -> list[Command]:
    pg_port = args.postgres_port
    backend_port = args.backend_port
    vite_port = args.vite_port
    database = f"{DATABASE_PREFIX}{token}"
    data = runtime / "pgdata"
    pg_env = safe_env({"PATH": str(PG_BIN)})
    database_url = f"postgresql://postgres@127.0.0.1:{pg_port}/{database}"
    app_env = safe_env({
        "PATH": os.pathsep.join((str(PYTHON.parent), str(PG_BIN), str(NODE.parent))),
        "APP_ENV": "uat",
        "DATABASE_URL": database_url,
        "FORWARDER_UAT_PASSWORD": password,
        "SECRET_KEY": secrets.token_urlsafe(32),
        "JWT_SECRET_KEY": secrets.token_urlsafe(32),
        "AUTO_MIGRATE_ON_STARTUP": "false",
    })
    frontend_env = safe_env({
        "PATH": str(NODE.parent),
        "NODE_ENV": "development",
        "VITE_BACKEND_URL": f"http://127.0.0.1:{backend_port}",
    })
    browser_env = safe_env({
        "PATH": str(NODE.parent),
        "PHASE1B_UAT_BASE_URL": f"http://127.0.0.1:{vite_port}",
        "PHASE1B_UAT_API_URL": f"http://127.0.0.1:{backend_port}",
        "PHASE1B_UAT_PASSWORD": password,
        "PHASE1B_UAT_EVIDENCE_DIR": str(runtime / "evidence"),
        "PHASE1B_UAT_MODE": "targeted-smoke" if getattr(args, "targeted_smoke", False) else "full",
    })
    browser_argv = (str(NODE), str(Path(args.browser_runner).resolve())) if args.browser_runner else (
        str(NODE), "<required-browser-runner>")
    return [
        Command("postgres-init", (str(PG_BIN / "initdb.exe"), "-D", str(data),
                                  "-U", "postgres", "--auth-host=trust",
                                  "--auth-local=trust", "--encoding=UTF8"), pg_env),
        Command("postgres-start", (str(PG_BIN / "pg_ctl.exe"), "start", "-D", str(data),
                                   "-l", str(runtime / "logs" / "postgres.server.log"),
                                   "-o", f"-h 127.0.0.1 -p {pg_port}", "-w"), pg_env),
        Command("postgres-ready", (str(PG_BIN / "pg_isready.exe"), "-h", "127.0.0.1",
                                   "-p", str(pg_port), "-d", "postgres",
                                   "-U", "postgres"), pg_env),
        Command("postgres-stop", (str(PG_BIN / "pg_ctl.exe"), "stop", "-D", str(data),
                                  "-m", "fast", "-w"), pg_env),
        Command("database-create", (str(PG_BIN / "createdb.exe"), "-h", "127.0.0.1",
                                    "-p", str(pg_port), "-U", "postgres", database), pg_env),
        Command("migration", (str(PYTHON), "-m", "backend.migration_cli",
                              "upgrade", "--confirm"), app_env),
        Command("seed", (str(PYTHON), "-m", "backend.operational_cli",
                         "seed-phase1b-uat", "--confirm"), app_env),
        Command("backend", (str(PYTHON), "-m", "waitress",
                            f"--listen=127.0.0.1:{backend_port}", "backend.wsgi:app"),
                app_env, True),
        Command("vite", (str(NODE), str(root / "node_modules/vite/bin/vite.js"),
                         "--host", "127.0.0.1", "--port", str(vite_port),
                         "--strictPort"), frontend_env, True),
        Command("browser", browser_argv, browser_env),
        Command("database-drop", (str(PG_BIN / "dropdb.exe"), "-h", "127.0.0.1",
                                  "-p", str(pg_port), "-U", "postgres",
                                  "--if-exists", database), pg_env),
    ]


def write_reports(output_dir: Path, run_id: str, mode: str,
                  results: Sequence[StepResult], plan: Sequence[Command]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1, "run_id": run_id, "mode": mode,
        "classification": "AUTOMATED_EXECUTOR_CAPABILITY_LIMITATION",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "persistent_applied": False,
        "results": [dataclasses.asdict(item) for item in results],
        "commands": [display_command(command) for command in plan],
    }
    json_path = output_dir / f"{run_id}.json"
    md_path = output_dir / f"{run_id}.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        f"# Phase 1B full UAT harness — {run_id}", "",
        f"- Mode: `{mode}`", "- Persistent applied: `NO`",
        "- Secrets: `SANITIZED`", "", "| Check | Result | Detail |", "|---|---|---|",
    ]
    lines.extend(f"| {r.name} | {r.status} | {sanitize(r.detail).replace('|', '/')} |" for r in results)
    lines += ["", "## Command plan", "", "Every command uses an argument vector and `shell=False`.", "", "```json",
              json.dumps(payload["commands"], indent=2, sort_keys=True), "```", ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def execute(root: Path, args: argparse.Namespace, runtime: Path,
            plan: Sequence[Command]) -> list[StepResult]:
    commands = {command.name: command for command in plan}
    logs = runtime / "logs"
    logs.mkdir(parents=True)
    (runtime / "evidence").mkdir()
    results: list[StepResult] = []
    processes: list[tuple[str, subprocess.Popen[bytes], IO[bytes], IO[bytes]]] = []
    postgres_started = False
    database_created = False

    def failure_detail(name: str, returncode: int) -> str:
        candidates = [
            logs / f"{name}.stderr.log",
            logs / f"{name}.stdout.log",
        ]
        if name == "browser":
            candidates.append(runtime / "evidence" / "phase1b_browser_result.json")
        if name.startswith("postgres"):
            candidates.append(logs / "postgres.server.log")
        lines: list[str] = []
        for path in candidates:
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                lines.extend(line.strip() for line in text.splitlines() if line.strip())
        tail = " / ".join(lines[-8:]).replace(str(runtime), "[RUNTIME]")
        suffix = f" Final log: {sanitize(tail)}" if tail else ""
        return f"{name} failed with exit code {returncode}.{suffix}"

    def one_shot(name: str, timeout: float = 120.0) -> None:
        started = time.monotonic()
        with (logs / f"{name}.stdout.log").open("wb") as out, \
                (logs / f"{name}.stderr.log").open("wb") as err:
            completed = run_capture(commands[name], root, timeout, out, err)
        if completed.returncode:
            raise HarnessError(failure_detail(name, completed.returncode))
        results.append(StepResult(name, "PASS", "completed",
                                  round(time.monotonic() - started, 3)))

    try:
        one_shot("postgres-init")
        one_shot("postgres-start", args.readiness_timeout)
        postgres_started = True
        one_shot("postgres-ready", args.readiness_timeout)
        results.append(StepResult("postgres", "PASS", "loopback ready"))
        one_shot("database-create")
        database_created = True
        one_shot("migration", args.step_timeout)
        one_shot("seed", args.step_timeout)
        for name, url in (
            ("backend", f"http://127.0.0.1:{args.backend_port}/api/health"),
            ("vite", f"http://127.0.0.1:{args.vite_port}/"),
        ):
            out = (logs / f"{name}.stdout.log").open("wb")
            err = (logs / f"{name}.stderr.log").open("wb")
            process = start_process(commands[name], root, out, err)
            processes.append((name, process, out, err))
            wait_for_probe(url, process, args.readiness_timeout)
            results.append(StepResult(name, "PASS", "ready"))
        one_shot("browser", args.browser_timeout)
        return results
    except KeyboardInterrupt as exc:
        results.append(StepResult("run", "INTERRUPTED", "KeyboardInterrupt"))
        raise HarnessError("Run interrupted by operator.") from exc
    finally:
        for name, process, out, err in reversed(processes):
            with contextlib.suppress(Exception):
                terminate_process(process)
                results.append(StepResult(f"{name}-cleanup", "PASS", "stopped"))
            out.close()
            err.close()
        if database_created and postgres_started:
            with contextlib.suppress(Exception):
                one_shot("database-drop", 60)
        if postgres_started or (runtime / "pgdata" / "postmaster.pid").is_file():
            with contextlib.suppress(Exception):
                one_shot("postgres-stop", 60)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--targeted-smoke", action="store_true")
    result.add_argument("--confirm", action="store_true",
                        help="mandatory second gate for real execution")
    result.add_argument("--browser-runner",
                        help="absolute or repository-relative Node browser runner")
    result.add_argument("--output-dir", type=Path,
                        help="sanitized report directory (default: OS temp)")
    result.add_argument("--postgres-port", type=int, default=55432)
    result.add_argument("--backend-port", type=int, default=57066)
    result.add_argument("--vite-port", type=int, default=5174)
    result.add_argument("--readiness-timeout", type=float, default=60)
    result.add_argument("--step-timeout", type=float, default=300)
    result.add_argument("--browser-timeout", type=float, default=900)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    real_run = args.run or args.targeted_smoke
    if real_run and not args.confirm:
        print("REFUSED: real execution requires --run --confirm.", file=sys.stderr)
        return 2
    if args.confirm and not real_run:
        print("REFUSED: --confirm is valid only with --run.", file=sys.stderr)
        return 2
    token = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S%f")
    run_id = f"P1B-UAT-{token}"
    password = secrets.token_urlsafe(24)
    runtime = Path(tempfile.gettempdir()) / run_id
    plan = build_plan(root, args, runtime, token.lower(), password)
    results = validate(root, args)
    blocking = [r for r in results if r.status == "FAIL" and
                (r.name != "browser-runner" or real_run)]
    mode = ("validate-only" if args.validate_only else "dry-run" if args.dry_run
            else "targeted-smoke" if args.targeted_smoke else "run")
    output = (args.output_dir.resolve() if args.output_dir
              else Path(tempfile.gettempdir()) / "forwarder-phase1b-uat-reports")
    exit_code = 0
    try:
        if blocking:
            exit_code = 1
        elif real_run:
            runtime.mkdir(parents=True, exist_ok=False)
            results.extend(execute(root, args, runtime, plan))
        paths = write_reports(output, run_id, mode, results, plan)
        print(json.dumps({
            "mode": mode, "result": "PASS" if exit_code == 0 else "FAIL",
            "processes_started": bool(args.run and not blocking),
            "reports": [str(path) for path in paths],
        }, sort_keys=True))
    except HarnessError as exc:
        results.append(StepResult("harness", "FAIL", sanitize(exc)))
        artifact_dir = output / f"{run_id}-artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        for source in (runtime / "logs" / "browser.stdout.log",
                       runtime / "logs" / "browser.stderr.log",
                       runtime / "evidence" / "phase1b_browser_result.json",
                       runtime / "evidence" / "phase1b-last-failure.png"):
            if source.is_file():
                shutil.copy2(source, artifact_dir / source.name)
        results.append(StepResult("browser-artifacts", "PASS", str(artifact_dir)))
        write_reports(output, run_id, mode, results, plan)
        print(f"HARNESS_FAILED: {sanitize(exc)}", file=sys.stderr)
        exit_code = 1
    finally:
        if real_run and runtime.exists():
            shutil.rmtree(runtime, ignore_errors=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
