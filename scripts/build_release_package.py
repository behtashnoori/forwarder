"""Build the immutable Forwarder 1.9.0 package from its exact annotated tag."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.9.0"
PREVIOUS_VERSION = "1.8.0"
TAG = "v1.9.0"
RELEASE_DATE = "20260809"
RELEASE_DIR = ROOT / f"release-v{VERSION}-{RELEASE_DATE}"
NPM_EXECUTABLE = "npm.cmd" if os.name == "nt" else "npm"
PRODUCTION_BASELINE_REVISION = "20260809_cargo_catalog_items"
DATABASE_REVISION = "20260818_immutable_fx_provenance"
UPGRADE_MIGRATIONS = [
    ("20260810_logistics_network", "backend/migrations/versions/20260810_logistics_network.py"),
    ("20260811_project_configuration", "backend/migrations/versions/20260811_project_configuration.py"),
    ("security_credential_remediation", "backend/migrations/versions/security_credential_remediation.py"),
    ("20260812_operational_execution", "backend/migrations/versions/20260812_operational_execution.py"),
    ("20260813_mdpm_readiness", "backend/migrations/versions/20260813_mdpm_document_readiness.py"),
    ("20260814_oip_situations", "backend/migrations/versions/20260814_oip_situations.py"),
    ("20260815_oip_threshold_policy", "backend/migrations/versions/20260815_oip_threshold_policy.py"),
    ("20260816_oip_projection_health", "backend/migrations/versions/20260816_oip_projection_health.py"),
    ("20260817_shipment_economics_core", "backend/migrations/versions/20260817_shipment_economics_core.py"),
    ("20260818_immutable_fx_provenance", "backend/migrations/versions/20260818_immutable_fx_provenance.py"),
]
UPGRADE_REVISIONS = [revision for revision, _ in UPGRADE_MIGRATIONS]


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def migration_path(revision: str) -> Path:
    relative = dict(UPGRADE_MIGRATIONS).get(revision)
    if relative is None:
        raise SystemExit(f"Unknown release migration {revision}")
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"Missing migration file for {revision}: {relative}")
    return path


def tag_status() -> str:
    probe = subprocess.run(
        ("git", "cat-file", "-t", TAG), cwd=ROOT, text=True, capture_output=True
    )
    if probe.returncode:
        return "absent"
    object_type = probe.stdout.strip()
    if object_type != "tag":
        return "not-annotated"
    return "matches-head" if run("git", "rev-list", "-n", "1", TAG) == run("git", "rev-parse", "HEAD") else "wrong-commit"


def validate_source() -> str:
    version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    if version != VERSION:
        raise SystemExit(f"package.json version mismatch: {version} != {VERSION}")
    heads = run(sys.executable, "-m", "alembic", "-c", "backend/migrations/alembic.ini", "heads")
    if heads.splitlines() != [f"{DATABASE_REVISION} (head)"]:
        raise SystemExit(f"Alembic head mismatch: {heads!r}")
    for revision in UPGRADE_REVISIONS:
        migration_path(revision)
    requirements = {
        line.strip()
        for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if "psycopg2-binary==2.9.11" not in requirements:
        raise SystemExit("Missing exact PostgreSQL runtime driver declaration")
    return tag_status()


def npm_version() -> str:
    return run(NPM_EXECUTABLE, "--version")


def build_frontend() -> None:
    subprocess.check_call((NPM_EXECUTABLE, "run", "build"), cwd=ROOT)


def promote_release_directory(staging: Path, final: Path) -> None:
    """Atomically publish a complete sibling directory without overwriting."""
    if staging.parent != final.parent:
        raise ValueError("Release staging and final directories must be siblings")
    if not staging.is_dir():
        raise FileNotFoundError(f"Release staging directory does not exist: {staging}")
    if final.exists():
        raise FileExistsError(f"Refusing to overwrite {final}")
    os.rename(staging, final)


def copy_file(source: Path, relative: Path, package_root: Path) -> None:
    target = package_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def build() -> None:
    status = validate_source()
    if status != "matches-head":
        raise SystemExit(f"{TAG} must be an annotated tag pointing at HEAD; status={status}")
    if run("git", "status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("Tracked working tree must be clean")
    if RELEASE_DIR.exists():
        raise SystemExit(f"Refusing to overwrite {RELEASE_DIR}")

    commit = run("git", "rev-parse", "HEAD")
    tree = run("git", "rev-parse", "HEAD^{tree}")
    tag_object = run("git", "rev-parse", f"{TAG}^{{tag}}")
    build_frontend()
    if not (ROOT / "dist" / "index.html").is_file():
        raise SystemExit("Tagged-source production build did not create dist/index.html")
    with tempfile.TemporaryDirectory(
        prefix=f".{RELEASE_DIR.name}-staging-", dir=ROOT
    ) as temporary:
        package_root = Path(temporary)
        for source in sorted((ROOT / "dist").rglob("*")):
            if source.is_file():
                copy_file(source, source.relative_to(ROOT / "dist"), package_root)

        root_files = [
            "manage.py", "requirements.txt", "Dockerfile", "docker-compose.production.yml",
            "DEPLOYMENT.md", "SMOKE-TEST.md", "ROLLBACK.md", "MIGRATION-PREFLIGHT.md",
            "VERIFY-PACKAGE.ps1", "VERIFY-SERVER.ps1", "verify_package_secrets.py",
        ]
        for name in root_files:
            copy_file(ROOT / name, Path(name), package_root)

        for name in run("git", "ls-files", "backend").splitlines():
            relative = Path(name)
            if "tests" in relative.parts or relative.suffix in {".pyc", ".map"}:
                continue
            copy_file(ROOT / relative, relative, package_root)

        index = (package_root / "index.html").read_text(encoding="utf-8")
        js = re.search(r'src="/([^\"]+\.js)"', index).group(1)
        css = re.search(r'href="/([^\"]+\.css)"', index).group(1)
        requirements_hash = sha256(ROOT / "requirements.txt")
        env_data = {
            "node": run("node", "--version"),
            "npm": npm_version(),
            "python": platform.python_version(),
            "package_lock_sha256": sha256(ROOT / "package-lock.json"),
            "requirements_sha256": requirements_hash,
        }
        env_canonical = json.dumps(env_data, sort_keys=True, separators=(",", ":")).encode()
        records = "".join(
            f"{path.relative_to(package_root).as_posix()}\0{sha256(path)}\n"
            for path in sorted(package_root.rglob("*")) if path.is_file()
        )
        package_hash = hashlib.sha256(records.encode()).hexdigest()
        migration_files = [
            {
                "revision": revision,
                "path": migration_path(revision).relative_to(ROOT).as_posix(),
                "sha256": sha256(migration_path(revision)),
            }
            for revision in UPGRADE_REVISIONS
        ]
        manifest = {
        "application_version": VERSION,
        "previous_version": PREVIOUS_VERSION,
        "release_name": "Integrated Operational Execution, MDPM, OIP, and Shipment Economics",
        "change_type": "MINOR",
        "git_commit": commit,
        "git_tree": tree,
        "git_tag": TAG,
        "git_tag_object": tag_object,
        "build_timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "package_hash": package_hash,
        "package_hash_definition": "SHA-256 of sorted '<relative-path>\\0<file-sha256>\\n' records for every package file except release-manifest.json",
        "requirements_sha256": requirements_hash,
        "frontend_entry_js": js,
        "frontend_entry_css": css,
        "frontend_entry_js_bytes": (package_root / js).stat().st_size,
        "frontend_entry_js_gzip_bytes": len(gzip.compress((package_root / js).read_bytes())),
        "frontend_entry_css_bytes": (package_root / css).stat().st_size,
        "frontend_entry_css_gzip_bytes": len(gzip.compress((package_root / css).read_bytes())),
        "backend_revision": commit,
        "database_revision": DATABASE_REVISION,
        "production_baseline_revision": PRODUCTION_BASELINE_REVISION,
        "previous_database_revision": PRODUCTION_BASELINE_REVISION,
        "upgrade_revisions": UPGRADE_REVISIONS,
        "migration_files": migration_files,
        "database_migration_included": True,
        "deployment_type": "backend-frontend-migration",
        "api_base": "same-origin",
        "environment_fingerprint": "sha256:" + hashlib.sha256(env_canonical).hexdigest(),
        "environment_fingerprint_definition": "SHA-256 of canonical secret-free JSON containing Python, Node, npm, package-lock SHA-256, and requirements SHA-256",
        "rollback_release": "release-v1.6.1-20260802",
        "rollback_strategy": "forward-fix before durable use; restore coordinated pre-deployment database and document-storage backups when schema rollback is required after durable MDPM/OIP/Economics/FX facts",
        "rollback_restore_required_from_revision": "20260817_shipment_economics_core",
        "milestone_type_catalog_filename": "backend/reference_data/milestone-types-v1.0.0.json",
        "milestone_type_catalog_version": "1.0.0",
        "milestone_type_catalog_sha256": sha256(ROOT / "backend/reference_data/milestone-types-v1.0.0.json"),
        "milestone_type_catalog_apply_status": "not applied",
        "production_seed_executed": False,
        "service_worker_included": False,
        "cache_policy": {
            "application_shell": "no-cache, no-store, must-revalidate",
            "pragma": "no-cache",
            "expires": "0",
            "hashed_assets": "public, max-age=31536000, immutable",
            "root_metadata": "public, max-age=0, must-revalidate",
            "api_headers_owned_by_backend": True,
        },
        "build_warnings": [
            "Browserslist data age and frontend chunk-size advisories are accepted non-blocking build warnings when reproduced by the final tagged build."
        ],
        "ui_version_display_status": "not visibly rendered",
        "known_limitations": [
            "Existing shipments receive no automatic Operational Execution, MDPM, OIP, or Economics rows.",
            "ACTUAL Shipment Economics remains incomplete when authoritative revenue or cost facts are unavailable.",
            "Reference Data and OIP policies/thresholds require separately authorized administrator initialization; no Seed runs during deployment.",
            "Database downgrade is fail-closed after durable Economics history and may require coordinated backup restore.",
        ],
        }
        (package_root / "release-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        promote_release_directory(package_root, RELEASE_DIR)
    print(RELEASE_DIR)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-source", action="store_true", help="validate 1.9 source metadata without creating a package")
    args = parser.parse_args()
    if args.check_source:
        status = validate_source()
        print(
            f"source=PASS version={VERSION} head={DATABASE_REVISION} "
            f"tag={TAG} tag_status={status} commit={run('git', 'rev-parse', 'HEAD')}"
        )
        return
    build()


if __name__ == "__main__":
    main()
