"""Build the distinct operator transfer bundles for Forwarder v1.10.0."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


VERSION = "1.10.0"
SOURCE_SHA = "e36ee7cee157657c97dc42a539eaf1909f510a33"
BEFORE_HEAD = "20260921_shipment_evidence_ownership"
TARGET_HEAD = "20260926_fixed_shipment_responsible_expert"
READ_ONLY_REVISION = "r2"
READ_ONLY_NAME = f"Forwarder-v{VERSION}-Read-Only-Preflight-Bundle-{SOURCE_SHA[:12]}-{READ_ONLY_REVISION}"
DEPLOYMENT_NAME = f"Forwarder-v{VERSION}-Production-Deployment-Bundle-{SOURCE_SHA[:12]}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sorted_files(root: Path) -> list[Path]:
    return sorted(
        (item for item in root.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(root).as_posix(),
    )


def copy_relative(source_root: Path, target_root: Path, relative: str) -> None:
    destination = target_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_root / relative, destination)


def finish_bundle(root: Path, archive: Path, stamp: datetime) -> dict[str, object]:
    payload = [
        {"path": item.relative_to(root).as_posix(), "bytes": item.stat().st_size, "sha256": sha256(item)}
        for item in sorted_files(root)
        if item.name not in {"BUNDLE-INVENTORY.json", "SHA256SUMS.txt"}
    ]
    (root / "BUNDLE-INVENTORY.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    files = sorted_files(root)
    (root / "SHA256SUMS.txt").write_text(
        "\n".join(f"{sha256(item)}  {item.relative_to(root).as_posix()}" for item in files) + "\n",
        encoding="utf-8",
    )
    fixed = stamp.astimezone(timezone.utc)
    date_time = (fixed.year, fixed.month, fixed.day, fixed.hour, fixed.minute, fixed.second - fixed.second % 2)
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for item in sorted_files(root):
            info = zipfile.ZipInfo(item.relative_to(root).as_posix(), date_time=date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            bundle.writestr(info, item.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = sha256(archive)
    Path(str(archive) + ".sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    return {"path": str(archive), "sha256": digest, "bytes": archive.stat().st_size}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--tooling-root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument(
        "--read-only-only",
        action="store_true",
        help="Build only the corrected read-only preflight bundle; leave deployment material untouched.",
    )
    args = parser.parse_args()
    package = args.package.resolve()
    output_root = args.output_root.resolve()
    tooling_root = args.tooling_root.resolve()
    sidecar = Path(str(package) + ".sha256")
    if not package.is_file() or not sidecar.is_file():
        raise RuntimeError("qualified Production package and SHA256 sidecar are required")
    outer_sha = sha256(package)
    parts = sidecar.read_text(encoding="ascii").strip().split("  ", 1)
    if parts != [outer_sha, package.name]:
        raise RuntimeError("Production package SHA256 sidecar mismatch")
    with zipfile.ZipFile(package) as bundle:
        manifest = json.loads(bundle.read("release-manifest.json"))
    if (
        manifest.get("release_stage") != "Production"
        or manifest.get("application_version") != VERSION
        or manifest.get("application_commit") != SOURCE_SHA
        or manifest.get("before_database_revision") != BEFORE_HEAD
        or manifest.get("database_revision") != TARGET_HEAD
        or manifest.get("reference_impact") != "NONE"
    ):
        raise RuntimeError("Production package identity mismatch")
    stamp = datetime.fromisoformat(manifest["build_date"]).astimezone(timezone.utc)
    output_root.mkdir(parents=True, exist_ok=True)
    read_only_root = output_root / READ_ONLY_NAME
    deployment_root = output_root / DEPLOYMENT_NAME
    read_only_zip = output_root / f"{READ_ONLY_NAME}.zip"
    deployment_zip = output_root / f"{DEPLOYMENT_NAME}.zip"
    outputs = [read_only_root, read_only_zip, Path(str(read_only_zip)+".sha256")]
    if not args.read_only_only:
        outputs.extend((deployment_root, deployment_zip, Path(str(deployment_zip)+".sha256")))
    if any(item.exists() for item in outputs):
        raise RuntimeError("refusing to overwrite an existing transfer bundle")

    read_only_root.mkdir()
    for relative in (
        "Collect-ForwarderV110ProductionReadOnly.ps1",
        "Invoke-ForwarderV110ReadOnlySql.py",
        "legacy-production-witness.json",
        "sql/adr047-production-classifier.sql",
        "sql/migration-compatibility-readonly.sql",
    ):
        copy_relative(tooling_root, read_only_root, relative)
    read_only_manifest = {
        "schema": "forwarder-v1.10.0-read-only-preflight-bundle-v2",
        "collector_revision": READ_ONLY_REVISION,
        "purpose": "read_only_production_fact_collection",
        "product_version": VERSION,
        "application_source_sha": SOURCE_SHA,
        "expected_current_database_revision": BEFORE_HEAD,
        "target_database_revision": TARGET_HEAD,
        "production_mutation_authorized": False,
        "production_accessed_during_build": False,
        "reference_impact": "NONE",
    }
    (read_only_root / "BUNDLE-MANIFEST.json").write_text(json.dumps(read_only_manifest, indent=2)+"\n", encoding="utf-8")
    (read_only_root / "README-FIRST.md").write_text(
        "# Forwarder v1.10.0 read-only Production preflight\n\n"
        "Copy this directory to `C:\\1-webapp\\forwarder-production-preflight\\v1.10.0-20260921` on the Production server. Run only `Collect-ForwarderV110ProductionReadOnly.ps1` locally on that server. The collector makes no Production mutation and writes one sanitized JSON result beside the script. Copy that JSON back for GO/NO-GO review. This bundle does not authorize deployment.\n",
        encoding="utf-8",
    )

    result = {
        "read_only_preflight_bundle": finish_bundle(read_only_root, read_only_zip, stamp),
        "production_package_sha256": outer_sha,
        "production_accessed": False,
    }
    if not args.read_only_only:
        deployment_root.mkdir()
        shutil.copy2(package, deployment_root / package.name)
        shutil.copy2(sidecar, deployment_root / sidecar.name)
        for relative in (
            "Deploy-ForwarderV110Production.ps1",
            "Invoke-ForwarderV110RollbackContainment.ps1",
            "New-ForwarderV110PreDeploymentBackup.ps1",
            "Verify-ForwarderV110PostDeploy.ps1",
            "Verify-ForwarderV110ProductionPackage.ps1",
            "sql/post-migration-assertions-readonly.sql",
        ):
            copy_relative(tooling_root, deployment_root, relative)
        deployment_manifest = {
            "schema": "forwarder-v1.10.0-production-deployment-bundle-v1",
            "purpose": "operator_mediated_production_deployment_after_separate_go",
            "product_version": VERSION,
            "application_source_sha": SOURCE_SHA,
            "before_database_revision": BEFORE_HEAD,
            "target_database_revision": TARGET_HEAD,
            "production_package": package.name,
            "production_package_sha256": outer_sha,
            "production_accessed_during_build": False,
            "reference_impact": "NONE",
        }
        (deployment_root / "BUNDLE-MANIFEST.json").write_text(json.dumps(deployment_manifest, indent=2)+"\n", encoding="utf-8")
        (deployment_root / "README-FIRST.md").write_text(
            "# Forwarder v1.10.0 Production deployment bundle\n\n"
            "Keep this bundle on the laptop until the returned live read-only preflight has been reviewed and a separate GO has been issued. On the server, verify the package, run the deployer with `-ValidateOnly`, obtain explicit human authorization, and only then use `-Execute -ConfirmDeployment` during the maintenance window. No force or safety-bypass mode exists.\n",
            encoding="utf-8",
        )
        result["production_deployment_bundle"] = finish_bundle(deployment_root, deployment_zip, stamp)

    result_path = output_root / (
        "Forwarder-v1.10.0-read-only-preflight-r2.build-result.json"
        if args.read_only_only
        else "Forwarder-v1.10.0-transfer-bundles.build-result.json"
    )
    if result_path.exists():
        raise RuntimeError("refusing to overwrite transfer bundle build result")
    result_path.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
