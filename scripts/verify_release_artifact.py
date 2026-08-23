"""Verify a Forwarder release ZIP and sidecar manifest."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(artifact, sidecar):
    artifact, sidecar = Path(artifact).resolve(), Path(sidecar).resolve()
    outer = json.loads(sidecar.read_text(encoding="utf-8"))
    if (
        outer["artifact_filename"] != artifact.name
        or outer["artifact_size"] != artifact.stat().st_size
        or outer["artifact_sha256"] != digest(artifact.read_bytes())
    ):
        raise RuntimeError("artifact identity mismatch")
    with zipfile.ZipFile(artifact) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            PurePosixPath(x).is_absolute() or ".." in PurePosixPath(x).parts
            for x in names
        ):
            raise RuntimeError("unsafe ZIP members")
        required = {
            "dist/index.html",
            "requirements.txt",
            "requirements-release.txt",
            "manage.py",
            "release-manifest.json",
            "backend/global_logistics_point_catalog.py",
            "backend/global_logistics_point_catalog_cli.py",
            "backend/reference_data/global-logistics-points-china-iran-v1.0.0-approved-baseline.json",
        }
        if not required <= set(names) or not any(
            x.startswith("backend/migrations/") for x in names
        ):
            raise RuntimeError("required structure missing")
        inner = json.loads(archive.read("release-manifest.json").decode("utf-8"))
        expected = {x["path"]: x for x in inner["files"]}
        if set(expected) != set(names) - {"release-manifest.json"}:
            raise RuntimeError("manifest membership mismatch")
        for name, record in expected.items():
            data = archive.read(name)
            if len(data) != record["bytes"] or digest(data) != record["sha256"]:
                raise RuntimeError(f"content mismatch: {name}")
    for key in ("source_commit", "alembic_head", "baseline_checksum"):
        if inner[key] != outer[key]:
            raise RuntimeError(f"manifest identity mismatch: {key}")
    return outer


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--artifact", required=True)
    p.add_argument("--manifest", required=True)
    a = p.parse_args(argv)
    print(json.dumps(verify(a.artifact, a.manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
