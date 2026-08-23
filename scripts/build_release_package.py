"""Build a governed Forwarder release from one explicit authorized commit."""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_HEAD = "20260906_global_logistics_point_materialization"
BASELINE = Path(
    "backend/reference_data/global-logistics-points-china-iran-v1.0.0-approved-baseline.json"
)
BASELINE_VERSION = "china-iran-global-logistics-points-1.0.0-approved-baseline"
BASELINE_CHECKSUM = (
    "sha256:08a7ca1fb17ae79964930cd47c019261b6952aa9542b2fc48ee09c7564690c7c"
)
HISTORICAL_SECURITY_REMEDIATION = {
    "policy": "exact-credential-migration-remediated-in-ancestry-v1",
    "legacy_revision": "20240926_add_password_to_expert_user",
    "legacy_file_sha256": "6ed41e455ed80e69922f201dbe2e8fd4e9db3e1c60f49bf64fb39a4451013554",
    "remediation_revision": "security_credential_remediation",
    "remediation_sha256": "72e19843e625054dac4f338ee7f54772bc2ebef332dabdab7417e50fab6635ee",
}
ROOT_FILES = ("manage.py", "requirements.txt", "requirements-release.txt")
OPTIONAL_FILES = (
    "Dockerfile",
    "docker-compose.production.yml",
    "DEPLOYMENT.md",
    "SMOKE-TEST.md",
    "ROLLBACK.md",
    "MIGRATION-PREFLIGHT.md",
    "VERIFY-PACKAGE.ps1",
    "VERIFY-SERVER.ps1",
    "verify_package_secrets.py",
)


class BuildError(RuntimeError):
    pass


def run(args, cwd, *, env=None, output=True):
    p = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=output)
    if p.returncode:
        lines = (p.stderr or p.stdout or "").strip().splitlines()
        raise BuildError(
            f"command failed ({p.returncode}): {' '.join(map(str, args))}"
            + (f"; {lines[-1]}" if lines else "")
        )
    return (p.stdout or "").strip()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(payload):
    unsigned = {k: v for k, v in payload.items() if k != "checksum"}
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
    )


def validate_source(source, commit):
    if run(["git", "rev-parse", "HEAD"], source) != commit:
        raise BuildError("source HEAD does not equal authorized commit")
    if run(["git", "status", "--porcelain"], source):
        raise BuildError("isolated source is dirty")
    heads = run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "backend/migrations/alembic.ini",
            "heads",
        ],
        source,
    ).splitlines()
    if heads != [EXPECTED_HEAD + " (head)"]:
        raise BuildError(f"unexpected Alembic heads: {heads}")
    try:
        package = json.loads((source / BASELINE).read_text(encoding="utf-8"))
    except Exception as exc:
        raise BuildError("baseline is not strict UTF-8 JSON") from exc
    if (
        package.get("catalog_version") != BASELINE_VERSION
        or package.get("checksum") != BASELINE_CHECKSUM
        or canonical(package) != BASELINE_CHECKSUM
        or package.get("approved_subset_count") != 9
        or len(package.get("approved_global_logistics_points", [])) != 9
    ):
        raise BuildError("baseline identity/checksum/count mismatch")
    for name in ROOT_FILES:
        if not (source / name).is_file():
            raise BuildError(f"required source file missing: {name}")
    return package


def gates(source):
    npm = "npm.cmd" if os.name == "nt" else "npm"
    with tempfile.TemporaryDirectory(prefix="forwarder-release-venv-") as raw:
        venv = Path(raw)
        run([sys.executable, "-m", "venv", str(venv)], source)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "-r",
                "requirements.txt",
                "-r",
                "requirements-release.txt",
            ],
            source,
            output=False,
        )
        run([str(python), "scripts/scan_repository_secrets.py", "current"], source)
        run([npm, "ci"], source, output=False)
        run(
            [
                str(python),
                "-m",
                "ruff",
                "check",
                "backend/global_logistics_point_catalog.py",
                "backend/global_logistics_point_catalog_cli.py",
                "backend/tests/test_global_logistics_point_catalog_importer.py",
                "scripts/build_release_package.py",
                "scripts/verify_release_artifact.py",
                "scripts/certify_global_logistics_point_importer_postgres.py",
                "scripts/tests/test_release_package_builder.py",
            ],
            source,
            output=False,
        )
        run([str(python), "-m", "pytest"], source, output=False)
        run([npm, "run", "test:frontend"], source, output=False)
        run([npm, "exec", "tsc", "--", "--noEmit"], source, output=False)
        run([npm, "run", "lint"], source, output=False)
        env = os.environ.copy()
        env["VITE_API_URL"] = "__FORWARDER_SAME_ORIGIN__"
        run([npm, "run", "build"], source, env=env, output=False)
        run([str(python), "-m", "compileall", "-q", "backend"], source)
        run([str(python), "scripts/check_architecture_governance.py"], source)
        run(["git", "diff", "--check"], source)
        return {
            "python": run([str(python), "--version"], source),
            "node": run(["node", "--version"], source),
            "npm": run([npm, "--version"], source),
        }


def copy(source, relative, target):
    out = target / relative
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, out)


def assemble(source, target):
    for name in ROOT_FILES + OPTIONAL_FILES:
        if (source / name).is_file():
            copy(source / name, Path(name), target)
    for name in run(["git", "ls-files", "backend", "scripts"], source).splitlines():
        relative = Path(name)
        if "tests" in relative.parts or relative.suffix in {".pyc", ".map"}:
            continue
        copy(source / relative, relative, target)
    dist = source / "dist"
    if not (dist / "index.html").is_file():
        raise BuildError("fresh dist/index.html is missing")
    for path in sorted(dist.rglob("*")):
        if path.is_file():
            copy(path, Path("dist") / path.relative_to(dist), target)


def verify_tree(target):
    required = [
        Path("backend"),
        Path("backend/migrations"),
        Path("backend/reference_data"),
        Path("dist/index.html"),
        *map(Path, ROOT_FILES),
        BASELINE,
        Path("backend/global_logistics_point_catalog.py"),
        Path("backend/global_logistics_point_catalog_cli.py"),
    ]
    missing = [x.as_posix() for x in required if not (target / x).exists()]
    if missing:
        raise BuildError(f"artifact structure missing: {missing}")


def build(repo, commit, output, label, *, skip_gates=False):
    repo, output = repo.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", label):
        raise BuildError("unsafe release label")
    if (
        run(["git", "rev-parse", "--show-toplevel"], repo).replace("\\", "/").lower()
        != repo.as_posix().lower()
    ):
        raise BuildError("repository must be exact Git root")
    if (
        not re.fullmatch(r"[0-9a-f]{40}", commit)
        or run(["git", "cat-file", "-t", commit], repo) != "commit"
    ):
        raise BuildError("authorized commit is invalid or unavailable")
    artifact = output / f"Forwarder-{label}-{commit[:7]}.zip"
    sidecar = output / (artifact.name + ".manifest.json")
    if artifact.exists() or sidecar.exists():
        raise BuildError("refusing to overwrite output")
    with tempfile.TemporaryDirectory(prefix="forwarder-authorized-source-") as raw:
        source = Path(raw) / "source"
        run(["git", "worktree", "add", "--detach", str(source), commit], repo)
        try:
            baseline = validate_source(source, commit)
            tools = {"gates": "skipped-for-test"} if skip_gates else gates(source)
            with tempfile.TemporaryDirectory(
                prefix="forwarder-package-"
            ) as package_raw:
                package = Path(package_raw)
                assemble(source, package)
                verify_tree(package)
                records = []
                for path in sorted(package.rglob("*")):
                    if path.is_file():
                        records.append(
                            {
                                "path": path.relative_to(package).as_posix(),
                                "bytes": path.stat().st_size,
                                "sha256": file_hash(path),
                            }
                        )
                content_hash = hashlib.sha256(
                    "".join(f"{x['path']}\0{x['sha256']}\n" for x in records).encode()
                ).hexdigest()
                manifest = {
                    "manifest_schema": "forwarder-release-content-v2",
                    "release_label": label,
                    "source_commit": commit,
                    "build_utc": datetime.now(timezone.utc)
                    .replace(microsecond=0)
                    .isoformat(),
                    "alembic_head": EXPECTED_HEAD,
                    "baseline_catalog_version": baseline["catalog_version"],
                    "baseline_checksum": baseline["checksum"],
                    "baseline_count": 9,
                    "artifact_filename": artifact.name,
                    "content_hash": "sha256:" + content_hash,
                    "content_hash_definition": "SHA-256 of sorted path\\0file-sha256\\n records excluding release-manifest.json",
                    "toolchain": tools,
                    "files": records,
                }
                (package / "release-manifest.json").write_text(
                    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with zipfile.ZipFile(
                    artifact, "x", zipfile.ZIP_DEFLATED, compresslevel=9
                ) as archive:
                    for path in sorted(package.rglob("*")):
                        if path.is_file():
                            archive.write(path, path.relative_to(package).as_posix())
        finally:
            run(["git", "worktree", "remove", "--force", str(source)], repo)
    outer = {
        "manifest_schema": "forwarder-release-artifact-v1",
        "artifact_filename": artifact.name,
        "artifact_size": artifact.stat().st_size,
        "artifact_sha256": file_hash(artifact),
        "source_commit": commit,
        "alembic_head": EXPECTED_HEAD,
        "baseline_catalog_version": BASELINE_VERSION,
        "baseline_checksum": BASELINE_CHECKSUM,
        "baseline_count": 9,
    }
    sidecar.write_text(
        json.dumps(outer, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return artifact, sidecar


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repository", required=True, type=Path)
    p.add_argument("--authorized-commit", required=True)
    p.add_argument("--output-directory", required=True, type=Path)
    p.add_argument("--release-label", required=True)
    p.add_argument("--skip-gates", action="store_true", help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    artifact, sidecar = build(
        a.repository,
        a.authorized_commit,
        a.output_directory,
        a.release_label,
        skip_gates=a.skip_gates,
    )
    print(
        json.dumps(
            {
                "artifact": str(artifact),
                "manifest": str(sidecar),
                "bytes": artifact.stat().st_size,
                "sha256": file_hash(artifact),
                "source_commit": a.authorized_commit,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"release build failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
