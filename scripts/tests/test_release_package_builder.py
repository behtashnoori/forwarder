import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


builder = module("release_builder", ROOT / "scripts/build_release_package.py")
verifier = module("release_verifier", ROOT / "scripts/verify_release_artifact.py")


def test_builder_pins_current_head_and_approved_baseline():
    assert builder.EXPECTED_HEAD == "20260908_governed_international_geography"
    payload = json.loads((ROOT / builder.BASELINE).read_text(encoding="utf-8"))
    assert builder.canonical(payload) == builder.BASELINE_CHECKSUM
    assert len(payload["approved_global_logistics_points"]) == 9


def test_builder_rejects_non_full_or_unavailable_authorized_commit(tmp_path):
    with pytest.raises(builder.BuildError, match="authorized commit"):
        builder.build(ROOT, "052a63d", tmp_path, "test", skip_gates=True)


def test_external_release_commands_are_bounded_and_timeout_is_diagnostic(tmp_path):
    with pytest.raises(builder.BuildError, match="TIMEOUT") as failure:
        builder.run(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            tmp_path,
            timeout_seconds=0.05,
        )
    message = str(failure.value)
    assert '"outcome": "TIMEOUT"' in message
    assert '"process_id"' in message
    assert '"working_directory"' in message


def test_npm_commands_have_specific_bounded_contracts():
    source = (ROOT / "scripts/build_release_package.py").read_text(encoding="utf-8")
    assert 'NPM_CI_TIMEOUT_SECONDS = 600' in source
    assert 'NPM_BUILD_TIMEOUT_SECONDS = 300' in source
    assert 'subprocess.CREATE_NEW_PROCESS_GROUP' in source
    assert '"taskkill.exe", "/PID", str(process.pid), "/T", "/F"' in source
    assert '"taskkill.exe", "/IM"' not in source


def test_artifact_verifier_checks_structure_hashes_and_membership(tmp_path):
    files = {
        "dist/index.html": b"ok",
        "requirements.txt": b"r",
        "requirements-release.txt": b"rr",
        "manage.py": b"m",
        "backend/migrations/alembic.ini": b"a",
        "backend/global_logistics_point_catalog.py": b"g",
        "backend/global_logistics_point_catalog_cli.py": b"c",
        "backend/reference_data/global-logistics-points-china-iran-v1.0.0-approved-baseline.json": b"{}",
    }
    records = [
        {"path": k, "bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()}
        for k, v in sorted(files.items())
    ]
    inner = {
        "source_commit": "a" * 40,
        "alembic_head": builder.EXPECTED_HEAD,
        "baseline_checksum": builder.BASELINE_CHECKSUM,
        "files": records,
    }
    artifact = tmp_path / "candidate.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr("release-manifest.json", json.dumps(inner))
    outer = {
        "artifact_filename": artifact.name,
        "artifact_size": artifact.stat().st_size,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "source_commit": "a" * 40,
        "alembic_head": builder.EXPECTED_HEAD,
        "baseline_checksum": builder.BASELINE_CHECKSUM,
    }
    sidecar = tmp_path / "candidate.zip.manifest.json"
    sidecar.write_text(json.dumps(outer), encoding="utf-8")
    assert (
        verifier.verify(artifact, sidecar)["artifact_sha256"]
        == outer["artifact_sha256"]
    )
    artifact.write_bytes(artifact.read_bytes() + b"tamper")
    with pytest.raises(RuntimeError, match="identity"):
        verifier.verify(artifact, sidecar)
