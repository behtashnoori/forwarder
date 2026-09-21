"""Build the governed legacy Production byte-identity witness."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


EXPECTED_ARCHIVE_SHA256 = "e9196ad9cc10dfeef44eba40d98e50520af4c505474211d5c23397bdf7774617"
EXPECTED_SOURCE_SHA = "e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4"
EXPECTED_CANDIDATE = "Forwarder-Operational-Workspace-Production-CERTIFIED"
EXPECTED_DATABASE_REVISION = "20260921_shipment_evidence_ownership"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = args.source_archive.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError("refusing to overwrite legacy witness")
    if sha256_file(source) != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("legacy Production source witness SHA256 mismatch")

    with zipfile.ZipFile(source) as bundle:
        names = sorted(name.replace("\\", "/") for name in bundle.namelist())
        if "release-manifest.json" not in names:
            raise RuntimeError("legacy source manifest missing")
        manifest = json.loads(bundle.read("release-manifest.json"))
        if (
            manifest.get("application_source_commit") != EXPECTED_SOURCE_SHA
            or manifest.get("candidate") != EXPECTED_CANDIDATE
            or manifest.get("required_db_revision") != EXPECTED_DATABASE_REVISION
        ):
            raise RuntimeError("legacy source manifest identity mismatch")
        files: list[dict[str, object]] = []
        for name in names:
            path = PurePosixPath(name)
            if name == "release-manifest.json" or name.endswith("/"):
                continue
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError("unsafe legacy witness path")
            payload = bundle.read(name)
            files.append({"path": name, "bytes": len(payload), "sha256": sha256_bytes(payload)})

    canonical = "".join(f"{item['path']}\0{item['sha256']}\n" for item in files).encode("utf-8")
    frontend_count = sum(1 for item in files if str(item["path"]).startswith("dist/"))
    backend_count = sum(1 for item in files if str(item["path"]).startswith("backend/"))
    witness = {
        "schema": "forwarder-v1.10.0-legacy-production-witness-v1",
        "authority": "preserved_current_production_source_20260921",
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "candidate": EXPECTED_CANDIDATE,
        "application_source_commit": EXPECTED_SOURCE_SHA,
        "application_version": None,
        "required_database_revision": EXPECTED_DATABASE_REVISION,
        "inventory_sha256": sha256_bytes(canonical),
        "file_count": len(files),
        "frontend_file_count": frontend_count,
        "backend_file_count": backend_count,
        "files": files,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(witness, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: witness[key] for key in witness if key != "files"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
