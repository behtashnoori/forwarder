"""Fail-closed package secret scan with one governed historical exception."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


LEGACY_PATH = Path("backend/migrations/versions/20240926_add_password_to_expert_user.py")
REMEDIATION_PATH = Path("backend/migrations/versions/security_credential_remediation.py")
LEGACY_FILE_SHA256 = "6ed41e455ed80e69922f201dbe2e8fd4e9db3e1c60f49bf64fb39a4451013554"
LEGACY_CREDENTIAL_SHA256 = "34a6c1a9600377c8dc05ea00380f406fb52e8104e921dc6bd5869bfdf1516164"
LEGACY_HASH_SHA256 = "bf651e7cafa9928e695fc3d7bbd6da97223d5f3cd82ec5db3d1d28fce7675230"
REMEDIATION_SHA256 = "72e19843e625054dac4f338ee7f54772bc2ebef332dabdab7417e50fab6635ee"
BASELINE = "20260809_cargo_catalog_items"
REMEDIATION = "security_credential_remediation"
SECRET_PATTERN = re.compile(
    rb"(?i)(BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|postgres(?:ql)?://[^\s:@]+:[^\s@]+@|(?:password|secret|api[_-]?key)\s*[=:]\s*[\"'][^\"']+[\"'])"
)
SKIPPED_SUFFIXES = {".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def historical_exception_is_valid(root: Path, manifest: dict) -> bool:
    legacy = root / LEGACY_PATH
    remediation = root / REMEDIATION_PATH
    revisions = manifest.get("upgrade_revisions", [])
    migration_hashes = {
        item.get("revision"): item.get("sha256")
        for item in manifest.get("migration_files", [])
        if isinstance(item, dict)
    }
    try:
        legacy_bytes = legacy.read_bytes()
        return (
            manifest.get("production_baseline_revision") == BASELINE
            and REMEDIATION in revisions
            and revisions.index(REMEDIATION) < revisions.index("20260812_operational_execution")
            and sha256(legacy) == LEGACY_FILE_SHA256
            and hashlib.sha256(b"expert" + b"123").hexdigest()
            == LEGACY_CREDENTIAL_SHA256
            and LEGACY_HASH_SHA256
            in {
                hashlib.sha256(value).hexdigest()
                for value in re.findall(
                    rb"\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}", legacy_bytes
                )
            }
            and remediation.is_file()
            and sha256(remediation) == REMEDIATION_SHA256
            and migration_hashes.get(REMEDIATION) == REMEDIATION_SHA256
        )
    except (OSError, ValueError):
        return False


def findings(root: Path) -> list[str]:
    manifest = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
    exception_valid = historical_exception_is_valid(root, manifest)
    problems: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.suffix.lower() in SKIPPED_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if not SECRET_PATTERN.search(path.read_bytes()):
            continue
        if relative == LEGACY_PATH and exception_valid:
            continue
        problems.append(relative.as_posix())
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    problems = findings(args.root.resolve())
    for problem in problems:
        print(f"package-secret-policy=FAIL path={problem}")
    if problems:
        return 1
    print("package-secret-policy=PASS historical_exception=exact-remediated-migration-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
