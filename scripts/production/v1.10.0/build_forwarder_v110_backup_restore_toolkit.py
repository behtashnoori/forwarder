"""Build the operator-mediated v1.10.0 backup and restore-proof toolkit."""
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
PACKAGE_SHA256 = "2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf"
BEFORE_HEAD = "20260921_shipment_evidence_ownership"
TARGET_HEAD = "20260926_fixed_shipment_responsible_expert"
TOOLKIT_REVISION = "r1"
TOOLKIT_NAME = f"Forwarder-v{VERSION}-Backup-Restore-Proof-Toolkit-{SOURCE_SHA[:12]}-{TOOLKIT_REVISION}"


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


def copy_file(source_root: Path, target_root: Path, source: str, destination: str) -> None:
    target = target_root / destination
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_root / source, target)


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
    args = parser.parse_args()
    package = args.package.resolve()
    output_root = args.output_root.resolve()
    tooling_root = args.tooling_root.resolve()
    if not package.is_file() or sha256(package) != PACKAGE_SHA256:
        raise RuntimeError("qualified Production package identity mismatch")
    with zipfile.ZipFile(package) as bundle:
        manifest = json.loads(bundle.read("release-manifest.json"))
    if (
        manifest.get("application_version") != VERSION
        or manifest.get("application_commit") != SOURCE_SHA
        or manifest.get("before_database_revision") != BEFORE_HEAD
        or manifest.get("database_revision") != TARGET_HEAD
        or manifest.get("reference_impact") != "NONE"
    ):
        raise RuntimeError("qualified Production package manifest mismatch")

    stamp = datetime.fromisoformat(manifest["build_date"]).astimezone(timezone.utc)
    output_root.mkdir(parents=True, exist_ok=True)
    root = output_root / TOOLKIT_NAME
    archive = output_root / f"{TOOLKIT_NAME}.zip"
    sidecar = Path(str(archive) + ".sha256")
    result_path = output_root / "Forwarder-v1.10.0-backup-restore-proof-toolkit-r1.build-result.json"
    if any(path.exists() for path in (root, archive, sidecar, result_path)):
        raise RuntimeError("refusing to overwrite an existing backup/restore-proof toolkit")
    root.mkdir()

    copy_file(tooling_root, root, "New-ForwarderV110PreDeploymentBackup.ps1", "server/New-ForwarderV110PreDeploymentBackup.ps1")
    copy_file(tooling_root, root, "Invoke-ForwarderV110ProductionRestoreProof.ps1", "restore/Invoke-ForwarderV110ProductionRestoreProof.ps1")
    copy_file(tooling_root, root, "Verify-ForwarderV110ProductionPackage.ps1", "restore/Verify-ForwarderV110ProductionPackage.ps1")
    for name in (
        "migration-compatibility-readonly.sql",
        "adr047-production-classifier.sql",
        "post-migration-assertions-readonly.sql",
    ):
        copy_file(tooling_root, root, f"sql/{name}", f"restore/sql/{name}")

    bundle_manifest = {
        "schema": "forwarder-v1.10.0-backup-restore-proof-toolkit-v1",
        "toolkit_revision": TOOLKIT_REVISION,
        "product_version": VERSION,
        "target_application_source": SOURCE_SHA,
        "qualified_production_package_sha256": PACKAGE_SHA256,
        "source_database_revision": BEFORE_HEAD,
        "target_database_revision": TARGET_HEAD,
        "live_readonly_preflight": "PASS",
        "fresh_backup_restore_proof": "PENDING_HUMAN_EXECUTION",
        "production_deployment_authorized": False,
        "production_accessed_during_build": False,
        "reference_impact": "NONE",
    }
    (root / "BUNDLE-MANIFEST.json").write_text(json.dumps(bundle_manifest, indent=2) + "\n", encoding="utf-8")
    (root / "README-FIRST.md").write_text(
        "# Forwarder v1.10.0 backup and restore-proof toolkit\n\n"
        "Copy only `server/New-ForwarderV110PreDeploymentBackup.ps1` to the protected Production preflight directory. "
        "A human runs it locally on SRV8756807400 to create the fresh custom-format dump and sanitized JSON. "
        "Keep the `restore` directory on the controlled laptop. Transfer the protected dump and sanitized JSON only through the approved operator channel, then run the restore-proof tool against an owned disposable PostgreSQL 18 instance. "
        "The restore tool removes only its generated disposable database and never connects to Production. This toolkit does not authorize validate-only, migration, or deployment on Production.\n",
        encoding="utf-8",
    )
    result = {
        "backup_restore_proof_toolkit": finish_bundle(root, archive, stamp),
        "production_package_sha256": PACKAGE_SHA256,
        "production_accessed": False,
        "production_deployment_performed": False,
    }
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
