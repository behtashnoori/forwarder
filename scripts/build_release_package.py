"""Build the immutable Forwarder deployment package from tracked release inputs."""

from __future__ import annotations

import gzip
import hashlib
import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.8.0"
TAG = "v1.8.0"
RELEASE_DIR = ROOT / "release-v1.8.0-20260804"


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_file(source: Path, relative: Path) -> None:
    target = RELEASE_DIR / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main() -> None:
    commit = run("git", "rev-parse", "HEAD")
    if run("git", "rev-list", "-n", "1", TAG) != commit:
        raise SystemExit(f"{TAG} does not point to HEAD")
    if RELEASE_DIR.exists():
        raise SystemExit(f"Refusing to overwrite {RELEASE_DIR}")
    if json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"] != VERSION:
        raise SystemExit("package.json version mismatch")

    RELEASE_DIR.mkdir()
    for source in sorted((ROOT / "dist").rglob("*")):
        if source.is_file():
            copy_file(source, source.relative_to(ROOT / "dist"))

    root_files = [
        "manage.py", "requirements.txt", "Dockerfile", "docker-compose.production.yml",
        "DEPLOYMENT.md", "SMOKE-TEST.md", "ROLLBACK.md",
        "MIGRATION-PREFLIGHT.md", "VERIFY-PACKAGE.ps1", "VERIFY-SERVER.ps1",
    ]
    for name in root_files:
        copy_file(ROOT / name, Path(name))

    tracked_backend = run("git", "ls-files", "backend").splitlines()
    for name in tracked_backend:
        relative = Path(name)
        if "tests" in relative.parts or relative.suffix in {".pyc", ".map"}:
            continue
        copy_file(ROOT / relative, relative)

    index = (RELEASE_DIR / "index.html").read_text(encoding="utf-8")
    import re
    js = re.search(r'src="/([^\"]+\.js)"', index).group(1)
    css = re.search(r'href="/([^\"]+\.css)"', index).group(1)
    env_data = {
        "node": run("node", "--version"), "npm": run("npm", "--version"),
        "python": platform.python_version(), "package_lock_sha256": sha256(ROOT / "package-lock.json"),
        "requirements_sha256": sha256(ROOT / "requirements.txt"),
    }
    env_canonical = json.dumps(env_data, sort_keys=True, separators=(",", ":")).encode()

    records = "".join(
        f"{path.relative_to(RELEASE_DIR).as_posix()}\0{sha256(path)}\n"
        for path in sorted(RELEASE_DIR.rglob("*")) if path.is_file()
    )
    package_hash = hashlib.sha256(records.encode()).hexdigest()
    manifest = {
        "application_version": VERSION, "previous_version": "1.7.0",
        "release_name": "Project Configuration Foundation", "change_type": "MINOR",
        "git_commit": commit, "git_tag": TAG,
        "build_timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "package_hash": package_hash,
        "package_hash_definition": "SHA-256 of UTF-8 concatenation of sorted records '<relative-path-with-forward-slashes>\\0<lowercase-file-sha256>\\n' for every package file except release-manifest.json",
        "frontend_entry_js": js, "frontend_entry_css": css,
        "frontend_entry_js_bytes": (RELEASE_DIR / js).stat().st_size,
        "frontend_entry_js_gzip_bytes": len(gzip.compress((RELEASE_DIR / js).read_bytes())),
        "frontend_entry_css_bytes": (RELEASE_DIR / css).stat().st_size,
        "frontend_entry_css_gzip_bytes": len(gzip.compress((RELEASE_DIR / css).read_bytes())),
        "backend_revision": commit, "database_revision": "20260811_project_configuration",
        "previous_database_revision": "20260810_logistics_network", "database_migration_included": True,
        "deployment_type": "backend-frontend-migration", "api_base": "http://server.logisticmarket.ir",
        "environment_fingerprint": "sha256:" + hashlib.sha256(env_canonical).hexdigest(),
        "environment_fingerprint_definition": "SHA-256 of canonical secret-free JSON containing Python, Node, npm, package-lock SHA-256, and requirements SHA-256",
        "rollback_release": "release-v1.7.0-20260803",
        "milestone_type_catalog_filename": "backend/reference_data/milestone-types-v1.0.0.json",
        "milestone_type_catalog_version": "1.0.0",
        "milestone_type_catalog_sha256": sha256(ROOT / "backend/reference_data/milestone-types-v1.0.0.json"),
        "milestone_type_catalog_apply_status": "not applied",
        "production_seed_executed": False, "service_worker_included": False,
        "cache_policy": {"application_shell": "no-cache, no-store, must-revalidate", "pragma": "no-cache", "expires": "0", "hashed_assets": "public, max-age=31536000, immutable", "root_metadata": "public, max-age=0, must-revalidate", "api_headers_owned_by_backend": True},
        "build_warnings": ["Browserslist caniuse-lite data is 14 months old.", "The main JavaScript chunk exceeds Vite's 500 kB warning threshold."],
        "ui_version_display_status": "not visibly rendered",
        "known_limitations": ["Version 1.8.0 is embedded in the frontend build but is not visibly rendered in the UI.", "Application rollback normally retains the additive 1.8.0 schema; database downgrade requires separate authorization and data-retention assessment after Production use.", "MilestoneType catalog rollback or deactivation is separate governed work if it is later applied."]
    }
    (RELEASE_DIR / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(RELEASE_DIR)


if __name__ == "__main__":
    main()
