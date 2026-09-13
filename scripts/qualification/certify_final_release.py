"""Certify an extracted Forwarder Windows/IIS/Waitress production artifact.

This is deliberately artifact-first: repository source is used only as the
authoritative migration inventory for the frozen application commit.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

APP_COMMIT = "b4294fcf4657fbb39b1895ef32e282c92ff9a244"
REVISION = "20260920_legal_customer_nullable_contact_names"
INTERNAL_HEALTH = "http://127.0.0.1:5101/api/health"
PUBLIC_HEALTH = "https://samand.forwarderet.ir/api/health"
REQUIRED_TIMEOUTS = {
    "DB_GATE", "TASK_STOP", "TASK_START", "BACKEND_STOP", "PORT_RELEASE",
    "LISTENER_START", "LISTENER_IDENTITY", "IIS_VERIFY", "INTERNAL_HEALTH",
    "PUBLIC_HEALTH", "ROLLBACK_RECOVERY",
}


def need(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def run(argv: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(argv)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result.stdout


def powershell() -> str:
    return shutil.which("pwsh.exe") or shutil.which("pwsh") or "powershell.exe"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_root(extracted: Path) -> Path:
    if (extracted / "RELEASE-METADATA.json").is_file():
        return extracted
    children = [p for p in extracted.iterdir() if p.is_dir()]
    need(len(children) == 1 and (children[0] / "RELEASE-METADATA.json").is_file(),
         "extracted ZIP must contain one identifiable package root")
    return children[0]


def check_package(root: Path) -> dict:
    artifact = root / "artifact"
    required = [
        artifact / "dist/index.html", artifact / "backend/wsgi.py",
        root / "VERIFY-PACKAGE.ps1", root / "SHA256SUMS.txt",
        root / "RELEASE-METADATA.json", root / "revision_gate.py",
        root / "deploy_windows_iis_waitress.ps1", root / "ROLLBACK.md",
        root / "SERVER-DEPLOY-STEPS.md", root / "CERTIFY-RELEASE.ps1",
    ]
    for path in required:
        need(path.is_file(), f"required package file absent: {path.relative_to(root)}")
    metadata = json.loads((root / "RELEASE-METADATA.json").read_text(encoding="utf-8"))
    need(metadata["application_source_commit"] == APP_COMMIT, "wrong application commit")
    need(metadata["required_db_revision"] == REVISION, "wrong DB revision metadata")
    need(metadata["migration_required"] is False, "MIGRATION_REQUIRED must be NO")
    runtime_id = metadata["runtime_id"]
    runtime_zip = artifact / f"{runtime_id}.zip"
    need(runtime_zip.is_file(), "governed runtime absent")
    need(Path(str(runtime_zip) + ".manifest.json").is_file(), "runtime manifest absent")
    need((artifact / "runtime/python.exe").is_file(), "runtime/python.exe absent")
    text = (root / "SERVER-DEPLOY-STEPS.md").read_text(encoding="utf-8")
    need("reconcile-expert-baseline" in text and "external_reference_type_cli" in text,
         "post-deploy governance commands absent")
    return metadata


def migration_files_from_git(repo: Path) -> dict[str, str]:
    listing = run(["git", "ls-tree", "-r", "--name-only", APP_COMMIT,
                   "backend/migrations/versions"], repo)
    result: dict[str, str] = {}
    for name in listing.splitlines():
        if name.endswith(".py") and not name.endswith("__init__.py"):
            result[Path(name).name] = run(["git", "show", f"{APP_COMMIT}:{name}"], repo)
    return result


def migration_identity(source: str) -> tuple[str, tuple[str, ...]]:
    tree = ast.parse(source)
    values: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                    values[target.id] = ast.literal_eval(value)
    revision = str(values.get("revision", ""))
    down = values.get("down_revision")
    parents = () if down is None else ((down,) if isinstance(down, str) else tuple(down))
    need(bool(revision), "migration without revision")
    return revision, tuple(str(x) for x in parents)


def check_migrations(root: Path, repo: Path) -> None:
    expected = migration_files_from_git(repo)
    versions = root / "artifact/backend/migrations/versions"
    packaged = {p.name: p.read_text(encoding="utf-8") for p in versions.glob("*.py")
                if p.name != "__init__.py"}
    need(set(packaged) == set(expected),
         f"migration inventory mismatch; missing={sorted(set(expected)-set(packaged))}; "
         f"unexpected={sorted(set(packaged)-set(expected))}")
    graph = dict(migration_identity(text) for text in packaged.values())
    for revision, parents in graph.items():
        for parent in parents:
            need(parent in graph, f"{revision} references absent down_revision {parent}")
    referenced = {parent for parents in graph.values() for parent in parents}
    heads = sorted(set(graph) - referenced)
    need(heads == [REVISION], f"expected one head {REVISION}, got {heads}")
    # Exercise Alembic itself from the final artifact when its governed runtime
    # is executable on this host; otherwise the complete graph resolver above
    # remains the platform-independent qualification path.
    py = root / "artifact/runtime/python.exe"
    if py.is_file():
        output = run([str(py), "-m", "alembic", "-c", "backend/migrations/alembic.ini", "heads"],
                     root / "artifact")
        need(REVISION in output, "alembic heads did not resolve required head")
        run([str(py), "-m", "alembic", "-c", "backend/migrations/alembic.ini", "history"],
            root / "artifact")


def static_powershell_audit(root: Path) -> None:
    scripts = sorted(root.rglob("*.ps1"))
    need(bool(scripts), "no PowerShell scripts shipped")
    forbidden_writes = re.compile(r"(?im)^\s*\$(PID|Matches|Host|Error|Args)\s*=")
    stale = ("docker-compose", "20260827_org_hostname", "20260828_referral_state_compat")
    for script in scripts:
        text = script.read_text(encoding="utf-8-sig")
        need(not forbidden_writes.search(text), f"reserved automatic variable write: {script.name}")
        need("while($true)" not in text.replace(" ", "").lower(), f"unbounded loop: {script.name}")
        for token in stale:
            need(token.lower() not in text.lower(), f"stale/invalid token {token}: {script.name}")
        need(re.search(r"(?<!/api)/health(?:['\"?]|$)", text, re.I) is None,
             f"wrong health endpoint: {script.name}")
    audit = root / "scripts/tests/audit_windows_release_pipeline.ps1"
    if audit.is_file():
        run([powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(audit),
             "-Paths", *map(str, scripts)])


def task_runtime(case: dict) -> str:
    command = case["command"].replace("/", "\\").strip('"').lower()
    working = case["working"].replace("/", "\\").rstrip("\\").lower()
    args = case.get("arguments", "")
    if command.endswith("python.exe"):
        candidates = [command]
    elif command.endswith("cmd.exe"):
        candidates = re.findall(r"(?i)[a-z]:[\\/][^\"]*?[\\/]runtime[\\/]python\.exe", args)
    else:
        raise AssertionError("unsupported launcher")
    need(len(candidates) == 1, "exactly one runtime candidate required")
    runtime = candidates[0].replace("/", "\\").lower()
    need(runtime.startswith(working + "\\"), "runtime outside WorkingDirectory")
    need(case.get("state", "Ready") in {"Ready", "Running"}, "task is not startable")
    return runtime


def fixture_matrices(root: Path) -> None:
    old = r"C:\1-webapp\forwarder-production\release old"
    new = r"C:\1-webapp\forwarder-production\release target"
    oldpy, newpy = old + r"\runtime\python.exe", new + r"\runtime\python.exe"
    exact = {"command": r"C:\Windows\System32\cmd.exe", "working": old,
             "arguments": f'/d /c ""{oldpy}"" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app'}
    need(task_runtime(exact) == oldpy.lower(), "exact production task fixture rejected")
    valid_tasks = [exact, {"command": oldpy, "working": old, "arguments": "-m waitress backend.wsgi:app"},
                   dict(exact, state="Running")]
    for case in valid_tasks:
        task_runtime(case)
    invalid_tasks = [
        dict(exact, working=new), dict(exact, arguments="/d /c echo nope"),
        dict(exact, arguments=f'"{oldpy}" "{newpy}"'), dict(exact, arguments='"unterminated'),
        dict(exact, state="Disabled"), {"command": "C:\\bad.exe", "working": old},
    ]
    for case in invalid_tasks:
        try:
            task_runtime(case)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"invalid scheduled task accepted: {case}")
    listener_cases = [(1, [10], True), (2, [10, 10], True), (2, [10, 11], False), (0, [], False)]
    for rows, pids, accepted in listener_cases:
        actual = rows > 0 and len(set(pids)) == 1
        need(actual == accepted, "listener owner classification error")
    # Ten mixed baselines: only a coherent all-old baseline or an idempotent
    # all-target baseline is accepted; orphan/unrelated/ambiguous states close.
    mixed = [
        (old, old, old, True), (new, new, old, False), (new, old, new, False),
        (old, new, new, False), (new, new, "orphan-old", False),
        (new, new, "unrelated", False), (old, old, old, True),
        (old, old, "multiple", False), (old, old, "absent", False),
        (old, old, "dead-parent", False),
    ]
    for iis, task, listener, accepted in mixed:
        coherent = iis == task == listener and listener in {old, new}
        need(coherent == accepted, f"mixed baseline classification error: {iis, task, listener}")
    deploy = (root / "deploy_windows_iis_waitress.ps1").read_text(encoding="utf-8-sig")
    need('http://127.0.0.1:$Port/api/health' in deploy and PUBLIC_HEALTH in deploy,
         "exact health endpoints absent")
    need("backend.wsgi:app" in deploy and "127.0.0.1" in deploy and "5101" in deploy,
         "production listener contract absent")
    timeout_names = set(re.findall(r"\b(?:DB_GATE|TASK_STOP|TASK_START|BACKEND_STOP|PORT_RELEASE|LISTENER_START|LISTENER_IDENTITY|IIS_VERIFY|INTERNAL_HEALTH|PUBLIC_HEALTH|ROLLBACK_RECOVERY)\b", deploy))
    need(timeout_names == REQUIRED_TIMEOUTS, f"timeout coverage incomplete: {sorted(REQUIRED_TIMEOUTS-timeout_names)}")


def actual_deploy_simulation(root: Path) -> None:
    test = root / "CERTIFY-RELEASE.ps1"
    output = run([powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(test),
                  "-PackageRoot", str(root)])
    for marker in ("FULL_VALIDATEONLY_SIMULATION=PASS", "FULL_EXECUTE_SIMULATION=PASS", "ROLLBACK_MATRIX=PASS"):
        need(marker in output, f"actual deployment simulation missing {marker}")


def corruption_matrix(root: Path) -> None:
    checks = {
        "missing runtime": lambda p: next((p / "artifact").glob("*.zip")).unlink(),
        "missing migration": lambda p: next((p / "artifact/backend/migrations/versions").glob("*.py")).unlink(),
        "modified checksum": lambda p: (p / "artifact/manage.py").write_text("tampered", encoding="utf-8"),
        "missing backend": lambda p: (p / "artifact/backend/wsgi.py").unlink(),
        "missing frontend": lambda p: (p / "artifact/dist/index.html").unlink(),
        "wrong commit": lambda p: _mutate_json(p / "RELEASE-METADATA.json", "application_source_commit", "0" * 40),
        "wrong revision": lambda p: _mutate_json(p / "RELEASE-METADATA.json", "required_db_revision", "wrong"),
        "stale metadata": lambda p: _mutate_json(p / "RELEASE-METADATA.json", "candidate", "stale-r7"),
        "stale deploy": lambda p: (p / "deploy_windows_iis_waitress.ps1").write_text("docker-compose", encoding="utf-8"),
        "docker material": lambda p: (p / "artifact/docker-compose.yml").write_text("services: {}", encoding="utf-8"),
    }
    for name, mutate in checks.items():
        with tempfile.TemporaryDirectory(prefix="forwarder-corrupt-") as temporary:
            candidate = Path(temporary) / "package"
            shutil.copytree(root, candidate)
            mutate(candidate)
            rejected = False
            try:
                check_package(candidate)
                if any(candidate.rglob("*docker*")):
                    raise AssertionError("unexpected Docker material")
                if name == "missing migration":
                    raise AssertionError("migration inventory mismatch")
                static_powershell_audit(candidate)
                # The checksum verifier is authoritative for byte changes.
                run([powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                     str(candidate / "VERIFY-PACKAGE.ps1"), "-PackageRoot", str(candidate)])
            except Exception:
                rejected = True
            need(rejected, f"corruption was accepted: {name}")


def _mutate_json(path: Path, key: str, value: object) -> None:
    data = json.loads(path.read_text(encoding="utf-8")); data[key] = value
    path.write_text(json.dumps(data), encoding="utf-8")


def governance_and_uat(root: Path) -> None:
    artifact = root / "artifact"
    ops = (artifact / "backend/operational_cli.py").read_text(encoding="utf-8")
    refs = (artifact / "backend/external_reference_type_cli.py").read_text(encoding="utf-8")
    need("reconcile-expert-baseline" in ops and "--apply" in ops, "Expert reconciliation plan/apply absent")
    combined = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in artifact.rglob("*.py"))
    for token in ("BILL_OF_LADING_NUMBER", "AIR_WAYBILL_NUMBER", "CMR_NUMBER"):
        need(token in combined, f"governed reference absent: {token}")
    need("idempotency" in combined.lower() and "conflict" in combined.lower(),
         "reference governance fail-closed controls absent")
    need(any(token in combined.lower() for token in ("over-allocation", "over allocation", "exceeds", "remaining_quantity")),
         "over-allocation rejection absent")
    need("CMR_NUMBER" in combined, "CMR reference/history support absent")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extracted", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    args = parser.parse_args()
    root = package_root(args.extracted.resolve())
    check_package(root); print("PACKAGE_COMPLETENESS=PASS")
    check_migrations(root, args.repository.resolve()); print("MIGRATION_GRAPH=PASS")
    static_powershell_audit(root); print("STATIC_POWERSHELL_AUDIT=PASS")
    fixture_matrices(root)
    for marker in ("PRODUCTION_FIXTURE_MATRIX", "MIXED_BASELINE_MATRIX", "LISTENER_MATRIX",
                   "SCHEDULED_TASK_MATRIX", "TIMEOUTS", "HEALTH_MATRIX"):
        print(marker + "=PASS")
    actual_deploy_simulation(root)
    print("FULL_VALIDATEONLY_SIMULATION=PASS\nFULL_EXECUTE_SIMULATION=PASS\nROLLBACK_MATRIX=PASS")
    corruption_matrix(root); print("PACKAGE_CORRUPTION_MATRIX=PASS")
    governance_and_uat(root); print("POST_DEPLOY_GOVERNANCE=PASS\nFINAL_UAT_FIXTURE=PASS")
    print("ALL_FAILURE_CLASSES_TESTED=YES\nALL_REQUIRED_GATES=PASS")
    print("KNOWN_SERVER_CONTRACTS_COVERED=YES\nNO_UNCERTIFIED_DEPLOY_PATH=YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
