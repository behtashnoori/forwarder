"""Build a reproducible Forwarder v1.10.0 Production package from frozen source."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


VERSION = "1.10.0"
ACCEPTED_BASE = "a742628293359379cb476b782a2fe27e61a8db1f"
SOURCE_SHA = "e36ee7cee157657c97dc42a539eaf1909f510a33"
BEFORE_HEAD = "20260921_shipment_evidence_ownership"
TARGET_HEAD = "20260926_fixed_shipment_responsible_expert"
RUNTIME_NAME = "Forwarder-Windows-Runtime-S7-RC-a257669-r4.zip"
RUNTIME_SHA256 = "f4a8f108aa89a78d7986f01fb8f6aa8af5e2d35e00617a8453eb1f15df945070"
RUNTIME_ID = "Forwarder-Windows-Runtime-S7-RC-a257669-r4"
PACKAGE_BASENAME = f"Forwarder-Production-v{VERSION}-{SOURCE_SHA[:12]}"
HISTORICAL_SECURITY_REMEDIATION = {
    "policy": "exact-credential-migration-remediated-in-ancestry-v1",
    "legacy_revision": "20240926_add_password_to_expert_user",
    "legacy_file_sha256": "6ed41e455ed80e69922f201dbe2e8fd4e9db3e1c60f49bf64fb39a4451013554",
    "remediation_revision": "security_credential_remediation",
    "remediation_sha256": "72e19843e625054dac4f338ee7f54772bc2ebef332dabdab7417e50fab6635ee",
}
TOOLING_FILES = (
    "Deploy-ForwarderV110Production.ps1",
    "Invoke-ForwarderV110RollbackContainment.ps1",
    "New-ForwarderV110PreDeploymentBackup.ps1",
    "Verify-ForwarderV110PostDeploy.ps1",
    "Verify-ForwarderV110ProductionPackage.ps1",
    "sql/adr047-production-classifier.sql",
    "sql/migration-compatibility-readonly.sql",
    "sql/post-migration-assertions-readonly.sql",
)


def run(args: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> str:
    return subprocess.run(args, cwd=cwd, env=env, check=True, text=True, capture_output=True).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def revision_heads(versions: Path) -> list[str]:
    graph: dict[str, tuple[str, ...]] = {}
    for path in versions.glob("*.py"):
        values: dict[str, object] = {}
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                    values[target.id] = ast.literal_eval(node.value)
        revision, parent = values.get("revision"), values.get("down_revision")
        if isinstance(revision, str):
            graph[revision] = () if parent is None else ((parent,) if isinstance(parent, str) else tuple(parent))
    referenced = {str(parent) for parents in graph.values() for parent in parents}
    return sorted(set(graph) - referenced)


def verify_runtime_tree(runtime: Path, manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("artifact") != RUNTIME_NAME or manifest.get("artifact_sha256") != RUNTIME_SHA256 or manifest.get("runtime_id") != RUNTIME_ID:
        raise RuntimeError("approved runtime manifest identity mismatch")
    expected = {item["path"]: (item["bytes"], item["sha256"]) for item in manifest.get("files", [])}
    actual = {path.relative_to(runtime).as_posix(): (path.stat().st_size, sha256(path)) for path in runtime.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError("approved runtime tree mismatch")


def write_deterministic_zip(source: Path, target: Path, stamp: datetime) -> None:
    stamp = stamp.astimezone(timezone.utc)
    year = max(1980, min(2107, stamp.year))
    fixed = (year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second - stamp.second % 2)
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(
            (item for item in source.rglob("*") if item.is_file()),
            key=lambda item: item.relative_to(source).as_posix(),
        ):
            info = zipfile.ZipInfo(path.relative_to(source).as_posix(), date_time=fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            bundle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def verify_zip(zip_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="forwarder-prod-verify-") as temporary:
        extracted = Path(temporary) / "package"
        with zipfile.ZipFile(zip_path) as bundle:
            names = bundle.namelist()
            if len(names) != len(set(names)) or any(name.startswith(("/", "\\")) or ".." in Path(name).parts for name in names):
                raise RuntimeError("unsafe archive layout")
            bundle.extractall(extracted)
        checksums = {}
        for line in (extracted / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            expected, relative = line.split("  ", 1)
            checksums[relative] = expected
            target = extracted / relative
            if not target.is_file() or sha256(target) != expected:
                raise RuntimeError(f"extracted checksum mismatch: {relative}")
        actual = {path.relative_to(extracted).as_posix() for path in extracted.rglob("*") if path.is_file() and path.name != "SHA256SUMS.txt"}
        if actual != set(checksums):
            raise RuntimeError("extracted package inventory mismatch")
        verify_runtime_tree(extracted / "runtime", extracted / "runtime-manifest.json")
        shutil.rmtree(extracted / "runtime")
        subprocess.run([sys.executable, str(extracted / "verify_package_secrets.py"), str(extracted)], cwd=extracted, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True, help="clean detached worktree at the frozen application source")
    parser.add_argument("--tooling-root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    source_root, tooling_root, output_root = args.source_root.resolve(), args.tooling_root.resolve(), args.output_root.resolve()
    if run(["git", "rev-parse", "HEAD"], source_root) != SOURCE_SHA:
        raise RuntimeError("source worktree is not the frozen application source")
    if run(["git", "rev-parse", "--abbrev-ref", "HEAD"], source_root) != "HEAD":
        raise RuntimeError("source worktree must be detached")
    if run(["git", "status", "--porcelain", "--untracked-files=all"], source_root):
        raise RuntimeError("source worktree must be clean")
    if run(["git", "merge-base", ACCEPTED_BASE, SOURCE_SHA], source_root) != ACCEPTED_BASE:
        raise RuntimeError("frozen source does not descend from the accepted Product baseline")
    for relative in TOOLING_FILES:
        if not (tooling_root / relative).is_file():
            raise RuntimeError(f"required Production tooling missing: {relative}")

    package_dir = output_root / PACKAGE_BASENAME
    zip_path = output_root / f"{PACKAGE_BASENAME}.zip"
    sidecar = Path(str(zip_path) + ".sha256")
    result_path = output_root / f"{PACKAGE_BASENAME}.build-result.json"
    if any(path.exists() for path in (package_dir, zip_path, sidecar, result_path)):
        raise RuntimeError("refusing to overwrite existing Production package output")

    source_timestamp = datetime.fromisoformat(run(["git", "show", "-s", "--format=%cI", SOURCE_SHA], source_root)).astimezone(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="forwarder-prod-source-") as temporary:
        archive = Path(temporary) / "source.zip"
        with archive.open("wb") as stream:
            subprocess.run(["git", "archive", "--format=zip", SOURCE_SHA], cwd=source_root, check=True, stdout=stream)
        source = Path(temporary) / "source"; source.mkdir()
        with zipfile.ZipFile(archive) as bundle: bundle.extractall(source)

        package_meta = json.loads((source / "package.json").read_text(encoding="utf-8"))
        backend_tree = ast.parse((source / "backend/__init__.py").read_text(encoding="utf-8"))
        backend_version = next(ast.literal_eval(node.value) for node in backend_tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets))
        if package_meta["version"] != VERSION or backend_version != VERSION:
            raise RuntimeError("Product version sources are inconsistent")
        if revision_heads(source / "backend/migrations/versions") != [TARGET_HEAD]:
            raise RuntimeError("migration graph does not have the one expected head")

        subprocess.run(["npm.cmd" if os.name == "nt" else "npm", "ci", "--no-audit", "--no-fund"], cwd=source_root, check=True)
        build_env = os.environ.copy(); build_env["VITE_API_URL"] = "__FORWARDER_SAME_ORIGIN__"
        subprocess.run(["npm.cmd" if os.name == "nt" else "npm", "run", "build"], cwd=source_root, env=build_env, check=True)

        package_dir.mkdir(parents=True)
        application_inventory: list[dict[str, object]] = []
        for name in ("backend", "contracts"):
            shutil.copytree(source / name, package_dir / name, ignore=shutil.ignore_patterns("__pycache__", "tests", "Dockerfile", "docker-compose*"))
        shutil.copytree(source_root / "dist", package_dir / "dist")
        for name in ("manage.py", "requirements-release.txt", "package.json", "verify_package_secrets.py"):
            shutil.copy2(source / name, package_dir / name)
        for path in sorted(
            (item for item in package_dir.rglob("*") if item.is_file()),
            key=lambda item: item.relative_to(package_dir).as_posix(),
        ):
            application_inventory.append({"path": path.relative_to(package_dir).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path), "source_commit": SOURCE_SHA, "classification": "built_frontend" if path.is_relative_to(package_dir / "dist") else "source_file"})

        runtime_archive = source_root / "release-candidates" / RUNTIME_NAME
        runtime_manifest = Path(str(runtime_archive) + ".manifest.json")
        if not runtime_archive.is_file() or sha256(runtime_archive) != RUNTIME_SHA256 or not runtime_manifest.is_file():
            raise RuntimeError("approved Windows runtime is unavailable or changed")
        with zipfile.ZipFile(runtime_archive) as bundle: bundle.extractall(package_dir / "runtime")
        verify_runtime_tree(package_dir / "runtime", runtime_manifest)
        shutil.copy2(runtime_manifest, package_dir / "runtime-manifest.json")

        tools_dir = package_dir / "production-tooling"; tools_dir.mkdir()
        for relative in TOOLING_FILES:
            destination = tools_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tooling_root / relative, destination)
        shutil.copy2(tooling_root / "Verify-ForwarderV110ProductionPackage.ps1", package_dir / "VERIFY-PRODUCTION-PACKAGE.ps1")

        manifest = {
            "schema": "forwarder-production-release-manifest-v1", "product_name": "Forwarder", "release_stage": "Production",
            "application_version": VERSION, "frontend_version": VERSION, "backend_version": VERSION,
            "accepted_product_base_sha": ACCEPTED_BASE, "release_source_sha": SOURCE_SHA, "application_commit": SOURCE_SHA,
            "before_database_revision": BEFORE_HEAD, "database_revision": TARGET_HEAD, "alembic_head_count": 1,
            "build_date": source_timestamp.isoformat(), "release_id": f"Forwarder-Production-v{VERSION}", "package_filename": zip_path.name,
            "outer_zip_sha256_contract": f"sidecar:{zip_path.name}.sha256", "runtime_entrypoint": r"C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py",
            "runtime_id": RUNTIME_ID, "runtime_sha256": RUNTIME_SHA256, "backend_listener_contract": "127.0.0.1:5101",
            "external_environment_path": r"C:\1-webapp\forwarder-runtime\production.env", "auto_migrate_on_startup": False,
            "mutable_data_packaged": False, "historical_security_remediation": HISTORICAL_SECURITY_REMEDIATION,
            "reference_impact": "NONE", "production_accessed": False,
        }
        (package_dir / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (package_dir / "APPLICATION-INVENTORY.json").write_text(json.dumps(application_inventory, indent=2) + "\n", encoding="utf-8")
        (package_dir / "PRODUCTION-README.md").write_text(
            f"# Forwarder Production v{VERSION}\n\nThis immutable package was built from `{SOURCE_SHA}` for database target `{TARGET_HEAD}`. It is not self-authorizing. Verify it, run the read-only collector, obtain GO, run validate-only, obtain explicit deployment authorization, create and verify the fresh backup, and only then use the Production deployer. Do not use any UAT launcher.\n",
            encoding="utf-8",
        )

        inventory_excluded = {"PACKAGE-INVENTORY.json", "SHA256SUMS.txt"}
        payload = [{"path": path.relative_to(package_dir).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in sorted((item for item in package_dir.rglob("*") if item.is_file()), key=lambda item: item.relative_to(package_dir).as_posix()) if path.relative_to(package_dir).as_posix() not in inventory_excluded]
        (package_dir / "PACKAGE-INVENTORY.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        files = sorted((item for item in package_dir.rglob("*") if item.is_file()), key=lambda item: item.relative_to(package_dir).as_posix())
        (package_dir / "SHA256SUMS.txt").write_text("\n".join(f"{sha256(path)}  {path.relative_to(package_dir).as_posix()}" for path in files) + "\n", encoding="utf-8")

        output_root.mkdir(parents=True, exist_ok=True)
        write_deterministic_zip(package_dir, zip_path, source_timestamp)
        sidecar.write_text(f"{sha256(zip_path)}  {zip_path.name}\n", encoding="ascii")

    verify_zip(zip_path)
    result = {"release_id": f"Forwarder-Production-v{VERSION}", "release_stage": "Production", "release_source_sha": SOURCE_SHA,
              "database_head": TARGET_HEAD, "package_path": str(zip_path), "package_sha256": sha256(zip_path),
              "package_size": zip_path.stat().st_size, "package_directory": str(package_dir), "deterministic_timestamp": source_timestamp.isoformat()}
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
