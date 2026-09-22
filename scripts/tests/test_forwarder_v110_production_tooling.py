from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "scripts" / "production" / "v1.10.0"
R2_TASK_PROJECTION_FIXTURE = ROOT / "scripts" / "tests" / "fixtures" / "forwarder-v110-production-r2-scheduled-task-projection.json"
SOURCE = "e36ee7cee157657c97dc42a539eaf1909f510a33"
BEFORE = "20260921_shipment_evidence_ownership"
TARGET = "20260926_fixed_shipment_responsible_expert"
ADR047_SHA256 = "16a50c18a4e824ce35564beca18ea11131ed105d3d0d13f51e08ca021c780bae"
WINDOWS_POWERSHELL = Path(os.environ["WINDIR"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def task_xml(release: Path) -> str:
    release_text = str(release)
    python = str(release / "runtime" / "python.exe")
    launcher = r"C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py"
    payload = (
        f'set PYTHONPATH={release_text}&& cd /d "{release_text}"&& '
        f'"{python}" "{launcher}" serve --env "C:\\1-webapp\\forwarder-runtime\\production.env" '
        f'--repo "{release_text}" --host 127.0.0.1 --port 5101 '
        f'--log "C:\\1-webapp\\forwarder-runtime\\waitress.log"'
    )
    document = ET.Element("Task")
    actions = ET.SubElement(document, "Actions")
    action = ET.SubElement(actions, "Exec")
    ET.SubElement(action, "Command").text = r"C:\Windows\System32\cmd.exe"
    ET.SubElement(action, "Arguments").text = '/d /c "' + payload.replace('"', '""') + '"'
    ET.SubElement(action, "WorkingDirectory").text = release_text
    return ET.tostring(document, encoding="unicode")


def create_package(root: Path) -> tuple[Path, str]:
    package = root / "Forwarder-Production-v1.10.0-e36ee7cee157.zip"
    manifest = {
        "schema": "forwarder-production-release-manifest-v1",
        "product_name": "Forwarder",
        "release_stage": "Production",
        "application_version": "1.10.0",
        "frontend_version": "1.10.0",
        "backend_version": "1.10.0",
        "accepted_product_base_sha": "a742628293359379cb476b782a2fe27e61a8db1f",
        "application_commit": SOURCE,
        "release_source_sha": SOURCE,
        "before_database_revision": BEFORE,
        "database_revision": TARGET,
        "alembic_head_count": 1,
        "runtime_entrypoint": r"C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py",
        "runtime_id": "Forwarder-Windows-Runtime-S7-RC-a257669-r4",
        "runtime_sha256": "f4a8f108aa89a78d7986f01fb8f6aa8af5e2d35e00617a8453eb1f15df945070",
        "backend_listener_contract": "127.0.0.1:5101",
        "external_environment_path": r"C:\1-webapp\forwarder-runtime\production.env",
        "auto_migrate_on_startup": False,
        "mutable_data_packaged": False,
        "reference_impact": "NONE",
        "production_accessed": False,
        "build_date": "2026-09-21T20:00:00+00:00",
    }
    content: dict[str, bytes] = {
        "release-manifest.json": (json.dumps(manifest) + "\n").encode(),
        "APPLICATION-INVENTORY.json": (json.dumps([{
            "path": "backend/migration_cli.py", "bytes": len(b"# fixture\n"),
            "sha256": digest_bytes(b"# fixture\n"), "source_commit": SOURCE,
        }]) + "\n").encode(),
        "PRODUCTION-README.md": b"fixture\n",
        "runtime/python.exe": b"fixture-runtime",
        "dist/index.html": b"<!doctype html><title>Forwarder</title>",
        "backend/migration_cli.py": b"# fixture\n",
    }
    for name in (
        "Deploy-ForwarderV110Production.ps1",
        "Invoke-ForwarderV110RollbackContainment.ps1",
        "New-ForwarderV110PreDeploymentBackup.ps1",
        "Verify-ForwarderV110PostDeploy.ps1",
        "Verify-ForwarderV110ProductionPackage.ps1",
    ):
        content[f"production-tooling/{name}"] = (TOOLS / name).read_bytes()
    for name in (
        "adr047-production-classifier.sql",
        "migration-compatibility-readonly.sql",
        "post-migration-assertions-readonly.sql",
    ):
        content[f"production-tooling/sql/{name}"] = (TOOLS / "sql" / name).read_bytes()
    content["VERIFY-PRODUCTION-PACKAGE.ps1"] = (TOOLS / "Verify-ForwarderV110ProductionPackage.ps1").read_bytes()
    inventory = [
        {"path": name, "bytes": len(payload), "sha256": digest_bytes(payload)}
        for name, payload in sorted(content.items())
    ]
    content["PACKAGE-INVENTORY.json"] = (json.dumps(inventory) + "\n").encode()
    content["SHA256SUMS.txt"] = (
        "\n".join(f"{digest_bytes(payload)}  {name}" for name, payload in sorted(content.items())) + "\n"
    ).encode()
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, payload in sorted(content.items()):
            bundle.writestr(name, payload)
    package_hash = hashlib.sha256(package.read_bytes()).hexdigest()
    Path(str(package) + ".sha256").write_text(f"{package_hash}  {package.name}\n", encoding="ascii")
    return package, package_hash


def fixture(tmp_path: Path) -> dict[str, Path | str | dict]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    package, package_hash = create_package(tmp_path)
    release_root = tmp_path / "forwarder-production"
    runtime_root = tmp_path / "forwarder-runtime"
    backup_root = tmp_path / "forwarder-backups"
    document_root = tmp_path / "documents"
    for path in (release_root, runtime_root, backup_root, document_root):
        path.mkdir()
    current = release_root / "release-20260920010101-20260921_shipment_evidence_ownership"
    current_python = current / "runtime" / "python.exe"
    pre_execute_evidence_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=1)
    preflight = {
        "schema": "forwarder-v1.10.0-production-readonly-preflight-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "collector_status": "PASS",
        "host": {"computer_name": "fixture"},
        "collection_errors": 0,
        "active_release": {"runtime_agreement": True, "active_release_path": str(current)},
        "listener_ownership_verified": True,
        "mandatory_config_missing_or_invalid_count": 0,
        "scheduled_task": {"release_path": str(current)},
        "listeners": [{"executable": str(current_python)}],
        "iis": {"physical_path": str(current / "dist")},
        "config": {
            "AUTO_MIGRATE_ON_STARTUP": {"state": "SAFE_VALUE_OK"},
            "CORS_ALLOW_ALL_ORIGINS": {"state": "SAFE_VALUE_OK"},
            "DOCUMENT_STORAGE_ROOT": {"state": "PRESENT", "path": str(document_root), "exists": True, "outside_release_root": True},
        },
        "database": {
            "collection": "AVAILABLE",
            "identity": {"alembic_revision_count": 1, "alembic_revision": BEFORE, "primary_state": "PRIMARY", "database_size_bytes": 1024},
            "schema_drift_blocker_count": 0,
            "adr047": {
                "fixed_owner_already_valid_count": 2,
                "fixed_owner_deterministic_repair_count": 1,
                "fixed_owner_ambiguous_count": 0,
                "fixed_owner_contradiction_count": 0,
                "fixed_owner_other_unresolved_count": 0,
            },
        },
        "backup_readiness": {
            "mechanism_identified": True,
            "destination_ready": True,
            "tooling_available": True,
            "latest_dump": {"dump_sha256": "a" * 64},
            "backup_evidence_available": True,
            "backup_evidence": {
                "state": "VERIFIED_EXACT_DUMP",
                "created_utc": pre_execute_evidence_time.isoformat(),
                "dump_sha256": "a" * 64,
            },
            "restore_evidence_available": True,
            "restore_evidence": {
                "state": "VERIFIED_EXACT_DUMP",
                "tested_utc": pre_execute_evidence_time.isoformat(),
                "source_dump_sha256": "a" * 64,
            },
            "pre_execute_backup_restore_proof_required": True,
            "pre_execute_backup_restore_proof_ready": True,
            "pre_execute_backup_restore_proof_status": "PASS",
            "fresh_deployment_window_backup_present": False,
            "fresh_deployment_window_backup_required": True,
            "deployment_window_backup_timing": "AFTER_WRITER_CONTAINMENT_BEFORE_MIGRATION",
            "deployment_window_backup_verification": "HASH_SIZE_CATALOG_AND_BASELINE_IDENTITY",
            "deployment_prerequisite_status": "READY_FOR_SEPARATE_GO_REVIEW",
        },
        "deployment_prerequisite_status": "READY_FOR_SEPARATE_GO_REVIEW",
        "storage": {"drives": [{"root": release_root.anchor, "free_bytes": 10 * 1024**3}]},
    }
    preflight_path = tmp_path / "preflight.json"
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
    state = {
        "iis_path": str(current / "dist"), "task_enabled": True, "task_xml": task_xml(current),
        "task_release": str(current), "listener_pid": 42, "listener_executable": str(current_python),
        "listener_command": f'"{current_python}" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app',
        "listener_release": str(current), "listener_up": True, "health": True, "readiness": True,
        "public_health": True, "public_readiness": True, "frontend": True, "login_shell": True,
        "numeric_tracking_status": 404, "invalid_tracking_status": 404, "database_head": BEFORE,
        "traffic_contained": False, "backup_verified": True, "migration_allowed": True,
        "deterministic_repairs_applied": 0,
        "containment_behavior": "immediate", "containment_timeout_milliseconds": 500,
        "containment_poll_milliseconds": 20, "containment_quiet_milliseconds": 60,
        "post_assertions": [{"code": "FIXTURE", "state": "PASS", "detail": "controlled"}],
    }
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    target = release_root / f"release-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{TARGET}"
    return {
        "package": package, "package_hash": package_hash, "release_root": release_root,
        "runtime_root": runtime_root, "backup_root": backup_root, "document_root": document_root,
        "preflight": preflight, "preflight_path": preflight_path, "state": state,
        "state_path": state_path, "target": target,
    }


def run_deployer(data: dict, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(WINDOWS_POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(TOOLS / "Deploy-ForwarderV110Production.ps1"),
            "-PackagePath", str(data["package"]), "-ExpectedPackageSha256", str(data["package_hash"]),
            "-PreflightResultPath", str(data["preflight_path"]), "-TargetReleasePath", str(data["target"]),
            "-FixtureStatePath", str(data["state_path"]), "-ReleaseRoot", str(data["release_root"]),
            "-RuntimeRoot", str(data["runtime_root"]), "-ApprovedBackupRoot", str(data["backup_root"]),
            *extra,
        ],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace",
    )


def test_powershell_scripts_parse() -> None:
    script = """
$root=$args[0];$failed=$false
Get-ChildItem -LiteralPath $root -Filter '*.ps1' -File|ForEach-Object{$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$t,[ref]$e)|Out-Null;if($e.Count){$failed=$true;$e|ForEach-Object{Write-Output ($_.Extent.StartLineNumber.ToString()+':'+$_.Message)}}}
if($failed){exit 1}
"""
    escaped_root = str(TOOLS).replace("'", "''")
    command = "& { param([string]$root) " + script + " } '" + escaped_root + "'"
    result = subprocess.run([str(WINDOWS_POWERSHELL), "-NoProfile", "-Command", command], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert result.returncode == 0, result.stdout


def test_powershell_scripts_do_not_define_automatic_or_read_only_variables() -> None:
    script = r"""
$root=$args[0]
$protected=@(Get-Variable|Where-Object{$_.Options -match 'ReadOnly|Constant'}|Select-Object -ExpandProperty Name)
$protected+=@('args','input','this','foreach','switch','matches','MyInvocation','PSScriptRoot','PSBoundParameters','NestedPromptLevel','PSCmdlet','StackTrace','LastExitCode')
$violations=New-Object 'System.Collections.Generic.List[string]'
Get-ChildItem -LiteralPath $root -Filter '*.ps1' -File|ForEach-Object{
    $file=$_;$tokens=$null;$errors=$null
    $ast=[System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$tokens,[ref]$errors)
    $definitions=New-Object 'System.Collections.Generic.List[object]'
    $ast.FindAll({param($node) $node -is [System.Management.Automation.Language.AssignmentStatementAst]},$true)|ForEach-Object{
        $_.Left.FindAll({param($node) $node -is [System.Management.Automation.Language.VariableExpressionAst]},$true)|ForEach-Object{$definitions.Add($_)}
    }
    $ast.FindAll({param($node) $node -is [System.Management.Automation.Language.ParameterAst]},$true)|ForEach-Object{$definitions.Add($_.Name)}
    $ast.FindAll({param($node) $node -is [System.Management.Automation.Language.ForEachStatementAst]},$true)|ForEach-Object{$definitions.Add($_.Variable)}
    foreach($definition in $definitions){
        $name=$definition.VariablePath.UserPath
        if($protected -icontains $name){$violations.Add($file.Name+':'+$definition.Extent.StartLineNumber+':$'+$name)}
    }
}
$violations|Sort-Object -Unique|Write-Output
if($violations.Count){exit 1}
"""
    escaped_root = str(TOOLS).replace("'", "''")
    command = "& { param([string]$root) " + script + " } '" + escaped_root + "'"
    result = subprocess.run(
        [str(WINDOWS_POWERSHELL), "-NoProfile", "-Command", command],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout


def test_collector_is_read_only_and_secret_safe() -> None:
    source = (TOOLS / "Collect-ForwarderV110ProductionReadOnly.ps1").read_text(encoding="utf-8")
    forbidden_commands = (
        "Set-WebConfigurationProperty", "Register-ScheduledTask", "Enable-ScheduledTask", "Disable-ScheduledTask",
        "Start-ScheduledTask", "Stop-ScheduledTask", "Stop-Process", "Start-Process", "Copy-Item", "Move-Item",
        "Remove-Item", "Restart-Service", "Set-Service", "New-Service", "Invoke-Expression",
    )
    assert not any(re.search(rf"(?im)^\s*{re.escape(command)}\b", source) for command in forbidden_commands)
    assert "BEGIN TRANSACTION READ ONLY" in source
    assert "SQL_MUTATION_KEYWORD_REJECTED" in source
    assert "secret_values_emitted=$false" in source
    assert "production_mutation_performed=$false" in source
    assert "DATABASE_URL']" in source and "DATABASE_URL=" not in source
    assert "Get-ScheduledTask -TaskName $TaskName" not in source
    assert "SCHEDULED_TASK_IDENTITY_AMBIGUOUS" in source
    assert "LEGACY_PRODUCTION_WITNESS" in source
    assert "ACTIVE_RELEASE_SOURCE_IDENTITY_UNPROVEN" in source
    assert "VERIFIED_EXACT_DUMP" in source
    assert "pre_execute_backup_restore_proof_ready" in source
    assert "deployment_window_backup_timing='AFTER_WRITER_CONTAINMENT_BEFORE_MIGRATION'" in source
    assert "elseif (-not $backup.pre_execute_backup_restore_proof_ready)" in source
    assert "or -not $backup.fresh_deployment_window_backup_present" not in source


def test_collector_live_topology_self_test_and_legacy_witness(tmp_path: Path) -> None:
    release = tmp_path / "release-without-manifest"
    files = {
        "backend/probe.py": b"legacy backend witness\n",
        "dist/index.html": b"<!doctype html><title>legacy</title>\n",
    }
    inventory = []
    for relative, payload in sorted(files.items()):
        path = release / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        inventory.append({"path": relative, "bytes": len(payload), "sha256": digest_bytes(payload)})
    canonical = "".join(f"{item['path']}\0{item['sha256']}\n" for item in inventory).encode()
    witness = tmp_path / "legacy-production-witness.json"
    witness.write_text(json.dumps({
        "schema": "forwarder-v1.10.0-legacy-production-witness-v1",
        "authority": "controlled_test_fixture",
        "source_archive_sha256": "1" * 64,
        "candidate": "legacy-fixture",
        "application_source_commit": "e" * 40,
        "application_version": None,
        "required_database_revision": BEFORE,
        "inventory_sha256": digest_bytes(canonical),
        "file_count": len(inventory),
        "frontend_file_count": 1,
        "backend_file_count": 1,
        "files": inventory,
    }), encoding="utf-8")
    result = subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(TOOLS / "Collect-ForwarderV110ProductionReadOnly.ps1"), "-ToolingSelfTest",
        "-SelfTestReleaseRoot", str(release), "-SelfTestWitnessPath", str(witness),
        "-SelfTestProjectionFixturePath", str(R2_TASK_PROJECTION_FIXTURE),
    ], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stdout
    assert "TASK_NAME_MISMATCH_WITH_EXACT_ACTION=PASS" in result.stdout
    assert "TASK_AMBIGUITY=FAIL_CLOSED" in result.stdout
    assert "R2_SELECTED_TASK_PROJECTION=PASS" in result.stdout
    assert "R2_LISTENER_OWNERSHIP=TRUE" in result.stdout
    assert "R2_LISTENER_OWNERSHIP_MISMATCH=FAIL_CLOSED" in result.stdout
    assert "LEGACY_RELEASE_WITHOUT_MANIFEST=IDENTITY_PROVEN_BY_WITNESS" in result.stdout
    assert "PRODUCTION_MUTATION_PERFORMED=NO" in result.stdout


def test_backup_and_restore_proof_tooling_self_tests() -> None:
    backup = subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(TOOLS / "New-ForwarderV110PreDeploymentBackup.ps1"),
        "-RestoreOwner", "controlled-self-test", "-ToolingSelfTest",
    ], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    assert backup.returncode == 0, backup.stdout
    assert "SQLALCHEMY_DATABASE_URL=SUPPORTED" in backup.stdout
    assert "BACKUP_EVIDENCE_CONTRACT=PASS" in backup.stdout
    assert "PRODUCTION_MUTATION_PERFORMED=NO" in backup.stdout

    restore = subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(TOOLS / "Invoke-ForwarderV110ProductionRestoreProof.ps1"), "-ToolingSelfTest",
    ], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    assert restore.returncode == 0, restore.stdout
    assert "ISOLATED_RESTORE_TARGET=DISPOSABLE_ONLY" in restore.stdout
    assert "FIVE_MIGRATION_SEQUENCE=EXACT" in restore.stdout
    assert "PRODUCTION_ACCESS_PERFORMED=NO" in restore.stdout

    deployer = subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(TOOLS / "Deploy-ForwarderV110Production.ps1"),
            "-PackagePath", "controlled-self-test.zip",
            "-ExpectedPackageSha256", "0" * 64,
            "-PreflightResultPath", "controlled-self-test.json",
            "-TargetReleasePath", "C:\\controlled-self-test",
            "-ToolingSelfTest",
            "-SelfTestPythonPath", sys.executable,
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    assert deployer.returncode == 0, deployer.stdout
    assert "NATIVE_ORPHAN_LISTENER_PARENT_ABSENT=PASS" in deployer.stdout
    assert "NATIVE_EXACT_PID_SOCKET_TEARDOWN=PASS" in deployer.stdout
    assert "DEPLOYER_SQLALCHEMY_DATABASE_URL=SUPPORTED" in deployer.stdout
    assert "PRODUCTION_MUTATION_PERFORMED=NO" in deployer.stdout


def test_backup_restore_proof_contract_is_bounded_and_secret_safe() -> None:
    backup = (TOOLS / "New-ForwarderV110PreDeploymentBackup.ps1").read_text(encoding="utf-8")
    restore = (TOOLS / "Invoke-ForwarderV110ProductionRestoreProof.ps1").read_text(encoding="utf-8")
    deployer = (TOOLS / "Deploy-ForwarderV110Production.ps1").read_text(encoding="utf-8")
    assert "postgresql\\+psycopg2" in backup
    assert "forwarder-v1.10.0-predeployment-backup-evidence-v2" in backup
    assert "Forwarder-v1.10.0-PreDeploymentBackup-$stamp.json" in backup
    assert "database_revision=$identity.AlembicRevision" in backup
    assert "PRODUCTION_DATABASE_MUTATED=NO" in backup
    assert "Read-Host" in restore and "-AsSecureString" in restore
    assert "--exit-on-error --single-transaction --no-owner --no-privileges" in restore
    assert "forwarder-production-restore-evidence-v1" in restore
    assert "Remove-OwnedDatabase" in restore
    assert "production_accessed=$false" in restore
    assert "postgresql\\+psycopg2" in deployer
    assert "PGSSLMODE" in deployer
    for revision in (
        "20260922_notification_foundation", "20260923_notification_lifecycle",
        "20260924_request_cargo_items", "20260925_quote_communication",
        "20260926_fixed_shipment_responsible_expert",
    ):
        assert revision in restore


def test_database_bridge_uses_runtime_loader_and_never_places_secret_on_command_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    helper_path = TOOLS / "Invoke-ForwarderV110ReadOnlySql.py"
    spec = importlib.util.spec_from_file_location("forwarder_v110_readonly_bridge", helper_path)
    assert spec and spec.loader
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    secret = "test-only-p%40ss:word"
    env_file = tmp_path / "production.env"
    env_file.write_text(
        f'DATABASE_URL="postgresql+psycopg2://forwarder_user:{secret}@127.0.0.1:5432/forwarder?sslmode=require"\n',
        encoding="utf-8",
    )
    psql = tmp_path / "psql.exe"
    psql.write_bytes(b"fixture")
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["environment"] = dict(kwargs["env"])
        captured["input"] = kwargs["input"]
        return subprocess.CompletedProcess(command, 0, stdout="SAFE|PASS|fixture\n", stderr="")

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)
    sql = "BEGIN TRANSACTION READ ONLY;\nSELECT 1;\nCOMMIT;\n"
    output = bridge.run_read_only_sql(environment_file=env_file, psql_path=psql, sql=sql)
    assert output == "SAFE|PASS|fixture\n"
    assert secret not in " ".join(captured["command"])
    assert captured["environment"]["PGPASSWORD"] == "test-only-p@ss:word"
    assert captured["environment"]["PGSSLMODE"] == "require"
    assert captured["input"] == sql
    assert secret not in output


def test_collector_runs_in_controlled_missing_infrastructure_fixture(tmp_path: Path) -> None:
    output = tmp_path / "collector-output"
    output.mkdir()
    missing = tmp_path / "missing"
    result = subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(TOOLS / "Collect-ForwarderV110ProductionReadOnly.ps1"),
            "-OutputDirectory", str(output), "-EnvironmentFile", str(missing / "production.env"),
            "-ReleaseRoot", str(missing / "releases"), "-RuntimeRoot", str(missing / "runtime"),
            "-ApprovedBackupRoot", str(missing / "backups"),
            "-TaskName", "Forwarder v1.10.0 controlled missing fixture",
            "-IisSiteName", "forwarder-v110-controlled-missing", "-BackendPort", "65500",
            "-PsqlPath", str(missing / "psql.exe"), "-PgDumpPath", str(missing / "pg_dump.exe"),
            "-PgRestorePath", str(missing / "pg_restore.exe"),
        ],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stdout
    files = list(output.glob("Forwarder-v1.10.0-Production-ReadOnly-Preflight-*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["collector_status"] == "BLOCKED"
    assert payload["production_mutation_performed"] is False
    assert payload["secret_values_emitted"] is False
    assert "PRODUCTION_MUTATION_PERFORMED=NO" in result.stdout


def test_collector_exact_dump_restore_proof_is_a_distinct_pre_execute_gate(tmp_path: Path) -> None:
    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    created = datetime.now(timezone.utc).replace(microsecond=0)
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    dump = backup_root / f"forwarder-v1.10.0-predeploy-{stamp}.dump"
    dump.write_bytes(b"controlled exact restore-proven production backup fixture\n")
    dump_hash = digest_bytes(dump.read_bytes())
    catalog = Path(str(dump) + ".list.txt")
    catalog.write_text("fixture catalog\n", encoding="utf-8")
    hash_sidecar = Path(str(dump) + ".sha256.txt")
    hash_sidecar.write_text(f"{dump_hash}  {dump.name}\n", encoding="ascii")
    computer_name = subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-Command", "[Environment]::MachineName"],
        text=True,
    ).strip()
    backup_evidence = {
        "schema": "forwarder-v1.10.0-predeployment-backup-evidence-v2",
        "status": "PASS",
        "created_utc": created.isoformat(),
        "production_host": computer_name,
        "purpose": "fresh_predeployment_backup_and_isolated_restore_input",
        "product_version": "1.10.0",
        "current_application_commit": "e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4",
        "target_application_commit": SOURCE,
        "database_revision": BEFORE,
        "alembic_revision_count": 1,
        "database_state": "PRIMARY",
        "postgresql_version": "18.1",
        "database_size_bytes": 4096,
        "dump_format": "custom",
        "dump_size_bytes": dump.stat().st_size,
        "dump_sha256": dump_hash,
        "backup_path": str(dump.resolve()),
        "approved_backup_root": str(backup_root.resolve()),
        "catalog_path": str(catalog.resolve()),
        "sha256_sidecar_path": str(hash_sidecar.resolve()),
        "pg_dump_exit_code": 0,
        "pg_restore_list_exit_code": 0,
        "catalog_verification": "PASS",
        "production_database_mutated": False,
        "production_deployment_performed": False,
        "secret_values_emitted": False,
        "reference_impact": "NONE",
        "verified": True,
    }
    backup_json = backup_root / f"Forwarder-v1.10.0-PreDeploymentBackup-{stamp}.json"
    backup_json.write_text(json.dumps(backup_evidence), encoding="utf-8")
    restore_evidence = {
        "schema": "forwarder-production-restore-evidence-v1",
        "restore_test_status": "PASS",
        "tested_utc": created.isoformat(),
        "source_dump_sha256": dump_hash,
        "source_dump_size_bytes": dump.stat().st_size,
        "source_database_revision": BEFORE,
        "restored_database_disposable": True,
        "disposable_database_removed": True,
        "local_postgresql_major": 18,
        "baseline_compatibility": "PASS",
        "migration_sequence": [
            "20260922_notification_foundation",
            "20260923_notification_lifecycle",
            "20260924_request_cargo_items",
            "20260925_quote_communication",
            "20260926_fixed_shipment_responsible_expert",
        ],
        "production_derived_migration_rehearsal": "PASS",
        "target_database_revision": TARGET,
        "target_alembic_head_count": 1,
        "pending_migrations": False,
        "post_migration_assertions": "PASS",
        "post_migration_assertion_count": 12,
        "adr047_production_data": "PASS",
        "notification_migration_rows": 0,
        "synthetic_historical_cargo_rows": 0,
        "target_application_source": SOURCE,
        "package_sha256": "2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf",
        "production_accessed": False,
        "production_database_mutated": False,
        "production_deployment_performed": False,
        "customer_rows_emitted": False,
        "credentials_emitted": False,
        "reference_impact": "NONE",
    }
    restore_json = Path(str(dump) + ".restore-evidence.json")
    restore_json.write_text(json.dumps(restore_evidence), encoding="utf-8")

    def collect(output: Path) -> dict:
        output.mkdir()
        missing = tmp_path / "missing"
        result = subprocess.run(
            [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(TOOLS / "Collect-ForwarderV110ProductionReadOnly.ps1"),
                "-OutputDirectory", str(output), "-EnvironmentFile", str(missing / "production.env"),
                "-ReleaseRoot", str(missing / "releases"), "-RuntimeRoot", str(missing / "runtime"),
                "-ApprovedBackupRoot", str(backup_root),
                "-TaskName", "Forwarder v1.10.0 controlled missing fixture",
                "-IisSiteName", "forwarder-v110-controlled-missing", "-BackendPort", "65500",
                "-PsqlPath", str(missing / "psql.exe"), "-PgDumpPath", str(missing / "pg_dump.exe"),
                "-PgRestorePath", str(missing / "pg_restore.exe"),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0, result.stdout
        files = list(output.glob("Forwarder-v1.10.0-Production-ReadOnly-Preflight-*.json"))
        assert len(files) == 1
        return json.loads(files[0].read_text(encoding="utf-8"))

    payload = collect(tmp_path / "valid-output")
    readiness = payload["backup_readiness"]
    assert readiness["pre_execute_backup_restore_proof_status"] == "PASS"
    assert readiness["pre_execute_backup_restore_proof_ready"] is True
    assert readiness["restore_evidence"]["state"] == "VERIFIED_EXACT_DUMP"
    assert readiness["latest_dump"]["dump_sha256"] == dump_hash
    assert readiness["fresh_deployment_window_backup_present"] is False
    assert readiness["deployment_window_backup_timing"] == "AFTER_WRITER_CONTAINMENT_BEFORE_MIGRATION"
    assert payload["deployment_prerequisite_status"] == "BLOCKED_COLLECTOR"

    restore_evidence["source_dump_sha256"] = "0" * 64
    restore_json.write_text(json.dumps(restore_evidence), encoding="utf-8")
    invalid = collect(tmp_path / "invalid-output")["backup_readiness"]
    assert invalid["pre_execute_backup_restore_proof_ready"] is False
    assert invalid["restore_evidence"]["state"] == "INVALID_METADATA_OR_IDENTITY"


def test_adr047_classifier_is_exact_preserved_contract() -> None:
    sql = (TOOLS / "sql" / "adr047-production-classifier.sql").read_bytes()
    assert hashlib.sha256(sql).hexdigest() == ADR047_SHA256
    text = sql.decode()
    for forbidden in ("is_active", "assigned_to", "PLATFORM_ADMIN", "ORGANIZATION_ADMIN", "created_by"):
        if forbidden == "created_by":
            assert "created_by_expert_id" in text
        else:
            assert forbidden not in text
    assert "BEGIN TRANSACTION READ ONLY;" in text and text.rstrip().endswith("COMMIT;")


def test_package_builder_identity_and_determinism_contract() -> None:
    source = (TOOLS / "build_forwarder_v110_production_release.py").read_text(encoding="utf-8")
    assert f'SOURCE_SHA = "{SOURCE}"' in source
    assert f'TARGET_HEAD = "{TARGET}"' in source
    assert '"release_stage": "Production"' in source
    assert '"historical_security_remediation": HISTORICAL_SECURITY_REMEDIATION' in source
    assert "write_deterministic_zip" in source
    assert "START-UAT.ps1" not in source


def test_transfer_bundle_builder_keeps_preflight_and_deployment_separate() -> None:
    source = (TOOLS / "build_forwarder_v110_transfer_bundles.py").read_text(encoding="utf-8")
    assert "READ_ONLY_NAME" in source and "DEPLOYMENT_NAME" in source
    assert 'READ_ONLY_REVISION = "r5"' in source
    assert 'DEPLOYMENT_REVISION = "r5"' in source
    read_only_section, deployment_section = source.split("deployment_root.mkdir()", 1)
    assert "Collect-ForwarderV110ProductionReadOnly.ps1" in read_only_section
    assert "Invoke-ForwarderV110ReadOnlySql.py" in read_only_section
    assert "legacy-production-witness.json" in read_only_section
    assert "Deploy-ForwarderV110Production.ps1" not in read_only_section
    assert "shutil.copy2(package" in deployment_section
    assert '"production_mutation_authorized": False' in source


def test_read_only_only_bundle_build_does_not_rebuild_or_emit_deployment_bundle(tmp_path: Path) -> None:
    package_root = tmp_path / "package"
    package_root.mkdir()
    package, _ = create_package(package_root)
    output = tmp_path / "output"
    result = subprocess.run([
        "python", str(TOOLS / "build_forwarder_v110_transfer_bundles.py"),
        "--package", str(package), "--output-root", str(output), "--read-only-only",
    ], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stdout
    archives = list(output.glob("Forwarder-v1.10.0-Read-Only-Preflight-Bundle-*-r5.zip"))
    assert len(archives) == 1
    assert not list(output.glob("*Production-Deployment-Bundle*.zip"))
    with zipfile.ZipFile(archives[0]) as bundle:
        names = set(bundle.namelist())
        assert "Collect-ForwarderV110ProductionReadOnly.ps1" in names
        assert "Invoke-ForwarderV110ReadOnlySql.py" in names
        assert "legacy-production-witness.json" in names
        assert "Deploy-ForwarderV110Production.ps1" not in names


def test_deployment_only_bundle_preserves_product_and_contains_authoritative_gate_tooling(tmp_path: Path) -> None:
    package_root = tmp_path / "package"
    package_root.mkdir()
    package, package_hash = create_package(package_root)
    output = tmp_path / "output"
    result = subprocess.run(
        [
            "python",
            str(TOOLS / "build_forwarder_v110_transfer_bundles.py"),
            "--package",
            str(package),
            "--output-root",
            str(output),
            "--deployment-only",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout
    archives = list(output.glob("Forwarder-v1.10.0-Production-Deployment-Bundle-*-r5.zip"))
    assert len(archives) == 1
    assert not list(output.glob("*Read-Only-Preflight-Bundle*.zip"))
    with zipfile.ZipFile(archives[0]) as bundle:
        manifest = json.loads(bundle.read("BUNDLE-MANIFEST.json"))
        assert manifest["deployment_tooling_revision"] == "r5"
        assert manifest["failed_target_disposition"] == "preserve_and_use_new_absent_target"
        assert manifest["writer_containment_timeout_milliseconds"] == 15000
        assert manifest["writer_containment_poll_milliseconds"] == 250
        assert manifest["writer_containment_quiet_milliseconds"] == 2000
        assert manifest["writer_containment_process_scope"] == "captured_identity_revalidated_listener_pid_only"
        assert manifest["replacement_listener_disposition"] == "fail_closed_do_not_terminate"
        assert len(manifest["known_failed_targets"]) == 2
        assert manifest["authoritative_deployer"] == "bundle_root/Deploy-ForwarderV110Production.ps1"
        assert manifest["frozen_product_package_rebuilt"] is False
        assert digest_bytes(bundle.read(package.name)) == package_hash
        deployer = bundle.read("Deploy-ForwarderV110Production.ps1").decode()
        assert "READY_FOR_SEPARATE_GO_REVIEW" in deployer
        assert "postgresql\\+psycopg2" in deployer
        assert "$listenerPid" in deployer
        assert not re.search(r"(?i)\\$pid\\b", deployer)
        assert "WriterContainmentTimeoutMilliseconds=15000" in deployer
        assert "replacement listener detected" in deployer
        assert "replacement_not_terminated=YES" in deployer
        assert "Stop-Process -Id $ProcessId -Force" in deployer
        assert deployer.count("Stop-Process") == 2

    second_output = tmp_path / "second-output"
    repeated = subprocess.run(
        [
            "python",
            str(TOOLS / "build_forwarder_v110_transfer_bundles.py"),
            "--package",
            str(package),
            "--output-root",
            str(second_output),
            "--deployment-only",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    assert repeated.returncode == 0, repeated.stdout
    repeated_archive = next(second_output.glob("Forwarder-v1.10.0-Production-Deployment-Bundle-*-r5.zip"))
    assert repeated_archive.read_bytes() == archives[0].read_bytes()


def test_checked_in_legacy_witness_is_strong_and_source_bound() -> None:
    witness = json.loads((TOOLS / "legacy-production-witness.json").read_text(encoding="utf-8"))
    assert witness["application_source_commit"] == "e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4"
    assert witness["source_archive_sha256"] == "e9196ad9cc10dfeef44eba40d98e50520af4c505474211d5c23397bdf7774617"
    assert witness["required_database_revision"] == BEFORE
    assert witness["file_count"] == len(witness["files"]) == 323
    assert witness["frontend_file_count"] == 13
    assert witness["backend_file_count"] == 309
    canonical = "".join(f"{item['path']}\0{item['sha256']}\n" for item in witness["files"]).encode()
    assert digest_bytes(canonical) == witness["inventory_sha256"]


def test_package_verifier_accepts_valid_and_rejects_hash_mismatch(tmp_path: Path) -> None:
    package, package_hash = create_package(tmp_path)
    command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(TOOLS / "Verify-ForwarderV110ProductionPackage.ps1"), "-PackagePath", str(package), "-ExpectedSha256", package_hash]
    passed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert passed.returncode == 0 and "PRODUCTION_PACKAGE_VERIFICATION=PASS" in passed.stdout
    failed = subprocess.run(command[:-1] + ["0" * 64], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert failed.returncode != 0 and "outer SHA256 mismatch" in failed.stdout


def test_validate_only_is_zero_mutation(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    before = Path(data["state_path"]).read_bytes()
    result = run_deployer(data, "-ValidateOnly")
    assert result.returncode == 0, result.stdout
    assert "PRODUCTION_VALIDATE_ONLY=PASS" in result.stdout
    assert "VALIDATEONLY_ZERO_MUTATION=YES" in result.stdout
    assert Path(data["state_path"]).read_bytes() == before
    assert not Path(data["target"]).exists()


def test_validate_only_enforces_ready_aggregate_and_exact_restore_identity(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    before = Path(data["state_path"]).read_bytes()
    data["preflight"]["deployment_prerequisite_status"] = "BLOCKED_PRE_EXECUTE_BACKUP_RESTORE_PROOF_REQUIRED"  # type: ignore[index]
    Path(data["preflight_path"]).write_text(json.dumps(data["preflight"]), encoding="utf-8")
    result = run_deployer(data, "-ValidateOnly")
    assert result.returncode != 0 and "not ready for separate GO review" in result.stdout
    assert Path(data["state_path"]).read_bytes() == before
    assert not Path(data["target"]).exists()

    data = fixture(tmp_path / "hash-mismatch")
    data["preflight"]["backup_readiness"]["restore_evidence"]["source_dump_sha256"] = "0" * 64  # type: ignore[index]
    Path(data["preflight_path"]).write_text(json.dumps(data["preflight"]), encoding="utf-8")
    result = run_deployer(data, "-ValidateOnly")
    assert result.returncode != 0 and "dump identity mismatch" in result.stdout
    assert not Path(data["target"]).exists()


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (("database", "identity", "alembic_revision"), "wrong starting database revision"),
        (("database", "adr047", "fixed_owner_ambiguous_count"), "ambiguous rows"),
        (("database", "adr047", "fixed_owner_contradiction_count"), "contradictory rows"),
        (("database", "adr047", "fixed_owner_other_unresolved_count"), "unresolved rows"),
        (("database", "schema_drift_blocker_count"), "schema drift"),
        (("mandatory_config_missing_or_invalid_count",), "mandatory config"),
        (("backup_readiness", "tooling_available"), "backup readiness"),
    ],
)
def test_validate_only_blocks_unsafe_preflight(tmp_path: Path, mutation: tuple[str, ...], expected: str) -> None:
    data = fixture(tmp_path)
    value: object = data["preflight"]
    for key in mutation[:-1]:
        value = value[key]  # type: ignore[index]
    key = mutation[-1]
    value[key] = (BEFORE + "_wrong") if key == "alembic_revision" else (False if key == "tooling_available" else 1)  # type: ignore[index]
    Path(data["preflight_path"]).write_text(json.dumps(data["preflight"]), encoding="utf-8")
    result = run_deployer(data, "-ValidateOnly")
    assert result.returncode != 0 and expected.lower() in result.stdout.lower()


def test_validate_only_blocks_insufficient_capacity_and_process_mismatch(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    data["preflight"]["storage"]["drives"][0]["free_bytes"] = 1  # type: ignore[index]
    Path(data["preflight_path"]).write_text(json.dumps(data["preflight"]), encoding="utf-8")
    result = run_deployer(data, "-ValidateOnly")
    assert result.returncode != 0 and "insufficient" in result.stdout.lower()
    data = fixture(tmp_path / "second")
    Path(data["state_path"]).parent.mkdir(parents=True, exist_ok=True) if not Path(data["state_path"]).parent.exists() else None
    state = copy.deepcopy(data["state"])
    state["listener_executable"] = str(tmp_path / "unowned" / "python.exe")
    Path(data["state_path"]).write_text(json.dumps(state), encoding="utf-8")
    result = run_deployer(data, "-ValidateOnly")
    assert result.returncode != 0 and "listener changed" in result.stdout.lower()


def test_validate_only_blocks_target_collision(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    Path(data["target"]).mkdir()
    result = run_deployer(data, "-ValidateOnly")
    assert result.returncode != 0 and "already exists" in result.stdout.lower()


def test_execute_fixture_applies_deterministic_repair_and_cutover(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    result = run_deployer(data, "-Execute", "-ConfirmDeployment", "-RestoreOwner", "fixture-dba")
    assert result.returncode == 0, result.stdout
    state = json.loads(Path(data["state_path"]).read_text(encoding="utf-8-sig"))
    assert state["database_head"] == TARGET
    assert state["deterministic_repairs_applied"] == 1
    assert state["task_enabled"] and state["listener_up"]
    assert Path(state["iis_path"]) == Path(data["target"]) / "dist"
    baseline_line = next(line for line in result.stdout.splitlines() if line.startswith("BASELINE_STATE="))
    baseline = json.loads(Path(baseline_line.split("=", 1)[1]).read_text(encoding="utf-8"))
    assert baseline["pre_execute_backup_restore_proof_status"] == "PASS"
    assert baseline["pre_execute_restore_proven_dump_sha256"] == "a" * 64
    assert baseline["deployment_window_backup_status"] == "PASS"
    assert baseline["deployment_window_backup_dump_sha256"] == "b" * 64
    assert datetime.fromisoformat(baseline["deployment_window_backup_created_utc"]) >= datetime.fromisoformat(
        baseline["writer_containment_confirmed_utc"]
    )
    assert "DEPLOYMENT_WINDOW_BACKUP=PASS" in result.stdout
    assert "PRODUCTION_DEPLOYMENT_TOOL_RESULT=PASS" in result.stdout


def test_writer_containment_polls_delayed_teardown_and_proves_task_state(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    state = data["state"]
    state.update({"containment_behavior": "delayed_teardown", "containment_teardown_after_polls": 3})  # type: ignore[union-attr]
    Path(data["state_path"]).write_text(json.dumps(state), encoding="utf-8")
    result = run_deployer(data, "-Execute", "-ConfirmDeployment", "-RestoreOwner", "fixture-dba")
    assert result.returncode == 0, result.stdout
    assert all(
        marker in result.stdout
        for marker in (
            "TASK_DISABLED=PASS",
            "ORIGINAL_LISTENER_TERMINATED=PASS",
            "GOVERNED_PORT_FREE=PASS",
            "NO_REPLACEMENT_LISTENER=PASS",
            "WRITER_CONTAINMENT=PASS",
        )
    )
    final_state = json.loads(Path(data["state_path"]).read_text(encoding="utf-8-sig"))
    assert final_state["containment_poll_count"] >= 3
    assert final_state["containment_stopped_process_ids"] == [42]
    assert final_state["containment_task_state_checks"] >= 2
    assert final_state["containment_task_disabled_proven"] is True
    assert final_state["containment_no_replacement_listener_proven"] is True
    baseline_line = next(line for line in result.stdout.splitlines() if line.startswith("BASELINE_STATE="))
    baseline = json.loads(Path(baseline_line.split("=", 1)[1]).read_text(encoding="utf-8"))
    assert baseline["writer_containment_task_disabled"] is True
    assert baseline["writer_containment_original_listener_terminated"] is True
    assert baseline["writer_containment_governed_port_free"] is True
    assert baseline["writer_containment_no_replacement_listener"] is True
    assert baseline["writer_containment_timeout_milliseconds"] == 500
    assert baseline["writer_containment_poll_milliseconds"] == 20
    assert baseline["writer_containment_quiet_milliseconds"] == 60


def test_writer_containment_timeout_fails_closed_before_backup_or_migration_and_restores_checkpoint_a(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    state = data["state"]
    state.update({"containment_behavior": "teardown_timeout", "containment_timeout_milliseconds": 220})  # type: ignore[union-attr]
    Path(data["state_path"]).write_text(json.dumps(state), encoding="utf-8")
    result = run_deployer(data, "-Execute", "-ConfirmDeployment", "-RestoreOwner", "fixture-dba")
    assert result.returncode != 0
    assert "writer/listener containment failed: teardown timeout" in result.stdout
    assert "ROLLBACK_CHECKPOINT=A" in result.stdout
    assert "PRIOR_APPLICATION_RESTORED=YES" in result.stdout
    assert "WRITER_CONTAINMENT=PASS" not in result.stdout
    assert "DEPLOYMENT_WINDOW_BACKUP=PASS" not in result.stdout
    final_state = json.loads(Path(data["state_path"]).read_text(encoding="utf-8-sig"))
    assert final_state["database_head"] == BEFORE
    assert final_state["task_enabled"] and final_state["listener_up"]
    assert final_state["containment_stopped_process_ids"] == [42]


def test_writer_containment_replacement_listener_fails_closed_without_killing_replacement(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    state = data["state"]
    state.update({"containment_behavior": "replacement_listener", "containment_replacement_pid": 84})  # type: ignore[union-attr]
    Path(data["state_path"]).write_text(json.dumps(state), encoding="utf-8")
    result = run_deployer(data, "-Execute", "-ConfirmDeployment", "-RestoreOwner", "fixture-dba")
    assert result.returncode != 0
    assert "replacement listener detected" in result.stdout
    assert "replacement_pid(s)=84" in result.stdout
    assert "replacement_not_terminated=YES" in result.stdout
    assert "ROLLBACK_CHECKPOINT=A" in result.stdout
    assert "DEPLOYMENT_WINDOW_BACKUP=PASS" not in result.stdout
    final_state = json.loads(Path(data["state_path"]).read_text(encoding="utf-8-sig"))
    assert final_state["database_head"] == BEFORE
    assert final_state["containment_replacement_observed"] is True
    assert final_state["containment_stopped_process_ids"] == [42]
    assert 84 not in final_state["containment_stopped_process_ids"]


def test_containment_order_keeps_backup_and_migration_behind_pass_and_rollback_uses_bounded_wait() -> None:
    deployer = (TOOLS / "Deploy-ForwarderV110Production.ps1").read_text(encoding="utf-8")
    containment = deployer.index("$writerContainment=Invoke-WriterContainment")
    containment_pass = deployer.index("Write-Output 'TASK_DISABLED=PASS'", containment)
    backup = deployer.index("Inject 'BACKUP'", containment_pass)
    migration = deployer.index("Inject 'MIGRATION'", backup)
    assert containment < containment_pass < backup < migration
    assert "Stop-Process -Id $ProcessId -Force" in deployer
    assert not re.search(r"Get-Process\s+(?:python|python\.exe).+Stop-Process", deployer, re.IGNORECASE)

    rollback = (TOOLS / "Invoke-ForwarderV110RollbackContainment.ps1").read_text(encoding="utf-8")
    assert "$WriterContainmentTimeoutMilliseconds=15000" in rollback
    assert "$WriterContainmentPollMilliseconds=250" in rollback
    assert "$WriterContainmentQuietMilliseconds=2000" in rollback
    assert "replacement_not_terminated=YES" in rollback
    assert "Stop-Process -Id $listenerPid -Force" in rollback


def test_failure_injection_before_migration_restores_checkpoint_a(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    result = run_deployer(
        data, "-Execute", "-ConfirmDeployment", "-RestoreOwner", "fixture-dba",
        "-FailAt", "BACKUP",
    )
    assert result.returncode != 0 and "ROLLBACK_CHECKPOINT=A" in result.stdout
    assert "WRITER_CONTAINMENT=PASS" in result.stdout
    assert "DEPLOYMENT_WINDOW_BACKUP=PASS" not in result.stdout
    state = json.loads(Path(data["state_path"]).read_text(encoding="utf-8-sig"))
    assert state["database_head"] == BEFORE
    assert state["task_enabled"] and state["listener_up"]
    assert Path(state["iis_path"]) == Path(data["state"]["iis_path"])
    assert Path(data["target"]).exists()
    version = subprocess.run(
        [str(WINDOWS_POWERSHELL), "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    assert version.returncode == 0 and version.stdout.strip().startswith("5.1"), version.stdout


def test_failure_injection_after_migration_contains_checkpoint_b_or_c(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    result = run_deployer(
        data, "-Execute", "-ConfirmDeployment", "-RestoreOwner", "fixture-dba",
        "-FailAt", "POST_MIGRATION",
    )
    assert result.returncode != 0 and "ROLLBACK_CHECKPOINT=B_OR_C" in result.stdout
    assert "DBA_RELEASE_OWNER_DECISION_REQUIRED=YES" in result.stdout
    state = json.loads(Path(data["state_path"]).read_text(encoding="utf-8-sig"))
    assert state["database_head"] == TARGET
    assert not state["task_enabled"] and not state["listener_up"]
    assert state["traffic_contained"]


def test_rollback_checkpoints_are_explicit(tmp_path: Path) -> None:
    data = fixture(tmp_path)
    target = Path(data["target"])
    target.mkdir()
    baseline = {"target_release_path": str(target), "prior_release_path": str(data["release_root"] / "prior"), "prior_iis_path": str(data["release_root"] / "prior" / "dist"), "prior_task_xml_path": str(tmp_path / "prior.xml")}
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    state = data["state"]
    state.update({"task_release": str(target), "listener_release": str(target), "iis_path": str(target / "dist")})
    Path(data["state_path"]).write_text(json.dumps(state), encoding="utf-8")
    base = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(TOOLS / "Invoke-ForwarderV110RollbackContainment.ps1"), "-BaselineStatePath", str(baseline_path), "-TargetReleasePath", str(target), "-FixtureStatePath", str(data["state_path"])]
    plan = subprocess.run(base + ["-Checkpoint", "B", "-PlanOnly"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert plan.returncode == 0 and "AUTOMATIC_DATABASE_DOWNGRADE=NO" in plan.stdout and "RECOVERY_DECISION=" in plan.stdout
    forbidden = subprocess.run(base + ["-Checkpoint", "B", "-ExecuteContainment", "-ConfirmContainment", "-RestorePriorApplication"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert forbidden.returncode != 0 and "prohibited after migration" in forbidden.stdout
