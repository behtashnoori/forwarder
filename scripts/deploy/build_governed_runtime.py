"""Freeze and verify the relocatable Windows runtime used by REQ-12."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

EPOCH = (2026, 9, 3, 0, 0, 0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main(source: Path, artifact: Path) -> int:
    source = source.resolve()
    python = source / "python.exe"
    if not python.is_file() or not (source / "python312._pth").is_file():
        raise RuntimeError("source is not the qualified relocatable Python runtime")
    probe = subprocess.run(
        [str(python), "-c", "import flask,sqlalchemy,waitress,psycopg2;print('RUNTIME_IMPORTS=PASS')"],
        text=True, capture_output=True, timeout=30,
    )
    if probe.returncode or probe.stdout.strip() != "RUNTIME_IMPORTS=PASS":
        raise RuntimeError(f"runtime dependency probe failed: {probe.stderr}")
    if artifact.exists() or artifact.with_suffix(artifact.suffix + ".manifest.json").exists():
        raise RuntimeError("refusing to overwrite governed runtime artifact")
    files = sorted(p for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    records = []
    with zipfile.ZipFile(artifact, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
            records.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "schema": "forwarder-governed-windows-runtime-v1",
        "python_version": subprocess.check_output([str(python), "-c", "import platform;print(platform.python_version())"], text=True).strip(),
        "architecture": subprocess.check_output([str(python), "-c", "import platform;print(platform.machine())"], text=True).strip(),
        "artifact": artifact.name,
        "artifact_bytes": artifact.stat().st_size,
        "artifact_sha256": sha256(artifact),
        "files": records,
    }
    sidecar = artifact.with_suffix(artifact.suffix + ".manifest.json")
    sidecar.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(artifact), "sha256": manifest["artifact_sha256"], "manifest": str(sidecar), "manifest_sha256": sha256(sidecar)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2])))
    except (IndexError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
