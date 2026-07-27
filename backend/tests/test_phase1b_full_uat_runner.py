"""Unit tests for the safe boundary of the operator-run Phase 1B harness."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


RUNNER = Path(__file__).parents[2] / "scripts/uat/phase1b_full_uat_runner.py"
SPEC = importlib.util.spec_from_file_location("phase1b_full_uat_runner", RUNNER)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def args(**overrides):
    values = {
        "browser_runner": None, "postgres_port": 55432,
        "backend_port": 57066, "vite_port": 5174,
        "targeted_smoke": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_plan_uses_argument_vectors_limited_environments_and_no_forbidden_ports(tmp_path):
    plan = runner.build_plan(Path(__file__).parents[2], args(), tmp_path, "unit", "top-secret")

    assert {item.name for item in plan} >= {
        "postgres-init", "postgres-start", "postgres-ready", "postgres-stop",
        "database-create", "migration", "seed", "backend", "vite", "browser",
        "database-drop",
    }
    assert all(isinstance(item.argv, tuple) for item in plan)
    assert all("cmd" not in Path(item.argv[0]).name.lower() for item in plan)
    assert all("npm" not in Path(item.argv[0]).name.lower() for item in plan)
    assert all(str(runner.PRODUCTION_PORT) not in item.argv for item in plan)
    assert all(str(runner.PUBLIC_POSTGRES_PORT) not in item.argv for item in plan)
    assert all("USERPROFILE" not in item.env for item in plan)
    commands = {item.name: item for item in plan}
    assert Path(commands["postgres-start"].argv[0]).name == "pg_ctl.exe"
    assert commands["postgres-start"].argv[1] == "start"
    assert commands["postgres-start"].argv[-1] == "-w"
    assert "-l" in commands["postgres-start"].argv
    assert commands["postgres-ready"].argv[0].endswith("pg_isready.exe")
    assert commands["postgres-stop"].argv[1:3] == ("stop", "-D")


def test_display_command_redacts_secrets_and_database_credentials():
    credential_url = "postgresql://" + "user" + ":" + "hunter2" + "@127.0.0.1:55432/db"
    command = runner.Command(
        "sample", ("tool", credential_url),
        {"FORWARDER_UAT_PASSWORD": "hunter2", "DATABASE_URL":
         credential_url},
    )
    rendered = json.dumps(runner.display_command(command))

    assert "hunter2" not in rendered
    assert "[REDACTED]" in rendered


def test_display_command_redacts_browser_password():
    command = runner.Command(
        "browser", ("node", "runner.mjs"),
        {"PHASE1B_UAT_PASSWORD": "ephemeral-browser-secret"},
    )

    rendered = json.dumps(runner.display_command(command))

    assert "ephemeral-browser-secret" not in rendered
    assert "[REDACTED]" in rendered


def test_targeted_mode_is_passed_only_to_browser_child(tmp_path):
    plan = runner.build_plan(Path(__file__).parents[2], args(targeted_smoke=True), tmp_path, "unit", "secret")
    browser = next(item for item in plan if item.name == "browser")
    assert browser.env["PHASE1B_UAT_MODE"] == "targeted-smoke"
    assert all("PHASE1B_UAT_MODE" not in item.env for item in plan if item.name != "browser")


@pytest.mark.parametrize("argv", [
    ["--run"],
    ["--validate-only", "--confirm"],
    ["--dry-run", "--confirm"],
    ["--targeted-smoke"],
])
def test_real_run_gate_refuses_incomplete_or_misplaced_confirmation(monkeypatch, argv):
    monkeypatch.setattr(runner, "validate", lambda *_: [])
    assert runner.main(argv) == 2


def test_validate_only_and_dry_run_never_execute(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "validate", lambda *_: [])
    monkeypatch.setattr(runner, "execute",
                        lambda *_: pytest.fail("safe mode must not execute"))

    assert runner.main(["--validate-only", "--output-dir", str(tmp_path)]) == 0
    assert runner.main(["--dry-run", "--output-dir", str(tmp_path)]) == 0
    payloads = [json.loads(path.read_text(encoding="utf-8"))
                for path in tmp_path.glob("*.json")]
    assert {payload["mode"] for payload in payloads} == {"validate-only", "dry-run"}
    assert all(payload["persistent_applied"] is False for payload in payloads)


def test_start_process_always_passes_shell_false(monkeypatch, tmp_path):
    captured = {}

    def fake_popen(argv, **kwargs):
        captured.update(argv=argv, **kwargs)
        return object()

    monkeypatch.setattr(runner.subprocess, "Popen", fake_popen)
    with (tmp_path / "out").open("wb") as out, (tmp_path / "err").open("wb") as err:
        runner.start_process(runner.Command("x", ("python", "-V"), {}), tmp_path, out, err)

    assert captured["argv"] == ["python", "-V"]
    assert captured["shell"] is False
    assert captured["stdin"] is runner.subprocess.DEVNULL


def test_cleanup_terminates_then_kills_on_timeout(monkeypatch):
    events = []

    class FakeProcess:
        def poll(self):
            return None

        def terminate(self):
            events.append("terminate")

        def wait(self, timeout):
            events.append(("wait", timeout))
            if events.count(("wait", timeout)) == 1:
                raise runner.subprocess.TimeoutExpired("x", timeout)

        def kill(self):
            events.append("kill")

    runner.terminate_process(FakeProcess(), timeout=3)
    assert events == ["terminate", ("wait", 3), "kill", ("wait", 3)]


def test_sanitize_removes_common_secret_shapes():
    text = "DATABASE_URL=postgresql://" + "u" + ":" + "p" + "@localhost/db token=abc password=q"
    sanitized = runner.sanitize(text)
    assert "://u:p@" not in sanitized
    assert "abc" not in sanitized
    assert "password=q" not in sanitized
